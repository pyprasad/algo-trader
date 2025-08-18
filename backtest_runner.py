#!/usr/bin/env python3
"""
Backtest runner for the algo trading system using historical tick data
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import yaml

class SimpleBacktester:
    def __init__(self, config_path: str = "configs/simplified_trading.yaml"):
        """Initialize backtester with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.positions = {}
        self.trades = []
        self.balance = 10000  # Starting balance
        self.initial_balance = self.balance
        
    def load_tick_data(self, filepath: str) -> pd.DataFrame:
        """Load tick data from JSON file"""
        ticks = []
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    tick = json.loads(line)
                    ticks.append({
                        'timestamp': pd.to_datetime(tick['timestamp']['$date']),
                        'bid': tick['bid'],
                        'offer': tick['offer'],
                        'midprice': tick['midprice'],
                        'market': tick['market']
                    })
                except:
                    continue
        
        df = pd.DataFrame(ticks)
        df = df.sort_values('timestamp')
        df = df.reset_index(drop=True)
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, df: pd.DataFrame, market: str) -> pd.DataFrame:
        """Generate trading signals based on RSI"""
        market_config = self.config['market_strategies'].get(market, {})
        
        rsi_period = market_config.get('rsi_period', 14)
        rsi_buy = market_config.get('rsi_buy_threshold', 30)
        rsi_sell = market_config.get('rsi_sell_threshold', 70)
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['midprice'], rsi_period)
        
        # Generate signals
        df['signal'] = 0
        df.loc[df['rsi'] < rsi_buy, 'signal'] = 1  # Buy signal
        df.loc[df['rsi'] > rsi_sell, 'signal'] = -1  # Sell signal
        
        return df
    
    def execute_trade(self, market: str, signal: int, price: float, timestamp: pd.Timestamp):
        """Execute a trade based on signal"""
        market_config = self.config['market_strategies'].get(market, {})
        
        stop_loss_pips = market_config.get('stop_loss_pips', 10)
        take_profit_pips = market_config.get('take_profit_pips', 15)
        
        # Position sizing (£1 per point for simplicity)
        size = 1.0
        
        if market not in self.positions:
            if signal != 0:
                # Open new position
                position = {
                    'market': market,
                    'direction': 'BUY' if signal > 0 else 'SELL',
                    'entry_price': price,
                    'size': size,
                    'stop_loss': price - stop_loss_pips if signal > 0 else price + stop_loss_pips,
                    'take_profit': price + take_profit_pips if signal > 0 else price - take_profit_pips,
                    'entry_time': timestamp
                }
                self.positions[market] = position
                print(f"📈 {timestamp} - {market} {position['direction']} @ {price:.2f}")
        
    def check_exits(self, market: str, price: float, timestamp: pd.Timestamp):
        """Check if position should be closed"""
        if market not in self.positions:
            return
            
        position = self.positions[market]
        
        # Check stop loss and take profit
        if position['direction'] == 'BUY':
            if price <= position['stop_loss'] or price >= position['take_profit']:
                # Close position
                pnl = (price - position['entry_price']) * position['size']
                self.balance += pnl
                
                trade = {
                    'market': market,
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'pnl': pnl,
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp
                }
                self.trades.append(trade)
                
                status = "✅" if pnl > 0 else "❌"
                print(f"{status} {timestamp} - {market} CLOSE @ {price:.2f} | P&L: £{pnl:.2f}")
                
                del self.positions[market]
        
        elif position['direction'] == 'SELL':
            if price >= position['stop_loss'] or price <= position['take_profit']:
                # Close position
                pnl = (position['entry_price'] - price) * position['size']
                self.balance += pnl
                
                trade = {
                    'market': market,
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': price,
                    'pnl': pnl,
                    'entry_time': position['entry_time'],
                    'exit_time': timestamp
                }
                self.trades.append(trade)
                
                status = "✅" if pnl > 0 else "❌"
                print(f"{status} {timestamp} - {market} CLOSE @ {price:.2f} | P&L: £{pnl:.2f}")
                
                del self.positions[market]
    
    def run_backtest(self, ftse_file: str, dax_file: str):
        """Run backtest on both markets"""
        print("🚀 Starting Backtest...")
        print(f"💰 Initial Balance: £{self.initial_balance:.2f}")
        print("="*60)
        
        # Load data
        print("📊 Loading tick data...")
        ftse_df = self.load_tick_data(ftse_file)
        dax_df = self.load_tick_data(dax_file)
        
        print(f"✅ FTSE 100: {len(ftse_df)} ticks")
        print(f"✅ DAX: {len(dax_df)} ticks")
        
        # Generate signals
        print("\n🔍 Generating trading signals...")
        ftse_df = self.generate_signals(ftse_df, 'FTSE 100')
        dax_df = self.generate_signals(dax_df, 'DAX')
        
        # Sample data for faster processing (every 100th tick)
        ftse_sample = ftse_df.iloc[::100].copy()
        dax_sample = dax_df.iloc[::100].copy()
        
        print(f"📈 Processing {len(ftse_sample)} FTSE samples and {len(dax_sample)} DAX samples")
        
        # Combine and sort by timestamp
        ftse_sample['market'] = 'FTSE 100'
        dax_sample['market'] = 'DAX'
        
        all_ticks = pd.concat([ftse_sample, dax_sample])
        all_ticks = all_ticks.sort_values('timestamp')
        
        print("\n🎯 Executing trades...")
        print("="*60)
        
        # Process each tick
        for idx, row in all_ticks.iterrows():
            market = row['market']
            price = row['midprice']
            timestamp = row['timestamp']
            signal = row['signal']
            
            # Check exits first
            self.check_exits(market, price, timestamp)
            
            # Then check for new entries
            if pd.notna(signal):
                self.execute_trade(market, signal, price, timestamp)
        
        # Close any remaining positions at last price
        print("\n🔚 Closing remaining positions...")
        for market, position in list(self.positions.items()):
            last_price = ftse_sample.iloc[-1]['midprice'] if market == 'FTSE 100' else dax_sample.iloc[-1]['midprice']
            self.check_exits(market, last_price, all_ticks.iloc[-1]['timestamp'])
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate backtest report"""
        print("\n" + "="*60)
        print("📊 BACKTEST RESULTS")
        print("="*60)
        
        total_trades = len(self.trades)
        if total_trades == 0:
            print("⚠️ No trades executed during backtest!")
            print("\nPossible reasons:")
            print("1. RSI thresholds too extreme (current: buy<30, sell>70)")
            print("2. Not enough data points for RSI calculation")
            print("3. Confidence thresholds too high")
            return
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        print(f"\n💰 Financial Summary:")
        print(f"   Initial Balance: £{self.initial_balance:.2f}")
        print(f"   Final Balance: £{self.balance:.2f}")
        print(f"   Total P&L: £{total_pnl:.2f}")
        print(f"   Return: {((self.balance - self.initial_balance) / self.initial_balance * 100):.2f}%")
        
        print(f"\n📈 Trading Statistics:")
        print(f"   Total Trades: {total_trades}")
        print(f"   Winning Trades: {len(winning_trades)}")
        print(f"   Losing Trades: {len(losing_trades)}")
        print(f"   Win Rate: {win_rate:.2f}%")
        
        if winning_trades:
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
            print(f"   Average Win: £{avg_win:.2f}")
        
        if losing_trades:
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
            print(f"   Average Loss: £{avg_loss:.2f}")
        
        # Market breakdown
        print(f"\n🎯 Market Breakdown:")
        for market in ['FTSE 100', 'DAX']:
            market_trades = [t for t in self.trades if t['market'] == market]
            if market_trades:
                market_pnl = sum(t['pnl'] for t in market_trades)
                market_wins = len([t for t in market_trades if t['pnl'] > 0])
                print(f"   {market}: {len(market_trades)} trades, P&L: £{market_pnl:.2f}, Win Rate: {(market_wins/len(market_trades)*100):.1f}%")
        
        print("\n" + "="*60)

if __name__ == "__main__":
    backtester = SimpleBacktester()
    backtester.run_backtest(
        ftse_file="tick_ftse_100_08_18.json",
        dax_file="tick_dax_08_18.json"
    )