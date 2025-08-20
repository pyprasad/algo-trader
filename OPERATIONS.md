# Operations Guide

## Running the System

### Basic Execution

#### Demo Mode (Recommended for Testing)
```bash
# Run with demo account (paper trading)
python runners/run_multi_market.py --demo

# Run for specific duration
python runners/run_multi_market.py --demo --duration 3600  # Run for 1 hour

# Run specific markets
python runners/run_multi_market.py --demo --markets FTSE_100,DAX
```

#### Production Mode
```bash
# Run with live account (real money)
python runners/run_multi_market.py --live

# With safety confirmation
python runners/run_multi_market.py --live --confirm

# Production with specific config
python runners/run_multi_market.py --live --config configs/production.yaml
```

### Command Line Options

```bash
python runners/run_multi_market.py [OPTIONS]

Options:
  --demo                    Run in demo mode (paper trading)
  --live                    Run in live mode (real money)
  --markets MARKETS         Comma-separated list of markets
  --duration SECONDS        Run duration in seconds
  --config FILE            Custom configuration file
  --log-level LEVEL        Logging level (DEBUG, INFO, WARNING, ERROR)
  --no-ml                  Disable machine learning predictions
  --no-sentiment           Disable sentiment analysis
  --backtest               Run in backtest mode
  --from-date DATE         Backtest start date (YYYY-MM-DD)
  --to-date DATE           Backtest end date (YYYY-MM-DD)
  --dry-run                Execute without placing orders
  --confirm                Require confirmation for live trading
```

### Startup Sequence

1. **Configuration Loading**
```
[INFO] Loading configuration files...
[INFO] ✓ ig_config.yaml loaded
[INFO] ✓ database_config.yaml loaded
[INFO] ✓ strategy_config.yaml loaded
[INFO] ✓ risk_config.yaml loaded
```

2. **Service Initialization**
```
[INFO] Initializing services...
[INFO] ✓ MongoDB connected
[INFO] ✓ IG Markets API authenticated
[INFO] ✓ Lightstreamer connected
[INFO] ✓ ML models loaded
```

3. **Market Validation**
```
[INFO] Validating markets...
[INFO] ✓ FTSE_100: TRADEABLE
[INFO] ✓ DAX: TRADEABLE
```

4. **Strategy Activation**
```
[INFO] Starting trading strategies...
[INFO] ✓ FTSE_100: enhanced_multi_signal strategy active
[INFO] ✓ DAX: enhanced_multi_signal strategy active
```

## Process Management

### Running as a Service

#### SystemD (Linux)

Create service file `/etc/systemd/system/algo-trader.service`:
```ini
[Unit]
Description=Algo Trader Trading System
After=network.target mongodb.service

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/algo-trader
Environment="PATH=/opt/algo-trader/venv/bin"
ExecStart=/opt/algo-trader/venv/bin/python /opt/algo-trader/runners/run_multi_market.py --live
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable algo-trader
sudo systemctl start algo-trader
sudo systemctl status algo-trader
```

#### Supervisor (Alternative)

Configuration `/etc/supervisor/conf.d/algo-trader.conf`:
```ini
[program:algo-trader]
command=/opt/algo-trader/venv/bin/python /opt/algo-trader/runners/run_multi_market.py --live
directory=/opt/algo-trader
user=trader
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/algo-trader/output.log
environment=PATH="/opt/algo-trader/venv/bin"
```

### Process Monitoring

#### Health Checks
```bash
# Check if system is running
ps aux | grep run_multi_market

# Check system health
curl http://localhost:8080/health

# View recent logs
tail -f logs/algo_trader.log
```

#### Resource Monitoring
```bash
# Monitor CPU and memory
htop -p $(pgrep -f run_multi_market)

# Monitor network connections
netstat -tunp | grep python

# Check disk usage
df -h /var/lib/mongodb
```

## Monitoring

### Real-Time Monitoring

#### Console Output
```
════════════════════════════════════════════════════════════════════
                    ALGO TRADER - LIVE TRADING
════════════════════════════════════════════════════════════════════
Account: LIVE-123456 | Balance: £10,000.00 | Available: £8,500.00
════════════════════════════════════════════════════════════════════

MARKET STATUS:
├─ FTSE 100: 7500.5/7501.5 ↑0.45% | Volume: 125M
└─ DAX: 15250.0/15251.0 ↓0.12% | Volume: 85M

ACTIVE POSITIONS:
├─ FTSE_100: LONG 1.0 @ 7495.0 | P&L: +£25.50 | Stop: 7480.0
└─ DAX: None

SIGNALS:
├─ FTSE_100: BUY (0.72) | Tech: 0.65 | ML: 0.78 | Sent: 0.70
└─ DAX: HOLD (0.48) | Tech: 0.45 | ML: 0.52 | Sent: 0.47

PERFORMANCE:
├─ Today P&L: +£125.50 | Trades: 5 | Win Rate: 60%
└─ Month P&L: +£1,250.00 | Sharpe: 1.85 | Max DD: -3.2%
```

#### Log Files

Log locations:
```
logs/
├── algo_trader.log          # Main application log
├── trades.log              # Trade execution log
├── errors.log              # Error log
├── performance.log         # Performance metrics
└── api_requests.log        # API communication log
```

Log rotation configuration:
```yaml
# logging_config.yaml
handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: logs/algo_trader.log
    maxBytes: 10485760  # 10MB
    backupCount: 30
    formatter: detailed
```

### Performance Dashboards

#### Grafana Setup

1. Install Grafana:
```bash
sudo apt-get install grafana
sudo systemctl start grafana-server
```

2. Configure data source (MongoDB):
```json
{
  "name": "AlgoTrader-MongoDB",
  "type": "mongodb-datasource",
  "url": "mongodb://localhost:27017",
  "database": "algo_trader"
}
```

3. Import dashboard template:
```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/algo_trader_dashboard.json
```

#### Key Metrics to Monitor

**System Health**
- API connectivity status
- Data feed latency
- Order execution time
- Error rate

**Trading Performance**
- Real-time P&L
- Open positions
- Win/loss ratio
- Sharpe ratio
- Maximum drawdown

**Risk Metrics**
- Current exposure
- Margin utilization
- VaR (Value at Risk)
- Correlation exposure

**ML Performance**
- Model accuracy
- Prediction confidence
- Feature importance
- Retraining frequency

### Alert Configuration

#### Email Alerts
```python
# configs/alerts_config.yaml
alerts:
  email:
    enabled: true
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    from_email: "algo.trader@example.com"
    to_emails: ["trader@example.com"]
    
  triggers:
    - event: "position_opened"
      severity: "info"
      template: "New {direction} position: {market} @ {price}"
      
    - event: "stop_loss_hit"
      severity: "warning"
      template: "Stop loss triggered: {market} - Loss: {loss}"
      
    - event: "daily_limit_reached"
      severity: "critical"
      template: "Daily loss limit reached: {amount}"
      
    - event: "system_error"
      severity: "critical"
      template: "System error: {error_message}"
```

#### Slack Integration
```python
# Slack webhook configuration
slack_config = {
    "webhook_url": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
    "channel": "#trading-alerts",
    "username": "AlgoTrader Bot"
}

def send_slack_alert(message, severity="info"):
    color = {"info": "good", "warning": "warning", "critical": "danger"}
    payload = {
        "attachments": [{
            "color": color[severity],
            "text": message,
            "ts": time.time()
        }]
    }
    requests.post(slack_config["webhook_url"], json=payload)
```

## Maintenance

### Daily Tasks

#### Morning Checklist
```bash
# 1. Check system status
systemctl status algo-trader

# 2. Review overnight trades
python scripts/daily_report.py --date yesterday

# 3. Check account balance
python scripts/check_account.py

# 4. Verify data feeds
python scripts/verify_feeds.py

# 5. Review error logs
grep ERROR logs/algo_trader.log | tail -20
```

#### End of Day
```bash
# 1. Generate daily report
python scripts/daily_report.py

# 2. Backup trade data
python scripts/backup_trades.py

# 3. Check tomorrow's calendar
python scripts/economic_calendar.py --date tomorrow

# 4. Verify all positions closed (if required)
python scripts/check_positions.py
```

### Weekly Maintenance

```bash
# 1. Performance analysis
python scripts/weekly_performance.py

# 2. Model performance review
python scripts/model_metrics.py

# 3. Database cleanup
python scripts/cleanup_database.py --older-than 30

# 4. Log rotation
logrotate -f /etc/logrotate.d/algo-trader

# 5. System updates (weekend)
pip install --upgrade -r requirements.txt
```

### Monthly Tasks

```bash
# 1. Full system backup
python scripts/full_backup.py

# 2. Strategy parameter review
python scripts/strategy_analysis.py --period month

# 3. Risk metrics review
python scripts/risk_report.py --period month

# 4. Database optimization
python scripts/optimize_database.py

# 5. Security audit
python scripts/security_audit.py
```

## Backup and Recovery

### Backup Strategy

#### Automated Backups
```bash
# Daily backup script (crontab)
0 2 * * * /opt/algo-trader/scripts/backup.sh

# backup.sh content:
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/algo-trader"

# Backup MongoDB
mongodump --out ${BACKUP_DIR}/mongodb_${DATE}

# Backup configurations
tar -czf ${BACKUP_DIR}/configs_${DATE}.tar.gz configs/

# Backup logs
tar -czf ${BACKUP_DIR}/logs_${DATE}.tar.gz logs/

# Keep only last 30 days
find ${BACKUP_DIR} -mtime +30 -delete
```

#### Manual Backup
```bash
# Full system backup
python scripts/backup.py --full --destination /backup/

# Specific component backup
python scripts/backup.py --component database
python scripts/backup.py --component configs
python scripts/backup.py --component models
```

### Recovery Procedures

#### System Recovery
```bash
# 1. Stop the system
systemctl stop algo-trader

# 2. Restore database
mongorestore --drop /backup/mongodb_20240115/

# 3. Restore configurations
tar -xzf /backup/configs_20240115.tar.gz -C /

# 4. Verify configuration
python scripts/verify_config.py

# 5. Start in demo mode first
python runners/run_multi_market.py --demo --duration 300

# 6. If successful, start production
systemctl start algo-trader
```

#### Position Recovery
```python
# Emergency position recovery
python scripts/recover_positions.py --from-backup

# Manual position reconciliation
python scripts/reconcile_positions.py --with-broker
```

## Performance Optimization

### System Tuning

#### Database Optimization
```bash
# Create indexes
python scripts/create_indexes.py

# Analyze query performance
python scripts/analyze_queries.py

# Compact database
mongo algo_trader --eval "db.runCommand({compact: 'tick_data'})"
```

#### Code Profiling
```bash
# Profile execution
python -m cProfile -o profile.stats runners/run_multi_market.py --demo --duration 3600

# Analyze profile
python -m pstats profile.stats
```

### Resource Management

#### Memory Optimization
```python
# Monitor memory usage
import psutil

process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Garbage collection tuning
import gc
gc.set_threshold(700, 10, 10)
```

#### CPU Optimization
```python
# Use multiprocessing for parallel markets
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(analyze_market, markets)
```

## Troubleshooting Operations

### Common Operational Issues

#### System Won't Start
```bash
# Check for running instances
ps aux | grep run_multi_market

# Check port availability
netstat -tulpn | grep 8080

# Verify configurations
python scripts/verify_config.py

# Check dependencies
pip check
```

#### Data Feed Issues
```bash
# Test Lightstreamer connection
python scripts/test_streaming.py

# Check network connectivity
ping demo-apd.marketdatasystems.com

# Verify subscription status
python scripts/check_subscriptions.py
```

#### Trading Issues
```bash
# Check account status
python scripts/account_status.py

# Verify market hours
python scripts/market_hours.py

# Test order placement (demo)
python scripts/test_order.py --demo
```

## Disaster Recovery

### Emergency Procedures

#### Market Crash
```python
# Emergency market crash response
python scripts/emergency_close.py --all --immediate
```

#### System Failure
```bash
# 1. Stop all trading
python scripts/emergency_stop.py

# 2. Close all positions
python scripts/close_all_positions.py --confirm

# 3. Disable auto-trading
python scripts/disable_trading.py

# 4. Notify team
python scripts/send_alert.py --critical "System failure - trading halted"
```

### Business Continuity

#### Failover Setup
```yaml
# Failover configuration
failover:
  primary_server: "prod-server-1.example.com"
  backup_server: "prod-server-2.example.com"
  
  health_check:
    interval: 60  # seconds
    timeout: 10
    failure_threshold: 3
    
  switch_conditions:
    - "primary_unreachable"
    - "data_feed_lost"
    - "critical_error"
```

#### Disaster Recovery Plan
1. **Detection**: Automated monitoring detects failure
2. **Alert**: Team notified via multiple channels
3. **Assessment**: Determine severity and impact
4. **Response**: Execute appropriate recovery procedure
5. **Recovery**: Restore normal operations
6. **Review**: Post-incident analysis

## Compliance and Auditing

### Trade Auditing
```python
# Generate audit report
python scripts/audit_report.py --period month

# Verify trade records
python scripts/verify_trades.py --with-broker

# Export for compliance
python scripts/export_trades.py --format csv --output trades_202401.csv
```

### Regulatory Compliance
- Maintain trade records for 5 years
- Daily reconciliation with broker
- Regular risk assessments
- Audit trail for all actions

## Security Operations

### Access Control
```bash
# Review access logs
grep "LOGIN" logs/access.log | tail -50

# Check failed authentication
grep "AUTH_FAILED" logs/security.log

# Rotate API keys
python scripts/rotate_api_keys.py
```

### Security Monitoring
```bash
# Check for suspicious activity
python scripts/security_scan.py

# Review firewall rules
sudo iptables -L

# Update security patches
sudo apt-get update && sudo apt-get upgrade
```