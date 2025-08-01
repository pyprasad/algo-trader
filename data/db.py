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
    Check if we can open a new trade for this market
    - Only OPEN trades block new trades (confirmed positions)
    - Allow limited PENDING trades (they may timeout/fail)
    - Clean up old PENDING trades automatically
    """
    # First, clean up old pending trades
    cleanup_old_pending_trades(market)
    
    # Only count OPEN trades as blocking (confirmed positions)
    open_trades = get_open_trades(market)
    if len(open_trades) > 0:
        print(f"⚠️ Cannot open new {market} trade: {len(open_trades)} confirmed open positions")
        return False
    
    # Allow limited PENDING trades (they may fail/timeout)
    pending_trades = list(trades_collection.find({"market": market, "status": "PENDING"}))
    if len(pending_trades) >= max_pending:
        print(f"⚠️ Cannot open new {market} trade: {len(pending_trades)} pending trades (max: {max_pending})")
        return False
    
    return True

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
