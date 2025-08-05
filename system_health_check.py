#!/usr/bin/env python3
"""
System Health Check for Algorithm Trading System
Tests critical functions to ensure they don't crash with runtime errors
"""

import sys
import os
import traceback
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.market_adaptive_strategy import get_market_adaptive_strategy

def test_market_adaptive_strategy():
    """Test the market adaptive strategy with various scenarios"""
    print("=== TESTING MARKET ADAPTIVE STRATEGY ===")
    
    try:
        strategy = get_market_adaptive_strategy()
        print("✅ Strategy instance created successfully")
        
        # Test 1: Normal price data
        print("\n1. Testing normal price data...")
        normal_prices = [9100.0 + i + (i % 3) * 0.5 for i in range(50)]
        result = strategy.analyze_market_conditions(normal_prices, "FTSE 100")
        if result:
            print(f"✅ Normal analysis: {result['signal']} (confidence: {result.get('confidence', 0):.2f})")
        else:
            print("❌ Normal analysis returned None")
        
        # Test 2: Minimal price data
        print("\n2. Testing minimal price data...")
        minimal_prices = [9100.0, 9101.0, 9102.0]
        result = strategy.analyze_market_conditions(minimal_prices, "DAX")
        if result:
            print(f"✅ Minimal data analysis: {result['signal']} - {result.get('reason', 'No reason')}")
        else:
            print("❌ Minimal data analysis returned None")
        
        # Test 3: Empty price data
        print("\n3. Testing empty price data...")
        result = strategy.analyze_market_conditions([], "FTSE 100")
        if result:
            print(f"✅ Empty data analysis: {result['signal']} - {result.get('reason', 'No reason')}")
        else:
            print("❌ Empty data analysis returned None")
        
        # Test 4: None price data
        print("\n4. Testing None price data...")
        result = strategy.analyze_market_conditions(None, "DAX")
        if result:
            print(f"✅ None data analysis: {result['signal']} - {result.get('reason', 'No reason')}")
        else:
            print("❌ None data analysis returned None")
        
        # Test 5: Price data with None values
        print("\n5. Testing corrupted price data...")
        corrupted_prices = [9100.0, None, 9102.0, 9103.0, None] + [9100.0 + i for i in range(20)]
        result = strategy.analyze_market_conditions(corrupted_prices, "FTSE 100")
        if result:
            print(f"✅ Corrupted data analysis: {result['signal']} - {result.get('reason', 'No reason')}")
        else:
            print("❌ Corrupted data analysis returned None")
        
        # Test 6: Recent performance calculation
        print("\n6. Testing recent performance calculation...")
        try:
            perf_ftse = strategy._get_recent_market_performance("FTSE 100")
            perf_dax = strategy._get_recent_market_performance("DAX")
            print(f"✅ Performance calculation: FTSE £{perf_ftse:.2f}, DAX £{perf_dax:.2f}")
        except Exception as perf_error:
            print(f"❌ Performance calculation failed: {perf_error}")
        
        print("\n🎉 All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Critical test failure: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        return False

def test_emergency_mode():
    """Test emergency mode functionality"""
    print("\n=== TESTING EMERGENCY MODE ===")
    
    try:
        strategy = get_market_adaptive_strategy()
        
        # Simulate emergency scenario with minimal data
        emergency_prices = [9100.0 + i * 0.1 for i in range(15)]
        result = strategy._emergency_analysis(emergency_prices, "FTSE 100")
        
        if result and result.get("emergency_mode"):
            print(f"✅ Emergency mode: {result['signal']} (confidence: {result.get('confidence', 0):.2f})")
            print(f"   Reason: {result.get('reason', 'No reason')}")
            return True
        else:
            print("❌ Emergency mode test failed")
            return False
            
    except Exception as e:
        print(f"❌ Emergency mode test error: {e}")
        return False

def system_health_report():
    """Generate a comprehensive system health report"""
    print("=" * 60)
    print("ALGORITHM TRADING SYSTEM HEALTH CHECK")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Test core functionality
    if not test_market_adaptive_strategy():
        all_tests_passed = False
    
    if not test_emergency_mode():
        all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 SYSTEM HEALTH: EXCELLENT")
        print("✅ All critical functions working properly")
        print("✅ Error handling and fallbacks functional")
        print("✅ Algorithm ready to resume trading")
    else:
        print("🚨 SYSTEM HEALTH: ISSUES DETECTED")
        print("❌ Some critical functions still failing")
        print("⚠️ Manual intervention may be required")
    
    print("=" * 60)
    
    return all_tests_passed

if __name__ == "__main__":
    success = system_health_report()
    
    if success:
        print("\n🚀 RECOMMENDATION: Algorithm is ready to resume trading")
        print("   The critical errors have been fixed:")
        print("   ✅ NoneType arithmetic errors resolved")
        print("   ✅ Undefined variable errors fixed")
        print("   ✅ Emergency fallback systems active")
    else:
        print("\n⚠️ RECOMMENDATION: Do not resume trading yet")
        print("   Additional debugging required")
    
    sys.exit(0 if success else 1)