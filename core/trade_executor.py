# core/trade_executor.py

"""
💼 Trade Executor Module

Handles:
- Market rules validation
- Dynamic SL/TP adjustment based on margin
- Trade execution via IG REST API

Author: ChatGPT Algo Team
"""

import requests
from utils.auth_helper import authenticate
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.config_loader import load_global_config, load_asset_config
from data.db import log_trade
from datetime import datetime

global_config = load_global_config()
asset_config = load_asset_config("FTSE 100")

API_KEY = global_config["ig"]["api_key"]
BASE_URL = global_config["ig"]["base_url"]
USERNAME = global_config["ig"]["username"]
PASSWORD = global_config["ig"]["password"]

MARKET_ID = asset_config["epic"]
TRADE_SIZE = asset_config["trade_size"]


# === Global Token Storage ===
CST, XST, _, _ = authenticate()
HEADERS = {
    "X-IG-API-KEY": API_KEY,
    "CST": CST,
    "X-SECURITY-TOKEN": XST,
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def get_market_details(epic):
    """
    Fetch market metadata such as min distance, trading hours, etc.
    """
    url = f"{BASE_URL}/markets/{epic}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    snapshot = data.get("snapshot", {})
    dealing_rules = data.get("dealingRules", {})

    return {
        "marketStatus": snapshot.get("marketStatus"),
        "minDistance": float(dealing_rules.get("minControlledRiskStopDistance", {}).get("value", 1)),
        "marginRequirement": float(data.get("marginDepositBands", [{}])[0].get("margin", 1)),
        "epic": epic
    }


def place_trade(direction, stop_distance, limit_distance):
    """
    Place a market trade with stop-loss and take-profit dynamically applied.
    """
    url = f"{BASE_URL}/positions/otc"
    body = {
        "epic": MARKET_ID,
        "expiry": "DFB",
        "direction": direction,  # 'BUY' or 'SELL'
        "size": TRADE_SIZE,
        "orderType": "MARKET",
        "guaranteedStop": False,
        "forceOpen": True,
        "currencyCode": "GBP",
        "stopDistance": str(stop_distance),
        "limitDistance": str(limit_distance),
        "timeInForce": "FILL_OR_KILL"
    }

    print(f"📤 Sending trade request: {direction} | SL: {stop_distance} | TP: {limit_distance}")
    response = requests.post(url, headers=HEADERS, json=body)
    response.raise_for_status()
    result = response.json()

    deal_ref = result.get("dealReference")
    print(f"✅ Trade request sent. DealRef: {deal_ref}")
    return deal_ref


def confirm_trade(deal_ref):
    """
    Confirm execution of the trade.
    """
    url = f"{BASE_URL}/confirms/{deal_ref}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    result = response.json()

    print(f"🧾 Confirmation: Status={result.get('dealStatus')} | P/L={result.get('profit')}")
    return result


def execute_trade(direction, strategy_sl=10, strategy_tp=20, strategy_signals=None):
    """
    Master function to place trade after validating market rules and log to MongoDB.
    """
    execution_start = datetime.utcnow()
    
    print("🔎 Fetching market constraints...")
    market_data = get_market_details(MARKET_ID)

    min_distance = market_data["minDistance"]
    print(f"🛡️ Market min stop distance: {min_distance}")

    # Adjust strategy SL/TP if below market minimum
    stop_distance = max(min_distance, strategy_sl)
    limit_distance = max(min_distance, strategy_tp)

    deal_ref = place_trade(direction, stop_distance, limit_distance)
    confirm = confirm_trade(deal_ref)
    
    # Log trade to MongoDB
    if confirm and confirm.get('dealStatus') in ['ACCEPTED', 'OPEN']:
        trade_data = {
            "market": "FTSE 100",
            "direction": direction,
            "size": TRADE_SIZE,
            "entry_price": confirm.get('level', 0),
            "stop_loss": stop_distance,
            "take_profit": limit_distance,
            "deal_reference": deal_ref,
            "deal_status": confirm.get('dealStatus'),
            "execution_time": (datetime.utcnow() - execution_start).total_seconds(),
            "profit_loss": confirm.get('profit', 0)
        }
        
        # Include strategy signals if provided
        if strategy_signals:
            trade_data.update(strategy_signals)
            
        log_trade(trade_data)
    
    return confirm
