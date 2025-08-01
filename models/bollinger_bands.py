# models/bollinger_bands.py

import pandas as pd
import numpy as np

def compute_bollinger_bands(price_series: pd.Series, period: int = 20, std_dev: float = 2.0):
    """
    Compute Bollinger Bands.
    
    Parameters:
    - price_series: pd.Series of prices (close prices)
    - period: Moving average period (default: 20)
    - std_dev: Standard deviation multiplier (default: 2.0)
    
    Returns:
    - dict: {"upper": pd.Series, "middle": pd.Series, "lower": pd.Series, "bandwidth": pd.Series}
    """
    
    # Middle band (Simple Moving Average)
    middle_band = price_series.rolling(window=period).mean()
    
    # Standard deviation
    rolling_std = price_series.rolling(window=period).std()
    
    # Upper and lower bands
    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)
    
    # Bandwidth (measure of volatility)
    bandwidth = (upper_band - lower_band) / middle_band * 100
    
    # %B indicator (position within bands)
    percent_b = (price_series - lower_band) / (upper_band - lower_band)
    
    return {
        "upper": upper_band,
        "middle": middle_band,
        "lower": lower_band,
        "bandwidth": bandwidth,
        "percent_b": percent_b
    }

def generate_bollinger_signals(bb_data: dict, price_series: pd.Series):
    """
    Generate trading signals based on Bollinger Bands.
    
    Parameters:
    - bb_data: Output from compute_bollinger_bands()
    - price_series: Original price series
    
    Returns:
    - pd.Series: Trading signals (1=BUY, -1=SELL, 0=HOLD)
    """
    
    upper = bb_data["upper"]
    middle = bb_data["middle"]
    lower = bb_data["lower"]
    percent_b = bb_data["percent_b"]
    bandwidth = bb_data["bandwidth"]
    
    signals = pd.Series(0, index=price_series.index)
    
    for i in range(1, len(price_series)):
        current_price = price_series.iloc[i]
        prev_price = price_series.iloc[i-1]
        
        # Bollinger Bounce Strategy (mean reversion)
        # BUY when price bounces off lower band
        if (prev_price <= lower.iloc[i-1] and 
            current_price > lower.iloc[i] and 
            percent_b.iloc[i] < 0.2):  # Oversold condition
            signals.iloc[i] = 1  # BUY
        
        # SELL when price bounces off upper band
        elif (prev_price >= upper.iloc[i-1] and 
              current_price < upper.iloc[i] and 
              percent_b.iloc[i] > 0.8):  # Overbought condition
            signals.iloc[i] = -1  # SELL
        
        # Bollinger Band Squeeze breakout strategy
        # When bandwidth is low (squeeze), prepare for breakout
        elif bandwidth.iloc[i] < 10:  # Low volatility threshold
            # Breakout above upper band with volume expansion
            if current_price > upper.iloc[i] and prev_price <= upper.iloc[i-1]:
                signals.iloc[i] = 1  # BUY breakout
            # Breakdown below lower band
            elif current_price < lower.iloc[i] and prev_price >= lower.iloc[i-1]:
                signals.iloc[i] = -1  # SELL breakdown
    
    return signals