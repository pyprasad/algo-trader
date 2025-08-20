# System Architecture

## Overview

The Algo-Trader system follows a modular, event-driven architecture designed for high performance, reliability, and scalability. The system processes real-time market data, generates trading signals through multiple analysis engines, and executes trades while maintaining strict risk controls.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         External Systems                         │
├─────────────────┬──────────────────┬────────────────────────────┤
│  IG Markets API │  News APIs       │  MongoDB Database          │
│  - REST API     │  - Alpha Vantage │  - Tick Data               │
│  - Lightstreamer│  - Forex Factory │  - Trade History           │
└────────┬────────┴────────┬─────────┴────────┬───────────────────┘
         │                 │                  │
         ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
├─────────────────┬──────────────────┬────────────────────────────┤
│ Data Collector  │ Stream Monitor   │ Database Handler           │
│ - Real-time     │ - Lightstreamer  │ - MongoDB Client           │
│ - Historical    │ - Account Updates │ - Data Persistence         │
└────────┬────────┴────────┬─────────┴────────┬───────────────────┘
         │                 │                  │
         ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Analysis Layer                                │
├──────────────┬────────────────┬─────────────┬───────────────────┤
│Signal Analyzer│ ML Engine      │ Sentiment   │ Market Regime     │
│- Technical    │- Random Forest │ Analyzer    │ Detector          │
│- Indicators   │- Gradient Boost│- News       │- Trend Analysis   │
│- Patterns     │- Ensemble      │- TextBlob   │- Volatility       │
└──────┬───────┴───────┬────────┴──────┬──────┴───────────────────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Decision Layer                                │
├─────────────────┬──────────────────┬────────────────────────────┤
│ Strategy Engine │ Risk Manager     │ Position Manager           │
│ - Signal Fusion │ - Position Sizing │ - Dynamic Adjustment       │
│ - Entry/Exit    │ - Stop Loss      │ - AI Optimization          │
│ - Confidence    │ - Risk Limits    │ - Performance Based        │
└────────┬────────┴────────┬─────────┴────────┬───────────────────┘
         │                 │                  │
         ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Layer                               │
├─────────────────┬──────────────────┬────────────────────────────┤
│ Trade Executor  │ Order Manager    │ Emergency Controller       │
│ - Order Routing │ - Order Tracking │ - Manual Override          │
│ - Execution     │ - Fill Monitor   │ - Position Closure         │
└────────┬────────┴────────┬─────────┴────────────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Monitoring Layer                              │
├─────────────────┬──────────────────┬────────────────────────────┤
│Performance Track│ Logger           │ Alert System               │
│ - P&L Tracking  │ - Trade Logs     │ - Risk Alerts              │
│ - Metrics       │ - System Logs    │ - Performance Alerts       │
└─────────────────┴──────────────────┴────────────────────────────┘
```

## Core Components

### 1. Data Layer

#### Data Collector (`core/data_collector.py`)
- **Purpose**: Aggregates market data from multiple sources
- **Key Functions**:
  - Real-time price streaming via Lightstreamer
  - Historical data fetching for backtesting
  - Tick data aggregation and storage
  - Market depth analysis
- **Interfaces**: IG Markets API, MongoDB

#### Stream Monitor (`monitoring/stream_monitor.py`)
- **Purpose**: Manages real-time data streams
- **Key Functions**:
  - Lightstreamer subscription management
  - Connection health monitoring
  - Auto-reconnection on failures
  - Account balance updates
- **Protocols**: WebSocket, HTTP streaming

#### Database Handler (`utils/database_handler.py`)
- **Purpose**: Manages all database operations
- **Collections**:
  - `tick_data`: Raw market prices
  - `trades`: Executed trade records
  - `ml_predictions`: Model outputs
  - `performance_metrics`: System analytics
- **Features**: Connection pooling, bulk operations, indexing

### 2. Analysis Layer

#### Signal Analyzer (`core/signal_analyzer.py`)
- **Purpose**: Technical analysis engine
- **Indicators**:
  - Trend: SMA, EMA, MACD
  - Momentum: RSI, Stochastic
  - Volatility: Bollinger Bands, ATR
  - Volume: OBV, Volume Profile
- **Timeframes**: 1m, 5m, 15m, 1h, 4h, 1d

#### ML Engine (`ml/ensemble_model.py`)
- **Purpose**: Machine learning predictions
- **Models**:
  - Random Forest Classifier
  - Gradient Boosting Classifier
  - Ensemble voting mechanism
- **Features**:
  - 50+ engineered features
  - Auto-retraining pipeline
  - Performance validation

#### Sentiment Analyzer (`strategies/enhanced_strategy.py`)
- **Purpose**: News sentiment analysis
- **Sources**:
  - Alpha Vantage news feed
  - Forex Factory calendar
  - Financial news aggregators
- **Processing**:
  - TextBlob sentiment scoring
  - Financial keyword weighting
  - Entity recognition

### 3. Decision Layer

#### Strategy Engine (`core/strategy_engine.py`)
- **Purpose**: Central decision-making system
- **Signal Integration**:
  - Technical signal weight: 30%
  - ML prediction weight: 25%
  - Sentiment weight: 20%
  - Market regime weight: 25%
- **Decision Process**:
  1. Collect all signals
  2. Apply confidence thresholds
  3. Check risk constraints
  4. Generate trade decision

#### Risk Manager (`core/risk_manager.py`)
- **Purpose**: Risk control and position sizing
- **Controls**:
  - Maximum position size per trade
  - Daily loss limits
  - Maximum drawdown protection
  - Correlation limits
- **Calculations**:
  - Kelly Criterion position sizing
  - Value at Risk (VaR)
  - Expected shortfall

#### Position Manager
- **Purpose**: Dynamic position management
- **Features**:
  - AI-driven position adjustments
  - Performance-based scaling
  - Partial profit taking
  - Emergency position reduction

### 4. Execution Layer

#### Trade Executor (`core/trade_executor.py`)
- **Purpose**: Order execution and management
- **Order Types**:
  - Market orders
  - Limit orders
  - Stop orders
  - Trailing stops
- **Execution Logic**:
  - Smart order routing
  - Slippage minimization
  - Fill optimization

#### Order Manager
- **Purpose**: Order lifecycle management
- **Functions**:
  - Order validation
  - Status tracking
  - Fill monitoring
  - Partial fill handling

### 5. Monitoring Layer

#### Performance Tracker (`monitoring/performance_tracker.py`)
- **Metrics**:
  - Real-time P&L
  - Win rate
  - Sharpe ratio
  - Maximum drawdown
  - Risk-adjusted returns
- **Reporting**: Real-time dashboards, daily summaries

## Data Flow

### 1. Market Data Flow
```
Market Data → Lightstreamer → Data Collector → Database
                    ↓
              Stream Monitor → Signal Analyzer
```

### 2. Signal Generation Flow
```
Technical Analysis ─┐
ML Predictions ─────┼→ Strategy Engine → Trade Signal
Sentiment Score ────┤
Market Regime ──────┘
```

### 3. Trade Execution Flow
```
Trade Signal → Risk Check → Position Sizing → Order Creation → Execution
                   ↓              ↓                ↓              ↓
              Risk Manager   Position Mgr    Order Manager   IG Markets
```

## Communication Patterns

### Event-Driven Architecture
- **Pub/Sub Pattern**: Components subscribe to relevant events
- **Event Types**:
  - `MARKET_UPDATE`: New price data
  - `SIGNAL_GENERATED`: Trading signal created
  - `TRADE_EXECUTED`: Order filled
  - `RISK_ALERT`: Risk threshold breached

### API Integration
- **REST API**: IG Markets trading operations
- **WebSocket**: Real-time data streaming
- **Polling**: Account status updates

## Scalability Considerations

### Horizontal Scaling
- Multiple market support through configuration
- Parallel signal processing
- Distributed ML model training

### Performance Optimization
- MongoDB indexing for fast queries
- In-memory caching for frequently accessed data
- Asynchronous processing for non-critical paths
- Connection pooling for API calls

## Reliability Features

### Fault Tolerance
- Automatic reconnection for dropped connections
- Graceful degradation when components fail
- Transaction logging for recovery
- State persistence across restarts

### Error Handling
- Comprehensive exception handling
- Retry logic with exponential backoff
- Circuit breakers for external services
- Detailed error logging and alerting

## Security Architecture

### Authentication
- API key management
- Secure credential storage
- Session management

### Data Security
- Encrypted database connections
- No sensitive data in logs
- Secure configuration management

## Deployment Architecture

### Components
- **Application Server**: Python runtime
- **Database Server**: MongoDB instance
- **Streaming Services**: Lightstreamer connections
- **External APIs**: IG Markets, news services

### Requirements
- **CPU**: Multi-core for parallel processing
- **Memory**: 4GB+ for ML models
- **Network**: Low-latency connection
- **Storage**: SSD for database performance

## Extension Points

### Adding New Markets
1. Create market configuration in `configs/assets/`
2. Update strategy parameters
3. Configure data collection

### Adding New Strategies
1. Implement strategy interface
2. Register in strategy engine
3. Configure signal weights

### Adding New Indicators
1. Implement in signal analyzer
2. Add to feature engineering
3. Update strategy logic

## Performance Characteristics

### Latency
- Market data processing: <100ms
- Signal generation: <500ms
- Order execution: <1s

### Throughput
- Tick processing: 1000+ ticks/second
- Concurrent markets: 10+
- Order capacity: 100+ orders/hour

### Resource Usage
- CPU: 20-40% average
- Memory: 2-3GB typical
- Network: 10-50 Mbps
- Storage: 1-5GB/day