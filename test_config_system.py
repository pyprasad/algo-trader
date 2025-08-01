#!/usr/bin/env python3
# test_config_system.py - Test the configuration-driven system

import sys
import os
sys.path.append(os.path.abspath('.'))

from utils.market_config_loader import MarketConfigLoader
from runners.run_multi_market import MultiMarketTradingSystem

def test_config_system():
    """Test the configuration-driven trading system initialization"""
    print("🧪 Testing Configuration-Driven Trading System")
    print("=" * 60)
    
    try:
        # Test configuration loading
        print("\n1. Loading configuration...")
        config_loader = MarketConfigLoader()
        config_loader.print_market_summary()
        
        # Test system initialization
        print("\n2. Initializing trading system...")
        trading_system = MultiMarketTradingSystem(config_loader)
        
        # Test system status
        print("\n3. Getting system status...")
        status = trading_system.get_system_status()
        print(f"   Running: {status['running']}")
        print(f"   Markets: {status['markets']}")
        print(f"   Data Streaming: {status['data_streaming']}")
        
        print("\n✅ Configuration system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config_system()
    sys.exit(0 if success else 1)