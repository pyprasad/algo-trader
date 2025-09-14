# tests/test_margin_system.py

"""
🧪 Comprehensive Unit Tests for Margin System

Tests all components of the dynamic margin rate management system including
rate calculations, timezone handling, session detection, and API integration.

Author: Test Engineering Team
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timedelta, time
import pytz

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import components to test
from core.margin_rate_manager import MarginRateManager, MarketSession
from core.timezone_manager import EnhancedTimezoneManager, MarketStatus
from core.enhanced_session_detector import EnhancedSessionDetector, SessionType
from core.enhanced_margin_calculator import EnhancedMarginCalculator
from core.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from core.secure_config import SecureConfigManager

class TestMarginRateManager(unittest.TestCase):
    """Test MarginRateManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = MarginRateManager()
    
    def test_initialization(self):
        """Test proper initialization"""
        self.assertIsInstance(self.manager, MarginRateManager)
        self.assertTrue(self.manager.enabled)
        self.assertEqual(self.manager.daily_request_limit, 800)
        self.assertGreater(len(self.manager.market_hours_cache), 0)
    
    def test_instrument_classification(self):
        """Test instrument classification"""
        # Test indices
        self.assertEqual(
            self.manager._classify_instrument("IX.D.FTSE.DAILY.IP"),
            "indices"
        )
        
        # Test forex
        self.assertEqual(
            self.manager._classify_instrument("CS.D.EURUSD.MINI.IP"),
            "forex"
        )
        
        # Test commodities
        self.assertEqual(
            self.manager._classify_instrument("CC.D.LCO.UMA.IP"),
            "commodities"
        )
    
    def test_tiered_margin_calculation(self):
        """Test tiered margin structure"""
        base_rate = 0.01  # 1%
        
        # Tier 1: <= £5000
        tier1_rate = self.manager._apply_tiered_margin(base_rate, 5000)
        self.assertEqual(tier1_rate, base_rate)
        
        # Tier 2: <= £25000
        tier2_rate = self.manager._apply_tiered_margin(base_rate, 25000)
        self.assertEqual(tier2_rate, base_rate * 1.2)
        
        # Tier 3: <= £100000
        tier3_rate = self.manager._apply_tiered_margin(base_rate, 100000)
        self.assertEqual(tier3_rate, base_rate * 1.5)
        
        # Tier 4: > £100000
        tier4_rate = self.manager._apply_tiered_margin(base_rate, 150000)
        self.assertEqual(tier4_rate, base_rate * 2.0)
    
    def test_api_usage_tracking(self):
        """Test API usage tracking"""
        # Initially no requests
        self.assertTrue(self.manager.can_make_api_request())
        
        # Record some requests
        for _ in range(750):
            self.manager.record_api_request()
        
        # Should still be able to make requests
        self.assertTrue(self.manager.can_make_api_request())
        
        # Get usage status
        status = self.manager.get_api_usage_status()
        self.assertEqual(status['requests_used'], 750)
        self.assertEqual(status['requests_remaining'], 50)
    
    def test_cache_functionality(self):
        """Test margin rate caching"""
        instrument = "IX.D.FTSE.DAILY.IP"
        session = MarketSession.MARKET_HOURS
        rate = 0.01
        
        # Cache a rate
        self.manager._cache_margin_rate(instrument, session, rate)
        
        # Should be able to retrieve it
        cached_rate = self.manager._get_cached_margin_rate(instrument)
        self.assertIsNotNone(cached_rate)
        self.assertEqual(cached_rate.rate, rate)
        self.assertEqual(cached_rate.session, session)
    
    @patch('core.margin_rate_manager.datetime')
    def test_market_session_detection(self, mock_datetime):
        """Test market session detection with mocked time"""
        # Mock London market hours (8 AM)
        mock_time = datetime(2024, 1, 15, 8, 0)  # Monday 8 AM
        mock_datetime.utcnow.return_value = mock_time
        
        session = self.manager._get_current_market_session("IX.D.FTSE.DAILY.IP")
        self.assertEqual(session, MarketSession.MARKET_HOURS)
        
        # Mock overnight (11 PM)
        mock_time = datetime(2024, 1, 15, 23, 0)  # Monday 11 PM
        mock_datetime.utcnow.return_value = mock_time
        
        session = self.manager._get_current_market_session("IX.D.FTSE.DAILY.IP")
        self.assertEqual(session, MarketSession.OVERNIGHT)

class TestTimezoneManager(unittest.TestCase):
    """Test EnhancedTimezoneManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tz_manager = EnhancedTimezoneManager()
    
    def test_initialization(self):
        """Test proper initialization"""
        self.assertIsInstance(self.tz_manager, EnhancedTimezoneManager)
        self.assertGreater(len(self.tz_manager.market_schedules), 0)
        self.assertGreater(len(self.tz_manager.holidays), 0)
    
    def test_timezone_conversion(self):
        """Test timezone conversion"""
        # Test UTC to London
        utc_time = datetime(2024, 6, 15, 12, 0)  # Summer time
        london_time = self.tz_manager.convert_time(
            utc_time, "UTC", "Europe/London"
        )
        
        # Should be 1 PM in London (BST)
        self.assertEqual(london_time.hour, 13)
    
    def test_market_status_detection(self):
        """Test market status detection"""
        # Test with London market hours
        london_market_time = datetime(2024, 1, 15, 10, 0)  # Monday 10 AM London
        status = self.tz_manager.get_market_status("IX.D.FTSE.DAILY.IP", london_market_time)
        self.assertEqual(status, MarketStatus.OPEN)
        
        # Test weekend
        weekend_time = datetime(2024, 1, 13, 10, 0)  # Saturday
        status = self.tz_manager.get_market_status("IX.D.FTSE.DAILY.IP", weekend_time)
        self.assertEqual(status, MarketStatus.WEEKEND)
    
    def test_holiday_detection(self):
        """Test holiday detection"""
        # Test Christmas Day (known holiday)
        christmas = datetime(2024, 12, 25).date()
        is_holiday = self.tz_manager.is_market_holiday("IX.D.FTSE.DAILY.IP", christmas)
        self.assertTrue(is_holiday)
        
        # Test normal day
        normal_day = datetime(2024, 6, 15).date()
        is_holiday = self.tz_manager.is_market_holiday("IX.D.FTSE.DAILY.IP", normal_day)
        self.assertFalse(is_holiday)
    
    def test_dst_detection(self):
        """Test DST detection"""
        # Test summer time in London
        summer_time = datetime(2024, 6, 15, 12, 0)
        is_dst = self.tz_manager.is_dst_active("Europe/London", summer_time)
        self.assertTrue(is_dst)
        
        # Test winter time in London
        winter_time = datetime(2024, 1, 15, 12, 0)
        is_dst = self.tz_manager.is_dst_active("Europe/London", winter_time)
        self.assertFalse(is_dst)
    
    def test_next_market_open(self):
        """Test next market open calculation"""
        # Test from Friday evening
        friday_evening = datetime(2024, 1, 12, 20, 0)  # Friday 8 PM UTC
        next_open = self.tz_manager.get_next_market_open("IX.D.FTSE.DAILY.IP", friday_evening)
        
        self.assertIsNotNone(next_open)
        # Should be Monday morning
        self.assertEqual(next_open.weekday(), 0)  # Monday

class TestSessionDetector(unittest.TestCase):
    """Test EnhancedSessionDetector functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = EnhancedSessionDetector()
    
    def test_initialization(self):
        """Test proper initialization"""
        self.assertIsInstance(self.detector, EnhancedSessionDetector)
        self.assertGreater(len(self.detector.session_definitions), 0)
        self.assertGreater(len(self.detector.margin_rate_mappings), 0)
    
    def test_session_detection(self):
        """Test session detection"""
        # Mock continuous trading session
        with patch('core.enhanced_session_detector.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime(2024, 1, 15, 10, 0)  # Monday 10 AM
            
            session = self.detector.detect_current_session("IX.D.FTSE.DAILY.IP")
            self.assertEqual(session.session_type, SessionType.CONTINUOUS_TRADING)
    
    def test_margin_rate_mapping(self):
        """Test margin rate mapping by session"""
        # Test market hours rate
        market_rate = self.detector.get_margin_rate_for_session(
            SessionType.CONTINUOUS_TRADING, "IX.D.FTSE.DAILY.IP"
        )
        self.assertGreater(market_rate, 0)
        
        # Test overnight rate should be higher
        overnight_rate = self.detector.get_margin_rate_for_session(
            SessionType.OVERNIGHT, "IX.D.FTSE.DAILY.IP"
        )
        self.assertGreater(overnight_rate, market_rate)
    
    def test_overlapping_sessions(self):
        """Test overlapping session detection"""
        overlaps = self.detector.get_overlapping_sessions()
        self.assertIsInstance(overlaps, list)
        # Should have some overlapping markets during active hours
        
    def test_next_session_prediction(self):
        """Test next session change prediction"""
        next_change = self.detector.predict_next_session_change("IX.D.FTSE.DAILY.IP")
        
        if next_change:
            change_time, next_session, new_rate = next_change
            self.assertIsInstance(change_time, datetime)
            self.assertIsInstance(next_session, SessionType)
            self.assertGreater(new_rate, 0)

class TestMarginCalculator(unittest.TestCase):
    """Test EnhancedMarginCalculator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = EnhancedMarginCalculator()
    
    def test_initialization(self):
        """Test proper initialization"""
        self.assertIsInstance(self.calculator, EnhancedMarginCalculator)
        self.assertGreater(self.calculator.margin_buffer_percent, 0)
        self.assertGreater(self.calculator.max_margin_utilization, 0)
    
    def test_position_margin_calculation(self):
        """Test position margin calculation"""
        margin_req = self.calculator.calculate_position_margin(
            instrument="IX.D.FTSE.DAILY.IP",
            size=10,
            current_price=7500,
            direction="BUY"
        )
        
        self.assertGreater(margin_req.margin_required, 0)
        self.assertEqual(margin_req.position_value, 75000)  # 10 * 7500
        self.assertGreater(margin_req.margin_rate, 0)
    
    def test_account_margin_status(self):
        """Test account margin status calculation"""
        # Mock positions
        positions = [
            {
                'instrument': 'IX.D.FTSE.DAILY.IP',
                'size': 10,
                'current_price': 7500
            },
            {
                'instrument': 'IX.D.DAX.DAILY.IP', 
                'size': 5,
                'current_price': 15000
            }
        ]
        
        status = self.calculator.calculate_account_margin_status(
            positions, account_balance=100000
        )
        
        self.assertGreater(status.used_margin, 0)
        self.assertGreater(status.available_margin, 0)
        self.assertGreaterEqual(status.margin_utilization, 0)
        self.assertEqual(status.positions_count, 2)
        self.assertIn(status.status, ["healthy", "warning", "critical"])
    
    def test_position_size_calculation(self):
        """Test position size for risk calculation"""
        size_calc = self.calculator.calculate_position_size_for_risk(
            instrument="IX.D.FTSE.DAILY.IP",
            current_price=7500,
            risk_amount=100,
            stop_loss_pips=10,
            account_balance=10000
        )
        
        self.assertGreater(size_calc['recommended_size'], 0)
        self.assertIn(size_calc['size_limited_by'], ['risk', 'margin'])
        self.assertGreater(size_calc['margin_rate'], 0)
    
    def test_margin_breach_detection(self):
        """Test margin breach detection"""
        # Create high-margin positions
        high_margin_positions = [
            {
                'instrument': 'IX.D.FTSE.DAILY.IP',
                'size': 100,
                'current_price': 7500
            }
        ]
        
        breach_info = self.calculator.check_margin_breach(
            high_margin_positions, account_balance=10000
        )
        
        self.assertIn('has_breach', breach_info)
        self.assertIn('breach_type', breach_info)
        self.assertIn('margin_utilization', breach_info)

class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_initialization(self):
        """Test proper initialization"""
        self.assertIsInstance(self.error_handler, ErrorHandler)
        self.assertGreater(len(self.error_handler.circuit_breakers), 0)
        self.assertGreater(len(self.error_handler.retry_strategies), 0)
    
    def test_error_handling(self):
        """Test error handling"""
        test_error = Exception("Test error")
        
        context = self.error_handler.handle_error(
            test_error,
            ErrorCategory.CALCULATION_ERROR,
            ErrorSeverity.MEDIUM
        )
        
        self.assertEqual(context.category, ErrorCategory.CALCULATION_ERROR)
        self.assertEqual(context.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(context.exception, test_error)
        self.assertIn(context, self.error_handler.error_history)
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        cb = self.error_handler.circuit_breakers["calculation"]
        
        # Initially closed
        self.assertEqual(cb.state, "closed")
        
        # Trigger failures
        for _ in range(cb.failure_threshold + 1):
            try:
                cb.call(lambda: 1/0)  # Always fails
            except:
                pass
        
        # Should be open now
        self.assertEqual(cb.state, "open")
    
    def test_retry_strategy(self):
        """Test retry strategy"""
        retry_strategy = self.error_handler.retry_strategies["calculation"]
        
        attempt_count = 0
        
        def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = retry_strategy.execute_with_retry(failing_function)
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count, 3)

class TestSecureConfig(unittest.TestCase):
    """Test SecureConfigManager functionality"""
    
    @patch.dict(os.environ, {
        'IG_API_KEY': 'test_key',
        'IG_USERNAME': 'test_user', 
        'IG_PASSWORD': 'test_pass'
    })
    def test_secure_config_loading(self):
        """Test secure configuration loading"""
        try:
            config = SecureConfigManager()
            
            # Should load without error
            self.assertIsInstance(config, SecureConfigManager)
            
            # Should have credentials
            creds = config.get_ig_credentials()
            self.assertEqual(creds['api_key'], 'test_key')
            self.assertEqual(creds['username'], 'test_user')
            self.assertEqual(creds['password'], 'test_pass')
            
            # Test feature flags
            self.assertIsInstance(config.is_feature_enabled('margin_management'), bool)
            
        except ValueError as e:
            # Expected if other required env vars missing
            self.assertIn("validation failed", str(e))

class TestIntegration(unittest.TestCase):
    """Integration tests for margin system components"""
    
    def test_end_to_end_margin_calculation(self):
        """Test complete margin calculation flow"""
        # Initialize components
        manager = MarginRateManager()
        calculator = EnhancedMarginCalculator(manager)
        
        # Test complete flow
        instrument = "IX.D.FTSE.DAILY.IP"
        size = 10
        price = 7500
        
        # Get margin rate
        rate = manager.get_current_margin_rate(instrument, size * price)
        self.assertGreater(rate, 0)
        
        # Calculate position margin
        margin_req = calculator.calculate_position_margin(instrument, size, price)
        self.assertGreater(margin_req.margin_required, 0)
        
        # Calculate account status
        positions = [{'instrument': instrument, 'size': size, 'current_price': price}]
        status = calculator.calculate_account_margin_status(positions, 100000)
        
        self.assertEqual(status.positions_count, 1)
        self.assertGreater(status.used_margin, 0)

if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestMarginRateManager,
        TestTimezoneManager,
        TestSessionDetector,
        TestMarginCalculator,
        TestErrorHandler,
        TestSecureConfig,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print(f"TESTS RUN: {result.testsRun}")
    print(f"FAILURES: {len(result.failures)}")
    print(f"ERRORS: {len(result.errors)}")
    print(f"SUCCESS RATE: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)