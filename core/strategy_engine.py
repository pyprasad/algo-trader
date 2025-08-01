# core/strategy_engine.py

import pandas as pd
from datetime import datetime, timedelta
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.regime_model import detect_regime
from core.signal_classifier import generate_trade_signal
from data.db import collection as mongo_collection
from models.ema import compute_ema
import yaml
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Load strategy config
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

RSI_PERIOD = config["strategy"]["rsi_period"]
BUY_THRESHOLD = config["strategy"]["rsi_buy_threshold"]
SELL_THRESHOLD = config["strategy"]["rsi_sell_threshold"]
DYNAMIC_ATR_SLTP = config["strategy"]["dynamic_atr_sltp"]

# Core strategy function
def run_strategy(asset="FTSE 100", lookback_minutes=60, timeframe='1min'):
    """
    Runs the full strategy pipeline:
    - Fetches historical ticks from Mongo
    - Computes RSI & ATR
    - Detects market regime
    - Classifies trade signal
    """

    # 1. Load recent tick data from MongoDB
    since = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    cursor = mongo_collection.find(
        {"market": asset, "timestamp": {"$gte": since}}
    ).sort("timestamp", 1)

    ticks = list(cursor)
    if len(ticks) < RSI_PERIOD + 5:
        print("❌ Not enough data to compute indicators.")
        return None

    df = pd.DataFrame(ticks)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)

    # 2. Compute Midprice, RSI, ATR
    df["midprice"] = (df["bid"] + df["offer"]) / 2
    df["rsi"] = compute_rsi(df["midprice"], period=RSI_PERIOD)
    df["atr"] = compute_atr(df["midprice"]) if DYNAMIC_ATR_SLTP else None

    # 2.5 Compute EMA for trend filtering
    df["ema"] = compute_ema(df["midprice"], span=50)
    latest_ema = df["ema"].iloc[-1]
    latest_price = df["midprice"].iloc[-1]

    # Trend Filter using EMA
    if latest_price > latest_ema:
        trend = "uptrend"
    elif latest_price < latest_ema:
        trend = "downtrend"
    else:
        trend = "sideways"

    print(f" - Trend (EMA): {trend}")

    # 3. Detect Market Regime using HMM
    regime = detect_regime(df["midprice"])

    # 4. Generate Trade Signal (BUY/SELL/HOLD)
    latest = df.iloc[-1]
    signal = generate_trade_signal(
        rsi=latest["rsi"],
        atr=latest["atr"] if DYNAMIC_ATR_SLTP else None,
        regime=regime,
        thresholds=(BUY_THRESHOLD, SELL_THRESHOLD),
        trend=trend
    )

    # 5. Logging the decision
    print(f"📊 {asset} | Time: {latest.name}")
    print(f" - RSI: {latest['rsi']:.2f} | ATR: {latest['atr'] if DYNAMIC_ATR_SLTP else 'N/A'}")
    print(f" - Regime: {regime}")
    print(f" - Trade Signal: {signal}")

    # 6. Return signal and strategy context for logging
    strategy_context = {
        "rsi": float(latest["rsi"]),
        "atr": float(latest["atr"]) if DYNAMIC_ATR_SLTP else None,
        "regime": regime,
        "trend": trend,
        "signal": signal
    }

    return signal, strategy_context
