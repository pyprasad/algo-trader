#!/usr/bin/env python3
"""
🔧 Trade Database Migration & Sync Script

This script fixes corrupted trade records by:
1. Finding trades marked as OPEN but actually closed
2. Synchronizing database with IG API reality
3. Cleaning up trade lifecycle inconsistencies

Usage: python fix_corrupted_trades.py [--dry-run]

Author: Database Migration Tool
"""

import sys
import os
from datetime import datetime, timedelta
import requests
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from data.db import trades_collection
from utils.auth_helper import authenticate
from utils.config_loader import load_global_config

config = load_global_config()

class TradeDatabaseFixer:
    """Fixes corrupted trade records in the database"""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.fixed_count = 0
        self.errors = []
        
        # Initialize IG API connection
        try:
            self.cst, self.xst, _, _ = authenticate()
            self.headers = {
                "X-IG-API-KEY": config["ig"]["api_key"],
                "CST": self.cst,
                "X-SECURITY-TOKEN": self.xst,
                "Content-Type": "application/json"
            }
            self.base_url = config["ig"]["base_url"]
            print("✅ IG API connection established")
        except Exception as e:
            print(f"❌ Failed to connect to IG API: {e}")
            self.headers = None
    
    def find_corrupted_trades(self):
        """Find trades that appear to be corrupted"""
        print("🔍 Scanning for corrupted trade records...")
        
        # Find trades that are marked as OPEN but are old (likely closed)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Trades older than 24 hours
        
        corrupted_trades = list(trades_collection.find({
            "status": {"$in": ["OPEN", "PENDING"]},
            "timestamp": {"$lt": cutoff_time}
        }))
        
        print(f"📊 Found {len(corrupted_trades)} potentially corrupted trades")
        return corrupted_trades
    
    def get_position_from_ig(self, deal_reference):
        """Check if position exists in IG API"""
        if not self.headers:
            return None
        
        try:
            # Get all positions from IG
            url = f"{self.base_url}/positions"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                positions = response.json().get("positions", [])
                
                # Look for this deal reference
                for position in positions:
                    if position.get("position", {}).get("dealReference") == deal_reference:
                        return position
                
                return None  # Position not found = it's closed
            else:
                print(f"⚠️ IG API error: {response.status_code}")
                return "unknown"
                
        except Exception as e:
            print(f"❌ Error checking IG position {deal_reference}: {e}")
            return "unknown"
        
        time.sleep(0.1)  # Rate limiting
    
    def fix_trade_record(self, trade):
        """Fix a single corrupted trade record"""
        deal_reference = trade.get("deal_reference")
        trade_id = trade.get("_id")
        market = trade.get("market")
        
        print(f"🔧 Fixing trade: {market} {deal_reference}")
        
        # Check current status in IG
        ig_position = self.get_position_from_ig(deal_reference)
        
        if ig_position is None:
            # Position not found in IG = it's closed
            print(f"   ✅ Position {deal_reference} is closed in IG")
            
            if not self.dry_run:
                # Update database to mark as closed
                result = trades_collection.update_one(
                    {"_id": trade_id},
                    {
                        "$set": {
                            "status": "CLOSED",
                            "close_timestamp": datetime.utcnow(),
                            "last_update": datetime.utcnow(),
                            "close_reason": "Migration: Found closed in IG",
                            "profit_loss": 0  # We don't know the actual P/L
                        }
                    }
                )
                
                if result.modified_count > 0:
                    print(f"   💾 Database updated: OPEN -> CLOSED")
                    self.fixed_count += 1
                else:
                    print(f"   ❌ Failed to update database")
                    self.errors.append(f"Failed to update {deal_reference}")
            else:
                print(f"   [DRY RUN] Would mark {deal_reference} as CLOSED")
                self.fixed_count += 1
                
        elif ig_position == "unknown":
            # API error - mark as unknown but likely closed if old enough
            trade_age = datetime.utcnow() - trade.get("timestamp", datetime.utcnow())
            if trade_age.total_seconds() > 86400:  # Older than 24 hours
                print(f"   ⚠️ Old trade {deal_reference}, marking as closed due to age")
                
                if not self.dry_run:
                    result = trades_collection.update_one(
                        {"_id": trade_id},
                        {
                            "$set": {
                                "status": "CLOSED",
                                "close_timestamp": datetime.utcnow(),
                                "last_update": datetime.utcnow(),
                                "close_reason": "Migration: Old trade, likely closed",
                                "profit_loss": 0
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        self.fixed_count += 1
                    else:
                        self.errors.append(f"Failed to update old trade {deal_reference}")
                else:
                    self.fixed_count += 1
            else:
                print(f"   ⏸️ Recent trade, keeping as is")
        else:
            # Position still exists in IG
            print(f"   ✅ Position {deal_reference} still active in IG")
    
    def run_migration(self):
        """Run the complete migration process"""
        print("🚀 Starting Trade Database Migration")
        print("=" * 50)
        
        if self.dry_run:
            print("🧪 DRY RUN MODE - No changes will be made")
        
        # Find corrupted trades
        corrupted_trades = self.find_corrupted_trades()
        
        if not corrupted_trades:
            print("✅ No corrupted trades found!")
            return
        
        print(f"\n🔧 Processing {len(corrupted_trades)} corrupted trades...")
        
        for i, trade in enumerate(corrupted_trades, 1):
            try:
                print(f"\n[{i}/{len(corrupted_trades)}]", end=" ")
                self.fix_trade_record(trade)
            except Exception as e:
                error_msg = f"Error fixing trade {trade.get('deal_reference', 'unknown')}: {e}"
                print(f"   ❌ {error_msg}")
                self.errors.append(error_msg)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Migration Summary:")
        print(f"   ✅ Fixed trades: {self.fixed_count}")
        print(f"   ❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print("\n⚠️ Errors encountered:")
            for error in self.errors:
                print(f"   • {error}")
        
        if not self.dry_run:
            print("\n✅ Migration completed! Database should now be consistent.")
            print("💡 Run the trading system again to verify the fix.")
        else:
            print(f"\n🧪 DRY RUN COMPLETE")
            print(f"💡 Run without --dry-run to apply these {self.fixed_count} fixes.")

def main():
    """Main entry point"""
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🧪 Running in DRY RUN mode - no changes will be made")
    
    # Create and run the fixer
    fixer = TradeDatabaseFixer(dry_run=dry_run)
    fixer.run_migration()

if __name__ == "__main__":
    main()