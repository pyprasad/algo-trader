#!/usr/bin/env python3
"""
⚡ Aggressive Profile Trading Runner

Event-based volatility trading with higher risk tolerance.
Designed for experienced traders comfortable with volatility.

Features:
- 3% position sizes
- 8% daily loss limit
- Trade INTO economic events (15min pause windows)
- 55-65% target win rate
- 5-15 trades per day

Usage:
    python3 scripts/run_aggressive.py --duration 7d
    python3 scripts/run_aggressive.py --duration 1w --live

Author: Multi-Profile Trading System
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_profile import ProfileTradingRunner

def main():
    parser = argparse.ArgumentParser(description="Run Aggressive Profile Trading")
    parser.add_argument("--duration", "-d", default="7d",
                       help="Duration to run (e.g., 1d, 7d, 1w, 24h)")
    parser.add_argument("--live", action="store_true",
                       help="Run in live mode (default: demo)")
    parser.add_argument("--paper", action="store_true", 
                       help="Force paper trading mode")
    
    args = parser.parse_args()
    
    # Override live mode if paper trading requested
    live_mode = args.live and not args.paper
    
    print("⚡ AGGRESSIVE TRADING PROFILE")
    print("=" * 50)
    print("Strategy: Event-based volatility trading")
    print("Risk Level: MEDIUM-HIGH")
    print("Expected: 5-15 trades/day, 55-65% win rate")
    print("Position Size: 3% of account")
    print("Daily Risk: 8% maximum")
    print("Economic Events: TRADE THE VOLATILITY!")
    print("Event Windows: 15min pause before, trade during")
    print("")
    
    try:
        # Initialize aggressive runner
        runner = ProfileTradingRunner(
            profile_name="aggressive",
            duration_str=args.duration,
            live_mode=live_mode
        )
        
        # Load profile and start trading
        runner.load_profile()
        runner.initialize_trading_system()
        runner.start_performance_tracking()
        runner.run_trading_session()
        runner.finalize_performance_tracking()
        
        print("✅ Aggressive trading session completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Aggressive trading session interrupted by user")
    except Exception as e:
        print(f"❌ Error in aggressive trading session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()