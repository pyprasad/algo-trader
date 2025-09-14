#!/usr/bin/env python3.12
# runners/optimal_trading_system.py

"""
OPTIMAL TRADING SYSTEM
Based on comprehensive timeframe and algorithm testing

Key Findings:
- 10-minute candles work best for both FTSE and DAX
- MA Crossover (5/20) most profitable algorithm
- SuperTrend as backup strategy
- Conservative risk management essential
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
import yaml
import time

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.candle_aggregator import CandleAggregator
from core.enhanced_strategies import EnhancedTradingStrategies

class OptimalTradingSystem:
    """
    Production-ready trading system using optimal configurations
    """
    
    def __init__(self, config_path='configs/optimal_config.yaml'):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.aggregator = CandleAggregator()
        self.strategies = EnhancedTradingStrategies()
        
        # Trading state
        self.positions = {}
        self.daily_trades = {}
        self.daily_pnl = {}
        self.total_pnl = 0.0
        self.balance = 10000.0  # Starting balance
        
        print("🚀 OPTIMAL TRADING SYSTEM INITIALIZED")
        print(f"   Starting Balance: £{self.balance:.2f}")
    
    def get_market_config(self, market_name):
        """Get optimal configuration for specific market"""
        timeframe = self.config['trading']['optimal_timeframes'].get(market_name, '10min')
        
        primary_algo = self.config['trading']['optimal_algorithms'].get(market_name, {}).get('primary', 'ma_crossover')
        
        algo_params = self.config['algorithms'][primary_algo].get(market_name, 
                     self.config['algorithms'][primary_algo]['default'])
        
        return timeframe, primary_algo, algo_params
    
    def load_and_process_data(self, file_path, market_name):
        """Load tick data and convert to optimal timeframe"""
        
        # Load tick data
        ticks = []
        with open(file_path, 'r') as f:
            for i, line in enumerate(f):
                if i > 100000:  # Reasonable limit for demo
                    break
                if line.strip():
                    tick = json.loads(line.strip())
                    if 'timestamp' in tick and '$date' in tick['timestamp']:
                        tick['timestamp'] = datetime.fromisoformat(
                            tick['timestamp']['$date'].replace('Z', '+00:00')
                        )
                    ticks.append(tick)
        
        tick_df = pd.DataFrame(ticks).sort_values('timestamp')
        
        # Get optimal timeframe for this market
        timeframe, _, _ = self.get_market_config(market_name)
        
        # Convert to candles
        candles = self.aggregator.ticks_to_candles(tick_df, timeframe.replace('min', 'T'))
        candles = self.aggregator.add_volatility_filter(candles)
        
        return candles
    
    def should_trade(self, candle_data, market_name):
        """Check if conditions are right for trading"""
        
        # Daily trade limit
        today = datetime.now().date()
        daily_trades = self.daily_trades.get(today, 0)
        max_daily = self.config['risk_management']['max_daily_trades']
        
        if daily_trades >= max_daily:
            return False, f"Daily trade limit reached ({daily_trades}/{max_daily})"
        
        # Daily loss limit
        daily_loss = self.daily_pnl.get(today, 0)
        max_loss_pct = self.config['risk_management']['max_daily_loss_percent']
        max_loss_amount = self.balance * (max_loss_pct / 100)
        
        if daily_loss <= -max_loss_amount:
            return False, f"Daily loss limit reached (£{daily_loss:.2f})"
        
        # Position limit
        current_positions = len(self.positions)
        max_positions = self.config['risk_management']['max_positions']
        
        if current_positions >= max_positions:
            return False, f"Maximum positions reached ({current_positions}/{max_positions})"
        
        # Spread check
        spread = candle_data.get('spread', 0)
        max_spread = self.config['risk_management']['max_spread_pips']
        
        if spread > max_spread:
            return False, f"Spread too wide (£{spread:.2f} > £{max_spread})"
        
        # Volatility check
        atr = candle_data.get('atr', 0)
        min_atr = self.config['volatility']['min_atr_threshold']
        max_atr = self.config['volatility']['max_atr_threshold']
        
        if atr < min_atr:
            return False, f"Volatility too low (ATR: {atr:.2f})"
        if atr > max_atr:
            return False, f"Volatility too high (ATR: {atr:.2f})"
        
        return True, "All conditions passed"
    
    def calculate_position_size(self, market_name):
        """Calculate position size based on risk management"""
        risk_pct = self.config['risk_management']['position_size_percent']
        position_value = self.balance * (risk_pct / 100)
        return position_value / self.balance  # Normalize to 1.0 for calculation
    
    def execute_trade(self, signal, candle_data, market_name, algo_params):
        """Execute a trade based on signal"""
        
        # Calculate position size
        position_size = self.calculate_position_size(market_name)
        
        # Entry price (account for spread)
        if signal == 'BUY':
            entry_price = candle_data['offer_close']
            sl_distance = algo_params.get('stop_loss_pips', 15)
            tp_distance = algo_params.get('take_profit_pips', 30)
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + tp_distance
        else:  # SELL
            entry_price = candle_data['bid_close']
            sl_distance = algo_params.get('stop_loss_pips', 15)
            tp_distance = algo_params.get('take_profit_pips', 30)
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - tp_distance
        
        # Adjust for spread buffer
        spread_buffer = self.config['risk_management']['spread_buffer']
        if signal == 'BUY':
            stop_loss -= spread_buffer
            take_profit -= spread_buffer
        else:
            stop_loss += spread_buffer
            take_profit += spread_buffer
        
        # Create position
        position = {
            'market': market_name,
            'direction': signal,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'timestamp': candle_data['timestamp'],
            'entry_candle': candle_data
        }
        
        self.positions[market_name] = position
        
        # Update counters
        today = datetime.now().date()
        self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
        
        print(f"📈 TRADE EXECUTED: {market_name}")
        print(f"   Direction: {signal}")
        print(f"   Entry: £{entry_price:.2f}")
        print(f"   Stop Loss: £{stop_loss:.2f}")
        print(f"   Take Profit: £{take_profit:.2f}")
        print(f"   Position Size: {position_size:.1%}")
        
        return position
    
    def check_exits(self, candle_data, market_name):
        """Check if any positions should be closed"""
        
        if market_name not in self.positions:
            return None
        
        position = self.positions[market_name]
        
        # Check stop loss / take profit
        current_low = candle_data['low']
        current_high = candle_data['high']
        
        exit_triggered = False
        exit_price = None
        exit_reason = None
        
        if position['direction'] == 'BUY':
            if current_low <= position['stop_loss']:
                exit_triggered = True
                exit_price = position['stop_loss']
                exit_reason = 'STOP_LOSS'
            elif current_high >= position['take_profit']:
                exit_triggered = True
                exit_price = position['take_profit']
                exit_reason = 'TAKE_PROFIT'
        
        else:  # SELL
            if current_high >= position['stop_loss']:
                exit_triggered = True
                exit_price = position['stop_loss']
                exit_reason = 'STOP_LOSS'
            elif current_low <= position['take_profit']:
                exit_triggered = True
                exit_price = position['take_profit']
                exit_reason = 'TAKE_PROFIT'
        
        if exit_triggered:
            return self.close_position(position, exit_price, exit_reason, candle_data)
        
        return None
    
    def close_position(self, position, exit_price, exit_reason, candle_data):
        """Close a position and calculate P&L"""
        
        # Calculate P&L
        if position['direction'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['position_size'] * self.balance
        else:
            pnl = (position['entry_price'] - exit_price) * position['position_size'] * self.balance
        
        # Account for spread costs
        spread_cost = candle_data.get('spread', 2.0)
        pnl -= spread_cost
        
        # Update balance and tracking
        self.balance += pnl
        self.total_pnl += pnl
        
        today = datetime.now().date()
        self.daily_pnl[today] = self.daily_pnl.get(today, 0) + pnl
        
        # Create trade record
        trade = {
            'market': position['market'],
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl,
            'exit_reason': exit_reason,
            'duration': (candle_data['timestamp'] - position['timestamp']).total_seconds() / 3600,  # Hours
            'timestamp': candle_data['timestamp']
        }
        
        # Remove position
        del self.positions[position['market']]
        
        print(f"🔚 POSITION CLOSED: {position['market']}")
        print(f"   Exit: £{exit_price:.2f} ({exit_reason})")
        print(f"   P&L: £{pnl:.2f}")
        print(f"   New Balance: £{self.balance:.2f}")
        
        return trade
    
    def run_backtest(self, data_files):
        """Run complete backtest on multiple files"""
        
        print("\n🚀 RUNNING OPTIMAL TRADING SYSTEM BACKTEST")
        print("=" * 70)
        
        all_trades = []
        
        for file_path in data_files:
            if not os.path.exists(file_path):
                print(f"⚠️  File not found: {file_path}")
                continue
            
            print(f"\n📁 Processing {os.path.basename(file_path)}...")
            
            # Determine market name
            if 'ftse' in file_path.lower():
                market_name = 'FTSE 100'
            elif 'dax' in file_path.lower():
                market_name = 'DAX'
            else:
                market_name = 'UNKNOWN'
            
            # Load and process data
            candles = self.load_and_process_data(file_path, market_name)
            print(f"   📊 Generated {len(candles)} candles")
            
            # Get optimal configuration
            timeframe, algorithm, algo_params = self.get_market_config(market_name)
            print(f"   ⚙️  Using {algorithm} strategy on {timeframe} timeframe")
            
            # Apply strategy
            if algorithm == 'ma_crossover':
                strategy_df = self.strategies.ma_crossover_strategy(candles, algo_params)
            elif algorithm == 'supertrend':
                strategy_df = self.strategies.supertrend_strategy(candles, algo_params)
            else:
                print(f"   ❌ Unknown algorithm: {algorithm}")
                continue
            
            # Process each candle
            for i, (_, candle) in enumerate(strategy_df.iterrows()):
                
                # Check for exits first
                trade = self.check_exits(candle.to_dict(), market_name)
                if trade:
                    all_trades.append(trade)
                
                # Check for new entries
                if candle['signal'] in ['BUY', 'SELL']:
                    
                    # Check if we should trade
                    can_trade, reason = self.should_trade(candle.to_dict(), market_name)
                    
                    if can_trade and market_name not in self.positions:
                        position = self.execute_trade(
                            candle['signal'], 
                            candle.to_dict(), 
                            market_name, 
                            algo_params
                        )
        
        # Close any remaining positions
        for market_name, position in list(self.positions.items()):
            # Close at last available price
            last_candle = strategy_df.iloc[-1].to_dict()
            exit_price = last_candle['close']
            trade = self.close_position(position, exit_price, 'END_OF_DATA', last_candle)
            if trade:
                all_trades.append(trade)
        
        # Display results
        self.display_results(all_trades)
        
        return all_trades
    
    def display_results(self, trades):
        """Display comprehensive trading results"""
        
        print("\n" + "=" * 80)
        print("💰 OPTIMAL TRADING SYSTEM RESULTS")
        print("=" * 80)
        
        if not trades:
            print("❌ No trades executed")
            return
        
        # Calculate metrics
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = (len(wins) / len(trades)) * 100
        avg_win = sum(w['pnl'] for w in wins) / len(wins) if wins else 0
        avg_loss = sum(l['pnl'] for l in losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(w['pnl'] for w in wins) / sum(l['pnl'] for l in losses)) if losses else float('inf')
        
        avg_duration = sum(t['duration'] for t in trades) / len(trades)
        
        # Performance summary
        print(f"📊 PERFORMANCE SUMMARY:")
        print(f"   Total P&L: £{total_pnl:.2f}")
        print(f"   Starting Balance: £10,000.00")
        print(f"   Final Balance: £{self.balance:.2f}")
        print(f"   Return: {((self.balance - 10000) / 10000 * 100):+.2f}%")
        print()
        print(f"📈 TRADE STATISTICS:")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Winning Trades: {len(wins)} ({win_rate:.1f}%)")
        print(f"   Losing Trades: {len(losses)}")
        print(f"   Average Win: £{avg_win:.2f}")
        print(f"   Average Loss: £{avg_loss:.2f}")
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Average Duration: {avg_duration:.1f} hours")
        
        # Trade breakdown
        print(f"\n📋 DETAILED TRADE LOG:")
        print(f"{'Market':<12} {'Dir':<4} {'Entry':<8} {'Exit':<8} {'P&L':<10} {'Reason':<12} {'Duration':<10}")
        print("-" * 80)
        
        for trade in trades:
            print(f"{trade['market']:<12} {trade['direction']:<4} £{trade['entry_price']:<7.2f} "
                  f"£{trade['exit_price']:<7.2f} £{trade['pnl']:<9.2f} {trade['exit_reason']:<12} "
                  f"{trade['duration']:<9.1f}h")
        
        # Success assessment
        if total_pnl > 0:
            print(f"\n✅ SYSTEM PROFITABLE!")
            print(f"   Strategy successfully identified profitable opportunities")
        else:
            print(f"\n❌ System needs optimization")
            print(f"   Consider adjusting parameters or testing different timeframes")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimal Trading System')
    parser.add_argument('files', nargs='+', help='Tick data files to backtest')
    parser.add_argument('--config', default='configs/optimal_config.yaml',
                       help='Configuration file')
    
    args = parser.parse_args()
    
    system = OptimalTradingSystem(args.config)
    trades = system.run_backtest(args.files)
    
    return trades


if __name__ == "__main__":
    main()