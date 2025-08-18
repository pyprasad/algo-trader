#!/usr/bin/env python3
"""
Detailed backtest runner with comprehensive P&L breakdown
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import yaml

class DetailedBacktester:
    def __init__(self, config_path: str = "configs/trading_enabled.yaml"):
        """Initialize backtester with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
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
    
    def generate_signals(self, df: pd.DataFrame, market: str) -> pd.DataFrame:
        """Generate trading signals based on RSI"""
        market_config = self.config['market_strategies'].get(market, {})
        
        rsi_period = market_config.get('rsi_period', 14)
        rsi_buy = market_config.get('rsi_buy_threshold', 30)
        rsi_sell = market_config.get('rsi_sell_threshold', 70)
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['midprice'], rsi_period)
        
        # Generate signals - with 50/50 thresholds, use momentum
        df['signal'] = 0
        df['momentum'] = df['midprice'].pct_change(5) * 100  # 5-tick momentum
        
        # Buy when RSI near 50 and positive momentum
        df.loc[(df['rsi'] <= rsi_buy) & (df['momentum'] > 0.02), 'signal'] = 1
        # Sell when RSI near 50 and negative momentum  
        df.loc[(df['rsi'] >= rsi_sell) & (df['momentum'] < -0.02), 'signal'] = -1
        
        return df
    
    def calculate_position_size(self, market: str, price: float) -> float:
        """Calculate position size based on risk management"""
        # Use £2 per point for DAX, £5 per point for FTSE
        if market == 'DAX':
            return 2.0
        else:  # FTSE 100
            return 5.0
    
    def execute_trade(self, market: str, signal: int, price: float, timestamp: pd.Timestamp, spread: float):
        """Execute a trade based on signal"""
        market_config = self.config['market_strategies'].get(market, {})
        
        stop_loss_pips = market_config.get('stop_loss_pips', 10)
        take_profit_pips = market_config.get('take_profit_pips', 15)
        
        # Position sizing
        size = self.calculate_position_size(market, price)
        
        if market not in self.positions:
            if signal != 0:
                # Account for spread
                entry_price = price + (spread/2) if signal > 0 else price - (spread/2)
                
                # Open new position
                position = {
                    'market': market,
                    'direction': 'BUY' if signal > 0 else 'SELL',
                    'entry_price': entry_price,
                    'size': size,
                    'stop_loss': entry_price - stop_loss_pips if signal > 0 else entry_price + stop_loss_pips,
                    'take_profit': entry_price + take_profit_pips if signal > 0 else entry_price - take_profit_pips,
                    'entry_time': timestamp,
                    'spread_cost': spread * size
                }
                self.positions[market] = position
                # print(f"📈 {timestamp.strftime('%H:%M:%S')} - {market} {position['direction']} @ {entry_price:.2f} (size: £{size}/pt)")
        
    def check_exits(self, market: str, bid: float, offer: float, timestamp: pd.Timestamp):
        """Check if position should be closed"""
        if market not in self.positions:
            return
            
        position = self.positions[market]
        
        # Use bid for selling (closing longs), offer for buying (closing shorts)
        if position['direction'] == 'BUY':
            exit_price = bid  # We sell at bid to close long
            if exit_price <= position['stop_loss'] or exit_price >= position['take_profit']:
                # Close position
                pnl = (exit_price - position['entry_price']) * position['size']
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
                    'duration': (timestamp - position['entry_time']).total_seconds() / 60  # minutes
                }
                self.trades.append(trade)
                
                del self.positions[market]
        
        elif position['direction'] == 'SELL':
            exit_price = offer  # We buy at offer to close short
            if exit_price >= position['stop_loss'] or exit_price <= position['take_profit']:
                # Close position
                pnl = (position['entry_price'] - exit_price) * position['size']
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
                    'duration': (timestamp - position['entry_time']).total_seconds() / 60  # minutes
                }
                self.trades.append(trade)
                
                del self.positions[market]
    
    def run_backtest(self, ftse_file: str, dax_file: str):
        """Run backtest on both markets"""
        print("🚀 DETAILED BACKTEST - UNBLOCKED CONFIGURATION")
        print("🗓️ Today's Data (08/18) - Post Protection Removal")
        print("="*70)
        print(f"💰 Initial Balance: £{self.initial_balance:,.2f}")
        print(f"📊 Configuration: trading_enabled.yaml (All protections disabled)")
        print(f"🎯 Strategy: RSI 50/50 + Momentum + 1 trade per market")
        print("="*70)
        
        # Load data
        print("\n📊 Loading tick data...")
        ftse_df = self.load_tick_data(ftse_file)
        dax_df = self.load_tick_data(dax_file)
        
        print(f"✅ FTSE 100: {len(ftse_df):,} ticks")
        print(f"✅ DAX: {len(dax_df):,} ticks")
        
        # Calculate average spreads
        ftse_spread = (ftse_df['offer'] - ftse_df['bid']).mean()
        dax_spread = (dax_df['offer'] - dax_df['bid']).mean()
        print(f"\n📊 Average Spreads:")
        print(f"   FTSE 100: {ftse_spread:.2f} points")
        print(f"   DAX: {dax_spread:.2f} points")
        
        # Generate signals
        print("\n🔍 Generating trading signals...")
        ftse_df = self.generate_signals(ftse_df, 'FTSE 100')
        dax_df = self.generate_signals(dax_df, 'DAX')
        
        # Sample data more realistically for 1 trade per market rule
        ftse_sample = ftse_df.iloc[::200].copy()  # Less frequent sampling
        dax_sample = dax_df.iloc[::200].copy()    # To allow proper trade spacing
        
        print(f"📈 Processing {len(ftse_sample):,} FTSE samples and {len(dax_sample):,} DAX samples")
        
        # Combine and sort by timestamp
        ftse_sample['market'] = 'FTSE 100'
        dax_sample['market'] = 'DAX'
        
        all_ticks = pd.concat([ftse_sample, dax_sample])
        all_ticks = all_ticks.sort_values('timestamp')
        
        # Process each tick
        hourly_pnl = {}
        for idx, row in all_ticks.iterrows():
            market = row['market']
            bid = row['bid']
            offer = row['offer']
            price = row['midprice']
            timestamp = row['timestamp']
            signal = row['signal']
            spread = offer - bid
            
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
            if pd.notna(signal):
                self.execute_trade(market, signal, price, timestamp, spread)
        
        # Close any remaining positions at last price
        for market, position in list(self.positions.items()):
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
        """Generate detailed backtest report with P&L breakdown"""
        print("\n" + "="*70)
        print("📊 DETAILED BACKTEST RESULTS")
        print("="*70)
        
        total_trades = len(self.trades)
        if total_trades == 0:
            print("⚠️ No trades executed during backtest!")
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
        
        if winning_trades and losing_trades:
            profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades))
            print(f"   Profit Factor:      {profit_factor:.2f}")
        
        # Market breakdown
        print(f"\n🎯 MARKET-BY-MARKET BREAKDOWN:")
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
                
                # Position sizing used
                sizes = list(set(t['size'] for t in market_trades))
                print(f"      Position Size:   £{sizes[0]:.0f}/point" if sizes else "")
        
        # Hourly P&L breakdown
        print(f"\n⏰ HOURLY P&L BREAKDOWN:")
        print(f"   {'Hour':<10} {'Trades':<10} {'P&L':<15} {'Cumulative':<15}")
        print("   " + "-"*50)
        
        cumulative = 0
        for hour in sorted(hourly_pnl.keys()):
            if hourly_pnl[hour]['trades'] > 0:
                pnl = hourly_pnl[hour]['pnl']
                cumulative += pnl
                print(f"   {hour:02d}:00-{hour:02d}:59  {hourly_pnl[hour]['trades']:<10} £{pnl:+10.2f}     £{cumulative:+10.2f}")
        
        # Best and worst trades
        if self.trades:
            best_trade = max(self.trades, key=lambda x: x['pnl'])
            worst_trade = min(self.trades, key=lambda x: x['pnl'])
            
            print(f"\n🏆 BEST TRADE:")
            print(f"   Market:    {best_trade['market']}")
            print(f"   Direction: {best_trade['direction']}")
            print(f"   Entry:     {best_trade['entry_time'].strftime('%H:%M:%S')} @ {best_trade['entry_price']:.2f}")
            print(f"   Exit:      {best_trade['exit_time'].strftime('%H:%M:%S')} @ {best_trade['exit_price']:.2f}")
            print(f"   P&L:       £{best_trade['pnl']:+,.2f}")
            
            print(f"\n💔 WORST TRADE:")
            print(f"   Market:    {worst_trade['market']}")
            print(f"   Direction: {worst_trade['direction']}")
            print(f"   Entry:     {worst_trade['entry_time'].strftime('%H:%M:%S')} @ {worst_trade['entry_price']:.2f}")
            print(f"   Exit:      {worst_trade['exit_time'].strftime('%H:%M:%S')} @ {worst_trade['exit_price']:.2f}")
            print(f"   P&L:       £{worst_trade['pnl']:+,.2f}")
        
        # Trading session analysis
        print(f"\n📊 TRADING SESSION ANALYSIS:")
        if self.trades:
            morning_trades = [t for t in self.trades if 7 <= t['entry_time'].hour < 12]
            afternoon_trades = [t for t in self.trades if 12 <= t['entry_time'].hour < 17]
            evening_trades = [t for t in self.trades if t['entry_time'].hour >= 17 or t['entry_time'].hour < 7]
            
            if morning_trades:
                morning_pnl = sum(t['pnl'] for t in morning_trades)
                print(f"   Morning (07:00-12:00):   {len(morning_trades)} trades, P&L: £{morning_pnl:+,.2f}")
            
            if afternoon_trades:
                afternoon_pnl = sum(t['pnl'] for t in afternoon_trades)
                print(f"   Afternoon (12:00-17:00): {len(afternoon_trades)} trades, P&L: £{afternoon_pnl:+,.2f}")
            
            if evening_trades:
                evening_pnl = sum(t['pnl'] for t in evening_trades)
                print(f"   Evening (17:00-07:00):   {len(evening_trades)} trades, P&L: £{evening_pnl:+,.2f}")
        
        print("\n" + "="*70)
        print(f"💡 SUMMARY: With optimized settings, you could have made £{total_pnl:+,.2f} today")
        print(f"           representing a {((self.balance - self.initial_balance) / self.initial_balance * 100):+.2f}% return on capital")
        print("="*70)

if __name__ == "__main__":
    backtester = DetailedBacktester()
    backtester.run_backtest(
        ftse_file="tick_ftse_100_08_18.json",
        dax_file="tick_dax_08_18.json"
    )