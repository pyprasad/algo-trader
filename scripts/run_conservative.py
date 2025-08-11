#!/usr/bin/env python3
"""
🛡️ Conservative Profile Trading Runner

Ultra-safe capital preservation trading with maximum risk controls.
Designed for risk-averse traders prioritizing capital protection.

Features:
- 0.5% position sizes
- 2% daily loss limit  
- 3-hour pause windows around economic events
- 70-80% target win rate
- 1-3 trades per day

Usage:
    python3 scripts/run_conservative.py --duration 7d
    python3 scripts/run_conservative.py --duration 1w --live

Author: Multi-Profile Trading System
"""

import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_profile import ProfileTradingRunner

def main():
    parser = argparse.ArgumentParser(description="Run Conservative Profile Trading")
    parser.add_argument("--duration", "-d", default="7d",
                       help="Duration to run (e.g., 1d, 7d, 1w, 24h)")
    parser.add_argument("--live", action="store_true",
                       help="Run in live mode (default: demo)")
    parser.add_argument("--paper", action="store_true", 
                       help="Force paper trading mode")
    
    args = parser.parse_args()
    
    # Override live mode if paper trading requested
    live_mode = args.live and not args.paper
    
    print("🛡️ CONSERVATIVE TRADING PROFILE")
    print("=" * 50)
    print("Strategy: Ultra-safe capital preservation")
    print("Risk Level: VERY LOW")
    print("Expected: 1-3 trades/day, 70-80% win rate")
    print("Position Size: 0.5% of account")
    print("Daily Risk: 2% maximum")
    print("Economic Events: 3-hour pause windows")
    print("")
    
    try:
        # Initialize conservative runner
        runner = ProfileTradingRunner(
            profile_name="conservative",
            duration_str=args.duration,
            live_mode=live_mode
        )
        
        # Load profile and start trading
        runner.load_profile()
        runner.initialize_trading_system()
        runner.start_performance_tracking()
        runner.run_trading_session()
        runner.finalize_performance_tracking()
        
        print("✅ Conservative trading session completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Conservative trading session interrupted by user")
    except Exception as e:
        print(f"❌ Error in conservative trading session: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()