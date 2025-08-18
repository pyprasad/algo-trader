#!/usr/bin/env python3
"""
Reset trading blocks and cooling off periods
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from data.db import trades_collection
from pymongo import MongoClient
from datetime import datetime
import yaml

def reset_trading_blocks():
    """Reset all trading blocks and cooling off periods"""
    
    print("🔧 RESETTING TRADING BLOCKS...")
    print("="*50)
    
    try:
        # Clear any market suspension records
        client = MongoClient("mongodb://127.0.0.1:27017")
        db = client.ftse100_scalping_bot
        
        # Clear collections that might store suspension state
        collections_to_clear = [
            'market_suspensions',
            'consecutive_losses', 
            'cooling_off_periods',
            'daily_losses',
            'market_performance'
        ]
        
        for coll_name in collections_to_clear:
            if coll_name in db.list_collection_names():
                result = db[coll_name].delete_many({})
                print(f"✅ Cleared {coll_name}: {result.deleted_count} records")
            else:
                print(f"ℹ️ Collection {coll_name} doesn't exist (OK)")
        
        # Update the active configuration to use trading_enabled.yaml
        print("\n🔧 UPDATING CONFIGURATION...")
        
        # Copy our trading enabled config to the active market config
        with open('configs/trading_enabled.yaml', 'r') as f:
            enabled_config = f.read()
        
        with open('configs/market_specific_strategy.yaml', 'w') as f:
            f.write(enabled_config)
        
        print("✅ Updated market_specific_strategy.yaml with trading-enabled config")
        
        print("\n" + "="*50)
        print("🎯 TRADING BLOCKS RESET COMPLETE!")
        print("="*50)
        print("\n✅ ALL PROTECTIVE MECHANISMS DISABLED:")
        print("   - DAX cooling off period: CLEARED")
        print("   - Consecutive loss limits: DISABLED (999)")
        print("   - Daily loss limits: DISABLED (99999)")
        print("   - Signal confidence thresholds: LOWERED (0.1)")
        print("   - ML prediction failures: BYPASSED")
        print("   - Market suspensions: DISABLED")
        print("   - Trend confirmation: DISABLED")
        print("   - Smart Money concepts: DISABLED")
        print("   - Advanced ML: DISABLED")
        print("\n🚨 WARNING: Trading is now VERY AGGRESSIVE")
        print("   - Use small position sizes")
        print("   - Monitor closely")
        print("   - 1 trade per market rule still enforced")
        print("\n💡 Ready to start trading system!")
        
    except Exception as e:
        print(f"❌ Error resetting blocks: {e}")

if __name__ == "__main__":
    reset_trading_blocks()