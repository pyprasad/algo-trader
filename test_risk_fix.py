#!/usr/bin/env python3
"""Test if the emergency risk manager position size validation is fixed"""

import sys
sys.path.append('.')

from core.emergency_risk_manager import EmergencyRiskManager

def test_position_validation():
    """Test position size validation for Spread Betting"""
    
    risk_manager = EmergencyRiskManager()
    
    print("\n🧪 Testing Emergency Risk Manager for Spread Betting")
    print("=" * 60)
    
    # Test scenarios for Spread Betting (£ per point)
    test_cases = [
        # (market, direction, size_per_point, price, stop_loss)
        ("FTSE 100", "BUY", 2, 8500, 8490),   # £2/point, 10 point stop
        ("DAX", "SELL", 1, 18000, 18020),     # £1/point, 20 point stop
        ("FTSE 100", "BUY", 5, 8500, 8480),   # £5/point, 20 point stop
    ]
    
    for market, direction, size, price, stop_loss in test_cases:
        can_trade, reason = risk_manager.validate_trade(
            market=market,
            direction=direction,
            size=size,
            current_price=price,
            stop_loss=stop_loss
        )
        
        # For Spread Betting, position risk = size_per_point * stop_distance
        stop_distance = abs(price - stop_loss)
        max_risk = size * stop_distance
        print(f"\nTest: {market} {direction} £{size}/point @ {price}")
        print(f"  Stop distance: {stop_distance} points")
        print(f"  Max risk: £{max_risk:.2f}")
        print(f"  Result: {'✅ PASSED' if can_trade else '❌ FAILED'}")
        if not can_trade:
            print(f"  Reason: {reason}")
    
    print("\n" + "=" * 60)
    print("Risk Manager Configuration:")
    print(f"  Max position size: {risk_manager.MAX_POSITION_SIZE:.1%}")
    print(f"  Max loss per trade: {risk_manager.MAX_LOSS_PER_TRADE:.1%}")
    print(f"  Daily loss limit: {risk_manager.DAILY_LOSS_LIMIT:.1%}")
    print(f"  Max total exposure: {risk_manager.MAX_TOTAL_EXPOSURE:.1%}")

if __name__ == "__main__":
    test_position_validation()