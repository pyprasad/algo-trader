# Troubleshooting Guide

## Common Issues and Solutions

### Authentication Issues

#### Problem: "Invalid API Key" Error
```
ERROR: API key authentication failed: error.security.api-key-invalid
```

**Solutions:**
1. Verify API key is correct in `configs/ig_config.yaml`
2. Check API key is active in IG Markets account settings
3. Ensure using correct environment (demo vs live)
4. Regenerate API key if necessary

```bash
# Test API connection
python scripts/test_ig_connection.py

# Verify credentials
python -c "from core.ig_service import IGService; ig = IGService(); ig.test_connection()"
```

#### Problem: "Session Expired" Error
```
ERROR: Session token expired or invalid
```

**Solutions:**
1. Implement automatic session refresh
2. Check session timeout settings
3. Verify keep-alive is working

```python
# Add to ig_service.py
def refresh_session(self):
    """Refresh expired session."""
    self.logout()
    time.sleep(2)
    self.login()
```

### Connection Issues

#### Problem: Cannot Connect to Lightstreamer
```
ERROR: Lightstreamer connection failed: Connection refused
```

**Solutions:**
1. Check network connectivity
```bash
ping demo-apd.marketdatasystems.com
telnet demo-apd.marketdatasystems.com 443
```

2. Verify firewall settings
```bash
# Check if port 443 is open
sudo ufw status
sudo iptables -L
```

3. Test with curl
```bash
curl -I https://demo-apd.marketdatasystems.com
```

4. Check proxy settings
```python
# If behind proxy
import os
os.environ['HTTP_PROXY'] = 'http://proxy.example.com:8080'
os.environ['HTTPS_PROXY'] = 'http://proxy.example.com:8080'
```

#### Problem: MongoDB Connection Timeout
```
ERROR: ServerSelectionTimeoutError: localhost:27017: Connection refused
```

**Solutions:**
1. Check MongoDB service status
```bash
# Linux
sudo systemctl status mongod
sudo systemctl start mongod

# macOS
brew services list
brew services start mongodb-community

# Windows
net start MongoDB
```

2. Verify MongoDB is listening
```bash
netstat -an | grep 27017
```

3. Test connection
```bash
mongo --eval "db.adminCommand('ping')"
```

4. Check configuration
```yaml
# configs/database_config.yaml
mongodb:
  connection_string: "mongodb://localhost:27017/"  # Verify this
```

### Trading Issues

#### Problem: "Market Closed" Error
```
ERROR: Cannot place order: Market status is CLOSED
```

**Solutions:**
1. Check market hours
```python
# Add market hours check
def is_market_open(market):
    now = datetime.now(pytz.timezone('Europe/London'))
    market_hours = config['markets'][market]['hours']
    
    open_time = datetime.strptime(market_hours['open'], '%H:%M').time()
    close_time = datetime.strptime(market_hours['close'], '%H:%M').time()
    
    return open_time <= now.time() <= close_time
```

2. Account for holidays
```python
# Check if today is a holiday
holidays = config['markets'][market]['holidays']
if datetime.now().date() in holidays:
    logger.info("Market closed for holiday")
```

#### Problem: "Insufficient Funds" Error
```
ERROR: Order rejected: Insufficient funds
```

**Solutions:**
1. Check account balance
```python
account = ig_service.get_account_info()
print(f"Available: {account['available']}")
print(f"Balance: {account['balance']}")
print(f"Margin: {account['margin']}")
```

2. Reduce position size
```python
# Adjust position sizing
position_size = min(
    calculated_size,
    account['available'] * 0.5  # Use max 50% of available
)
```

3. Check margin requirements
```python
market_info = ig_service.get_market_details(epic)
margin_required = position_size * market_info['margin_factor']
```

#### Problem: "Stop Distance Too Small" Error
```
ERROR: Order rejected: Stop distance must be at least 8 points
```

**Solutions:**
1. Check minimum stop distance
```python
market_details = ig_service.get_market_details(epic)
min_stop = market_details['minStopDistance']
```

2. Adjust stop loss calculation
```python
stop_distance = max(
    calculated_stop,
    min_stop * 1.1  # Add 10% buffer
)
```

### Data Issues

#### Problem: Missing or Delayed Data
```
WARNING: No data received for FTSE_100 in 60 seconds
```

**Solutions:**
1. Check subscription status
```python
def check_subscriptions():
    for subscription in active_subscriptions:
        if not subscription.is_active():
            logger.warning(f"Resubscribing to {subscription.items}")
            client.unsubscribe(subscription)
            client.subscribe(subscription)
```

2. Implement data validation
```python
def validate_tick_data(tick):
    if tick['timestamp'] < time.time() - 300:  # 5 minutes old
        logger.warning(f"Stale data: {tick}")
        return False
    
    if tick['bid'] >= tick['ask']:
        logger.error(f"Invalid spread: {tick}")
        return False
        
    return True
```

3. Add redundant data sources
```python
# Fallback to REST API if streaming fails
if not streaming_data:
    data = ig_service.get_market_snapshot(epic)
```

#### Problem: Database Write Failures
```
ERROR: Failed to insert tick data: WriteError
```

**Solutions:**
1. Check disk space
```bash
df -h
du -sh /var/lib/mongodb
```

2. Verify database permissions
```bash
mongo --eval "db.runCommand({connectionStatus: 1})"
```

3. Implement retry logic
```python
def insert_with_retry(collection, document, max_retries=3):
    for attempt in range(max_retries):
        try:
            collection.insert_one(document)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

### Machine Learning Issues

#### Problem: "Model Not Found" Error
```
ERROR: Could not load model: FileNotFoundError: models/rf_model.pkl
```

**Solutions:**
1. Train initial models
```bash
python ml/model_trainer.py --initial-training
```

2. Check model path
```python
import os
model_path = os.path.join(os.getcwd(), 'models', 'rf_model.pkl')
if not os.path.exists(model_path):
    logger.error(f"Model not found at {model_path}")
```

3. Download pre-trained models
```bash
# If using remote models
wget https://example.com/models/rf_model.pkl -O models/rf_model.pkl
```

#### Problem: Poor Model Performance
```
WARNING: Model accuracy dropped below threshold: 0.45
```

**Solutions:**
1. Retrain with recent data
```python
# Force retraining
python ml/model_trainer.py --force-retrain --lookback-days 60
```

2. Check feature quality
```python
# Analyze feature importance
importances = model.feature_importances_
for feature, importance in zip(features, importances):
    if importance < 0.01:
        logger.warning(f"Low importance feature: {feature}")
```

3. Validate data quality
```python
# Check for data issues
def validate_training_data(df):
    # Check for NaN values
    nan_cols = df.columns[df.isna().any()].tolist()
    if nan_cols:
        logger.warning(f"NaN values in: {nan_cols}")
    
    # Check for outliers
    for col in df.select_dtypes(include=[np.number]):
        z_scores = np.abs(stats.zscore(df[col]))
        outliers = df[z_scores > 3]
        if len(outliers) > 0:
            logger.warning(f"Outliers in {col}: {len(outliers)}")
```

### Performance Issues

#### Problem: High CPU Usage
```
WARNING: CPU usage above 80%
```

**Solutions:**
1. Profile code to find bottlenecks
```bash
python -m cProfile -o profile.stats runners/run_multi_market.py
python -m pstats profile.stats
```

2. Optimize heavy computations
```python
# Use numpy vectorization
# Bad
result = []
for price in prices:
    result.append(price * 2)

# Good
result = np.array(prices) * 2
```

3. Implement caching
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_indicator(prices_tuple, period):
    prices = np.array(prices_tuple)
    # Expensive calculation
    return result
```

#### Problem: Memory Leak
```
ERROR: MemoryError: Unable to allocate array
```

**Solutions:**
1. Monitor memory usage
```python
import psutil
import gc

process = psutil.Process()
logger.info(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Force garbage collection
gc.collect()
```

2. Limit data retention
```python
# Clear old data periodically
def cleanup_old_data():
    cutoff = datetime.now() - timedelta(hours=24)
    db.tick_data.delete_many({'timestamp': {'$lt': cutoff}})
```

3. Use generators for large datasets
```python
# Bad: Loads all data into memory
def get_all_ticks():
    return list(db.tick_data.find())

# Good: Generator approach
def get_all_ticks():
    for tick in db.tick_data.find():
        yield tick
```

### Risk Management Issues

#### Problem: Stop Loss Not Triggered
```
ERROR: Position exceeded stop loss but not closed
```

**Solutions:**
1. Verify stop loss is set
```python
position = ig_service.get_position(deal_id)
if not position.get('stopLevel'):
    logger.error(f"No stop loss on position {deal_id}")
    ig_service.update_position(deal_id, stop_level=calculated_stop)
```

2. Check guaranteed stops
```python
# Use guaranteed stops for gap protection
order['guaranteedStop'] = True
order['stopLevel'] = stop_level
```

3. Implement backup monitoring
```python
def monitor_positions():
    for position in get_open_positions():
        current_price = get_current_price(position['epic'])
        
        if position['direction'] == 'BUY':
            if current_price <= position['stopLevel']:
                logger.warning("Stop loss breach detected")
                close_position(position['dealId'])
```

#### Problem: Daily Loss Limit Exceeded
```
CRITICAL: Daily loss limit exceeded: -£650 (limit: -£600)
```

**Solutions:**
1. Implement pre-trade checks
```python
def check_daily_loss_limit():
    daily_pnl = calculate_daily_pnl()
    
    if daily_pnl <= -config['max_daily_loss']:
        logger.critical("Daily loss limit reached")
        disable_trading()
        return False
    
    return True
```

2. Add progressive position reduction
```python
# Reduce position size as approaching limit
daily_loss_percent = abs(daily_pnl / account_balance)
if daily_loss_percent > 0.04:  # 4% loss
    position_multiplier = 0.5  # Halve position sizes
elif daily_loss_percent > 0.02:  # 2% loss
    position_multiplier = 0.75  # Reduce by 25%
```

## Diagnostic Tools

### System Health Check Script

```python
# scripts/health_check.py
def run_health_check():
    checks = {
        'mongodb': check_mongodb(),
        'ig_api': check_ig_api(),
        'lightstreamer': check_lightstreamer(),
        'disk_space': check_disk_space(),
        'memory': check_memory(),
        'models': check_models_exist(),
        'config': validate_configs()
    }
    
    for component, status in checks.items():
        if status['healthy']:
            print(f"✓ {component}: OK")
        else:
            print(f"✗ {component}: {status['error']}")
            
    return all(s['healthy'] for s in checks.values())
```

### Log Analysis

```bash
# Find errors in logs
grep -E "ERROR|CRITICAL" logs/algo_trader.log | tail -50

# Count errors by type
grep ERROR logs/algo_trader.log | cut -d: -f4 | sort | uniq -c

# Find slow operations
grep "took [0-9]\{4,\}ms" logs/performance.log

# Monitor log in real-time
tail -f logs/algo_trader.log | grep --line-buffered ERROR
```

### Debug Mode

```python
# Enable debug mode
import logging
logging.basicConfig(level=logging.DEBUG)

# Add debug decorators
from functools import wraps

def debug_function(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__}")
        logger.debug(f"Args: {args}")
        logger.debug(f"Kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
            
    return wrapper
```

## Recovery Procedures

### Emergency Stop

```python
# scripts/emergency_stop.py
def emergency_stop():
    """Emergency stop all trading activities."""
    try:
        # 1. Cancel all pending orders
        orders = ig_service.get_working_orders()
        for order in orders:
            ig_service.cancel_order(order['dealId'])
            
        # 2. Close all positions
        positions = ig_service.get_positions()
        for position in positions:
            ig_service.close_position(
                position['dealId'],
                size=position['size']
            )
            
        # 3. Disable auto-trading
        config['trading_enabled'] = False
        save_config(config)
        
        # 4. Send alerts
        send_alert("EMERGENCY STOP ACTIVATED", severity="critical")
        
        logger.critical("Emergency stop completed")
        
    except Exception as e:
        logger.critical(f"Emergency stop failed: {e}")
        # Last resort: kill process
        os.kill(os.getpid(), signal.SIGTERM)
```

### Data Recovery

```python
# scripts/recover_data.py
def recover_missing_data(start_date, end_date):
    """Recover missing historical data."""
    
    # Find gaps in data
    gaps = find_data_gaps(start_date, end_date)
    
    for gap in gaps:
        logger.info(f"Recovering data for {gap['start']} to {gap['end']}")
        
        # Fetch from IG Markets
        historical = ig_service.get_historical_prices(
            epic=gap['epic'],
            resolution='MINUTE',
            start=gap['start'],
            end=gap['end']
        )
        
        # Store in database
        db.tick_data.insert_many(historical)
        
    logger.info("Data recovery completed")
```

## Getting Help

### Support Channels

1. **Documentation**: Check relevant documentation files
2. **Logs**: Review detailed logs in `logs/` directory
3. **Diagnostics**: Run `python scripts/diagnose.py`
4. **Community**: Post in discussion forums
5. **Support**: Contact development team

### Information to Provide

When reporting issues, include:
1. Error messages and stack traces
2. Configuration files (sanitized)
3. System information (OS, Python version)
4. Steps to reproduce
5. Log files from time of error
6. Output of diagnostic scripts

### Diagnostic Report

```bash
# Generate diagnostic report
python scripts/generate_diagnostic_report.py > diagnostic_report.txt
```

The report includes:
- System information
- Configuration validation
- Connection tests
- Recent errors
- Performance metrics
- Database statistics