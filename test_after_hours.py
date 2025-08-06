#!/usr/bin/env python3

"""
Test After-Hours Trading System

Tests:
- Market session detection
- Margin calculations
- Position sizing adjustments
- After-hours trade execution

Author: Algo Trading System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from utils.after_hours_manager import AfterHoursManager
from core.margin_calculator import MarginCalculator
from datetime import datetime
import time

def test_market_sessions():
    """Test market session detection"""
    print("=" * 60)
    print("📊 TESTING MARKET SESSION DETECTION")
    print("=" * 60)
    
    manager = AfterHoursManager()
    markets = ["FTSE 100", "S&P 500", "NASDAQ 100", "DAX"]
    
    for market in markets:
        print(f"\n🔍 Testing {market}:")
        
        # Detect current session
        session = manager.detect_trading_session(market)
        print(f"   Current session: {session}")
        
        # Get session parameters
        params = manager.get_session_parameters(market)
        print(f"   Is tradeable: {params['is_tradeable']}")
        print(f"   Margin multiplier: {params['margin_multiplier']}x")
        print(f"   Spread multiplier: {params['spread_multiplier']}x")
        
        # Get trading recommendation
        recommendation = manager.get_trading_recommendation(market)
        print(f"   Can trade: {recommendation['can_trade']}")
        print(f"   Position adjustment: {recommendation['position_size_adjustment']}x")
        
        if recommendation['recommendations']:
            print("   Recommendations:")
            for rec in recommendation['recommendations']:
                print(f"      • {rec}")

def test_margin_calculations():
    """Test margin calculator"""
    print("\n" + "=" * 60)
    print("💰 TESTING MARGIN CALCULATIONS")
    print("=" * 60)
    
    calculator = MarginCalculator()
    
    # Test margin status
    print("\n📊 Current Margin Status:")
    status = calculator.get_current_margin_status()
    print(f"   Margin used: £{status['margin_used']:.2f}")
    print(f"   Available to deal: £{status['available_to_deal']:.2f}")
    print(f"   Utilization: {status['utilization_percent']:.1f}%")
    print(f"   Status: {status['status']}")
    print(f"   Can open new: {status['can_open_new']}")
    
    # Test position sizing for different markets
    test_balance = 10000  # £10,000 test balance
    markets = ["FTSE 100", "S&P 500"]
    
    for market in markets:
        print(f"\n📈 Position Sizing for {market}:")
        sizing = calculator.calculate_safe_position_size(market, test_balance)
        print(f"   Session: {sizing['session']}")
        print(f"   Is after-hours: {sizing['is_after_hours']}")
        print(f"   Default size: {sizing['default_trade_size']}")
        print(f"   Position multiplier: {sizing['position_multiplier']}x")
        print(f"   Recommended size: {sizing['recommended_size']:.2f}")
        print(f"   Can trade: {sizing['can_trade']}")
        
        # Test margin validation
        if sizing['recommended_size'] > 0:
            can_trade, validation = calculator.validate_trade_margin(
                market, sizing['recommended_size']
            )
            print(f"   Margin validation: {'✅ PASS' if can_trade else '❌ FAIL'}")
            if not can_trade and validation['reasons']:
                print("   Rejection reasons:")
                for reason in validation['reasons']:
                    print(f"      • {reason}")

def test_stop_limit_adjustments():
    """Test stop-loss and take-profit adjustments"""
    print("\n" + "=" * 60)
    print("📐 TESTING STOP/LIMIT ADJUSTMENTS")
    print("=" * 60)
    
    manager = AfterHoursManager()
    sessions = ["regular", "pre_market", "after_hours", "weekend"]
    
    base_stop = 10
    base_limit = 20
    
    print(f"\nBase values: SL={base_stop}, TP={base_limit}")
    print("\nAdjustments by session:")
    
    for session in sessions:
        adj_stop, adj_limit = manager.calculate_adjusted_stops(
            base_stop, base_limit, session
        )
        print(f"   {session:12} -> SL={adj_stop:.1f}, TP={adj_limit:.1f}")

def test_api_market_status():
    """Test real API market status check"""
    print("\n" + "=" * 60)
    print("🌐 TESTING API MARKET STATUS")
    print("=" * 60)
    
    manager = AfterHoursManager()
    
    # Test with known EPICs
    test_epics = {
        "FTSE 100": "IX.D.FTSE.DAILY.IP",
        "S&P 500": "IX.D.SPTRD.DAILY.IP"
    }
    
    for market, epic in test_epics.items():
        print(f"\n📊 {market} ({epic}):")
        
        try:
            # Get API status
            api_status = manager.get_market_status_from_api(epic)
            
            if "error" not in api_status:
                print(f"   Market status: {api_status.get('marketStatus', 'UNKNOWN')}")
                print(f"   Min distance: {api_status.get('minDistance', 'N/A')}")
                print(f"   Margin requirement: {api_status.get('marginRequirement', 'N/A')}")
                print(f"   Streaming available: {api_status.get('streamingPricesAvailable', False)}")
                
                if api_status.get('bid') and api_status.get('offer'):
                    spread = float(api_status['offer']) - float(api_status['bid'])
                    print(f"   Current spread: {spread:.2f}")
            else:
                print(f"   ⚠️ Error: {api_status['error']}")
                
        except Exception as e:
            print(f"   ❌ Failed to get status: {e}")

def test_high_risk_detection():
    """Test high-risk period detection"""
    print("\n" + "=" * 60)
    print("⚠️ TESTING HIGH-RISK PERIOD DETECTION")
    print("=" * 60)
    
    manager = AfterHoursManager()
    markets = ["FTSE 100", "S&P 500", "NASDAQ 100", "DAX"]
    
    for market in markets:
        is_high_risk = manager.is_high_risk_period(market)
        session = manager.detect_trading_session(market)
        print(f"   {market:12} | Session: {session:10} | High Risk: {'YES ⚠️' if is_high_risk else 'NO ✅'}")

def run_all_tests():
    """Run all after-hours trading tests"""
    print("\n" + "🧪 " * 20)
    print("AFTER-HOURS TRADING SYSTEM TEST SUITE")
    print("🧪 " * 20)
    print(f"\nTest Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run tests
    test_market_sessions()
    test_margin_calculations()
    test_stop_limit_adjustments()
    test_api_market_status()
    test_high_risk_detection()
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test after-hours trading system")
    parser.add_argument("--test", choices=[
        "sessions", "margin", "stops", "api", "risk", "all"
    ], default="all", help="Which test to run")
    
    args = parser.parse_args()
    
    if args.test == "sessions":
        test_market_sessions()
    elif args.test == "margin":
        test_margin_calculations()
    elif args.test == "stops":
        test_stop_limit_adjustments()
    elif args.test == "api":
        test_api_market_status()
    elif args.test == "risk":
        test_high_risk_detection()
    else:
        run_all_tests()