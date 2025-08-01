#!/usr/bin/env python3
"""
🧪 Test Dynamic Position Management System

Tests the sophisticated dynamic limit adjustment system that:
- Monitors real-time P&L via websocket
- Analyzes strategy confidence continuously  
- Adjusts take profit limits based on performance
- Protects against losses while capturing more upside

This demonstrates advanced algorithmic trading risk management.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.dynamic_position_manager import DynamicPositionManager, PositionAnalysis
from datetime import datetime
import yaml

def test_dynamic_position_management():
    """Test the dynamic position management system"""
    print("🧪 Testing Dynamic Position Management System")
    print("=" * 60)
    
    # Load current configuration
    with open("configs/global.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    dynamic_config = config.get("dynamic_limits", {})
    
    print("📋 Current Configuration:")
    print(f"   Enabled: {dynamic_config.get('enabled', False)}")
    print(f"   Update Interval: {dynamic_config.get('update_interval_seconds', 30)}s")
    print(f"   Confidence Threshold: {dynamic_config.get('confidence_threshold', 0.7)}")
    print(f"   Limit Range: {dynamic_config.get('min_limit_decrease', 0.5)}x - {dynamic_config.get('max_limit_increase', 2.0)}x")
    print(f"   P&L Threshold: {dynamic_config.get('pnl_threshold_percent', 5.0)}%")
    
    # Initialize the manager
    print(f"\n🚀 Initializing Dynamic Position Manager...")
    manager = DynamicPositionManager()
    
    # Test the limit multiplier calculation logic
    print(f"\n📊 Testing Limit Multiplier Calculation:")
    
    test_scenarios = [
        {
            "name": "High Confidence + Outperforming",
            "current_pnl": 25.0,
            "expected_pnl": 20.0,
            "confidence": 0.9,
            "regime": "trending",
            "signal": "BUY",
            "direction": "BUY"
        },
        {
            "name": "Low Confidence + Underperforming", 
            "current_pnl": -10.0,
            "expected_pnl": 20.0,
            "confidence": 0.4,
            "regime": "volatile",
            "signal": "SELL",
            "direction": "BUY"
        },
        {
            "name": "Medium Confidence + Normal Performance",
            "current_pnl": 18.0,
            "expected_pnl": 20.0, 
            "confidence": 0.75,
            "regime": "mean-reverting",
            "signal": "HOLD",
            "direction": "SELL"
        },
        {
            "name": "High Confidence + Volatile Market",
            "current_pnl": 30.0,
            "expected_pnl": 20.0,
            "confidence": 0.85,
            "regime": "volatile", 
            "signal": "SELL",
            "direction": "SELL"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}️⃣ Scenario: {scenario['name']}")
        
        multiplier, reason = manager._calculate_limit_multiplier(
            scenario["current_pnl"],
            scenario["expected_pnl"], 
            scenario["confidence"],
            scenario["regime"],
            scenario["signal"],
            scenario["direction"]
        )
        
        print(f"   📈 Input:")
        print(f"      Current P&L: {scenario['current_pnl']:+.1f}")
        print(f"      Expected P&L: {scenario['expected_pnl']:+.1f}")
        print(f"      Confidence: {scenario['confidence']:.2f}")
        print(f"      Market Regime: {scenario['regime']}")
        print(f"      Signal vs Direction: {scenario['signal']} vs {scenario['direction']}")
        
        print(f"   🎯 Result:")
        print(f"      Recommended Multiplier: {multiplier:.2f}x")
        print(f"      Reasoning: {reason}")
        
        # Show impact on take profit
        original_tp = 20  # pips
        new_tp = original_tp * multiplier
        print(f"      Take Profit: {original_tp} → {new_tp:.1f} pips ({multiplier:.2f}x)")
    
    # Test status reporting
    print(f"\n📊 System Status:")
    status = manager.get_status()
    for key, value in status.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    # Demonstrate feature flag usage
    print(f"\n🔧 Feature Flag Control:")
    print(f"   To ENABLE dynamic position management:")
    print(f"   1. Edit configs/global.yaml")
    print(f"   2. Set dynamic_limits.enabled = true")
    print(f"   3. Restart the trading system")
    print(f"   4. System will automatically start adjusting limits")
    
    print(f"\n✅ Dynamic Position Management Test Complete!")
    
    # Show the benefits
    print("=" * 60)
    print("🎯 Key Benefits of Dynamic Position Management:")
    print("   • 📈 Capture More Profits: Extend limits when confidence is high")
    print("   • 🛡️ Reduce Risk: Cut limits when strategy underperforms")
    print("   • 🔄 Adapt to Markets: Adjust based on regime changes")
    print("   • 🤖 Fully Automated: No manual intervention required")
    print("   • 📊 Performance Tracking: Complete history of adjustments")
    
    print(f"\n💡 Advanced Trading Intelligence:")
    print("   This system combines technical analysis, machine learning")
    print("   predictions, sentiment analysis, and real-time P&L to make")
    print("   sophisticated position management decisions automatically.")

def demonstrate_usage_scenarios():
    """Show real-world usage scenarios"""
    print(f"\n" + "="*60)
    print("🌟 Real-World Usage Scenarios")
    print("="*60)
    
    scenarios = [
        {
            "title": "Strong Trending Market",
            "description": "DAX in strong uptrend, high ML confidence, positive sentiment",
            "example": "Original TP: 20 pips → Dynamic TP: 35 pips (1.75x)",
            "benefit": "Captures 75% more profit from trending moves"
        },
        {
            "title": "Volatile Conditions",
            "description": "Market whipsawing, low strategy confidence, mixed signals", 
            "example": "Original TP: 20 pips → Dynamic TP: 12 pips (0.6x)",
            "benefit": "Protects profits by taking them earlier in uncertainty"
        },
        {
            "title": "Strategy Underperforming",
            "description": "Recent trades not meeting expectations, regime change",
            "example": "Original TP: 20 pips → Dynamic TP: 10 pips (0.5x)",
            "benefit": "Adapts to reduced effectiveness, preserves capital"
        },
        {
            "title": "High Confidence Setup",
            "description": "All signals align: Technical + ML + Sentiment + Regime",
            "example": "Original TP: 20 pips → Dynamic TP: 40 pips (2.0x)",
            "benefit": "Maximizes profits from high-probability setups"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}️⃣ {scenario['title']}")
        print(f"   Conditions: {scenario['description']}")
        print(f"   Adjustment: {scenario['example']}")
        print(f"   Benefit: {scenario['benefit']}")

if __name__ == "__main__":
    test_dynamic_position_management()
    demonstrate_usage_scenarios()
    
    print(f"\n🚀 Dynamic Position Management is ready to enhance your")
    print(f"   algorithmic trading with intelligent risk management!")