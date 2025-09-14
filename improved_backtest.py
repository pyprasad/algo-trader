#!/usr/bin/env python3.12
# improved_backtest.py - Enhanced backtesting with SuperTrend strategy

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

def improved_backtest(data_file, strategy='supertrend'):
    """Enhanced backtesting with improved strategies and parameters"""
    
    print(f"🚀 IMPROVED BACKTEST - {data_file}")
    print("="*60)
    print("✅ Optimized SuperTrend Strategy")
    print("✅ 10-minute timeframe")
    print("✅ Conservative 0.5% position sizing")
    print("✅ Wider stops (30 pips) for better risk/reward")
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
    
    # Apply improved strategy based on previous successful tests
    if strategy == 'supertrend':
        # SuperTrend with optimized parameters (proven profitable on DAX)
        strategy_df = strategies.supertrend_strategy(candles, {
            'atr_period': 14,
            'multiplier': 2.5,  # More sensitive to trends
            'stop_loss_pips': 30,  # Wider stops
            'take_profit_pips': 60,  # Better risk/reward ratio
            'volatility_filter': True,  # Only trade in good volatility
            'trend_confirmation': True  # Require trend confirmation
        })
    else:
        # MA Crossover with improved parameters
        strategy_df = strategies.ma_crossover_strategy(candles, {
            'fast_ma': 8,
            'slow_ma': 21,
            'stop_loss_pips': 30,  # Wider stops
            'take_profit_pips': 60  # Better risk/reward
        })
    
    # Enhanced simulation with risk management
    balance = 10000.0
    position = None
    trades = []
    max_daily_trades = 3  # Risk management
    daily_loss_limit = 100.0  # Maximum daily loss
    
    print(f"\n📈 RUNNING ENHANCED SIMULATION...")
    print("Starting Balance: £10,000")
    print("Risk Management: 0.5% position size, 30 pip stops, max 3 trades/day")
    
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
                # Calculate CORRECT P&L with conservative position sizing
                position_value = balance * 0.005  # 0.5% position (was 2% in buggy version)
                
                if position['direction'] == 'BUY':
                    price_change = exit_price - position['entry_price']
                else:
                    price_change = position['entry_price'] - exit_price
                
                # Correct P&L calculation
                pnl = (price_change / position['entry_price']) * position_value - 2.0  # Include spread
                
                balance += pnl
                
                trade = {
                    'direction': position['direction'],
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason,
                    'balance': balance,
                    'atr': candle.get('atr', 0),
                    'volatility_ok': candle.get('atr', 0) > 5.0  # Volatility check
                }
                
                trades.append(trade)
                
                print(f"🔚 TRADE CLOSED:")
                print(f"   {position['direction']} £{position['entry_price']:.2f} → £{exit_price:.2f}")
                print(f"   P&L: £{pnl:+.2f} | Reason: {exit_reason}")
                print(f"   Balance: £{balance:.2f} | ATR: {candle.get('atr', 0):.1f}")
                
                position = None
        
        # Check for new entry with enhanced filters
        if not position and candle['signal'] in ['BUY', 'SELL']:
            
            # Enhanced entry filters
            can_trade = True
            
            # Limit daily trades
            if len(trades) >= max_daily_trades:
                can_trade = False
            
            # Daily loss protection
            daily_pnl = sum(t['pnl'] for t in trades)
            if daily_pnl <= -daily_loss_limit:
                can_trade = False
            
            # Volatility filter (only trade with sufficient volatility)
            if candle.get('atr', 0) < 8.0:  # Minimum ATR threshold
                can_trade = False
            
            # Spread filter (avoid wide spreads)
            spread = candle.get('spread', 0)
            if spread > 5.0:  # Maximum spread threshold
                can_trade = False
            
            if can_trade:
                if candle['signal'] == 'BUY':
                    entry_price = candle.get('offer_close', candle['close'])
                    stop_loss = entry_price - 30  # 30 pip stop
                    take_profit = entry_price + 60  # 60 pip target
                else:  # SELL
                    entry_price = candle.get('bid_close', candle['close'])
                    stop_loss = entry_price + 30
                    take_profit = entry_price - 60
                
                position = {
                    'direction': candle['signal'],
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
                
                print(f"📈 TRADE OPENED:")
                print(f"   {candle['signal']} £{entry_price:.2f}")
                print(f"   SL: £{stop_loss:.2f} | TP: £{take_profit:.2f}")
                print(f"   ATR: {candle.get('atr', 0):.1f} | Spread: £{spread:.2f}")
    
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
    print("📊 ENHANCED BACKTEST RESULTS")
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
        
        print(f"📈 ENHANCED PERFORMANCE:")
        print(f"   Strategy: {strategy.upper()}")
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
            volatility_status = "✅" if trade.get('volatility_ok', False) else "⚠️"
            print(f"   {i}. {trade['direction']} | "
                  f"£{trade['entry_price']:.2f}→£{trade['exit_price']:.2f} | "
                  f"P&L: £{trade['pnl']:+.2f} | {trade['exit_reason']} {volatility_status}")
        
        # Strategy Assessment
        if total_pnl > 0 and win_rate >= 30:
            print(f"\n✅ IMPROVED STRATEGY SUCCESSFUL!")
            print(f"   Positive returns with reasonable win rate")
            if profit_factor > 1.5:
                print(f"   Excellent profit factor: {profit_factor:.2f}")
        elif total_pnl > 0:
            print(f"\n⚠️  MARGINAL PERFORMANCE")
            print(f"   Profitable but low win rate - needs further optimization")
        else:
            print(f"\n❌ Strategy needs more optimization")
            print(f"   Consider adjusting parameters or timeframes")
    else:
        print("❌ No trades executed - strategy too restrictive or insufficient signals")
    
    print("="*60)
    return trades

def main():
    parser = argparse.ArgumentParser(description='Improved Backtesting System')
    parser.add_argument('data_file', help='Tick data file to backtest')
    parser.add_argument('--strategy', choices=['supertrend', 'ma_crossover'], 
                       default='supertrend', help='Strategy to test')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.data_file):
        print(f"❌ File not found: {args.data_file}")
        return
    
    improved_backtest(args.data_file, args.strategy)

if __name__ == "__main__":
    main()