#!/usr/bin/env python3
"""
Profile comparison backtest - tests all profile configurations
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import yaml

class ProfileBacktester:
    def __init__(self, profile_path: str):
        """Initialize backtester with profile configuration"""
        with open(profile_path, 'r') as f:
            self.profile = yaml.safe_load(f)
        
        self.profile_name = self.profile.get('profile_info', {}).get('name', 'unknown')
        self.positions = {}
        self.trades = []
        self.balance = 10000  # Starting balance
        self.initial_balance = self.balance
        self.peak_balance = self.balance
        self.max_drawdown = 0
        self.trade_count = 0
        self.daily_loss = 0
        self.consecutive_losses = 0
        
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
    
    def get_strategy_params(self) -> Dict:
        """Extract strategy parameters from profile"""
        params = self.profile.get('strategy_parameters', {})
        emergency = self.profile.get('emergency_risk', {})
        prof_trading = self.profile.get('professional_trading', {})
        
        # Set RSI thresholds based on profile
        if self.profile_name == 'scalping':
            rsi_buy = 45
            rsi_sell = 55
            rsi_period = 7
            stop_loss = params.get('stop_loss_pips', 2)
            take_profit = params.get('profit_target_pips', 3)
        elif self.profile_name == 'conservative':
            rsi_buy = 25
            rsi_sell = 75
            rsi_period = 21
            stop_loss = 15
            take_profit = 30
        elif self.profile_name == 'aggressive':
            rsi_buy = 35
            rsi_sell = 65
            rsi_period = 10
            stop_loss = 20
            take_profit = 30
        else:  # simplified
            rsi_buy = 40
            rsi_sell = 60
            rsi_period = 10
            stop_loss = 15
            take_profit = 20
        
        return {
            'rsi_buy': rsi_buy,
            'rsi_sell': rsi_sell,
            'rsi_period': rsi_period,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'min_confidence': prof_trading.get('min_signal_confidence', 0.5),
            'max_position_size': emergency.get('max_position_size', 0.1),
            'max_loss_per_trade': emergency.get('max_loss_per_trade', 0.05),
            'daily_loss_limit': emergency.get('daily_loss_limit', 0.1),
            'max_consecutive_losses': emergency.get('max_consecutive_losses', 5),
            'max_trades_per_hour': prof_trading.get('max_trades_per_hour', 10)
        }
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on profile settings"""
        params = self.get_strategy_params()
        
        # Calculate RSI
        df['rsi'] = self.calculate_rsi(df['midprice'], params['rsi_period'])
        
        # Generate signals with confidence
        df['signal'] = 0
        df['confidence'] = 0.5  # Base confidence
        
        # Scalping uses momentum
        if self.profile_name == 'scalping':
            # Quick momentum signals
            df['momentum'] = df['midprice'].pct_change(5)
            df.loc[(df['rsi'] < params['rsi_buy']) & (df['momentum'] > 0), 'signal'] = 1
            df.loc[(df['rsi'] > params['rsi_sell']) & (df['momentum'] < 0), 'signal'] = -1
            df.loc[df['signal'] != 0, 'confidence'] = 0.6
            
        # Conservative needs strong signals
        elif self.profile_name == 'conservative':
            # Only trade on extreme RSI
            df.loc[df['rsi'] < params['rsi_buy'], 'signal'] = 1
            df.loc[df['rsi'] > params['rsi_sell'], 'signal'] = -1
            df.loc[df['signal'] != 0, 'confidence'] = 0.9
            
        # Aggressive trades more frequently
        elif self.profile_name == 'aggressive':
            df.loc[df['rsi'] < params['rsi_buy'], 'signal'] = 1
            df.loc[df['rsi'] > params['rsi_sell'], 'signal'] = -1
            df.loc[df['signal'] != 0, 'confidence'] = 0.65
            
        else:  # Default/simplified
            df.loc[df['rsi'] < params['rsi_buy'], 'signal'] = 1
            df.loc[df['rsi'] > params['rsi_sell'], 'signal'] = -1
            df.loc[df['signal'] != 0, 'confidence'] = 0.5
        
        return df
    
    def check_risk_limits(self) -> bool:
        """Check if we should stop trading based on risk limits"""
        params = self.get_strategy_params()
        
        # Check daily loss limit
        daily_loss_pct = abs(self.daily_loss / self.initial_balance)
        if daily_loss_pct > params['daily_loss_limit']:
            return False
        
        # Check consecutive losses
        if self.consecutive_losses >= params['max_consecutive_losses']:
            return False
        
        return True
    
    def calculate_position_size(self, market: str, confidence: float) -> float:
        """Calculate position size based on profile and confidence"""
        params = self.get_strategy_params()
        
        # Base size
        if market == 'DAX':
            base_size = 2.0
        else:  # FTSE 100
            base_size = 5.0
        
        # Adjust based on profile
        if self.profile_name == 'scalping':
            # Smaller positions for scalping
            size_multiplier = 0.5
        elif self.profile_name == 'conservative':
            # Very small positions
            size_multiplier = 0.3
        elif self.profile_name == 'aggressive':
            # Larger positions
            size_multiplier = 1.5
        else:
            size_multiplier = 1.0
        
        # Adjust for confidence
        confidence_multiplier = confidence
        
        final_size = base_size * size_multiplier * confidence_multiplier
        
        # Cap at max position size
        max_size = self.balance * params['max_position_size'] / 100
        return min(final_size, max_size / 100)  # Convert to per-point
    
    def execute_trade(self, market: str, signal: int, price: float, timestamp: pd.Timestamp, spread: float, confidence: float):
        """Execute a trade based on signal and profile rules"""
        if not self.check_risk_limits():
            return
        
        params = self.get_strategy_params()
        
        # Check confidence threshold
        if confidence < params['min_confidence']:
            return
        
        # Check if we already have a position
        if market in self.positions:
            return
        
        if signal != 0:
            # Position sizing
            size = self.calculate_position_size(market, confidence)
            
            # Account for spread
            entry_price = price + (spread/2) if signal > 0 else price - (spread/2)
            
            # Open new position
            position = {
                'market': market,
                'direction': 'BUY' if signal > 0 else 'SELL',
                'entry_price': entry_price,
                'size': size,
                'stop_loss': entry_price - params['stop_loss'] if signal > 0 else entry_price + params['stop_loss'],
                'take_profit': entry_price + params['take_profit'] if signal > 0 else entry_price - params['take_profit'],
                'entry_time': timestamp,
                'confidence': confidence
            }
            self.positions[market] = position
            self.trade_count += 1
    
    def check_exits(self, market: str, bid: float, offer: float, timestamp: pd.Timestamp):
        """Check if position should be closed"""
        if market not in self.positions:
            return
            
        position = self.positions[market]
        
        # Use bid for selling (closing longs), offer for buying (closing shorts)
        if position['direction'] == 'BUY':
            exit_price = bid
            if exit_price <= position['stop_loss'] or exit_price >= position['take_profit']:
                # Close position
                pnl = (exit_price - position['entry_price']) * position['size']
                self.balance += pnl
                self.daily_loss += min(0, pnl)
                
                # Track consecutive losses
                if pnl < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0
                
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
                
                del self.positions[market]
        
        elif position['direction'] == 'SELL':
            exit_price = offer
            if exit_price >= position['stop_loss'] or exit_price <= position['take_profit']:
                # Close position
                pnl = (position['entry_price'] - exit_price) * position['size']
                self.balance += pnl
                self.daily_loss += min(0, pnl)
                
                # Track consecutive losses
                if pnl < 0:
                    self.consecutive_losses += 1
                else:
                    self.consecutive_losses = 0
                
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
                
                del self.positions[market]
    
    def run_backtest(self, ftse_file: str, dax_file: str) -> Dict:
        """Run backtest and return results"""
        # Load data
        ftse_df = self.load_tick_data(ftse_file)
        dax_df = self.load_tick_data(dax_file)
        
        # Generate signals
        ftse_df = self.generate_signals(ftse_df)
        dax_df = self.generate_signals(dax_df)
        
        # Sample based on profile
        if self.profile_name == 'scalping':
            sample_rate = 100  # More frequent for scalping
        elif self.profile_name == 'conservative':
            sample_rate = 500  # Less frequent for conservative
        elif self.profile_name == 'aggressive':
            sample_rate = 200
        else:
            sample_rate = 300
        
        ftse_sample = ftse_df.iloc[::sample_rate].copy()
        dax_sample = dax_df.iloc[::sample_rate].copy()
        
        # Combine and sort
        ftse_sample['market'] = 'FTSE 100'
        dax_sample['market'] = 'DAX'
        
        all_ticks = pd.concat([ftse_sample, dax_sample])
        all_ticks = all_ticks.sort_values('timestamp')
        
        # Process each tick
        for idx, row in all_ticks.iterrows():
            market = row['market']
            bid = row['bid']
            offer = row['offer']
            price = row['midprice']
            timestamp = row['timestamp']
            signal = row['signal']
            confidence = row.get('confidence', 0.5)
            spread = offer - bid
            
            # Check exits first
            self.check_exits(market, bid, offer, timestamp)
            
            # Then check for new entries
            if pd.notna(signal):
                self.execute_trade(market, signal, price, timestamp, spread, confidence)
        
        # Close remaining positions
        for market in list(self.positions.keys()):
            if market == 'FTSE 100':
                last_bid = ftse_sample.iloc[-1]['bid']
                last_offer = ftse_sample.iloc[-1]['offer']
            else:
                last_bid = dax_sample.iloc[-1]['bid']
                last_offer = dax_sample.iloc[-1]['offer']
            self.check_exits(market, last_bid, last_offer, all_ticks.iloc[-1]['timestamp'])
        
        # Calculate results
        total_trades = len(self.trades)
        if total_trades == 0:
            return {
                'profile': self.profile_name,
                'total_trades': 0,
                'total_pnl': 0,
                'return_pct': 0,
                'win_rate': 0,
                'max_drawdown': 0,
                'avg_trade_duration': 0
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = (len(winning_trades) / total_trades) * 100
        avg_duration = sum(t['duration'] for t in self.trades) / total_trades
        
        return {
            'profile': self.profile_name,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'return_pct': (self.balance - self.initial_balance) / self.initial_balance * 100,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown,
            'avg_trade_duration': avg_duration,
            'final_balance': self.balance
        }

def compare_all_profiles():
    """Compare all profile configurations"""
    profiles = [
        'configs/profiles/scalping.yaml',
        'configs/profiles/conservative.yaml',
        'configs/profiles/aggressive.yaml',
        'configs/simplified_trading.yaml'
    ]
    
    results = []
    
    print("="*70)
    print("🎯 PROFILE COMPARISON BACKTEST - Today's Data (08/18)")
    print("="*70)
    print("\nTesting all profile configurations...\n")
    
    for profile_path in profiles:
        profile_name = profile_path.split('/')[-1].replace('.yaml', '')
        print(f"📊 Testing {profile_name} profile...")
        
        try:
            tester = ProfileBacktester(profile_path)
            result = tester.run_backtest(
                'tick_ftse_100_08_18.json',
                'tick_dax_08_18.json'
            )
            result['profile'] = profile_name
            results.append(result)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Display results comparison
    print("\n" + "="*70)
    print("📊 BACKTEST RESULTS COMPARISON")
    print("="*70)
    
    # Sort by P&L
    results.sort(key=lambda x: x['total_pnl'], reverse=True)
    
    print(f"\n{'Profile':<15} {'Trades':<10} {'P&L':<12} {'Return':<10} {'Win Rate':<10} {'Max DD':<10} {'Avg Duration':<12}")
    print("-"*90)
    
    for result in results:
        print(f"{result['profile']:<15} {result['total_trades']:<10} "
              f"£{result['total_pnl']:>+10.2f} {result['return_pct']:>8.2f}% "
              f"{result['win_rate']:>8.1f}% {result['max_drawdown']:>8.2f}% "
              f"{result['avg_trade_duration']:>10.1f} min")
    
    # Find best configuration
    print("\n" + "="*70)
    print("🏆 BEST CONFIGURATION ANALYSIS")
    print("="*70)
    
    if results:
        best_pnl = max(results, key=lambda x: x['total_pnl'])
        best_return = max(results, key=lambda x: x['return_pct'])
        best_winrate = max(results, key=lambda x: x['win_rate'])
        lowest_dd = min(results, key=lambda x: x['max_drawdown'])
        
        print(f"\n💰 Best P&L:        {best_pnl['profile']} with £{best_pnl['total_pnl']:+.2f}")
        print(f"📈 Best Return:     {best_return['profile']} with {best_return['return_pct']:+.2f}%")
        print(f"🎯 Best Win Rate:   {best_winrate['profile']} with {best_winrate['win_rate']:.1f}%")
        print(f"🛡️ Lowest Drawdown: {lowest_dd['profile']} with {lowest_dd['max_drawdown']:.2f}%")
        
        # Overall recommendation
        print("\n" + "="*70)
        print("💡 RECOMMENDATION")
        print("="*70)
        
        # Score each profile
        for result in results:
            score = 0
            if result['total_pnl'] > 0:
                score += 3
            if result['win_rate'] > 45:
                score += 2
            if result['max_drawdown'] < 5:
                score += 2
            if result['total_trades'] > 10:
                score += 1
            result['score'] = score
        
        best_overall = max(results, key=lambda x: x['score'])
        
        print(f"\n✅ Best Overall Configuration: {best_overall['profile'].upper()}")
        print(f"   - P&L: £{best_overall['total_pnl']:+.2f}")
        print(f"   - Return: {best_overall['return_pct']:+.2f}%")
        print(f"   - Win Rate: {best_overall['win_rate']:.1f}%")
        print(f"   - Max Drawdown: {best_overall['max_drawdown']:.2f}%")
        print(f"   - Total Trades: {best_overall['total_trades']}")
        print(f"   - Avg Trade Duration: {best_overall['avg_trade_duration']:.1f} minutes")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    compare_all_profiles()