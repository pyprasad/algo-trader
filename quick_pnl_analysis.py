# quick_pnl_analysis.py

"""Quick P&L Analysis for DAX and FTSE"""

import sys
import os
sys.path.append('/Users/my/mayu_solutions/algo-trader')

from backtest_engine import BacktestEngine
from datetime import datetime

def run_quick_analysis():
    print('🎯 COMPREHENSIVE P&L ANALYSIS')
    print('=' * 50)
    print(f'Started: {datetime.now().strftime("%H:%M:%S")}')
    print()
    
    engine = BacktestEngine()
    
    markets = ["DAX", "FTSE 100"]
    results = {}
    
    for market in markets:
        print(f'📈 ANALYZING {market}')
        print('-' * 30)
        
        market_results = {}
        
        # Original Strategy
        print(f'1️⃣ Running Original Strategy for {market}...')
        original_params = engine.get_original_strategy_params(market)
        original_trades = engine.run_backtest(market, original_params)
        original_metrics = engine.calculate_metrics(original_trades, 'Original', market)
        
        market_results['original'] = {
            'trades': len(original_trades),
            'win_rate': original_metrics.win_rate,
            'total_pnl': original_metrics.total_pnl,
            'max_drawdown': original_metrics.max_drawdown,
            'profit_factor': original_metrics.profit_factor
        }
        
        print(f'   Original Results: {original_metrics.total_trades} trades, {original_metrics.win_rate:.1f}% win rate, £{original_metrics.total_pnl:.2f} P&L')
        
        # Adaptive Strategy
        print(f'2️⃣ Running Adaptive Strategy for {market}...')
        adaptive_params = engine.get_adaptive_strategy_params(market)
        adaptive_trades = engine.run_backtest(market, adaptive_params)
        adaptive_metrics = engine.calculate_metrics(adaptive_trades, 'Adaptive', market)
        
        market_results['adaptive'] = {
            'trades': len(adaptive_trades),
            'win_rate': adaptive_metrics.win_rate,
            'total_pnl': adaptive_metrics.total_pnl,
            'max_drawdown': adaptive_metrics.max_drawdown,
            'profit_factor': adaptive_metrics.profit_factor
        }
        
        print(f'   Adaptive Results: {adaptive_metrics.total_trades} trades, {adaptive_metrics.win_rate:.1f}% win rate, £{adaptive_metrics.total_pnl:.2f} P&L')
        
        # Comparison
        improvement = adaptive_metrics.total_pnl - original_metrics.total_pnl
        win_rate_change = adaptive_metrics.win_rate - original_metrics.win_rate
        trade_change = adaptive_metrics.total_trades - original_metrics.total_trades
        
        print(f'🎯 {market} IMPROVEMENT:')
        print(f'   P&L Change: £{improvement:+.2f}')
        print(f'   Win Rate Change: {win_rate_change:+.1f}%')
        print(f'   Trade Count Change: {trade_change:+d}')
        print()
        
        results[market] = market_results
        
        # Export individual trades
        original_csv = f'{market.replace(" ", "_")}_ORIGINAL_TRADES.csv'
        adaptive_csv = f'{market.replace(" ", "_")}_ADAPTIVE_TRADES.csv'
        
        engine.export_trades_to_csv(original_trades, original_csv)
        engine.export_trades_to_csv(adaptive_trades, adaptive_csv)
        
        print(f'📊 Exported: {original_csv}, {adaptive_csv}')
        print()
    
    # Overall Summary
    print('🏆 OVERALL SUMMARY')
    print('=' * 40)
    
    total_original_pnl = sum(results[market]['original']['total_pnl'] for market in markets)
    total_adaptive_pnl = sum(results[market]['adaptive']['total_pnl'] for market in markets)
    total_improvement = total_adaptive_pnl - total_original_pnl
    
    print(f'Original Strategy Total P&L: £{total_original_pnl:.2f}')
    print(f'Adaptive Strategy Total P&L: £{total_adaptive_pnl:.2f}')
    print(f'Overall Improvement: £{total_improvement:+.2f}')
    
    if total_original_pnl != 0:
        improvement_pct = (total_improvement / abs(total_original_pnl)) * 100
        print(f'Percentage Improvement: {improvement_pct:+.1f}%')
    
    print()
    print('📋 Market Breakdown:')
    for market in markets:
        orig_pnl = results[market]['original']['total_pnl']
        adapt_pnl = results[market]['adaptive']['total_pnl']
        market_improvement = adapt_pnl - orig_pnl
        
        print(f'  {market}:')
        print(f'    Original: £{orig_pnl:.2f} | Adaptive: £{adapt_pnl:.2f} | Change: £{market_improvement:+.2f}')
    
    print()
    print(f'✅ Analysis Complete: {datetime.now().strftime("%H:%M:%S")}')
    
    return results

if __name__ == "__main__":
    results = run_quick_analysis()