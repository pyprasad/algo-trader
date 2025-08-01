# models/ema.py

"""
ema.py

🔹 Purpose:
Compute Exponential Moving Average (EMA) for trend filtering in our trading strategy.

📌 Note:
EMA is a basic trend detection method. We plan to upgrade to SuperTrend later
for better performance in volatile or choppy markets.

🛠️ TODO:
- Add SuperTrend logic and compare against EMA
"""

import pandas as pd

def compute_ema(series: pd.Series, span: int = 50) -> pd.Series:
    """
    Compute the Exponential Moving Average (EMA) of a given price series.

    Parameters:
        series (pd.Series): The price series (e.g., midprice)
        span (int): The smoothing window (default = 50)

    Returns:
        pd.Series: The EMA values
    """
    return series.ewm(span=span, adjust=False).mean()
