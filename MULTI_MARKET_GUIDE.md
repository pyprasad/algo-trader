# 🚀 Multi-Market Trading System Guide

## Overview
Your algo-trader now supports unlimited markets simultaneously with proper database segregation, global balance management, and concurrent processing. Each market (APPLE, GOOGLE, FTSE, etc.) gets its own dedicated data storage while sharing unified trading logic.

## ✅ Key Features Implemented

### 1. **Asset-Based Database Storage**
- **Dynamic Collections**: Each market gets its own MongoDB collection
  - `ticks_aapl` for Apple
  - `ticks_googl` for Google  
  - `ticks_ftse_100` for FTSE 100
- **Auto-Creation**: Tables created automatically when new markets are added
- **Unified Processing**: All markets use same strategy logic with market-specific data

### 2. **Global Balance Management**
- **Pre-Trade Validation**: Every trade checks account balance before execution
- **Margin Calculation**: Dynamic margin requirements per market
- **Real-time Updates**: Balance updated after each trade
- **Risk Management**: Exposure tracking and utilization monitoring

### 3. **Multi-Market Architecture**
- **Concurrent Streaming**: Multiple markets streamed simultaneously
- **Market-Specific Strategies**: Each market has its own strategy engine instance
- **Thread-Safe Operations**: Safe concurrent processing across markets

## 📁 New/Updated Files

### Updated Files:
- `data/db.py` - Enhanced with multi-market collections and balance checking
- `core/trade_executor.py` - Added global balance validation and market-specific trading
- `core/strategy_engine.py` - Added StrategyEngine class for multi-market analysis

### New Files:
- `data/multi_market_collector.py` - Multi-market data collection system
- `runners/run_multi_market.py` - Complete multi-market trading system
- `utils/balance_manager.py` - Comprehensive balance management utility
- `test_multi_market.py` - Test suite for multi-market functionality
- `demo_multi_market.py` - Demo script showing multi-market capabilities

## 🚀 Usage

### Configuration-Driven Trading
The system now uses configuration files instead of hardcoded markets:

#### Start Multi-Market Trading
```bash
python3.13 runners/run_multi_market.py
```

#### Manage Active Markets (Interactive)
```bash
python3.13 manage_markets.py
```

#### View Market Configuration
```bash
python3.13 utils/market_config_loader.py --summary
```

#### Add/Remove Markets via CLI
```bash
# Add a market
python3.13 utils/market_config_loader.py --add-market 'TSLA'

# Remove a market
python3.13 utils/market_config_loader.py --remove-market 'DAX'

# List available markets
python3.13 utils/market_config_loader.py --list-available

# List active markets
python3.13 utils/market_config_loader.py --list-active
```

#### Balance Management
```bash
# Set initial balance
python3.13 utils/balance_manager.py --set-balance 10000

# View account summary
python3.13 utils/balance_manager.py --summary

# Add funds to account
python3.13 utils/balance_manager.py --add-funds 5000
```

#### Test System Components
```bash
# Test all components
python3.13 test_multi_market.py

# Test configuration system
python3.13 test_config_system.py

# Run configuration demo
python3.13 demo_config_system.py

# Run market data demo  
python3.13 demo_multi_market.py
```

## 📊 Database Structure

### Collections Created:
- `ticks_aapl` - Apple tick data
- `ticks_googl` - Google tick data  
- `ticks_ftse_100` - FTSE 100 tick data
- `trades` - All trades across markets
- `account_balance` - Current account balance

### Example Tick Document:
```json
{
  "_id": ObjectId("..."),
  "market": "AAPL",
  "bid": 150.25,
  "offer": 150.27,
  "timestamp": ISODate("2025-01-01T10:00:00.000Z")
}
```

### Example Trade Document:
```json
{
  "_id": ObjectId("..."),
  "market": "AAPL",
  "direction": "BUY",
  "size": 15,
  "entry_price": 150.26,
  "stop_loss": 10,
  "take_profit": 20,
  "margin_used": 225.39,
  "status": "OPEN",
  "timestamp": ISODate("2025-01-01T10:00:00.000Z")
}
```

## 🛡️ Global Rules Implemented

1. **Balance Check**: Every trade validates sufficient balance first
2. **Market-Specific Collections**: Each asset stores data in dedicated collections  
3. **Dynamic Configuration**: Uses asset config for market-specific parameters
4. **Risk Management**: Tracks margin utilization and exposure per market
5. **Concurrent Processing**: Multiple markets analyzed simultaneously
6. **Error Handling**: Graceful handling of missing data or market failures

## ⚙️ Configuration

### 🆕 Configuration-Driven System
The system now uses three configuration files:

#### 1. Market Assets (`configs/assets_comprehensive.yaml`)
Defines all available markets and their parameters:
```yaml
"AAPL":
  epic: "AAPL.NASDAQ"
  trade_size: 15
  min_stop_distance: 0.1
  currency: "USD"
  market_hours:
    open: "09:30"
    close: "16:00"
    timezone: "US/Eastern"
  sector: "Technology"
  volatility_factor: 1.2

"FTSE 100":
  epic: "IX.D.FTSE.DAILY.IP"
  trade_size: 1
  min_stop_distance: 1
  currency: "GBP"
  market_hours:
    open: "08:00"
    close: "16:30"
    timezone: "Europe/London"
  sector: "Index"
  volatility_factor: 1.0
```

#### 2. Trading Configuration (`configs/trading_config.yaml`)
Defines which markets to trade and system settings:
```yaml
# Markets to trade - must exist in assets_comprehensive.yaml
active_markets:
  - "FTSE 100"
  - "AAPL"
  - "TSLA"

# System settings
system:
  initial_balance: 10000.0
  max_concurrent_markets: 5
  analysis_interval_seconds: 60
  data_collection_timeout_seconds: 30

# Risk management
risk_management:
  max_margin_utilization_percent: 80
  max_exposure_per_market_percent: 20
  emergency_stop_loss_percent: 10
```

#### 3. Global Strategy Configuration (`configs/global.yaml`)
Strategy and connection settings:
```yaml
strategy:
  mode: "LIVE"
  rsi_period: 14
  rsi_buy_threshold: 80
  rsi_sell_threshold: 20
  stop_loss_pips: 10
  take_profit_pips: 20
  dynamic_atr_sltp: true
```

## 📈 Adding New Markets

### 🆕 Easy Market Management

#### Method 1: Interactive Management
```bash
python3.13 manage_markets.py
# Follow the interactive menu to add/remove markets
```

#### Method 2: Command Line
```bash
# Add Tesla to active trading
python3.13 utils/market_config_loader.py --add-market 'TSLA'

# Remove DAX from active trading
python3.13 utils/market_config_loader.py --remove-market 'DAX'
```

#### Method 3: Edit Configuration File
Edit `configs/trading_config.yaml`:
```yaml
active_markets:
  - "FTSE 100"
  - "AAPL"
  - "TSLA"  # <- Add here
```

### Adding Completely New Markets

1. **Add to assets config** (`configs/assets_comprehensive.yaml`):
```yaml
"NEW_MARKET":
  epic: "NEW.MARKET.EPIC"
  trade_size: 10
  min_stop_distance: 0.1
  currency: "USD"
  market_hours:
    open: "09:30"
    close: "16:00"
    timezone: "US/Eastern"
  sector: "Technology"
  volatility_factor: 1.2
```

2. **Add to active markets**:
```bash
python3.13 utils/market_config_loader.py --add-market 'NEW_MARKET'
```

3. **The system will automatically**:
   - Create `ticks_new_market` collection
   - Start streaming new market data
   - Apply strategy analysis
   - Include in balance calculations

## 🔧 System Architecture

```
Multi-Market Trading System
├── Data Collection (multi_market_collector.py)
│   ├── Lightstreamer connections per market
│   ├── Market-specific tick listeners
│   └── Dynamic market addition/removal
│
├── Database Layer (db.py)
│   ├── Asset-based collections (ticks_*)
│   ├── Unified trades collection
│   ├── Balance management
│   └── Risk calculations
│
├── Strategy Engine (strategy_engine.py)
│   ├── Market-specific analysis
│   ├── RSI, ATR, EMA indicators
│   ├── Trend detection
│   └── Signal generation
│
├── Trade Execution (trade_executor.py)
│   ├── Global balance validation
│   ├── Market-specific parameters
│   ├── Margin requirement calculation
│   └── Trade logging
│
└── Balance Management (balance_manager.py)
    ├── Account balance tracking
    ├── Margin utilization monitoring
    ├── P&L analysis
    └── Risk metrics
```

## 🎯 Example Multi-Market Scenario

When running with APPLE and GOOGLE:

1. **Data Collection**: 
   - Streams live data for both markets
   - Stores APPLE ticks in `ticks_aapl`
   - Stores GOOGLE ticks in `ticks_googl`

2. **Strategy Analysis**:
   - Runs parallel analysis threads
   - APPLE analysis uses only APPLE data
   - GOOGLE analysis uses only GOOGLE data

3. **Trade Execution**:
   - APPLE signal: BUY → Checks balance → Places APPLE trade
   - GOOGLE signal: SELL → Checks balance → Places GOOGLE trade
   - Both trades logged with market identification

4. **Balance Management**:
   - Global balance decreases by margin used for both trades
   - Risk tracked separately per market
   - P&L calculated across all markets

## 🚨 Important Notes

- **Balance Checking**: All trades require sufficient balance first
- **Market Independence**: Each market's data is completely isolated
- **Concurrent Safe**: Multiple markets can trade simultaneously  
- **Dynamic Scaling**: Add/remove markets without system restart
- **Risk Management**: Global exposure limits across all markets
- **Error Isolation**: One market failure doesn't affect others

## 📞 Support Commands

```bash
# View system status
python3.13 -c "from data.db import get_available_markets; print(get_available_markets())"

# Check balance
python3.13 utils/balance_manager.py --balance

# View recent trades  
python3.13 -c "from data.db import trades_collection; print(list(trades_collection.find().limit(5)))"

# List all collections
python3.13 -c "from data.db import db; print(db.list_collection_names())"
```

Your multi-market trading system is now ready to handle unlimited markets with proper segregation, balance management, and concurrent processing! 🎉