# models/supertrend.py

import pandas as pd
import numpy as np

def compute_supertrend(df, atr_period=10, multiplier=3.0):
    """
    Compute SuperTrend indicator - a trend-following algorithm
    
    SuperTrend is much more reliable than RSI for trending markets
    
    Parameters:
    - df: DataFrame with 'high', 'low', 'close' columns (or midprice)
    - atr_period: Period for ATR calculation (default: 10)
    - multiplier: ATR multiplier (default: 3.0)
    
    Returns:
    - df with 'supertrend', 'signal' columns added
    """
    
    # Calculate True Range and ATR
    if 'high' in df.columns and 'low' in df.columns:
        # Use proper OHLC data
        high = df['high']
        low = df['low']
        close = df['close']
    else:
        # Use midprice as proxy (for tick data)
        close = df['midprice']
        high = close.rolling(2).max()
        low = close.rolling(2).min()
    
    # True Range calculation
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR (Average True Range)
    atr = tr.ewm(span=atr_period).mean()
    
    # SuperTrend calculation
    hl_avg = (high + low) / 2
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    # Initialize SuperTrend
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, len(df)):
        # Current values
        curr_close = close.iloc[i]
        prev_close = close.iloc[i-1]
        curr_upper = upper_band.iloc[i]
        curr_lower = lower_band.iloc[i]
        prev_upper = upper_band.iloc[i-1] if i > 0 else curr_upper
        prev_lower = lower_band.iloc[i-1] if i > 0 else curr_lower
        
        # Update bands
        if curr_upper < prev_upper or prev_close > prev_upper:
            upper_band.iloc[i] = curr_upper
        else:
            upper_band.iloc[i] = prev_upper
            
        if curr_lower > prev_lower or prev_close < prev_lower:
            lower_band.iloc[i] = curr_lower
        else:
            lower_band.iloc[i] = prev_lower
        
        # Determine SuperTrend direction
        if i == 1:
            if curr_close <= lower_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1  # Downtrend
            else:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1   # Uptrend
        else:
            if supertrend.iloc[i-1] == upper_band.iloc[i-1] and curr_close < upper_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            elif supertrend.iloc[i-1] == upper_band.iloc[i-1] and curr_close >= upper_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            elif supertrend.iloc[i-1] == lower_band.iloc[i-1] and curr_close > lower_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
    
    # Generate trading signals
    df['supertrend'] = supertrend
    df['st_direction'] = direction
    
    # Signal generation
    signals = []
    for i in range(len(df)):
        if i == 0:
            signals.append('HOLD')
        else:
            if direction.iloc[i] == 1 and direction.iloc[i-1] == -1:
                signals.append('BUY')
            elif direction.iloc[i] == -1 and direction.iloc[i-1] == 1:
                signals.append('SELL')
            else:
                signals.append('HOLD')
    
    df['st_signal'] = signals
    return df

def compute_ma_crossover(df, fast_period=10, slow_period=50):
    """
    Simple but effective Moving Average Crossover strategy
    
    Much more reliable than RSI for trending markets
    """
    close = df['midprice'] if 'midprice' in df.columns else df['close']
    
    # Calculate moving averages
    df['ma_fast'] = close.rolling(fast_period).mean()
    df['ma_slow'] = close.rolling(slow_period).mean()
    
    # Generate signals
    signals = []
    for i in range(len(df)):
        if i < slow_period:
            signals.append('HOLD')
        else:
            fast_now = df['ma_fast'].iloc[i]
            slow_now = df['ma_slow'].iloc[i]
            fast_prev = df['ma_fast'].iloc[i-1]
            slow_prev = df['ma_slow'].iloc[i-1]
            
            # Crossover detection
            if fast_prev <= slow_prev and fast_now > slow_now:
                signals.append('BUY')
            elif fast_prev >= slow_prev and fast_now < slow_now:
                signals.append('SELL')
            else:
                signals.append('HOLD')
    
    df['ma_signal'] = signals
    return df