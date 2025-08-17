# 🚀 Algorithmic Trading System - Comprehensive Guide
# Updated: December 2024

**Professional Spread Betting Platform for IG Markets**

---

## 📋 Table of Contents

1. [**Executive Overview**](#-executive-overview)
2. [**System Architecture**](#-system-architecture)
3. [**Trading Strategies & Profiles**](#-trading-strategies--profiles)
4. [**Configuration Mastery**](#-configuration-mastery)
5. [**Core System Components**](#-core-system-components)
6. [**Operational Guide**](#-operational-guide)
7. [**Advanced Features**](#-advanced-features)
8. [**Performance Optimization**](#-performance-optimization)
9. [**Troubleshooting Guide**](#-troubleshooting-guide)
10. [**Recent Updates & Changes**](#-recent-updates--changes)

---

# 🎯 Executive Overview

## What This System Is

This is a **professional-grade algorithmic spread betting platform** designed for IG Markets. It evolved from a simple RSI-based bot into a comprehensive automated trading system optimized for spread betting on indices, forex, and commodities.

### Key Capabilities
- **Spread Betting Focus**: Optimized for £ per point trading (not CFDs)
- **Multi-Market Support**: FTSE 100, DAX (in GBP), S&P 500, and 12+ other markets
- **Simplified Strategy**: Streamlined RSI-based mean reversion approach
- **Real-time Risk Management**: Emergency circuit breakers with realistic limits
- **Professional Monitoring**: Comprehensive logging and performance tracking

### Current Configuration Status (December 2024)
- **Trading Mode**: Aggressive (2-minute analysis intervals)
- **Position Sizing**: Up to £10 per point (capped for safety)
- **Risk Limits**: 5% per trade, 10% daily loss limit
- **Active Features**: Professional trading engine, dynamic limits, emergency risk management
- **Disabled Features**: ML models, Smart Money concepts, Economic Calendar blocking (to reduce complexity)

---

# 🏗️ System Architecture

## Simplified Architecture (Current)

```
┌─────────────────────────────────────────────────────────────────┐
│                 SPREAD BETTING TRADING SYSTEM                   │
├─────────────────────────────────────────────────────────────────┤
│  📊 DATA LAYER                                                 │
│  ├── Real-time Market Data (IG Markets Spread Betting API)     │
│  ├── Lightstreamer WebSocket Connections                       │
│  └── MongoDB Historical Storage                                │
├─────────────────────────────────────────────────────────────────┤
│  🧠 STRATEGY LAYER (SIMPLIFIED)                               │
│  ├── RSI Mean Reversion (Primary Strategy)                    │
│  ├── Single Timeframe Analysis (5M)                           │
│  └── Basic Signal Validation                                  │
├─────────────────────────────────────────────────────────────────┤
│  ⚙️ EXECUTION LAYER                                            │
│  ├── Spread Betting Position Management (£/point)              │
│  ├── Risk Management (10% position limit)                      │
│  ├── Trade Execution with GBP currency                         │
│  └── Stop Loss/Take Profit Management                          │
├─────────────────────────────────────────────────────────────────┤
│  📈 MONITORING LAYER                                           │
│  ├── Real-time P&L Tracking                                   │
│  ├── Position Monitoring                                       │
│  └── Error Logging and Alerts                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# 📁 Configuration Files

## Primary Configuration Files

### 1. `configs/global.yaml`
Main system configuration with simplified settings:

```yaml
professional_trading:
  enabled: true
  system_mode: aggressive  # Changed from moderate
  
  # Disabled complex features
  smart_money:
    enabled: false  # Disabled to reduce complexity
  
  advanced_ml:
    enabled: false  # Disabled to reduce complexity
  
  emergency_risk:
    max_loss_per_trade: 0.05    # 5% (increased from 2%)
    daily_loss_limit: 0.10       # 10% (increased from 5%)
    max_position_size: 0.10      # 10% (increased from 1%)
    max_total_exposure: 0.20     # 20% (increased from 10%)

economic_calendar:
  enabled: false  # Disabled to allow more trading opportunities

sentiment_analysis:
  enabled: false  # Disabled to simplify system
```

### 2. `configs/market_specific_strategy.yaml`
Simplified market-specific parameters:

```yaml
market_strategies:
  "DAX":
    rsi_period: 14
    rsi_buy_threshold: 35        # Buy on oversold (changed from 75)
    rsi_sell_threshold: 65       # Sell on overbought (changed from 25)
    stop_loss_pips: 8            # Tighter stops (changed from 15)
    take_profit_pips: 12         # Achievable targets (changed from 30)
    min_confidence_threshold: 0.55  # Lower threshold (changed from 0.8)
    
    # Removed time and news restrictions
    trading_hours:
      avoid_hours: []            # Trade all hours
      preferred_hours: []        # No preference
    
  "FTSE 100":
    rsi_period: 14
    rsi_buy_threshold: 30        # Standard oversold (changed from 70)
    rsi_sell_threshold: 70       # Standard overbought (changed from 30)
    stop_loss_pips: 5            # Tighter stops (changed from 10)
    take_profit_pips: 10         # Achievable targets (changed from 20)
    min_confidence_threshold: 0.5   # Lower threshold (changed from 0.7)

# Simplified timeframe requirements
timeframe_analysis:
  "DAX":
    require_timeframes: ["5M"]   # Single timeframe (was 3)
    minimum_aligned_timeframes: 1
    
  "FTSE 100":
    require_timeframes: ["5M"]   # Single timeframe (was 2)
    minimum_aligned_timeframes: 1
```

### 3. `configs/assets_comprehensive.yaml`
Updated asset configuration for spread betting:

```yaml
"DAX":
  epic: "IX.D.DAX.DAILY.IP"
  trade_size: 1
  min_stop_distance: 2
  currency: "GBP"  # Changed from EUR to save overnight financing
  market_hours:
    open: "08:00"
    close: "16:30"
    timezone: "Europe/Berlin"
  sector: "Index"
  volatility_factor: 1.2

"FTSE 100":
  epic: "IX.D.FTSE.DAILY.IP"
  trade_size: 1
  min_stop_distance: 1
  currency: "GBP"  # Native currency
  market_hours:
    open: "08:00"
    close: "16:30"
    timezone: "Europe/London"
  sector: "Index"
  volatility_factor: 1.0
```

---

# 🎮 Trading Strategies

## Current Active Strategy: Simplified RSI Mean Reversion

### Strategy Logic
```python
# Buy Signal (Oversold)
if RSI < buy_threshold (30-35):
    signal = BUY
    
# Sell Signal (Overbought)  
if RSI > sell_threshold (65-70):
    signal = SELL
```

### Key Parameters
- **RSI Period**: 14 (standard)
- **Buy Thresholds**: FTSE 30, DAX 35
- **Sell Thresholds**: FTSE 70, DAX 65
- **Confidence Required**: 0.5-0.55 (lowered for more trades)
- **Timeframe**: 5-minute only (simplified from multi-timeframe)

---

# 💰 Position Sizing for Spread Betting

## How Spread Betting Sizing Works

In spread betting, positions are sized in **£ per point** movement:

```python
# Spread Betting Position Calculation
position_size = £_per_point  # e.g., £2 per point
stop_distance = 10 points     # e.g., 10 point stop loss
max_risk = position_size * stop_distance  # £20 risk

# Example for FTSE at 8500:
# - Trade size: £2 per point
# - Stop loss: 10 points (8490)
# - Maximum risk: £20
# - If FTSE moves to 8510 (+10 points): Profit = £20
```

## Position Size Limits
- **Maximum**: £10 per point (capped for safety)
- **Typical**: £1-5 per point for retail traders
- **Account Risk**: Max 10% of account per position
- **Per Trade Risk**: Max 5% of account

---

# 🚦 Risk Management

## Emergency Risk Parameters (Updated)

```yaml
# Current Settings (Relaxed for Trading)
MAX_LOSS_PER_TRADE: 5%       # Was 2%
DAILY_LOSS_LIMIT: 10%        # Was 5%
MAX_POSITION_SIZE: 10%        # Was 1%
MAX_TOTAL_EXPOSURE: 20%       # Was 10%
MAX_CONSECUTIVE_LOSSES: 5     # Unchanged
```

## Circuit Breakers
- **Daily Loss**: Stops trading if -10% reached
- **Consecutive Losses**: Pauses after 5 losses
- **Volatility**: Adjusts sizing in extreme volatility
- **Drawdown**: Emergency stop at -15%

---

# 🔧 Operational Guide

## Starting the System

### 1. Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows

# Verify dependencies
pip install -r requirements.txt
# Note: numpy<2.0.0 required for PyTorch compatibility
```

### 2. Configuration Check
```bash
# Test configuration
python test_config.py

# Test risk validation
python test_risk_fix.py
```

### 3. Run Trading System
```bash
# Multi-market trading
python3.12 runners/run_multi_market.py

# Single market (if needed)
python runners/run_ftse100_scalping.py
```

## Monitoring Active Trades

### Key Files to Monitor
- `ig_streaming.log` - Real-time trading activity
- `session_cache.json` - Current session state
- MongoDB collections - Historical trades

### Important Metrics
- Current P&L
- Open positions
- Daily loss percentage
- Consecutive losses
- Signal confidence levels

---

# 🔍 Troubleshooting Guide

## Common Issues and Solutions

### 1. "Position size exceeds limit" Error
**Problem**: Emergency risk manager blocking trades
**Solution**: Already fixed by updating position size limits to 10% and correcting spread betting calculations

### 2. NumPy Version Conflict
**Problem**: "Module compiled with NumPy 1.x cannot run in NumPy 2.x"
**Solution**: 
```bash
pip install "numpy<2.0.0" --force-reinstall
```

### 3. No Trades Executing
**Possible Causes**:
- RSI not reaching thresholds
- Confidence too low
- Risk limits hit

**Solutions**:
- Check current RSI values
- Verify market is open
- Review daily P&L status
- Check logs for validation failures

### 4. ML Model Training Errors
**Error**: "int object is not subscriptable"
**Solution**: ML is disabled in current config, error is non-critical

### 5. DAX Currency Issues
**Problem**: Overnight financing charges with EUR
**Solution**: Already fixed - DAX now trades in GBP

### 6. "CRITICAL: All trades must have stop loss defined"
**Problem**: Emergency risk manager blocking all trades
**Solution**: Already fixed - trade_executor.py now calculates stop_loss when missing from strategy signals
**Config files updated**: Added stop_loss values to assets_comprehensive.yaml

### 7. Monitoring NoneType Comparison Error
**Problem**: "Monitoring error: '>' not supported between instances of 'NoneType' and 'int'"
**Solution**: Already fixed - professional_monitor.py now checks for None values before comparisons
**Result**: Performance monitoring works correctly

---

# 📊 Performance Optimization Tips

## Current Optimizations Applied

1. **Simplified Logic**
   - Single timeframe analysis (5M)
   - Disabled ML and Smart Money concepts
   - Removed news/economic calendar blocks

2. **Relaxed Constraints**
   - Lower confidence thresholds (0.5-0.55)
   - Wider position limits (10%)
   - No trading hour restrictions

3. **Faster Execution**
   - Aggressive mode (2-minute intervals)
   - Streamlined validation
   - Direct spread betting sizing

## Further Optimization Options

```yaml
# If still not trading enough, consider:
- Reduce RSI thresholds further (25/75)
- Increase position limits to 15%
- Reduce stop loss to 3-5 pips
- Increase analysis frequency to 1 minute
```

---

# 📝 Recent Updates (December 2024)

## Major Changes Implemented

1. **Spread Betting Focus**
   - Updated all references from CFD to Spread Betting
   - Corrected position sizing for £/point
   - Fixed validation logic

2. **Configuration Simplification**
   - Disabled ML models
   - Disabled Smart Money concepts
   - Removed economic calendar blocking
   - Removed trading hour restrictions

3. **Risk Parameter Adjustments**
   - Position size limit: 1% → 10%
   - Daily loss limit: 5% → 10%
   - Stop loss: Reduced to 5-8 pips
   - Take profit: Reduced to 10-12 pips

4. **Currency Optimization**
   - DAX: EUR → GBP (saves overnight charges)
   - All positions now in GBP

5. **RSI Strategy Update**
   - Reversed to standard mean reversion
   - Buy on oversold (RSI < 30-35)
   - Sell on overbought (RSI > 65-70)

6. **Critical Error Fixes** (Latest Updates)
   - Fixed stop loss validation error preventing trades
   - Fixed monitoring NoneType comparison errors
   - Added proper None value handling throughout system
   - Enhanced error handling and fallback mechanisms

---

# 🎯 Quick Reference

## Essential Commands
```bash
# Test system
python test_config.py
python test_risk_fix.py

# Run trading
python3.12 runners/run_multi_market.py

# Check logs
tail -f ig_streaming.log

# Monitor database
python -c "from data.db import trades_collection; print(list(trades_collection.find().limit(5)))"
```

## Key Configuration Locations
- Main config: `configs/global.yaml`
- Market strategies: `configs/market_specific_strategy.yaml`
- Asset definitions: `configs/assets_comprehensive.yaml`
- Active markets: `configs/trading_config.yaml`

## System Status Checklist
- [ ] NumPy < 2.0 installed
- [ ] IG API credentials valid
- [ ] MongoDB running
- [ ] Account balance > £1000
- [ ] Risk parameters configured
- [ ] Markets selected in trading_config.yaml

---

# 📚 Additional Resources

## Project Structure
```
algo-trader/
├── configs/               # All configuration files
├── core/                 # Core trading logic
├── models/               # ML models (currently disabled)
├── data/                 # Database connections
├── runners/              # Execution scripts
├── utils/                # Helper functions
└── tests/                # Test files
```

## Support & Maintenance
- Regular config reviews recommended
- Monitor performance weekly
- Adjust parameters based on results
- Keep logs for analysis

## Recent Fixes (Latest)
- ✅ Stop loss validation error resolved
- ✅ Monitoring NoneType comparison error fixed
- ✅ System ready for live trading without critical blocks
- ✅ All major configuration issues addressed

---

**Last Updated**: December 2024
**Version**: 2.0 (Simplified Spread Betting Edition)
**Status**: Production Ready