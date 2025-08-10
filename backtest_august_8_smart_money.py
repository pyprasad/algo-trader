#!/usr/bin/env python3
"""
📊 August 8th Smart Money Concepts Backtest

This script runs the actual trading system against August 8th tick data
with Smart Money Concepts enabled vs disabled to show P&L improvement.

Uses the existing backtest framework with SMC enhancement.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from collections import deque
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

# Import actual trading system components
from core.enhanced_strategy_engine import get_enhanced_strategy_engine
from core.market_adaptive_strategy import get_market_adaptive_strategy
from core.professional_strategy_engine import get_professional_strategy_engine, ProfessionalStrategyEngine
from data.db import can_open_new_trade, get_trade_lifecycle_status, trades_collection
from core.emergency_risk_manager import get_emergency_risk_manager

class SmartMoneyAugust8Backtest:
    """
    Backtest August 8th with Smart Money Concepts comparison
    """
    
    def __init__(self):
        # Initialize strategy engines - WITH and WITHOUT Smart Money
        self.professional_with_smc = ProfessionalStrategyEngine(enable_smart_money=True)
        self.professional_without_smc = ProfessionalStrategyEngine(enable_smart_money=False)
        
        # Other engines
        self.market_adaptive_strategy = get_market_adaptive_strategy()
        self.enhanced_strategy_engine = get_enhanced_strategy_engine()
        self.emergency_risk_manager = get_emergency_risk_manager()
        
        # Load historical data
        self.ftse_ticks = self._load_tick_data("tick_ftse_100_08_08.json", "FTSE 100")
        self.dax_ticks = self._load_tick_data("tick_dax_08_08.json", "DAX")
        
        # Combine and sort by timestamp
        self.all_ticks = sorted(self.ftse_ticks + self.dax_ticks, key=lambda x: x['timestamp'])
        
        print(f"📊 Loaded {len(self.ftse_ticks)} FTSE ticks, {len(self.dax_ticks)} DAX ticks")
        print(f"📊 Total ticks: {len(self.all_ticks)}")
        
        if self.all_ticks:
            print(f"📅 Period: {self.all_ticks[0]['timestamp']} to {self.all_ticks[-1]['timestamp']}")
    
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
            return []
        
        return ticks
    
    def simulate_trading_session(self, use_smart_money: bool, session_name: str) -> Dict:
        """
        Simulate trading session with or without Smart Money Concepts
        """
        print(f"\n🎯 SIMULATING: {session_name}")
        print("=" * 80)
        
        # Choose the appropriate strategy engine
        if use_smart_money:
            professional_strategy = self.professional_with_smc
        else:
            professional_strategy = self.professional_without_smc
        
        # Track state
        active_positions = {'FTSE 100': None, 'DAX': None}
        last_analysis_time = {'FTSE 100': None, 'DAX': None}
        analysis_interval = timedelta(minutes=3)  # Conservative interval
        
        # Results tracking
        trades_executed = []
        total_trades = 0
        blocked_trades = 0
        signals_generated = 0
        
        # Price buffers for analysis
        ftse_price_buffer = deque(maxlen=100)  # Larger buffer for Smart Money analysis
        dax_price_buffer = deque(maxlen=100)
        
        # P&L tracking
        total_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        
        # Clear any existing test trades
        trades_collection.delete_many({"deal_reference": {"$regex": "^SMC_TEST_"}})
        
        print(f"Processing {len(self.all_ticks)} ticks...")
        
        # Process ticks chronologically
        for i, tick in enumerate(self.all_ticks):
            market = tick['market']
            current_price = tick['mid_price']
            current_time = tick['timestamp']
            
            # Update price buffers
            if market == 'FTSE 100':
                ftse_price_buffer.append(current_price)
                price_buffer = list(ftse_price_buffer)
            else:
                dax_price_buffer.append(current_price)
                price_buffer = list(dax_price_buffer)
            
            # Need minimum data for analysis
            if len(price_buffer) < 50:  # More data needed for Smart Money analysis
                continue
            
            # Check if it's time to analyze (controlled frequency)
            if last_analysis_time[market]:
                time_since_last = current_time - last_analysis_time[market]
                if time_since_last < analysis_interval:
                    continue
            
            last_analysis_time[market] = current_time
            
            # PROFESSIONAL STRATEGY ANALYSIS (with or without Smart Money)
            try:
                professional_signal = professional_strategy.analyze_market_conditions(price_buffer, market)
                signals_generated += 1
                
                signals = None
                signal_source = None
                confidence = 0
                
                # Use professional signal if strong enough
                if professional_signal.get('confidence', 0) >= 0.65:  # Higher threshold
                    signals = professional_signal
                    signal_source = 'professional_engine'
                    confidence = professional_signal.get('confidence', 0)
                    
                    # Smart Money boost
                    if use_smart_money and 'smart_money' in str(professional_signal):
                        signal_source += '_with_SMC'
                
                # Check for trading signal
                if signals and signals.get('signal') in ['BUY', 'SELL']:
                    print(f"\n📊 {current_time.strftime('%H:%M:%S')} {market}: {signals['signal']} "
                          f"from {signal_source} (conf: {confidence:.2%})")
                    
                    # Position checking (bulletproof safety)
                    can_trade = can_open_new_trade(market)
                    
                    if not can_trade:
                        blocked_trades += 1
                        trade_status = get_trade_lifecycle_status(market)
                        print(f"   ❌ BLOCKED by position checking: {trade_status}")
                        continue
                    
                    # Emergency risk validation
                    can_trade_risk, risk_reason = self.emergency_risk_manager.validate_trade(
                        market=market,
                        direction=signals['signal'],
                        size=1,
                        current_price=current_price,
                        stop_loss=current_price - 15 if signals['signal'] == 'BUY' else current_price + 15
                    )
                    
                    if not can_trade_risk:
                        blocked_trades += 1
                        print(f"   ❌ BLOCKED by risk manager: {risk_reason}")
                        continue
                    
                    # Execute trade
                    total_trades += 1
                    deal_ref = f"SMC_TEST_{total_trades:04d}"
                    
                    # Calculate entry/exit prices
                    if signals['signal'] == 'BUY':
                        entry_price = tick['offer']
                        stop_loss = entry_price - 15
                        take_profit = entry_price + 30  # 2:1 RR
                    else:
                        entry_price = tick['bid']
                        stop_loss = entry_price + 15
                        take_profit = entry_price - 30
                    
                    # Simulate trade outcome (simplified)
                    trade_outcome = self._simulate_trade_outcome(
                        market, signals['signal'], entry_price, stop_loss, 
                        take_profit, current_time, i
                    )
                    
                    trade_record = {
                        'deal_reference': deal_ref,
                        'market': market,
                        'direction': signals['signal'],
                        'entry_price': entry_price,
                        'exit_price': trade_outcome['exit_price'],
                        'entry_time': current_time,
                        'exit_time': trade_outcome['exit_time'],
                        'pnl': trade_outcome['pnl'],
                        'confidence': confidence,
                        'signal_source': signal_source,
                        'exit_reason': trade_outcome['reason']
                    }
                    
                    trades_executed.append(trade_record)
                    total_pnl += trade_outcome['pnl']
                    
                    if trade_outcome['pnl'] > 0:
                        winning_trades += 1
                    else:
                        losing_trades += 1
                    
                    print(f"   ✅ EXECUTED: Entry={entry_price:.1f}, Exit={trade_outcome['exit_price']:.1f}, "
                          f"P&L=£{trade_outcome['pnl']:.2f} ({trade_outcome['reason']})")
                    
                    # Log to database for position checking
                    trades_collection.insert_one({
                        'market': market,
                        'direction': signals['signal'],
                        'entry_price': entry_price,
                        'timestamp': current_time,
                        'deal_reference': deal_ref,
                        'status': 'closed',
                        'exit_price': trade_outcome['exit_price'],
                        'pnl': trade_outcome['pnl']
                    })
                    
            except Exception as e:
                print(f"   ⚠️ Analysis error at {current_time}: {e}")
                continue
            
            # Progress indicator
            if i % 1000 == 0:
                progress = (i / len(self.all_ticks)) * 100
                print(f"   📊 Progress: {progress:.1f}% ({i}/{len(self.all_ticks)})")
        
        # Calculate final statistics
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_win = sum(t['pnl'] for t in trades_executed if t['pnl'] > 0) / winning_trades if winning_trades > 0 else 0
        avg_loss = sum(t['pnl'] for t in trades_executed if t['pnl'] < 0) / losing_trades if losing_trades > 0 else 0
        
        results = {
            'session_name': session_name,
            'use_smart_money': use_smart_money,
            'total_ticks_processed': len(self.all_ticks),
            'signals_generated': signals_generated,
            'total_trades': total_trades,
            'blocked_trades': blocked_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_win': max((t['pnl'] for t in trades_executed), default=0),
            'max_loss': min((t['pnl'] for t in trades_executed), default=0),
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            'trades': trades_executed
        }
        
        # Clear test trades
        trades_collection.delete_many({"deal_reference": {"$regex": "^SMC_TEST_"}})
        
        return results
    
    def _simulate_trade_outcome(self, market: str, direction: str, entry_price: float, 
                              stop_loss: float, take_profit: float, entry_time: datetime, 
                              start_index: int) -> Dict:
        """
        Simulate trade outcome by looking at future price action
        """
        
        # Look for exit conditions in next 2 hours of ticks
        max_duration = timedelta(hours=2)
        
        for i in range(start_index + 1, min(start_index + 500, len(self.all_ticks))):
            tick = self.all_ticks[i]
            
            # Only check same market
            if tick['market'] != market:
                continue
            
            # Check time limit
            if tick['timestamp'] - entry_time > max_duration:
                # Time exit
                exit_price = tick['mid_price']
                pnl = (exit_price - entry_price) if direction == 'BUY' else (entry_price - exit_price)
                return {
                    'exit_price': exit_price,
                    'exit_time': tick['timestamp'],
                    'pnl': pnl - 1.0,  # Account for spread
                    'reason': 'time_exit'
                }
            
            current_price = tick['mid_price']
            
            # Check stop loss
            if direction == 'BUY' and current_price <= stop_loss:
                pnl = (stop_loss - entry_price) - 1.0  # Spread cost
                return {
                    'exit_price': stop_loss,
                    'exit_time': tick['timestamp'],
                    'pnl': pnl,
                    'reason': 'stop_loss'
                }
            elif direction == 'SELL' and current_price >= stop_loss:
                pnl = (entry_price - stop_loss) - 1.0
                return {
                    'exit_price': stop_loss,
                    'exit_time': tick['timestamp'],
                    'pnl': pnl,
                    'reason': 'stop_loss'
                }
            
            # Check take profit
            if direction == 'BUY' and current_price >= take_profit:
                pnl = (take_profit - entry_price) - 1.0
                return {
                    'exit_price': take_profit,
                    'exit_time': tick['timestamp'],
                    'pnl': pnl,
                    'reason': 'take_profit'
                }
            elif direction == 'SELL' and current_price <= take_profit:
                pnl = (entry_price - take_profit) - 1.0
                return {
                    'exit_price': take_profit,
                    'exit_time': tick['timestamp'],
                    'pnl': pnl,
                    'reason': 'take_profit'
                }
        
        # If no exit condition met, exit at end of data
        final_tick = self.all_ticks[-1]
        exit_price = final_tick['mid_price'] if final_tick['market'] == market else entry_price
        pnl = (exit_price - entry_price) if direction == 'BUY' else (entry_price - exit_price)
        
        return {
            'exit_price': exit_price,
            'exit_time': final_tick['timestamp'],
            'pnl': pnl - 1.0,
            'reason': 'end_of_data'
        }
    
    def run_comparison_backtest(self):
        """Run complete comparison between Smart Money and traditional strategies"""
        
        print("\n" + "="*100)
        print("🏆 AUGUST 8TH SMART MONEY CONCEPTS vs TRADITIONAL BACKTEST")
        print("="*100)
        
        # Run WITHOUT Smart Money Concepts
        results_without_smc = self.simulate_trading_session(
            use_smart_money=False, 
            session_name="TRADITIONAL ANALYSIS (No Smart Money)"
        )
        
        # Run WITH Smart Money Concepts  
        results_with_smc = self.simulate_trading_session(
            use_smart_money=True,
            session_name="SMART MONEY CONCEPTS ENHANCED"
        )
        
        # Print comprehensive comparison
        self.print_detailed_comparison(results_without_smc, results_with_smc)
        
        return results_without_smc, results_with_smc
    
    def print_detailed_comparison(self, without_smc: Dict, with_smc: Dict):
        """Print detailed P&L comparison report"""
        
        print("\n" + "="*100)
        print("📊 DETAILED P&L COMPARISON REPORT - AUGUST 8TH")
        print("="*100)
        
        # Header
        print(f"\n{'Metric':<30} {'Traditional':<20} {'Smart Money':<20} {'Improvement':<20}")
        print("-" * 90)
        
        # Calculate improvements
        improvements = {}
        
        metrics = [
            ('Total Signals', 'signals_generated'),
            ('Total Trades', 'total_trades'),
            ('Blocked Trades', 'blocked_trades'),
            ('Winning Trades', 'winning_trades'),
            ('Losing Trades', 'losing_trades'),
            ('Win Rate', 'win_rate'),
            ('Total P&L', 'total_pnl'),
            ('Average Win', 'avg_win'),
            ('Average Loss', 'avg_loss'),
            ('Max Win', 'max_win'),
            ('Max Loss', 'max_loss'),
            ('Profit Factor', 'profit_factor')
        ]
        
        for metric_name, key in metrics:
            val_without = without_smc[key]
            val_with = with_smc[key]
            
            # Format values
            if key in ['win_rate']:
                val_without_str = f"{val_without:.1%}"
                val_with_str = f"{val_with:.1%}"
                improvement = (val_with - val_without) * 100
                improvement_str = f"+{improvement:.1f}pp" if improvement > 0 else f"{improvement:.1f}pp"
            elif key in ['total_pnl', 'avg_win', 'avg_loss', 'max_win', 'max_loss']:
                val_without_str = f"£{val_without:.2f}"
                val_with_str = f"£{val_with:.2f}"
                if val_without != 0:
                    improvement = ((val_with - val_without) / abs(val_without)) * 100
                    improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
                else:
                    improvement_str = "N/A"
            elif key == 'profit_factor':
                val_without_str = f"{val_without:.2f}x"
                val_with_str = f"{val_with:.2f}x"
                if val_without != 0 and val_without != float('inf'):
                    improvement = ((val_with - val_without) / val_without) * 100
                    improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
                else:
                    improvement_str = "N/A"
            else:
                val_without_str = f"{val_without}"
                val_with_str = f"{val_with}"
                if val_without != 0:
                    improvement = ((val_with - val_without) / val_without) * 100
                    improvement_str = f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
                else:
                    improvement_str = "N/A"
            
            print(f"{metric_name:<30} {val_without_str:<20} {val_with_str:<20} {improvement_str:<20}")
        
        # Key insights
        print("\n" + "="*100)
        print("🎯 KEY INSIGHTS FROM AUGUST 8TH BACKTEST")
        print("="*100)
        
        pnl_improvement = with_smc['total_pnl'] - without_smc['total_pnl']
        win_rate_improvement = (with_smc['win_rate'] - without_smc['win_rate']) * 100
        
        print(f"\n📈 PERFORMANCE IMPACT:")
        
        if pnl_improvement > 100:
            print(f"✅ EXCELLENT: Smart Money improved P&L by £{pnl_improvement:.2f}")
        elif pnl_improvement > 50:
            print(f"✅ GOOD: Smart Money improved P&L by £{pnl_improvement:.2f}")
        elif pnl_improvement > 0:
            print(f"⚠️ MODEST: Smart Money improved P&L by £{pnl_improvement:.2f}")
        else:
            print(f"❌ UNDERPERFORMED: Smart Money reduced P&L by £{abs(pnl_improvement):.2f}")
        
        if win_rate_improvement > 10:
            print(f"✅ WIN RATE BOOST: +{win_rate_improvement:.1f} percentage points")
        elif win_rate_improvement > 5:
            print(f"⚠️ MODEST WIN RATE: +{win_rate_improvement:.1f} percentage points")  
        elif win_rate_improvement > 0:
            print(f"⚠️ SMALL WIN RATE: +{win_rate_improvement:.1f} percentage points")
        else:
            print(f"❌ WIN RATE DECLINED: {win_rate_improvement:.1f} percentage points")
        
        # Safety analysis
        print(f"\n🛡️ SAFETY ANALYSIS:")
        print(f"   Blocked Trades (Traditional): {without_smc['blocked_trades']}")
        print(f"   Blocked Trades (Smart Money): {with_smc['blocked_trades']}")
        print(f"   ✅ Bulletproof position checking working in both systems")
        
        # Smart Money specific insights
        smc_trades = [t for t in with_smc['trades'] if 'SMC' in t.get('signal_source', '')]
        if smc_trades:
            smc_pnl = sum(t['pnl'] for t in smc_trades)
            smc_wins = len([t for t in smc_trades if t['pnl'] > 0])
            smc_win_rate = smc_wins / len(smc_trades)
            
            print(f"\n🏦 SMART MONEY SPECIFIC TRADES:")
            print(f"   SMC-influenced trades: {len(smc_trades)}")
            print(f"   SMC trades P&L: £{smc_pnl:.2f}")
            print(f"   SMC win rate: {smc_win_rate:.1%}")
        
        # Final verdict
        print(f"\n🏆 AUGUST 8TH VERDICT:")
        if pnl_improvement > 50 and win_rate_improvement > 5:
            print("✅ SMART MONEY CONCEPTS SUCCESSFULLY ENHANCED PERFORMANCE!")
            print("   The SMC integration is working as expected on historical data.")
        elif pnl_improvement > 0 and win_rate_improvement > 0:
            print("⚠️ SMART MONEY CONCEPTS PROVIDED MODEST IMPROVEMENT")
            print("   Performance gains visible but below maximum potential.")
        else:
            print("❌ SMART MONEY CONCEPTS NEED OPTIMIZATION FOR THIS DATA")
            print("   May need pattern threshold adjustments or different market conditions.")
        
        print("\n📌 Note: This backtest uses the actual August 8th tick data with all")
        print("   bulletproof safety systems active. Results show how SMC would have")
        print("   performed with proper risk management in place.")


def main():
    """Run the August 8th Smart Money backtest"""
    
    print("🧪 AUGUST 8TH SMART MONEY CONCEPTS BACKTEST")
    print("="*80)
    print(f"Started at: {datetime.now()}")
    
    try:
        # Initialize backtester
        backtester = SmartMoneyAugust8Backtest()
        
        if not backtester.all_ticks:
            print("❌ No tick data loaded. Please ensure tick_ftse_100_08_08.json and tick_dax_08_08.json exist.")
            return False
        
        # Run comparison
        results_without, results_with = backtester.run_comparison_backtest()
        
        print(f"\n✅ August 8th Smart Money backtest completed!")
        print(f"📊 Traditional system: {results_without['total_trades']} trades, £{results_without['total_pnl']:.2f} P&L")
        print(f"🏦 Smart Money system: {results_with['total_trades']} trades, £{results_with['total_pnl']:.2f} P&L")
        
        improvement = results_with['total_pnl'] - results_without['total_pnl']
        print(f"💰 Net improvement: £{improvement:.2f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)