#!/usr/bin/env python3
"""
Fix for phantom positions blocking trades.

This script:
1. Clears any stuck positions in the database
2. Syncs with IG API to get real position status
3. Ensures clean state for trading
"""

import requests
import yaml
from datetime import datetime, timezone
from data.db import trades_collection
import json

def clear_phantom_positions():
    """Clear any phantom positions that are blocking trades"""
    
    print("🔧 FIXING PHANTOM POSITIONS")
    print("=" * 60)
    
    # Step 1: Check database for open positions
    print("\n📊 Step 1: Checking database for open positions...")
    open_trades = list(trades_collection.find({"status": {"$in": ["OPEN", "open", "PENDING", "pending"]}}))
    
    if open_trades:
        print(f"Found {len(open_trades)} potentially stuck trades:")
        for trade in open_trades:
            print(f"  - {trade.get('reference', 'N/A')} ({trade.get('market', 'N/A')}): {trade.get('status')}")
    else:
        print("✅ No open trades found in database")
    
    # Step 2: Get session credentials
    print("\n🔑 Step 2: Getting IG session credentials...")
    try:
        with open('session_cache.json', 'r') as f:
            session = json.load(f)
    except:
        print("❌ No valid session found. Please run the trading system first.")
        return False
    headers = {
        "X-IG-API-KEY": "d3130b47b056e9c9b1e54c569bf0ba3e1b87a00a",
        "CST": session.get("CST"),
        "X-SECURITY-TOKEN": session.get("XST"),
        "Content-Type": "application/json"
    }
    
    # Step 3: Check real positions with IG API
    print("\n🔄 Step 3: Checking real positions with IG API...")
    base_url = "https://demo-api.ig.com/gateway/deal"
    
    try:
        response = requests.get(f"{base_url}/positions", headers=headers, timeout=15)
        
        if response.status_code == 200:
            ig_positions = response.json().get("positions", [])
            print(f"Found {len(ig_positions)} real positions in IG account")
            
            if ig_positions:
                for pos in ig_positions:
                    position = pos.get("position", {})
                    market = pos.get("market", {})
                    print(f"  - {position.get('dealReference')} ({market.get('instrumentName')}): "
                          f"Size={position.get('size')} @ {position.get('level')}")
            else:
                print("✅ No open positions in IG account")
                
        else:
            print(f"⚠️ Failed to get IG positions: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking IG positions: {e}")
        return False
    
    # Step 4: Clear any phantom positions
    print("\n🧹 Step 4: Clearing phantom positions...")
    
    # Get deal references from IG
    ig_deal_refs = set()
    if ig_positions:
        ig_deal_refs = {
            pos.get("position", {}).get("dealReference") 
            for pos in ig_positions 
            if pos.get("position", {}).get("dealReference")
        }
    
    # Close any database trades that don't exist in IG
    closed_count = 0
    for trade in open_trades:
        if trade.get("reference") not in ig_deal_refs:
            print(f"  Closing phantom trade: {trade.get('reference')}")
            trades_collection.update_one(
                {"_id": trade["_id"]},
                {
                    "$set": {
                        "status": "CLOSED",
                        "close_timestamp": datetime.now(timezone.utc),
                        "profit_loss": 0,
                        "close_reason": "Phantom position - not found in IG"
                    }
                }
            )
            closed_count += 1
    
    if closed_count > 0:
        print(f"✅ Closed {closed_count} phantom positions")
    else:
        print("✅ No phantom positions to clear")
    
    # Step 5: Clear any stuck PENDING trades older than 5 minutes
    print("\n🧹 Step 5: Clearing old pending trades...")
    from datetime import timedelta
    
    five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    result = trades_collection.update_many(
        {
            "status": {"$in": ["PENDING", "pending"]},
            "timestamp": {"$lt": five_minutes_ago}
        },
        {
            "$set": {
                "status": "EXPIRED",
                "close_timestamp": datetime.now(timezone.utc),
                "close_reason": "Pending trade timeout"
            }
        }
    )
    
    if result.modified_count > 0:
        print(f"✅ Cleared {result.modified_count} old pending trades")
    else:
        print("✅ No old pending trades to clear")
    
    print("\n" + "=" * 60)
    print("✅ PHANTOM POSITION FIX COMPLETE")
    print("You can now restart the trading system.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    clear_phantom_positions()