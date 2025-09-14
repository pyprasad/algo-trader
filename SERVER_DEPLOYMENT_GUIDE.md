# 🖥️ SERVER DEPLOYMENT GUIDE - AUTONOMOUS TRADING SYSTEM

## 🎯 DEPLOYMENT ARCHITECTURE

### **Single Trader Per Market Design**
```
Server
├── DAX Trader (Primary) - SuperTrend Improved
├── FTSE Trader (Future) - When DAX proves profitable
└── Risk Manager (Global) - Monitors all traders
```

**Why One Trader Per Market?**
- ✅ **Risk Isolation**: Losses in one market don't affect others
- ✅ **Resource Management**: Dedicated processing per market
- ✅ **Strategy Optimization**: Each trader optimized for specific market
- ✅ **Monitoring Clarity**: Easy to track performance per market
- ✅ **Scaling Control**: Add markets gradually as system proves itself

## 🚀 SERVER SETUP INSTRUCTIONS

### **1. SERVER PREPARATION**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-pip -y

# Install system dependencies
sudo apt install git curl wget htop screen tmux -y

# Create trading user (optional but recommended)
sudo adduser trader
sudo usermod -aG sudo trader
su - trader
```

### **2. PROJECT DEPLOYMENT**

```bash
# Clone your repository
git clone <your-repo-url> algo-trader
cd algo-trader

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install pandas numpy pyyaml scikit-learn requests python-dateutil

# Create required directories
mkdir -p logs results models/autonomous_models backups data

# Set permissions
chmod +x runners/*.py
```

### **3. CONFIGURATION SETUP**

```bash
# Copy and edit the main configuration
cp configs/autonomous_config.yaml configs/production_config.yaml

# Edit for production settings
nano configs/production_config.yaml
```

**Production Configuration Changes:**
```yaml
# configs/production_config.yaml
autonomous_engine:
  trading:
    enabled: true
    max_simultaneous_positions: 1  # One position per trader
    position_size_percent: 0.5     # Very conservative
    
risk_management:
  daily_limits:
    max_trades: 3                  # Conservative limit
    max_loss_amount: 100           # £100 daily loss limit
    
  emergency_controls:
    max_consecutive_losses: 3      # Stop after 3 losses
    max_drawdown_percent: 5.0      # 5% max drawdown
    
monitoring:
  alerts:
    email_enabled: true           # Enable email alerts
    max_daily_loss: 100           # Alert threshold
    
  notifications:
    console_enabled: true
    file_logging: true

# Email configuration (fill in your details)
email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  username: "your-email@gmail.com"
  password: "your-app-password"
  from_email: "trading-bot@yourdomain.com"
  to_email: "alerts@yourdomain.com"
```

### **4. DAX TRADER DEPLOYMENT (Primary)**

Create the DAX trader service:

```bash
# Create DAX trader script
cat > ~/algo-trader/run_dax_trader.sh << 'EOF'
#!/bin/bash

# DAX Autonomous Trader Service
cd /home/trader/algo-trader
source venv/bin/activate

echo "🚀 Starting DAX Autonomous Trader..."
echo "Time: $(date)"
echo "Config: Production Mode"
echo "Market: DAX"
echo "Strategy: SuperTrend Improved"
echo "Position Size: 0.5%"
echo "================================"

# Run the autonomous trader
python3.12 runners/autonomous_master.py \
    --config configs/production_config.yaml \
    --strategy supertrend_improved \
    --timeframe 10min \
    --market DAX \
    --demo-mode \
    --position-size 0.5 \
    --daily-limit 100 \
    2>&1 | tee logs/dax_trader_$(date +%Y%m%d).log

echo "DAX Trader stopped at $(date)"
EOF

chmod +x run_dax_trader.sh
```

### **5. SYSTEM SERVICE SETUP**

Create systemd service for automatic startup:

```bash
# Create service file
sudo tee /etc/systemd/system/dax-trader.service > /dev/null << 'EOF'
[Unit]
Description=DAX Autonomous Trading Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=trader
Group=trader
WorkingDirectory=/home/trader/algo-trader
ExecStart=/home/trader/algo-trader/run_dax_trader.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONPATH=/home/trader/algo-trader
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable dax-trader.service
```

### **6. MONITORING SETUP**

```bash
# Create monitoring script
cat > ~/algo-trader/monitor_traders.sh << 'EOF'
#!/bin/bash

echo "🔍 AUTONOMOUS TRADING SYSTEM STATUS"
echo "=================================="
echo "Time: $(date)"
echo ""

# Check DAX trader service
echo "📊 DAX TRADER STATUS:"
sudo systemctl status dax-trader.service --no-pager -l

echo ""
echo "💰 RECENT PERFORMANCE:"
tail -n 20 logs/dax_trader_$(date +%Y%m%d).log | grep -E "(P&L|Balance|TRADE|ALERT)"

echo ""
echo "🚨 RECENT ALERTS:"
tail -n 10 logs/autonomous_monitoring.log | grep -E "(WARNING|CRITICAL|EMERGENCY)"

echo ""
echo "📈 DISK USAGE:"
df -h /home/trader/algo-trader

echo ""
echo "🖥️ SYSTEM RESOURCES:"
free -h
uptime
EOF

chmod +x monitor_traders.sh
```

### **7. DEPLOYMENT COMMANDS**

#### **Start DAX Trader (Manual)**
```bash
cd ~/algo-trader
./run_dax_trader.sh
```

#### **Start DAX Trader (Service)**
```bash
sudo systemctl start dax-trader.service
```

#### **Monitor Trader**
```bash
# Check status
sudo systemctl status dax-trader.service

# View live logs
sudo journalctl -u dax-trader.service -f

# Run monitoring script
./monitor_traders.sh
```

#### **Emergency Stop**
```bash
# Stop service
sudo systemctl stop dax-trader.service

# Or kill process
pkill -f "autonomous_master.py"
```

### **8. DAILY OPERATIONS**

#### **Morning Routine** (Recommended: 8 AM London time)
```bash
cd ~/algo-trader

# Check overnight performance
./monitor_traders.sh

# Check for alerts
tail -n 50 logs/autonomous_monitoring.log

# Restart trader if needed
sudo systemctl restart dax-trader.service
```

#### **Evening Routine** (Recommended: 6 PM London time)
```bash
# Generate daily report
python3.12 -c "
from core.monitoring_system import AutonomousMonitoringSystem
monitor = AutonomousMonitoringSystem()
report = monitor.get_performance_report()
print('📊 DAILY SUMMARY:', report)
"

# Check positions and P&L
./monitor_traders.sh

# Backup logs
cp logs/dax_trader_$(date +%Y%m%d).log backups/
```

## 🔧 ADVANCED DEPLOYMENT OPTIONS

### **Multi-Market Deployment** (When Ready)
```bash
# After DAX proves successful for 1 month, add FTSE trader

# Create FTSE trader script
cat > run_ftse_trader.sh << 'EOF'
#!/bin/bash
cd /home/trader/algo-trader
source venv/bin/activate

python3.12 runners/autonomous_master.py \
    --config configs/production_config.yaml \
    --strategy ma_crossover_dynamic \
    --timeframe 10min \
    --market FTSE_100 \
    --demo-mode \
    --position-size 0.5 \
    --daily-limit 100 \
    2>&1 | tee logs/ftse_trader_$(date +%Y%m%d).log
EOF

# Create FTSE service
sudo tee /etc/systemd/system/ftse-trader.service > /dev/null << 'EOF'
[Unit]
Description=FTSE Autonomous Trading Bot
After=network.target

[Service]
Type=simple
User=trader
ExecStart=/home/trader/algo-trader/run_ftse_trader.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ftse-trader.service
```

### **Load Balancer Setup** (For Multiple Markets)
```bash
# Install nginx for load balancing (future web interface)
sudo apt install nginx -y

# Configure nginx for trading dashboard
sudo tee /etc/nginx/sites-available/trading-dashboard << 'EOF'
server {
    listen 8080;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/trading-dashboard /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## 🚨 EMERGENCY PROCEDURES

### **Emergency Stop All Traders**
```bash
#!/bin/bash
# Save as emergency_stop.sh

echo "🚨 EMERGENCY STOP INITIATED"
sudo systemctl stop dax-trader.service
sudo systemctl stop ftse-trader.service
pkill -f "autonomous_master.py"
echo "✅ All traders stopped"
./monitor_traders.sh
```

### **Recovery Procedures**
```bash
#!/bin/bash
# Save as recovery_start.sh

echo "🔄 RECOVERY STARTUP"
sudo systemctl start dax-trader.service
sleep 10
./monitor_traders.sh
echo "✅ Recovery complete"
```

## 📊 PERFORMANCE MONITORING

### **Key Metrics to Monitor Daily:**
- Daily P&L per trader
- Win rate trends
- System uptime
- Alert frequency
- Resource usage

### **Weekly Review:**
- Compare performance vs targets
- Analyze strategy effectiveness
- Review risk metrics
- Plan parameter adjustments

## 🔐 SECURITY CONSIDERATIONS

```bash
# Firewall setup
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8080  # For future web dashboard

# Secure log files
chmod 640 logs/*.log
chown trader:trader logs/*.log

# Automated backups
echo "0 2 * * * /home/trader/algo-trader/backup_system.sh" | crontab -
```

---

## 🚀 QUICK START CHECKLIST

- [ ] Server prepared with Python 3.12
- [ ] Repository cloned and dependencies installed
- [ ] Production config created and email configured
- [ ] DAX trader script created and tested
- [ ] System service configured and enabled
- [ ] Monitoring scripts setup
- [ ] Emergency procedures documented
- [ ] Daily operations scheduled

**Ready to deploy with:** `sudo systemctl start dax-trader.service`

---

*This creates a single DAX trader that can run 24/7 with full monitoring and emergency controls.*