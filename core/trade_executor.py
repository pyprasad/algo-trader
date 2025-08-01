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
from data.db import log_trade, check_sufficient_balance, get_account_balance, update_account_balance, can_open_new_trade, get_trade_lifecycle_status
from datetime import datetime

global_config = load_global_config()

API_KEY = global_config["ig"]["api_key"]
BASE_URL = global_config["ig"]["base_url"]
USERNAME = global_config["ig"]["username"]
PASSWORD = global_config["ig"]["password"]


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


def place_trade(market_name, direction, stop_distance, limit_distance):
    """
    Place a market trade with stop-loss and take-profit dynamically applied.
    """
    # Load market-specific config
    asset_config = load_asset_config(market_name)
    market_id = asset_config["epic"]
    trade_size = asset_config["trade_size"]
    currency = asset_config.get("currency", "GBP")
    
    url = f"{BASE_URL}/positions/otc"
    body = {
        "epic": market_id,
        "expiry": "DFB",
        "direction": direction,  # 'BUY' or 'SELL'
        "size": trade_size,
        "orderType": "MARKET",
        "guaranteedStop": False,
        "forceOpen": True,
        "currencyCode": currency,
        "stopDistance": str(stop_distance),
        "limitDistance": str(limit_distance),
        "timeInForce": "FILL_OR_KILL"
    }

    print(f"📤 Sending trade request for {market_name}: {direction} | SL: {stop_distance} | TP: {limit_distance}")
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


def execute_trade(market_name, direction, strategy_sl=10, strategy_tp=20, strategy_signals=None):
    """
    Master function to place trade after validating market rules, balance check, and log to MongoDB.
    """
    execution_start = datetime.utcnow()
    
    # Check if we can open a new trade for this market (no existing positions)
    if not can_open_new_trade(market_name):
        trade_status = get_trade_lifecycle_status(market_name)
        print(f"❌ TRADE BLOCKED: {market_name} has active positions - {trade_status}")
        return {"error": "Active position exists", "trade_status": trade_status}
    
    # Load market-specific config
    asset_config = load_asset_config(market_name)
    trade_size = asset_config["trade_size"]
    market_id = asset_config["epic"]
    
    print(f"🔎 Fetching market constraints for {market_name}...")
    market_data = get_market_details(market_id)

    min_distance = market_data["minDistance"]
    margin_requirement = market_data["marginRequirement"]
    
    # Calculate required margin for this trade
    required_margin = trade_size * margin_requirement
    
    print(f"🛡️ Market: {market_name} | Min distance: {min_distance} | Required margin: £{required_margin}")
    
    # GLOBAL BALANCE CHECK - Critical validation before any trade
    if not check_sufficient_balance(required_margin):
        current_balance = get_account_balance()
        print(f"❌ INSUFFICIENT BALANCE: Current: £{current_balance} | Required: £{required_margin}")
        return {"error": "Insufficient balance", "required": required_margin, "current": current_balance}

    # Adjust strategy SL/TP if below market minimum
    stop_distance = max(min_distance, strategy_sl)
    limit_distance = max(min_distance, strategy_tp)

    deal_ref = place_trade(market_name, direction, stop_distance, limit_distance)
    confirm = confirm_trade(deal_ref)
    
    # Log trade to MongoDB
    if confirm and confirm.get('dealStatus') in ['ACCEPTED', 'OPEN']:
        trade_data = {
            "market": market_name,
            "direction": direction,
            "size": trade_size,
            "entry_price": confirm.get('level', 0),
            "stop_loss": stop_distance,
            "take_profit": limit_distance,
            "deal_reference": deal_ref,
            "deal_status": confirm.get('dealStatus'),
            "execution_time": (datetime.utcnow() - execution_start).total_seconds(),
            "profit_loss": confirm.get('profit', 0),
            "margin_used": required_margin
        }
        
        # Include strategy signals if provided
        if strategy_signals:
            trade_data.update(strategy_signals)
            
        log_trade(trade_data)
        
        # Update account balance after successful trade
        current_balance = get_account_balance()
        new_balance = current_balance - required_margin
        update_account_balance(new_balance)
    
    return confirm
