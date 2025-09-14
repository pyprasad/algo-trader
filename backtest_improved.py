#!/usr/bin/env python3.12
# backtest_improved.py - Fixed backtesting with correct position sizing

import sys
import os
sys.path.append('.')

from runners.optimal_trading_system import OptimalTradingSystem
import argparse

class FixedOptimalSystem(OptimalTradingSystem):
    """Fixed version with correct position sizing"""
    
    def calculate_position_size(self, market_name):
        """Fixed position size calculation - 0.5% instead of 2%"""
        risk_pct = 0.5  # FIXED: 0.5% instead of 2%
        position_value = self.balance * (risk_pct / 100)
        return position_value / self.balance

def main():
    parser = argparse.ArgumentParser(description='Improved Backtest System')
    parser.add_argument('files', nargs='+', help='Tick data files to backtest')
    parser.add_argument('--config', default='configs/optimal_config.yaml')
    
    args = parser.parse_args()
    
    print("🔧 IMPROVED BACKTESTING SYSTEM")
    print("="*50)
    print("✅ Position Size: 0.5% (FIXED)")
    print("✅ Strategy: MA Crossover + SuperTrend")
    print("✅ Timeframe: 10min")
    print("="*50)
    
    # Use fixed system
    system = FixedOptimalSystem(args.config)
    trades = system.run_backtest(args.files)
    
    return trades

if __name__ == "__main__":
    main()