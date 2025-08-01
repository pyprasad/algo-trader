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
    """Insert executed trade into MongoDB trades collection"""
    trade_document = {
        "timestamp": datetime.utcnow(),
        "market": trade_data.get("market"),
        "direction": trade_data.get("direction"),
        "size": trade_data.get("size"),
        "entry_price": trade_data.get("entry_price"),
        "stop_loss": trade_data.get("stop_loss"),
        "take_profit": trade_data.get("take_profit"),
        "deal_reference": trade_data.get("deal_reference"),
        "deal_status": trade_data.get("deal_status"),
        "strategy_signals": {
            "rsi": trade_data.get("rsi"),
            "atr": trade_data.get("atr"),
            "regime": trade_data.get("regime"),
            "trend": trade_data.get("trend"),
            "signal": trade_data.get("signal")
        },
        "profit_loss": trade_data.get("profit_loss", 0),
        "execution_time": trade_data.get("execution_time"),
        "status": "OPEN"  # OPEN, CLOSED, REJECTED
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
    """Get current account balance from database"""
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
