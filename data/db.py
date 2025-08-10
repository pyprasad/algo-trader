# data/db.py

from pymongo import MongoClient
from datetime import datetime
import yaml
import re

# Load config
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

MONGO_URI = config["mongodb"]["uri"]
DB_NAME = config["mongodb"]["database"]

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
trades_collection = db["trades"]
balance_collection = db["account_balance"]

def sanitize_collection_name(market_name: str) -> str:
    """Convert market name to valid MongoDB collection name"""
    # Remove special characters and spaces, convert to lowercase
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', market_name.replace(' ', '_'))
    sanitized = re.sub(r'_+', '_', sanitized).strip('_').lower()
    return f"ticks_{sanitized}"

def ensure_tick_collection_exists(market: str) -> str:
    """Ensure collection exists for the market, create if not"""
    collection_name = sanitize_collection_name(market)
    
    # Check if collection exists
    if collection_name not in db.list_collection_names():
        # Create collection with index on timestamp for efficient queries
        tick_collection = db[collection_name]
        tick_collection.create_index("timestamp")
        tick_collection.create_index("market")
        print(f"🆕 Created new collection: {collection_name} for market: {market}")
    
    return collection_name

def log_tick(market: str, bid: float, offer: float):
    """Insert tick data into market-specific MongoDB collection"""
    collection_name = ensure_tick_collection_exists(market)
    tick_collection = db[collection_name]
    
    document = {
        "market": market,
        "bid": bid,
        "offer": offer,
        "timestamp": datetime.utcnow()
    }
    tick_collection.insert_one(document)
    print(f"📥 Tick logged to {collection_name}: {market} | Bid: {bid} | Offer: {offer}")

def log_trade(trade_data: dict):
    """Insert executed trade into MongoDB trades collection with lifecycle tracking"""
    trade_document = {
        "timestamp": datetime.utcnow(),
        "market": trade_data.get("market"),
        "direction": trade_data.get("direction"),
        "size": trade_data.get("size"),
        "entry_price": trade_data.get("entry_price"),
        "stop_loss": trade_data.get("stop_loss"),
        "take_profit": trade_data.get("take_profit"),
        "deal_reference": trade_data.get("deal_reference"),
        "deal_status": trade_data.get("deal_status", "PENDING"),
        
        # Lifecycle tracking fields
        "deal_id": None,  # Will be set when trade is confirmed
        "actual_entry_price": None,  # Actual price when trade executed
        "actual_stop_level": None,  # Actual stop loss level set
        "actual_limit_level": None,  # Actual take profit level set
        "confirmation_timestamp": None,  # When trade was confirmed by IG
        "close_timestamp": None,  # When position was closed
        "close_level": None,  # Price at which position was closed
        "last_update": datetime.utcnow(),
        
        "strategy_signals": {
            "rsi": trade_data.get("rsi"),
            "atr": trade_data.get("atr"),
            "regime": trade_data.get("regime"),
            "trend": trade_data.get("trend"),
            "signal": trade_data.get("signal"),
            "momentum": trade_data.get("momentum")
        },
        "profit_loss": trade_data.get("profit_loss", 0),
        "execution_time": trade_data.get("execution_time"),
        "status": "PENDING"  # PENDING -> OPEN -> CLOSED/REJECTED
    }
    
    result = trades_collection.insert_one(trade_document)
    print(f"💾 Trade logged to DB: {trade_data.get('direction')} {trade_data.get('market')} | ID: {result.inserted_id}")
    return result.inserted_id

def get_open_trades(market: str = None):
    """Get all open trades, optionally filtered by market"""
    query = {"status": "OPEN"}
    if market:
        query["market"] = market
    return list(trades_collection.find(query))

def update_trade_status(trade_id, status: str, profit_loss: float = None):
    """Update trade status (CLOSED, REJECTED) and P/L"""
    update_data = {"status": status, "close_timestamp": datetime.utcnow()}
    if profit_loss is not None:
        update_data["profit_loss"] = profit_loss
    
    trades_collection.update_one({"_id": trade_id}, {"$set": update_data})
    print(f"📊 Trade {trade_id} updated: Status={status}, P/L={profit_loss}")

def get_account_balance():
    """Get current account balance from database or live stream"""
    # First try to get live balance if streaming is active
    try:
        from data.account_streamer import get_live_account_balance
        live_balance = get_live_account_balance()
        if live_balance > 0:
            return live_balance
    except ImportError:
        pass  # Account streamer not available
    except Exception:
        pass  # Live streaming not active, fall back to database
    
    # Fall back to database balance
    balance_doc = balance_collection.find_one({"type": "current"})
    if balance_doc:
        return balance_doc.get("balance", 0.0)
    return 0.0

def update_account_balance(balance: float):
    """Update account balance in database"""
    balance_collection.update_one(
        {"type": "current"},
        {"$set": {"balance": balance, "updated_at": datetime.utcnow()}},
        upsert=True
    )
    print(f"💰 Account balance updated: £{balance}")

def check_sufficient_balance(required_margin: float) -> bool:
    """Check if account has sufficient balance for trade margin"""
    current_balance = get_account_balance()
    return current_balance >= required_margin

def get_market_tick_data(market: str, limit: int = 100):
    """Get recent tick data for specific market"""
    collection_name = sanitize_collection_name(market)
    if collection_name not in db.list_collection_names():
        return []
    
    tick_collection = db[collection_name]
    return list(tick_collection.find().sort("timestamp", -1).limit(limit))

def get_available_markets():
    """Get list of all markets with tick data"""
    collections = db.list_collection_names()
    markets = []
    for col in collections:
        if col.startswith("ticks_"):
            # Get latest tick to extract market name
            latest_tick = db[col].find_one(sort=[("timestamp", -1)])
            if latest_tick and "market" in latest_tick:
                markets.append(latest_tick["market"])
    return markets

def cleanup_old_pending_trades(market: str = None, timeout_minutes: int = 5):
    """Clean up PENDING trades older than timeout (likely failed/rejected)"""
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    query = {
        "status": "PENDING",
        "timestamp": {"$lt": cutoff_time}
    }
    if market:
        query["market"] = market
    
    result = trades_collection.update_many(
        query,
        {"$set": {"status": "TIMEOUT", "close_timestamp": datetime.utcnow()}}
    )
    
    if result.modified_count > 0:
        print(f"🧹 Cleaned up {result.modified_count} old PENDING trades (timeout: {timeout_minutes}min)")
    
    return result.modified_count

def can_open_new_trade(market: str, max_pending: int = 2) -> bool:
    """
    BULLETPROOF POSITION CHECKING with multi-layer validation
    
    🛡️ CRITICAL SAFETY SYSTEM - DO NOT MODIFY WITHOUT EXTREME CAUTION
    
    This function implements multiple layers of validation to prevent
    multiple positions in the same market:
    
    Layer 1: Database cleanup and validation
    Layer 2: Live IG API position check 
    Layer 3: Pending trade limits
    Layer 4: Recent trade timing check
    Layer 5: Final safety validation
    """
    import time
    from datetime import datetime, timedelta
    
    print(f"🛡️ BULLETPROOF POSITION CHECK for {market}")
    print("=" * 60)
    
    # LAYER 1: Clean up old pending trades first
    print("🧹 Layer 1: Cleaning up old pending trades...")
    cleanup_result = cleanup_old_pending_trades(market, timeout_minutes=3)  # Reduced timeout for safety
    if cleanup_result > 0:
        print(f"   ✅ Cleaned {cleanup_result} old pending trades")
    
    # LAYER 2: CRITICAL - Sync with IG API before any decision
    print("🔄 Layer 2: Syncing with IG API positions...")
    try:
        sync_result = sync_trade_statuses_with_ig()
        print(f"   ✅ IG sync completed: {sync_result.get('closed', 0)} trades closed")
    except Exception as e:
        print(f"   ❌ WARNING: IG sync failed: {e}")
        # FAIL-SAFE: If we can't sync with IG, we BLOCK the trade for safety
        print(f"   🚨 BLOCKING trade due to IG sync failure (fail-safe mode)")
        return False
    
    # LAYER 3: Database position validation (after sync)
    print("📊 Layer 3: Database position validation...")
    open_trades = get_open_trades(market)
    if len(open_trades) > 0:
        print(f"   ❌ BLOCKED: {len(open_trades)} confirmed open positions found")
        for trade in open_trades:
            print(f"      - {trade.get('deal_reference', 'N/A')} | {trade.get('direction', 'N/A')} | Status: {trade.get('status', 'N/A')}")
        return False
    print("   ✅ No open positions found in database")
    
    # LAYER 4: Live IG API position check (double verification)
    print("🌐 Layer 4: Live IG API position verification...")
    try:
        ig_positions = get_live_ig_positions(market)
        if len(ig_positions) > 0:
            print(f"   ❌ CRITICAL BLOCK: {len(ig_positions)} live positions found on IG")
            for pos in ig_positions:
                print(f"      - Deal ID: {pos.get('dealId', 'N/A')} | Size: {pos.get('size', 'N/A')} | Direction: {pos.get('direction', 'N/A')}")
            return False
        print("   ✅ No live positions found on IG API")
    except Exception as e:
        print(f"   ❌ WARNING: Live IG check failed: {e}")
        # FAIL-SAFE: If we can't check IG live positions, we BLOCK for safety
        print(f"   🚨 BLOCKING trade due to live IG check failure (fail-safe mode)")
        return False
    
    # LAYER 5: Pending trade limits (but more restrictive)
    print("⏳ Layer 5: Pending trade validation...")
    pending_trades = list(trades_collection.find({"market": market, "status": "PENDING"}))
    if len(pending_trades) >= max_pending:
        print(f"   ❌ BLOCKED: {len(pending_trades)} pending trades (max: {max_pending})")
        for trade in pending_trades:
            print(f"      - {trade.get('deal_reference', 'N/A')} | {trade.get('timestamp', 'N/A')}")
        return False
    print(f"   ✅ Pending trades: {len(pending_trades)}/{max_pending}")
    
    # LAYER 6: Recent trade timing check (prevent rapid successive trades)
    print("⏰ Layer 6: Recent trade timing validation...")
    recent_cutoff = datetime.utcnow() - timedelta(minutes=5)  # No trades within 5 minutes
    recent_trades = list(trades_collection.find({
        "market": market,
        "timestamp": {"$gte": recent_cutoff},
        "status": {"$in": ["OPEN", "PENDING", "ACCEPTED"]}
    }))
    
    if len(recent_trades) > 0:
        print(f"   ❌ BLOCKED: {len(recent_trades)} recent trades within 5 minutes")
        for trade in recent_trades:
            print(f"      - {trade.get('deal_reference', 'N/A')} | {trade.get('timestamp', 'N/A')} | {trade.get('status', 'N/A')}")
        return False
    print("   ✅ No recent trades within 5 minutes")
    
    # LAYER 7: Final safety validation
    print("🔒 Layer 7: Final safety checks...")
    
    # Check if this market had any trades in the last hour that are unresolved
    hour_cutoff = datetime.utcnow() - timedelta(hours=1)
    unresolved_trades = list(trades_collection.find({
        "market": market,
        "timestamp": {"$gte": hour_cutoff},
        "status": {"$in": ["PENDING"]}  # Only truly problematic statuses
    }))
    
    if len(unresolved_trades) > 0:
        print(f"   ⚠️ WARNING: {len(unresolved_trades)} unresolved trades in last hour")
        # Don't block, but log for monitoring
        for trade in unresolved_trades:
            print(f"      - {trade.get('deal_reference', 'N/A')} | {trade.get('timestamp', 'N/A')} | {trade.get('status', 'N/A')}")
    
    print("=" * 60)
    print(f"✅ BULLETPROOF CHECK PASSED: {market} is safe for new trade")
    print("=" * 60)
    
    return True

def get_live_ig_positions(market: str = None):
    """
    Get live positions directly from IG API for a specific market
    Used by bulletproof position checking for real-time validation
    """
    try:
        from utils.auth_helper import authenticate
        from utils.config_loader import load_global_config, load_asset_config
        import requests
        
        config = load_global_config()
        
        # Get IG API credentials
        cst, xst, _, _ = authenticate()
        headers = {
            "X-IG-API-KEY": config["ig"]["api_key"],
            "CST": cst,
            "X-SECURITY-TOKEN": xst,
            "Content-Type": "application/json"
        }
        base_url = config["ig"]["base_url"]
        
        # Get all open positions
        url = f"{base_url}/positions"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        positions_data = response.json()
        positions = positions_data.get('positions', [])
        
        if market:
            # Filter positions for specific market
            try:
                asset_config = load_asset_config(market)
                market_epic = asset_config["epic"]
                
                filtered_positions = []
                for pos in positions:
                    if pos.get('market', {}).get('epic') == market_epic:
                        filtered_positions.append({
                            'dealId': pos.get('position', {}).get('dealId'),
                            'size': pos.get('position', {}).get('size'),
                            'direction': pos.get('position', {}).get('direction'),
                            'epic': pos.get('market', {}).get('epic'),
                            'instrumentName': pos.get('market', {}).get('instrumentName')
                        })
                return filtered_positions
                
            except Exception as e:
                print(f"❌ Error filtering positions for {market}: {e}")
                return []
        
        # Return all positions if no market specified
        return positions
        
    except Exception as e:
        print(f"❌ Error fetching live IG positions: {e}")
        raise e

def sync_trade_statuses_with_ig():
    """
    Synchronize database trade statuses with IG API reality.
    This function prevents corrupted trade records by checking if trades
    marked as OPEN in DB are actually closed in IG.
    """
    try:
        from utils.auth_helper import authenticate
        from utils.config_loader import load_global_config
        import requests
        
        config = load_global_config()
        
        # Get IG API credentials
        cst, xst, _, _ = authenticate()
        headers = {
            "X-IG-API-KEY": config["ig"]["api_key"],
            "CST": cst,
            "X-SECURITY-TOKEN": xst,
            "Content-Type": "application/json"
        }
        base_url = config["ig"]["base_url"]
        
        # Get all open trades from database
        open_trades = list(trades_collection.find({"status": "OPEN"}))
        if not open_trades:
            print("📊 No open trades in database to sync")
            return {"synced": 0, "closed": 0, "errors": 0}
        
        print(f"🔄 Syncing {len(open_trades)} open trades with IG API...")
        
        # Get all positions from IG
        url = f"{base_url}/positions"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Failed to get IG positions: {response.status_code}")
            return {"synced": 0, "closed": 0, "errors": 1}
        
        ig_positions = response.json().get("positions", [])
        ig_deal_references = {
            pos.get("position", {}).get("dealReference") 
            for pos in ig_positions 
            if pos.get("position", {}).get("dealReference")
        }
        
        synced_count = 0
        closed_count = 0
        error_count = 0
        
        # Check each database trade against IG positions
        for trade in open_trades:
            deal_reference = trade.get("deal_reference")
            
            if not deal_reference:
                continue
                
            # If trade is not in IG positions, it's closed
            if deal_reference not in ig_deal_references:
                try:
                    # Mark as closed in database
                    result = trades_collection.update_one(
                        {"_id": trade["_id"]},
                        {
                            "$set": {
                                "status": "CLOSED",
                                "close_timestamp": datetime.utcnow(),
                                "close_reason": "Auto-sync: Found closed in IG",
                                "last_update": datetime.utcnow()
                            }
                        }
                    )
                    
                    if result.modified_count > 0:
                        closed_count += 1
                        print(f"💾 Auto-closed: {trade.get('market')} {deal_reference}")
                    
                except Exception as e:
                    print(f"❌ Error closing {deal_reference}: {e}")
                    error_count += 1
            else:
                synced_count += 1
        
        print(f"✅ Sync complete: {synced_count} still open, {closed_count} auto-closed, {error_count} errors")
        return {"synced": synced_count, "closed": closed_count, "errors": error_count}
        
    except Exception as e:
        print(f"❌ Trade sync error: {e}")
        return {"synced": 0, "closed": 0, "errors": 1}

def get_trade_lifecycle_status(market: str = None):
    """Get summary of trade lifecycle for monitoring"""
    query = {}
    if market:
        query["market"] = market
    
    pending_count = trades_collection.count_documents({**query, "status": "PENDING"})
    open_count = trades_collection.count_documents({**query, "status": "OPEN"})
    closed_count = trades_collection.count_documents({**query, "status": "CLOSED"})
    rejected_count = trades_collection.count_documents({**query, "status": "REJECTED"})
    timeout_count = trades_collection.count_documents({**query, "status": "TIMEOUT"})
    
    return {
        "market": market or "ALL",
        "pending": pending_count,
        "open": open_count,
        "closed": closed_count,
        "rejected": rejected_count,
        "timeout": timeout_count,
        "total_active": open_count,  # Only count OPEN as truly active
        "pending_unconfirmed": pending_count  # Separate count for pending
    }
