#!/usr/bin/env python3.12
# optimized_backtest.py - Test with discovered optimal parameters

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
import argparse

sys.path.append('.')
from core.candle_aggregator import CandleAggregator
from core.enhanced_strategies import EnhancedTradingStrategies

def optimized_backtest(data_file, strategy='optimized_rsi'):
    """Test with optimized parameters discovered through systematic optimization"""
    
    print(f"🏆 OPTIMIZED BACKTEST - {data_file}")
    print("="*60)
    print("✅ DISCOVERED OPTIMAL PARAMETERS:")
    print("✅ RSI Buy: 60 (contrarian - buy overbought)")
    print("✅ RSI Sell: 40 (contrarian - sell oversold)")
    print("✅ Stop Loss: 12 pips (tight control)")
    print("✅ Take Profit: 25 pips (2:1 risk/reward)")
    print("✅ 0.5% position sizing (FIXED)")
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
    
    # Apply OPTIMIZED RSI strategy with discovered parameters
    if strategy == 'optimized_rsi':
        strategy_df = strategies.rsi_trend_strategy(candles, {
            'rsi_period': 14,
            'rsi_overbought': 60,       # CONTRARIAN - sell when above 60
            'rsi_oversold': 40,         # CONTRARIAN - buy when below 40
            'trend_ema': 50,            # EMA for trend filter
            'stop_loss_pips': 12,       # Tight stops
            'take_profit_pips': 25      # Good risk/reward
        })
    else:
        # Fallback to MA crossover
        strategy_df = strategies.ma_crossover_strategy(candles, {
            'fast_ma': 8,
            'slow_ma': 21,
            'stop_loss_pips': 12,
            'take_profit_pips': 25
        })
    
    # Enhanced simulation
    balance = 10000.0
    position = None
    trades = []
    
    print(f"\n📈 RUNNING OPTIMIZED SIMULATION...")
    print("Starting Balance: £10,000")
    print("Strategy: Contrarian RSI with tight risk management")
    
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
                # Calculate CORRECT P&L with 0.5% position sizing (FIXED)
                position_value = balance * 0.005  # 0.5% position
                
                if position['direction'] == 'BUY':
                    price_change = exit_price - position['entry_price']
                else:
                    price_change = position['entry_price'] - exit_price
                
                # Correct P&L calculation
                pnl = (price_change / position['entry_price']) * position_value - 2.0
                
                balance += pnl
                
                trade = {
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'balance': balance,
                    'rsi_entry': candle.get('rsi', 0)
                }
                
                trades.append(trade)
                
                print(f"🔚 TRADE CLOSED:")
                print(f"   {position['direction']} £{position['entry_price']:.2f} → £{exit_price:.2f}")
                print(f"   P&L: £{pnl:+.2f} | Reason: {exit_reason}")
                print(f"   Balance: £{balance:.2f} | RSI: {candle.get('rsi', 0):.1f}")
                
                position = None
        
        # Check for new entry using OPTIMIZED signals
        if not position and candle['signal'] in ['BUY', 'SELL']:
            
            # Enhanced filters for optimized strategy
            rsi = candle.get('rsi', 50)
            atr = candle.get('atr', 0)
            spread = candle.get('spread', 0)
            
            # Quality filters
            can_trade = True
            if len(trades) >= 10:  # Limit trades for analysis
                can_trade = False
            if atr < 3.0:  # Minimum volatility
                can_trade = False
            if spread > 5.0:  # Maximum spread
                can_trade = False
            
            # RSI confirmation for contrarian strategy
            if candle['signal'] == 'BUY' and rsi < 55:  # Need overbought for contrarian buy
                can_trade = False
            if candle['signal'] == 'SELL' and rsi > 45:  # Need oversold for contrarian sell
                can_trade = False
            
            if can_trade:
                if candle['signal'] == 'BUY':
                    entry_price = candle.get('offer_close', candle['close'])
                    stop_loss = entry_price - 12  # 12 pip stop
                    take_profit = entry_price + 25  # 25 pip target
                else:  # SELL
                    entry_price = candle.get('bid_close', candle['close'])
                    stop_loss = entry_price + 12
                    take_profit = entry_price - 25
                
                position = {
                    'direction': candle['signal'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                print(f"📈 OPTIMIZED TRADE OPENED:")
                print(f"   {candle['signal']} £{entry_price:.2f} (RSI: {rsi:.1f})")
                print(f"   SL: £{stop_loss:.2f} | TP: £{take_profit:.2f}")
                print(f"   Strategy: Contrarian RSI")
    
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
    
    # Enhanced Results Analysis
    print(f"\n" + "="*60)
    print("🏆 OPTIMIZED STRATEGY RESULTS")
    print("="*60)
    
    if trades:
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(wins) / len(trades) * 100
        avg_win = sum(w['pnl'] for w in wins) / len(wins) if wins else 0
        avg_loss = sum(l['pnl'] for l in losses) / len(losses) if losses else 0
        
        # Risk metrics
        profit_factor = abs(sum(w['pnl'] for w in wins) / sum(l['pnl'] for l in losses)) if losses else float('inf')
        max_drawdown = min(t['balance'] for t in trades) - 10000
        
        print(f"🎯 OPTIMIZED PERFORMANCE:")
        print(f"   Strategy: Contrarian RSI (60/40 thresholds)")
        print(f"   Total Trades: {len(trades)}")
        print(f"   Total P&L: £{total_pnl:+.2f}")
        print(f"   Final Balance: £{balance:.2f}")
        print(f"   Return: {(balance-10000)/10000*100:+.2f}%")
        print(f"   Win Rate: {win_rate:.1f}% ({len(wins)}/{len(trades)})")
        print(f"   Average Win: £{avg_win:+.2f}")
        print(f"   Average Loss: £{avg_loss:+.2f}")
        print(f"   Profit Factor: {profit_factor:.2f}")
        print(f"   Max Drawdown: £{max_drawdown:+.2f}")
        
        print(f"\n📋 DETAILED TRADE LOG:")
        for i, trade in enumerate(trades, 1):
            rsi_info = f"RSI: {trade.get('rsi_entry', 'N/A'):.1f}" if 'rsi_entry' in trade else ""
            print(f"   {i}. {trade['direction']} | "
                  f"£{trade['entry_price']:.2f}→£{trade['exit_price']:.2f} | "
                  f"P&L: £{trade['pnl']:+.2f} | {trade['exit_reason']} | {rsi_info}")
        
        # Strategy Assessment
        if total_pnl > 0 and win_rate >= 40:
            print(f"\n✅ OPTIMIZED STRATEGY SUCCESSFUL!")
            print(f"   Contrarian RSI approach shows promise")
            if profit_factor > 2.0:
                print(f"   Excellent profit factor: {profit_factor:.2f}")
        elif total_pnl > 0:
            print(f"\n⚠️  MARGINAL IMPROVEMENT")
            print(f"   Profitable but needs refinement")
        else:
            print(f"\n📊 STRATEGY ANALYSIS:")
            print(f"   Market conditions may not suit contrarian approach")
            print(f"   Consider trending vs ranging market detection")
    else:
        print("❌ No trades executed - signals too restrictive or insufficient volatility")
    
    print("="*60)
    return trades

def main():
    parser = argparse.ArgumentParser(description='Optimized Strategy Backtesting')
    parser.add_argument('data_file', help='Tick data file to backtest')
    parser.add_argument('--strategy', choices=['optimized_rsi', 'ma_crossover'], 
                       default='optimized_rsi', help='Strategy to test')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_file):
        print(f"❌ File not found: {args.data_file}")
        return
    
    optimized_backtest(args.data_file, args.strategy)

if __name__ == "__main__":
    main()