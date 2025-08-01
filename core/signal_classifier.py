# core/signal_classifier.py

def generate_trade_signal(rsi, atr=None, regime="neutral", thresholds=(70, 30), trend="neutral", momentum=None):
    """
    Improved trade signal logic that's more opportunistic and catches market drops.

    Parameters:
    - rsi (float): Latest RSI value
    - atr (float or None): Latest ATR value (used if SL/TP sizing depends on volatility)
    - regime (str): Market regime label (e.g., 'trending', 'volatile', 'mean-reverting')
    - thresholds (tuple): (sell_threshold, buy_threshold) e.g., (70, 30)
    - trend (str): 'uptrend', 'downtrend', or 'sideways'
    - momentum (float or None): Rate of price change for catching rapid moves

    Returns:
    - str: One of 'BUY', 'SELL', or 'HOLD'
    """

    sell_threshold, buy_threshold = thresholds

    # === Mean-Reverting Market (Improved Logic) ===
    if regime == "mean-reverting":
        # Buy oversold conditions regardless of trend (catch the dips!)
        if rsi < buy_threshold:
            # Extra confirmation for very oversold conditions
            if rsi < 25:  # Very oversold - high confidence buy
                return "BUY"
            elif trend == "uptrend" or trend == "sideways":
                return "BUY"
            elif trend == "downtrend" and momentum and momentum < -0.5:
                # Buy during steep drops (catching falling knife with momentum confirmation)
                return "BUY"
            else:
                return "BUY"  # Default to buy when oversold
                
        # Sell overbought conditions
        elif rsi > sell_threshold:
            if rsi > 75:  # Very overbought - high confidence sell
                return "SELL"
            elif trend == "downtrend" or trend == "sideways":
                return "SELL"
            elif trend == "uptrend" and momentum and momentum > 0.5:
                # Sell during steep rises (taking profits)
                return "SELL"
            else:
                return "SELL"  # Default to sell when overbought
        else:
            return "HOLD"

    # === Trending Market (Follow the trend) ===
    elif regime == "trending":
        if trend == "uptrend" and rsi > 40 and rsi < 75:
            # Buy pullbacks in uptrend
            return "BUY"
        elif trend == "downtrend" and rsi < 60 and rsi > 25:
            # Sell rallies in downtrend
            return "SELL"
        elif rsi < buy_threshold:
            # Still buy oversold even in trending markets
            return "BUY"
        elif rsi > sell_threshold:
            # Still sell overbought even in trending markets
            return "SELL"
        else:
            return "HOLD"

    # === Volatile Market (More cautious but still opportunistic) ===
    elif regime == "volatile":
        # Only trade extreme conditions in volatile markets
        if rsi < 25:  # Very oversold
            return "BUY"
        elif rsi > 75:  # Very overbought
            return "SELL"
        else:
            return "HOLD"

    # === Default case ===
    # Basic RSI signals if regime is unknown
    if rsi < buy_threshold:
        return "BUY"
    elif rsi > sell_threshold:
        return "SELL"
    
    return "HOLD"
