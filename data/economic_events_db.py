#!/usr/bin/env python3
"""
📊 Economic Events Database Operations

Handles storage and retrieval of economic calendar events in SQLite database.
Provides CRUD operations for economic events with efficient querying.

Author: Economic Calendar Integration System
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import logging
from dataclasses import asdict
from pathlib import Path

from core.economic_calendar_fetcher import EconomicEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EconomicEventsDatabase:
    """Database operations for economic calendar events"""
    
    def __init__(self, db_path: str = "data/economic_events.db"):
        """Initialize database connection and create tables"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Initialize database
        self._create_tables()
        logger.info(f"Economic events database initialized: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        """Create economic events tables"""
        
        create_events_table = """
        CREATE TABLE IF NOT EXISTS economic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date DATETIME NOT NULL,
            event_name TEXT NOT NULL,
            currency TEXT NOT NULL,
            impact_level TEXT NOT NULL CHECK(impact_level IN ('HIGH', 'MEDIUM', 'LOW')),
            actual_value TEXT,
            forecast_value TEXT,
            previous_value TEXT,
            source TEXT NOT NULL,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(event_date, event_name, currency, source)
        );
        """
        
        create_event_pauses_table = """
        CREATE TABLE IF NOT EXISTS event_pauses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            pause_start DATETIME NOT NULL,
            pause_end DATETIME NOT NULL,
            pause_reason TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES economic_events (id)
        );
        """
        
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_event_date ON economic_events (event_date);",
            "CREATE INDEX IF NOT EXISTS idx_currency ON economic_events (currency);",
            "CREATE INDEX IF NOT EXISTS idx_impact_level ON economic_events (impact_level);",
            "CREATE INDEX IF NOT EXISTS idx_source ON economic_events (source);",
            "CREATE INDEX IF NOT EXISTS idx_pause_times ON event_pauses (pause_start, pause_end);",
            "CREATE INDEX IF NOT EXISTS idx_pause_active ON event_pauses (is_active);"
        ]
        
        with self._get_connection() as conn:
            conn.execute(create_events_table)
            conn.execute(create_event_pauses_table)
            
            for index in create_indexes:
                conn.execute(index)
            
            conn.commit()
        
        logger.info("Economic events database tables created/verified")
    
    def insert_event(self, event: EconomicEvent) -> Optional[int]:
        """Insert a single economic event, return event ID"""
        
        insert_query = """
        INSERT OR REPLACE INTO economic_events (
            event_date, event_name, currency, impact_level,
            actual_value, forecast_value, previous_value,
            source, description, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(insert_query, (
                    event.event_date.isoformat(),
                    event.event_name,
                    event.currency,
                    event.impact_level,
                    str(event.actual_value) if event.actual_value is not None else None,
                    str(event.forecast_value) if event.forecast_value is not None else None,
                    str(event.previous_value) if event.previous_value is not None else None,
                    event.source,
                    event.description
                ))
                
                event_id = cursor.lastrowid
                conn.commit()
                return event_id
                
        except sqlite3.Error as e:
            logger.error(f"Error inserting event: {e}")
            return None
    
    def insert_events_batch(self, events: List[EconomicEvent]) -> int:
        """Insert multiple events in batch, return count of inserted events"""
        
        if not events:
            return 0
        
        insert_query = """
        INSERT OR REPLACE INTO economic_events (
            event_date, event_name, currency, impact_level,
            actual_value, forecast_value, previous_value,
            source, description, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        try:
            with self._get_connection() as conn:
                batch_data = []
                for event in events:
                    batch_data.append((
                        event.event_date.isoformat(),
                        event.event_name,
                        event.currency,
                        event.impact_level,
                        str(event.actual_value) if event.actual_value is not None else None,
                        str(event.forecast_value) if event.forecast_value is not None else None,
                        str(event.previous_value) if event.previous_value is not None else None,
                        event.source,
                        event.description
                    ))
                
                cursor = conn.executemany(insert_query, batch_data)
                conn.commit()
                
                inserted_count = cursor.rowcount
                logger.info(f"Inserted/updated {inserted_count} economic events")
                return inserted_count
                
        except sqlite3.Error as e:
            logger.error(f"Error inserting events batch: {e}")
            return 0
    
    def get_upcoming_events(self, 
                          hours_ahead: int = 168,  # 7 days default
                          currencies: List[str] = None,
                          impact_levels: List[str] = None,
                          min_impact: str = None) -> List[Dict]:
        """Get upcoming economic events with filters"""
        
        base_query = """
        SELECT id, event_date, event_name, currency, impact_level,
               actual_value, forecast_value, previous_value,
               source, description, created_at, updated_at
        FROM economic_events
        WHERE event_date BETWEEN ? AND ?
        """
        
        params = [
            datetime.now().isoformat(),
            (datetime.now() + timedelta(hours=hours_ahead)).isoformat()
        ]
        
        conditions = []
        
        # Filter by currencies
        if currencies:
            placeholders = ','.join(['?' for _ in currencies])
            conditions.append(f"currency IN ({placeholders})")
            params.extend(currencies)
        
        # Filter by impact levels
        if impact_levels:
            placeholders = ','.join(['?' for _ in impact_levels])
            conditions.append(f"impact_level IN ({placeholders})")
            params.extend(impact_levels)
        
        # Filter by minimum impact
        if min_impact:
            impact_hierarchy = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3}
            if min_impact == 'MEDIUM':
                conditions.append("impact_level IN ('MEDIUM', 'HIGH')")
            elif min_impact == 'HIGH':
                conditions.append("impact_level = 'HIGH'")
        
        # Add conditions to query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        base_query += " ORDER BY event_date ASC"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(base_query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event_dict = dict(row)
                    event_dict['event_date'] = datetime.fromisoformat(event_dict['event_date'])
                    events.append(event_dict)
                
                return events
                
        except sqlite3.Error as e:
            logger.error(f"Error fetching upcoming events: {e}")
            return []
    
    def get_high_impact_events_today(self) -> List[Dict]:
        """Get today's high-impact events"""
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return self.get_upcoming_events(
            hours_ahead=24,
            impact_levels=['HIGH']
        )
    
    def get_events_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events within specific timeframe"""
        
        query = """
        SELECT id, event_date, event_name, currency, impact_level,
               actual_value, forecast_value, previous_value,
               source, description
        FROM economic_events
        WHERE event_date BETWEEN ? AND ?
        ORDER BY event_date ASC
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, [start_time.isoformat(), end_time.isoformat()])
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event_dict = dict(row)
                    event_dict['event_date'] = datetime.fromisoformat(event_dict['event_date'])
                    events.append(event_dict)
                
                return events
                
        except sqlite3.Error as e:
            logger.error(f"Error fetching events in timeframe: {e}")
            return []
    
    def create_event_pause(self, 
                          event_id: int, 
                          pause_start: datetime, 
                          pause_end: datetime, 
                          reason: str = None) -> Optional[int]:
        """Create a trading pause record for an event"""
        
        insert_query = """
        INSERT INTO event_pauses (event_id, pause_start, pause_end, pause_reason, is_active)
        VALUES (?, ?, ?, ?, TRUE)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(insert_query, [
                    event_id,
                    pause_start.isoformat(),
                    pause_end.isoformat(),
                    reason
                ])
                
                pause_id = cursor.lastrowid
                conn.commit()
                return pause_id
                
        except sqlite3.Error as e:
            logger.error(f"Error creating event pause: {e}")
            return None
    
    def get_active_pauses(self, current_time: datetime = None) -> List[Dict]:
        """Get currently active trading pauses"""
        
        if current_time is None:
            current_time = datetime.now()
        
        query = """
        SELECT p.id as pause_id, p.event_id, p.pause_start, p.pause_end, p.pause_reason,
               e.event_name, e.currency, e.impact_level
        FROM event_pauses p
        JOIN economic_events e ON p.event_id = e.id
        WHERE p.is_active = TRUE
          AND p.pause_start <= ?
          AND p.pause_end >= ?
        ORDER BY p.pause_end ASC
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, [
                    current_time.isoformat(),
                    current_time.isoformat()
                ])
                rows = cursor.fetchall()
                
                pauses = []
                for row in rows:
                    pause_dict = dict(row)
                    pause_dict['pause_start'] = datetime.fromisoformat(pause_dict['pause_start'])
                    pause_dict['pause_end'] = datetime.fromisoformat(pause_dict['pause_end'])
                    pauses.append(pause_dict)
                
                return pauses
                
        except sqlite3.Error as e:
            logger.error(f"Error fetching active pauses: {e}")
            return []
    
    def deactivate_pause(self, pause_id: int) -> bool:
        """Deactivate a trading pause"""
        
        update_query = "UPDATE event_pauses SET is_active = FALSE WHERE id = ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(update_query, [pause_id])
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error deactivating pause: {e}")
            return False
    
    def cleanup_old_events(self, days_to_keep: int = 30) -> int:
        """Remove events older than specified days"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        delete_query = "DELETE FROM economic_events WHERE event_date < ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(delete_query, [cutoff_date.isoformat()])
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} old economic events")
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Error cleaning up old events: {e}")
            return 0
    
    def get_event_statistics(self) -> Dict:
        """Get statistics about stored events"""
        
        stats_query = """
        SELECT 
            COUNT(*) as total_events,
            COUNT(CASE WHEN impact_level = 'HIGH' THEN 1 END) as high_impact,
            COUNT(CASE WHEN impact_level = 'MEDIUM' THEN 1 END) as medium_impact,
            COUNT(CASE WHEN impact_level = 'LOW' THEN 1 END) as low_impact,
            COUNT(CASE WHEN event_date > datetime('now') THEN 1 END) as upcoming_events,
            COUNT(DISTINCT currency) as currencies_tracked,
            COUNT(DISTINCT source) as data_sources,
            MIN(event_date) as earliest_event,
            MAX(event_date) as latest_event
        FROM economic_events
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(stats_query)
                row = cursor.fetchone()
                
                stats = dict(row) if row else {}
                
                # Convert datetime strings
                if stats.get('earliest_event'):
                    stats['earliest_event'] = datetime.fromisoformat(stats['earliest_event'])
                if stats.get('latest_event'):
                    stats['latest_event'] = datetime.fromisoformat(stats['latest_event'])
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Error fetching event statistics: {e}")
            return {}

# Global database instance
_economic_events_db = None

def get_economic_events_db() -> EconomicEventsDatabase:
    """Get global economic events database instance"""
    global _economic_events_db
    if _economic_events_db is None:
        _economic_events_db = EconomicEventsDatabase()
    return _economic_events_db

def test_economic_events_db():
    """Test economic events database operations"""
    print("🧪 Testing Economic Events Database")
    print("=" * 40)
    
    # Initialize database
    db = EconomicEventsDatabase("test_economic_events.db")
    
    # Create test events
    test_events = [
        EconomicEvent(
            event_date=datetime.now() + timedelta(hours=2),
            event_name="FOMC Interest Rate Decision",
            currency="USD",
            impact_level="HIGH",
            forecast_value="5.25%",
            previous_value="5.0%",
            source="test",
            description="Federal Reserve interest rate decision"
        ),
        EconomicEvent(
            event_date=datetime.now() + timedelta(days=1),
            event_name="ECB Meeting",
            currency="EUR",
            impact_level="HIGH",
            source="test",
            description="European Central Bank policy meeting"
        ),
        EconomicEvent(
            event_date=datetime.now() + timedelta(hours=6),
            event_name="UK CPI",
            currency="GBP",
            impact_level="MEDIUM",
            actual_value="2.1%",
            forecast_value="2.0%",
            source="test",
            description="UK Consumer Price Index"
        )
    ]
    
    # Test batch insert
    inserted_count = db.insert_events_batch(test_events)
    print(f"✅ Inserted {inserted_count} test events")
    
    # Test upcoming events query
    upcoming = db.get_upcoming_events(hours_ahead=48, currencies=['USD', 'EUR', 'GBP'])
    print(f"✅ Found {len(upcoming)} upcoming events")
    
    # Test high-impact events
    high_impact = db.get_upcoming_events(impact_levels=['HIGH'])
    print(f"✅ Found {len(high_impact)} high-impact events")
    
    # Test statistics
    stats = db.get_event_statistics()
    print(f"✅ Database statistics:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test pause creation
    if upcoming:
        event_id = upcoming[0]['id']
        pause_start = datetime.now()
        pause_end = pause_start + timedelta(hours=4)
        
        pause_id = db.create_event_pause(event_id, pause_start, pause_end, "Test pause")
        print(f"✅ Created test pause: {pause_id}")
        
        # Test active pauses
        active_pauses = db.get_active_pauses()
        print(f"✅ Found {len(active_pauses)} active pauses")
    
    # Cleanup
    try:
        import os
        os.remove("test_economic_events.db")
        print("✅ Test database cleaned up")
    except:
        pass
    
    print("\n🎉 Economic Events Database test completed!")

if __name__ == "__main__":
    test_economic_events_db()