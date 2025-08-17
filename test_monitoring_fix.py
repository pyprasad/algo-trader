#!/usr/bin/env python3
"""Test if the monitoring NoneType comparison error is fixed"""

import sys
sys.path.append('.')

from core.professional_monitor import ProfessionalTradingMonitor
from data.db import trades_collection
from datetime import datetime, timedelta

def test_monitoring_none_comparisons():
    """Test monitoring functions with None values to ensure no TypeError"""
    
    print("🧪 Testing Professional Monitor NoneType Fix")
    print("=" * 60)
    
    # Create a monitor instance
    monitor = ProfessionalTradingMonitor()
    
    # Insert test trades with None profit_loss to trigger the error condition
    test_trades = [
        {
            "timestamp": datetime.now() - timedelta(days=1),
            "market": "FTSE 100",
            "status": "CLOSED",
            "profit_loss": None,  # This should not cause comparison errors
            "entry_price": 8500,
            "stop_loss": 8490,
            "size": 2
        },
        {
            "timestamp": datetime.now() - timedelta(days=2),
            "market": "DAX",
            "status": "CLOSED", 
            "profit_loss": 10.5,  # Valid profit
            "entry_price": 18000,
            "stop_loss": 17990,
            "size": 1
        },
        {
            "timestamp": datetime.now() - timedelta(days=3),
            "market": "FTSE 100",
            "status": "CLOSED",
            "profit_loss": -5.0,  # Valid loss
            "entry_price": 8520,
            "stop_loss": 8530,
            "size": 1
        }
    ]
    
    # Clean up any existing test data
    trades_collection.delete_many({"market": {"$in": ["FTSE 100", "DAX"]}})
    
    # Insert test trades
    trades_collection.insert_many(test_trades)
    print(f"✅ Inserted {len(test_trades)} test trades")
    
    # Test the monitoring functions that previously caused errors
    try:
        print("\n🔍 Testing update_performance_metrics()...")
        monitor.update_performance_metrics()
        print("✅ update_performance_metrics() completed without errors")
        
        print("\n🔍 Testing get_performance_summary()...")
        summary = monitor.get_performance_summary()
        print("✅ get_performance_summary() completed without errors")
        print(f"   Summary keys: {list(summary.keys())}")
        
        # Test specific values that could cause None comparison errors
        if 'recent_trades' in summary:
            print(f"   Recent trades: {summary['recent_trades']}")
        if 'win_rate' in summary:
            print(f"   Win rate: {summary['win_rate']:.1%}")
            
        print("\n🔍 Testing _calculate_risk_metrics()...")
        monitor._calculate_risk_metrics()
        print("✅ _calculate_risk_metrics() completed without errors")
        
        print("\n🔍 Testing _update_trade_quality()...")
        monitor._update_trade_quality()
        print("✅ _update_trade_quality() completed without errors")
        
        print("\n✅ SUCCESS: All monitoring functions work without NoneType errors!")
        
    except TypeError as e:
        if "'>' not supported between instances of 'NoneType' and 'int'" in str(e):
            print(f"❌ FAILED: NoneType comparison error still present: {e}")
        else:
            print(f"❌ FAILED: Different TypeError: {e}")
    except Exception as e:
        print(f"⚠️ OTHER ERROR (not NoneType comparison): {e}")
    finally:
        # Clean up test data
        trades_collection.delete_many({"market": {"$in": ["FTSE 100", "DAX"]}})
        print(f"\n🧹 Cleaned up test data")

if __name__ == "__main__":
    test_monitoring_none_comparisons()