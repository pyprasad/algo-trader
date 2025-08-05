#!/usr/bin/env python3
"""
Debug strategy to understand why no trades are generated
"""

import pandas as pd
import numpy as np
from datetime import datetime

class SimpleTechnicalIndicators:
    """Simplified technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [max(0, change) for change in changes]
        losses = [max(0, -change) for change in changes]
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_ema(prices, period=20):
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema

def debug_analysis():
    """Debug the strategy analysis"""
    
    # Load sample data
    ftse_data = pd.read_csv('ticks_ftse_100.csv')
    ftse_data['timestamp'] = pd.to_datetime(ftse_data['timestamp'])
    ftse_data = ftse_data.sort_values('timestamp')
    
    indicators = SimpleTechnicalIndicators()
    
    print("=== DEBUGGING STRATEGY ANALYSIS ===")
    print(f"Total FTSE ticks: {len(ftse_data)}")
    
    # Test different window sizes
    for lookback in [50, 100, 200]:
        prices = ftse_data['bid'].head(lookback).tolist()
        
        if len(prices) < 20:
            continue
            
        rsi = indicators.calculate_rsi(prices, period=14)
        ema_20 = indicators.calculate_ema(prices, period=20)
        current_price = prices[-1]
        
        print(f"\nLookback {lookback} ticks:")
        print(f"  Current Price: £{current_price:.2f}")
        print(f"  RSI: {rsi:.2f}")
        print(f"  EMA(20): £{ema_20:.2f}")
        print(f"  Trend Up: {current_price > ema_20}")
        
        # Check signal conditions
        if rsi < 30:
            print(f"  RSI < 30: OVERSOLD condition met")
        elif rsi > 70:
            print(f"  RSI > 70: OVERBOUGHT condition met")
        else:
            print(f"  RSI neutral (30-70 range)")
    
    # Test with different markets and parameters
    print(f"\n=== TESTING RELAXED PARAMETERS ===")
    
    # More relaxed parameters
    relaxed_params = {
        'rsi_oversold': 40,  # More lenient
        'rsi_overbought': 60,  # More lenient
        'min_confidence': 0.3  # Lower confidence threshold
    }
    
    prices = ftse_data['bid'].head(100).tolist()
    rsi = indicators.calculate_rsi(prices, period=14)
    ema_20 = indicators.calculate_ema(prices, period=20)
    current_price = prices[-1]
    
    trend_up = current_price > ema_20
    
    print(f"Current Price: £{current_price:.2f}")
    print(f"RSI: {rsi:.2f}")
    print(f"EMA(20): £{ema_20:.2f}")
    print(f"Trend Up: {trend_up}")
    
    # Test signals with relaxed parameters
    signal = 'HOLD'
    confidence = 0.0
    
    if rsi < relaxed_params['rsi_oversold'] and trend_up:
        signal = 'BUY'
        confidence = (relaxed_params['rsi_oversold'] - rsi) / relaxed_params['rsi_oversold']
        print(f"BUY signal generated! Confidence: {confidence:.2f}")
    elif rsi > relaxed_params['rsi_overbought'] and not trend_up:
        signal = 'SELL'
        confidence = (rsi - relaxed_params['rsi_overbought']) / (100 - relaxed_params['rsi_overbought'])
        print(f"SELL signal generated! Confidence: {confidence:.2f}")
    else:
        print("No signal with relaxed parameters")
    
    # Check confidence threshold
    if confidence >= relaxed_params['min_confidence']:
        print(f"✅ Signal passes confidence threshold: {signal}")
    else:
        print(f"❌ Signal fails confidence threshold ({confidence:.2f} < {relaxed_params['min_confidence']})")
    
    # Test across different time periods
    print(f"\n=== RSI ACROSS DIFFERENT PERIODS ===")
    sample_indices = [100, 500, 1000, 2000, 5000, 10000]
    
    for idx in sample_indices:
        if idx > len(ftse_data):
            continue
            
        prices = ftse_data['bid'].head(idx).tolist()
        rsi = indicators.calculate_rsi(prices, period=14)
        print(f"Index {idx}: RSI = {rsi:.2f}")

if __name__ == "__main__":
    debug_analysis()