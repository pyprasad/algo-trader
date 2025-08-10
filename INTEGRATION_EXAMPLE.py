#!/usr/bin/env python3
"""
🔧 Integration Example: How to Use Mode Settings in Your Trading System

This shows how to integrate the mode settings into your run_multi_market.py
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from utils.system_mode_manager import get_system_mode_config
from core.enhanced_strategy_engine import get_enhanced_strategy_engine

def example_trading_loop_with_modes():
    """
    Example of how to integrate mode settings into your trading loop
    """
    
    print("🔧 Trading System with Mode Integration")
    print("=" * 50)
    
    # 1. GET MODE CONFIGURATION AT STARTUP
    mode_config = get_system_mode_config()
    
    print(f"🎯 Current Mode: {mode_config['mode'].upper()}")
    print(f"   Signal Confidence Required: {mode_config['min_signal_confidence']:.0%}")
    print(f"   Analysis Interval: {mode_config['analysis_interval_minutes']} minutes")
    print(f"   Max Trades/Hour: {mode_config['max_trades_per_hour']} per market")
    print(f"   Daily Loss Limit: £{mode_config['daily_loss_limit']}")
    print()
    
    # 2. INITIALIZE SYSTEMS
    strategy_engine = get_enhanced_strategy_engine()
    
    # 3. TRADING LOOP WITH MODE SETTINGS
    markets = ["FTSE 100", "DAX"]
    last_analysis_time = {market: None for market in markets}
    hourly_trade_count = {market: [] for market in markets}
    daily_pnl = 0
    
    # Convert mode settings to usable variables
    min_confidence = mode_config['min_signal_confidence']
    analysis_interval = timedelta(minutes=mode_config['analysis_interval_minutes'])
    max_trades_per_hour = mode_config['max_trades_per_hour']
    daily_loss_limit = mode_config['daily_loss_limit']
    
    print("🚀 Starting trading loop with mode-based settings...")
    
    # Simulate trading loop
    for tick_count in range(100):  # Simulate 100 ticks
        current_time = datetime.utcnow()
        
        for market in markets:
            # 4. MODE-BASED TIMING CONTROL
            if last_analysis_time[market]:
                time_since_last = current_time - last_analysis_time[market]
                if time_since_last < analysis_interval:
                    continue  # Skip analysis based on mode timing
            
            last_analysis_time[market] = current_time
            
            # 5. MODE-BASED SAFETY CHECKS
            
            # Check daily loss limit (mode-specific)
            if abs(daily_pnl) >= daily_loss_limit:
                print(f"🚨 Daily loss limit hit: £{daily_pnl:.2f} >= £{daily_loss_limit}")
                continue
            
            # Check hourly trade limits (mode-specific)
            one_hour_ago = current_time - timedelta(hours=1)
            hourly_trade_count[market] = [
                t for t in hourly_trade_count[market] if t > one_hour_ago
            ]
            
            if len(hourly_trade_count[market]) >= max_trades_per_hour:
                print(f"⏰ {market}: Hourly trade limit reached ({max_trades_per_hour})")
                continue
            
            # 6. GET TRADING SIGNALS
            # Simulate getting signals (in real system, use actual price data)
            mock_prices = [9100 + (tick_count % 10) for _ in range(50)]  # Mock data
            signals = strategy_engine.analyze_market_conditions(mock_prices, market)
            
            if not signals:
                continue
                
            signal_confidence = signals.get('confidence', 0.0)
            signal_direction = signals.get('signal', 'HOLD')
            
            # 7. MODE-BASED SIGNAL FILTERING
            if signal_confidence < min_confidence:
                print(f"📊 {market}: Signal confidence {signal_confidence:.2f} below mode minimum {min_confidence:.2f}")
                continue
            
            if signal_direction in ['BUY', 'SELL']:
                print(f"✅ {market}: {signal_direction} signal (conf: {signal_confidence:.2f}) PASSED mode filter")
                
                # 8. EXECUTE TRADE (with all your existing safety systems)
                # This is where you'd call your execute_trade function
                # execute_trade(market, signal_direction, ...)
                
                # Record trade for hourly limits
                hourly_trade_count[market].append(current_time)
                
                # Simulate P&L impact
                simulated_pnl = (tick_count % 3 - 1) * 10  # Random -10, 0, or +10
                daily_pnl += simulated_pnl
                
                print(f"💰 Trade executed: {market} {signal_direction} | P&L: £{simulated_pnl} | Daily: £{daily_pnl:.2f}")
            
        # Simulate tick delay
        time.sleep(0.1)  # In real system, this would be natural tick timing
    
    print(f"\n🎯 Example completed with mode: {mode_config['mode']}")
    print(f"Final daily P&L: £{daily_pnl:.2f}")

def show_integration_points():
    """Show key integration points for your existing system"""
    
    print("\n🔗 KEY INTEGRATION POINTS FOR YOUR run_multi_market.py")
    print("=" * 60)
    
    print("""
1. ADD AT THE TOP OF YOUR FILE:
   from utils.system_mode_manager import get_system_mode_config

2. GET MODE CONFIG AT STARTUP:
   mode_config = get_system_mode_config()
   min_confidence = mode_config['min_signal_confidence']
   analysis_interval = timedelta(minutes=mode_config['analysis_interval_minutes'])

3. USE IN YOUR SIGNAL FILTERING:
   if signal_confidence >= min_confidence:
       # Execute trade
   else:
       # Skip trade - confidence too low for current mode

4. USE IN YOUR TIMING CONTROL:
   if current_time - last_analysis > analysis_interval:
       # Run analysis

5. USE IN YOUR SAFETY CHECKS:
   if daily_pnl <= -mode_config['daily_loss_limit']:
       # Stop trading - daily loss limit hit

6. USE IN TRADE FREQUENCY CONTROL:
   if hourly_trades < mode_config['max_trades_per_hour']:
       # Allow trade
   """)

def main():
    """Main demonstration"""
    
    # Show current mode
    mode_config = get_system_mode_config()
    print(f"Current system mode: {mode_config['mode']}")
    
    # Run example
    example_trading_loop_with_modes()
    
    # Show integration points
    show_integration_points()
    
    print("\n💡 To change modes:")
    print("   python3 switch_trading_mode.py conservative")
    print("   python3 switch_trading_mode.py moderate") 
    print("   python3 switch_trading_mode.py aggressive")

if __name__ == "__main__":
    main()