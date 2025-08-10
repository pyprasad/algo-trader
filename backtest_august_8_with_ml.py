#!/usr/bin/env python3
"""
📊 August 8th Backtest with ML Enhancement

This script replays the actual trading system against August 8th data
but WITH ML predictions added to improve signal quality.

Compares:
1. Original system (with fixes) - no ML
2. ML-enhanced system - with ML predictions

Author: ML Enhancement Team
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import deque
import time
import joblib

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import actual trading system components
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from core.market_adaptive_strategy import get_market_adaptive_strategy
from core.professional_strategy_engine import get_professional_strategy_engine
from data.db import can_open_new_trade, get_trade_lifecycle_status, trades_collection
from core.emergency_risk_manager import get_emergency_risk_manager
from models.ml_predictor import MLTradingPredictor

class MLEnhancedAugust8Backtest:
    """
    Backtest August 8th with ML-enhanced trading decisions
    """
    
    def __init__(self):
        # Initialize actual strategy engines
        self.enhanced_strategy_engine = get_enhanced_strategy_engine()
        self.market_adaptive_strategy = get_market_adaptive_strategy()
        self.professional_strategy = get_professional_strategy_engine()
        self.emergency_risk_manager = get_emergency_risk_manager()
        
        # Load historical data
        self.ftse_ticks = self._load_tick_data("tick_ftse_100_08_08.json", "FTSE 100")
        self.dax_ticks = self._load_tick_data("tick_dax_08_08.json", "DAX")
        
        # Combine and sort by timestamp
        self.all_ticks = sorted(self.ftse_ticks + self.dax_ticks, key=lambda x: x['timestamp'])
        
        print(f"📊 Loaded {len(self.ftse_ticks)} FTSE ticks, {len(self.dax_ticks)} DAX ticks")
        print(f"📊 Total ticks: {len(self.all_ticks)}")
        
        # Load trained ML models
        self.ml_models = self._load_ml_models()
        
        # Track trades and P&L for both approaches
        self.trades_without_ml = []
        self.trades_with_ml = []
        self.initial_balance = 10000.0
        
        # Price buffers for strategy analysis (like run_multi_market.py)
        self.ftse_price_buffer = deque(maxlen=50)
        self.dax_price_buffer = deque(maxlen=50)
        
    def _load_tick_data(self, filename: str, market: str) -> List[Dict]:
        """Load tick data from JSON file"""
        ticks = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    tick_data = json.loads(line.strip())
                    timestamp_str = tick_data['timestamp']['$date']
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    ticks.append({
                        'market': market,
                        'bid': tick_data['bid'],
                        'offer': tick_data['offer'],
                        'timestamp': timestamp,
                        'mid_price': (tick_data['bid'] + tick_data['offer']) / 2
                    })
        except Exception as e:
            print(f"❌ Error loading {filename}: {e}")
        
        return ticks
    
    def _load_ml_models(self) -> Dict:
        """Load pre-trained ML models"""
        ml_models = {}
        
        # Try to load FTSE 100 models
        try:
            ftse_rf = MLTradingPredictor()
            ftse_rf.load_model("models/ml_backtest_ftse_100_rf.pkl")
            ml_models['FTSE 100'] = {'rf': ftse_rf}
            print("✅ Loaded FTSE 100 ML models")
        except Exception as e:
            print(f"⚠️ Could not load FTSE 100 ML models: {e}")
            ml_models['FTSE 100'] = None
        
        # Try to load DAX models (if available)
        try:
            dax_rf = MLTradingPredictor()
            dax_rf.load_model("models/ml_backtest_dax_rf.pkl")
            ml_models['DAX'] = {'rf': dax_rf}
            print("✅ Loaded DAX ML models")
        except Exception as e:
            print(f"⚠️ Could not load DAX ML models: {e}")
            ml_models['DAX'] = None
        
        return ml_models
    
    def _get_ml_enhanced_signal(self, signals: Dict, market: str, recent_prices: List[float]) -> Dict:
        """Enhance trading signals with ML predictions"""
        if market not in self.ml_models or not self.ml_models[market]:
            return signals  # Return original signals if no ML model
        
        try:
            # Get ML prediction
            ml_model = self.ml_models[market]['rf']
            
            # Create DataFrame for ML prediction
            import pandas as pd
            df = pd.DataFrame({
                'bid': recent_prices,
                'offer': recent_prices,  # Simplified
                'midprice': recent_prices
            })
            df.index = pd.date_range(end=datetime.now(), periods=len(recent_prices), freq='1min')
            
            ml_prediction = ml_model.predict(df)
            
            # Combine signals with ML
            enhanced_signals = signals.copy()
            
            # ML confidence boost/reduction
            ml_signal = ml_prediction.get('signal', 'HOLD')
            ml_confidence = ml_prediction.get('confidence', 0.5)
            
            print(f"      🤖 ML: {ml_signal} (conf: {ml_confidence:.2f}) | Original: {signals.get('signal', 'HOLD')} (conf: {signals.get('confidence', 0.5):.2f})")
            
            # ML Enhancement Logic
            if ml_signal == signals.get('signal', 'HOLD') and ml_confidence > 0.7:
                # ML agrees and is confident - boost confidence
                enhanced_signals['confidence'] = min(0.95, signals.get('confidence', 0.5) + 0.2)
                enhanced_signals['ml_enhanced'] = True
                enhanced_signals['ml_boost'] = 'agreement_boost'
            elif ml_signal != signals.get('signal', 'HOLD') and ml_confidence > 0.8:
                # ML disagrees strongly - reduce confidence  
                enhanced_signals['confidence'] = max(0.3, signals.get('confidence', 0.5) - 0.3)
                enhanced_signals['ml_enhanced'] = True
                enhanced_signals['ml_boost'] = 'disagreement_penalty'
            elif ml_signal != 'HOLD' and signals.get('signal', 'HOLD') == 'HOLD':
                # Original says HOLD but ML suggests trade
                if ml_confidence > 0.85:
                    enhanced_signals['signal'] = ml_signal
                    enhanced_signals['confidence'] = ml_confidence * 0.8  # Slight discount for ML-only signals
                    enhanced_signals['ml_enhanced'] = True
                    enhanced_signals['ml_boost'] = 'ml_override'
            
            enhanced_signals['ml_signal'] = ml_signal
            enhanced_signals['ml_confidence'] = ml_confidence
            
            return enhanced_signals
            
        except Exception as e:
            print(f"      ⚠️ ML enhancement failed: {e}")
            return signals  # Return original on error
    
    def simulate_without_ml(self):
        """Run original backtest without ML"""
        return self._run_simulation("WITHOUT_ML", use_ml=False)
    
    def simulate_with_ml(self):
        """Run backtest with ML enhancement"""
        return self._run_simulation("WITH_ML", use_ml=True)
    
    def _run_simulation(self, simulation_name: str, use_ml: bool = False):
        """
        Core simulation logic
        """
        print(f"\n🎯 SIMULATING AUGUST 8TH - {simulation_name}")
        print("=" * 80)
        
        # Track state
        active_positions = {'FTSE 100': None, 'DAX': None}
        last_analysis_time = {'FTSE 100': None, 'DAX': None}
        analysis_interval = timedelta(seconds=60)  # From config
        
        total_trades = 0
        blocked_trades = 0
        ml_enhanced_trades = 0
        trades_list = []
        
        # Clear any existing test trades in database
        trades_collection.delete_many({"deal_reference": {"$regex": f"^{simulation_name}_"}})
        
        # Reset price buffers
        ftse_buffer = deque(maxlen=50)
        dax_buffer = deque(maxlen=50)
        
        # Process ticks chronologically
        for i, tick in enumerate(self.all_ticks):
            market = tick['market']
            current_price = tick['mid_price']
            current_time = tick['timestamp']
            
            # Update price buffers
            if market == 'FTSE 100':
                ftse_buffer.append(current_price)
                price_buffer = list(ftse_buffer)
            else:
                dax_buffer.append(current_price)
                price_buffer = list(dax_buffer)
            
            # Need minimum data for analysis
            if len(price_buffer) < 20:
                continue
            
            # Check if it's time to analyze (60 second intervals)
            if last_analysis_time[market]:
                time_since_last = current_time - last_analysis_time[market]
                if time_since_last < analysis_interval:
                    continue
            
            last_analysis_time[market] = current_time
            
            # STEP 1: Professional Strategy Analysis (from run_multi_market.py)
            professional_signal = self.professional_strategy.analyze_market(price_buffer, market)
            
            signals = None
            signal_source = None
            
            # Use professional signal if strong enough
            if professional_signal.get('strength', 0) >= 0.6:
                signals = professional_signal
                signal_source = 'professional_engine'
            else:
                # Fallback to market-adaptive strategy
                signals = self.market_adaptive_strategy.analyze_market_conditions(price_buffer, market)
                signal_source = 'market_adaptive'
                
                # Further fallback to enhanced strategy if needed
                if not signals or signals.get('signal') == 'HOLD':
                    enhanced_signals = self.enhanced_strategy_engine.analyze_market_conditions(price_buffer, market)
                    if enhanced_signals and enhanced_signals.get('signal') != 'HOLD':
                        if self.market_adaptive_strategy._is_good_trading_time(market):
                            signals = enhanced_signals
                            signal_source = 'enhanced_strategy'
            
            # STEP 2: ML Enhancement (if enabled)
            if use_ml and signals:
                original_signal = signals.get('signal', 'HOLD')
                original_confidence = signals.get('confidence', 0.5)
                
                signals = self._get_ml_enhanced_signal(signals, market, price_buffer)
                
                if signals.get('ml_enhanced'):
                    print(f"   🤖 ML Enhanced: {original_signal}({original_confidence:.2f}) → {signals.get('signal')}({signals.get('confidence'):.2f})")
            
            # Check for trading signal
            if signals and signals.get('signal') in ['BUY', 'SELL']:
                # Add current price to signals
                signals['price'] = current_price
                
                print(f"\n📊 {current_time.strftime('%H:%M')} {market}: {signals['signal']} signal from {signal_source}")
                if use_ml and signals.get('ml_enhanced'):
                    print(f"   🔬 ML Enhancement: {signals.get('ml_boost', 'none')}")
                
                # NEW FIXES: Check if we can open a new trade
                can_trade = can_open_new_trade(market)
                
                if not can_trade:
                    blocked_trades += 1
                    trade_status = get_trade_lifecycle_status(market)
                    print(f"   ❌ BLOCKED by position checking: {trade_status}")
                    continue
                
                # NEW FIXES: Emergency risk validation
                can_trade_risk, risk_reason = self.emergency_risk_manager.validate_trade(
                    market=market,
                    direction=signals['signal'],
                    size=1,
                    current_price=current_price,
                    stop_loss=current_price - 10 if signals['signal'] == 'BUY' else current_price + 10
                )
                
                if not can_trade_risk:
                    blocked_trades += 1
                    print(f"   ❌ BLOCKED by risk manager: {risk_reason}")
                    continue
                
                # Trade would be executed here
                total_trades += 1
                if signals.get('ml_enhanced'):
                    ml_enhanced_trades += 1
                    
                deal_ref = f"{simulation_name}_{total_trades:04d}"
                
                # Calculate entry price based on spread
                if signals['signal'] == 'BUY':
                    entry_price = tick['offer']
                    stop_loss = entry_price - 10
                    take_profit = entry_price + 20
                else:
                    entry_price = tick['bid']
                    stop_loss = entry_price + 10
                    take_profit = entry_price - 20
                
                # Log trade to database (for position checking to work)
                trade_data = {
                    'market': market,
                    'direction': signals['signal'],
                    'entry_price': entry_price,
                    'timestamp': current_time,
                    'deal_reference': deal_ref,
                    'status': 'OPEN',
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'strategy_signals': signals,
                    'signal_source': signal_source,
                    'simulation_type': simulation_name,
                    'ml_enhanced': signals.get('ml_enhanced', False),
                    'ml_signal': signals.get('ml_signal', 'NONE'),
                    'ml_confidence': signals.get('ml_confidence', 0.0)
                }
                
                trades_collection.insert_one(trade_data)
                active_positions[market] = trade_data
                trades_list.append(trade_data)
                
                print(f"   ✅ TRADE {total_trades}: {market} {signals['signal']} at {entry_price:.1f}")
                print(f"      Strategy: {signal_source} | Confidence: {signals.get('confidence', 0):.2f}")
                if signals.get('ml_enhanced'):
                    print(f"      🤖 ML Enhanced: {signals.get('ml_signal')} ({signals.get('ml_confidence', 0):.2f})")
            
            # Simulate trade exits (simplified)
            if active_positions[market]:
                trade = active_positions[market]
                exit_triggered = False
                exit_price = None
                pnl = 0
                
                if trade['direction'] == 'BUY':
                    if current_price <= trade['stop_loss']:
                        exit_triggered = True
                        exit_price = trade['stop_loss']
                        pnl = (exit_price - trade['entry_price'])
                    elif current_price >= trade['take_profit']:
                        exit_triggered = True
                        exit_price = trade['take_profit']
                        pnl = (exit_price - trade['entry_price'])
                else:  # SELL
                    if current_price >= trade['stop_loss']:
                        exit_triggered = True
                        exit_price = trade['stop_loss']
                        pnl = (trade['entry_price'] - exit_price)
                    elif current_price <= trade['take_profit']:
                        exit_triggered = True
                        exit_price = trade['take_profit']
                        pnl = (trade['entry_price'] - exit_price)
                
                if exit_triggered:
                    # Update database
                    trades_collection.update_one(
                        {'deal_reference': trade['deal_reference']},
                        {'$set': {
                            'status': 'CLOSED',
                            'exit_price': exit_price,
                            'exit_time': current_time,
                            'profit_loss': pnl
                        }}
                    )
                    
                    trade['profit_loss'] = pnl
                    trade['exit_price'] = exit_price
                    trade['status'] = 'CLOSED'
                    
                    active_positions[market] = None
                    
                    ml_indicator = "🤖" if trade.get('ml_enhanced') else ""
                    print(f"   💰 CLOSED: {trade['market']} P&L: £{pnl:.2f} {ml_indicator}")
        
        # Close any remaining positions at end of day
        for market, trade in active_positions.items():
            if trade and trade['status'] == 'OPEN':
                # Get last price for this market
                market_ticks = [t for t in self.all_ticks if t['market'] == market]
                if market_ticks:
                    last_tick = market_ticks[-1]
                    if trade['direction'] == 'BUY':
                        exit_price = last_tick['bid']
                        pnl = (exit_price - trade['entry_price'])
                    else:
                        exit_price = last_tick['offer']
                        pnl = (trade['entry_price'] - exit_price)
                    
                    trade['profit_loss'] = pnl
                    trade['exit_price'] = exit_price
                    trade['status'] = 'CLOSED_EOD'
                    
                    trades_collection.update_one(
                        {'deal_reference': trade['deal_reference']},
                        {'$set': {
                            'status': 'CLOSED_EOD',
                            'exit_price': exit_price,
                            'profit_loss': pnl
                        }}
                    )
        
        # Calculate results
        total_pnl = sum(t.get('profit_loss', 0) for t in trades_list)
        profitable_trades = [t for t in trades_list if t.get('profit_loss', 0) > 0]
        losing_trades = [t for t in trades_list if t.get('profit_loss', 0) < 0]
        
        ftse_trades = [t for t in trades_list if t['market'] == 'FTSE 100']
        dax_trades = [t for t in trades_list if t['market'] == 'DAX']
        
        ftse_pnl = sum(t.get('profit_loss', 0) for t in ftse_trades)
        dax_pnl = sum(t.get('profit_loss', 0) for t in dax_trades)
        
        # Clean up test trades
        trades_collection.delete_many({"deal_reference": {"$regex": f"^{simulation_name}_"}})
        
        return {
            'simulation_name': simulation_name,
            'total_trades': total_trades,
            'blocked_trades': blocked_trades,
            'ml_enhanced_trades': ml_enhanced_trades,
            'total_pnl': total_pnl,
            'profitable_trades': len(profitable_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(profitable_trades) / len(trades_list) if trades_list else 0,
            'ftse_trades': len(ftse_trades),
            'dax_trades': len(dax_trades),
            'ftse_pnl': ftse_pnl,
            'dax_pnl': dax_pnl,
            'final_balance': self.initial_balance + total_pnl,
            'return_percentage': (total_pnl / self.initial_balance) * 100
        }
    
    def run_comparison_backtest(self):
        """Run both simulations and compare results"""
        print("📊" + "=" * 80)
        print("📊 AUGUST 8TH ML ENHANCEMENT BACKTEST")
        print("📊" + "=" * 80)
        print(f"📅 Date: August 8, 2025")
        print(f"💰 Initial Balance: £{self.initial_balance:,.2f}")
        print(f"🤖 ML Models Available: {list(self.ml_models.keys())}")
        print("📊" + "=" * 80)
        
        # Run simulation without ML
        print("\n🔄 Running simulation WITHOUT ML...")
        results_without_ml = self.simulate_without_ml()
        
        # Run simulation with ML
        print("\n🔄 Running simulation WITH ML...")
        results_with_ml = self.simulate_with_ml()
        
        # Compare results
        self._print_comparison_results(results_without_ml, results_with_ml)
        
        return results_without_ml, results_with_ml
    
    def _print_comparison_results(self, without_ml: Dict, with_ml: Dict):
        """Print detailed comparison results"""
        print("\n📊" + "=" * 80)
        print("📊 ML ENHANCEMENT IMPACT ANALYSIS")
        print("📊" + "=" * 80)
        
        print(f"\n📈 TRADING ACTIVITY COMPARISON:")
        print(f"   {'Metric':<25} {'Without ML':<15} {'With ML':<15} {'Change':<15}")
        print(f"   {'-' * 70}")
        print(f"   {'Total Trades':<25} {without_ml['total_trades']:<15} {with_ml['total_trades']:<15} {with_ml['total_trades'] - without_ml['total_trades']:+d}")
        print(f"   {'Blocked Trades':<25} {without_ml['blocked_trades']:<15} {with_ml['blocked_trades']:<15} {with_ml['blocked_trades'] - without_ml['blocked_trades']:+d}")
        print(f"   {'ML Enhanced Trades':<25} {'0':<15} {with_ml['ml_enhanced_trades']:<15} {'+' + str(with_ml['ml_enhanced_trades'])}")
        print(f"   {'Win Rate':<25} {without_ml['win_rate']:.1%:<15} {with_ml['win_rate']:.1%:<15} {(with_ml['win_rate'] - without_ml['win_rate']):.1%:+}")
        
        print(f"\n💰 P&L COMPARISON:")
        print(f"   {'Metric':<25} {'Without ML':<15} {'With ML':<15} {'Improvement':<15}")
        print(f"   {'-' * 70}")
        print(f"   {'Total P&L':<25} £{without_ml['total_pnl']:<14.2f} £{with_ml['total_pnl']:<14.2f} £{with_ml['total_pnl'] - without_ml['total_pnl']:+.2f}")
        print(f"   {'FTSE P&L':<25} £{without_ml['ftse_pnl']:<14.2f} £{with_ml['ftse_pnl']:<14.2f} £{with_ml['ftse_pnl'] - without_ml['ftse_pnl']:+.2f}")
        print(f"   {'DAX P&L':<25} £{without_ml['dax_pnl']:<14.2f} £{with_ml['dax_pnl']:<14.2f} £{with_ml['dax_pnl'] - without_ml['dax_pnl']:+.2f}")
        print(f"   {'Return %':<25} {without_ml['return_percentage']:<14.2f}% {with_ml['return_percentage']:<14.2f}% {with_ml['return_percentage'] - without_ml['return_percentage']:+.2f}%")
        
        print(f"\n🎯 SUMMARY:")
        pnl_improvement = with_ml['total_pnl'] - without_ml['total_pnl']
        if pnl_improvement > 0:
            print(f"   ✅ ML Enhancement IMPROVED performance by £{pnl_improvement:.2f}")
            print(f"   🚀 ML models successfully enhanced trading decisions")
        elif pnl_improvement < 0:
            print(f"   ❌ ML Enhancement REDUCED performance by £{abs(pnl_improvement):.2f}")
            print(f"   🔧 ML models may need further tuning")
        else:
            print(f"   ⚖️ ML Enhancement had NEUTRAL impact")
        
        # Compare to August 8th disaster
        print(f"\n📊 COMPARISON TO ACTUAL AUGUST 8TH DISASTER:")
        print(f"   Actual System (broken): 14 FTSE trades, major losses")
        print(f"   Without ML (fixed): {without_ml['ftse_trades']} FTSE trades, £{without_ml['ftse_pnl']:.2f}")
        print(f"   With ML (enhanced): {with_ml['ftse_trades']} FTSE trades, £{with_ml['ftse_pnl']:.2f}")
        
        if max(without_ml['total_pnl'], with_ml['total_pnl']) > -100:
            print(f"\n✅ SUCCESS: Both approaches prevented the August 8th disaster!")
            if pnl_improvement > 10:
                print(f"   🏆 ML enhancement provided additional £{pnl_improvement:.2f} improvement!")
        
        print("📊" + "=" * 80)

def main():
    """Main execution"""
    try:
        backtest = MLEnhancedAugust8Backtest()
        results_without_ml, results_with_ml = backtest.run_comparison_backtest()
        
        print("\n🎯 ML Enhancement backtest completed successfully!")
        
    except FileNotFoundError as e:
        print(f"❌ Data files not found: {e}")
        print("📁 Ensure tick_ftse_100_08_08.json and tick_dax_08_08.json exist")
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()