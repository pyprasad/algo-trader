# 🎯 Trading Profiles System - Complete Guide

## Overview

The Multi-Profile Trading System allows you to run three distinct trading strategies for weekly A/B testing to determine which approach makes the most money in current market conditions.

**The Problem We Solved:** Too many trading pauses and restrictions were preventing profitable opportunities. This system lets you test different risk/reward approaches to find what actually works.

## 📊 Available Trading Profiles

### 🛡️ **Conservative Profile** - Capital Preservation
**"Fort Knox" Approach - Ultra-Safe**

```yaml
Target Audience: Risk-averse traders prioritizing capital protection
Expected Performance: 1-3 trades/day, 70-80% win rate
Risk Level: VERY LOW
Position Size: 0.5% of account
Daily Risk Limit: 2% maximum
```

**Features:**
- ✅ Maximum safety with multiple risk controls
- ✅ 3-hour pause windows around economic events  
- ✅ Very high signal confidence required (85%)
- ✅ Tight stop losses, wide take profits (2:1 R:R)
- ✅ Multiple timeframe confirmation required
- ✅ Respects all negative sentiment

**Best For:** New traders, small accounts, risk-averse investors

---

### ⚡ **Aggressive Profile** - Volatility Trading  
**"Trade the Storm" Approach - Event-Based**

```yaml
Target Audience: Experienced traders comfortable with volatility
Expected Performance: 5-15 trades/day, 55-65% win rate  
Risk Level: MEDIUM-HIGH
Position Size: 3% of account
Daily Risk Limit: 8% maximum
```

**Features:**
- 🔥 **TRADES INTO economic events** (15-minute pause windows)
- 🔥 Higher position sizes during volatile periods
- 🔥 Contrarian trading (fades crowd sentiment)
- 🔥 Lower confidence thresholds (55% vs 85%)
- 🔥 Momentum and breakout trading
- 🔥 News reaction trading enabled

**Best For:** Experienced traders who want to capitalize on volatility

---

### 🔥 **Scalping Profile** - High-Frequency
**"Rapid Fire" Approach - Volume Trading**

```yaml
Target Audience: Active traders comfortable with high-frequency trading
Expected Performance: 20-100 trades/day, 52-62% win rate
Risk Level: HIGH  
Position Size: 4% of account
Daily Risk Limit: 12% maximum
Trade Duration: 2-15 minutes average
```

**Features:**
- 💨 **NO economic event restrictions** - trades through everything
- 💨 Up to 20 trades per hour
- 💨 3-pip profit targets, 2-pip stop losses
- 💨 30-second minimum gap between trades
- 💨 Quick scalp signals (52% confidence threshold)
- 💨 Ignores sentiment analysis completely

**Best For:** Active day traders, high-risk tolerance, large accounts

## 🚀 How to Run Each Profile

### Quick Start Commands

```bash
# Test each profile for 1 day (paper trading)
python3 scripts/run_conservative.py --duration 1d --paper
python3 scripts/run_aggressive.py --duration 1d --paper  
python3 scripts/run_scalping.py --duration 1d --paper

# Run a profile for 1 week (demo account)
python3 scripts/run_conservative.py --duration 7d

# Run a profile live (REAL MONEY - be careful!)
python3 scripts/run_aggressive.py --duration 7d --live
```

### Advanced Usage

```bash
# Generic profile runner (most flexible)
python3 scripts/run_profile.py --profile conservative --duration 7d
python3 scripts/run_profile.py --profile aggressive --duration 24h --live
python3 scripts/run_profile.py --profile scalping --duration 1w --paper

# Duration formats
--duration 1d    # 1 day
--duration 7d    # 7 days  
--duration 1w    # 1 week
--duration 24h   # 24 hours
--duration 120m  # 120 minutes
```

## 📈 Weekly A/B Testing Protocol

### Week 1: Conservative Profile
```bash
# Run conservative profile for a full week
python3 scripts/run_conservative.py --duration 7d

# Monitor results
python3 reports/profile_analyzer.py --days 7
```

### Week 2: Aggressive Profile  
```bash
# Run aggressive profile for a full week
python3 scripts/run_aggressive.py --duration 7d

# Compare with previous week
python3 reports/profile_analyzer.py --days 14
```

### Week 3: Scalping Profile
```bash
# Run scalping profile for a full week  
python3 scripts/run_scalping.py --duration 7d

# Generate final comparison
python3 reports/profile_analyzer.py --days 21
```

### Week 4: Best Profile
```bash
# Get recommendation
python3 reports/profile_analyzer.py --week 1

# Run recommended profile
python3 scripts/run_[recommended].py --duration 7d --live
```

## 📊 Performance Analysis & Reporting

### View Profile Comparison
```bash
# Compare last 7 days of all profiles
python3 reports/profile_analyzer.py --days 7

# Compare specific week
python3 reports/profile_analyzer.py --week 1

# Save report to file
python3 reports/profile_analyzer.py --days 7 --save
```

### Sample Output
```
📊 TRADING PROFILE COMPARISON REPORT
==========================================
Analysis Period: Last 7 days
Total Reports: 21

Profile         Sessions   Trades   Win Rate   Total P&L    Profit Rate
----------------------------------------------------------------------
Conservative    3          42       74.2%      £145.67      100%
Aggressive      4          156      61.5%      £287.43      75%
Scalping        7          892      58.1%      £198.21      57%

💡 RECOMMENDATION: AGGRESSIVE
Confidence: HIGH
Reason: Aggressive profile: profitable (£287.43), 61.5% win rate, 75% session success
```

## 🔧 Configuration Management

### Profile Configurations Location
```
configs/profiles/
├── conservative.yaml    # Ultra-safe settings
├── aggressive.yaml      # Event trading settings  
└── scalping.yaml       # High-frequency settings
```

### Customizing Profiles
```yaml
# Edit any profile file
nano configs/profiles/aggressive.yaml

# Key settings to adjust:
emergency_risk:
  max_position_size: 0.03      # 3% positions (adjust up/down)
  daily_loss_limit: 0.08       # 8% daily limit (adjust up/down)

professional_trading:
  min_signal_confidence: 0.55  # Lower = more trades
  max_trades_per_hour: 5       # Higher = more frequent

economic_calendar:
  trade_during_events: true    # true = trade volatility
  pause_before_minutes: 15     # Lower = less restrictive
```

### Loading Custom Profiles
```python
# Python API for custom profiles
from utils.profile_manager import TradingProfileManager

manager = TradingProfileManager()
config = manager.load_profile('aggressive')
summary = manager.get_profile_summary('aggressive')
print(f"Risk Level: {summary['risk_level']}")
```

## 🛡️ Safety & Risk Management

### Built-in Protections (All Profiles)
- ✅ **Emergency Circuit Breakers** - Halt trading on major losses
- ✅ **Position Size Limits** - Maximum position sizes enforced
- ✅ **Daily Loss Limits** - Stop trading after daily limit hit
- ✅ **Consecutive Loss Protection** - Pause after losing streaks
- ✅ **Account Balance Monitoring** - Real-time balance tracking

### Profile-Specific Safety
- **Conservative**: Multiple confirmations, tight risk controls
- **Aggressive**: Volatility-aware risk management, event-based limits  
- **Scalping**: Rapid loss detection, frequency-based controls

### Override Controls
```bash
# Emergency stop any running profile
pkill -f "run_profile.py"
pkill -f "run_conservative.py"
pkill -f "run_aggressive.py" 
pkill -f "run_scalping.py"

# Check system status
python3 utils/trading_monitor.py
```

## 📁 Generated Files & Reports

### Session Reports
```
reports/
├── session_report_conservative_20240811_120000.json
├── session_report_aggressive_20240811_130000.json
├── session_report_scalping_20240811_140000.json
└── profile_comparison_20240811_150000.txt
```

### Report Contents
```json
{
  "profile": "aggressive",
  "session_info": {
    "start_time": "2024-08-11T12:00:00",
    "end_time": "2024-08-18T12:00:00", 
    "duration": "7 days, 0:00:00",
    "mode": "DEMO"
  },
  "performance": {
    "initial_balance": 10104.26,
    "final_balance": 10391.69,
    "balance_change": 287.43,
    "balance_change_percent": 2.84,
    "total_trades": 156,
    "winning_trades": 96,
    "losing_trades": 60,
    "win_rate": 61.5,
    "total_pnl": 287.43
  }
}
```

## 🔍 Troubleshooting

### Common Issues

#### "Profile not found"
```bash
# Recreate default profiles
python3 utils/profile_manager.py
```

#### "Trading system won't start"
```bash
# Check MongoDB connection
python3 -c "from pymongo import MongoClient; MongoClient('mongodb://127.0.0.1:27017').admin.command('ping'); print('✅ MongoDB OK')"

# Check account balance
python3 -c "from data.db import get_account_balance; print(f'Balance: £{get_account_balance():.2f}')"
```

#### "No trades being executed"
```bash
# Check profile settings
python3 -c "from utils.profile_manager import TradingProfileManager; m = TradingProfileManager(); print(m.get_profile_summary('aggressive'))"

# Check economic calendar status  
python3 -c "from core.emergency_risk_manager import get_emergency_risk_manager; r = get_emergency_risk_manager(); print(r.get_economic_calendar_status())"
```

### Debug Mode
```bash
# Run with debug logging
python3 scripts/run_profile.py --profile aggressive --duration 1h --paper 2>&1 | tee debug.log
```

## 💡 Tips for Optimal Results

### 1. **Start with Paper Trading**
Always test profiles with `--paper` flag first to understand their behavior.

### 2. **Run Full Weeks**
Give each profile a full 7-day test period for meaningful results.

### 3. **Monitor Market Conditions**
Different profiles perform better in different market conditions:
- **Conservative**: Best in uncertain/volatile markets
- **Aggressive**: Best during major economic events
- **Scalping**: Best in high-liquidity, trending markets

### 4. **Weekly Review Cycle**
```bash
# Every Sunday, review and switch
python3 reports/profile_analyzer.py --week 1
# Then run best profile for next week
```

### 5. **Position Sizing**
Adjust position sizes based on account size:
- Small accounts (<£5000): Use conservative profile
- Medium accounts (£5000-£20000): Test aggressive
- Large accounts (>£20000): Can handle scalping

## 🚀 Next Steps

1. **Week 1**: Run `python3 scripts/run_conservative.py --duration 7d --paper`
2. **Week 2**: Run `python3 scripts/run_aggressive.py --duration 7d --paper`  
3. **Week 3**: Run `python3 scripts/run_scalping.py --duration 7d --paper`
4. **Week 4**: Analyze with `python3 reports/profile_analyzer.py --days 21`
5. **Week 5**: Switch to live trading with best profile

## 📞 Support

- **View system status**: `python3 utils/trading_monitor.py`
- **Check profile configs**: `ls configs/profiles/`
- **View recent reports**: `ls reports/session_report_*.json`
- **Emergency stop**: `pkill -f run_profile`

---

**Remember:** The goal is to find which trading style actually makes money in current market conditions. Each profile represents a completely different philosophy - test them all to see what works best for you! 💰