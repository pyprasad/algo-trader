#!/usr/bin/env python3
"""
🧪 Test PENDING Trade Handling

Tests the improved PENDING trade logic to ensure:
1. PENDING trades don't block new trading opportunities
2. Old PENDING trades get cleaned up (timeout)
3. System allows reasonable number of PENDING trades
4. Only OPEN trades truly block new trades
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from data.db import (
    trades_collection, 
    can_open_new_trade, 
    cleanup_old_pending_trades,
    get_trade_lifecycle_status,
    log_trade
)
from datetime import datetime, timedelta

def test_pending_trade_handling():
    """Test the enhanced PENDING trade handling"""
    print("🧪 Testing PENDING Trade Handling")
    print("=" * 50)
    
    test_market = "TEST_DAX"
    
    # Clean up any existing test trades
    trades_collection.delete_many({"market": test_market})
    
    print(f"\n1️⃣ Testing: Fresh market allows new trades")
    can_trade = can_open_new_trade(test_market)
    print(f"   ✅ Fresh market can trade: {can_trade}")
    assert can_trade == True, "Fresh market should allow trading"
    
    print(f"\n2️⃣ Testing: PENDING trades don't block new trades (up to limit)")
    
    # Add first PENDING trade
    pending_trade_1 = {
        "market": test_market,
        "direction": "BUY",
        "size": 1,
        "entry_price": 23500,
        "deal_reference": "TEST_REF_1",
        "deal_status": "ACCEPTED"
    }
    log_trade(pending_trade_1)
    
    can_trade = can_open_new_trade(test_market)
    print(f"   ✅ With 1 PENDING trade, can still trade: {can_trade}")
    assert can_trade == True, "Should allow trading with 1 PENDING trade"
    
    # Add second PENDING trade
    pending_trade_2 = {
        "market": test_market,
        "direction": "SELL", 
        "size": 1,
        "entry_price": 23400,
        "deal_reference": "TEST_REF_2",
        "deal_status": "ACCEPTED"
    }
    log_trade(pending_trade_2)
    
    can_trade = can_open_new_trade(test_market, max_pending=3)  # Allow up to 3 pending
    print(f"   ✅ With 2 PENDING trades, can still trade: {can_trade}")
    assert can_trade == True, "Should allow trading with 2 PENDING trades (under limit of 3)"
    
    # Add third PENDING trade - should be blocked when we reach max_pending=3
    pending_trade_3 = {
        "market": test_market,
        "direction": "BUY", 
        "size": 1,
        "entry_price": 23300,
        "deal_reference": "TEST_REF_3",
        "deal_status": "ACCEPTED"
    }
    log_trade(pending_trade_3)
    
    can_trade = can_open_new_trade(test_market, max_pending=3)
    print(f"   ❌ With 3 PENDING trades at max limit: {can_trade}")
    assert can_trade == False, "Should NOT allow trading when at max_pending limit (3/3)"
    
    print(f"\n3️⃣ Testing: OPEN trades block new trades")
    
    # Update one PENDING to OPEN
    trades_collection.update_one(
        {"market": test_market, "deal_reference": "TEST_REF_1"},
        {"$set": {"status": "OPEN"}}
    )
    
    can_trade = can_open_new_trade(test_market)
    print(f"   ❌ With 1 OPEN trade, can trade: {can_trade}")
    assert can_trade == False, "Should NOT allow trading with OPEN position"
    
    print(f"\n4️⃣ Testing: Old PENDING trades get cleaned up")
    
    # Reset test - remove OPEN trade
    trades_collection.update_one(
        {"market": test_market, "deal_reference": "TEST_REF_1"},
        {"$set": {"status": "PENDING"}}
    )
    
    # Make one PENDING trade old (more than 5 minutes)
    old_timestamp = datetime.utcnow() - timedelta(minutes=10)
    trades_collection.update_one(
        {"market": test_market, "deal_reference": "TEST_REF_1"},
        {"$set": {"timestamp": old_timestamp}}
    )
    
    print(f"   🧹 Cleaning up old PENDING trades...")
    cleaned_count = cleanup_old_pending_trades(test_market, timeout_minutes=5)
    print(f"   ✅ Cleaned up {cleaned_count} old PENDING trades")
    
    # Check if old trade was marked as TIMEOUT
    old_trade = trades_collection.find_one({"market": test_market, "deal_reference": "TEST_REF_1"})
    print(f"   ✅ Old trade status changed to: {old_trade['status']}")
    assert old_trade['status'] == "TIMEOUT", "Old PENDING trade should be marked as TIMEOUT"
    
    print(f"\n5️⃣ Testing: Trade lifecycle status reporting")
    
    status = get_trade_lifecycle_status(test_market)
    print(f"   Trade Lifecycle Status for {test_market}:")
    print(f"      Pending: {status['pending']}")
    print(f"      Open: {status['open']}")
    print(f"      Timeout: {status['timeout']}")
    print(f"      Total Active: {status['total_active']}")
    print(f"      Pending Unconfirmed: {status['pending_unconfirmed']}")
    
    # Should have 2 PENDING (TEST_REF_2, TEST_REF_3) and 1 TIMEOUT (TEST_REF_1)
    assert status['pending'] == 2, f"Should have 2 PENDING, got {status['pending']}"
    assert status['timeout'] == 1, f"Should have 1 TIMEOUT, got {status['timeout']}"
    assert status['total_active'] == 0, f"Should have 0 active (only OPEN counts), got {status['total_active']}"
    
    print(f"\n6️⃣ Testing: Can trade again after cleanup")
    
    # We still have 2 PENDING trades, so with default max_pending=2, it should be blocked
    can_trade = can_open_new_trade(test_market, max_pending=2)
    print(f"   ❌ With 2 PENDING trades at max_pending=2: {can_trade}")
    assert can_trade == False, "Should NOT allow trading with 2 PENDING at max_pending=2"
    
    # But with higher limit, should allow
    can_trade = can_open_new_trade(test_market, max_pending=3)
    print(f"   ✅ With 2 PENDING trades under max_pending=3: {can_trade}")
    assert can_trade == True, "Should allow trading with 2 PENDING under max_pending=3"
    
    # Clean up test data
    trades_collection.delete_many({"market": test_market})
    
    print(f"\n✅ All PENDING Trade Handling Tests Passed!")
    print("=" * 50)
    print("🎯 Key Improvements:")
    print("   • PENDING trades don't block new opportunities")
    print("   • Old PENDING trades auto-cleanup after 5 minutes")
    print("   • Allow up to 2 PENDING trades per market")
    print("   • Only OPEN trades truly block new trading")
    print("   • Better trade lifecycle monitoring")

if __name__ == "__main__":
    test_pending_trade_handling()