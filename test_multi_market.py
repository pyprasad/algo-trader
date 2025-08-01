#!/usr/bin/env python3
# test_multi_market.py - Test script for multi-market functionality

import sys
import os
sys.path.append(os.path.abspath('.'))

def test_imports():
    """Test all imports work correctly"""
    print("🧪 Testing imports...")
    
    try:
        from data.db import log_tick, ensure_tick_collection_exists, get_account_balance
        print("✅ Database imports successful")
    except ImportError as e:
        print(f"❌ Database import failed: {e}")
        return False
    
    try:
        from core.strategy_engine import StrategyEngine
        print("✅ Strategy engine import successful")
    except ImportError as e:
        print(f"❌ Strategy engine import failed: {e}")
        return False
    
    try:
        from data.multi_market_collector import MultiMarketCollector
        print("✅ Multi-market collector import successful")
    except ImportError as e:
        print(f"❌ Multi-market collector import failed: {e}")
        return False
    
    try:
        from utils.balance_manager import BalanceManager
        print("✅ Balance manager import successful")
    except ImportError as e:
        print(f"❌ Balance manager import failed: {e}")
        return False
    
    return True

def test_database_operations():
    """Test database operations"""
    print("\n🧪 Testing database operations...")
    
    try:
        from data.db import log_tick, ensure_tick_collection_exists, get_available_markets
        
        # Test collection creation
        collection_name = ensure_tick_collection_exists("TEST_MARKET")
        print(f"✅ Collection creation successful: {collection_name}")
        
        # Test tick logging
        log_tick("TEST_MARKET", 100.5, 100.7)
        print("✅ Tick logging successful")
        
        # Test available markets
        markets = get_available_markets()
        print(f"✅ Available markets: {markets}")
        
        return True
    except Exception as e:
        print(f"❌ Database operations failed: {e}")
        return False

def test_strategy_engine():
    """Test strategy engine"""
    print("\n🧪 Testing strategy engine...")
    
    try:
        from core.strategy_engine import StrategyEngine
        
        # Create strategy engine
        engine = StrategyEngine()
        print("✅ Strategy engine creation successful")
        
        # Test with sample prices
        prices = [100 + i * 0.1 for i in range(50)]  # Generate 50 sample prices
        signals = engine.analyze_market_conditions(prices, "TEST_MARKET")
        
        if signals:
            print(f"✅ Strategy analysis successful: {signals.get('signal', 'No signal')}")
        else:
            print("⚠️ No signals generated (might need more data)")
        
        return True
    except Exception as e:
        print(f"❌ Strategy engine test failed: {e}")
        return False

def test_balance_manager():
    """Test balance manager"""
    print("\n🧪 Testing balance manager...")
    
    try:
        from utils.balance_manager import BalanceManager
        
        # Create balance manager
        manager = BalanceManager()
        print("✅ Balance manager creation successful")
        
        # Set test balance
        manager.set_initial_balance(5000.0)
        print("✅ Balance setting successful")
        
        # Get current balance
        balance = manager.get_current_balance()
        print(f"✅ Current balance: £{balance}")
        
        return True
    except Exception as e:
        print(f"❌ Balance manager test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Multi-Market System Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Database Operations", test_database_operations),
        ("Strategy Engine", test_strategy_engine),
        ("Balance Manager", test_balance_manager)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Multi-market system is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)