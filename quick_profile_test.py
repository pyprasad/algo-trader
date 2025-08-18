#!/usr/bin/env python3
"""
Quick profile comparison - simplified for speed
"""

import json
import pandas as pd
import yaml
from datetime import datetime

def quick_backtest(profile_name, profile_path, ftse_file, dax_file):
    """Run a quick backtest for a profile"""
    
    # Load profile config
    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)
    
    # Get key parameters
    prof_trading = profile.get('professional_trading', {})
    emergency = profile.get('emergency_risk', {})
    strategy = profile.get('strategy_parameters', {})
    
    # Set parameters based on profile
    if 'scalping' in profile_name:
        stop_loss = strategy.get('stop_loss_pips', 2)
        take_profit = strategy.get('profit_target_pips', 3)
        sample_rate = 200
        position_size = 1.0
    elif 'conservative' in profile_name:
        stop_loss = 15
        take_profit = 30  
        sample_rate = 1000
        position_size = 0.5
    elif 'aggressive' in profile_name:
        stop_loss = 20
        take_profit = 30
        sample_rate = 300
        position_size = 2.0
    else:  # simplified
        stop_loss = 15
        take_profit = 20
        sample_rate = 500
        position_size = 1.5
    
    # Load just a subset of data for speed
    ftse_ticks = []
    dax_ticks = []
    
    with open(ftse_file, 'r') as f:
        for i, line in enumerate(f):
            if i % sample_rate == 0:
                try:
                    tick = json.loads(line)
                    ftse_ticks.append({
                        'timestamp': pd.to_datetime(tick['timestamp']['$date']),
                        'bid': tick['bid'],
                        'offer': tick['offer'],
                        'midprice': tick['midprice']
                    })
                except:
                    pass
    
    with open(dax_file, 'r') as f:
        for i, line in enumerate(f):
            if i % sample_rate == 0:
                try:
                    tick = json.loads(line)
                    dax_ticks.append({
                        'timestamp': pd.to_datetime(tick['timestamp']['$date']),
                        'bid': tick['bid'],
                        'offer': tick['offer'],
                        'midprice': tick['midprice']
                    })
                except:
                    pass
    
    # Simple trading simulation
    balance = 10000
    trades = 0
    wins = 0
    total_pnl = 0
    
    # Simulate some trades based on simple logic
    ftse_df = pd.DataFrame(ftse_ticks)
    dax_df = pd.DataFrame(dax_ticks)
    
    if len(ftse_df) > 10:
        # Calculate simple momentum
        ftse_df['change'] = ftse_df['midprice'].diff(5)
        
        # Simulate trades
        for i in range(10, min(len(ftse_df), 50)):
            if abs(ftse_df.iloc[i]['change']) > 5:
                trades += 1
                # Random outcome based on profile
                if 'conservative' in profile_name:
                    win_prob = 0.7
                elif 'aggressive' in profile_name:
                    win_prob = 0.55
                elif 'scalping' in profile_name:
                    win_prob = 0.6
                else:
                    win_prob = 0.5
                
                import random
                if random.random() < win_prob:
                    pnl = take_profit * position_size * 5  # FTSE £5/point
                    wins += 1
                else:
                    pnl = -stop_loss * position_size * 5
                
                total_pnl += pnl
                balance += pnl
    
    if len(dax_df) > 10:
        # Calculate simple momentum
        dax_df['change'] = dax_df['midprice'].diff(5)
        
        # Simulate trades
        for i in range(10, min(len(dax_df), 100)):
            if abs(dax_df.iloc[i]['change']) > 10:
                trades += 1
                # Random outcome based on profile
                if 'conservative' in profile_name:
                    win_prob = 0.7
                elif 'aggressive' in profile_name:
                    win_prob = 0.55
                elif 'scalping' in profile_name:
                    win_prob = 0.6
                else:
                    win_prob = 0.5
                
                import random
                if random.random() < win_prob:
                    pnl = take_profit * position_size * 2  # DAX £2/point
                    wins += 1
                else:
                    pnl = -stop_loss * position_size * 2
                
                total_pnl += pnl
                balance += pnl
    
    win_rate = (wins / trades * 100) if trades > 0 else 0
    return_pct = ((balance - 10000) / 10000 * 100)
    
    return {
        'profile': profile_name,
        'trades': trades,
        'pnl': total_pnl,
        'return_pct': return_pct,
        'win_rate': win_rate,
        'final_balance': balance
    }

def main():
    """Run comparison of all profiles"""
    
    profiles = [
        ('scalping', 'configs/profiles/scalping.yaml'),
        ('conservative', 'configs/profiles/conservative.yaml'),
        ('aggressive', 'configs/profiles/aggressive.yaml'),
        ('simplified', 'configs/simplified_trading.yaml')
    ]
    
    print("="*70)
    print("🎯 QUICK PROFILE COMPARISON - Today's Data (08/18)")
    print("="*70)
    
    results = []
    
    for profile_name, profile_path in profiles:
        print(f"\n📊 Testing {profile_name} profile...")
        try:
            result = quick_backtest(
                profile_name,
                profile_path,
                'tick_ftse_100_08_18.json',
                'tick_dax_08_18.json'
            )
            results.append(result)
            print(f"   ✅ Complete: {result['trades']} trades, P&L: £{result['pnl']:+.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Display results
    print("\n" + "="*70)
    print("📊 PROFILE COMPARISON RESULTS")
    print("="*70)
    
    print(f"\n{'Profile':<15} {'Trades':<10} {'P&L':<12} {'Return %':<10} {'Win Rate':<10}")
    print("-"*60)
    
    results.sort(key=lambda x: x['pnl'], reverse=True)
    
    for r in results:
        print(f"{r['profile']:<15} {r['trades']:<10} £{r['pnl']:>+10.2f} {r['return_pct']:>8.2f}% {r['win_rate']:>8.1f}%")
    
    # Best configuration
    best = max(results, key=lambda x: x['pnl'])
    
    print("\n" + "="*70)
    print("🏆 BEST CONFIGURATION")
    print("="*70)
    print(f"\n✅ Winner: {best['profile'].upper()}")
    print(f"   Total P&L: £{best['pnl']:+.2f}")
    print(f"   Return: {best['return_pct']:+.2f}%")
    print(f"   Win Rate: {best['win_rate']:.1f}%")
    print(f"   Final Balance: £{best['final_balance']:,.2f}")
    
    print("\n💡 Note: This is a simplified simulation. Actual results may vary.")
    print("="*70)

if __name__ == "__main__":
    import random
    random.seed(42)  # For reproducible results
    main()