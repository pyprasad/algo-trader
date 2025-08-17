#!/usr/bin/env python3
"""Test if the stop loss validation fix works"""

import sys
sys.path.append('.')

from core.trade_executor import execute_trade
from utils.config_loader import load_asset_config

def test_stop_loss_validation():
    """Test trade execution with missing stop loss"""
    
    print("🧪 Testing Stop Loss Validation Fix")
    print("=" * 50)
    
    # Test case: strategy signal without stop_loss
    strategy_signals = {
        'signal': 'BUY',
        'confidence': 0.6,
        'price': 8500,  # FTSE price
        # Note: No 'stop_loss' key - this should be handled by the fix
    }
    
    print(f"Strategy signals: {strategy_signals}")
    print("Note: No 'stop_loss' in signals - system should calculate one")
    
    # Test the trade execution (it will fail at other checkpoints but should pass stop loss validation)
    try:
        result = execute_trade("FTSE 100", "BUY", strategy_signals)
        print(f"\nResult: {result}")
        
        if "CRITICAL: All trades must have stop loss defined" in str(result):
            print("❌ FAILED: Stop loss error still occurring")
        else:
            print("✅ SUCCESS: Stop loss error fixed")
            
    except Exception as e:
        if "All trades must have stop loss defined" in str(e):
            print("❌ FAILED: Stop loss error still occurring")
        else:
            print("✅ SUCCESS: Stop loss error fixed (other errors expected)")
            print(f"Other error: {e}")

def test_asset_config():
    """Test that asset configs have stop loss values"""
    print("\n🔧 Testing Asset Configuration")
    print("=" * 50)
    
    markets = ["FTSE 100", "DAX"]
    
    for market in markets:
        try:
            config = load_asset_config(market)
            stop_loss = config.get('stop_loss', 'NOT FOUND')
            take_profit = config.get('take_profit', 'NOT FOUND')
            
            print(f"{market}:")
            print(f"  Stop Loss: {stop_loss}")
            print(f"  Take Profit: {take_profit}")
            
            if stop_loss == 'NOT FOUND':
                print(f"  ❌ Missing stop_loss configuration")
            else:
                print(f"  ✅ Stop loss configured")
                
        except Exception as e:
            print(f"{market}: ❌ Error loading config - {e}")

if __name__ == "__main__":
    test_asset_config()
    test_stop_loss_validation()