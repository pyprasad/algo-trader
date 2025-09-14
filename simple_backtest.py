#!/usr/bin/env python3.12
# simple_backtest.py - Correct backtesting with proper P&L calculation

import sys
import os
import json
import pandas as pd
from datetime import datetime
import argparse

sys.path.append('.')
from core.candle_aggregator import CandleAggregator
from core.enhanced_strategies import EnhancedTradingStrategies

def simple_backtest(data_file):
    """Simple, correct backtesting"""
    
    print(f"🔧 SIMPLE BACKTEST - {data_file}")
    print("="*60)
    print("✅ CORRECT Position Sizing & P&L Calculation")
    print("✅ 10-minute timeframe")
    print("✅ MA Crossover strategy")
    print("="*60)
    
    # Initialize components
    aggregator = CandleAggregator()
    strategies = EnhancedTradingStrategies()
    
    # Load tick data
    ticks = []
    try:
        with open(data_file, 'r') as f:
            for i, line in enumerate(f):
                if i > 100000:  # Reasonable limit
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
            return
            
        print(f"📊 Loaded {len(ticks)} ticks")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Convert to DataFrame and create candles
    tick_df = pd.DataFrame(ticks).sort_values('timestamp')
    candles = aggregator.ticks_to_candles(tick_df, '10T')  # 10-minute candles
    candles = aggregator.add_volatility_filter(candles)
    
    print(f"📊 Generated {len(candles)} candles")
    
    if len(candles) < 50:
        print("❌ Insufficient candles for backtesting")
        return
    
    # Apply MA crossover strategy
    strategy_df = strategies.ma_crossover_strategy(candles, {
        'fast_ma': 5,
        'slow_ma': 20,
        'stop_loss_pips': 25,  # Wider stops
        'take_profit_pips': 50  # Better risk/reward
    })
    
    # Run simulation
    balance = 10000.0
    position = None
    trades = []
    
    print(f"\n📈 RUNNING SIMULATION...")
    print("Starting Balance: £10,000")
    
    for i, (_, candle) in enumerate(strategy_df.iterrows()):
        
        # Check for exit first
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
                # Calculate CORRECT P&L
                position_value = balance * 0.005  # 0.5% position
                
                if position['direction'] == 'BUY':
                    price_change = exit_price - position['entry_price']
                else:
                    price_change = position['entry_price'] - exit_price
                
                # P&L = (price change / entry price) * position value - spread
                pnl = (price_change / position['entry_price']) * position_value - 2.0
                
                balance += pnl
                
                trade = {
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'balance': balance
                }
                
                trades.append(trade)
                
                print(f"🔚 TRADE CLOSED:")
                print(f"   {position['direction']} £{position['entry_price']:.2f} → £{exit_price:.2f}")
                print(f"   P&L: £{pnl:+.2f} | Reason: {exit_reason}")
                print(f"   Balance: £{balance:.2f}")
                
                position = None
        
        # Check for new entry
        if not position and candle['signal'] in ['BUY', 'SELL']:
            
            if candle['signal'] == 'BUY':
                entry_price = candle.get('offer_close', candle['close'])
                stop_loss = entry_price - 25  # 25 pip stop
                take_profit = entry_price + 50  # 50 pip target
            else:  # SELL
                entry_price = candle.get('bid_close', candle['close'])
                stop_loss = entry_price + 25
                take_profit = entry_price - 50
            
            position = {
                'direction': candle['signal'],
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
            
            print(f"📈 TRADE OPENED:")
            print(f"   {candle['signal']} £{entry_price:.2f}")
            print(f"   SL: £{stop_loss:.2f} | TP: £{take_profit:.2f}")
    
    # Close any remaining position
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
            'exit_reason': 'END_OF_DATA',
            'balance': balance
        })
        
        print(f"🔚 FINAL POSITION CLOSED: P&L £{pnl:+.2f}")
    
    # Results
    print(f"\n" + "="*60)
    print("📊 BACKTEST RESULTS")
    print("="*60)
    
    if trades:
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100
        avg_win = sum(w['pnl'] for w in wins) / len(wins) if wins else 0
        avg_loss = sum(l['pnl'] for l in losses) / len(losses) if losses else 0
        
        print(f"📈 PERFORMANCE:")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Total P&L: £{total_pnl:+.2f}")
        print(f"   Final Balance: £{balance:.2f}")
        print(f"   Return: {(balance-10000)/10000*100:+.2f}%")
        print(f"   Win Rate: {win_rate:.1f}% ({len(wins)}/{len(trades)})")
        print(f"   Average Win: £{avg_win:+.2f}")
        print(f"   Average Loss: £{avg_loss:+.2f}")
        
        print(f"\n📋 TRADE DETAILS:")
        for i, trade in enumerate(trades, 1):
            print(f"   {i}. {trade['direction']} | "
                  f"£{trade['entry_price']:.2f}→£{trade['exit_price']:.2f} | "
                  f"P&L: £{trade['pnl']:+.2f} | {trade['exit_reason']}")
        
        if total_pnl > 0:
            print(f"\n✅ PROFITABLE STRATEGY!")
        else:
            print(f"\n❌ Strategy needs optimization")
    else:
        print("❌ No trades executed")
    
    print("="*60)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3.12 simple_backtest.py <data_file>")
        return
    
    simple_backtest(sys.argv[1])

if __name__ == "__main__":
    main()