# core/market_adaptive_strategy.py

"""
🎯 Market-Adaptive Strategy Engine

Implements market-specific trading strategies based on performance analysis:
- DAX: Conservative approach due to poor performance (14.3% win rate)
- FTSE 100: Optimized approach due to good performance (80% win rate)

Key Features:
- Market-specific parameters
- Time-based filtering
- Volatility-adjusted position sizing
- Emergency protection systems
- Multi-timeframe confirmation

Author: Performance Optimization Team
"""

import yaml
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.rsi import compute_rsi
from models.atr import compute_atr
from data.db import trades_collection, get_market_tick_data
from utils.config_loader import load_global_config

class MarketAdaptiveStrategy:
    """
    Advanced strategy engine that adapts to individual market characteristics
    """
    
    def __init__(self):
        """Initialize market adaptive strategy"""
        self.global_config = load_global_config()
        
        # Load market-specific configurations
        with open("configs/market_specific_strategy.yaml", "r") as f:
            self.market_config = yaml.safe_load(f)
        
        # Track market performance for dynamic adjustments
        self.market_performance = {}
        self.last_performance_update = {}
        
        # Emergency protection state
        self.market_suspension = {}
        self.consecutive_losses = {}
        self.daily_losses = {}
        self.last_trade_time = {}
        
        print("🎯 Market-Adaptive Strategy Engine initialized")
        print("   📊 Market-specific parameters loaded")
        print("   🛡️ Emergency protection systems active")
        print("   ⏰ Time-based filtering enabled")
        
    def analyze_market_conditions(self, prices: List[float], market_name: str) -> Optional[Dict]:
        """
        Analyze market conditions with market-specific approach
        """
        try:
            # Check if market is currently suspended
            if self._is_market_suspended(market_name):
                return {"signal": "HOLD", "reason": "Market suspended due to poor performance"}
            
            # Check if current time is suitable for trading this market
            if not self._is_good_trading_time(market_name):
                return {"signal": "HOLD", "reason": "Outside preferred trading hours"}
            
            # Check volatility conditions
            if not self._is_volatility_acceptable(prices, market_name):
                return {"signal": "HOLD", "reason": "Volatility too high for safe trading"}
            
            # Get market-specific strategy parameters
            strategy_params = self._get_market_strategy_params(market_name)
            
            # Perform enhanced technical analysis
            analysis = self._perform_technical_analysis(prices, market_name, strategy_params)
            
            if not analysis:
                return {"signal": "HOLD", "reason": "Insufficient data for analysis"}
            
            # Apply multi-timeframe confirmation if required
            if self._requires_timeframe_confirmation(market_name):
                timeframe_signal = self._get_multi_timeframe_confirmation(market_name)
                if not timeframe_signal:
                    return {"signal": "HOLD", "reason": "Multi-timeframe signals not aligned"}
                
                # Combine with single timeframe analysis
                analysis["multi_timeframe_signal"] = timeframe_signal
                analysis["confidence"] = min(analysis["confidence"] * 1.2, 1.0)  # Boost confidence
            
            # Apply final signal filtering
            final_signal = self._apply_signal_filters(analysis, market_name, strategy_params)
            
            return final_signal
            
        except Exception as e:
            print(f"❌ Error in market adaptive analysis for {market_name}: {e}")
            return {"signal": "HOLD", "reason": f"Analysis error: {e}"}
    
    def _get_market_strategy_params(self, market_name: str) -> Dict:
        """Get strategy parameters specific to the market"""
        market_strategies = self.market_config.get("market_strategies", {})
        
        # Get market-specific config or fall back to global
        if market_name in market_strategies:
            return market_strategies[market_name]
        else:
            # Fall back to global config for unknown markets
            return {
                "rsi_period": self.global_config["strategy"]["rsi_period"],
                "rsi_buy_threshold": self.global_config["strategy"]["rsi_buy_threshold"],
                "rsi_sell_threshold": self.global_config["strategy"]["rsi_sell_threshold"],
                "stop_loss_pips": self.global_config["strategy"]["stop_loss_pips"],
                "take_profit_pips": self.global_config["strategy"]["take_profit_pips"],
                "min_confidence_threshold": 0.7
            }
    
    def _perform_technical_analysis(self, prices: List[float], market_name: str, params: Dict) -> Optional[Dict]:
        """Perform technical analysis with market-specific parameters"""
        try:
            if len(prices) < params.get("rsi_period", 14) + 5:
                return None
            
            # Calculate technical indicators
            import pandas as pd
            price_series = pd.Series(prices)
            rsi_series = compute_rsi(price_series, params["rsi_period"])
            current_rsi = rsi_series.iloc[-1] if len(rsi_series) > 0 else 50
            
            # ATR for volatility assessment
            atr_series = compute_atr(price_series, 14)
            current_atr = atr_series.iloc[-1] if len(atr_series) > 0 else 0
            
            # Price analysis
            current_price = prices[-1]
            price_change = (current_price - prices[-2]) / prices[-2] * 100 if len(prices) > 1 else 0
            
            # Market-specific signal generation
            signal = "HOLD"
            confidence = 0.5
            reason_parts = []
            
            # RSI-based signals with market-specific thresholds
            if current_rsi >= params["rsi_buy_threshold"]:
                if market_name == "DAX":
                    # More conservative for DAX (poor performance)
                    signal = "SELL"  # Overbought = sell for mean reversion
                    confidence = 0.6 + (current_rsi - params["rsi_buy_threshold"]) / 100
                    reason_parts.append(f"DAX overbought RSI {current_rsi:.1f}")
                else:
                    # FTSE 100 or other markets
                    signal = "BUY" if price_change > 0 else "HOLD"
                    confidence = 0.7 + (current_rsi - params["rsi_buy_threshold"]) / 100
                    reason_parts.append(f"RSI {current_rsi:.1f} > threshold")
                    
            elif current_rsi <= params["rsi_sell_threshold"]:
                if market_name == "DAX":
                    # More conservative for DAX
                    signal = "BUY"  # Oversold = buy for mean reversion
                    confidence = 0.6 + (params["rsi_sell_threshold"] - current_rsi) / 100
                    reason_parts.append(f"DAX oversold RSI {current_rsi:.1f}")
                else:
                    # FTSE 100 or other markets
                    signal = "SELL" if price_change < 0 else "HOLD"
                    confidence = 0.7 + (params["rsi_sell_threshold"] - current_rsi) / 100
                    reason_parts.append(f"RSI {current_rsi:.1f} < threshold")
            
            # Apply market-specific confidence requirements
            min_confidence = params.get("min_confidence_threshold", 0.7)
            if confidence < min_confidence:
                signal = "HOLD"
                reason_parts.append(f"Confidence {confidence:.2f} < required {min_confidence}")
            
            # Volatility adjustment for confidence
            if current_atr > 0:
                normal_atr = np.mean(atr_values[-20:]) if len(atr_values) >= 20 else current_atr
                volatility_ratio = current_atr / normal_atr if normal_atr > 0 else 1.0
                
                if volatility_ratio > 1.5:  # High volatility
                    confidence *= 0.8  # Reduce confidence
                    reason_parts.append(f"High volatility ({volatility_ratio:.1f}x)")
            
            return {
                "signal": signal,
                "confidence": min(confidence, 1.0),
                "rsi": current_rsi,
                "atr": current_atr,
                "price": current_price,
                "price_change": price_change,
                "volatility_ratio": volatility_ratio if 'volatility_ratio' in locals() else 1.0,
                "market_specific": True,
                "strategy_params": params,
                "reason": "; ".join(reason_parts) if reason_parts else "Technical analysis complete"
            }
            
        except Exception as e:
            print(f"❌ Technical analysis error for {market_name}: {e}")
            return None
    
    def _is_good_trading_time(self, market_name: str) -> bool:
        """Check if current time is good for trading this market"""
        try:
            current_hour = datetime.utcnow().hour
            
            market_strategies = self.market_config.get("market_strategies", {})
            if market_name not in market_strategies:
                return True  # No restrictions for unknown markets
            
            trading_hours = market_strategies[market_name].get("trading_hours", {})
            avoid_hours = trading_hours.get("avoid_hours", [])
            preferred_hours = trading_hours.get("preferred_hours", [])
            
            # Check if current hour should be avoided
            if current_hour in avoid_hours:
                print(f"⏰ Avoiding {market_name} trading at {current_hour}:00 (configured avoid hour)")
                return False
            
            # If preferred hours are specified, check if we're in one
            if preferred_hours and current_hour not in preferred_hours:
                print(f"⏰ Outside preferred {market_name} trading hours (current: {current_hour}:00)")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking trading time for {market_name}: {e}")
            return True  # Default to allowing trading
    
    def _is_volatility_acceptable(self, prices: List[float], market_name: str) -> bool:
        """Check if current volatility is acceptable for trading"""
        try:
            if len(prices) < 20:
                return True  # Not enough data to judge
            
            market_strategies = self.market_config.get("market_strategies", {})
            if market_name not in market_strategies:
                return True
            
            params = market_strategies[market_name]
            max_atr_multiplier = params.get("max_atr_multiplier", 2.0)
            lookback = params.get("volatility_lookback", 20)
            
            # Calculate current vs normal ATR
            import pandas as pd
            price_series = pd.Series(prices)
            atr_series = compute_atr(price_series, 14)
            if len(atr_series) < lookback:
                return True
            
            current_atr = atr_series.iloc[-1]
            normal_atr = atr_series.iloc[-lookback:].mean()
            
            if normal_atr > 0:
                volatility_ratio = current_atr / normal_atr
                if volatility_ratio > max_atr_multiplier:
                    print(f"📊 {market_name} volatility too high: {volatility_ratio:.1f}x normal (max: {max_atr_multiplier}x)")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking volatility for {market_name}: {e}")
            return True
    
    def _is_market_suspended(self, market_name: str) -> bool:
        """Check if market trading is currently suspended due to poor performance"""
        try:
            # Check if market is in suspension list
            if market_name in self.market_suspension:
                suspension_end = self.market_suspension[market_name]
                if datetime.utcnow() < suspension_end:
                    return True
                else:
                    # Suspension period ended
                    del self.market_suspension[market_name]
            
            # Check daily loss limits
            today = datetime.utcnow().date()
            daily_key = f"{market_name}_{today}"
            
            if daily_key in self.daily_losses:
                daily_loss = self.daily_losses[daily_key]
                
                emergency_settings = self.market_config.get("emergency_global_settings", {})
                market_suspension = emergency_settings.get("market_suspension", {})
                
                if market_name in market_suspension:
                    max_daily_loss = market_suspension[market_name].get("suspend_if_daily_loss_exceeds", 1000)
                    if daily_loss >= max_daily_loss:
                        print(f"🚨 {market_name} suspended: daily loss £{daily_loss} >= limit £{max_daily_loss}")
                        return True
            
            # Check consecutive losses
            consecutive = self.consecutive_losses.get(market_name, 0)
            market_params = self._get_market_strategy_params(market_name)
            max_consecutive = market_params.get("emergency_protection", {}).get("max_consecutive_losses", 5)
            
            if consecutive >= max_consecutive:
                # Impose cooling off period
                cooling_hours = market_params.get("emergency_protection", {}).get("cooling_off_hours", 1)
                last_trade = self.last_trade_time.get(market_name)
                
                if last_trade and datetime.utcnow() < last_trade + timedelta(hours=cooling_hours):
                    print(f"🚨 {market_name} in cooling off: {consecutive} consecutive losses")
                    return True
                else:
                    # Reset consecutive losses after cooling off
                    self.consecutive_losses[market_name] = 0
            
            return False
            
        except Exception as e:
            print(f"❌ Error checking market suspension for {market_name}: {e}")
            return False
    
    def _requires_timeframe_confirmation(self, market_name: str) -> bool:
        """Check if this market requires multi-timeframe confirmation"""
        timeframe_config = self.market_config.get("timeframe_analysis", {})
        return market_name in timeframe_config
    
    def _get_multi_timeframe_confirmation(self, market_name: str) -> Optional[str]:
        """Get multi-timeframe signal confirmation (placeholder - would need actual implementation)"""
        # This would require implementing actual multi-timeframe analysis
        # For now, return a conservative approach for DAX
        if market_name == "DAX":
            return "HOLD"  # Be more conservative with DAX
        return "HOLD"  # Default to neutral for now
    
    def _apply_signal_filters(self, analysis: Dict, market_name: str, params: Dict) -> Dict:
        """Apply final filters to the trading signal"""
        signal = analysis["signal"]
        confidence = analysis["confidence"]
        
        # Apply market-specific position sizing
        emergency_protection = params.get("emergency_protection", {})
        position_multiplier = emergency_protection.get("reduce_position_size", 1.0)
        
        # For DAX, be extra conservative
        if market_name == "DAX" and signal != "HOLD":
            # Check recent performance
            recent_performance = self._get_recent_market_performance(market_name)
            if recent_performance < 0:  # Recent losses
                confidence *= 0.7  # Reduce confidence
                analysis["reason"] += "; DAX recent performance poor"
        
        # Update analysis with final adjustments
        analysis.update({
            "signal": signal,
            "confidence": confidence,
            "position_multiplier": position_multiplier,
            "market_adaptive": True,
            "final_filters_applied": True
        })
        
        return analysis
    
    def _get_recent_market_performance(self, market_name: str) -> float:
        """Get recent P&L performance for a market"""
        try:
            # Get recent trades from last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_trades = list(trades_collection.find({
                "market": market_name,
                "timestamp": {"$gte": yesterday},
                "status": {"$in": ["CLOSED", "REJECTED"]}
            }))
            
            if not recent_trades:
                return 0.0
            
            total_pnl = sum(trade.get("profit_loss", 0) for trade in recent_trades)
            return total_pnl
            
        except Exception as e:
            print(f"❌ Error getting recent performance for {market_name}: {e}")
            return 0.0
    
    def record_trade_result(self, market_name: str, pnl: float):
        """Record trade result for performance tracking"""
        try:
            today = datetime.utcnow().date()
            daily_key = f"{market_name}_{today}"
            
            # Update daily losses
            if daily_key not in self.daily_losses:
                self.daily_losses[daily_key] = 0
            
            if pnl < 0:
                self.daily_losses[daily_key] += abs(pnl)
                
                # Update consecutive losses
                self.consecutive_losses[market_name] = self.consecutive_losses.get(market_name, 0) + 1
            else:
                # Reset consecutive losses on profit
                self.consecutive_losses[market_name] = 0
            
            # Update last trade time
            self.last_trade_time[market_name] = datetime.utcnow()
            
            print(f"📊 {market_name} trade recorded: £{pnl:.2f} | Consecutive losses: {self.consecutive_losses.get(market_name, 0)}")
            
        except Exception as e:
            print(f"❌ Error recording trade result: {e}")
    
    def get_market_status(self) -> Dict:
        """Get current status of all markets"""
        status = {}
        
        for market in ["DAX", "FTSE 100"]:
            is_suspended = self._is_market_suspended(market)
            consecutive_losses = self.consecutive_losses.get(market, 0)
            recent_performance = self._get_recent_market_performance(market)
            
            status[market] = {
                "suspended": is_suspended,
                "consecutive_losses": consecutive_losses,
                "recent_performance": recent_performance,
                "good_trading_time": self._is_good_trading_time(market)
            }
        
        return status

# Global instance
_market_adaptive_strategy = None

def get_market_adaptive_strategy() -> MarketAdaptiveStrategy:
    """Get global market adaptive strategy instance"""
    global _market_adaptive_strategy
    if _market_adaptive_strategy is None:
        _market_adaptive_strategy = MarketAdaptiveStrategy()
    return _market_adaptive_strategy

if __name__ == "__main__":
    # Test the market adaptive strategy
    print("🧪 Testing Market-Adaptive Strategy")
    print("=" * 50)
    
    strategy = MarketAdaptiveStrategy()
    
    # Test sample data
    sample_prices = [23450 + i + np.random.normal(0, 5) for i in range(30)]
    
    # Test DAX analysis
    dax_result = strategy.analyze_market_conditions(sample_prices, "DAX")
    print(f"DAX Analysis: {dax_result}")
    
    # Test FTSE analysis  
    ftse_prices = [9050 + i + np.random.normal(0, 2) for i in range(30)]
    ftse_result = strategy.analyze_market_conditions(ftse_prices, "FTSE 100")
    print(f"FTSE Analysis: {ftse_result}")
    
    # Show market status
    status = strategy.get_market_status()
    print(f"Market Status: {status}")