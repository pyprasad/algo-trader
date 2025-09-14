# core/enhanced_session_detector.py

"""
📊 Enhanced Market Session Detector

Provides precise market session detection with support for extended trading hours,
session overlaps, and dynamic margin rate mapping based on current market conditions.

Key Features:
- Precise session boundary detection
- Extended trading hours support
- Session overlap handling for global markets
- Real-time margin rate mapping
- Volume-based session confirmation

Author: Market Analysis Team
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import timezone manager
from core.timezone_manager import get_timezone_manager, MarketStatus

class SessionType(Enum):
    """Detailed session types for margin calculation"""
    PRE_MARKET = "pre_market"
    MARKET_OPEN_AUCTION = "market_open_auction"
    CONTINUOUS_TRADING = "continuous_trading"
    INTRADAY_AUCTION = "intraday_auction"
    CLOSING_AUCTION = "closing_auction"
    POST_MARKET = "post_market"
    AFTER_HOURS = "after_hours"
    OVERNIGHT = "overnight"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"

@dataclass
class SessionInfo:
    """Detailed session information"""
    session_type: SessionType
    start_time: datetime
    end_time: datetime
    margin_rate: float
    liquidity_level: str  # "high", "medium", "low"
    volatility_expectation: str  # "high", "medium", "low"
    volume_multiplier: float
    
@dataclass
class MarketMicrostructure:
    """Market microstructure data for session detection"""
    bid_ask_spread: float
    volume: float
    trade_count: int
    average_trade_size: float
    order_imbalance: float
    
class EnhancedSessionDetector:
    """
    Advanced session detector with precise boundary detection and margin mapping
    """
    
    def __init__(self):
        """Initialize the enhanced session detector"""
        self.timezone_manager = get_timezone_manager()
        
        # Session definitions with precise timing
        self.session_definitions = self._initialize_session_definitions()
        
        # Margin rate mappings by session type
        self.margin_rate_mappings = self._initialize_margin_mappings()
        
        # Volume patterns by session
        self.volume_patterns = self._initialize_volume_patterns()
        
        # Session overlap handling
        self.overlap_rules = self._initialize_overlap_rules()
        
        logger.info("📊 Enhanced Session Detector initialized")
    
    def _initialize_session_definitions(self) -> Dict[str, Dict[SessionType, Tuple[time, time]]]:
        """Initialize detailed session definitions for each market"""
        return {
            "IX.D.FTSE.DAILY.IP": {
                SessionType.PRE_MARKET: (time(7, 0), time(7, 50)),
                SessionType.MARKET_OPEN_AUCTION: (time(7, 50), time(8, 0)),
                SessionType.CONTINUOUS_TRADING: (time(8, 0), time(16, 30)),
                SessionType.CLOSING_AUCTION: (time(16, 30), time(16, 35)),
                SessionType.POST_MARKET: (time(16, 35), time(21, 0)),
                SessionType.OVERNIGHT: (time(21, 0), time(7, 0))
            },
            "IX.D.DAX.DAILY.IP": {
                SessionType.PRE_MARKET: (time(7, 0), time(7, 50)),
                SessionType.MARKET_OPEN_AUCTION: (time(7, 50), time(8, 0)),
                SessionType.CONTINUOUS_TRADING: (time(8, 0), time(17, 30)),
                SessionType.INTRADAY_AUCTION: (time(13, 0), time(13, 2)),  # Xetra intraday auction
                SessionType.CLOSING_AUCTION: (time(17, 30), time(17, 35)),
                SessionType.POST_MARKET: (time(17, 35), time(22, 0)),  # Extended hours
                SessionType.OVERNIGHT: (time(22, 0), time(7, 0))
            },
            "IX.D.SPX.DAILY.IP": {
                SessionType.PRE_MARKET: (time(4, 0), time(9, 30)),
                SessionType.MARKET_OPEN_AUCTION: (time(9, 28), time(9, 30)),
                SessionType.CONTINUOUS_TRADING: (time(9, 30), time(16, 0)),
                SessionType.CLOSING_AUCTION: (time(15, 58), time(16, 0)),
                SessionType.AFTER_HOURS: (time(16, 0), time(20, 0)),
                SessionType.OVERNIGHT: (time(20, 0), time(4, 0))
            },
            # Forex - 24/5 with session overlaps
            "CS.D.EURUSD.MINI.IP": {
                SessionType.CONTINUOUS_TRADING: (time(0, 0), time(23, 59))  # Simplified for forex
            }
        }
    
    def _initialize_margin_mappings(self) -> Dict[SessionType, Dict[str, float]]:
        """Initialize margin rate mappings by session type"""
        return {
            SessionType.PRE_MARKET: {
                "base_multiplier": 1.5,  # 50% higher than market hours
                "indices": 0.015,
                "forex": 0.04,
                "commodities": 0.075
            },
            SessionType.MARKET_OPEN_AUCTION: {
                "base_multiplier": 1.2,  # Slightly elevated during auction
                "indices": 0.012,
                "forex": 0.035,
                "commodities": 0.06
            },
            SessionType.CONTINUOUS_TRADING: {
                "base_multiplier": 1.0,  # Standard rates
                "indices": 0.01,
                "forex": 0.0333,
                "commodities": 0.05
            },
            SessionType.INTRADAY_AUCTION: {
                "base_multiplier": 1.1,  # Slightly elevated
                "indices": 0.011,
                "forex": 0.035,
                "commodities": 0.055
            },
            SessionType.CLOSING_AUCTION: {
                "base_multiplier": 1.2,
                "indices": 0.012,
                "forex": 0.035,
                "commodities": 0.06
            },
            SessionType.POST_MARKET: {
                "base_multiplier": 1.5,
                "indices": 0.015,
                "forex": 0.04,
                "commodities": 0.075
            },
            SessionType.AFTER_HOURS: {
                "base_multiplier": 1.75,
                "indices": 0.0175,
                "forex": 0.045,
                "commodities": 0.085
            },
            SessionType.OVERNIGHT: {
                "base_multiplier": 2.0,
                "indices": 0.02,
                "forex": 0.05,
                "commodities": 0.10
            },
            SessionType.WEEKEND: {
                "base_multiplier": 3.0,
                "indices": 0.03,
                "forex": 0.075,
                "commodities": 0.15
            },
            SessionType.HOLIDAY: {
                "base_multiplier": 2.5,
                "indices": 0.025,
                "forex": 0.065,
                "commodities": 0.125
            }
        }
    
    def _initialize_volume_patterns(self) -> Dict[SessionType, Dict[str, float]]:
        """Initialize expected volume patterns by session"""
        return {
            SessionType.PRE_MARKET: {
                "volume_ratio": 0.05,  # 5% of daily volume
                "volatility": "medium",
                "liquidity": "low"
            },
            SessionType.MARKET_OPEN_AUCTION: {
                "volume_ratio": 0.15,  # 15% of daily volume
                "volatility": "high",
                "liquidity": "medium"
            },
            SessionType.CONTINUOUS_TRADING: {
                "volume_ratio": 0.60,  # 60% of daily volume
                "volatility": "medium",
                "liquidity": "high"
            },
            SessionType.CLOSING_AUCTION: {
                "volume_ratio": 0.15,  # 15% of daily volume
                "volatility": "high",
                "liquidity": "medium"
            },
            SessionType.POST_MARKET: {
                "volume_ratio": 0.05,  # 5% of daily volume
                "volatility": "medium",
                "liquidity": "low"
            },
            SessionType.OVERNIGHT: {
                "volume_ratio": 0.01,  # 1% of daily volume
                "volatility": "low",
                "liquidity": "very_low"
            }
        }
    
    def _initialize_overlap_rules(self) -> Dict[str, List[str]]:
        """Initialize market overlap rules for global trading"""
        return {
            "LONDON_NY_OVERLAP": ["13:00-17:00 UTC"],  # Most liquid period
            "TOKYO_LONDON_OVERLAP": ["08:00-09:00 UTC"],
            "SYDNEY_TOKYO_OVERLAP": ["00:00-06:00 UTC"],
            "MAJOR_NEWS_WINDOWS": [
                "08:30 EST",  # US Non-farm payrolls
                "10:00 EST",  # US Consumer confidence
                "14:30 GMT",  # UK GDP
                "08:00 CET"   # ECB announcements
            ]
        }
    
    def detect_current_session(self, instrument: str, 
                              check_time: Optional[datetime] = None,
                              market_data: Optional[MarketMicrostructure] = None) -> SessionInfo:
        """
        Detect current market session with high precision
        
        Args:
            instrument: Market instrument
            check_time: Time to check (defaults to now)
            market_data: Optional market microstructure data
            
        Returns:
            SessionInfo with detailed session information
        """
        if check_time is None:
            check_time = datetime.utcnow()
        
        # Get basic market status
        market_status = self.timezone_manager.get_market_status(instrument, check_time)
        
        # Get local market time
        local_time = self.timezone_manager.get_market_time(instrument, check_time)
        current_time = local_time.time()
        
        # Handle special cases first
        if market_status == MarketStatus.WEEKEND:
            return self._create_session_info(SessionType.WEEKEND, instrument, check_time)
        elif market_status == MarketStatus.HOLIDAY:
            return self._create_session_info(SessionType.HOLIDAY, instrument, check_time)
        
        # Get session definitions for this instrument
        sessions = self.session_definitions.get(instrument, {})
        
        # Find matching session
        for session_type, (start_time, end_time) in sessions.items():
            if self._time_in_range(current_time, start_time, end_time):
                # Validate with market data if available
                if market_data:
                    session_type = self._validate_session_with_market_data(
                        session_type, market_data
                    )
                
                return self._create_session_info(session_type, instrument, check_time)
        
        # Default to overnight if no match
        return self._create_session_info(SessionType.OVERNIGHT, instrument, check_time)
    
    def _time_in_range(self, current: time, start: time, end: time) -> bool:
        """Check if time is in range, handling midnight crossover"""
        if start <= end:
            return start <= current <= end
        else:  # Crosses midnight
            return current >= start or current <= end
    
    def _validate_session_with_market_data(self, session_type: SessionType, 
                                          market_data: MarketMicrostructure) -> SessionType:
        """
        Validate detected session with market microstructure data
        
        Args:
            session_type: Initially detected session
            market_data: Market microstructure data
            
        Returns:
            Validated or adjusted session type
        """
        # Check if market data suggests different session
        if session_type == SessionType.CONTINUOUS_TRADING:
            # Check for abnormal conditions
            if market_data.bid_ask_spread > 0.001:  # Wide spread
                if market_data.volume < 100:  # Low volume
                    # Might actually be in auction or transition
                    logger.warning("Low liquidity detected during continuous trading")
            
            # Check for auction characteristics
            if market_data.order_imbalance > 0.8:  # High imbalance
                if market_data.trade_count < 10:  # Few trades
                    # Likely in auction
                    logger.info("Auction characteristics detected")
                    return SessionType.INTRADAY_AUCTION
        
        return session_type
    
    def _create_session_info(self, session_type: SessionType, 
                            instrument: str, check_time: datetime) -> SessionInfo:
        """Create SessionInfo object with all details"""
        
        # Get margin rate for this session
        margin_rate = self.get_margin_rate_for_session(session_type, instrument)
        
        # Get volume pattern
        volume_pattern = self.volume_patterns.get(session_type, {})
        
        # Get session boundaries
        boundaries = self.get_session_boundaries(instrument, check_time, session_type)
        
        return SessionInfo(
            session_type=session_type,
            start_time=boundaries['start'],
            end_time=boundaries['end'],
            margin_rate=margin_rate,
            liquidity_level=volume_pattern.get('liquidity', 'medium'),
            volatility_expectation=volume_pattern.get('volatility', 'medium'),
            volume_multiplier=volume_pattern.get('volume_ratio', 1.0)
        )
    
    def get_margin_rate_for_session(self, session_type: SessionType, instrument: str) -> float:
        """
        Get margin rate for specific session type
        
        Args:
            session_type: Type of market session
            instrument: Market instrument
            
        Returns:
            Margin rate as decimal
        """
        # Determine asset class
        asset_class = self._classify_instrument(instrument)
        
        # Get session-specific rates
        session_rates = self.margin_rate_mappings.get(session_type, {})
        
        # Get rate for asset class
        rate = session_rates.get(asset_class, session_rates.get("indices", 0.02))
        
        return rate
    
    def _classify_instrument(self, instrument: str) -> str:
        """Classify instrument into asset class"""
        instrument_upper = instrument.upper()
        
        if "IX.D." in instrument_upper:
            return "indices"
        elif "CS.D." in instrument_upper and any(pair in instrument_upper for pair in ["USD", "EUR", "GBP", "JPY"]):
            return "forex"
        elif "CC.D." in instrument_upper or "OIL" in instrument_upper or "GOLD" in instrument_upper:
            return "commodities"
        else:
            return "indices"  # Default
    
    def get_session_boundaries(self, instrument: str, date: datetime, 
                              session_type: SessionType) -> Dict[str, datetime]:
        """
        Get exact session boundaries
        
        Args:
            instrument: Market instrument
            date: Date to check
            session_type: Session type
            
        Returns:
            Dictionary with start and end times
        """
        sessions = self.session_definitions.get(instrument, {})
        
        if session_type in sessions:
            start_time, end_time = sessions[session_type]
            
            # Convert to datetime
            market_tz = self.timezone_manager.get_timezone(
                self.timezone_manager.market_schedules[instrument].timezone
            )
            
            start_dt = datetime.combine(date.date(), start_time)
            end_dt = datetime.combine(date.date(), end_time)
            
            # Handle overnight sessions
            if end_time < start_time:
                end_dt += timedelta(days=1)
            
            # Localize and convert to UTC
            start_dt = market_tz.localize(start_dt).astimezone()
            end_dt = market_tz.localize(end_dt).astimezone()
            
            return {'start': start_dt, 'end': end_dt}
        
        # Default to full day
        return {
            'start': date.replace(hour=0, minute=0, second=0),
            'end': date.replace(hour=23, minute=59, second=59)
        }
    
    def get_overlapping_sessions(self, check_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get all market sessions overlapping at given time
        
        Args:
            check_time: Time to check (defaults to now)
            
        Returns:
            List of overlapping market sessions
        """
        if check_time is None:
            check_time = datetime.utcnow()
        
        overlapping = []
        
        # Check major markets
        major_markets = [
            ("IX.D.FTSE.DAILY.IP", "London"),
            ("IX.D.DAX.DAILY.IP", "Frankfurt"),
            ("IX.D.SPX.DAILY.IP", "New York"),
            ("IX.D.NIKKEI.DAILY.IP", "Tokyo")
        ]
        
        for instrument, city in major_markets:
            session = self.detect_current_session(instrument, check_time)
            
            if session.session_type in [SessionType.CONTINUOUS_TRADING, 
                                       SessionType.PRE_MARKET,
                                       SessionType.POST_MARKET]:
                overlapping.append({
                    'market': city,
                    'instrument': instrument,
                    'session': session.session_type.value,
                    'margin_rate': session.margin_rate,
                    'liquidity': session.liquidity_level
                })
        
        return overlapping
    
    def predict_next_session_change(self, instrument: str, 
                                   from_time: Optional[datetime] = None) -> Optional[Tuple[datetime, SessionType, float]]:
        """
        Predict next session change for an instrument
        
        Args:
            instrument: Market instrument
            from_time: Start time (defaults to now)
            
        Returns:
            Tuple of (change_time, new_session, new_margin_rate) or None
        """
        if from_time is None:
            from_time = datetime.utcnow()
        
        current_session = self.detect_current_session(instrument, from_time)
        sessions = self.session_definitions.get(instrument, {})
        
        # Get local time
        local_time = self.timezone_manager.get_market_time(instrument, from_time)
        current_time = local_time.time()
        
        # Find next session
        next_session = None
        min_time_diff = timedelta(days=1)
        
        for session_type, (start_time, end_time) in sessions.items():
            if session_type == current_session.session_type:
                continue
            
            # Calculate time until session starts
            start_dt = datetime.combine(local_time.date(), start_time)
            if start_dt <= local_time:
                start_dt += timedelta(days=1)
            
            time_diff = start_dt - local_time
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                next_session = session_type
                next_time = start_dt
        
        if next_session:
            next_margin_rate = self.get_margin_rate_for_session(next_session, instrument)
            return (next_time, next_session, next_margin_rate)
        
        return None
    
    def get_session_volatility_profile(self, session_type: SessionType) -> Dict[str, Any]:
        """
        Get expected volatility profile for a session
        
        Args:
            session_type: Type of session
            
        Returns:
            Volatility profile dictionary
        """
        profiles = {
            SessionType.MARKET_OPEN_AUCTION: {
                "volatility": "high",
                "typical_range_multiplier": 2.0,
                "gap_risk": "high",
                "recommended_position_reduction": 0.8
            },
            SessionType.CONTINUOUS_TRADING: {
                "volatility": "medium",
                "typical_range_multiplier": 1.0,
                "gap_risk": "low",
                "recommended_position_reduction": 1.0
            },
            SessionType.CLOSING_AUCTION: {
                "volatility": "high",
                "typical_range_multiplier": 1.5,
                "gap_risk": "medium",
                "recommended_position_reduction": 0.9
            },
            SessionType.OVERNIGHT: {
                "volatility": "low",
                "typical_range_multiplier": 0.5,
                "gap_risk": "high",
                "recommended_position_reduction": 0.7
            },
            SessionType.WEEKEND: {
                "volatility": "very_low",
                "typical_range_multiplier": 0.3,
                "gap_risk": "very_high",
                "recommended_position_reduction": 0.5
            }
        }
        
        return profiles.get(session_type, {
            "volatility": "medium",
            "typical_range_multiplier": 1.0,
            "gap_risk": "medium",
            "recommended_position_reduction": 1.0
        })
    
    def generate_session_report(self, instrument: str) -> str:
        """
        Generate comprehensive session report
        
        Args:
            instrument: Market instrument
            
        Returns:
            Formatted report string
        """
        current_session = self.detect_current_session(instrument)
        next_change = self.predict_next_session_change(instrument)
        overlapping = self.get_overlapping_sessions()
        
        report = f"""
╔══════════════════════════════════════════════════════╗
║           SESSION DETECTION REPORT                     ║
╠══════════════════════════════════════════════════════╣
║ Instrument: {instrument:<42}║
║                                                        ║
║ Current Session:                                       ║
║   Type: {current_session.session_type.value:<45}║
║   Margin Rate: {current_session.margin_rate*100:>5.2f}%                              ║
║   Liquidity: {current_session.liquidity_level:<43}║
║   Volatility: {current_session.volatility_expectation:<42}║
║                                                        ║"""
        
        if next_change:
            next_time, next_session, next_rate = next_change
            report += f"""
║ Next Session Change:                                   ║
║   Time: {next_time.strftime('%Y-%m-%d %H:%M %Z'):<45}║
║   Session: {next_session.value:<43}║
║   New Rate: {next_rate*100:>5.2f}%                               ║
║                                                        ║"""
        
        if overlapping:
            report += """
║ Overlapping Markets:                                   ║"""
            for market in overlapping:
                report += f"""
║   • {market['market']:<15} ({market['session']:<20}) {market['margin_rate']*100:>5.2f}%║"""
        
        report += """
╚══════════════════════════════════════════════════════╝"""
        
        return report

# Global instance
_session_detector = None

def get_session_detector() -> EnhancedSessionDetector:
    """Get global session detector instance"""
    global _session_detector
    if _session_detector is None:
        _session_detector = EnhancedSessionDetector()
    return _session_detector

if __name__ == "__main__":
    # Test the enhanced session detector
    print("📊 Testing Enhanced Session Detector")
    print("=" * 50)
    
    detector = EnhancedSessionDetector()
    
    # Test instruments
    test_instruments = [
        "IX.D.FTSE.DAILY.IP",
        "IX.D.DAX.DAILY.IP",
        "CS.D.EURUSD.MINI.IP"
    ]
    
    print("\n🕐 Current Sessions:")
    for instrument in test_instruments:
        session = detector.detect_current_session(instrument)
        print(f"{instrument}:")
        print(f"  Session: {session.session_type.value}")
        print(f"  Margin Rate: {session.margin_rate*100:.2f}%")
        print(f"  Liquidity: {session.liquidity_level}")
    
    print("\n📈 Session Report:")
    print(detector.generate_session_report("IX.D.FTSE.DAILY.IP"))
    
    print("\n🌍 Overlapping Sessions:")
    overlapping = detector.get_overlapping_sessions()
    for market in overlapping:
        print(f"  {market['market']}: {market['session']} (Rate: {market['margin_rate']*100:.2f}%)")