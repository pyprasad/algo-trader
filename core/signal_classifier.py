# core/signal_classifier.py

def generate_trade_signal(rsi, atr=None, regime="neutral", thresholds=(80, 20), trend="neutral"):
    """
    Decide on a trade signal based on RSI, ATR, market regime, and EMA trend filter.

    Parameters:
    - rsi (float): Latest RSI value
    - atr (float or None): Latest ATR value (used if SL/TP sizing depends on volatility)
    - regime (str): Market regime label (e.g., 'trending', 'volatile', 'mean-reverting')
    - thresholds (tuple): (buy_threshold, sell_threshold)
    - trend (str): 'uptrend', 'downtrend', or 'sideways'

    Returns:
    - str: One of 'BUY', 'SELL', or 'HOLD'
    """

    buy_threshold, sell_threshold = thresholds

    # === Mean-Reverting Market with EMA Filter ===
    if regime == "mean-reverting":
        if rsi > buy_threshold and trend == "downtrend":
            return "SELL"
        elif rsi < sell_threshold and trend == "uptrend":
            return "BUY"
        else:
            return "HOLD"

    # === Trending Market (less strict filter) ===
    elif regime == "trending":
        if rsi > 70 and trend == "uptrend":
            return "BUY"
        elif rsi < 30 and trend == "downtrend":
            return "SELL"
        else:
            return "HOLD"

    # === Volatile Market ===
    elif regime == "volatile":
        return "HOLD"

    return "HOLD"
