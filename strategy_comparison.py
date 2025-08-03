# strategy_comparison.py

"""
🔬 Strategy Comparison Framework

Runs comprehensive backtesting comparison between:
1. Original Strategy (caused the losses)
2. Market-Adaptive Strategy (our improvements)

Processes entire tick dataset and generates detailed P&L sheets and analysis.

Author: Strategy Analysis Team
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
# Optional plotting imports - skip if not available
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("📊 Plotting libraries not available - text reports only")
from typing import Dict, List
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from backtest_engine import BacktestEngine, BacktestTrade, BacktestMetrics

class StrategyComparison:
    """
    Comprehensive strategy comparison and analysis framework
    """
    
    def __init__(self):
        """Initialize strategy comparison"""
        self.engine = BacktestEngine()
        self.results = {}
        self.comparison_data = {}
        
        print("🔬 Strategy Comparison Framework initialized")
        print("   📊 Ready to process 105,740+ ticks")
        print("   🎯 Comparing Original vs Market-Adaptive strategies")
    
    def run_full_comparison(self, markets: List[str] = None) -> Dict:
        """Run complete strategy comparison across all markets"""
        if markets is None:
            markets = ["DAX", "FTSE 100"]
        
        print(f"\n🚀 RUNNING FULL STRATEGY COMPARISON")
        print("=" * 60)
        print(f"Markets: {', '.join(markets)}")
        print(f"Strategies: Original vs Market-Adaptive")
        print(f"Expected processing time: ~30 minutes")
        
        all_results = {}
        
        for market in markets:
            print(f"\n📈 PROCESSING {market.upper()}")
            print("-" * 40)
            
            market_results = {}
            
            # Run Original Strategy
            print(f"1️⃣ Running Original Strategy for {market}...")
            original_params = self.engine.get_original_strategy_params(market)
            original_trades = self.engine.run_backtest(market, original_params)
            original_metrics = self.engine.calculate_metrics(original_trades, "Original", market)
            
            market_results["original"] = {
                "trades": original_trades,
                "metrics": original_metrics,
                "params": original_params
            }
            
            # Export original trades
            original_csv = f"BACKTEST_ORIGINAL_{market.replace(' ', '_')}.csv"
            self.engine.export_trades_to_csv(original_trades, original_csv)
            
            # Run Market-Adaptive Strategy
            print(f"2️⃣ Running Market-Adaptive Strategy for {market}...")
            adaptive_params = self.engine.get_adaptive_strategy_params(market)
            adaptive_trades = self.engine.run_backtest(market, adaptive_params)
            adaptive_metrics = self.engine.calculate_metrics(adaptive_trades, "Adaptive", market)
            
            market_results["adaptive"] = {
                "trades": adaptive_trades,
                "metrics": adaptive_metrics,
                "params": adaptive_params
            }
            
            # Export adaptive trades
            adaptive_csv = f"BACKTEST_ADAPTIVE_{market.replace(' ', '_')}.csv"
            self.engine.export_trades_to_csv(adaptive_trades, adaptive_csv)
            
            all_results[market] = market_results
            
            # Quick summary
            self.print_market_summary(market, market_results)
        
        self.results = all_results
        return all_results
    
    def print_market_summary(self, market: str, results: Dict):
        """Print quick summary for a market"""
        orig_metrics = results["original"]["metrics"]
        adapt_metrics = results["adaptive"]["metrics"]
        
        print(f"\n📊 {market} QUICK SUMMARY:")
        print(f"   Original Strategy:")
        print(f"     Trades: {orig_metrics.total_trades} | Win Rate: {orig_metrics.win_rate:.1f}% | P&L: £{orig_metrics.total_pnl:.2f}")
        print(f"   Adaptive Strategy:")
        print(f"     Trades: {adapt_metrics.total_trades} | Win Rate: {adapt_metrics.win_rate:.1f}% | P&L: £{adapt_metrics.total_pnl:.2f}")
        
        improvement = adapt_metrics.total_pnl - orig_metrics.total_pnl
        improvement_pct = (improvement / abs(orig_metrics.total_pnl) * 100) if orig_metrics.total_pnl != 0 else 0
        
        print(f"   🎯 IMPROVEMENT: £{improvement:+.2f} ({improvement_pct:+.1f}%)")
    
    def generate_comprehensive_report(self) -> str:
        """Generate comprehensive comparison report"""
        if not self.results:
            return "No results available. Run comparison first."
        
        report = []
        report.append("📊 COMPREHENSIVE STRATEGY COMPARISON REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall summary
        total_original_pnl = 0
        total_adaptive_pnl = 0
        total_original_trades = 0
        total_adaptive_trades = 0
        
        for market, results in self.results.items():
            orig_metrics = results["original"]["metrics"]
            adapt_metrics = results["adaptive"]["metrics"]
            
            total_original_pnl += orig_metrics.total_pnl
            total_adaptive_pnl += adapt_metrics.total_pnl
            total_original_trades += orig_metrics.total_trades
            total_adaptive_trades += adapt_metrics.total_trades
        
        overall_improvement = total_adaptive_pnl - total_original_pnl
        improvement_pct = (overall_improvement / abs(total_original_pnl) * 100) if total_original_pnl != 0 else 0
        
        report.append("🎯 OVERALL RESULTS SUMMARY")
        report.append("-" * 30)
        report.append(f"Original Strategy Total P&L: £{total_original_pnl:.2f}")
        report.append(f"Adaptive Strategy Total P&L: £{total_adaptive_pnl:.2f}")
        report.append(f"Total Improvement: £{overall_improvement:+.2f} ({improvement_pct:+.1f}%)")
        report.append(f"Original Total Trades: {total_original_trades}")
        report.append(f"Adaptive Total Trades: {total_adaptive_trades}")
        report.append("")
        
        # Market-by-market analysis
        for market, results in self.results.items():
            report.append(f"📈 {market.upper()} DETAILED ANALYSIS")
            report.append("-" * 40)
            
            orig_metrics = results["original"]["metrics"]
            adapt_metrics = results["adaptive"]["metrics"]
            
            # Strategy parameters comparison
            report.append(f"Strategy Parameters:")
            orig_params = results["original"]["params"]
            adapt_params = results["adaptive"]["params"]
            
            report.append(f"  Original: RSI {orig_params['rsi_buy_threshold']}/{orig_params['rsi_sell_threshold']}, SL/TP {orig_params['stop_loss_pips']}/{orig_params['take_profit_pips']}")
            report.append(f"  Adaptive: RSI {adapt_params['rsi_buy_threshold']}/{adapt_params['rsi_sell_threshold']}, SL/TP {adapt_params['stop_loss_pips']}/{adapt_params['take_profit_pips']}")
            
            if "trading_hours" in adapt_params:
                avoid_hours = adapt_params["trading_hours"].get("avoid_hours", [])
                report.append(f"  Time Filters: Avoiding hours {avoid_hours}")
            
            report.append("")
            
            # Performance comparison
            report.append("Performance Metrics:")
            report.append(f"                      Original    Adaptive    Improvement")
            report.append(f"Total Trades:         {orig_metrics.total_trades:8d}    {adapt_metrics.total_trades:8d}    {adapt_metrics.total_trades - orig_metrics.total_trades:+8d}")
            report.append(f"Win Rate:             {orig_metrics.win_rate:8.1f}%   {adapt_metrics.win_rate:8.1f}%   {adapt_metrics.win_rate - orig_metrics.win_rate:+8.1f}%")
            report.append(f"Total P&L:            £{orig_metrics.total_pnl:7.2f}   £{adapt_metrics.total_pnl:7.2f}   £{adapt_metrics.total_pnl - orig_metrics.total_pnl:+7.2f}")
            report.append(f"Profit Factor:        {orig_metrics.profit_factor:8.2f}    {adapt_metrics.profit_factor:8.2f}    {adapt_metrics.profit_factor - orig_metrics.profit_factor:+8.2f}")
            report.append(f"Max Drawdown:         £{orig_metrics.max_drawdown:7.2f}   £{adapt_metrics.max_drawdown:7.2f}   £{adapt_metrics.max_drawdown - orig_metrics.max_drawdown:+7.2f}")
            report.append(f"Avg Win:              £{orig_metrics.average_win:7.2f}   £{adapt_metrics.average_win:7.2f}   £{adapt_metrics.average_win - orig_metrics.average_win:+7.2f}")
            report.append(f"Avg Loss:             £{orig_metrics.average_loss:7.2f}   £{adapt_metrics.average_loss:7.2f}   £{adapt_metrics.average_loss - orig_metrics.average_loss:+7.2f}")
            report.append(f"Max Consecutive Losses: {orig_metrics.max_consecutive_losses:6d}      {adapt_metrics.max_consecutive_losses:6d}      {adapt_metrics.max_consecutive_losses - orig_metrics.max_consecutive_losses:+6d}")
            report.append(f"Sharpe Ratio:         {orig_metrics.sharpe_ratio:8.2f}    {adapt_metrics.sharpe_ratio:8.2f}    {adapt_metrics.sharpe_ratio - orig_metrics.sharpe_ratio:+8.2f}")
            report.append("")
            
            # Cost analysis
            report.append("Cost Analysis:")
            report.append(f"Original Spread/Commission Costs: £{orig_metrics.total_spread_cost:.2f}")
            report.append(f"Adaptive Spread/Commission Costs: £{adapt_metrics.total_spread_cost:.2f}")
            report.append(f"Cost Difference: £{adapt_metrics.total_spread_cost - orig_metrics.total_spread_cost:+.2f}")
            report.append("")
            
            # Risk assessment
            if orig_metrics.max_drawdown > 0:
                orig_return_to_dd = orig_metrics.total_pnl / orig_metrics.max_drawdown
            else:
                orig_return_to_dd = float('inf') if orig_metrics.total_pnl > 0 else 0
            
            if adapt_metrics.max_drawdown > 0:
                adapt_return_to_dd = adapt_metrics.total_pnl / adapt_metrics.max_drawdown
            else:
                adapt_return_to_dd = float('inf') if adapt_metrics.total_pnl > 0 else 0
            
            report.append("Risk Assessment:")
            report.append(f"Original Return/Drawdown Ratio: {orig_return_to_dd:.2f}")
            report.append(f"Adaptive Return/Drawdown Ratio: {adapt_return_to_dd:.2f}")
            report.append("")
        
        # Conclusions and recommendations
        report.append("🎯 CONCLUSIONS AND RECOMMENDATIONS")
        report.append("-" * 40)
        
        if overall_improvement > 0:
            report.append("✅ POSITIVE RESULTS:")
            report.append(f"• Market-Adaptive strategy shows £{overall_improvement:.2f} improvement")
            report.append(f"• Overall improvement of {improvement_pct:.1f}%")
            
            # Identify best performing market
            best_market = None
            best_improvement = float('-inf')
            for market, results in self.results.items():
                market_improvement = results["adaptive"]["metrics"].total_pnl - results["original"]["metrics"].total_pnl
                if market_improvement > best_improvement:
                    best_improvement = market_improvement
                    best_market = market
            
            if best_market:
                report.append(f"• {best_market} shows strongest improvement: £{best_improvement:+.2f}")
            
            report.append("• Recommended: Deploy Market-Adaptive strategy for live trading")
            
        else:
            report.append("⚠️ MIXED RESULTS:")
            report.append(f"• Overall P&L change: £{overall_improvement:.2f}")
            report.append("• Further optimization may be needed")
            report.append("• Consider parameter fine-tuning")
        
        report.append("")
        report.append("📋 NEXT STEPS:")
        report.append("1. Review detailed trade logs in CSV files")
        report.append("2. Analyze time-based performance patterns")
        report.append("3. Consider additional risk management measures")
        report.append("4. Monitor live performance closely if deploying")
        report.append("")
        
        return "\\n".join(report)
    
    def create_hourly_analysis(self) -> Dict:
        """Analyze performance by hour of day"""
        hourly_data = {}
        
        for market, results in self.results.items():
            hourly_data[market] = {}
            
            for strategy_name in ["original", "adaptive"]:
                trades = results[strategy_name]["trades"]
                
                # Group trades by hour
                hourly_pnl = {}
                for trade in trades:
                    hour = trade.timestamp.hour
                    if hour not in hourly_pnl:
                        hourly_pnl[hour] = []
                    hourly_pnl[hour].append(trade.pnl)
                
                # Calculate hourly statistics
                hourly_stats = {}
                for hour, pnls in hourly_pnl.items():
                    hourly_stats[hour] = {
                        "total_pnl": sum(pnls),
                        "trades": len(pnls),
                        "avg_pnl": np.mean(pnls),
                        "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100
                    }
                
                hourly_data[market][strategy_name] = hourly_stats
        
        return hourly_data
    
    def export_master_pnl_sheet(self, filename: str = "MASTER_PNL_COMPARISON.csv"):
        """Export master P&L comparison sheet"""
        try:
            all_trades = []
            
            for market, results in self.results.items():
                for strategy_name in ["original", "adaptive"]:
                    trades = results[strategy_name]["trades"]
                    for trade in trades:
                        trade_dict = {
                            "timestamp": trade.timestamp,
                            "market": market,
                            "strategy": strategy_name,
                            "signal": trade.signal,
                            "entry_price": trade.entry_price,
                            "exit_price": trade.exit_price,
                            "size": trade.size,
                            "pnl": trade.pnl,
                            "cumulative_pnl": trade.cumulative_pnl,
                            "win": trade.win,
                            "duration_seconds": trade.duration_seconds,
                            "reason": trade.reason,
                            "entry_rsi": trade.entry_rsi,
                            "exit_rsi": trade.exit_rsi,
                            "spread_cost": trade.spread_cost
                        }
                        all_trades.append(trade_dict)
            
            # Convert to DataFrame and sort by timestamp
            df = pd.DataFrame(all_trades)
            df = df.sort_values("timestamp")
            
            # Export to CSV
            df.to_csv(filename, index=False)
            print(f"📊 Master P&L sheet exported to {filename}")
            print(f"   Total records: {len(all_trades):,}")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting master P&L sheet: {e}")
            return None
    
    def export_summary_json(self, filename: str = "BACKTEST_SUMMARY.json"):
        """Export summary results to JSON"""
        try:
            summary = {}
            
            for market, results in self.results.items():
                market_summary = {}
                
                for strategy_name in ["original", "adaptive"]:
                    metrics = results[strategy_name]["metrics"]
                    
                    # Convert metrics to dictionary (excluding non-serializable objects)
                    metrics_dict = {
                        "strategy_name": metrics.strategy_name,
                        "market": metrics.market,
                        "total_trades": metrics.total_trades,
                        "winning_trades": metrics.winning_trades,
                        "losing_trades": metrics.losing_trades,
                        "win_rate": metrics.win_rate,
                        "total_pnl": metrics.total_pnl,
                        "gross_profit": metrics.gross_profit,
                        "gross_loss": metrics.gross_loss,
                        "profit_factor": metrics.profit_factor,
                        "average_win": metrics.average_win,
                        "average_loss": metrics.average_loss,
                        "largest_win": metrics.largest_win,
                        "largest_loss": metrics.largest_loss,
                        "max_drawdown": metrics.max_drawdown,
                        "max_consecutive_wins": metrics.max_consecutive_wins,
                        "max_consecutive_losses": metrics.max_consecutive_losses,
                        "avg_trade_duration": metrics.avg_trade_duration,
                        "total_spread_cost": metrics.total_spread_cost,
                        "sharpe_ratio": metrics.sharpe_ratio,
                        "return_std": metrics.return_std
                    }
                    
                    market_summary[strategy_name] = {
                        "metrics": metrics_dict,
                        "params": results[strategy_name]["params"]
                    }
                
                summary[market] = market_summary
            
            # Add timestamp
            summary["generated_at"] = datetime.now().isoformat()
            
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"📋 Summary exported to {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error exporting summary: {e}")
            return None

def main():
    """Main execution function"""
    print("🚀 COMPREHENSIVE STRATEGY BACKTESTING")
    print("=" * 50)
    print("Processing entire tick dataset...")
    print("Expected duration: 20-30 minutes")
    print()
    
    # Initialize comparison framework
    comparison = StrategyComparison()
    
    # Run full comparison
    results = comparison.run_full_comparison(["DAX", "FTSE 100"])
    
    if results:
        print("\n" + "=" * 60)
        print("📊 GENERATING COMPREHENSIVE REPORTS")
        print("=" * 60)
        
        # Generate text report
        report = comparison.generate_comprehensive_report()
        
        # Save report to file
        with open("COMPREHENSIVE_BACKTEST_REPORT.txt", "w") as f:
            f.write(report)
        
        print("📋 Reports generated:")
        print("   • COMPREHENSIVE_BACKTEST_REPORT.txt - Detailed analysis")
        
        # Export master P&L sheet
        master_file = comparison.export_master_pnl_sheet()
        if master_file:
            print(f"   • {master_file} - All trades combined")
        
        # Export JSON summary
        json_file = comparison.export_summary_json()
        if json_file:
            print(f"   • {json_file} - Machine-readable summary")
        
        # Generate hourly analysis
        hourly_data = comparison.create_hourly_analysis()
        
        print("\\n" + report)
        
        print("\\n🎯 BACKTESTING COMPLETE!")
        print("All files have been generated in the current directory.")
        
    else:
        print("❌ Backtesting failed - no results generated")

if __name__ == "__main__":
    main()