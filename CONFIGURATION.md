# Configuration Reference

## Overview

The Algo-Trader system uses YAML configuration files for maximum flexibility and ease of management. All configuration files are located in the `configs/` directory with market-specific configurations in `configs/assets/`.

## Configuration Files Structure

```
configs/
├── ig_config.yaml           # IG Markets API credentials
├── database_config.yaml     # MongoDB connection settings
├── strategy_config.yaml     # Trading strategy parameters
├── risk_config.yaml         # Risk management settings
├── ml_config.yaml          # Machine learning configuration
├── sentiment_config.yaml    # Sentiment analysis settings
└── assets/                  # Market-specific configurations
    ├── ftse_100.yaml       # FTSE 100 market config
    ├── dax.yaml            # DAX market config
    └── dow_jones.yaml      # Dow Jones market config
```

## Core Configuration Files

### 1. IG Markets Configuration (`ig_config.yaml`)

```yaml
# IG Markets API Configuration
ig_service:
  # Account credentials
  username: "YOUR_USERNAME"
  password: "YOUR_PASSWORD"
  api_key: "YOUR_API_KEY"
  
  # Account settings
  acc_type: "DEMO"  # Options: DEMO, LIVE
  acc_number: "YOUR_ACCOUNT_NUMBER"
  
  # Additional settings
  lightstreamer_endpoint: "https://demo-apd.marketdatasystems.com"
  lightstreamer_password: "CST-XXX|XST-XXX"  # Auto-generated on login

api_config:
  # API endpoints
  base_url: "https://demo-api.ig.com/gateway/deal"  # Change for LIVE
  streaming_url: "https://demo-apd.marketdatasystems.com"
  
  # API version
  version: "3"
  
  # Request settings
  timeout: 30  # seconds
  max_retries: 3
  retry_delay: 5  # seconds
  
  # Rate limiting
  requests_per_second: 5
  requests_per_minute: 60

session:
  # Session management
  keepalive_interval: 300  # seconds
  auto_reconnect: true
  max_reconnect_attempts: 10
  reconnect_delay: 30  # seconds
```

### 2. Database Configuration (`database_config.yaml`)

```yaml
# MongoDB Configuration
mongodb:
  # Connection settings
  connection_string: "mongodb://localhost:27017/"
  # For MongoDB Atlas:
  # connection_string: "mongodb+srv://username:password@cluster.mongodb.net/"
  
  # Database name
  database_name: "algo_trader"
  
  # Collection names
  collections:
    tick_data: "tick_data"
    trades: "trades"
    ml_predictions: "ml_predictions"
    performance_metrics: "performance_metrics"
    strategy_signals: "strategy_signals"
    risk_events: "risk_events"
    system_logs: "system_logs"
  
  # Connection pool settings
  options:
    max_pool_size: 100
    min_pool_size: 10
    max_idle_time_ms: 45000
    wait_queue_timeout_ms: 10000
    connect_timeout_ms: 10000
    socket_timeout_ms: 0
    server_selection_timeout_ms: 30000
    
  # Index configuration
  indexes:
    tick_data:
      - keys: [["timestamp", -1], ["symbol", 1]]
        unique: false
      - keys: [["symbol", 1], ["timestamp", -1]]
        unique: false
    trades:
      - keys: [["timestamp", -1]]
        unique: false
      - keys: [["status", 1], ["timestamp", -1]]
        unique: false
        
  # Data retention
  retention:
    tick_data_days: 30
    trades_days: 365
    ml_predictions_days: 90
    performance_metrics_days: 365
```

### 3. Strategy Configuration (`strategy_config.yaml`)

```yaml
# Trading Strategy Configuration
strategy:
  # Strategy type
  type: "enhanced_multi_signal"
  
  # Signal generation
  signals:
    # Technical analysis settings
    technical:
      enabled: true
      weight: 0.30
      min_confidence: 0.60
      
      # Indicator settings
      indicators:
        sma:
          periods: [20, 50, 200]
          weight: 0.15
        ema:
          periods: [12, 26]
          weight: 0.15
        rsi:
          period: 14
          overbought: 70
          oversold: 30
          weight: 0.20
        macd:
          fast: 12
          slow: 26
          signal: 9
          weight: 0.20
        bollinger:
          period: 20
          std_dev: 2
          weight: 0.15
        volume:
          period: 20
          weight: 0.15
          
      # Timeframes for analysis
      timeframes:
        - "1min"
        - "5min"
        - "15min"
        - "1hour"
      
    # Machine learning predictions
    ml:
      enabled: true
      weight: 0.25
      min_confidence: 0.65
      ensemble_method: "voting"  # Options: voting, stacking
      
    # Sentiment analysis
    sentiment:
      enabled: true
      weight: 0.20
      min_confidence: 0.55
      
      # Sentiment thresholds
      bullish_threshold: 0.6
      bearish_threshold: -0.6
      neutral_range: [-0.2, 0.2]
      
    # Market regime
    regime:
      enabled: true
      weight: 0.25
      
      # Regime detection parameters
      lookback_period: 100
      trend_threshold: 0.02
      volatility_percentile: 75
  
  # Entry conditions
  entry:
    # Minimum combined signal strength
    min_signal_strength: 0.65
    
    # Confirmation requirements
    require_volume_confirmation: true
    require_trend_alignment: true
    
    # Timing
    avoid_news_events: true
    news_blackout_minutes: 30
    
    # Market conditions
    min_liquidity: 1000000  # minimum daily volume
    max_spread_pips: 2
    
  # Exit conditions
  exit:
    # Take profit
    take_profit:
      method: "dynamic"  # Options: fixed, dynamic, trailing
      base_multiplier: 2.0  # Risk:Reward ratio
      atr_multiplier: 1.5
      
    # Stop loss
    stop_loss:
      method: "atr"  # Options: fixed, atr, support_resistance
      atr_multiplier: 1.5
      min_distance_pips: 10
      
    # Trailing stop
    trailing_stop:
      enabled: true
      activation_profit: 1.0  # Activate after 1x risk in profit
      trail_distance: 0.5  # Trail by 0.5x ATR
      
    # Time-based exits
    max_holding_period: 1440  # minutes (24 hours)
    end_of_day_close: true
    
  # Position management
  position:
    # Scaling
    scale_in:
      enabled: false
      levels: 3
      size_distribution: [0.5, 0.3, 0.2]
      
    scale_out:
      enabled: true
      profit_levels: [1.0, 2.0, 3.0]  # Take profit at 1R, 2R, 3R
      size_distribution: [0.33, 0.33, 0.34]
      
  # Filters
  filters:
    # Trading hours
    trading_hours:
      enabled: true
      # Defined per market in asset configs
      
    # Avoid trading during major news
    news_filter:
      enabled: true
      high_impact_only: false
      
    # Market state filters
    trend_filter:
      enabled: true
      min_trend_strength: 0.3
      
    volatility_filter:
      enabled: true
      min_volatility: 0.5  # percentage
      max_volatility: 3.0  # percentage
```

### 4. Risk Management Configuration (`risk_config.yaml`)

```yaml
# Risk Management Configuration
risk_management:
  # Position sizing
  position_sizing:
    method: "kelly_criterion"  # Options: fixed, percentage, kelly_criterion
    
    # Fixed method
    fixed_size: 1.0  # lots
    
    # Percentage method
    risk_per_trade: 0.02  # 2% of account
    
    # Kelly Criterion
    kelly:
      fraction: 0.25  # Use 25% of Kelly suggestion
      max_leverage: 10
      lookback_trades: 100
      
  # Risk limits
  limits:
    # Per trade limits
    max_risk_per_trade: 0.02  # 2% of account
    max_position_size: 5.0  # lots
    
    # Daily limits
    max_daily_loss: 0.06  # 6% daily loss limit
    max_daily_trades: 20
    
    # Overall limits
    max_open_positions: 5
    max_exposure: 0.15  # 15% of account
    max_drawdown: 0.20  # 20% maximum drawdown
    
    # Correlation limits
    max_correlated_positions: 3
    correlation_threshold: 0.7
    
  # Stop loss settings
  stop_loss:
    # Mandatory stop loss
    mandatory: true
    
    # Stop loss methods
    initial:
      method: "atr"  # Options: fixed, atr, support_resistance
      atr_multiplier: 1.5
      min_distance: 10  # pips
      max_distance: 50  # pips
      
    # Trailing stop
    trailing:
      enabled: true
      activation_profit: 20  # pips
      trail_distance: 10  # pips
      
  # Emergency controls
  emergency:
    # Circuit breakers
    circuit_breaker:
      enabled: true
      daily_loss_threshold: 0.05  # 5% triggers circuit breaker
      cooldown_period: 3600  # seconds
      
    # Kill switch
    kill_switch:
      enabled: true
      conditions:
        - consecutive_losses: 5
        - drawdown_percent: 15
        - technical_errors: 3
        
    # Position closure
    close_all_positions:
      on_daily_loss_limit: true
      on_connection_loss: false
      on_data_feed_loss: true
      
  # Margin management
  margin:
    # Margin requirements
    min_free_margin: 0.30  # Keep 30% margin free
    margin_call_level: 0.50  # IG margin call level
    margin_closeout_level: 0.25  # Automatic closeout
    
    # Margin alerts
    alerts:
      - level: 0.40
        action: "reduce_positions"
      - level: 0.35
        action: "stop_new_trades"
      - level: 0.30
        action: "close_losing_positions"
```

### 5. Machine Learning Configuration (`ml_config.yaml`)

```yaml
# Machine Learning Configuration
ml_config:
  # Model settings
  models:
    # Random Forest
    random_forest:
      enabled: true
      n_estimators: 100
      max_depth: 10
      min_samples_split: 5
      min_samples_leaf: 2
      max_features: "sqrt"
      
    # Gradient Boosting
    gradient_boosting:
      enabled: true
      n_estimators: 100
      learning_rate: 0.1
      max_depth: 5
      min_samples_split: 5
      min_samples_leaf: 2
      subsample: 0.8
      
    # Ensemble settings
    ensemble:
      method: "voting"  # Options: voting, stacking, blending
      weights: [0.5, 0.5]  # RF, GB weights
      
  # Feature engineering
  features:
    # Technical features
    technical:
      - "rsi"
      - "macd"
      - "bollinger_position"
      - "volume_ratio"
      - "price_change"
      - "volatility"
      
    # Market microstructure
    microstructure:
      - "bid_ask_spread"
      - "order_imbalance"
      - "trade_intensity"
      
    # Lag features
    lags:
      periods: [1, 5, 10, 30, 60]
      
    # Rolling statistics
    rolling:
      windows: [5, 15, 30, 60]
      statistics: ["mean", "std", "min", "max"]
      
  # Training settings
  training:
    # Data split
    train_test_split: 0.8
    validation_split: 0.2
    
    # Sampling
    sample_size: 10000
    resampling_method: "SMOTE"  # Handle imbalanced data
    
    # Cross-validation
    cv_folds: 5
    cv_method: "TimeSeriesSplit"
    
    # Retraining
    retrain_interval: 86400  # seconds (24 hours)
    min_samples_for_retrain: 1000
    performance_threshold: 0.55  # Retrain if accuracy drops below
    
  # Prediction settings
  prediction:
    # Confidence thresholds
    min_confidence: 0.65
    
    # Prediction horizon
    lookforward_periods: 5  # Predict 5 periods ahead
    
    # Output
    prediction_classes: 3  # Buy, Hold, Sell
    probability_calibration: true
    
  # Model persistence
  persistence:
    model_path: "models/"
    save_interval: 86400  # seconds
    keep_versions: 5
    
  # Performance monitoring
  monitoring:
    # Metrics to track
    metrics:
      - "accuracy"
      - "precision"
      - "recall"
      - "f1_score"
      - "auc_roc"
      
    # Alert thresholds
    alert_on_degradation: 0.1  # 10% performance drop
```

### 6. Sentiment Analysis Configuration (`sentiment_config.yaml`)

```yaml
# Sentiment Analysis Configuration
sentiment:
  # Data sources
  sources:
    # Alpha Vantage News
    alpha_vantage:
      enabled: true
      api_key: "YOUR_API_KEY"
      endpoints:
        news: "https://www.alphavantage.co/query"
      refresh_interval: 300  # seconds
      
    # Forex Factory Calendar
    forex_factory:
      enabled: true
      url: "https://www.forexfactory.com/calendar"
      high_impact_only: false
      
    # Twitter (optional)
    twitter:
      enabled: false
      api_key: "YOUR_API_KEY"
      api_secret: "YOUR_API_SECRET"
      accounts_to_follow:
        - "@Bloomberg"
        - "@Reuters"
        - "@FT"
        
  # Analysis settings
  analysis:
    # Sentiment model
    model: "textblob"  # Options: textblob, vader, transformer
    
    # Scoring
    scoring:
      method: "weighted"  # Options: simple, weighted
      
      # Weight by source credibility
      source_weights:
        alpha_vantage: 1.0
        forex_factory: 0.8
        twitter: 0.5
        
      # Weight by recency
      time_decay:
        enabled: true
        half_life: 3600  # seconds
        
    # Financial keywords
    keywords:
      bullish:
        - "surge"
        - "rally"
        - "breakout"
        - "bullish"
        - "upgrade"
        - "beat estimates"
        weight: 1.5
        
      bearish:
        - "crash"
        - "plunge"
        - "breakdown"
        - "bearish"
        - "downgrade"
        - "miss estimates"
        weight: 1.5
        
      neutral:
        - "unchanged"
        - "steady"
        - "flat"
        weight: 1.0
        
  # Event impact
  events:
    # Economic calendar
    calendar:
      enabled: true
      
      # Event importance levels
      impact_levels:
        high: 1.0
        medium: 0.5
        low: 0.2
        
      # Pre/post event windows
      blackout_windows:
        high_impact:
          before: 30  # minutes
          after: 30   # minutes
        medium_impact:
          before: 15
          after: 15
        low_impact:
          before: 5
          after: 5
          
    # Market-moving events
    special_events:
      - name: "NFP"
        impact: "high"
        markets: ["USD", "EUR"]
      - name: "ECB Rate Decision"
        impact: "high"
        markets: ["EUR"]
      - name: "FOMC"
        impact: "high"
        markets: ["USD"]
        
  # Output settings
  output:
    # Aggregation
    aggregation_window: 900  # seconds (15 minutes)
    
    # Score range
    score_range: [-1, 1]
    
    # Confidence calculation
    min_articles_for_confidence: 3
    
    # Caching
    cache_duration: 300  # seconds
```

## Asset Configuration Files

### Market-Specific Configuration (`configs/assets/ftse_100.yaml`)

```yaml
# FTSE 100 Market Configuration
asset:
  # Basic information
  name: "FTSE 100"
  symbol: "FTSE"
  epic: "IX.D.FTSE.DAILY.IP"  # IG Markets EPIC code
  currency: "GBP"
  exchange: "LSE"
  
  # Trading specifications
  trading:
    # Contract specifications
    point_value: 1  # Value per point movement
    min_deal_size: 0.5  # Minimum position size
    max_deal_size: 500  # Maximum position size
    
    # Margin requirements
    margin_factor: 0.05  # 5% margin
    
    # Costs
    spread:
      typical: 1.0  # pips
      min: 0.8
      max: 3.0
    commission: 0  # Included in spread
    financing:
      long: -0.0082  # Daily financing cost
      short: 0.0082
      
  # Market hours
  hours:
    # Regular trading hours
    regular:
      start: "08:00"
      end: "16:30"
      timezone: "Europe/London"
      
    # Extended hours (if available)
    extended:
      pre_market:
        start: "07:00"
        end: "08:00"
      after_hours:
        start: "16:30"
        end: "20:00"
        
    # Holidays (dates when market is closed)
    holidays:
      - "2024-01-01"  # New Year's Day
      - "2024-03-29"  # Good Friday
      - "2024-04-01"  # Easter Monday
      - "2024-05-06"  # Early May Bank Holiday
      - "2024-05-27"  # Spring Bank Holiday
      - "2024-08-26"  # Summer Bank Holiday
      - "2024-12-25"  # Christmas Day
      - "2024-12-26"  # Boxing Day
      
  # Strategy overrides (market-specific)
  strategy_overrides:
    # Technical indicators
    indicators:
      rsi:
        period: 14
        overbought: 75  # More conservative for FTSE
        oversold: 25
        
    # Entry/exit modifications
    entry:
      min_signal_strength: 0.70  # Higher threshold for FTSE
      
    exit:
      take_profit_multiplier: 1.8  # Slightly lower TP for FTSE
      
  # Risk overrides
  risk_overrides:
    max_position_size: 3.0  # Lower max size for FTSE
    stop_loss_min_distance: 10  # Larger minimum stop
    
  # Market-specific features
  features:
    # Correlation assets
    correlations:
      - asset: "DAX"
        typical_correlation: 0.85
      - asset: "EUR/GBP"
        typical_correlation: -0.4
        
    # Market characteristics
    characteristics:
      average_daily_range: 80  # points
      average_volume: 800000000  # shares
      volatility_regime:
        low: [0, 0.8]
        medium: [0.8, 1.5]
        high: [1.5, 3.0]
```

## Configuration Loading Priority

1. **Default Values**: Built-in defaults in code
2. **Configuration Files**: YAML files override defaults
3. **Environment Variables**: Override configuration files
4. **Command Line Arguments**: Highest priority

Example:
```python
# Priority order (highest to lowest):
# 1. Command line: --risk-per-trade 0.01
# 2. Environment: RISK_PER_TRADE=0.015
# 3. Config file: risk_per_trade: 0.02
# 4. Default: 0.02
```

## Dynamic Configuration Updates

Some configurations can be updated while the system is running:

### Hot-Reloadable Configs
- Strategy parameters
- Risk limits
- ML confidence thresholds
- Sentiment weights

### Requires Restart
- Database connections
- API credentials
- Market definitions
- Core system settings

## Configuration Validation

The system validates all configurations on startup:

```python
# Automatic validation checks:
- Required fields present
- Value ranges valid
- Cross-configuration consistency
- API credentials working
- Database connectivity
- Market hours valid
```

## Best Practices

1. **Security**
   - Never commit credentials to version control
   - Use environment variables for sensitive data
   - Rotate API keys regularly

2. **Testing**
   - Always test configuration changes in demo mode
   - Keep separate configs for demo/live
   - Version control configuration files

3. **Documentation**
   - Comment complex configurations
   - Document any deviations from defaults
   - Keep configuration changelog

4. **Monitoring**
   - Log configuration changes
   - Alert on configuration errors
   - Monitor parameter effectiveness