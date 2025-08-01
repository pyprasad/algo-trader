# models/momentum_strategies.py

import pandas as pd
import numpy as np

def compute_momentum(price_series: pd.Series, period: int = 10):
    """
    Compute price momentum (rate of change).
    
    Parameters:
    - price_series: pd.Series of prices
    - period: Lookback period for momentum calculation
    
    Returns:
    - pd.Series: Momentum values
    """
    return ((price_series / price_series.shift(period)) - 1) * 100

def compute_rate_of_change(price_series: pd.Series, period: int = 12):
    """
    Compute Rate of Change (ROC) indicator.
    """
    return ((price_series - price_series.shift(period)) / price_series.shift(period)) * 100

def compute_williams_r(high_series: pd.Series, low_series: pd.Series, close_series: pd.Series, period: int = 14):
    """
    Compute Williams %R oscillator.
    
    Returns:
    - pd.Series: Williams %R values (typically between -100 and 0)
    """
    
    highest_high = high_series.rolling(window=period).max()
    lowest_low = low_series.rolling(window=period).min()
    
    williams_r = ((highest_high - close_series) / (highest_high - lowest_low)) * -100
    
    return williams_r

def compute_commodity_channel_index(high_series: pd.Series, low_series: pd.Series, close_series: pd.Series, period: int = 20):
    """
    Compute Commodity Channel Index (CCI).
    
    Returns:
    - pd.Series: CCI values
    """
    
    # Typical Price
    typical_price = (high_series + low_series + close_series) / 3
    
    # Simple Moving Average of Typical Price
    sma_tp = typical_price.rolling(window=period).mean()
    
    # Mean Deviation
    mean_deviation = typical_price.rolling(window=period).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    
    # CCI calculation
    cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
    
    return cci

def generate_momentum_signals(price_series: pd.Series, momentum_period: int = 10, threshold: float = 2.0):
    """
    Generate trading signals based on momentum.
    
    Parameters:
    - price_series: pd.Series of prices
    - momentum_period: Period for momentum calculation
    - threshold: Momentum threshold for signal generation
    
    Returns:
    - pd.Series: Trading signals (1=BUY, -1=SELL, 0=HOLD)
    """
    
    momentum = compute_momentum(price_series, momentum_period)
    signals = pd.Series(0, index=price_series.index)
    
    # Generate signals based on momentum crossovers
    for i in range(1, len(momentum)):
        # Strong positive momentum
        if momentum.iloc[i] > threshold and momentum.iloc[i-1] <= threshold:
            signals.iloc[i] = 1  # BUY
        
        # Strong negative momentum
        elif momentum.iloc[i] < -threshold and momentum.iloc[i-1] >= -threshold:
            signals.iloc[i] = -1  # SELL
    
    return signals

def generate_multi_timeframe_momentum(price_series: pd.Series, short_period: int = 5, medium_period: int = 10, long_period: int = 20):
    """
    Generate signals using multiple timeframe momentum analysis.
    
    Returns:
    - dict: Momentum values and composite signal
    """
    
    short_momentum = compute_momentum(price_series, short_period)
    medium_momentum = compute_momentum(price_series, medium_period)
    long_momentum = compute_momentum(price_series, long_period)
    
    signals = pd.Series(0, index=price_series.index)
    
    # Multi-timeframe alignment
    for i in range(max(short_period, medium_period, long_period), len(price_series)):
        short_val = short_momentum.iloc[i]
        medium_val = medium_momentum.iloc[i]
        long_val = long_momentum.iloc[i]
        
        # All timeframes bullish
        if short_val > 0 and medium_val > 0 and long_val > 0:
            signals.iloc[i] = 1  # Strong BUY
        
        # All timeframes bearish
        elif short_val < 0 and medium_val < 0 and long_val < 0:
            signals.iloc[i] = -1  # Strong SELL
        
        # Mixed signals - look for momentum acceleration
        elif short_val > medium_val > long_val and short_val > 1:
            signals.iloc[i] = 1  # Accelerating upward momentum
        
        elif short_val < medium_val < long_val and short_val < -1:
            signals.iloc[i] = -1  # Accelerating downward momentum
    
    return {
        "short_momentum": short_momentum,
        "medium_momentum": medium_momentum,
        "long_momentum": long_momentum,
        "signals": signals
    }