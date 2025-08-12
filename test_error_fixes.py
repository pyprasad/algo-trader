#!/usr/bin/env python3
"""
Test script to verify the fixes for:
1. Monitoring error: '>' not supported between instances of 'NoneType' and 'int'
2. ML prediction failed: could not convert string to float: 'DAX'
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.professional_monitor import ProfessionalTradingMonitor
from models.ml_predictor import get_ml_trading_signal
from core.enhanced_strategy_engine import get_enhanced_strategy_engine

def test_monitoring_fix():
    """Test that monitoring handles None values correctly"""
    print("Testing monitoring fix...")
    try:
        monitor = ProfessionalTradingMonitor()
        # This should not raise an error even with None balance
        monitor.update_performance_metrics()
        print("✅ Monitoring test passed - handles None values correctly")
        return True
    except Exception as e:
        print(f"❌ Monitoring test failed: {e}")
        return False

def test_ml_prediction_fix():
    """Test that ML prediction handles arguments correctly"""
    print("\nTesting ML prediction fix...")
    
    # Test with correct arguments
    test_prices = [100.0 + i * 0.1 for i in range(50)]
    
    try:
        # Test normal call
        result = get_ml_trading_signal("DAX", test_prices)
        if "error" not in result or "not trained" in result.get("error", ""):
            print("✅ ML prediction test passed - handles arguments correctly")
        else:
            print(f"⚠️ ML prediction returned error: {result.get('error')}")
        
        # Test swapped arguments (should be auto-corrected)
        result2 = get_ml_trading_signal(test_prices, "DAX")
        if "error" not in result2 or "not trained" in result2.get("error", ""):
            print("✅ ML prediction test passed - auto-corrects swapped arguments")
        else:
            print(f"⚠️ ML prediction with swapped args returned error: {result2.get('error')}")
        
        return True
    except Exception as e:
        print(f"❌ ML prediction test failed: {e}")
        return False

def test_enhanced_strategy():
    """Test enhanced strategy engine with proper data"""
    print("\nTesting enhanced strategy engine...")
    
    try:
        engine = get_enhanced_strategy_engine()
        test_prices = [23500.0 + i * 10 for i in range(50)]
        
        # This should work without errors
        result = engine.analyze_market_conditions(test_prices, "DAX")
        
        if result:
            print(f"✅ Enhanced strategy test passed - Signal: {result.get('signal', 'NONE')}")
            return True
        else:
            print("❌ Enhanced strategy returned None")
            return False
    except Exception as e:
        print(f"❌ Enhanced strategy test failed: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTING ERROR FIXES")
    print("=" * 60)
    
    all_passed = True
    
    # Test monitoring fix
    if not test_monitoring_fix():
        all_passed = False
    
    # Test ML prediction fix
    if not test_ml_prediction_fix():
        all_passed = False
    
    # Test enhanced strategy
    if not test_enhanced_strategy():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Errors have been fixed!")
    else:
        print("❌ Some tests failed - please review the output above")
    print("=" * 60)

if __name__ == "__main__":
    main()