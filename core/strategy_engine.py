# core/strategy_engine.py

import pandas as pd
from datetime import datetime, timedelta
from models.rsi import compute_rsi
from models.atr import compute_atr
from models.regime_model import detect_regime
from core.signal_classifier import generate_trade_signal
from data.db import db, sanitize_collection_name
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

    # 1. Load recent tick data from market-specific MongoDB collection
    since = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    collection_name = sanitize_collection_name(asset)
    
    # Check if collection exists
    if collection_name not in db.list_collection_names():
        print(f"❌ No tick data found for {asset} (collection: {collection_name})")
        return None
    
    tick_collection = db[collection_name]
    cursor = tick_collection.find(
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


class StrategyEngine:
    """
    Multi-market strategy engine for analyzing trading signals
    """
    
    def __init__(self):
        # Load strategy config
        with open("configs/global.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        self.rsi_period = config["strategy"]["rsi_period"]
        self.buy_threshold = config["strategy"]["rsi_buy_threshold"]
        self.sell_threshold = config["strategy"]["rsi_sell_threshold"]
        self.dynamic_atr_sltp = config["strategy"]["dynamic_atr_sltp"]
    
    def analyze_market_conditions(self, prices, market_name=None):
        """
        Analyze market conditions from a list of prices
        
        Args:
            prices (list): List of prices (most recent last)
            market_name (str): Optional market name for logging
            
        Returns:
            dict: Strategy signals and indicators
        """
        if len(prices) < self.rsi_period + 5:
            if market_name:
                print(f"❌ {market_name}: Not enough price data for analysis ({len(prices)} prices)")
            return None
        
        # Convert to pandas DataFrame
        df = pd.DataFrame({'price': prices})
        df.index = pd.date_range(end=datetime.utcnow(), periods=len(prices), freq='1min')
        
        # Compute indicators
        df["rsi"] = compute_rsi(df["price"], period=self.rsi_period)
        df["atr"] = compute_atr(df["price"]) if self.dynamic_atr_sltp else None
        df["ema"] = compute_ema(df["price"], span=50)
        
        # Get latest values
        latest = df.iloc[-1]
        latest_price = latest["price"]
        latest_ema = latest["ema"]
        
        # Determine trend
        if latest_price > latest_ema:
            trend = "uptrend"
        elif latest_price < latest_ema:
            trend = "downtrend"
        else:
            trend = "sideways"
        
        # Detect market regime
        regime = detect_regime(df["price"])
        
        # Generate trade signal
        signal = generate_trade_signal(
            rsi=latest["rsi"],
            atr=latest["atr"] if self.dynamic_atr_sltp else None,
            regime=regime,
            thresholds=(self.buy_threshold, self.sell_threshold),
            trend=trend
        )
        
        # Create strategy context
        strategy_context = {
            "rsi": float(latest["rsi"]) if pd.notna(latest["rsi"]) else None,
            "atr": float(latest["atr"]) if self.dynamic_atr_sltp and pd.notna(latest["atr"]) else None,
            "regime": regime,
            "trend": trend,
            "signal": signal,
            "price": float(latest_price)
        }
        
        return strategy_context
