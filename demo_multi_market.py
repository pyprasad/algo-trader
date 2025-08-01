#!/usr/bin/env python3
# demo_multi_market.py - Demo of multi-market functionality

import sys
import os
import time
sys.path.append(os.path.abspath('.'))

from data.db import (
    log_tick, 
    get_available_markets, 
    get_market_tick_data,
    update_account_balance,
    get_account_balance
)
from core.strategy_engine import StrategyEngine
from utils.balance_manager import BalanceManager

def simulate_market_data():
    """Simulate tick data for multiple markets"""
    print("📊 Simulating tick data for multiple markets...")
    
    markets = {
        "AAPL": {"base_price": 150.0, "volatility": 0.5},
        "GOOGL": {"base_price": 2800.0, "volatility": 10.0},
        "FTSE 100": {"base_price": 7500.0, "volatility": 5.0}
    }
    
    import random
    
    for i in range(20):  # Generate 20 ticks per market
        for market, config in markets.items():
            base = config["base_price"]
            vol = config["volatility"]
            
            # Simulate price movement
            change = random.uniform(-vol, vol)
            bid = base + change - 0.1
            offer = base + change + 0.1
            
            log_tick(market, bid, offer)
        
        time.sleep(0.1)  # Small delay between ticks
    
    print("✅ Market data simulation complete")

def demonstrate_multi_market_analysis():
    """Demonstrate strategy analysis across multiple markets"""
    print("\n🎯 Demonstrating multi-market strategy analysis...")
    
    available_markets = get_available_markets()
    print(f"Available markets: {available_markets}")
    
    strategy_engine = StrategyEngine()
    
    for market in available_markets:
        print(f"\n--- Analyzing {market} ---")
        
        # Get recent tick data
        tick_data = get_market_tick_data(market, limit=30)
        
        if len(tick_data) < 20:
            print(f"⚠️ Not enough data for {market} ({len(tick_data)} ticks)")
            continue
        
        # Extract bid prices for analysis
        prices = [tick['bid'] for tick in reversed(tick_data)]
        
        # Analyze market conditions
        signals = strategy_engine.analyze_market_conditions(prices, market)
        
        if signals:
            print(f"📈 {market} Analysis:")
            print(f"   Signal: {signals.get('signal', 'None')}")
            print(f"   RSI: {signals.get('rsi', 'N/A')}")
            print(f"   Trend: {signals.get('trend', 'N/A')}")
            print(f"   Price: {signals.get('price', 'N/A')}")
        else:
            print(f"❌ Could not analyze {market}")

def demonstrate_balance_management():
    """Demonstrate balance management features"""
    print("\n💰 Demonstrating balance management...")
    
    manager = BalanceManager()
    
    # Set initial balance
    manager.set_initial_balance(10000.0)
    
    # Show account summary
    manager.print_account_summary()
    
    # Test margin check
    required_margin = 500.0
    can_trade = manager.check_margin_requirement(required_margin)
    print(f"\nCan trade with £{required_margin} margin? {'✅ Yes' if can_trade else '❌ No'}")

def main():
    """Run multi-market demonstration"""
    print("🚀 Multi-Market Trading System Demo")
    print("=" * 60)
    
    try:
        # Step 1: Set up initial balance
        print("1. Setting up account balance...")
        update_account_balance(10000.0)
        balance = get_account_balance()
        print(f"   Initial balance: £{balance}")
        
        # Step 2: Simulate market data
        print("\n2. Simulating market data...")
        simulate_market_data()
        
        # Step 3: Show available markets
        print("\n3. Available markets with data:")
        markets = get_available_markets()
        for market in markets:
            tick_count = len(get_market_tick_data(market, limit=1000))
            print(f"   {market}: {tick_count} ticks")
        
        # Step 4: Demonstrate strategy analysis
        demonstrate_multi_market_analysis()
        
        # Step 5: Demonstrate balance management
        demonstrate_balance_management()
        
        print("\n" + "=" * 60)
        print("✅ Multi-market demo completed successfully!")
        print("\nTo start live trading:")
        print("  python3.13 runners/run_multi_market.py")
        print("\nTo manage balance:")
        print("  python3.13 utils/balance_manager.py --summary")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)