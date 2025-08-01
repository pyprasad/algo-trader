# runners/run_continuous.py

import os
import sys
import time
import yaml
from datetime import datetime, timedelta
import signal as signal_module
import threading

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategy_engine import run_strategy
from core.trade_executor import execute_trade
from data.db import get_open_trades
from utils.market_hours import is_market_open, get_market_status

# Load configuration
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

# Configuration
STRATEGY_MODE = config["strategy"]["mode"]
EXECUTION_INTERVAL = 60  # seconds between strategy runs
MAX_OPEN_TRADES = 3      # maximum concurrent trades
TRADING_HOURS_START = 8  # 8 AM
TRADING_HOURS_END = 17   # 5 PM
WEEKEND_TRADING = False  # disable weekend trading

# Global control variables
running = True
trade_count = 0
last_signal_time = None

def signal_handler(signum, frame):
    """Handle graceful shutdown on SIGINT (Ctrl+C)"""
    global running
    print("\n🛑 Shutdown signal received. Finishing current cycle...")
    running = False

def is_trading_hours():
    """Check if current time is within trading hours using market hours utility"""
    return is_market_open("FTSE")

def should_execute_trade(signal, strategy_context):
    """
    Advanced logic to determine if we should execute a trade based on:
    - Market conditions
    - Open position limits
    - Time since last trade
    - Risk management rules
    """
    global last_signal_time, trade_count
    
    if signal == "HOLD":
        return False
    
    # Check if we're in trading hours
    if not is_trading_hours():
        print("⏰ Outside trading hours, skipping trade execution")
        return False
    
    # Check maximum open trades limit
    open_trades = get_open_trades("FTSE 100")
    if len(open_trades) >= MAX_OPEN_TRADES:
        print(f"🚫 Maximum open trades ({MAX_OPEN_TRADES}) reached, skipping execution")
        return False
    
    # Prevent rapid-fire trading (minimum 5 minutes between trades)
    if last_signal_time and (datetime.now() - last_signal_time).total_seconds() < 300:
        print("⏳ Cooling down, too soon since last trade")
        return False
    
    # Check signal strength (example: only trade on strong RSI signals)
    rsi = strategy_context.get("rsi", 50)
    if signal == "BUY" and rsi < 75:  # More conservative than 80
        print(f"📊 RSI {rsi:.2f} not strong enough for BUY signal")
        return False
    elif signal == "SELL" and rsi > 25:  # More conservative than 20
        print(f"📊 RSI {rsi:.2f} not strong enough for SELL signal")
        return False
    
    # Check regime compatibility
    regime = strategy_context.get("regime", "neutral")
    trend = strategy_context.get("trend", "sideways")
    
    # Only trade in favorable regime-trend combinations
    if regime == "volatile":
        print("🌪️ Volatile regime detected, avoiding trade execution")
        return False
    
    if regime == "mean-reverting" and trend == "sideways":
        print("📈 Sideways trend in mean-reverting regime, avoiding trade")
        return False
    
    return True

def run_continuous_strategy():
    """Main continuous trading loop"""
    global running, trade_count, last_signal_time
    
    print("🚀 Starting continuous strategy execution...")
    print(f"📊 Strategy Mode: {STRATEGY_MODE}")
    print(f"⏰ Execution Interval: {EXECUTION_INTERVAL}s")
    print(f"🕐 Trading Hours: {TRADING_HOURS_START}:00 - {TRADING_HOURS_END}:00")
    print(f"📈 Max Open Trades: {MAX_OPEN_TRADES}")
    print("="*60)
    
    # Register signal handlers for graceful shutdown
    signal_module.signal(signal_module.SIGINT, signal_handler)
    signal_module.signal(signal_module.SIGTERM, signal_handler)
    
    cycle_count = 0
    
    while running:
        try:
            cycle_count += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n🔄 Cycle #{cycle_count} | {current_time}")
            
            # Skip execution if in HISTORICAL mode
            if STRATEGY_MODE == "HISTORICAL":
                print("📚 Running in HISTORICAL mode - analysis only")
            
            # Run strategy
            result = run_strategy(
                asset="FTSE 100",
                lookback_minutes=60,
                timeframe='1min'
            )
            
            if result:
                signal, strategy_context = result
                print(f"📊 Strategy Result: {signal}")
                
                # Advanced execution logic
                if STRATEGY_MODE == "LIVE" and should_execute_trade(signal, strategy_context):
                    print(f"✅ Executing trade: {signal}")
                    try:
                        trade_result = execute_trade(
                            direction=signal,
                            strategy_signals=strategy_context
                        )
                        
                        if trade_result and trade_result.get('dealStatus') in ['ACCEPTED', 'OPEN']:
                            trade_count += 1
                            last_signal_time = datetime.now()
                            print(f"🎯 Trade #{trade_count} executed successfully!")
                        else:
                            print(f"❌ Trade execution failed: {trade_result}")
                            
                    except Exception as e:
                        print(f"💥 Trade execution error: {e}")
                
                else:
                    print("⏸️ Trade execution skipped based on conditions")
            
            else:
                print("⚠️ No strategy result returned")
            
            # Show current portfolio status
            open_trades = get_open_trades("FTSE 100")
            print(f"💼 Open Positions: {len(open_trades)}")
            
            # Wait for next cycle
            if running:
                print(f"⏳ Waiting {EXECUTION_INTERVAL}s until next cycle...")
                time.sleep(EXECUTION_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n🛑 Manual interruption received")
            break
        except Exception as e:
            print(f"💥 Unexpected error in main loop: {e}")
            print("⏳ Waiting 30s before retry...")
            time.sleep(30)
    
    print(f"\n🏁 Continuous strategy stopped after {cycle_count} cycles")
    print(f"📊 Total trades executed: {trade_count}")
    print("👋 Goodbye!")

if __name__ == "__main__":
    run_continuous_strategy()