#!/usr/bin/env python3
"""
🧪 Test Enhanced Trading System

Tests the complete enhanced trading system with machine learning,
sentiment analysis, and multi-timeframe analysis.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from core.enhanced_strategy_engine import get_enhanced_strategy_engine
import numpy as np

def test_enhanced_strategy_engine():
    """Test the enhanced strategy engine with sample data"""
    print("🧪 Testing Enhanced Trading System")
    print("=" * 50)
    
    # Get the enhanced strategy engine
    engine = get_enhanced_strategy_engine()
    
    # Generate realistic price data (simulating a market downturn)
    np.random.seed(42)
    base_price = 23500
    prices = [base_price]
    
    print("📊 Generating sample market data...")
    # Generate realistic price series (trending down with volatility)
    for i in range(100):
        # Add some realistic market behavior
        if i < 20:
            # Initial stability
            change = np.random.normal(0, 8)
        elif i < 60:
            # Downward trend (like the DAX drop we analyzed)
            change = np.random.normal(-3, 15)  # Downward bias with volatility
        else:
            # Recovery attempt
            change = np.random.normal(1, 12)
        
        new_price = prices[-1] + change
        prices.append(max(23000, min(24000, new_price)))  # Keep within bounds
    
    # Test with different markets
    test_markets = ["DAX", "FTSE100", "SPX500"]
    
    for market in test_markets:
        print(f"\n🎯 Testing Enhanced Analysis for {market}")
        print("-" * 40)
        
        try:
            # Run enhanced analysis
            result = engine.analyze_market_conditions(prices, market)
            
            if result:
                print(f"✅ Analysis completed successfully for {market}")
                print(f"   🎯 Final Signal: {result.get('signal', 'HOLD')}")
                print(f"   📊 Composite Score: {result.get('composite_score', 0):.3f}")
                print(f"   💪 Signal Strength: {result.get('signal_strength', 0):.2f}")
                print(f"   🤝 Confidence: {result.get('confidence', 0):.2f}")
                
                # Show technical indicators
                print(f"   📈 RSI: {result.get('rsi', 0):.1f}")
                print(f"   📊 Trend: {result.get('trend', 'N/A')}")
                print(f"   🌍 Regime: {result.get('regime', 'N/A')}")
                print(f"   💰 Current Price: £{result.get('price', 0):.2f}")
                
                # Show individual signals
                print(f"\n   🔍 Individual Signals:")
                print(f"      Technical: {result.get('technical_signal', 'HOLD')}")
                print(f"      Multi-Timeframe: {result.get('multi_timeframe_signal', 'HOLD')}")
                print(f"      ML Prediction: {result.get('ml_signal', 'HOLD')}")
                print(f"      News Sentiment: {result.get('sentiment_signal', 'HOLD')}")
                
            else:
                print(f"❌ Analysis failed for {market}")
                
        except Exception as e:
            print(f"❌ Error testing {market}: {e}")
    
    print(f"\n✅ Enhanced System Test Complete!")

if __name__ == "__main__":
    test_enhanced_strategy_engine()