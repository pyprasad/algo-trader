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
from utils.after_hours_manager import get_after_hours_manager
from core.margin_calculator import get_margin_calculator

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
    Now includes after-hours trading support with dynamic margin and position sizing.
    """
    execution_start = datetime.utcnow()
    
    # Check if we can open a new trade for this market (no existing positions)
    if not can_open_new_trade(market_name):
        trade_status = get_trade_lifecycle_status(market_name)
        print(f"❌ TRADE BLOCKED: {market_name} has active positions - {trade_status}")
        return {"error": "Active position exists", "trade_status": trade_status}
    
    # Load market-specific config
    asset_config = load_asset_config(market_name)
    base_trade_size = asset_config["trade_size"]
    market_id = asset_config["epic"]
    
    # Get after-hours manager and margin calculator
    after_hours_mgr = get_after_hours_manager()
    margin_calc = get_margin_calculator()
    
    # Check market session and get trading parameters
    trading_params = after_hours_mgr.get_session_parameters(market_name, market_id)
    session = trading_params["session"]
    
    print(f"🕐 Market Session: {session} | Is Tradeable: {trading_params['is_tradeable']}")
    
    # Check if market is open for trading
    if not trading_params["is_tradeable"]:
        print(f"❌ TRADE BLOCKED: {market_name} is not tradeable in {session} session")
        return {"error": f"Market not tradeable in {session} session", "session": session}
    
    # Use appropriate EPIC for weekend trading
    effective_epic = trading_params["effective_epic"]
    if effective_epic != market_id:
        print(f"🔄 Using weekend EPIC: {effective_epic}")
        market_id = effective_epic
    
    # Calculate position size based on session
    position_multiplier = after_hours_mgr.get_position_size_multiplier(session)
    trade_size = base_trade_size * position_multiplier
    
    print(f"📏 Position Sizing: Base={base_trade_size}, Multiplier={position_multiplier:.1f}, Final={trade_size}")
    
    print(f"🔎 Fetching market constraints for {market_name}...")
    market_data = get_market_details(market_id)

    min_distance = market_data["minDistance"]
    base_margin_requirement = market_data["marginRequirement"]
    
    # Apply after-hours margin multiplier
    margin_multiplier = trading_params["margin_multiplier"]
    adjusted_margin_requirement = base_margin_requirement * margin_multiplier
    
    # Calculate required margin for this trade
    required_margin = trade_size * adjusted_margin_requirement
    
    print(f"🛡️ Market: {market_name} | Session: {session}")
    print(f"   Base margin: £{base_margin_requirement:.2f} | Multiplier: {margin_multiplier}x")
    print(f"   Adjusted margin: £{adjusted_margin_requirement:.2f}")
    print(f"   Total required: £{required_margin:.2f}")
    
    # Validate margin requirements using margin calculator
    can_trade, validation = margin_calc.validate_trade_margin(market_name, trade_size, market_id)
    
    if not can_trade:
        print(f"❌ MARGIN VALIDATION FAILED:")
        for reason in validation["reasons"]:
            print(f"   • {reason}")
        return {
            "error": "Margin validation failed", 
            "reasons": validation["reasons"],
            "margin_status": validation["margin_status"],
            "current_utilization": validation["current_utilization"]
        }
    
    # GLOBAL BALANCE CHECK - Critical validation before any trade
    if not check_sufficient_balance(required_margin):
        current_balance = get_account_balance()
        print(f"❌ INSUFFICIENT BALANCE: Current: £{current_balance} | Required: £{required_margin}")
        return {"error": "Insufficient balance", "required": required_margin, "current": current_balance}

    # Adjust stops/limits for session (wider during after-hours)
    adjusted_sl, adjusted_tp = after_hours_mgr.calculate_adjusted_stops(strategy_sl, strategy_tp, session)
    
    # Ensure minimum distance requirements
    stop_distance = max(min_distance, adjusted_sl)
    limit_distance = max(min_distance, adjusted_tp)
    
    print(f"📐 Stop/Limit Adjustment:")
    print(f"   Original: SL={strategy_sl}, TP={strategy_tp}")
    print(f"   Adjusted: SL={adjusted_sl:.1f}, TP={adjusted_tp:.1f}")
    print(f"   Final: SL={stop_distance:.1f}, TP={limit_distance:.1f}")

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
            "margin_used": required_margin,
            "session": session,
            "is_after_hours": session in ["pre_market", "after_hours", "weekend"],
            "position_multiplier": position_multiplier,
            "margin_multiplier": margin_multiplier,
            "effective_epic": market_id
        }
        
        # Include strategy signals if provided
        if strategy_signals:
            trade_data.update(strategy_signals)
            
        log_trade(trade_data)
        
        # Add position for emergency monitoring (if dynamic position management is enabled)
        try:
            from core.dynamic_position_manager import get_dynamic_position_manager
            dpm = get_dynamic_position_manager()
            if dpm.enabled and deal_reference:
                dpm.add_position_for_emergency_monitoring(deal_reference)
        except:
            pass  # Don't fail trade if emergency monitoring unavailable
        
        # Update account balance after successful trade
        current_balance = get_account_balance()
        new_balance = current_balance - required_margin
        update_account_balance(new_balance)
    
    return confirm
