# run_focused_backtest.py

"""
🎯 Focused Backtesting Analysis

Runs targeted backtesting on our stored tick data to generate P&L comparison
between Original and Market-Adaptive strategies.

Author: Backtesting Team
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from strategy_comparison import StrategyComparison

def run_focused_analysis():
    """Run focused backtesting analysis"""
    print("🎯 FOCUSED BACKTESTING ANALYSIS")
    print("=" * 50)
    print("Running comprehensive strategy comparison...")
    print()
    
    # Initialize comparison
    comparison = StrategyComparison()
    
    # Run for both markets
    markets = ["DAX", "FTSE 100"]
    print(f"Markets to process: {', '.join(markets)}")
    print()
    
    results = {}
    
    for market in markets:
        print(f"🚀 PROCESSING {market}")
        print("-" * 30)
        
        try:
            # Run single market comparison
            market_results = comparison.run_full_comparison([market])
            results.update(market_results)
            
            # Show immediate results
            if market in market_results:
                orig_metrics = market_results[market]["original"]["metrics"]
                adapt_metrics = market_results[market]["adaptive"]["metrics"]
                
                print(f"✅ {market} RESULTS:")
                print(f"   Original: {orig_metrics.total_trades} trades, {orig_metrics.win_rate:.1f}% win rate, £{orig_metrics.total_pnl:.2f} P&L")
                print(f"   Adaptive: {adapt_metrics.total_trades} trades, {adapt_metrics.win_rate:.1f}% win rate, £{adapt_metrics.total_pnl:.2f} P&L")
                
                improvement = adapt_metrics.total_pnl - orig_metrics.total_pnl
                print(f"   Improvement: £{improvement:+.2f}")
                print()
        
        except Exception as e:
            print(f"❌ Error processing {market}: {e}")
            continue
    
    # Generate comprehensive analysis if we have results
    if results:
        comparison.results = results
        
        print("📊 GENERATING COMPREHENSIVE REPORTS")
        print("=" * 40)
        
        # Generate comprehensive report
        report = comparison.generate_comprehensive_report()
        
        # Save to file
        report_file = "BACKTEST_ANALYSIS_REPORT.txt"
        with open(report_file, "w") as f:
            f.write(report)
        
        print(f"📋 Report saved to: {report_file}")
        
        # Export master P&L sheet
        pnl_file = comparison.export_master_pnl_sheet("COMPLETE_PNL_ANALYSIS.csv")
        if pnl_file:
            print(f"📊 P&L sheet saved to: {pnl_file}")
        
        # Export JSON summary
        json_file = comparison.export_summary_json("BACKTEST_METRICS.json")
        if json_file:
            print(f"📋 JSON summary saved to: {json_file}")
        
        print()
        print("📈 SUMMARY RESULTS:")
        print(report)
        
    else:
        print("❌ No results generated")

if __name__ == "__main__":
    run_focused_analysis()