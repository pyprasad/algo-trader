# models/stochastic.py

import pandas as pd
import numpy as np

def compute_stochastic(high_series: pd.Series, low_series: pd.Series, close_series: pd.Series, 
                      k_period: int = 14, d_period: int = 3, smooth_k: int = 3):
    """
    Compute Stochastic Oscillator.
    
    Parameters:
    - high_series: pd.Series of high prices
    - low_series: pd.Series of low prices  
    - close_series: pd.Series of close prices
    - k_period: Period for %K calculation (default: 14)
    - d_period: Period for %D smoothing (default: 3)
    - smooth_k: Period for smoothing %K (default: 3)
    
    Returns:
    - dict: {"percent_k": pd.Series, "percent_d": pd.Series}
    """
    
    # Calculate raw %K
    lowest_low = low_series.rolling(window=k_period).min()
    highest_high = high_series.rolling(window=k_period).max()
    
    raw_k = ((close_series - lowest_low) / (highest_high - lowest_low)) * 100
    
    # Smooth %K
    percent_k = raw_k.rolling(window=smooth_k).mean()
    
    # Calculate %D (signal line)
    percent_d = percent_k.rolling(window=d_period).mean()
    
    return {
        "percent_k": percent_k,
        "percent_d": percent_d
    }

def generate_stochastic_signals(stoch_data: dict, oversold_level: float = 20, overbought_level: float = 80):
    """
    Generate trading signals based on Stochastic Oscillator.
    
    Parameters:
    - stoch_data: Output from compute_stochastic()
    - oversold_level: Oversold threshold (default: 20)
    - overbought_level: Overbought threshold (default: 80)
    
    Returns:
    - pd.Series: Trading signals (1=BUY, -1=SELL, 0=HOLD)
    """
    
    percent_k = stoch_data["percent_k"]
    percent_d = stoch_data["percent_d"]
    
    signals = pd.Series(0, index=percent_k.index)
    
    for i in range(1, len(percent_k)):
        # Bullish signal: %K crosses above %D in oversold territory
        if (percent_k.iloc[i] > percent_d.iloc[i] and 
            percent_k.iloc[i-1] <= percent_d.iloc[i-1] and 
            percent_k.iloc[i] < oversold_level + 10):  # Near oversold
            signals.iloc[i] = 1  # BUY
        
        # Bearish signal: %K crosses below %D in overbought territory
        elif (percent_k.iloc[i] < percent_d.iloc[i] and 
              percent_k.iloc[i-1] >= percent_d.iloc[i-1] and 
              percent_k.iloc[i] > overbought_level - 10):  # Near overbought
            signals.iloc[i] = -1  # SELL
    
    return signals

def compute_stochastic_from_price(price_series: pd.Series, k_period: int = 14, d_period: int = 3, smooth_k: int = 3):
    """
    Compute Stochastic from a single price series (using price as high, low, close).
    Useful when only midprice/close data is available.
    """
    
    # Create synthetic high/low from price movements
    high_proxy = price_series.rolling(window=2).max()
    low_proxy = price_series.rolling(window=2).min()
    
    return compute_stochastic(high_proxy, low_proxy, price_series, k_period, d_period, smooth_k)