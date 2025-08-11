#!/usr/bin/env python3
"""
🧪 Trading Profiles Testing Suite

Comprehensive tests for the multi-profile trading system to ensure
all profiles work correctly and can be compared effectively.

Author: Multi-Profile Trading System
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
import json
import tempfile
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.profile_manager import TradingProfileManager
from reports.profile_analyzer import ProfileAnalyzer

class TestTradingProfiles(unittest.TestCase):
    """Test trading profile system"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.profile_manager = TradingProfileManager(profiles_dir=f"{self.temp_dir}/profiles")
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_profile_manager_initialization(self):
        """Test profile manager initialization"""
        self.assertIsNotNone(self.profile_manager)
        self.assertEqual(len(self.profile_manager.available_profiles), 3)
        self.assertIn('conservative', self.profile_manager.available_profiles)
        self.assertIn('aggressive', self.profile_manager.available_profiles)
        self.assertIn('scalping', self.profile_manager.available_profiles)
    
    def test_create_default_profiles(self):
        """Test creating default profiles"""
        self.profile_manager.create_default_profiles()
        
        for profile in self.profile_manager.available_profiles:
            profile_path = self.profile_manager.profiles_dir / f"{profile}.yaml"
            self.assertTrue(profile_path.exists())
    
    def test_load_conservative_profile(self):
        """Test loading conservative profile"""
        self.profile_manager.create_default_profiles()
        config = self.profile_manager.load_profile('conservative')
        
        # Check key conservative characteristics
        self.assertEqual(config['profile_info']['name'], 'conservative')
        self.assertLessEqual(config['emergency_risk']['max_position_size'], 0.01)
        self.assertLessEqual(config['emergency_risk']['daily_loss_limit'], 0.03)
        self.assertGreaterEqual(config['economic_calendar']['pause_before_minutes'], 120)
        self.assertGreaterEqual(config['professional_trading']['min_signal_confidence'], 0.8)
    
    def test_load_aggressive_profile(self):
        """Test loading aggressive profile"""  
        self.profile_manager.create_default_profiles()
        config = self.profile_manager.load_profile('aggressive')
        
        # Check key aggressive characteristics
        self.assertEqual(config['profile_info']['name'], 'aggressive')
        self.assertGreater(config['emergency_risk']['max_position_size'], 0.02)
        self.assertGreater(config['emergency_risk']['daily_loss_limit'], 0.05)
        self.assertLess(config['economic_calendar']['pause_before_minutes'], 60)
        self.assertTrue(config['economic_calendar'].get('trade_during_events', False))
        self.assertLess(config['professional_trading']['min_signal_confidence'], 0.7)
    
    def test_load_scalping_profile(self):
        """Test loading scalping profile"""
        self.profile_manager.create_default_profiles()
        config = self.profile_manager.load_profile('scalping')
        
        # Check key scalping characteristics  
        self.assertEqual(config['profile_info']['name'], 'scalping')
        self.assertGreater(config['emergency_risk']['max_position_size'], 0.03)
        self.assertGreater(config['emergency_risk']['daily_loss_limit'], 0.1)
        self.assertFalse(config['economic_calendar']['enabled'])
        self.assertGreater(config['professional_trading']['max_trades_per_hour'], 10)
        self.assertTrue(config['strategy_parameters'].get('scalping_mode', False))
    
    def test_profile_summaries(self):
        """Test profile summary generation"""
        self.profile_manager.create_default_profiles()
        
        for profile_name in self.profile_manager.available_profiles:
            summary = self.profile_manager.get_profile_summary(profile_name)
            
            self.assertEqual(summary['name'], profile_name)
            self.assertIn('description', summary)
            self.assertIn('risk_level', summary)
            self.assertIn('trading_frequency', summary)
            self.assertIn('event_strategy', summary)
    
    def test_profile_comparison(self):
        """Test profile comparison functionality"""
        self.profile_manager.create_default_profiles()
        comparison = self.profile_manager.compare_profiles()
        
        self.assertEqual(len(comparison), 3)
        
        # Verify risk progression
        conservative_risk = comparison['conservative']['risk_level'] 
        aggressive_risk = comparison['aggressive']['risk_level']
        scalping_risk = comparison['scalping']['risk_level']
        
        # Risk levels should progress from low to high
        risk_levels = ['VERY_LOW', 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
        conservative_idx = risk_levels.index(conservative_risk)
        aggressive_idx = risk_levels.index(aggressive_risk)
        scalping_idx = risk_levels.index(scalping_risk)
        
        self.assertLess(conservative_idx, aggressive_idx)
        self.assertLess(aggressive_idx, scalping_idx)
    
    def test_performance_tracking(self):
        """Test performance tracking functionality"""
        profile_name = 'test_profile'
        
        # Start tracking
        self.profile_manager.start_profile_performance_tracking(profile_name)
        self.assertIn(profile_name, self.profile_manager.performance_history)
        
        # Create mock trades data
        mock_trades = [
            {'profit_loss': 10.5, 'timestamp': datetime.now()},
            {'profit_loss': -5.2, 'timestamp': datetime.now()},
            {'profit_loss': 15.8, 'timestamp': datetime.now()},
            {'profit_loss': -3.1, 'timestamp': datetime.now()},
        ]
        
        # Stop tracking with trades data
        performance = self.profile_manager.stop_profile_performance_tracking(
            profile_name, mock_trades
        )
        
        self.assertIsNotNone(performance)
        self.assertEqual(performance.total_trades, 4)
        self.assertEqual(performance.winning_trades, 2)
        self.assertEqual(performance.losing_trades, 2)
        self.assertEqual(performance.win_rate, 50.0)
        self.assertAlmostEqual(performance.total_pnl, 18.0, places=1)

class TestProfileAnalyzer(unittest.TestCase):
    """Test profile analyzer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.reports_dir = f"{self.temp_dir}/reports"
        os.makedirs(self.reports_dir)
        
        # Create mock analyzer
        self.analyzer = ProfileAnalyzer()
        self.analyzer.reports_dir = self.reports_dir
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def create_mock_session_report(self, profile_name: str, pnl: float, trades: int, win_rate: float):
        """Create a mock session report for testing"""
        report = {
            'profile': profile_name,
            'session_info': {
                'start_time': (datetime.now() - timedelta(days=1)).isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': '1 day, 0:00:00',
                'mode': 'DEMO'
            },
            'performance': {
                'initial_balance': 10000.0,
                'final_balance': 10000.0 + pnl,
                'balance_change': pnl,
                'balance_change_percent': (pnl / 10000.0) * 100,
                'total_trades': trades,
                'winning_trades': int(trades * win_rate / 100),
                'losing_trades': trades - int(trades * win_rate / 100),
                'win_rate': win_rate,
                'total_pnl': pnl
            }
        }
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.reports_dir}/session_report_{profile_name}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        return filename
    
    def test_analyze_session_reports(self):
        """Test session reports analysis"""
        # Create mock reports
        self.create_mock_session_report('conservative', 150.0, 25, 75.0)
        self.create_mock_session_report('aggressive', 280.0, 80, 62.5)
        self.create_mock_session_report('scalping', 180.0, 200, 55.0)
        
        # Analyze reports
        analysis = self.analyzer.analyze_session_reports(days_back=7)
        
        self.assertIn('profiles', analysis)
        self.assertIn('conservative', analysis['profiles'])
        self.assertIn('aggressive', analysis['profiles'])
        self.assertIn('scalping', analysis['profiles'])
    
    def test_recommendation_generation(self):
        """Test recommendation generation"""
        # Create reports with clear winner
        self.create_mock_session_report('conservative', 50.0, 10, 70.0)
        self.create_mock_session_report('aggressive', 300.0, 50, 65.0)  # Clear winner
        self.create_mock_session_report('scalping', 100.0, 150, 52.0)
        
        analysis = self.analyzer.analyze_session_reports(days_back=7)
        
        # Generate weekly comparison with recommendation
        weekly_comp = self.analyzer.generate_weekly_comparison(0)
        recommendation = weekly_comp.get('recommendation', {})
        
        self.assertIn('recommended_profile', recommendation)
        self.assertIn('reason', recommendation)
        self.assertIn('confidence', recommendation)

class TestProfileIntegration(unittest.TestCase):
    """Test integration with existing trading system"""
    
    def test_profile_runner_initialization(self):
        """Test profile runner can be initialized"""
        try:
            from scripts.run_profile import ProfileTradingRunner
            
            runner = ProfileTradingRunner(
                profile_name='conservative',
                duration_str='1h',
                live_mode=False
            )
            
            self.assertEqual(runner.profile_name, 'conservative')
            self.assertEqual(runner.live_mode, False)
            self.assertIsNotNone(runner.duration)
            
        except ImportError as e:
            self.skipTest(f"Profile runner not available: {e}")
    
    def test_duration_parsing(self):
        """Test duration string parsing"""
        try:
            from scripts.run_profile import ProfileTradingRunner
            
            # Test various duration formats
            test_cases = [
                ('1d', timedelta(days=1)),
                ('7d', timedelta(days=7)),
                ('1w', timedelta(weeks=1)),
                ('24h', timedelta(hours=24)),
                ('120m', timedelta(minutes=120))
            ]
            
            for duration_str, expected in test_cases:
                runner = ProfileTradingRunner('conservative', duration_str, False)
                self.assertEqual(runner.duration, expected)
                
        except ImportError as e:
            self.skipTest(f"Profile runner not available: {e}")

def run_profile_tests():
    """Run all profile-related tests"""
    
    print("🧪 Running Trading Profiles Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestTradingProfiles,
        TestProfileAnalyzer,
        TestProfileIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
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

def quick_system_test():
    """Run a quick system integration test"""
    
    print("🚀 Quick System Integration Test")
    print("=" * 40)
    
    try:
        # Test 1: Profile Manager
        print("1. Testing Profile Manager...")
        manager = TradingProfileManager()
        manager.create_default_profiles()
        
        for profile in manager.available_profiles:
            summary = manager.get_profile_summary(profile)
            print(f"   ✅ {profile}: {summary['risk_level']} risk, {summary['trading_frequency']} frequency")
        
        # Test 2: Profile Analysis
        print("\n2. Testing Profile Analyzer...")
        analyzer = ProfileAnalyzer()
        comparison = analyzer.compare_profiles_side_by_side(days_back=1)
        print("   ✅ Profile comparison report generated")
        
        # Test 3: Profile Configuration Validation
        print("\n3. Validating Profile Configurations...")
        for profile_name in ['conservative', 'aggressive', 'scalping']:
            config = manager.load_profile(profile_name)
            
            # Basic validation
            assert 'profile_info' in config
            assert 'emergency_risk' in config
            assert 'professional_trading' in config
            
            print(f"   ✅ {profile_name} configuration valid")
        
        print("\n🎉 All system tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ System test failed: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test trading profiles system")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Run quick system test only")
    parser.add_argument("--unit", "-u", action="store_true", 
                       help="Run unit tests only")
    
    args = parser.parse_args()
    
    if args.quick:
        success = quick_system_test()
    elif args.unit:
        success = run_profile_tests()
    else:
        # Run both
        quick_success = quick_system_test()
        print("\n")
        unit_success = run_profile_tests()
        success = quick_success and unit_success
    
    sys.exit(0 if success else 1)