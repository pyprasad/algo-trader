# utils/market_hours.py

from datetime import datetime, time, timedelta
import pytz

def is_market_open(market="FTSE"):
    """
    Check if the specified market is currently open for trading.
    
    Args:
        market (str): Market identifier ("FTSE", "NYSE", "FOREX")
    
    Returns:
        bool: True if market is open, False otherwise
    """
    
    # Get current UK time for FTSE
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    if market == "FTSE":
        # FTSE trading hours: 8:00 AM - 4:30 PM UK time
        # Monday to Friday only
        if now_uk.weekday() >= 5:  # Weekend
            return False
        
        market_open = time(8, 0)   # 8:00 AM
        market_close = time(16, 30)  # 4:30 PM
        
        current_time = now_uk.time()
        return market_open <= current_time <= market_close
    
    # Add other markets as needed
    elif market == "FOREX":
        # Forex is open 24/5
        return now_uk.weekday() < 5
    
    elif market == "NYSE":
        # NYSE trading hours: 9:30 AM - 4:00 PM EST
        us_tz = pytz.timezone('US/Eastern')
        now_us = datetime.now(us_tz)
        
        if now_us.weekday() >= 5:  # Weekend
            return False
        
        market_open = time(9, 30)   # 9:30 AM
        market_close = time(16, 0)  # 4:00 PM
        
        current_time = now_us.time()
        return market_open <= current_time <= market_close
    
    return False

def get_market_status(market="FTSE"):
    """
    Get detailed market status information.
    
    Returns:
        dict: Market status information
    """
    uk_tz = pytz.timezone('Europe/London')
    now_uk = datetime.now(uk_tz)
    
    is_open = is_market_open(market)
    
    if market == "FTSE":
        next_open = None
        next_close = None
        
        if is_open:
            # Market is open, calculate next close
            next_close = now_uk.replace(hour=16, minute=30, second=0, microsecond=0)
        else:
            # Market is closed, calculate next open
            days_ahead = 0
            if now_uk.weekday() >= 5:  # Weekend
                days_ahead = 7 - now_uk.weekday()  # Days until Monday
            elif now_uk.time() > time(16, 30):  # After close today
                days_ahead = 1
            
            next_open = (now_uk + timedelta(days=days_ahead)).replace(
                hour=8, minute=0, second=0, microsecond=0
            )
    
    return {
        "market": market,
        "is_open": is_open,
        "current_time": now_uk.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "next_open": next_open.strftime("%Y-%m-%d %H:%M:%S %Z") if next_open else None,
        "next_close": next_close.strftime("%Y-%m-%d %H:%M:%S %Z") if next_close else None,
        "weekday": now_uk.strftime("%A")
    }