# runners/run_advanced_strategy.py

import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.advanced_strategy_engine import advanced_strategy
from core.asset_manager import asset_manager
from utils.trading_monitor import print_trading_dashboard

def print_analysis_results(results: dict):
    """Print formatted analysis results."""
    
    print("\n" + "="*80)
    print("📊 ADVANCED STRATEGY ANALYSIS RESULTS")
    print("="*80)
    
    # Summary
    summary = results.get("summary", {})
    print(f"📈 Portfolio Summary:")
    print(f"  • Total Assets Analyzed: {summary.get('total_assets', 0)}")
    print(f"  • Currently Tradeable: {summary.get('tradeable_now', 0)}")
    print(f"  • Strong Signals: {summary.get('strong_signals', 0)}")
    print(f"  • Recommended Trades: {summary.get('recommended_trades', 0)}")
    print(f"  • Portfolio Risk: {summary.get('portfolio_risk', 0):.2%}")
    
    print(f"\n📊 Signal Distribution:")
    print(f"  • BUY Signals: {results.get('buy_signals', 0)}")
    print(f"  • SELL Signals: {results.get('sell_signals', 0)}")
    print(f"  • HOLD Signals: {results.get('hold_signals', 0)}")
    
    # Asset-by-asset analysis
    print(f"\n🔍 Individual Asset Analysis:")
    print("-" * 80)
    
    for asset, analysis in results.get("asset_analyses", {}).items():
        signal = analysis.get("final_signal", "HOLD")
        confidence = analysis.get("final_confidence", 0)
        price = analysis.get("price_latest", 0)
        tradeable = analysis.get("is_tradeable", False)
        
        # Signal emoji
        signal_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}[signal]
        tradeable_emoji = "✅" if tradeable else "🔒"
        
        print(f"{signal_emoji} {asset:12} | Price: {price:8.2f} | Signal: {signal:4} | "
              f"Confidence: {confidence:5.2f} | {tradeable_emoji}")
        
        # Show ensemble breakdown for strong signals
        if confidence > 0.5 and "ensemble" in analysis:
            ensemble_details = analysis["ensemble"].get("details", {})
            strategy_results = ensemble_details.get("strategy_results", {})
            
            print(f"    Strategy Breakdown:")
            for strategy, details in strategy_results.items():
                if isinstance(details, dict):
                    s_signal = details.get("signal", "HOLD")
                    s_conf = details.get("confidence", 0)
                    s_weight = details.get("weight", 0)
                    print(f"      • {strategy:15}: {s_signal:4} (conf: {s_conf:.2f}, weight: {s_weight:.2f})")
    
    # Portfolio recommendations
    recommendations = results.get("portfolio_recommendations", [])
    if recommendations:
        print(f"\n💼 PORTFOLIO RECOMMENDATIONS:")
        print("-" * 80)
        
        for i, rec in enumerate(recommendations, 1):
            asset = rec["asset"]
            signal = rec["signal"]
            confidence = rec["confidence"]
            risk = rec["risk_allocation"]
            size = rec["position_size"]
            
            signal_emoji = {"BUY": "🟢", "SELL": "🔴"}[signal]
            
            print(f"{i}. {signal_emoji} {asset:12} | {signal:4} | "
                  f"Confidence: {confidence:.2f} | Risk: {risk:.2%} | Size: {size:.2f}")
            print(f"   SL: {rec['stop_loss']:.2f} | TP: {rec['take_profit']:.2f}")
    
    print("="*80)

def main():
    """Main function to run advanced strategy analysis."""
    
    print("🚀 Advanced Multi-Asset Strategy Engine")
    print("="*60)
    
    # Show current trading dashboard first
    print_trading_dashboard()
    
    # Get user preferences
    print("\n🎯 Strategy Configuration:")
    print("1. Analyze all available assets")
    print("2. Analyze specific tech stocks (META, GOOGL, AAPL, NVDA, TSLA)")
    print("3. Analyze indices (FTSE 100, S&P 500, NASDAQ 100)")
    print("4. Analyze forex pairs (EURUSD, GBPUSD, USDJPY)")
    print("5. Custom asset selection")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    assets = None
    
    if choice == "1":
        # Use all available assets
        assets = None
        print("📈 Analyzing all available assets...")
        
    elif choice == "2":
        assets = ["META", "GOOGL", "AAPL", "NVDA", "TSLA"]
        print(f"💻 Analyzing tech stocks: {', '.join(assets)}")
        
    elif choice == "3":
        assets = ["FTSE 100", "S&P 500", "NASDAQ 100"]
        print(f"📊 Analyzing indices: {', '.join(assets)}")
        
    elif choice == "4":
        assets = ["EURUSD", "GBPUSD", "USDJPY"]
        print(f"💱 Analyzing forex pairs: {', '.join(assets)}")
        
    elif choice == "5":
        available_assets = asset_manager.get_tradeable_assets()
        print(f"\n📋 Available assets: {', '.join(available_assets)}")
        custom_input = input("Enter asset names (comma-separated): ").strip()
        assets = [asset.strip() for asset in custom_input.split(",") if asset.strip()]
        print(f"🎯 Analyzing custom selection: {', '.join(assets)}")
        
    else:
        print("❌ Invalid choice. Using default FTSE 100.")
        assets = ["FTSE 100"]
    
    # Set lookback period
    try:
        lookback = int(input("\nLookback period in minutes (default 60): ").strip() or "60")
    except ValueError:
        lookback = 60
        print("⚠️ Invalid input. Using default 60 minutes.")
    
    print(f"\n🔄 Running analysis with {lookback} minutes of data...")
    print("-" * 60)
    
    # Run the advanced strategy
    try:
        results = advanced_strategy.run_advanced_strategy(assets, lookback)
        
        # Print results
        print_analysis_results(results)
        
        # Option to save results
        save_results = input("\n💾 Save results to JSON file? (y/N): ").strip().lower()
        if save_results in ['y', 'yes']:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"advanced_strategy_results_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"📄 Results saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Error running advanced strategy: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()