# data/db.py

from pymongo import MongoClient
from datetime import datetime
import yaml

# Load config
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

MONGO_URI = config["mongodb"]["uri"]
DB_NAME = config["mongodb"]["database"]
COLLECTION_NAME = config["mongodb"]["collection"]

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
trades_collection = db["trades"]

def log_tick(market: str, bid: float, offer: float):
    """Insert tick data into MongoDB"""
    document = {
        "market": market,
        "bid": bid,
        "offer": offer,
        "timestamp": datetime.utcnow()
    }
    collection.insert_one(document)
    print(f"📥 Tick logged: {market} | Bid: {bid} | Offer: {offer}")

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
