#!/usr/bin/env python3
# demo_config_system.py - Demo the configuration-driven multi-market system

import sys
import os
import time
sys.path.append(os.path.abspath('.'))

from utils.market_config_loader import MarketConfigLoader
from data.db import log_tick, get_available_markets
from core.strategy_engine import StrategyEngine

def demo_configuration_system():
    """Demonstrate the configuration-driven system"""
    print("🚀 Configuration-Driven Multi-Market System Demo")
    print("=" * 70)
    
    # Step 1: Load configuration
    print("\n📋 Step 1: Loading Market Configuration")
    config_loader = MarketConfigLoader()
    
    # Show available vs active markets
    available_markets = config_loader.get_available_markets()
    active_markets = config_loader.get_active_markets()
    valid_markets, invalid_markets = config_loader.validate_active_markets()
    
    print(f"   📊 Available markets: {len(available_markets)}")
    print(f"   🎯 Active markets: {len(active_markets)}")
    print(f"   ✅ Valid markets: {len(valid_markets)}")
    if invalid_markets:
        print(f"   ❌ Invalid markets: {invalid_markets}")
    
    # Step 2: Show market details
    print(f"\n📈 Step 2: Active Market Details")
    for market in valid_markets:
        config = config_loader.get_market_config(market)
        print(f"   {market}:")
        print(f"     Epic: {config.get('epic', 'N/A')}")
        print(f"     Trade Size: {config.get('trade_size', 'N/A')}")
        print(f"     Currency: {config.get('currency', 'N/A')}")
        print(f"     Sector: {config.get('sector', 'N/A')}")
    
    # Step 3: Simulate some tick data for each market
    print(f"\n📊 Step 3: Simulating Tick Data for Active Markets")
    import random
    
    for market in valid_markets:
        config = config_loader.get_market_config(market)
        
        # Get base price based on market type
        if config.get('sector') == 'Index':
            base_price = 7500.0
        elif config.get('sector') == 'Technology':
            base_price = 150.0
        else:
            base_price = 100.0
        
        # Generate some sample ticks
        for i in range(5):
            bid = base_price + random.uniform(-1, 1)
            offer = bid + 0.02
            log_tick(market, bid, offer)
            time.sleep(0.1)
    
    # Step 4: Show database collections created
    print(f"\n💾 Step 4: Database Collections Created")
    db_markets = get_available_markets()
    for market in db_markets:
        if market in valid_markets:
            print(f"   ✅ {market} - Tick data collection created")
    
    # Step 5: Demonstrate strategy analysis
    print(f"\n🎯 Step 5: Strategy Analysis Example")
    strategy_engine = StrategyEngine()
    
    for market in valid_markets[:2]:  # Analyze first 2 markets
        from data.db import get_market_tick_data
        tick_data = get_market_tick_data(market, limit=20)
        
        if len(tick_data) >= 5:
            prices = [tick['bid'] for tick in reversed(tick_data)]
            signals = strategy_engine.analyze_market_conditions(prices, market)
            
            if signals:
                print(f"   📈 {market}:")
                print(f"     Signal: {signals.get('signal', 'None')}")
                print(f"     RSI: {signals.get('rsi', 'N/A')}")
                print(f"     Trend: {signals.get('trend', 'N/A')}")
        else:
            print(f"   ⚠️ {market}: Not enough data for analysis")
    
    # Step 6: Show system configuration
    print(f"\n⚙️ Step 6: System Configuration")
    system_config = config_loader.get_system_config()
    risk_config = config_loader.get_risk_config()
    
    print(f"   Initial Balance: £{system_config.get('initial_balance', 'N/A')}")
    print(f"   Analysis Interval: {system_config.get('analysis_interval_seconds', 'N/A')}s")
    print(f"   Max Margin Utilization: {risk_config.get('max_margin_utilization_percent', 'N/A')}%")
    print(f"   Max Exposure Per Market: {risk_config.get('max_exposure_per_market_percent', 'N/A')}%")
    
    print("\n" + "=" * 70)
    print("✅ Configuration-driven system demo completed!")
    print("\n🎮 How to Use:")
    print("   1. Manage markets: python3.13 manage_markets.py")
    print("   2. View config: python3.13 utils/market_config_loader.py --summary")
    print("   3. Start trading: python3.13 runners/run_multi_market.py")
    print("   4. Add market: python3.13 utils/market_config_loader.py --add-market 'TSLA'")
    print("   5. Remove market: python3.13 utils/market_config_loader.py --remove-market 'DAX'")

if __name__ == "__main__":
    try:
        demo_configuration_system()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)