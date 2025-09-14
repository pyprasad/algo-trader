# core/margin_rate_manager.py

"""
🎯 Dynamic Margin Rate Manager

Intelligently manages IG Markets' time-based margin rates to optimize position sizing
while minimizing API requests through smart caching and predictive scheduling.

Key Features:
- Time-aware margin rate calculation (market hours vs overnight/weekend)
- Smart API request optimization with daily budget tracking
- Predictive rate transition scheduling
- Intelligent caching with TTL and fallback logic
- Seamless integration with existing trading algorithms

Author: Advanced Trading Systems
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import yaml
import json
import pytz
from dataclasses import dataclass
from enum import Enum

# Import secure configuration
from core.secure_config import get_secure_config

class MarketSession(Enum):
    """Market session types for margin calculation"""
    MARKET_HOURS = "market_hours"
    OVERNIGHT = "overnight" 
    WEEKEND = "weekend"
    HOLIDAY = "holiday"

class AssetClass(Enum):
    """Asset classification for margin rates"""
    FOREX = "forex"
    INDICES = "indices"
    COMMODITIES = "commodities"
    STOCKS = "stocks"
    CRYPTO = "crypto"

@dataclass
class MarginRate:
    """Container for margin rate information"""
    asset_class: AssetClass
    instrument: str
    session: MarketSession
    rate: float
    effective_from: datetime
    effective_until: datetime
    source: str = "config"  # config, api, cache
    
@dataclass
class MarketHours:
    """Market trading hours for different instruments"""
    instrument: str
    timezone: str
    open_time: str  # "08:00"
    close_time: str  # "17:00"
    weekend_trading: bool = False
    
@dataclass
class APIUsageTracker:
    """Track API usage to stay within daily limits"""
    date: str
    requests_used: int
    requests_limit: int
    last_reset: datetime
    
class MarginRateManager:
    """
    Advanced margin rate manager that provides time-aware margin calculations
    while optimizing API usage and maintaining high reliability through caching
    """
    
    def __init__(self):
        """Initialize the margin rate manager"""
        # Load secure configuration
        self.config = get_secure_config()
        
        # Load configuration with defaults
        margin_config = self.config.get("margin_management", {})
        self.enabled = margin_config.get("enabled", True)
        
        # API optimization settings
        api_config = margin_config.get("api_optimization", {})
        self.daily_request_limit = api_config.get("daily_request_limit", 1000)
        self.bulk_fetch_hour = api_config.get("bulk_fetch_hour", 6)  # UTC
        self.cache_duration_minutes = api_config.get("cache_duration_minutes", 15)
        self.fallback_to_schedule = api_config.get("fallback_to_schedule", True)
        
        # Default margin rates
        self.default_rates = margin_config.get("default_rates", {
            "forex": {"market_hours": 0.0333, "overnight": 0.05},
            "indices": {"market_hours": 0.01, "overnight": 0.02},
            "commodities": {"market_hours": 0.05, "overnight": 0.08},
            "weekend_multiplier": 1.5
        })
        
        # Internal state
        self.margin_cache = {}  # instrument -> MarginRate
        self.market_hours_cache = {}  # instrument -> MarketHours
        self.api_usage_tracker = APIUsageTracker(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            requests_used=0,
            requests_limit=self.daily_request_limit,
            last_reset=datetime.utcnow()
        )
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Load predefined market hours
        self._initialize_market_hours()
        
        # Load cached margin data if available
        self._load_cached_data()
        
        print(f"🎯 Margin Rate Manager initialized")
        print(f"   Status: {'✅ ENABLED' if self.enabled else '❌ DISABLED'}")
        if self.enabled:
            print(f"   Daily API Limit: {self.daily_request_limit}")
            print(f"   Cache Duration: {self.cache_duration_minutes} minutes")
            print(f"   Bulk Fetch Time: {self.bulk_fetch_hour:02d}:00 UTC")
    
    def _initialize_market_hours(self):
        """Initialize predefined market hours for major instruments"""
        # Major indices market hours (all times in instrument's local timezone)
        self.market_hours_cache = {
            "IX.D.FTSE.DAILY.IP": MarketHours("FTSE 100", "Europe/London", "08:00", "16:30"),
            "IX.D.DAX.DAILY.IP": MarketHours("DAX 40", "Europe/Berlin", "08:00", "22:00"),
            "IX.D.SPX.DAILY.IP": MarketHours("S&P 500", "America/New_York", "09:30", "16:00"),
            "IX.D.DOW.DAILY.IP": MarketHours("Dow Jones", "America/New_York", "09:30", "16:00"),
            "IX.D.NASDAQ.DAILY.IP": MarketHours("NASDAQ", "America/New_York", "09:30", "16:00"),
            "IX.D.NIKKEI.DAILY.IP": MarketHours("Nikkei 225", "Asia/Tokyo", "09:00", "15:30"),
            
            # Major forex pairs (24/5 trading)
            "CS.D.EURUSD.MINI.IP": MarketHours("EUR/USD", "UTC", "00:00", "23:59"),
            "CS.D.GBPUSD.MINI.IP": MarketHours("GBP/USD", "UTC", "00:00", "23:59"),
            "CS.D.USDJPY.MINI.IP": MarketHours("USD/JPY", "UTC", "00:00", "23:59"),
            
            # Commodities
            "CC.D.LCO.UMA.IP": MarketHours("Brent Crude", "Europe/London", "01:00", "23:00"),
            "CS.D.CFEGOLD.CFE.IP": MarketHours("Gold", "America/New_York", "18:00", "17:15"),  # Sunday 6PM - Friday 5:15PM
        }
        
        print(f"📊 Initialized market hours for {len(self.market_hours_cache)} instruments")
    
    def _load_cached_data(self):
        """Load previously cached margin data from file"""
        try:
            with open("cache/margin_rates.json", "r") as f:
                cached_data = json.load(f)
                
                for instrument, data in cached_data.items():
                    # Convert cached data back to MarginRate object
                    margin_rate = MarginRate(
                        asset_class=AssetClass(data["asset_class"]),
                        instrument=data["instrument"],
                        session=MarketSession(data["session"]),
                        rate=data["rate"],
                        effective_from=datetime.fromisoformat(data["effective_from"]),
                        effective_until=datetime.fromisoformat(data["effective_until"]),
                        source=data["source"]
                    )
                    
                    # Only use if still valid
                    if margin_rate.effective_until > datetime.utcnow():
                        self.margin_cache[instrument] = margin_rate
                        
                print(f"💾 Loaded {len(self.margin_cache)} cached margin rates")
                        
        except FileNotFoundError:
            print("📁 No cached margin data found - will create new cache")
        except Exception as e:
            print(f"⚠️ Error loading cached margin data: {e}")
    
    def _save_cached_data(self):
        """Save current margin data to cache file"""
        try:
            import os
            os.makedirs("cache", exist_ok=True)
            
            cached_data = {}
            for instrument, margin_rate in self.margin_cache.items():
                cached_data[instrument] = {
                    "asset_class": margin_rate.asset_class.value,
                    "instrument": margin_rate.instrument,
                    "session": margin_rate.session.value,
                    "rate": margin_rate.rate,
                    "effective_from": margin_rate.effective_from.isoformat(),
                    "effective_until": margin_rate.effective_until.isoformat(),
                    "source": margin_rate.source
                }
            
            with open("cache/margin_rates.json", "w") as f:
                json.dump(cached_data, f, indent=2)
                
            print(f"💾 Saved {len(cached_data)} margin rates to cache")
            
        except Exception as e:
            print(f"⚠️ Error saving margin data to cache: {e}")
    
    def get_current_margin_rate(self, instrument: str, position_size: float = 1.0) -> float:
        """
        Get the current margin rate for an instrument based on current time and position size
        
        Args:
            instrument: IG instrument epic (e.g., "IX.D.FTSE.DAILY.IP")
            position_size: Position size for tiered margin calculation
            
        Returns:
            Current margin rate as decimal (e.g., 0.01 for 1%)
        """
        try:
            if not self.enabled:
                return self._get_fallback_margin_rate(instrument)
            
            with self.lock:
                # Try to get from cache first
                cached_rate = self._get_cached_margin_rate(instrument)
                if cached_rate and self._is_rate_still_valid(cached_rate):
                    print(f"📊 Using cached margin rate for {instrument}: {cached_rate.rate:.4f}")
                    return self._apply_tiered_margin(cached_rate.rate, position_size)
                
                # Determine current market session
                current_session = self._get_current_market_session(instrument)
                
                # Get base rate for current session
                base_rate = self._calculate_session_margin_rate(instrument, current_session)
                
                # Apply tiered margin adjustments
                final_rate = self._apply_tiered_margin(base_rate, position_size)
                
                # Cache the result
                self._cache_margin_rate(instrument, current_session, final_rate)
                
                print(f"🎯 Current margin rate for {instrument} ({current_session.value}): {final_rate:.4f}")
                return final_rate
                
        except Exception as e:
            print(f"❌ Error getting margin rate for {instrument}: {e}")
            return self._get_fallback_margin_rate(instrument)
    
    def _get_cached_margin_rate(self, instrument: str) -> Optional[MarginRate]:
        """Get margin rate from cache if available and valid"""
        cached_rate = self.margin_cache.get(instrument)
        if cached_rate and self._is_rate_still_valid(cached_rate):
            return cached_rate
        return None
    
    def _is_rate_still_valid(self, margin_rate: MarginRate) -> bool:
        """Check if cached margin rate is still valid"""
        now = datetime.utcnow()
        return margin_rate.effective_until > now
    
    def _get_current_market_session(self, instrument: str) -> MarketSession:
        """Determine current market session for an instrument"""
        try:
            now_utc = datetime.utcnow()
            
            # Check if it's weekend
            if now_utc.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return MarketSession.WEEKEND
            
            # Get market hours for this instrument
            market_hours = self.market_hours_cache.get(instrument)
            if not market_hours:
                # Unknown instrument - use conservative approach
                return MarketSession.OVERNIGHT
            
            # Convert current time to instrument's timezone
            instrument_tz = pytz.timezone(market_hours.timezone)
            now_local = now_utc.replace(tzinfo=pytz.UTC).astimezone(instrument_tz)
            
            # Parse market hours
            open_time = datetime.strptime(market_hours.open_time, "%H:%M").time()
            close_time = datetime.strptime(market_hours.close_time, "%H:%M").time()
            current_time = now_local.time()
            
            # Check if within market hours
            if market_hours.weekend_trading or now_utc.weekday() < 5:
                if open_time <= current_time <= close_time:
                    return MarketSession.MARKET_HOURS
            
            return MarketSession.OVERNIGHT
            
        except Exception as e:
            print(f"⚠️ Error determining market session for {instrument}: {e}")
            return MarketSession.OVERNIGHT
    
    def _calculate_session_margin_rate(self, instrument: str, session: MarketSession) -> float:
        """Calculate margin rate for a specific session"""
        # Determine asset class
        asset_class = self._classify_instrument(instrument)
        
        # Get base rates from configuration
        base_rates = self.default_rates.get(asset_class.value, self.default_rates["indices"])
        
        # Get session-specific rate
        if session == MarketSession.MARKET_HOURS:
            base_rate = base_rates.get("market_hours", 0.01)
        else:  # OVERNIGHT, WEEKEND, HOLIDAY
            base_rate = base_rates.get("overnight", 0.02)
            
            # Apply weekend multiplier if applicable
            if session == MarketSession.WEEKEND:
                weekend_multiplier = self.default_rates.get("weekend_multiplier", 1.5)
                base_rate *= weekend_multiplier
        
        return base_rate
    
    def _classify_instrument(self, instrument: str) -> AssetClass:
        """Classify instrument into asset class for margin calculation"""
        instrument_upper = instrument.upper()
        
        if "IX.D." in instrument_upper:
            return AssetClass.INDICES
        elif "CS.D." in instrument_upper and any(pair in instrument_upper for pair in ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"]):
            return AssetClass.FOREX
        elif "CC.D." in instrument_upper or "OIL" in instrument_upper or "GOLD" in instrument_upper:
            return AssetClass.COMMODITIES
        elif "COIN" in instrument_upper or "BTC" in instrument_upper or "ETH" in instrument_upper:
            return AssetClass.CRYPTO
        else:
            return AssetClass.STOCKS
    
    def _apply_tiered_margin(self, base_rate: float, position_size: float) -> float:
        """Apply IG's tiered margin structure"""
        # IG's typical tiered margin structure:
        # Tier 1: 0-£5000 exposure: Best rates
        # Tier 2: £5001-£25000: Slightly higher
        # Tier 3: £25001-£100000: Higher
        # Tier 4: £100001+: Highest rates
        
        # This is a simplified implementation - in production you'd want
        # to get the actual tiered rates from IG's API
        
        if position_size <= 5000:
            return base_rate  # Tier 1 - best rates
        elif position_size <= 25000:
            return base_rate * 1.2  # Tier 2 - 20% higher
        elif position_size <= 100000:
            return base_rate * 1.5  # Tier 3 - 50% higher
        else:
            return base_rate * 2.0  # Tier 4 - 100% higher
    
    def _cache_margin_rate(self, instrument: str, session: MarketSession, rate: float):
        """Cache a margin rate with appropriate expiration"""
        now = datetime.utcnow()
        expiry = now + timedelta(minutes=self.cache_duration_minutes)
        
        # Determine asset class
        asset_class = self._classify_instrument(instrument)
        
        margin_rate = MarginRate(
            asset_class=asset_class,
            instrument=instrument,
            session=session,
            rate=rate,
            effective_from=now,
            effective_until=expiry,
            source="calculated"
        )
        
        self.margin_cache[instrument] = margin_rate
        
        # Periodically save to disk
        if len(self.margin_cache) % 10 == 0:  # Save every 10 additions
            self._save_cached_data()
    
    def _get_fallback_margin_rate(self, instrument: str) -> float:
        """Get conservative fallback margin rate when system is disabled or fails"""
        asset_class = self._classify_instrument(instrument)
        base_rates = self.default_rates.get(asset_class.value, self.default_rates["indices"])
        
        # Use overnight rate as conservative fallback
        fallback_rate = base_rates.get("overnight", 0.05)  # 5% default
        
        print(f"⚠️ Using fallback margin rate for {instrument}: {fallback_rate:.4f}")
        return fallback_rate
    
    def get_next_rate_change(self, instrument: str) -> Optional[Tuple[datetime, MarketSession, float]]:
        """
        Predict when the next margin rate change will occur for an instrument
        
        Returns:
            Tuple of (change_time, new_session, expected_rate) or None if unknown
        """
        try:
            market_hours = self.market_hours_cache.get(instrument)
            if not market_hours:
                return None
            
            now_utc = datetime.utcnow()
            instrument_tz = pytz.timezone(market_hours.timezone)
            now_local = now_utc.replace(tzinfo=pytz.UTC).astimezone(instrument_tz)
            
            current_session = self._get_current_market_session(instrument)
            
            # Calculate next transition
            if current_session == MarketSession.MARKET_HOURS:
                # Next change: Market close -> Overnight
                close_time = datetime.strptime(market_hours.close_time, "%H:%M").time()
                next_change = datetime.combine(now_local.date(), close_time)
                if next_change <= now_local.replace(tzinfo=None):
                    next_change += timedelta(days=1)
                next_session = MarketSession.OVERNIGHT
            else:
                # Next change: Overnight -> Market open
                open_time = datetime.strptime(market_hours.open_time, "%H:%M").time()
                next_change = datetime.combine(now_local.date(), open_time)
                if next_change <= now_local.replace(tzinfo=None):
                    next_change += timedelta(days=1)
                next_session = MarketSession.MARKET_HOURS
            
            # Convert back to UTC
            try:
                next_change_localized = instrument_tz.localize(next_change)
                next_change_utc = next_change_localized.astimezone(pytz.UTC).replace(tzinfo=None)
            except Exception:
                # Handle ambiguous time (DST transition)
                next_change_localized = instrument_tz.localize(next_change, is_dst=False)
                next_change_utc = next_change_localized.astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Calculate expected rate for next session
            expected_rate = self._calculate_session_margin_rate(instrument, next_session)
            
            return (next_change_utc, next_session, expected_rate)
            
        except Exception as e:
            print(f"⚠️ Error calculating next rate change for {instrument}: {e}")
            return None
    
    def can_make_api_request(self) -> bool:
        """Check if we can make an API request without exceeding daily limit"""
        with self.lock:
            # Reset counter if new day
            today = datetime.utcnow().strftime("%Y-%m-%d")
            if self.api_usage_tracker.date != today:
                self.api_usage_tracker.date = today
                self.api_usage_tracker.requests_used = 0
                self.api_usage_tracker.last_reset = datetime.utcnow()
            
            return self.api_usage_tracker.requests_used < self.api_usage_tracker.requests_limit
    
    def record_api_request(self):
        """Record that an API request was made"""
        with self.lock:
            self.api_usage_tracker.requests_used += 1
    
    def get_api_usage_status(self) -> Dict:
        """Get current API usage status"""
        with self.lock:
            return {
                "requests_used": self.api_usage_tracker.requests_used,
                "requests_remaining": self.api_usage_tracker.requests_limit - self.api_usage_tracker.requests_used,
                "requests_limit": self.api_usage_tracker.requests_limit,
                "date": self.api_usage_tracker.date,
                "percentage_used": (self.api_usage_tracker.requests_used / self.api_usage_tracker.requests_limit) * 100
            }
    
    def preload_margin_rates(self, instruments: List[str]) -> int:
        """
        Preload margin rates for multiple instruments to optimize API usage
        
        Returns:
            Number of rates successfully preloaded
        """
        if not self.enabled:
            return 0
            
        preloaded_count = 0
        
        for instrument in instruments:
            try:
                # Get current rate (this will cache it)
                rate = self.get_current_margin_rate(instrument)
                if rate:
                    preloaded_count += 1
                    
                # Also cache the next rate transition if predictable
                next_change = self.get_next_rate_change(instrument)
                if next_change:
                    change_time, next_session, expected_rate = next_change
                    print(f"📅 {instrument}: Next rate change at {change_time.strftime('%H:%M UTC')} -> {expected_rate:.4f}")
                    
            except Exception as e:
                print(f"⚠️ Failed to preload margin rate for {instrument}: {e}")
        
        print(f"🎯 Preloaded margin rates for {preloaded_count}/{len(instruments)} instruments")
        return preloaded_count
    
    def get_status(self) -> Dict:
        """Get comprehensive status of the margin rate manager"""
        api_status = self.get_api_usage_status()
        
        return {
            "enabled": self.enabled,
            "cached_rates": len(self.margin_cache),
            "known_instruments": len(self.market_hours_cache),
            "cache_duration_minutes": self.cache_duration_minutes,
            "api_usage": api_status,
            "fallback_mode": not self.enabled or not self.can_make_api_request()
        }

# Global instance
_margin_rate_manager = None

def get_margin_rate_manager() -> MarginRateManager:
    """Get global margin rate manager instance"""
    global _margin_rate_manager
    if _margin_rate_manager is None:
        _margin_rate_manager = MarginRateManager()
    return _margin_rate_manager

if __name__ == "__main__":
    # Test the margin rate manager
    print("🧪 Testing Margin Rate Manager")
    print("=" * 50)
    
    manager = MarginRateManager()
    
    # Test instruments
    test_instruments = [
        "IX.D.FTSE.DAILY.IP",  # FTSE 100
        "IX.D.DAX.DAILY.IP",   # DAX
        "CS.D.EURUSD.MINI.IP"  # EUR/USD
    ]
    
    # Test current margin rates
    for instrument in test_instruments:
        rate = manager.get_current_margin_rate(instrument, position_size=10000)
        print(f"📊 {instrument}: {rate:.4f} ({rate*100:.2f}%)")
        
        # Test next rate change prediction
        next_change = manager.get_next_rate_change(instrument)
        if next_change:
            change_time, session, expected_rate = next_change
            print(f"   Next change: {change_time} -> {session.value} ({expected_rate:.4f})")
    
    # Test preloading
    preloaded = manager.preload_margin_rates(test_instruments)
    print(f"✅ Preloaded {preloaded} margin rates")
    
    # Show status
    status = manager.get_status()
    print(f"📈 System Status: {status}")