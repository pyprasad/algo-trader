# core/timezone_manager.py

"""
⏰ Enhanced Timezone Manager

Provides robust timezone handling with DST support, market calendar integration,
and comprehensive validation for accurate time-based margin calculations.

Key Features:
- Automatic DST (Daylight Saving Time) handling
- Market holiday calendar integration
- Timezone conversion with validation
- Session boundary detection
- Multi-market timezone support

Author: Time Management Team
"""

import pytz
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Union
import logging
from dataclasses import dataclass
from enum import Enum
import json
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketStatus(Enum):
    """Market status enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    HOLIDAY = "holiday"
    WEEKEND = "weekend"

@dataclass
class MarketSchedule:
    """Container for market trading schedule"""
    market_name: str
    timezone: str
    pre_market_open: time
    market_open: time
    market_close: time
    post_market_close: time
    trading_days: List[int]  # 0=Monday, 6=Sunday
    
@dataclass
class MarketHoliday:
    """Container for market holiday information"""
    date: datetime
    market: str
    description: str
    partial_day: bool = False
    early_close_time: Optional[time] = None

class EnhancedTimezoneManager:
    """
    Advanced timezone manager with comprehensive DST handling and market calendar support
    """
    
    def __init__(self):
        """Initialize the timezone manager"""
        # Major market timezones
        self.market_timezones = {
            "FTSE": "Europe/London",
            "DAX": "Europe/Berlin",
            "SPX": "America/New_York",
            "NIKKEI": "Asia/Tokyo",
            "ASX": "Australia/Sydney",
            "HSI": "Asia/Hong_Kong"
        }
        
        # Market schedules with precise timing
        self.market_schedules = self._initialize_market_schedules()
        
        # Holiday calendar
        self.holidays = self._load_holiday_calendar()
        
        # Cache for timezone objects
        self.tz_cache = {}
        
        # Validation settings
        self.strict_validation = True
        
        logger.info("⏰ Enhanced Timezone Manager initialized")
        logger.info(f"   Markets configured: {len(self.market_schedules)}")
        logger.info(f"   Holidays loaded: {len(self.holidays)}")
    
    def _initialize_market_schedules(self) -> Dict[str, MarketSchedule]:
        """Initialize comprehensive market schedules"""
        schedules = {
            "IX.D.FTSE.DAILY.IP": MarketSchedule(
                market_name="FTSE 100",
                timezone="Europe/London",
                pre_market_open=time(7, 0),
                market_open=time(8, 0),
                market_close=time(16, 30),
                post_market_close=time(21, 0),
                trading_days=[0, 1, 2, 3, 4]  # Monday to Friday
            ),
            "IX.D.DAX.DAILY.IP": MarketSchedule(
                market_name="DAX 40",
                timezone="Europe/Berlin",
                pre_market_open=time(7, 0),
                market_open=time(8, 0),
                market_close=time(22, 0),  # Extended hours
                post_market_close=time(22, 30),
                trading_days=[0, 1, 2, 3, 4]
            ),
            "IX.D.SPX.DAILY.IP": MarketSchedule(
                market_name="S&P 500",
                timezone="America/New_York",
                pre_market_open=time(4, 0),
                market_open=time(9, 30),
                market_close=time(16, 0),
                post_market_close=time(20, 0),
                trading_days=[0, 1, 2, 3, 4]
            ),
            "IX.D.NIKKEI.DAILY.IP": MarketSchedule(
                market_name="Nikkei 225",
                timezone="Asia/Tokyo",
                pre_market_open=time(8, 0),
                market_open=time(9, 0),
                market_close=time(15, 30),
                post_market_close=time(16, 30),
                trading_days=[0, 1, 2, 3, 4]
            ),
            # Forex markets (24/5)
            "CS.D.EURUSD.MINI.IP": MarketSchedule(
                market_name="EUR/USD",
                timezone="UTC",
                pre_market_open=time(0, 0),
                market_open=time(0, 0),
                market_close=time(23, 59),
                post_market_close=time(23, 59),
                trading_days=[0, 1, 2, 3, 4]  # Sunday 22:00 to Friday 22:00
            ),
            "CS.D.GBPUSD.MINI.IP": MarketSchedule(
                market_name="GBP/USD",
                timezone="UTC",
                pre_market_open=time(0, 0),
                market_open=time(0, 0),
                market_close=time(23, 59),
                post_market_close=time(23, 59),
                trading_days=[0, 1, 2, 3, 4]
            )
        }
        
        return schedules
    
    def _load_holiday_calendar(self) -> List[MarketHoliday]:
        """Load market holiday calendar"""
        holidays = []
        
        # 2024-2025 Major market holidays
        # UK Market (FTSE)
        holidays.extend([
            MarketHoliday(datetime(2024, 12, 25), "FTSE", "Christmas Day"),
            MarketHoliday(datetime(2024, 12, 26), "FTSE", "Boxing Day"),
            MarketHoliday(datetime(2025, 1, 1), "FTSE", "New Year's Day"),
            MarketHoliday(datetime(2025, 4, 18), "FTSE", "Good Friday"),
            MarketHoliday(datetime(2025, 4, 21), "FTSE", "Easter Monday"),
            MarketHoliday(datetime(2025, 5, 5), "FTSE", "Early May Bank Holiday"),
            MarketHoliday(datetime(2025, 5, 26), "FTSE", "Spring Bank Holiday"),
            MarketHoliday(datetime(2025, 8, 25), "FTSE", "Summer Bank Holiday"),
        ])
        
        # German Market (DAX)
        holidays.extend([
            MarketHoliday(datetime(2024, 12, 24), "DAX", "Christmas Eve", True, time(14, 0)),
            MarketHoliday(datetime(2024, 12, 25), "DAX", "Christmas Day"),
            MarketHoliday(datetime(2024, 12, 26), "DAX", "Boxing Day"),
            MarketHoliday(datetime(2025, 1, 1), "DAX", "New Year's Day"),
            MarketHoliday(datetime(2025, 4, 18), "DAX", "Good Friday"),
            MarketHoliday(datetime(2025, 4, 21), "DAX", "Easter Monday"),
            MarketHoliday(datetime(2025, 5, 1), "DAX", "Labour Day"),
        ])
        
        # US Market (SPX)
        holidays.extend([
            MarketHoliday(datetime(2024, 12, 25), "SPX", "Christmas Day"),
            MarketHoliday(datetime(2025, 1, 1), "SPX", "New Year's Day"),
            MarketHoliday(datetime(2025, 1, 20), "SPX", "Martin Luther King Jr. Day"),
            MarketHoliday(datetime(2025, 2, 17), "SPX", "Presidents Day"),
            MarketHoliday(datetime(2025, 4, 18), "SPX", "Good Friday"),
            MarketHoliday(datetime(2025, 5, 26), "SPX", "Memorial Day"),
            MarketHoliday(datetime(2025, 7, 4), "SPX", "Independence Day"),
            MarketHoliday(datetime(2025, 9, 1), "SPX", "Labor Day"),
            MarketHoliday(datetime(2025, 11, 27), "SPX", "Thanksgiving"),
            MarketHoliday(datetime(2025, 11, 28), "SPX", "Day after Thanksgiving", True, time(13, 0)),
        ])
        
        return holidays
    
    def get_timezone(self, timezone_str: str) -> pytz.timezone:
        """
        Get timezone object with caching and validation
        
        Args:
            timezone_str: Timezone string (e.g., "Europe/London")
            
        Returns:
            pytz timezone object
        """
        if timezone_str in self.tz_cache:
            return self.tz_cache[timezone_str]
        
        try:
            tz = pytz.timezone(timezone_str)
            self.tz_cache[timezone_str] = tz
            return tz
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone_str}")
            if self.strict_validation:
                raise
            # Fallback to UTC
            return pytz.UTC
    
    def convert_time(self, dt: datetime, from_tz: str, to_tz: str) -> datetime:
        """
        Convert time between timezones with DST handling
        
        Args:
            dt: Datetime to convert
            from_tz: Source timezone
            to_tz: Target timezone
            
        Returns:
            Converted datetime
        """
        try:
            # Get timezone objects
            source_tz = self.get_timezone(from_tz)
            target_tz = self.get_timezone(to_tz)
            
            # Localize if naive
            if dt.tzinfo is None:
                dt = source_tz.localize(dt)
            elif dt.tzinfo != source_tz:
                dt = dt.astimezone(source_tz)
            
            # Convert to target timezone
            converted = dt.astimezone(target_tz)
            
            return converted
            
        except Exception as e:
            logger.error(f"Error converting time: {e}")
            if self.strict_validation:
                raise
            return dt
    
    def get_market_time(self, instrument: str, utc_time: Optional[datetime] = None) -> datetime:
        """
        Get current time in market's local timezone
        
        Args:
            instrument: Market instrument
            utc_time: UTC time (defaults to now)
            
        Returns:
            Local market time
        """
        if utc_time is None:
            utc_time = datetime.utcnow()
        
        if utc_time.tzinfo is None:
            utc_time = pytz.UTC.localize(utc_time)
        
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            logger.warning(f"No schedule found for {instrument}")
            return utc_time
        
        market_tz = self.get_timezone(schedule.timezone)
        local_time = utc_time.astimezone(market_tz)
        
        return local_time
    
    def get_market_status(self, instrument: str, check_time: Optional[datetime] = None) -> MarketStatus:
        """
        Get current market status considering holidays and trading hours
        
        Args:
            instrument: Market instrument
            check_time: Time to check (defaults to now)
            
        Returns:
            MarketStatus enum
        """
        if check_time is None:
            check_time = datetime.utcnow()
        
        # Get market schedule
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            return MarketStatus.CLOSED
        
        # Convert to market local time
        local_time = self.get_market_time(instrument, check_time)
        
        # Check if weekend
        if local_time.weekday() not in schedule.trading_days:
            return MarketStatus.WEEKEND
        
        # Check if holiday
        if self.is_market_holiday(instrument, local_time.date()):
            return MarketStatus.HOLIDAY
        
        # Check trading hours
        current_time = local_time.time()
        
        if schedule.pre_market_open <= current_time < schedule.market_open:
            return MarketStatus.PRE_MARKET
        elif schedule.market_open <= current_time < schedule.market_close:
            return MarketStatus.OPEN
        elif schedule.market_close <= current_time < schedule.post_market_close:
            return MarketStatus.POST_MARKET
        else:
            return MarketStatus.CLOSED
    
    def is_market_holiday(self, instrument: str, date: datetime.date) -> bool:
        """
        Check if given date is a market holiday
        
        Args:
            instrument: Market instrument
            date: Date to check
            
        Returns:
            True if holiday, False otherwise
        """
        # Extract market identifier from instrument
        market = None
        if "FTSE" in instrument:
            market = "FTSE"
        elif "DAX" in instrument:
            market = "DAX"
        elif "SPX" in instrument or "DOW" in instrument or "NASDAQ" in instrument:
            market = "SPX"
        elif "NIKKEI" in instrument:
            market = "NIKKEI"
        
        if not market:
            return False
        
        # Check holidays
        for holiday in self.holidays:
            if holiday.market == market and holiday.date.date() == date:
                return True
        
        return False
    
    def get_next_market_open(self, instrument: str, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Get next market open time
        
        Args:
            instrument: Market instrument
            from_time: Start time (defaults to now)
            
        Returns:
            Next market open datetime or None
        """
        if from_time is None:
            from_time = datetime.utcnow()
        
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            return None
        
        # Convert to market time
        local_time = self.get_market_time(instrument, from_time)
        market_tz = self.get_timezone(schedule.timezone)
        
        # Check up to 7 days ahead
        for days_ahead in range(7):
            check_date = local_time.date() + timedelta(days=days_ahead)
            check_time = datetime.combine(check_date, schedule.market_open)
            check_time = market_tz.localize(check_time)
            
            # Skip if before current time
            if check_time <= local_time:
                continue
            
            # Skip weekends
            if check_time.weekday() not in schedule.trading_days:
                continue
            
            # Skip holidays
            if self.is_market_holiday(instrument, check_date):
                continue
            
            # Found next open
            return check_time.astimezone(pytz.UTC)
        
        return None
    
    def get_next_market_close(self, instrument: str, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Get next market close time
        
        Args:
            instrument: Market instrument
            from_time: Start time (defaults to now)
            
        Returns:
            Next market close datetime or None
        """
        if from_time is None:
            from_time = datetime.utcnow()
        
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            return None
        
        # Convert to market time
        local_time = self.get_market_time(instrument, from_time)
        market_tz = self.get_timezone(schedule.timezone)
        
        # Check if market is currently open
        status = self.get_market_status(instrument, from_time)
        if status == MarketStatus.OPEN:
            # Return today's close
            close_time = datetime.combine(local_time.date(), schedule.market_close)
            close_time = market_tz.localize(close_time)
            
            # Check for early close
            for holiday in self.holidays:
                if (holiday.partial_day and 
                    holiday.date.date() == local_time.date() and
                    holiday.early_close_time):
                    close_time = datetime.combine(local_time.date(), holiday.early_close_time)
                    close_time = market_tz.localize(close_time)
            
            return close_time.astimezone(pytz.UTC)
        
        # Find next open, then return its close
        next_open = self.get_next_market_open(instrument, from_time)
        if next_open:
            next_open_local = next_open.astimezone(market_tz)
            close_time = datetime.combine(next_open_local.date(), schedule.market_close)
            close_time = market_tz.localize(close_time)
            return close_time.astimezone(pytz.UTC)
        
        return None
    
    def is_dst_active(self, timezone_str: str, check_time: Optional[datetime] = None) -> bool:
        """
        Check if DST is currently active for a timezone
        
        Args:
            timezone_str: Timezone to check
            check_time: Time to check (defaults to now)
            
        Returns:
            True if DST is active
        """
        if check_time is None:
            check_time = datetime.utcnow()
        
        tz = self.get_timezone(timezone_str)
        
        # Localize to timezone
        if check_time.tzinfo is None:
            check_time = pytz.UTC.localize(check_time)
        
        local_time = check_time.astimezone(tz)
        
        # Check if DST is active
        return bool(local_time.dst())
    
    def get_dst_transitions(self, timezone_str: str, year: int) -> Dict[str, datetime]:
        """
        Get DST transition dates for a timezone
        
        Args:
            timezone_str: Timezone to check
            year: Year to check
            
        Returns:
            Dictionary with 'spring_forward' and 'fall_back' dates
        """
        tz = self.get_timezone(timezone_str)
        transitions = {}
        
        # Check each day of the year for DST transitions
        start_date = datetime(year, 1, 1, 12, 0)  # Noon to avoid edge cases
        
        prev_dst = None
        for day in range(365):
            check_date = start_date + timedelta(days=day)
            check_date = pytz.UTC.localize(check_date)
            local_time = check_date.astimezone(tz)
            
            current_dst = bool(local_time.dst())
            
            if prev_dst is not None and prev_dst != current_dst:
                if current_dst:  # Spring forward
                    transitions['spring_forward'] = check_date
                else:  # Fall back
                    transitions['fall_back'] = check_date
            
            prev_dst = current_dst
        
        return transitions
    
    def validate_market_time(self, instrument: str, check_time: datetime) -> Dict[str, any]:
        """
        Comprehensive validation of market time
        
        Args:
            instrument: Market instrument
            check_time: Time to validate
            
        Returns:
            Validation results dictionary
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'market_status': None,
            'local_time': None,
            'is_holiday': False,
            'is_dst': False
        }
        
        try:
            # Get market schedule
            schedule = self.market_schedules.get(instrument)
            if not schedule:
                results['valid'] = False
                results['errors'].append(f"No schedule found for {instrument}")
                return results
            
            # Convert to local time
            local_time = self.get_market_time(instrument, check_time)
            results['local_time'] = local_time
            
            # Check market status
            status = self.get_market_status(instrument, check_time)
            results['market_status'] = status.value
            
            # Check if holiday
            results['is_holiday'] = self.is_market_holiday(instrument, local_time.date())
            
            # Check DST
            results['is_dst'] = self.is_dst_active(schedule.timezone, check_time)
            
            # Add warnings
            if results['is_dst']:
                results['warnings'].append("DST is active - verify time calculations")
            
            if results['is_holiday']:
                results['warnings'].append("Market holiday - trading may be restricted")
            
        except Exception as e:
            results['valid'] = False
            results['errors'].append(str(e))
        
        return results
    
    def get_session_boundaries(self, instrument: str, date: datetime.date) -> Dict[str, datetime]:
        """
        Get all session boundaries for a trading day
        
        Args:
            instrument: Market instrument
            date: Trading date
            
        Returns:
            Dictionary with session boundary times
        """
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            return {}
        
        market_tz = self.get_timezone(schedule.timezone)
        
        boundaries = {}
        
        # Create boundary times
        times = {
            'pre_market_open': schedule.pre_market_open,
            'market_open': schedule.market_open,
            'market_close': schedule.market_close,
            'post_market_close': schedule.post_market_close
        }
        
        for name, time_obj in times.items():
            dt = datetime.combine(date, time_obj)
            dt = market_tz.localize(dt)
            boundaries[name] = dt.astimezone(pytz.UTC)
        
        return boundaries
    
    def get_trading_hours_summary(self, instrument: str) -> str:
        """
        Get formatted trading hours summary
        
        Args:
            instrument: Market instrument
            
        Returns:
            Formatted string with trading hours
        """
        schedule = self.market_schedules.get(instrument)
        if not schedule:
            return f"No schedule available for {instrument}"
        
        summary = f"""
Trading Hours for {schedule.market_name} ({schedule.timezone}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pre-Market:  {schedule.pre_market_open.strftime('%H:%M')} - {schedule.market_open.strftime('%H:%M')}
Market:      {schedule.market_open.strftime('%H:%M')} - {schedule.market_close.strftime('%H:%M')}
Post-Market: {schedule.market_close.strftime('%H:%M')} - {schedule.post_market_close.strftime('%H:%M')}
Trading Days: {', '.join(['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][i] for i in schedule.trading_days)}
"""
        
        # Add DST info
        is_dst = self.is_dst_active(schedule.timezone)
        summary += f"DST Active: {'Yes' if is_dst else 'No'}\n"
        
        # Add next transitions
        next_open = self.get_next_market_open(instrument)
        next_close = self.get_next_market_close(instrument)
        
        if next_open:
            summary += f"Next Open: {next_open.strftime('%Y-%m-%d %H:%M UTC')}\n"
        if next_close:
            summary += f"Next Close: {next_close.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
        return summary

# Global instance
_timezone_manager = None

def get_timezone_manager() -> EnhancedTimezoneManager:
    """Get global timezone manager instance"""
    global _timezone_manager
    if _timezone_manager is None:
        _timezone_manager = EnhancedTimezoneManager()
    return _timezone_manager

if __name__ == "__main__":
    # Test the timezone manager
    print("⏰ Testing Enhanced Timezone Manager")
    print("=" * 50)
    
    manager = EnhancedTimezoneManager()
    
    # Test instruments
    test_instruments = [
        "IX.D.FTSE.DAILY.IP",
        "IX.D.DAX.DAILY.IP",
        "IX.D.SPX.DAILY.IP"
    ]
    
    print("\n📊 Current Market Status:")
    for instrument in test_instruments:
        status = manager.get_market_status(instrument)
        local_time = manager.get_market_time(instrument)
        print(f"{instrument}: {status.value} (Local: {local_time.strftime('%H:%M %Z')})")
    
    print("\n📅 Trading Hours:")
    print(manager.get_trading_hours_summary("IX.D.FTSE.DAILY.IP"))
    
    # Test DST
    print("\n🕐 DST Status:")
    for tz in ["Europe/London", "America/New_York", "Asia/Tokyo"]:
        is_dst = manager.is_dst_active(tz)
        print(f"{tz}: DST {'Active' if is_dst else 'Inactive'}")
    
    # Test validation
    print("\n✅ Time Validation:")
    validation = manager.validate_market_time("IX.D.FTSE.DAILY.IP", datetime.utcnow())
    print(f"Valid: {validation['valid']}")
    print(f"Status: {validation['market_status']}")
    if validation['warnings']:
        print(f"Warnings: {', '.join(validation['warnings'])}")