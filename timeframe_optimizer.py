#!/usr/bin/env python3.12
# timeframe_optimizer.py - Test all timeframes to find optimal performance

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse

sys.path.append('.')
from core.candle_aggregator import CandleAggregator
from core.enhanced_strategies import EnhancedTradingStrategies

class TimeframeOptimizer:
    """Analyze tick data across multiple timeframes to find optimal trading periods"""
    
    def __init__(self):
        self.aggregator = CandleAggregator()
        self.strategies = EnhancedTradingStrategies()
        
        # Define timeframes to test (pandas frequency strings)
        self.timeframes = {
            '1min': '1T',
            '2min': '2T', 
            '5min': '5T',
            '10min': '10T',
            '15min': '15T',
            '30min': '30T',
            '1hour': '1H',
            '2hour': '2H',
            '4hour': '4H'
        }
        
        # Strategies to test
        self.strategies_config = {
            'ma_crossover_fast': {
                'fast_ma': 5,
                'slow_ma': 15,
                'stop_loss_pips': 20,
                'take_profit_pips': 40
            },
            'ma_crossover_medium': {
                'fast_ma': 8,
                'slow_ma': 21,
                'stop_loss_pips': 25,
                'take_profit_pips': 50
            },
            'ma_crossover_slow': {
                'fast_ma': 12,
                'slow_ma': 34,
                'stop_loss_pips': 30,
                'take_profit_pips': 60
            }
        }
    
    def load_tick_data(self, data_file, max_ticks=200000):
        """Load and analyze tick data structure"""
        print(f"📊 LOADING TICK DATA: {data_file}")
        print("="*60)
        
        ticks = []
        try:
            with open(data_file, 'r') as f:
                for i, line in enumerate(f):
                    if i > max_ticks:
                        break
                    if line.strip():
                        tick = json.loads(line.strip())
                        if 'timestamp' in tick and '$date' in tick['timestamp']:
                            tick['timestamp'] = datetime.fromisoformat(
                                tick['timestamp']['$date'].replace('Z', '+00:00')
                            )
                        ticks.append(tick)
            
            if not ticks:
                print("❌ No data loaded")
                return None
                
            tick_df = pd.DataFrame(ticks).sort_values('timestamp')
            
            # Analyze data structure
            start_time = tick_df['timestamp'].min()
            end_time = tick_df['timestamp'].max()
            duration = end_time - start_time
            
            print(f"📈 Data Analysis:")
            print(f"   Total Ticks: {len(tick_df):,}")
            print(f"   Date Range: {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Duration: {duration}")
            print(f"   Avg Ticks/Hour: {len(tick_df) / (duration.total_seconds() / 3600):.0f}")
            
            # Price analysis
            if 'midprice' not in tick_df.columns and 'bid' in tick_df.columns and 'offer' in tick_df.columns:
                tick_df['midprice'] = (tick_df['bid'] + tick_df['offer']) / 2
            
            price_range = tick_df['midprice'].max() - tick_df['midprice'].min()
            print(f"   Price Range: £{tick_df['midprice'].min():.1f} - £{tick_df['midprice'].max():.1f} (Range: £{price_range:.1f})")
            
            return tick_df
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return None
    
    def test_timeframe_strategy(self, tick_df, timeframe_name, timeframe_code, strategy_name, strategy_params):
        """Test a specific timeframe and strategy combination"""
        
        try:
            # Create candles for this timeframe
            candles = self.aggregator.ticks_to_candles(tick_df, timeframe_code)
            if len(candles) < 50:  # Need minimum candles for strategy
                return None
            
            candles = self.aggregator.add_volatility_filter(candles)
            
            # Apply strategy
            if strategy_name.startswith('ma_crossover'):
                strategy_df = self.strategies.ma_crossover_strategy(candles, strategy_params)
            else:
                return None  # Unknown strategy
            
            # Run simulation
            balance = 10000.0
            position = None
            trades = []
            
            for i, (_, candle) in enumerate(strategy_df.iterrows()):
                
                # Check exits first
                if position:
                    exit_triggered = False
                    exit_price = None
                    exit_reason = None
                    
                    if position['direction'] == 'BUY':
                        if candle['low'] <= position['stop_loss']:
                            exit_triggered = True
                            exit_price = position['stop_loss']
                            exit_reason = 'STOP_LOSS'
                        elif candle['high'] >= position['take_profit']:
                            exit_triggered = True
                            exit_price = position['take_profit']
                            exit_reason = 'TAKE_PROFIT'
                    else:  # SELL
                        if candle['high'] >= position['stop_loss']:
                            exit_triggered = True
                            exit_price = position['stop_loss']
                            exit_reason = 'STOP_LOSS'
                        elif candle['low'] <= position['take_profit']:
                            exit_triggered = True
                            exit_price = position['take_profit']
                            exit_reason = 'TAKE_PROFIT'
                    
                    if exit_triggered:
                        # Calculate P&L (CORRECTED version)
                        position_value = balance * 0.005  # 0.5% position size
                        
                        if position['direction'] == 'BUY':
                            price_change = exit_price - position['entry_price']
                        else:
                            price_change = position['entry_price'] - exit_price
                        
                        pnl = (price_change / position['entry_price']) * position_value - 2.0
                        balance += pnl
                        
                        trades.append({
                            'direction': position['direction'],
                            'entry_price': position['entry_price'],
                            'exit_price': exit_price,
                            'pnl': pnl,
                            'exit_reason': exit_reason
                        })
                        
                        position = None
                
                # Check for new entries
                if not position and candle['signal'] in ['BUY', 'SELL'] and len(trades) < 20:  # Limit trades for comparison
                    
                    # Basic filters
                    atr = candle.get('atr', 0)
                    spread = candle.get('spread', 0)
                    
                    if atr > 3.0 and spread < 8.0:  # Reasonable trading conditions
                        
                        if candle['signal'] == 'BUY':
                            entry_price = candle.get('offer_close', candle['close'])
                            stop_loss = entry_price - strategy_params['stop_loss_pips']
                            take_profit = entry_price + strategy_params['take_profit_pips']
                        else:  # SELL
                            entry_price = candle.get('bid_close', candle['close'])
                            stop_loss = entry_price + strategy_params['stop_loss_pips']
                            take_profit = entry_price - strategy_params['take_profit_pips']
                        
                        position = {
                            'direction': candle['signal'],
                            'entry_price': entry_price,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit
                        }
            
            # Close final position
            if position:
                exit_price = strategy_df.iloc[-1]['close']
                position_value = balance * 0.005
                
                if position['direction'] == 'BUY':
                    price_change = exit_price - position['entry_price']
                else:
                    price_change = position['entry_price'] - exit_price
                
                pnl = (price_change / position['entry_price']) * position_value - 2.0
                balance += pnl
                
                trades.append({
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': 'END_OF_DATA'
                })
            
            # Calculate performance metrics
            if trades:
                total_pnl = sum(t['pnl'] for t in trades)
                wins = [t for t in trades if t['pnl'] > 0]
                losses = [t for t in trades if t['pnl'] <= 0]
                
                win_rate = len(wins) / len(trades) * 100 if trades else 0
                avg_win = sum(w['pnl'] for w in wins) / len(wins) if wins else 0
                avg_loss = sum(l['pnl'] for l in losses) / len(losses) if losses else 0
                profit_factor = abs(sum(w['pnl'] for w in wins) / sum(l['pnl'] for l in losses)) if losses else float('inf')
                
                return {
                    'timeframe': timeframe_name,
                    'strategy': strategy_name,
                    'candles': len(candles),
                    'trades': len(trades),
                    'total_pnl': total_pnl,
                    'final_balance': balance,
                    'return_pct': (balance - 10000) / 10000 * 100,
                    'win_rate': win_rate,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'profit_factor': profit_factor,
                    'trade_details': trades[:5]  # First 5 trades for analysis
                }
            else:
                return {
                    'timeframe': timeframe_name,
                    'strategy': strategy_name,
                    'candles': len(candles),
                    'trades': 0,
                    'total_pnl': 0,
                    'final_balance': 10000,
                    'return_pct': 0,
                    'win_rate': 0,
                    'avg_win': 0,
                    'avg_loss': 0,
                    'profit_factor': 0,
                    'trade_details': []
                }
                
        except Exception as e:
            print(f"❌ Error testing {timeframe_name} {strategy_name}: {e}")
            return None
    
    def optimize_timeframes(self, data_file):
        """Test all timeframe and strategy combinations to find optimal setup"""
        
        print(f"🔍 TIMEFRAME OPTIMIZATION ANALYSIS")
        print("="*80)
        
        # Load data
        tick_df = self.load_tick_data(data_file)
        if tick_df is None:
            return
        
        results = []
        
        print(f"\n🧪 TESTING COMBINATIONS...")
        print(f"Timeframes: {len(self.timeframes)} | Strategies: {len(self.strategies_config)}")
        print("="*80)
        
        # Test all combinations
        for tf_name, tf_code in self.timeframes.items():
            for strategy_name, strategy_params in self.strategies_config.items():
                print(f"Testing {tf_name} + {strategy_name}...", end=" ")
                
                result = self.test_timeframe_strategy(tick_df, tf_name, tf_code, strategy_name, strategy_params)
                
                if result:
                    results.append(result)
                    print(f"✅ {result['trades']} trades, P&L: £{result['total_pnl']:+.2f}")
                else:
                    print("❌ Insufficient data")
        
        if not results:
            print("❌ No valid results generated")
            return
        
        # Sort by profitability
        results.sort(key=lambda x: x['total_pnl'], reverse=True)
        
        # Display comprehensive results
        print(f"\n📊 OPTIMIZATION RESULTS ({len(results)} combinations tested)")
        print("="*120)
        print(f"{'Rank':<4} {'Timeframe':<10} {'Strategy':<20} {'Trades':<7} {'P&L':<10} {'Return%':<8} {'WinRate%':<9} {'PF':<6} {'Candles':<8}")
        print("-"*120)
        
        for i, result in enumerate(results[:15], 1):  # Top 15 results
            pf_display = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
            
            print(f"{i:<4} {result['timeframe']:<10} {result['strategy']:<20} "
                  f"{result['trades']:<7} £{result['total_pnl']:<9.2f} "
                  f"{result['return_pct']:<7.2f} {result['win_rate']:<8.1f} "
                  f"{pf_display:<6} {result['candles']:<8}")
        
        # Best performer analysis
        best = results[0]
        print(f"\n🏆 OPTIMAL CONFIGURATION:")
        print("="*60)
        print(f"📈 Best Combination: {best['timeframe']} + {best['strategy']}")
        print(f"   Total P&L: £{best['total_pnl']:+.2f}")
        print(f"   Return: {best['return_pct']:+.2f}%")
        print(f"   Win Rate: {best['win_rate']:.1f}%")
        print(f"   Total Trades: {best['trades']}")
        print(f"   Candles Generated: {best['candles']}")
        
        if best['trade_details']:
            print(f"\n📋 Sample Trades from Best Configuration:")
            for i, trade in enumerate(best['trade_details'], 1):
                print(f"   {i}. {trade['direction']} £{trade['entry_price']:.2f}→£{trade['exit_price']:.2f} "
                      f"P&L: £{trade['pnl']:+.2f} ({trade['exit_reason']})")
        
        # Timeframe analysis
        print(f"\n📊 TIMEFRAME PERFORMANCE SUMMARY:")
        print("="*60)
        tf_performance = {}
        for result in results:
            tf = result['timeframe']
            if tf not in tf_performance:
                tf_performance[tf] = []
            tf_performance[tf].append(result['total_pnl'])
        
        for tf, pnls in tf_performance.items():
            avg_pnl = sum(pnls) / len(pnls)
            best_pnl = max(pnls)
            print(f"   {tf:<10}: Avg P&L: £{avg_pnl:+.2f} | Best: £{best_pnl:+.2f} | Tests: {len(pnls)}")
        
        # Profitable combinations
        profitable = [r for r in results if r['total_pnl'] > 0]
        print(f"\n✅ PROFITABLE COMBINATIONS: {len(profitable)}/{len(results)}")
        
        if profitable:
            print("="*60)
            for result in profitable:
                print(f"   🟢 {result['timeframe']} + {result['strategy']}: £{result['total_pnl']:+.2f} "
                      f"({result['win_rate']:.1f}% win rate)")
        else:
            print("   ⚠️  No profitable combinations found - market may be ranging or need different strategies")
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Timeframe Optimization System')
    parser.add_argument('data_file', help='Tick data file to analyze')
    parser.add_argument('--max-ticks', type=int, default=200000, 
                       help='Maximum ticks to process (default: 200,000)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_file):
        print(f"❌ File not found: {args.data_file}")
        return
    
    optimizer = TimeframeOptimizer()
    results = optimizer.optimize_timeframes(args.data_file)
    
    if results:
        print(f"\n🚀 ANALYSIS COMPLETE!")
        print(f"📁 Results for {os.path.basename(args.data_file)}")
        print(f"🔍 Use the top-performing combination for live trading")

if __name__ == "__main__":
    main()