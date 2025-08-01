# models/macd.py

import pandas as pd
import numpy as np

def compute_macd(price_series: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
    """
    Compute MACD (Moving Average Convergence Divergence) indicator.
    
    Parameters:
    - price_series: pd.Series of prices (close prices)
    - fast_period: Fast EMA period (default: 12)
    - slow_period: Slow EMA period (default: 26)
    - signal_period: Signal line EMA period (default: 9)
    
    Returns:
    - dict: {"macd": pd.Series, "signal": pd.Series, "histogram": pd.Series}
    """
    
    # Calculate fast and slow EMAs
    ema_fast = price_series.ewm(span=fast_period).mean()
    ema_slow = price_series.ewm(span=slow_period).mean()
    
    # MACD line = Fast EMA - Slow EMA
    macd_line = ema_fast - ema_slow
    
    # Signal line = EMA of MACD line
    signal_line = macd_line.ewm(span=signal_period).mean()
    
    # MACD histogram = MACD line - Signal line
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }

def generate_macd_signals(macd_data: dict, price_series: pd.Series):
    """
    Generate trading signals based on MACD crossovers.
    
    Parameters:
    - macd_data: Output from compute_macd()
    - price_series: Original price series for trend confirmation
    
    Returns:
    - pd.Series: Trading signals (1=BUY, -1=SELL, 0=HOLD)
    """
    
    macd = macd_data["macd"]
    signal = macd_data["signal"]
    histogram = macd_data["histogram"]
    
    signals = pd.Series(0, index=price_series.index)
    
    # Signal generation logic
    for i in range(1, len(macd)):
        # Bullish crossover: MACD crosses above signal line
        if macd.iloc[i] > signal.iloc[i] and macd.iloc[i-1] <= signal.iloc[i-1]:
            # Additional confirmation: MACD line should be below zero (oversold)
            if macd.iloc[i] < 0:
                signals.iloc[i] = 1  # BUY
        
        # Bearish crossover: MACD crosses below signal line
        elif macd.iloc[i] < signal.iloc[i] and macd.iloc[i-1] >= signal.iloc[i-1]:
            # Additional confirmation: MACD line should be above zero (overbought)
            if macd.iloc[i] > 0:
                signals.iloc[i] = -1  # SELL
    
    return signals