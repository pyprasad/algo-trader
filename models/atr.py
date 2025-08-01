# models/atr.py

import pandas as pd
import numpy as np

def compute_atr(price_series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute Average True Range (ATR) based on price series.

    Parameters:
    - price_series: pd.Series of midprices (or close prices)
    - period: lookback window (default: 14)

    Returns:
    - pd.Series of ATR values
    """

    # 1. Create high/low/close proxy from midprice (since we have no candles)
    # In production, this should be actual HLC data
    high = price_series.rolling(2).max()
    low = price_series.rolling(2).min()
    close = price_series.shift(1)

    # 2. Calculate True Range (TR)
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # 3. Smooth TR using EMA to get ATR
    atr = tr.ewm(span=period, adjust=False).mean()

    return atr
