#!/usr/bin/env python3
"""
🔥 Scalping Profile Trading Runner

High-frequency rapid trading with quick entries/exits.
Designed for active traders comfortable with high-frequency trading.

Features:
- 4% position sizes
- 12% daily loss limit
- NO economic event restrictions
- 52-62% target win rate  
- 20-100 trades per day
- 2-15 minute trade duration
- 3-pip profit targets, 2-pip stops

Usage:
    python3 scripts/run_scalping.py --duration 7d
    python3 scripts/run_scalping.py --duration 24h --live

Author: Multi-Profile Trading System
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_profile import ProfileTradingRunner

def main():
    parser = argparse.ArgumentParser(description="Run Scalping Profile Trading")
    parser.add_argument("--duration", "-d", default="7d",
                       help="Duration to run (e.g., 1d, 7d, 1w, 24h)")
    parser.add_argument("--live", action="store_true",
                       help="Run in live mode (default: demo)")
    parser.add_argument("--paper", action="store_true", 
                       help="Force paper trading mode")
    
    args = parser.parse_args()
    
    # Override live mode if paper trading requested
    live_mode = args.live and not args.paper
    
    print("🔥 SCALPING TRADING PROFILE")
    print("=" * 50)
    print("Strategy: High-frequency rapid trading")
    print("Risk Level: HIGH")
    print("Expected: 20-100 trades/day, 52-62% win rate")
    print("Position Size: 4% of account")
    print("Daily Risk: 12% maximum")
    print("Economic Events: IGNORED - Trade through everything!")
    print("Trade Duration: 2-15 minutes average")
    print("Targets: 3-pip profits, 2-pip stops")
    print("Frequency: Up to 20 trades per hour")
    print("")
    
    try:
        # Initialize scalping runner
        runner = ProfileTradingRunner(
            profile_name="scalping",
            duration_str=args.duration,
            live_mode=live_mode
        )
        
        # Load profile and start trading
        runner.load_profile()
        runner.initialize_trading_system()
        runner.start_performance_tracking()
        runner.run_trading_session()
        runner.finalize_performance_tracking()
        
        print("✅ Scalping trading session completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Scalping trading session interrupted by user")
    except Exception as e:
        print(f"❌ Error in scalping trading session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()