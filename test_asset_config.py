#!/usr/bin/env python3
# test_asset_config.py - Test asset configuration loading

import sys
import os
sys.path.append(os.path.abspath('.'))

from utils.config_loader import load_asset_config

def test_asset_config():
    """Test asset configuration loading for different markets"""
    print("🧪 Testing Asset Configuration Loading")
    print("=" * 50)
    
    test_markets = ["FTSE 100", "DAX", "AAPL", "GOOGL", "TSLA"]
    
    for market in test_markets:
        print(f"\n📊 Testing {market}:")
        
        try:
            config = load_asset_config(market)
            
            if not config:
                print(f"   ❌ No configuration found")
                continue
            
            print(f"   ✅ Configuration loaded successfully")
            print(f"   📈 Epic: {config.get('epic', 'MISSING')}")
            print(f"   💰 Trade Size: {config.get('trade_size', 'MISSING')}")
            print(f"   💱 Currency: {config.get('currency', 'MISSING')}")
            print(f"   🏢 Sector: {config.get('sector', 'MISSING')}")
            
            # Check required fields
            required_fields = ['epic', 'trade_size', 'currency']
            missing_fields = [field for field in required_fields if field not in config]
            
            if missing_fields:
                print(f"   ⚠️ Missing required fields: {missing_fields}")
            else:
                print(f"   ✅ All required fields present")
                
        except Exception as e:
            print(f"   ❌ Error loading configuration: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    test_asset_config()