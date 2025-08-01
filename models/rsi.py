# models/rsi.py

import pandas as pd

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute the Relative Strength Index (RSI).

    Parameters:
    - series: pd.Series of prices (typically midprice or close)
    - period: lookback window (default: 14)

    Returns:
    - pd.Series of RSI values
    """

    # 1. Calculate price changes between bars
    delta = series.diff()

    # 2. Separate gains (positive) and losses (negative)
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # 3. Calculate average gain and loss using exponential moving average (EMA)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    # 4. Calculate relative strength (RS)
    rs = avg_gain / avg_loss

    # 5. Calculate RSI using RS formula
    rsi = 100 - (100 / (1 + rs))

    # 6. Fill in initial values with NaN or zero
    rsi = rsi.fillna(0)

    return rsi
