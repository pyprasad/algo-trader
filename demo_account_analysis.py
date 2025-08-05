#!/usr/bin/env python3
"""
Demo Account Performance Analysis
Analyzes actual trading results from IG demo account
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

def analyze_demo_performance():
    """Analyze demo account transaction history"""
    
    # Load the transaction history
    df = pd.read_csv('TransactionHistory-Z5VPHI-(04-08-2025)-(05-08-2025).csv')
    
    print("=== DEMO ACCOUNT PERFORMANCE ANALYSIS ===")
    print(f"Total records: {len(df)}")
    print(f"Date range: {df['TextDate'].min()} to {df['TextDate'].max()}")
    print()
    
    # Filter only actual trades (exclude interest payments)
    trades = df[df['Transaction type'] == 'DEAL'].copy()
    print(f"Total trades executed: {len(trades)}")
    
    if len(trades) == 0:
        print("No trades found in the data!")
        return
    
    # Clean P&L data - remove currency symbols and convert to float
    trades['PnL_numeric'] = trades['ProfitAndLoss'].str.replace('£', '').str.replace(',', '').astype(float)
    
    # Analyze by market
    print("\n=== MARKET BREAKDOWN ===")
    for market in trades['MarketName'].unique():
        market_trades = trades[trades['MarketName'] == market]
        total_pnl = market_trades['PnL_numeric'].sum()
        trade_count = len(market_trades)
        win_rate = (market_trades['PnL_numeric'] > 0).mean() * 100
        avg_pnl = market_trades['PnL_numeric'].mean()
        
        print(f"{market}:")
        print(f"  Trades: {trade_count}")
        print(f"  Total P&L: £{total_pnl:.2f}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Avg P&L per trade: £{avg_pnl:.2f}")
        print()
    
    # Overall performance metrics
    pnl_values = trades['PnL_numeric']
    total_pnl = pnl_values.sum()
    total_trades = len(trades)
    wins = (pnl_values > 0).sum()
    losses = (pnl_values < 0).sum()
    win_rate = (wins / total_trades) * 100
    
    print("=== OVERALL PERFORMANCE ===")
    print(f"Total P&L: £{total_pnl:.2f}")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {wins}")
    print(f"Losing Trades: {losses}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Average P&L per trade: £{total_pnl/total_trades:.2f}")
    print(f"Largest Win: £{pnl_values.max():.2f}")
    print(f"Largest Loss: £{pnl_values.min():.2f}")
    
    # Calculate additional metrics
    winning_trades = pnl_values[pnl_values > 0]
    losing_trades = pnl_values[pnl_values < 0]
    
    if len(winning_trades) > 0 and len(losing_trades) > 0:
        avg_win = winning_trades.mean()
        avg_loss = losing_trades.mean()
        profit_factor = winning_trades.sum() / abs(losing_trades.sum())
        
        print(f"Average Win: £{avg_win:.2f}")
        print(f"Average Loss: £{avg_loss:.2f}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Risk/Reward Ratio: {abs(avg_loss)/avg_win:.2f}")
    
    # Trading frequency analysis
    trades['DateUtc_parsed'] = pd.to_datetime(trades['DateUtc'])
    trades_by_hour = trades.groupby(trades['DateUtc_parsed'].dt.hour).size()
    
    print("\n=== TRADING FREQUENCY BY HOUR ===")
    for hour, count in trades_by_hour.items():
        print(f"Hour {hour:02d}: {count} trades")
    
    print("\n=== RECENT TRADES SAMPLE ===")
    sample_trades = trades[['TextDate', 'MarketName', 'ProfitAndLoss', 'Open level', 'Close level', 'Size']].head(10)
    print(sample_trades.to_string(index=False))
    
    # Return summary for further analysis
    return {
        'total_pnl': total_pnl,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor if len(winning_trades) > 0 and len(losing_trades) > 0 else 0,
        'avg_win': avg_win if len(winning_trades) > 0 else 0,
        'avg_loss': avg_loss if len(losing_trades) > 0 else 0,
        'market_breakdown': trades.groupby('MarketName')['PnL_numeric'].agg(['count', 'sum', 'mean']).to_dict()
    }

if __name__ == "__main__":
    summary = analyze_demo_performance()
    print(f"\n=== SUMMARY FOR BACKTEST COMPARISON ===")
    print(f"Demo account achieved £{summary['total_pnl']:.2f} across {summary['total_trades']} trades")
    print(f"Target for backtest: Beat {summary['win_rate']:.1f}% win rate and £{summary['total_pnl']:.2f} total return")