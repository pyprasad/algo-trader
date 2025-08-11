#!/usr/bin/env python3
"""
📅 Economic Calendar Monitor

Core component that monitors economic events and determines when to pause trading.
Integrates with data fetchers and database to provide real-time event monitoring.

Features:
- Real-time event monitoring
- High-impact event detection
- Trading pause calculations
- Market-specific event filtering
- Automated data updates

Author: Economic Calendar Integration System
"""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
import logging
from dataclasses import dataclass

from core.economic_calendar_fetcher import EconomicCalendarDataFetcher, EconomicEvent
from data.economic_events_db import get_economic_events_db
from utils.config_loader import load_global_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradingPauseWindow:
    """Represents a trading pause window for an economic event"""
    event_id: int
    event_name: str
    currency: str
    impact_level: str
    event_time: datetime
    pause_start: datetime
    pause_end: datetime
    affected_markets: List[str]
    reason: str

class EconomicCalendarMonitor:
    """Main economic calendar monitoring system"""
    
    def __init__(self, config: Dict = None):
        """Initialize economic calendar monitor"""
        
        self.config = config or load_global_config().get('economic_calendar', {})
        self.db = get_economic_events_db()
        
        # Initialize data fetcher
        data_sources_config = self.config.get('data_sources', {})
        self.data_fetcher = EconomicCalendarDataFetcher(data_sources_config)
        
        # Configuration
        self.enabled = self.config.get('enabled', True)
        self.update_interval_hours = self.config.get('update_interval_hours', 6)
        
        # Pause settings
        pause_settings = self.config.get('pause_settings', {})
        self.high_impact_pause_enabled = pause_settings.get('high_impact_events', True)
        self.pause_before_minutes = pause_settings.get('pause_before_minutes', 120)
        self.pause_after_minutes = pause_settings.get('pause_after_minutes', 120)
        self.close_positions_before = pause_settings.get('close_positions_before', True)
        
        # High-impact events configuration
        self.high_impact_events = set(self.config.get('high_impact_events', [
            "FOMC Meeting",
            "Interest Rate Decision", 
            "ECB Meeting",
            "BOE Meeting",
            "Non-Farm Payrolls",
            "NFP",
            "CPI",
            "GDP",
            "Central Bank Speech"
        ]))
        
        # Market mappings
        self.market_mappings = self.config.get('market_mappings', {
            'BOE': ['FTSE'],
            'ECB': ['DAX'],
            'FOMC': ['US500'],
            'USD': ['US500'],
            'EUR': ['DAX'],
            'GBP': ['FTSE']
        })
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_update = None
        self.current_pauses: List[TradingPauseWindow] = []
        
        # Cache for performance
        self._upcoming_events_cache = []
        self._cache_expires = None
        
        logger.info(f"📅 Economic Calendar Monitor initialized")
        logger.info(f"   High-impact pause: {'✅ ENABLED' if self.high_impact_pause_enabled else '❌ DISABLED'}")
        logger.info(f"   Pause window: {self.pause_before_minutes}min before → {self.pause_after_minutes}min after")
        logger.info(f"   Update interval: {self.update_interval_hours} hours")
    
    def start_monitoring(self) -> bool:
        """Start continuous economic calendar monitoring"""
        
        if not self.enabled:
            logger.warning("Economic calendar monitoring is disabled")
            return False
        
        if self.monitoring_active:
            logger.warning("Economic calendar monitoring already active")
            return True
        
        try:
            # Initial data fetch
            logger.info("📥 Fetching initial economic calendar data...")
            self.update_events_data()
            
            # Start monitoring thread
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("📅 Economic Calendar Monitor started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start economic calendar monitoring: {e}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self):
        """Stop economic calendar monitoring"""
        
        self.monitoring_active = False
        
        if self.monitoring_thread:
            logger.info("📅 Stopping Economic Calendar Monitor...")
            self.monitoring_thread.join(timeout=10)
        
        logger.info("📅 Economic Calendar Monitor stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Update events data periodically
                if self._should_update_data():
                    logger.info("🔄 Updating economic calendar data...")
                    self.update_events_data()
                
                # Update current pause windows
                self._update_pause_windows()
                
                # Log status every hour
                current_time = datetime.now()
                if current_time.minute == 0:
                    self._log_monitoring_status()
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in economic calendar monitoring loop: {e}")
                time.sleep(60)
    
    def _should_update_data(self) -> bool:
        """Check if data should be updated"""
        
        if self.last_update is None:
            return True
        
        time_since_update = datetime.now() - self.last_update
        return time_since_update.total_seconds() > (self.update_interval_hours * 3600)
    
    def update_events_data(self) -> int:
        """Fetch and store latest economic events data"""
        
        try:
            # Fetch events from all sources
            events = self.data_fetcher.fetch_all_events(days_ahead=14)
            
            if events:
                # Store in database
                inserted_count = self.db.insert_events_batch(events)
                
                # Update cache
                self._update_cache()
                
                # Update last update time
                self.last_update = datetime.now()
                
                logger.info(f"📊 Updated {inserted_count} economic events")
                return inserted_count
            else:
                logger.warning("No events fetched from data sources")
                return 0
                
        except Exception as e:
            logger.error(f"Error updating events data: {e}")
            return 0
    
    def _update_cache(self):
        """Update upcoming events cache"""
        
        try:
            self._upcoming_events_cache = self.db.get_upcoming_events(
                hours_ahead=168,  # 7 days
                currencies=['USD', 'EUR', 'GBP']
            )
            self._cache_expires = datetime.now() + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Error updating events cache: {e}")
    
    def _update_pause_windows(self):
        """Update current trading pause windows"""
        
        try:
            # Get active pauses from database
            active_pauses_db = self.db.get_active_pauses()
            
            # Convert to pause windows
            self.current_pauses = []
            
            for pause_data in active_pauses_db:
                pause_window = TradingPauseWindow(
                    event_id=pause_data['event_id'],
                    event_name=pause_data['event_name'],
                    currency=pause_data['currency'],
                    impact_level=pause_data['impact_level'],
                    event_time=pause_data['pause_start'] + timedelta(minutes=self.pause_before_minutes),
                    pause_start=pause_data['pause_start'],
                    pause_end=pause_data['pause_end'],
                    affected_markets=self._get_affected_markets(pause_data['currency']),
                    reason=pause_data['pause_reason'] or f"High-impact {pause_data['event_name']}"
                )
                
                self.current_pauses.append(pause_window)
            
            # Create new pause windows for upcoming high-impact events
            self._create_new_pause_windows()
            
        except Exception as e:
            logger.error(f"Error updating pause windows: {e}")
    
    def _create_new_pause_windows(self):
        """Create pause windows for upcoming high-impact events"""
        
        if not self.high_impact_pause_enabled:
            return
        
        try:
            # Get upcoming high-impact events
            upcoming_events = self.get_upcoming_high_impact_events(hours_ahead=48)
            
            # Get existing pause event IDs
            existing_pause_event_ids = {pause.event_id for pause in self.current_pauses}
            
            for event in upcoming_events:
                event_id = event['id']
                
                # Skip if pause already exists
                if event_id in existing_pause_event_ids:
                    continue
                
                # Calculate pause window
                event_time = event['event_date']
                pause_start = event_time - timedelta(minutes=self.pause_before_minutes)
                pause_end = event_time + timedelta(minutes=self.pause_after_minutes)
                
                # Only create pause if it's in the future
                if pause_start > datetime.now():
                    # Create pause in database
                    reason = f"High-impact {event['event_name']} ({event['currency']})"
                    pause_id = self.db.create_event_pause(
                        event_id=event_id,
                        pause_start=pause_start,
                        pause_end=pause_end,
                        reason=reason
                    )
                    
                    if pause_id:
                        logger.info(f"📅 Created pause window for {event['event_name']} ({event_time.strftime('%Y-%m-%d %H:%M')})")
        
        except Exception as e:
            logger.error(f"Error creating new pause windows: {e}")
    
    def is_trading_paused(self, market: str = None, current_time: datetime = None) -> Tuple[bool, Optional[str]]:
        """Check if trading should be paused for a market"""
        
        if not self.enabled or not self.high_impact_pause_enabled:
            return False, None
        
        if current_time is None:
            current_time = datetime.now()
        
        for pause_window in self.current_pauses:
            # Check if we're in the pause window
            if pause_window.pause_start <= current_time <= pause_window.pause_end:
                
                # Check if this pause affects the specified market
                if market is None or market in pause_window.affected_markets:
                    return True, pause_window.reason
        
        return False, None
    
    def get_upcoming_high_impact_events(self, hours_ahead: int = 24) -> List[Dict]:
        """Get upcoming high-impact economic events"""
        
        try:
            events = self.db.get_upcoming_events(
                hours_ahead=hours_ahead,
                currencies=['USD', 'EUR', 'GBP'],
                impact_levels=['HIGH']
            )
            
            # Filter by high-impact event names
            high_impact_events = []
            for event in events:
                if self._is_high_impact_event(event['event_name']):
                    high_impact_events.append(event)
            
            return high_impact_events
            
        except Exception as e:
            logger.error(f"Error fetching upcoming high-impact events: {e}")
            return []
    
    def _is_high_impact_event(self, event_name: str) -> bool:
        """Check if an event is considered high-impact"""
        
        event_name_lower = event_name.lower()
        
        for high_impact_keyword in self.high_impact_events:
            if high_impact_keyword.lower() in event_name_lower:
                return True
        
        return False
    
    def _get_affected_markets(self, currency: str) -> List[str]:
        """Get markets affected by currency-specific events"""
        
        affected_markets = []
        
        # Direct currency mapping
        if currency in self.market_mappings:
            affected_markets.extend(self.market_mappings[currency])
        
        # Special cases
        if 'boe' in currency.lower() or currency == 'GBP':
            affected_markets.extend(self.market_mappings.get('BOE', []))
        
        if 'ecb' in currency.lower() or currency == 'EUR':
            affected_markets.extend(self.market_mappings.get('ECB', []))
        
        if 'fomc' in currency.lower() or 'fed' in currency.lower() or currency == 'USD':
            affected_markets.extend(self.market_mappings.get('FOMC', []))
        
        return list(set(affected_markets))  # Remove duplicates
    
    def get_next_pause_info(self) -> Optional[Dict]:
        """Get information about the next trading pause"""
        
        if not self.current_pauses:
            return None
        
        current_time = datetime.now()
        
        # Find next pause
        future_pauses = [
            pause for pause in self.current_pauses 
            if pause.pause_start > current_time
        ]
        
        if not future_pauses:
            return None
        
        # Sort by pause start time
        future_pauses.sort(key=lambda x: x.pause_start)
        next_pause = future_pauses[0]
        
        time_until_pause = next_pause.pause_start - current_time
        
        return {
            'event_name': next_pause.event_name,
            'currency': next_pause.currency,
            'event_time': next_pause.event_time,
            'pause_start': next_pause.pause_start,
            'pause_end': next_pause.pause_end,
            'affected_markets': next_pause.affected_markets,
            'time_until_pause': time_until_pause,
            'reason': next_pause.reason
        }
    
    def _log_monitoring_status(self):
        """Log current monitoring status"""
        
        try:
            # Current pause status
            is_paused, pause_reason = self.is_trading_paused()
            
            if is_paused:
                logger.info(f"📅 Trading currently PAUSED: {pause_reason}")
            else:
                # Show next pause if any
                next_pause = self.get_next_pause_info()
                if next_pause:
                    hours_until = next_pause['time_until_pause'].total_seconds() / 3600
                    logger.info(f"📅 Next pause: {next_pause['event_name']} in {hours_until:.1f}h ({next_pause['pause_start'].strftime('%Y-%m-%d %H:%M')})")
                else:
                    logger.info("📅 No upcoming trading pauses scheduled")
            
            # Statistics
            stats = self.db.get_event_statistics()
            if stats:
                logger.info(f"📊 Calendar stats: {stats.get('upcoming_events', 0)} upcoming, {stats.get('high_impact', 0)} high-impact")
        
        except Exception as e:
            logger.error(f"Error logging monitoring status: {e}")
    
    def get_calendar_summary(self) -> Dict:
        """Get comprehensive calendar summary"""
        
        try:
            current_time = datetime.now()
            
            # Current pause status
            is_paused, pause_reason = self.is_trading_paused()
            
            # Upcoming events
            upcoming_24h = self.get_upcoming_high_impact_events(hours_ahead=24)
            upcoming_7d = self.get_upcoming_high_impact_events(hours_ahead=168)
            
            # Next pause info
            next_pause = self.get_next_pause_info()
            
            # Database statistics
            stats = self.db.get_event_statistics()
            
            return {
                'monitoring_active': self.monitoring_active,
                'last_update': self.last_update,
                'current_pause': {
                    'is_paused': is_paused,
                    'reason': pause_reason
                },
                'upcoming_events': {
                    'next_24h': len(upcoming_24h),
                    'next_7d': len(upcoming_7d),
                    'events_24h': upcoming_24h[:5]  # Top 5
                },
                'next_pause': next_pause,
                'statistics': stats,
                'configuration': {
                    'enabled': self.enabled,
                    'pause_before_minutes': self.pause_before_minutes,
                    'pause_after_minutes': self.pause_after_minutes,
                    'update_interval_hours': self.update_interval_hours
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating calendar summary: {e}")
            return {'error': str(e)}

# Global monitor instance
_economic_calendar_monitor = None

def get_economic_calendar_monitor() -> EconomicCalendarMonitor:
    """Get global economic calendar monitor instance"""
    global _economic_calendar_monitor
    if _economic_calendar_monitor is None:
        _economic_calendar_monitor = EconomicCalendarMonitor()
    return _economic_calendar_monitor

def test_economic_calendar_monitor():
    """Test economic calendar monitor functionality"""
    print("🧪 Testing Economic Calendar Monitor")
    print("=" * 50)
    
    # Test configuration
    test_config = {
        'enabled': True,
        'data_sources': {
            'alpha_vantage': {
                'enabled': True,
                'key': 'WB87DUF9M5MPKMTM'
            }
        },
        'pause_settings': {
            'high_impact_events': True,
            'pause_before_minutes': 60,
            'pause_after_minutes': 60
        },
        'high_impact_events': [
            'FOMC Meeting',
            'Interest Rate Decision',
            'ECB Meeting',
            'BOE Meeting'
        ]
    }
    
    # Initialize monitor
    monitor = EconomicCalendarMonitor(test_config)
    
    # Test data update
    print("📥 Testing data update...")
    updated_count = monitor.update_events_data()
    print(f"✅ Updated {updated_count} events")
    
    # Test pause checking
    print("\n📅 Testing pause checking...")
    is_paused, reason = monitor.is_trading_paused()
    print(f"Trading paused: {is_paused}")
    if is_paused:
        print(f"Reason: {reason}")
    
    # Test upcoming events
    print("\n📊 Testing upcoming events...")
    upcoming = monitor.get_upcoming_high_impact_events(hours_ahead=168)
    print(f"Found {len(upcoming)} upcoming high-impact events:")
    
    for event in upcoming[:3]:  # Show first 3
        print(f"  📈 {event['event_date'].strftime('%Y-%m-%d %H:%M')} | {event['currency']} | {event['event_name']}")
    
    # Test summary
    print("\n📋 Testing calendar summary...")
    summary = monitor.get_calendar_summary()
    print(f"Monitoring active: {summary.get('monitoring_active')}")
    print(f"Events next 24h: {summary.get('upcoming_events', {}).get('next_24h', 0)}")
    
    print("\n🎉 Economic Calendar Monitor test completed!")

if __name__ == "__main__":
    test_economic_calendar_monitor()