#!/usr/bin/env python3
# test_streaming_fix.py - Test the streaming fix for multiple markets

import sys
import os
sys.path.append(os.path.abspath('.'))

from data.multi_market_collector import MultiMarketCollector
from utils.config_loader import load_asset_config

def test_subscription_creation():
    """Test subscription creation for multiple markets"""
    print("🧪 Testing Multi-Market Subscription Creation")
    print("=" * 60)
    
    test_markets = ["FTSE 100", "DAX"]
    
    # Test configuration loading first
    print("\n📋 Step 1: Testing Configuration Loading")
    for market in test_markets:
        config = load_asset_config(market)
        if config and 'epic' in config:
            print(f"   ✅ {market}: {config['epic']}")
        else:
            print(f"   ❌ {market}: Configuration issue")
    
    # Test collector initialization
    print(f"\n📊 Step 2: Testing Collector Initialization")
    try:
        collector = MultiMarketCollector(test_markets)
        print(f"   ✅ Collector initialized with markets: {collector.markets}")
    except Exception as e:
        print(f"   ❌ Collector initialization failed: {e}")
        return False
    
    # Test subscription creation (without connecting)
    print(f"\n🔗 Step 3: Testing Subscription Creation")
    for market in test_markets:
        try:
            subscription = collector.create_market_subscription(market)
            if subscription:
                print(f"   ✅ {market}: Subscription created successfully")
            else:
                print(f"   ❌ {market}: Subscription creation failed")
        except Exception as e:
            print(f"   ❌ {market}: Error creating subscription - {e}")
    
    print("\n" + "=" * 60)
    print("✅ Subscription creation test completed!")
    print("\nNote: This test only checks subscription creation, not actual streaming.")
    print("To test actual streaming, run: python3.13 runners/run_multi_market.py")
    
    return True

if __name__ == "__main__":
    try:
        success = test_subscription_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)