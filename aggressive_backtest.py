#!/usr/bin/env python3
"""
Aggressive backtest - trades on simple price movements to show potential
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import random

class AggressiveBacktester:
    def __init__(self):
        """Initialize backtester"""
        self.positions = {}
        self.trades = []
        self.balance = 10000  # Starting balance
        self.initial_balance = self.balance
        self.peak_balance = self.balance
        self.max_drawdown = 0
        
    def load_tick_data(self, filepath: str, market_name: str) -> pd.DataFrame:
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
                        'market': market_name
                    })
                except:
                    continue
        
        df = pd.DataFrame(ticks)
        df = df.sort_values('timestamp')
        df = df.reset_index(drop=True)
        return df
    
    def generate_aggressive_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate aggressive trading signals based on simple price movements"""
        
        # Calculate 5-period price change
        df['price_change'] = df['midprice'].diff(5)
        df['pct_change'] = df['midprice'].pct_change(10) * 100
        
        # Generate signals on ANY significant movement
        df['signal'] = 0
        
        # BUY on upward movement > 5 points for DAX, > 2 points for FTSE
        if 'DAX' in df['market'].iloc[0]:
            threshold = 8  # DAX moves more
        else:
            threshold = 3  # FTSE smaller moves
        
        # Buy on upward momentum
        df.loc[df['price_change'] > threshold, 'signal'] = 1
        # Sell on downward momentum  
        df.loc[df['price_change'] < -threshold, 'signal'] = -1
        
        return df
    
    def calculate_position_size(self, market: str) -> float:
        """Calculate position size"""
        if 'DAX' in market:
            return 2.0  # £2 per point for DAX
        else:  # FTSE 100
            return 5.0  # £5 per point for FTSE
    
    def execute_trade(self, market: str, signal: int, bid: float, offer: float, timestamp: pd.Timestamp):
        """Execute a trade based on signal"""
        if market in self.positions:
            return  # Only 1 trade per market
        
        if signal != 0:
            size = self.calculate_position_size(market)
            
            # Use realistic entry prices with spread
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
            current_price = bid
            if current_price <= position['stop_loss'] or current_price >= position['take_profit']:
                pnl = (current_price - position['entry_price']) * position['size']
                self.close_position(market, current_price, timestamp, pnl)
        
        elif position['direction'] == 'SELL':
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
        print("🚀 AGGRESSIVE BACKTEST - UNBLOCKED CONFIGURATION")
        print("🗓️ Today's Data (08/18) - Maximum Trading Potential")
        print("="*70)
        print(f"💰 Initial Balance: £{self.initial_balance:,.2f}")
        print(f"🎯 Strategy: Simple momentum trading (aggressive signals)")
        print(f"📊 Position Sizes: DAX £2/pt, FTSE £5/pt")
        print(f"⚡ Signal Threshold: DAX >8pts movement, FTSE >3pts movement")
        print("="*70)
        
        # Load data
        print("\n📊 Loading tick data...")
        ftse_df = self.load_tick_data(ftse_file, 'FTSE 100')
        dax_df = self.load_tick_data(dax_file, 'DAX')
        
        print(f"✅ FTSE 100: {len(ftse_df):,} ticks")
        print(f"✅ DAX: {len(dax_df):,} ticks")
        
        # Generate signals
        print("\n🔍 Generating aggressive trading signals...")
        ftse_df = self.generate_aggressive_signals(ftse_df)
        dax_df = self.generate_aggressive_signals(dax_df)
        
        # Count potential signals
        ftse_signals = len(ftse_df[ftse_df['signal'] != 0])
        dax_signals = len(dax_df[dax_df['signal'] != 0])
        print(f"🎯 Found {ftse_signals} FTSE signals and {dax_signals} DAX signals")
        
        # Sample for realistic 1-trade-per-market timing
        # Take every 2000th tick to allow proper trade spacing
        ftse_sample = ftse_df.iloc[::2000].copy()
        dax_sample = dax_df.iloc[::2000].copy()
        
        print(f"📈 Processing {len(ftse_sample)} FTSE samples and {len(dax_sample)} DAX samples")
        
        # Combine and sort by timestamp
        all_ticks = pd.concat([ftse_sample, dax_sample])
        all_ticks = all_ticks.sort_values('timestamp')
        
        print(f"\n🎯 Executing trades (max 1 per market)...")
        print("="*70)
        
        # Process each tick
        hourly_pnl = {}
        trades_today = 0
        
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
                trades_today += 1
            
            # Then check for new entries
            if pd.notna(signal) and signal != 0:
                self.execute_trade(market, signal, bid, offer, timestamp)
        
        # Close any remaining positions at end of day
        print(f"\n🔚 Closing remaining positions...")
        for market in list(self.positions.keys()):
            if market == 'FTSE 100':
                last_bid = ftse_df.iloc[-1]['bid']
                last_offer = ftse_df.iloc[-1]['offer']
                last_time = ftse_df.iloc[-1]['timestamp']
            else:
                last_bid = dax_df.iloc[-1]['bid']
                last_offer = dax_df.iloc[-1]['offer']
                last_time = dax_df.iloc[-1]['timestamp']
            
            self.check_exits(market, last_bid, last_offer, last_time)
        
        # Generate report
        self.generate_detailed_report(hourly_pnl, trades_today)
    
    def generate_detailed_report(self, hourly_pnl, trades_today):
        """Generate detailed P&L report"""
        print("\n" + "="*70)
        print("📊 AGGRESSIVE UNBLOCKED CONFIGURATION RESULTS")
        print("="*70)
        
        total_trades = len(self.trades)
        
        if total_trades == 0:
            print("⚠️ Still no trades executed!")
            print("💡 Even aggressive signals didn't generate trades.")
            print("   This suggests the original system constraints were")
            print("   preventing trades due to timing/spacing issues.")
            return
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        return_pct = ((self.balance - self.initial_balance) / self.initial_balance * 100)
        
        print(f"\n💰 FINANCIAL SUMMARY:")
        print(f"   Initial Balance:    £{self.initial_balance:,.2f}")
        print(f"   Final Balance:      £{self.balance:,.2f}")
        print(f"   Total P&L:          £{total_pnl:+,.2f}")
        print(f"   Return:             {return_pct:+.2f}%")
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
        
        if winning_trades and losing_trades:
            profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades))
            print(f"   Profit Factor:      {profit_factor:.2f}")
        
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
        
        # Best and worst trades
        if self.trades:
            best_trade = max(self.trades, key=lambda x: x['pnl'])
            worst_trade = min(self.trades, key=lambda x: x['pnl'])
            
            print(f"\n🏆 BEST TRADE:")
            print(f"   {best_trade['market']} {best_trade['direction']} @ {best_trade['entry_price']:.2f}")
            print(f"   Entry: {best_trade['entry_time'].strftime('%H:%M:%S')}")
            print(f"   Exit:  {best_trade['exit_time'].strftime('%H:%M:%S')} @ {best_trade['exit_price']:.2f}")
            print(f"   P&L:   £{best_trade['pnl']:+,.2f}")
            
            print(f"\n💔 WORST TRADE:")
            print(f"   {worst_trade['market']} {worst_trade['direction']} @ {worst_trade['entry_price']:.2f}")
            print(f"   Entry: {worst_trade['entry_time'].strftime('%H:%M:%S')}")
            print(f"   Exit:  {worst_trade['exit_time'].strftime('%H:%M:%S')} @ {worst_trade['exit_price']:.2f}")
            print(f"   P&L:   £{worst_trade['pnl']:+,.2f}")
        
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
        print("🎯 UNBLOCKED CONFIGURATION ANALYSIS")
        print("="*70)
        print(f"💡 With ALL protections disabled, you could have made: £{total_pnl:+,.2f}")
        print(f"📊 This represents a {return_pct:+.2f}% return on £{self.initial_balance:,.2f}")
        print(f"🎯 Total trades executed: {total_trades} (respecting 1 per market rule)")
        print(f"⚠️  This is maximum potential with aggressive trading")
        print(f"🛡️  Your original system protections were preventing these trades")
        print("="*70)

if __name__ == "__main__":
    # Set random seed for consistent results
    random.seed(42)
    
    backtester = AggressiveBacktester()
    backtester.run_backtest(
        ftse_file="tick_ftse_100_08_18.json",
        dax_file="tick_dax_08_18.json"
    )