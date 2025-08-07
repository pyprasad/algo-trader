# core/dynamic_position_manager.py

"""
🚀 Dynamic Position Manager

Dynamically adjusts take profit limits based on:
- Real-time P&L performance
- Strategy confidence levels
- Market condition changes
- Expected vs actual performance

This advanced risk management system can:
- Increase limits when strategy confidence is high
- Reduce limits when performance deteriorates
- Adapt to changing market conditions in real-time
- Protect against adverse moves while capturing more upside

Author: Advanced Risk Management System
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import yaml
import json
import requests
from dataclasses import dataclass

# Load configurations
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

from data.db import trades_collection, get_market_tick_data
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from data.trade_streamer import get_live_active_trades
from api.ig_position_manager import get_ig_position_manager

@dataclass
class PositionAnalysis:
    """Container for position analysis results"""
    deal_reference: str
    current_pnl: float
    entry_price: float
    current_price: float
    direction: str
    size: float
    expected_pnl: float
    strategy_confidence: float
    market_regime: str
    recommended_limit_multiplier: float
    reason: str

class DynamicPositionManager:
    """
    Advanced position manager that dynamically adjusts take profit limits
    based on real-time performance and strategy confidence
    """
    
    def __init__(self):
        """Initialize the dynamic position manager"""
        # Load configuration
        self.enabled = config.get("dynamic_limits", {}).get("enabled", False)
        self.update_interval = config.get("dynamic_limits", {}).get("update_interval_seconds", 30)
        self.confidence_threshold = config.get("dynamic_limits", {}).get("confidence_threshold", 0.7)
        self.max_increase = config.get("dynamic_limits", {}).get("max_limit_increase", 2.0)
        self.min_decrease = config.get("dynamic_limits", {}).get("min_limit_decrease", 0.5)
        self.pnl_threshold = config.get("dynamic_limits", {}).get("pnl_threshold_percent", 5.0)
        self.lookback_minutes = config.get("dynamic_limits", {}).get("strategy_lookback_minutes", 15)
        
        # Emergency protection configuration
        emergency_config = config.get("dynamic_limits", {}).get("emergency_protection", {})
        self.emergency_enabled = emergency_config.get("enabled", True)
        self.immediate_loss_threshold = emergency_config.get("immediate_loss_threshold", 15)
        self.rapid_check_interval = emergency_config.get("rapid_check_interval", 5)
        self.rapid_check_duration = emergency_config.get("rapid_check_duration", 300)
        self.emergency_stop_multiplier = emergency_config.get("emergency_stop_multiplier", 0.7)
        self.adverse_signal_close = emergency_config.get("adverse_signal_close", True)
        
        # IG API configuration
        self.ig_config = config["ig"]
        self.session_token = None
        self.cst_token = None
        
        # Internal state
        self.running = False
        self.positions_being_managed = {}  # deal_reference -> last_update_time
        self.position_adjustments = []  # History of adjustments
        self.emergency_positions = {}  # deal_reference -> entry_time (for rapid checking)
        self.strategy_engine = get_enhanced_strategy_engine()
        self.ig_manager = get_ig_position_manager() if self.enabled else None
        self.lock = threading.Lock()
        
        print(f"🚀 Dynamic Position Manager initialized")
        print(f"   Status: {'✅ ENABLED' if self.enabled else '❌ DISABLED'}")
        if self.enabled:
            print(f"   Update Interval: {self.update_interval}s")
            print(f"   Confidence Threshold: {self.confidence_threshold}")
            print(f"   Limit Range: {self.min_decrease}x - {self.max_increase}x")
            print(f"   P&L Threshold: {self.pnl_threshold}%")
            if self.emergency_enabled:
                print(f"   🚨 Emergency Protection: ACTIVE")
                print(f"      Loss Threshold: {self.immediate_loss_threshold} pips")
                print(f"      Rapid Check: Every {self.rapid_check_interval}s for {self.rapid_check_duration//60}min")
                print(f"      Emergency Stop: {self.emergency_stop_multiplier}x tighter")
    
    def start(self):
        """Start the dynamic position management thread"""
        if not self.enabled:
            print("⚠️ Dynamic Position Manager is disabled - set dynamic_limits.enabled=true to activate")
            return False
            
        print("🚀 Starting Dynamic Position Manager...")
        self.running = True
        
        # Start the management thread
        self.management_thread = threading.Thread(target=self._management_loop, daemon=True)
        self.management_thread.start()
        
        # Start emergency protection thread if enabled
        if self.emergency_enabled:
            self.emergency_thread = threading.Thread(target=self._emergency_protection_loop, daemon=True)
            self.emergency_thread.start()
            print("🚨 Emergency protection thread started")
        
        print("✅ Dynamic Position Manager started")
        return True
    
    def stop(self):
        """Stop the dynamic position management"""
        print("🛑 Stopping Dynamic Position Manager...")
        self.running = False
        if hasattr(self, 'management_thread'):
            self.management_thread.join(timeout=5)
        print("✅ Dynamic Position Manager stopped")
    
    def _management_loop(self):
        """Main management loop that runs continuously"""
        while self.running:
            try:
                # Get all open positions
                open_positions = self._get_open_positions()
                
                if open_positions:
                    print(f"🔍 Analyzing {len(open_positions)} open positions for dynamic adjustments...")
                    
                    for position in open_positions:
                        if self.running:  # Check if still running
                            self._analyze_and_adjust_position(position)
                else:
                    print("📊 No open positions to manage")
                
                # Wait before next analysis
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"❌ Error in dynamic position management loop: {e}")
                time.sleep(self.update_interval)
    
    def _emergency_protection_loop(self):
        """Emergency protection loop - rapid checking for new positions"""
        while self.running:
            try:
                if not self.emergency_positions:
                    time.sleep(5)  # No emergency positions to monitor
                    continue
                
                current_time = time.time()
                positions_to_remove = []
                
                for deal_reference, entry_time in self.emergency_positions.items():
                    # Check if position is past emergency monitoring period
                    if current_time - entry_time > self.rapid_check_duration:
                        positions_to_remove.append(deal_reference)
                        continue
                    
                    # Perform emergency checks
                    self._perform_emergency_check(deal_reference)
                
                # Remove positions that are past monitoring period
                for deal_ref in positions_to_remove:
                    with self.lock:
                        self.emergency_positions.pop(deal_ref, None)
                        print(f"📊 Ended emergency monitoring for {deal_ref}")
                
                # Sleep for rapid check interval
                time.sleep(self.rapid_check_interval)
                
            except Exception as e:
                print(f"❌ Error in emergency protection loop: {e}")
                time.sleep(self.rapid_check_interval)
    
    def _get_open_positions(self) -> List[Dict]:
        """Get all currently open positions from database and live data"""
        try:
            # Get positions from database
            db_positions = list(trades_collection.find({"status": "OPEN"}))
            
            # Enhance with live data if available
            try:
                live_positions = get_live_active_trades()
                # Merge live data with database positions
                for db_pos in db_positions:
                    deal_ref = db_pos.get("deal_reference")
                    if deal_ref in live_positions:
                        db_pos.update(live_positions[deal_ref])
            except:
                pass  # Live data not available, use database only
            
            return db_positions
            
        except Exception as e:
            print(f"❌ Error getting open positions: {e}")
            return []
    
    def _analyze_and_adjust_position(self, position: Dict):
        """Analyze a position and adjust limits if needed"""
        try:
            deal_reference = position.get("deal_reference")
            if not deal_reference:
                return
            
            # Skip if we've recently adjusted this position
            with self.lock:
                last_update = self.positions_being_managed.get(deal_reference, 0)
                if time.time() - last_update < self.update_interval:
                    return
                self.positions_being_managed[deal_reference] = time.time()
            
            # Perform position analysis
            analysis = self._perform_position_analysis(position)
            if not analysis:
                return
            
            print(f"📊 Position Analysis for {deal_reference}:")
            print(f"   Current P&L: {analysis.current_pnl:+.2f}")
            print(f"   Expected P&L: {analysis.expected_pnl:+.2f}")
            print(f"   Strategy Confidence: {analysis.strategy_confidence:.2f}")
            print(f"   Market Regime: {analysis.market_regime}")
            print(f"   Recommended Limit Multiplier: {analysis.recommended_limit_multiplier:.2f}x")
            print(f"   Reason: {analysis.reason}")
            
            # Check if adjustment is needed
            current_multiplier = self._get_current_limit_multiplier(position)
            
            if abs(analysis.recommended_limit_multiplier - current_multiplier) >= 0.2:  # Significant change
                success = self._adjust_position_limit(position, analysis)
                if success:
                    # Record the adjustment
                    adjustment = {
                        "timestamp": datetime.utcnow(),
                        "deal_reference": deal_reference,
                        "old_multiplier": current_multiplier,
                        "new_multiplier": analysis.recommended_limit_multiplier,
                        "reason": analysis.reason,
                        "current_pnl": analysis.current_pnl,
                        "strategy_confidence": analysis.strategy_confidence
                    }
                    self.position_adjustments.append(adjustment)
                    print(f"✅ Adjusted position {deal_reference}: {current_multiplier:.2f}x → {analysis.recommended_limit_multiplier:.2f}x")
                else:
                    print(f"❌ Failed to adjust position {deal_reference}")
            else:
                print(f"⏸️ No significant adjustment needed for {deal_reference}")
                
        except Exception as e:
            print(f"❌ Error analyzing position {position.get('deal_reference', 'Unknown')}: {e}")
    
    def _perform_position_analysis(self, position: Dict) -> Optional[PositionAnalysis]:
        """Perform comprehensive analysis of a position"""
        try:
            deal_reference = position.get("deal_reference", "Unknown")
            direction = position.get("direction", "BUY")
            entry_price = position.get("actual_entry_price") or position.get("entry_price", 0)
            size = position.get("size", 1)
            market = position.get("market", "Unknown")
            
            # Get current market price with fallback
            recent_ticks = get_market_tick_data(market, limit=50)  # Try to get more data
            if not recent_ticks:
                print(f"⚠️ No recent tick data for {market} - using entry price for analysis")
                current_price = entry_price
                # Create minimal analysis without strategy engine
                return self._create_minimal_analysis(deal_reference, direction, entry_price, current_price, size)
            
            current_price = recent_ticks[0]["bid"]
            
            # Calculate current P&L
            if direction == "BUY":
                current_pnl = (current_price - entry_price) * size
            else:  # SELL
                current_pnl = (entry_price - current_price) * size
            
            # Get strategy analysis for current market conditions with fallback
            if len(recent_ticks) >= 20:
                # Sufficient data for full analysis
                recent_prices = [tick["bid"] for tick in reversed(recent_ticks[-20:])]
                strategy_analysis = self.strategy_engine.analyze_market_conditions(recent_prices, market)
            else:
                # Insufficient data - use available data with warning
                print(f"⚠️ {market}: Limited price data ({len(recent_ticks)} ticks) - using simplified analysis")
                recent_prices = [tick["bid"] for tick in reversed(recent_ticks)]
                
                # Try analysis with available data, but expect it might fail
                strategy_analysis = None
                if len(recent_prices) >= 10:  # Minimum for basic analysis
                    try:
                        strategy_analysis = self.strategy_engine.analyze_market_conditions(recent_prices, market)
                    except:
                        strategy_analysis = None
                
                # If still no analysis, create minimal fallback
                if not strategy_analysis:
                    print(f"📊 {market}: Using fallback analysis due to insufficient data")
                    return self._create_minimal_analysis(deal_reference, direction, entry_price, current_price, size)
            
            strategy_confidence = strategy_analysis.get("confidence", 0.5)
            market_regime = strategy_analysis.get("regime", "neutral")
            current_signal = strategy_analysis.get("signal", "HOLD")
            
            # Calculate expected P&L based on original strategy
            original_tp_pips = config["strategy"]["take_profit_pips"]
            expected_pnl = original_tp_pips * size  # Simplified calculation
            
            # Determine recommended limit multiplier
            multiplier, reason = self._calculate_limit_multiplier(
                current_pnl, expected_pnl, strategy_confidence, 
                market_regime, current_signal, direction
            )
            
            return PositionAnalysis(
                deal_reference=deal_reference,
                current_pnl=current_pnl,
                entry_price=entry_price,
                current_price=current_price,
                direction=direction,
                size=size,
                expected_pnl=expected_pnl,
                strategy_confidence=strategy_confidence,
                market_regime=market_regime,
                recommended_limit_multiplier=multiplier,
                reason=reason
            )
            
        except Exception as e:
            print(f"❌ Error in position analysis: {e}")
            return None
    
    def _calculate_limit_multiplier(self, current_pnl: float, expected_pnl: float, 
                                  confidence: float, regime: str, signal: str, 
                                  direction: str) -> Tuple[float, str]:
        """Calculate the recommended limit multiplier based on analysis"""
        
        base_multiplier = 1.0
        reasons = []
        
        # Factor 1: Strategy Confidence
        if confidence >= self.confidence_threshold:
            if confidence >= 0.85:
                confidence_boost = 0.5  # High confidence = increase limits
                reasons.append(f"High confidence ({confidence:.2f})")
            else:
                confidence_boost = 0.3
                reasons.append(f"Good confidence ({confidence:.2f})")
        else:
            confidence_boost = -0.3  # Low confidence = reduce limits
            reasons.append(f"Low confidence ({confidence:.2f})")
        
        # Factor 2: Current Performance vs Expected
        pnl_ratio = current_pnl / expected_pnl if expected_pnl != 0 else 0
        if pnl_ratio > 1.2:  # Performing 20% better than expected
            performance_boost = 0.4
            reasons.append(f"Outperforming ({pnl_ratio:.1f}x expected)")
        elif pnl_ratio < 0.5:  # Performing poorly
            performance_boost = -0.4
            reasons.append(f"Underperforming ({pnl_ratio:.1f}x expected)")
        else:
            performance_boost = 0
        
        # Factor 3: Market Regime
        if regime == "trending":
            regime_boost = 0.3  # Trending markets = increase limits
            reasons.append("Trending market")
        elif regime == "volatile":
            regime_boost = -0.2  # Volatile markets = reduce limits
            reasons.append("Volatile market")
        else:
            regime_boost = 0  # Mean-reverting = no change
        
        # Factor 4: Signal Alignment
        if signal == direction:  # Signal still aligns with position
            signal_boost = 0.2
            reasons.append("Signal alignment")
        elif signal == "HOLD":
            signal_boost = 0
        else:  # Signal opposes position
            signal_boost = -0.3
            reasons.append("Signal opposition")
        
        # Calculate final multiplier
        total_adjustment = confidence_boost + performance_boost + regime_boost + signal_boost
        final_multiplier = base_multiplier + total_adjustment
        
        # Apply bounds
        final_multiplier = max(self.min_decrease, min(self.max_increase, final_multiplier))
        
        reason = "; ".join(reasons)
        return final_multiplier, reason
    
    def _get_current_limit_multiplier(self, position: Dict) -> float:
        """Get the current limit multiplier for a position"""
        # This would need to query IG API or database for current limit level
        # For now, return 1.0 as baseline
        return 1.0
    
    def _adjust_position_limit(self, position: Dict, analysis: PositionAnalysis) -> bool:
        """Adjust the position's take profit limit via IG API"""
        try:
            deal_id = position.get("deal_id")
            if not deal_id:
                print(f"⚠️ No deal ID found for position {analysis.deal_reference}")
                return False
            
            # Calculate new limit level
            original_tp_pips = config["strategy"]["take_profit_pips"]
            new_tp_pips = original_tp_pips * analysis.recommended_limit_multiplier
            
            if analysis.direction == "BUY":
                new_limit_level = analysis.entry_price + new_tp_pips
            else:  # SELL
                new_limit_level = analysis.entry_price - new_tp_pips
            
            # Call IG API to update position (placeholder - need to implement actual API call)
            success = self._call_ig_update_position_api(deal_id, new_limit_level)
            
            if success:
                print(f"🎯 Updated position {analysis.deal_reference} limit to {new_limit_level:.2f}")
            
            return success
            
        except Exception as e:
            print(f"❌ Error adjusting position limit: {e}")
            return False
    
    def _call_ig_update_position_api(self, deal_id: str, new_limit_level: float) -> bool:
        """Call IG API to update position limit"""
        try:
            if not self.ig_manager:
                print("❌ IG Position Manager not available")
                return False
            
            # Use the IG API to update the take profit limit
            success = self.ig_manager.update_take_profit_only(deal_id, new_limit_level)
            
            if success:
                print(f"✅ Successfully updated deal {deal_id} limit to {new_limit_level:.2f} via IG API")
            else:
                print(f"❌ Failed to update deal {deal_id} limit via IG API")
            
            return success
            
        except Exception as e:
            print(f"❌ Error calling IG API to update position: {e}")
            return False
    
    def add_position_for_emergency_monitoring(self, deal_reference: str):
        """Add a new position for emergency monitoring"""
        if self.emergency_enabled:
            with self.lock:
                self.emergency_positions[deal_reference] = time.time()
                print(f"🚨 Started emergency monitoring for {deal_reference}")
    
    def _perform_emergency_check(self, deal_reference: str):
        """Perform emergency check on a position"""
        try:
            # Get position from database
            position = trades_collection.find_one({"deal_reference": deal_reference, "status": "OPEN"})
            if not position:
                return  # Position might be closed
            
            # Perform position analysis
            analysis = self._perform_position_analysis(position)
            if not analysis:
                return
            
            print(f"🚨 Emergency check for {deal_reference}: P&L {analysis.current_pnl:+.1f} pips")
            
            # Check for immediate loss threshold
            if abs(analysis.current_pnl) >= self.immediate_loss_threshold and analysis.current_pnl < 0:
                print(f"🚨 EMERGENCY: Position {deal_reference} loss {analysis.current_pnl:.1f} exceeds threshold {self.immediate_loss_threshold}")
                self._emergency_close_position(position, analysis, "Loss threshold exceeded")
                return
            
            # Check for adverse signal (if enabled)
            if self.adverse_signal_close:
                current_signal = self._get_current_strategy_signal(position.get("market"))
                position_direction = position.get("direction")
                
                if self._signals_are_opposite(current_signal, position_direction):
                    print(f"🚨 EMERGENCY: Signal flipped opposite for {deal_reference} ({current_signal} vs {position_direction})")
                    self._emergency_close_position(position, analysis, "Signal reversal")
                    return
            
            # If position is significantly losing, tighten stop loss
            if analysis.current_pnl < -5:  # Losing more than 5 pips
                self._emergency_tighten_stop_loss(position, analysis)
                
        except Exception as e:
            print(f"❌ Error in emergency check for {deal_reference}: {e}")
    
    def _get_current_strategy_signal(self, market: str) -> str:
        """Get current strategy signal for a market"""
        try:
            recent_ticks = get_market_tick_data(market, limit=20)
            if not recent_ticks:
                return "HOLD"
            
            prices = [tick["bid"] for tick in reversed(recent_ticks)]
            analysis = self.strategy_engine.analyze_market_conditions(prices, market)
            
            return analysis.get("signal", "HOLD") if analysis else "HOLD"
        except:
            return "HOLD"
    
    def _signals_are_opposite(self, signal: str, direction: str) -> bool:
        """Check if signal is opposite to position direction"""
        if signal == "BUY" and direction == "SELL":
            return True
        elif signal == "SELL" and direction == "BUY":
            return True
        return False
    
    def _emergency_close_position(self, position: Dict, analysis: PositionAnalysis, reason: str):
        """Emergency close a position"""
        try:
            deal_id = position.get("deal_id")
            if not deal_id:
                print(f"❌ No deal ID for emergency close of {analysis.deal_reference}")
                return
            
            print(f"🚨 EMERGENCY CLOSE: {analysis.deal_reference} - {reason}")
            print(f"   Loss: {analysis.current_pnl:.1f} pips")
            
            # Use IG API to close position
            if self.ig_manager:
                success = self.ig_manager.close_position(deal_id)
                if success:
                    print(f"✅ Emergency closed position {analysis.deal_reference}")
                    
                    # CRITICAL: Update database to mark trade as CLOSED
                    try:
                        from data.db import trades_collection
                        update_result = trades_collection.update_one(
                            {"deal_reference": analysis.deal_reference},
                            {
                                "$set": {
                                    "status": "CLOSED",
                                    "close_timestamp": datetime.utcnow(),
                                    "close_level": analysis.current_price,
                                    "close_reason": f"Emergency close: {reason}",
                                    "profit_loss": analysis.current_pnl,
                                    "last_update": datetime.utcnow()
                                }
                            }
                        )
                        
                        if update_result.modified_count > 0:
                            print(f"💾 Database updated: {analysis.deal_reference} marked as CLOSED")
                        else:
                            print(f"⚠️ Database update failed for {analysis.deal_reference}")
                            
                    except Exception as db_error:
                        print(f"❌ Database update error for {analysis.deal_reference}: {db_error}")
                    
                    # Remove from emergency monitoring
                    with self.lock:
                        self.emergency_positions.pop(analysis.deal_reference, None)
                    
                    # Log emergency closure
                    emergency_action = {
                        "timestamp": datetime.utcnow(),
                        "deal_reference": analysis.deal_reference,
                        "action": "EMERGENCY_CLOSE",
                        "reason": reason,
                        "pnl_at_close": analysis.current_pnl,
                        "protection_saved": max(0, self.immediate_loss_threshold - abs(analysis.current_pnl))
                    }
                    self.position_adjustments.append(emergency_action)
                else:
                    print(f"❌ Failed to emergency close {analysis.deal_reference}")
            
        except Exception as e:
            print(f"❌ Error in emergency close: {e}")
    
    def _emergency_tighten_stop_loss(self, position: Dict, analysis: PositionAnalysis):
        """Tighten stop loss in emergency situation"""
        try:
            deal_id = position.get("deal_id")
            if not deal_id:
                return
            
            # Calculate tighter stop loss
            original_stop_pips = config["strategy"]["stop_loss_pips"]
            new_stop_pips = original_stop_pips * self.emergency_stop_multiplier
            
            if analysis.direction == "BUY":
                new_stop_level = analysis.entry_price - new_stop_pips
            else:  # SELL
                new_stop_level = analysis.entry_price + new_stop_pips
            
            print(f"🚨 EMERGENCY STOP TIGHTENING: {analysis.deal_reference}")
            print(f"   Original: {original_stop_pips} pips → New: {new_stop_pips:.1f} pips")
            
            # Update stop loss via IG API
            if self.ig_manager:
                success = self.ig_manager.update_stop_loss_only(deal_id, new_stop_level)
                if success:
                    print(f"✅ Tightened stop loss for {analysis.deal_reference}")
                    
                    # Log emergency adjustment
                    emergency_action = {
                        "timestamp": datetime.utcnow(),
                        "deal_reference": analysis.deal_reference,
                        "action": "EMERGENCY_STOP_TIGHTEN",
                        "old_stop_pips": original_stop_pips,
                        "new_stop_pips": new_stop_pips,
                        "current_pnl": analysis.current_pnl
                    }
                    self.position_adjustments.append(emergency_action)
                    
        except Exception as e:
            print(f"❌ Error tightening emergency stop loss: {e}")
    
    def _create_minimal_analysis(self, deal_reference: str, direction: str, entry_price: float, 
                               current_price: float, size: float) -> Optional[PositionAnalysis]:
        """Create minimal position analysis when insufficient data available"""
        try:
            # Calculate basic P&L
            if direction == "BUY":
                current_pnl = (current_price - entry_price) * size
            else:  # SELL
                current_pnl = (entry_price - current_price) * size
            
            # Use conservative defaults when data is insufficient
            strategy_confidence = 0.5  # Neutral confidence
            market_regime = "neutral"  # Neutral regime
            expected_pnl = config["strategy"]["take_profit_pips"] * size
            
            # Conservative limit multiplier for insufficient data
            if current_pnl < -10:  # Losing significantly
                multiplier = 0.7  # Reduce limits
                reason = "Conservative due to insufficient data + losses"
            elif current_pnl > 5:  # Small profit
                multiplier = 1.0  # Keep current limits
                reason = "Hold current due to insufficient data + small profit"
            else:
                multiplier = 0.8  # Slightly conservative
                reason = "Conservative due to insufficient data"
            
            return PositionAnalysis(
                deal_reference=deal_reference,
                current_pnl=current_pnl,
                entry_price=entry_price,
                current_price=current_price,
                direction=direction,
                size=size,
                expected_pnl=expected_pnl,
                strategy_confidence=strategy_confidence,
                market_regime=market_regime,
                recommended_limit_multiplier=multiplier,
                reason=reason
            )
            
        except Exception as e:
            print(f"❌ Error creating minimal analysis: {e}")
            return None
    
    def get_adjustment_history(self) -> List[Dict]:
        """Get history of position adjustments made"""
        return self.position_adjustments.copy()
    
    def get_status(self) -> Dict:
        """Get current status of dynamic position manager"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "positions_managed": len(self.positions_being_managed),
            "total_adjustments": len(self.position_adjustments),
            "update_interval": self.update_interval,
            "confidence_threshold": self.confidence_threshold,
            "limit_range": f"{self.min_decrease}x - {self.max_increase}x"
        }

# Global instance
_dynamic_position_manager = None

def get_dynamic_position_manager() -> DynamicPositionManager:
    """Get global dynamic position manager instance"""
    global _dynamic_position_manager
    if _dynamic_position_manager is None:
        _dynamic_position_manager = DynamicPositionManager()
    return _dynamic_position_manager

if __name__ == "__main__":
    # Test the dynamic position manager
    print("🧪 Testing Dynamic Position Manager")
    print("=" * 50)
    
    manager = DynamicPositionManager()
    status = manager.get_status()
    
    print(f"Status: {status}")
    
    if manager.enabled:
        print("✅ Dynamic Position Manager is enabled and ready")
        # manager.start()  # Uncomment to actually start
    else:
        print("ℹ️ Dynamic Position Manager is disabled")
        print("   Set dynamic_limits.enabled=true in global.yaml to activate")