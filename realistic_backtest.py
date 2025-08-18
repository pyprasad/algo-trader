#!/usr/bin/env python3
"""
Realistic backtest with unblocked configuration and proper signal generation
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import yaml

class RealisticBacktester:
    def __init__(self):
        """Initialize backtester"""
        self.positions = {}
        self.trades = []
        self.balance = 10000  # Starting balance
        self.initial_balance = self.balance
        self.peak_balance = self.balance
        self.max_drawdown = 0
        
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
    
    def generate_realistic_signals(self, df: pd.DataFrame, market: str) -> pd.DataFrame:
        """Generate realistic trading signals based on momentum and volatility"""
        
        # Calculate indicators
        df['rsi'] = self.calculate_rsi(df['midprice'], 14)
        df['sma_fast'] = df['midprice'].rolling(10).mean()
        df['sma_slow'] = df['midprice'].rolling(20).mean()
        df['momentum'] = df['midprice'].pct_change(5) * 100
        df['volatility'] = df['midprice'].rolling(20).std()
        
        # Generate signals based on multiple conditions
        df['signal'] = 0
        
        # BUY conditions: Oversold + positive momentum + trend alignment
        buy_conditions = (
            (df['rsi'] < 40) &  # Oversold
            (df['momentum'] > 0.05) &  # Positive momentum
            (df['sma_fast'] > df['sma_slow']) &  # Uptrend
            (df['volatility'] > df['volatility'].rolling(50).mean() * 0.8)  # Some volatility
        )
        
        # SELL conditions: Overbought + negative momentum + trend alignment
        sell_conditions = (
            (df['rsi'] > 60) &  # Overbought
            (df['momentum'] < -0.05) &  # Negative momentum
            (df['sma_fast'] < df['sma_slow']) &  # Downtrend
            (df['volatility'] > df['volatility'].rolling(50).mean() * 0.8)  # Some volatility
        )
        
        df.loc[buy_conditions, 'signal'] = 1
        df.loc[sell_conditions, 'signal'] = -1
        
        return df
    
    def calculate_position_size(self, market: str) -> float:
        """Calculate position size - realistic for unblocked config"""
        if market == 'DAX':
            return 3.0  # £3 per point (aggressive but manageable)
        else:  # FTSE 100
            return 8.0  # £8 per point (aggressive but manageable)
    
    def execute_trade(self, market: str, signal: int, bid: float, offer: float, timestamp: pd.Timestamp):
        """Execute a trade based on signal"""
        if market in self.positions:
            return  # Only 1 trade per market
        
        if signal != 0:
            size = self.calculate_position_size(market)
            
            # Use realistic entry prices
            if signal > 0:  # BUY
                entry_price = offer  # Buy at offer
                stop_loss = entry_price - 20  # 20 pip stop
                take_profit = entry_price + 30  # 30 pip target
            else:  # SELL
                entry_price = bid  # Sell at bid
                stop_loss = entry_price + 20  # 20 pip stop
                take_profit = entry_price - 30  # 30 pip target
            
            position = {
                'market': market,
                'direction': 'BUY' if signal > 0 else 'SELL',
                'entry_price': entry_price,
                'size': size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_time': timestamp
            }
            self.positions[market] = position
            print(f"📈 {timestamp.strftime('%H:%M:%S')} - {market} {position['direction']} @ {entry_price:.2f} (£{size}/pt)")
    
    def check_exits(self, market: str, bid: float, offer: float, timestamp: pd.Timestamp):
        """Check if position should be closed"""
        if market not in self.positions:
            return
            
        position = self.positions[market]
        
        if position['direction'] == 'BUY':
            # For longs, we exit at bid price
            current_price = bid
            if current_price <= position['stop_loss'] or current_price >= position['take_profit']:
                pnl = (current_price - position['entry_price']) * position['size']
                self.close_position(market, current_price, timestamp, pnl)
        
        elif position['direction'] == 'SELL':
            # For shorts, we exit at offer price
            current_price = offer
            if current_price >= position['stop_loss'] or current_price <= position['take_profit']:
                pnl = (position['entry_price'] - current_price) * position['size']
                self.close_position(market, current_price, timestamp, pnl)
    
    def close_position(self, market: str, exit_price: float, timestamp: pd.Timestamp, pnl: float):
        """Close a position and record the trade"""
        position = self.positions[market]
        
        self.balance += pnl
        
        # Track peak and drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance
        current_drawdown = (self.peak_balance - self.balance) / self.peak_balance * 100
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        trade = {
            'market': market,
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'size': position['size'],
            'pnl': pnl,
            'entry_time': position['entry_time'],
            'exit_time': timestamp,
            'duration': (timestamp - position['entry_time']).total_seconds() / 60
        }
        self.trades.append(trade)
        
        status = "✅" if pnl > 0 else "❌"
        print(f"{status} {timestamp.strftime('%H:%M:%S')} - {market} CLOSE @ {exit_price:.2f} | P&L: £{pnl:+.2f}")
        
        del self.positions[market]
    
    def run_backtest(self, ftse_file: str, dax_file: str):
        """Run backtest on both markets"""
        print("🚀 REALISTIC BACKTEST - UNBLOCKED CONFIGURATION")
        print("🗓️ Today's Data (08/18) - All Protections Disabled")
        print("="*70)
        print(f"💰 Initial Balance: £{self.initial_balance:,.2f}")
        print(f"🎯 Strategy: Momentum + RSI + Trend + 1 trade per market")
        print(f"📊 Position Sizes: DAX £3/pt, FTSE £8/pt")
        print("="*70)
        
        # Load data
        print("\n📊 Loading tick data...")
        ftse_df = self.load_tick_data(ftse_file)
        dax_df = self.load_tick_data(dax_file)
        
        print(f"✅ FTSE 100: {len(ftse_df):,} ticks")
        print(f"✅ DAX: {len(dax_df):,} ticks")
        
        # Generate signals
        print("\n🔍 Generating trading signals...")
        ftse_df = self.generate_realistic_signals(ftse_df, 'FTSE 100')
        dax_df = self.generate_realistic_signals(dax_df, 'DAX')
        
        # Sample for realistic timing (every 500 ticks to allow proper spacing)
        ftse_sample = ftse_df.iloc[::500].copy()
        dax_sample = dax_df.iloc[::500].copy()
        
        print(f"📈 Processing {len(ftse_sample)} FTSE signals and {len(dax_sample)} DAX signals")
        
        # Combine and sort by timestamp
        ftse_sample['market'] = 'FTSE 100'
        dax_sample['market'] = 'DAX'
        
        all_ticks = pd.concat([ftse_sample, dax_sample])
        all_ticks = all_ticks.sort_values('timestamp')
        
        print("\n🎯 Executing trades...")
        print("="*70)
        
        # Process each tick
        hourly_pnl = {}
        for idx, row in all_ticks.iterrows():
            market = row['market']
            bid = row['bid']
            offer = row['offer']
            timestamp = row['timestamp']
            signal = row['signal']
            
            # Track hourly P&L
            hour = timestamp.hour
            if hour not in hourly_pnl:
                hourly_pnl[hour] = {'trades': 0, 'pnl': 0}
            
            # Check exits first
            prev_balance = self.balance
            self.check_exits(market, bid, offer, timestamp)
            
            # If a trade was closed, update hourly P&L
            if self.balance != prev_balance:
                pnl_change = self.balance - prev_balance
                hourly_pnl[hour]['pnl'] += pnl_change
                hourly_pnl[hour]['trades'] += 1
            
            # Then check for new entries
            if pd.notna(signal) and signal != 0:
                self.execute_trade(market, signal, bid, offer, timestamp)
        
        # Close any remaining positions
        print("\n🔚 Closing remaining positions...")
        for market in list(self.positions.keys()):
            if market == 'FTSE 100':
                last_bid = ftse_sample.iloc[-1]['bid']
                last_offer = ftse_sample.iloc[-1]['offer']
            else:
                last_bid = dax_sample.iloc[-1]['bid']
                last_offer = dax_sample.iloc[-1]['offer']
            self.check_exits(market, last_bid, last_offer, all_ticks.iloc[-1]['timestamp'])
        
        # Generate comprehensive report
        self.generate_detailed_report(hourly_pnl)
    
    def generate_detailed_report(self, hourly_pnl):
        """Generate detailed backtest report"""
        print("\n" + "="*70)
        print("📊 UNBLOCKED CONFIGURATION RESULTS")
        print("="*70)
        
        total_trades = len(self.trades)
        if total_trades == 0:
            print("⚠️ No trades executed - signals still too restrictive!")
            print("\n💡 This means even with unblocked config, market conditions")
            print("   didn't generate strong enough signals for trades.")
            print("   The live system would likely be similar.")
            return
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        print(f"\n💰 FINANCIAL SUMMARY:")
        print(f"   Initial Balance:    £{self.initial_balance:,.2f}")
        print(f"   Final Balance:      £{self.balance:,.2f}")
        print(f"   Total P&L:          £{total_pnl:+,.2f}")
        print(f"   Return:             {((self.balance - self.initial_balance) / self.initial_balance * 100):+.2f}%")
        print(f"   Max Drawdown:       {self.max_drawdown:.2f}%")
        
        print(f"\n📈 TRADING STATISTICS:")
        print(f"   Total Trades:       {total_trades}")
        print(f"   Winning Trades:     {len(winning_trades)} ({win_rate:.1f}%)")
        print(f"   Losing Trades:      {len(losing_trades)} ({100-win_rate:.1f}%)")
        
        if winning_trades:
            avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades)
            max_win = max(t['pnl'] for t in winning_trades)
            print(f"   Average Win:        £{avg_win:+,.2f}")
            print(f"   Largest Win:        £{max_win:+,.2f}")
        
        if losing_trades:
            avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades)
            max_loss = min(t['pnl'] for t in losing_trades)
            print(f"   Average Loss:       £{avg_loss:+,.2f}")
            print(f"   Largest Loss:       £{max_loss:+,.2f}")
        
        # Market breakdown
        print(f"\n🎯 MARKET BREAKDOWN:")
        for market in ['FTSE 100', 'DAX']:
            market_trades = [t for t in self.trades if t['market'] == market]
            if market_trades:
                market_pnl = sum(t['pnl'] for t in market_trades)
                market_wins = len([t for t in market_trades if t['pnl'] > 0])
                market_win_rate = (market_wins/len(market_trades)*100)
                avg_duration = sum(t['duration'] for t in market_trades) / len(market_trades)
                
                print(f"\n   {market}:")
                print(f"      Trades:          {len(market_trades)}")
                print(f"      Total P&L:       £{market_pnl:+,.2f}")
                print(f"      Win Rate:        {market_win_rate:.1f}%")
                print(f"      Avg Duration:    {avg_duration:.1f} minutes")
        
        # Hourly breakdown
        if hourly_pnl:
            print(f"\n⏰ HOURLY P&L BREAKDOWN:")
            print(f"   {'Hour':<10} {'Trades':<10} {'P&L':<15}")
            print("   " + "-"*35)
            
            for hour in sorted(hourly_pnl.keys()):
                if hourly_pnl[hour]['trades'] > 0:
                    pnl = hourly_pnl[hour]['pnl']
                    print(f"   {hour:02d}:00-{hour:02d}:59  {hourly_pnl[hour]['trades']:<10} £{pnl:+10.2f}")
        
        print("\n" + "="*70)
        print(f"💡 CONCLUSION: With unblocked config, you could have made £{total_pnl:+,.2f} today")
        print(f"🎯 This represents a {((self.balance - self.initial_balance) / self.initial_balance * 100):+.2f}% return")
        print(f"⚠️ Remember: This is aggressive configuration with higher risk")
        print("="*70)

if __name__ == "__main__":
    backtester = RealisticBacktester()
    backtester.run_backtest(
        ftse_file="tick_ftse_100_08_18.json",
        dax_file="tick_dax_08_18.json"
    )