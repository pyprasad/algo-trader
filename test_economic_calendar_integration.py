#!/usr/bin/env python3
"""
🧪 Economic Calendar Integration Tests

Comprehensive test suite for the economic calendar system including:
- Data fetcher tests
- Database operations tests  
- Calendar monitor tests
- Risk manager integration tests
- End-to-end system tests

Author: Economic Calendar Integration System
"""

import unittest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.economic_calendar_fetcher import (
    EconomicEvent, AlphaVantageEconomicFetcher, 
    ForexFactoryFetcher, EconomicCalendarDataFetcher
)
from data.economic_events_db import EconomicEventsDatabase
from core.economic_calendar_monitor import EconomicCalendarMonitor
from core.emergency_risk_manager import EmergencyRiskManager

class TestEconomicEvent(unittest.TestCase):
    """Test EconomicEvent data class"""
    
    def test_economic_event_creation(self):
        """Test creating an economic event"""
        event = EconomicEvent(
            event_date=datetime.now(),
            event_name="FOMC Meeting",
            currency="USD",
            impact_level="HIGH",
            forecast_value="5.25%",
            source="test"
        )
        
        self.assertEqual(event.event_name, "FOMC Meeting")
        self.assertEqual(event.currency, "USD")
        self.assertEqual(event.impact_level, "HIGH")
        self.assertEqual(event.forecast_value, "5.25%")
        self.assertEqual(event.source, "test")

class TestAlphaVantageEconomicFetcher(unittest.TestCase):
    """Test Alpha Vantage economic data fetcher"""
    
    def setUp(self):
        self.fetcher = AlphaVantageEconomicFetcher("test_api_key")
    
    @patch('requests.get')
    def test_successful_api_request(self, mock_get):
        """Test successful API request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'date': '2024-08-01',
                    'value': '5.25'
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Mock sleep to speed up tests
        with patch('time.sleep'):
            data = self.fetcher._make_request('TEST_FUNCTION')
        
        self.assertIn('data', data)
        self.assertEqual(len(data['data']), 1)
    
    @patch('requests.get')
    def test_rate_limit_handling(self, mock_get):
        """Test rate limit handling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'Note': 'API call frequency limit reached'
        }
        mock_get.return_value = mock_response
        
        # Should return empty dict on rate limit
        with patch('time.sleep'):
            data = self.fetcher._make_request('TEST_FUNCTION')
        
        # Should attempt retry after rate limit
        self.assertEqual(mock_get.call_count, 2)  # Initial call + retry
    
    def test_fetch_economic_indicators(self):
        """Test fetching economic indicators"""
        with patch.object(self.fetcher, '_make_request') as mock_request:
            mock_request.return_value = {
                'data': [
                    {
                        'date': '2024-08-01',
                        'value': '5.25'
                    }
                ]
            }
            
            events = self.fetcher.fetch_economic_indicators()
            
            # Should call multiple economic indicators
            self.assertGreater(mock_request.call_count, 5)
            self.assertIsInstance(events, list)

class TestEconomicEventsDatabase(unittest.TestCase):
    """Test economic events database operations"""
    
    def setUp(self):
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_economic_events.db')
        self.db = EconomicEventsDatabase(self.db_path)
    
    def tearDown(self):
        # Clean up temporary database
        shutil.rmtree(self.temp_dir)
    
    def test_database_initialization(self):
        """Test database tables are created correctly"""
        # Database should be initialized without errors
        self.assertTrue(os.path.exists(self.db_path))
        
        # Test table creation by inserting a test event
        test_event = EconomicEvent(
            event_date=datetime.now(),
            event_name="Test Event",
            currency="USD",
            impact_level="HIGH",
            source="test"
        )
        
        event_id = self.db.insert_event(test_event)
        self.assertIsNotNone(event_id)
    
    def test_insert_and_retrieve_events(self):
        """Test inserting and retrieving events"""
        # Create test events
        events = [
            EconomicEvent(
                event_date=datetime.now() + timedelta(hours=2),
                event_name="FOMC Meeting",
                currency="USD",
                impact_level="HIGH",
                source="test"
            ),
            EconomicEvent(
                event_date=datetime.now() + timedelta(days=1),
                event_name="ECB Meeting",
                currency="EUR",
                impact_level="HIGH",
                source="test"
            )
        ]
        
        # Insert events
        inserted_count = self.db.insert_events_batch(events)
        self.assertEqual(inserted_count, 2)
        
        # Retrieve upcoming events
        upcoming = self.db.get_upcoming_events(hours_ahead=48)
        self.assertEqual(len(upcoming), 2)
        
        # Test filtering by currency
        usd_events = self.db.get_upcoming_events(
            hours_ahead=48, 
            currencies=['USD']
        )
        self.assertEqual(len(usd_events), 1)
        self.assertEqual(usd_events[0]['currency'], 'USD')
    
    def test_event_pause_operations(self):
        """Test event pause creation and retrieval"""
        # Insert a test event first
        test_event = EconomicEvent(
            event_date=datetime.now() + timedelta(hours=1),
            event_name="Test Event",
            currency="USD",
            impact_level="HIGH",
            source="test"
        )
        
        event_id = self.db.insert_event(test_event)
        
        # Create pause window
        pause_start = datetime.now()
        pause_end = pause_start + timedelta(hours=4)
        
        pause_id = self.db.create_event_pause(
            event_id, pause_start, pause_end, "Test pause"
        )
        self.assertIsNotNone(pause_id)
        
        # Check active pauses
        active_pauses = self.db.get_active_pauses()
        self.assertEqual(len(active_pauses), 1)
        self.assertEqual(active_pauses[0]['pause_reason'], "Test pause")
    
    def test_database_statistics(self):
        """Test database statistics"""
        # Insert some test events
        events = [
            EconomicEvent(
                event_date=datetime.now() + timedelta(hours=i),
                event_name=f"Event {i}",
                currency="USD" if i % 2 == 0 else "EUR",
                impact_level="HIGH" if i < 2 else "MEDIUM",
                source="test"
            )
            for i in range(5)
        ]
        
        self.db.insert_events_batch(events)
        
        # Get statistics
        stats = self.db.get_event_statistics()
        
        self.assertEqual(stats['total_events'], 5)
        self.assertEqual(stats['high_impact'], 2)
        self.assertEqual(stats['medium_impact'], 3)
        self.assertEqual(stats['currencies_tracked'], 2)

class TestEconomicCalendarMonitor(unittest.TestCase):
    """Test economic calendar monitor"""
    
    def setUp(self):
        # Create test configuration
        self.test_config = {
            'enabled': True,
            'data_sources': {
                'alpha_vantage': {
                    'enabled': True,
                    'key': 'test_key'
                }
            },
            'pause_settings': {
                'high_impact_events': True,
                'pause_before_minutes': 60,
                'pause_after_minutes': 60
            },
            'high_impact_events': [
                'FOMC Meeting',
                'ECB Meeting'
            ]
        }
        
        # Mock the database
        self.mock_db = Mock()
        
        # Create monitor with test config
        with patch('core.economic_calendar_monitor.get_economic_events_db', return_value=self.mock_db):
            self.monitor = EconomicCalendarMonitor(self.test_config)
    
    def test_monitor_initialization(self):
        """Test monitor initialization"""
        self.assertTrue(self.monitor.enabled)
        self.assertEqual(self.monitor.pause_before_minutes, 60)
        self.assertEqual(self.monitor.pause_after_minutes, 60)
        self.assertIn('FOMC Meeting', self.monitor.high_impact_events)
    
    def test_high_impact_event_detection(self):
        """Test high-impact event detection"""
        # Test positive cases
        self.assertTrue(self.monitor._is_high_impact_event("FOMC Meeting Minutes"))
        self.assertTrue(self.monitor._is_high_impact_event("ECB Interest Rate Decision"))
        
        # Test negative cases
        self.assertFalse(self.monitor._is_high_impact_event("Minor Economic Data"))
    
    def test_trading_pause_logic(self):
        """Test trading pause logic"""
        # Mock current pause windows
        current_time = datetime.now()
        pause_window = Mock()
        pause_window.pause_start = current_time - timedelta(minutes=30)
        pause_window.pause_end = current_time + timedelta(minutes=30)
        pause_window.affected_markets = ['USD', 'FTSE']
        pause_window.reason = "Test pause"
        
        self.monitor.current_pauses = [pause_window]
        
        # Test pause detection
        is_paused, reason = self.monitor.is_trading_paused()
        self.assertTrue(is_paused)
        self.assertEqual(reason, "Test pause")
        
        # Test market-specific pause
        is_paused_ftse, reason_ftse = self.monitor.is_trading_paused('FTSE')
        self.assertTrue(is_paused_ftse)
        
        # Test unaffected market
        is_paused_other, reason_other = self.monitor.is_trading_paused('OTHER')
        self.assertFalse(is_paused_other)
    
    @patch('core.economic_calendar_monitor.EconomicCalendarDataFetcher')
    def test_data_update(self, mock_fetcher_class):
        """Test data update functionality"""
        # Mock fetcher
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_events.return_value = [
            EconomicEvent(
                event_date=datetime.now() + timedelta(hours=2),
                event_name="Test Event",
                currency="USD",
                impact_level="HIGH",
                source="test"
            )
        ]
        mock_fetcher_class.return_value = mock_fetcher
        
        # Mock database
        self.mock_db.insert_events_batch.return_value = 1
        
        # Test data update
        count = self.monitor.update_events_data()
        
        self.assertEqual(count, 1)
        mock_fetcher.fetch_all_events.assert_called_once()
        self.mock_db.insert_events_batch.assert_called_once()

class TestRiskManagerIntegration(unittest.TestCase):
    """Test integration with emergency risk manager"""
    
    def setUp(self):
        # Mock account balance
        with patch('core.emergency_risk_manager.get_account_balance', return_value=10000):
            self.risk_manager = EmergencyRiskManager()
    
    @patch('core.emergency_risk_manager.get_economic_calendar_monitor')
    def test_economic_event_pause_integration(self, mock_get_calendar):
        """Test economic event pause integration"""
        # Mock calendar monitor
        mock_monitor = Mock()
        mock_monitor.enabled = True
        mock_monitor.is_trading_paused.return_value = (True, "FOMC Meeting in progress")
        mock_get_calendar.return_value = mock_monitor
        
        # Test trade validation during economic pause
        can_trade, reason = self.risk_manager.validate_trade(
            market="FTSE",
            direction="BUY", 
            size=100,
            current_price=100.0,
            stop_loss=95.0
        )
        
        self.assertFalse(can_trade)
        self.assertIn("Economic event pause", reason)
        self.assertIn("FOMC Meeting", reason)
    
    @patch('core.emergency_risk_manager.get_economic_calendar_monitor')
    def test_no_pause_when_calendar_disabled(self, mock_get_calendar):
        """Test no pause when calendar is disabled"""
        # Mock disabled calendar monitor
        mock_monitor = Mock()
        mock_monitor.enabled = False
        mock_get_calendar.return_value = mock_monitor
        
        # Mock account balance for trade validation
        with patch('core.emergency_risk_manager.get_account_balance', return_value=10000):
            # Test trade validation - should not be paused by calendar
            can_trade, reason = self.risk_manager.validate_trade(
                market="FTSE",
                direction="BUY",
                size=100, 
                current_price=100.0,
                stop_loss=95.0
            )
        
        # Should pass calendar check (but may fail other checks)
        self.assertNotIn("Economic event pause", reason)
    
    @patch('core.emergency_risk_manager.get_economic_calendar_monitor')
    def test_calendar_status_retrieval(self, mock_get_calendar):
        """Test calendar status retrieval"""
        # Mock calendar monitor with summary
        mock_monitor = Mock()
        mock_monitor.get_calendar_summary.return_value = {
            'monitoring_active': True,
            'current_pause': {
                'is_paused': False,
                'reason': None
            },
            'upcoming_events': {
                'next_24h': 2
            }
        }
        mock_get_calendar.return_value = mock_monitor
        
        # Get calendar status
        status = self.risk_manager.get_economic_calendar_status()
        
        self.assertTrue(status['available'])
        self.assertTrue(status['monitoring_active'])
        self.assertFalse(status['is_paused'])
        self.assertEqual(status['upcoming_events_24h'], 2)

class TestEndToEndIntegration(unittest.TestCase):
    """Test complete end-to-end integration"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    @patch('core.economic_calendar_fetcher.requests.get')
    def test_complete_workflow(self, mock_requests):
        """Test complete economic calendar workflow"""
        # Mock Alpha Vantage API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'date': (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d'),
                    'value': '5.25'
                }
            ]
        }
        mock_requests.return_value = mock_response
        
        # Create test database
        db_path = os.path.join(self.temp_dir, 'test_events.db')
        db = EconomicEventsDatabase(db_path)
        
        # Create test configuration
        config = {
            'enabled': True,
            'data_sources': {
                'alpha_vantage': {
                    'enabled': True,
                    'key': 'test_key'
                }
            },
            'pause_settings': {
                'high_impact_events': True,
                'pause_before_minutes': 120,
                'pause_after_minutes': 120
            },
            'high_impact_events': ['Federal Funds Rate']
        }
        
        # Test complete workflow
        with patch('core.economic_calendar_monitor.get_economic_events_db', return_value=db):
            with patch('time.sleep'):  # Speed up tests
                # Create monitor
                monitor = EconomicCalendarMonitor(config)
                
                # Update data
                count = monitor.update_events_data()
                self.assertGreaterEqual(count, 0)
                
                # Check pause status
                is_paused, reason = monitor.is_trading_paused()
                self.assertIsInstance(is_paused, bool)
                
                # Get calendar summary
                summary = monitor.get_calendar_summary()
                self.assertIn('monitoring_active', summary)
                self.assertIn('current_pause', summary)

def run_economic_calendar_tests():
    """Run all economic calendar tests"""
    print("🧪 Running Economic Calendar Integration Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestEconomicEvent,
        TestAlphaVantageEconomicFetcher,
        TestEconomicEventsDatabase,
        TestEconomicCalendarMonitor,
        TestRiskManagerIntegration,
        TestEndToEndIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   ✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"   ❌ Failed: {len(result.failures)}")
    print(f"   💥 Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Overall result
    success = len(result.failures) == 0 and len(result.errors) == 0
    status = "✅ ALL TESTS PASSED" if success else "❌ SOME TESTS FAILED"
    print(f"\n🏆 {status}")
    
    return success

if __name__ == "__main__":
    success = run_economic_calendar_tests()
    sys.exit(0 if success else 1)