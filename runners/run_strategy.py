# runners/run_strategy.py

import os
import sys

# === Add project root to sys.path BEFORE importing internal modules ===
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.trade_executor import execute_trade
from core.strategy_engine import run_strategy

if __name__ == "__main__":
    print("🚀 Running strategy engine on latest FTSE 100 data...\n")

    # Run strategy and get signal with context
    result = run_strategy(
        asset="FTSE 100",
        lookback_minutes=60,
        timeframe='1min'
    )

    if result:
        signal, strategy_context = result
        print(f"\n✅ FINAL SIGNAL: {signal}\n")

        if signal in ["BUY", "SELL"]:
            try:
                trade_result = execute_trade(
                    direction=signal, 
                    strategy_signals=strategy_context
                )
                print(f"📥 Trade Confirmed: {trade_result.get('dealStatus')}")
            except Exception as e:
                print(f"❌ Trade failed: {e}")
        else:
            print("⏸️ No trade executed due to HOLD signal.")
    else:
        print("\n⚠️ Strategy did not return a decision.\n")
