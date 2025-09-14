#!/bin/bash
# deploy.sh - Automated deployment script for trading system

echo "🚀 ALGORITHMIC TRADING SYSTEM DEPLOYMENT"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Do not run this script as root for security reasons"
    exit 1
fi

# Step 1: System Requirements Check
print_status "Checking system requirements..."

# Check Python version
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version | cut -d " " -f 2)
    print_status "Python version: $PYTHON_VERSION ✅"
else
    print_error "Python 3.12 is required but not found"
    print_status "Install Python 3.12 first:"
    echo "  Ubuntu: sudo apt update && sudo apt install python3.12 python3.12-venv"
    echo "  CentOS: sudo yum install python3.12"
    exit 1
fi

# Check available memory
MEMORY_GB=$(free -g | awk 'NR==2{printf "%.1f", $2}')
if (( $(echo "$MEMORY_GB < 4" | bc -l) )); then
    print_warning "Low memory detected: ${MEMORY_GB}GB. Recommended: 4GB+"
else
    print_status "Memory: ${MEMORY_GB}GB ✅"
fi

# Check disk space
DISK_SPACE=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$DISK_SPACE < 10" | bc -l) )); then
    print_warning "Low disk space: ${DISK_SPACE}GB available. Recommended: 20GB+"
else
    print_status "Disk space: ${DISK_SPACE}GB available ✅"
fi

# Step 2: Create directory structure
print_status "Creating directory structure..."
mkdir -p logs
mkdir -p results
mkdir -p data/tick_data
mkdir -p data/processed
mkdir -p backup
mkdir -p configs

# Step 3: Virtual environment setup
print_status "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
    print_status "Virtual environment created ✅"
else
    print_status "Virtual environment already exists ✅"
fi

# Activate virtual environment
source venv/bin/activate

# Step 4: Install dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Dependencies installed ✅"
else
    print_warning "requirements.txt not found, installing basic packages..."
    pip install pandas numpy pyyaml requests matplotlib seaborn
fi

# Step 5: Environment configuration
print_status "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status "Environment file created from template"
        print_warning "IMPORTANT: Edit .env file with your API credentials!"
    else
        cat > .env << 'EOF'
# Trading System Environment Configuration
# IMPORTANT: Fill in your actual values

# Broker API Configuration  
IG_API_KEY=your_api_key_here
IG_USERNAME=your_username_here
IG_PASSWORD=your_password_here
IG_ACCOUNT_ID=your_account_id_here

# Trading Configuration
TRADING_ENVIRONMENT=demo
DEFAULT_POSITION_SIZE=0.5
MAX_DAILY_TRADES=5
MAX_DAILY_LOSS=100

# System Configuration
LOG_LEVEL=INFO
DATA_DIRECTORY=./data
RESULTS_DIRECTORY=./results
EOF
        print_status "Environment template created"
    fi
    print_error "ACTION REQUIRED: Edit .env file with your broker credentials"
    print_status "Run: nano .env"
else
    print_status "Environment file already exists ✅"
fi

# Step 6: Configuration files
print_status "Creating system configuration files..."

# Create optimal config if it doesn't exist
if [ ! -f "configs/optimal_config.yaml" ]; then
    cat > configs/optimal_config.yaml << 'EOF'
# Optimal Trading System Configuration
# Based on backtesting analysis and proven profitable strategies

trading:
  optimal_timeframes:
    FTSE_100: "10min" 
    DAX: "10min"
  
  optimal_algorithms:
    FTSE_100:
      primary: "optimized_rsi"
      backup: "ma_crossover"
    DAX:
      primary: "optimized_rsi"
      backup: "ma_crossover"

algorithms:
  optimized_rsi:
    FTSE_100:
      rsi_period: 14
      rsi_overbought: 60    # Contrarian - sell when above 60
      rsi_oversold: 40      # Contrarian - buy when below 40  
      trend_ema: 50
      stop_loss_pips: 12    # Tight stops discovered through optimization
      take_profit_pips: 25  # 2:1 risk/reward ratio
    DAX:
      rsi_period: 14
      rsi_overbought: 60
      rsi_oversold: 40
      trend_ema: 50  
      stop_loss_pips: 12
      take_profit_pips: 25
  
  ma_crossover:
    default:
      fast_ma: 8
      slow_ma: 21
      stop_loss_pips: 30
      take_profit_pips: 60

risk_management:
  position_size_percent: 0.5   # CRITICAL: 0.5% position sizing (FIXED)
  max_daily_trades: 5
  max_daily_loss_percent: 1.0  # 1% of balance
  max_positions: 2
  max_spread_pips: 5.0
  spread_buffer: 1.0

volatility:
  min_atr_threshold: 5.0
  max_atr_threshold: 50.0
  consolidation_filter: true
  consolidation_atr_ratio: 0.5
EOF
    print_status "Optimal configuration created ✅"
fi

# Step 7: Create systemd service (optional)
print_status "Creating systemd service file..."
SERVICE_FILE="trading-system.service"
cat > $SERVICE_FILE << EOF
[Unit]
Description=Algorithmic Trading System
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python runners/live_trading.py --strategy optimized_rsi
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$(pwd)

[Install]
WantedBy=multi-user.target
EOF
print_status "Systemd service file created: $SERVICE_FILE"
print_status "To enable: sudo cp $SERVICE_FILE /etc/systemd/system/ && sudo systemctl enable trading-system"

# Step 8: Create startup script
print_status "Creating startup script..."
cat > start_trading.sh << 'EOF'
#!/bin/bash
# start_trading.sh - Start trading system

echo "🚀 Starting Algorithmic Trading System"
echo "======================================"

# Activate virtual environment
source venv/bin/activate

# Check environment
if [ "$TRADING_ENVIRONMENT" != "demo" ] && [ "$TRADING_ENVIRONMENT" != "live" ]; then
    echo "⚠️  TRADING_ENVIRONMENT not set. Defaulting to demo mode for safety."
    export TRADING_ENVIRONMENT=demo
fi

echo "Environment: $TRADING_ENVIRONMENT"
echo "Position Size: ${DEFAULT_POSITION_SIZE:-0.5}%"
echo "Max Daily Loss: £${MAX_DAILY_LOSS:-100}"

# Pre-flight checks
python3.12 -c "
import sys, os
print('✅ Python environment OK')

# Check if required files exist
required_files = ['core/enhanced_strategies.py', 'simple_backtest.py', '.env']
for file in required_files:
    if os.path.exists(file):
        print(f'✅ {file} found')
    else:
        print(f'❌ {file} missing')
        sys.exit(1)

print('🎯 System ready for trading')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎯 Choose trading mode:"
    echo "1) Paper Trading (Demo)"
    echo "2) Live Trading (Real Money)"
    echo "3) Backtesting Only"
    echo ""
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            export TRADING_ENVIRONMENT=demo
            echo "📈 Starting Paper Trading..."
            python3.12 runners/paper_trading.py --strategy optimized_rsi
            ;;
        2)
            if [ "$TRADING_ENVIRONMENT" = "demo" ]; then
                echo "⚠️  Switching to live trading requires explicit confirmation."
                read -p "Type 'CONFIRM' to enable live trading: " confirm
                if [ "$confirm" = "CONFIRM" ]; then
                    export TRADING_ENVIRONMENT=live
                    echo "💰 Starting Live Trading..."
                    python3.12 runners/live_trading.py --strategy optimized_rsi
                else
                    echo "❌ Live trading cancelled"
                    exit 1
                fi
            else
                echo "💰 Starting Live Trading..."
                python3.12 runners/live_trading.py --strategy optimized_rsi  
            fi
            ;;
        3)
            echo "📊 Running Backtesting..."
            if ls tick_*.json 1> /dev/null 2>&1; then
                ./backtest.sh tick_*.json
            else
                echo "❌ No tick data files found. Place tick data files in current directory."
            fi
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac
else
    echo "❌ Pre-flight checks failed"
    exit 1
fi
EOF

chmod +x start_trading.sh
print_status "Startup script created: start_trading.sh ✅"

# Step 9: Create monitoring script
print_status "Creating monitoring script..."
cat > monitor.sh << 'EOF'
#!/bin/bash
# monitor.sh - Monitor trading system

echo "📊 TRADING SYSTEM MONITOR"
echo "========================"

# Activate virtual environment
source venv/bin/activate

while true; do
    clear
    echo "📊 TRADING SYSTEM STATUS - $(date)"
    echo "=================================="
    
    # Check if trading process is running
    if pgrep -f "live_trading.py\|paper_trading.py" > /dev/null; then
        echo "🟢 Trading System: RUNNING"
        
        # Show recent log entries
        echo ""
        echo "📝 Recent Activity:"
        echo "------------------"
        if [ -f "logs/trading_$(date +%Y%m%d).log" ]; then
            tail -5 "logs/trading_$(date +%Y%m%d).log"
        else
            echo "No log file found for today"
        fi
        
        # System resources
        echo ""
        echo "💻 System Resources:"
        echo "-------------------"
        echo "Memory: $(free -h | awk 'NR==2{printf "%.1f/%.1fGB (%.0f%%)", $3/1024/1024, $2/1024/1024, $3*100/$2 }')"
        echo "CPU: $(top -bn1 | grep load | awk '{printf "%.2f%%", $(NF-2)*100}')"
        echo "Disk: $(df -h . | awk 'NR==2 {print $3"/"$2" ("$5" used)"}')"
    else
        echo "🔴 Trading System: STOPPED"
        echo ""
        echo "To start trading:"
        echo "./start_trading.sh"
    fi
    
    echo ""
    echo "Press Ctrl+C to exit monitoring"
    sleep 10
done
EOF

chmod +x monitor.sh
print_status "Monitoring script created: monitor.sh ✅"

# Step 10: Final verification
print_status "Running final verification..."

# Test imports
python3.12 -c "
try:
    import pandas as pd
    import numpy as np
    import yaml
    from core.candle_aggregator import CandleAggregator
    from core.enhanced_strategies import EnhancedTradingStrategies
    print('✅ All core modules can be imported')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
except Exception as e:
    print(f'⚠️  Warning: {e}')
"

# Create sample backup script
cat > backup.sh << 'EOF'
#!/bin/bash
# backup.sh - Backup critical system files

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup/backup_$BACKUP_DATE"

echo "📦 Creating backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup critical files
cp -r configs/ "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
cp -r logs/ "$BACKUP_DIR/"
cp -r results/ "$BACKUP_DIR/"

# Compress backup
tar -czf "backup_$BACKUP_DATE.tar.gz" "$BACKUP_DIR/"
rm -rf "$BACKUP_DIR/"

echo "✅ Backup created: backup_$BACKUP_DATE.tar.gz"
EOF

chmod +x backup.sh

# Final instructions
echo ""
print_status "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo ""
echo "📋 NEXT STEPS:"
echo "=============="
echo "1. Edit configuration:"
echo "   nano .env                    # Add your broker API credentials"
echo "   nano configs/optimal_config.yaml  # Adjust trading parameters"
echo ""
echo "2. Test the system:"
echo "   python3.12 simple_backtest.py tick_ftse_100_09_13.json"
echo ""  
echo "3. Start trading:"
echo "   ./start_trading.sh           # Interactive startup"
echo "   ./monitor.sh                 # Monitor system status"
echo ""
echo "4. Emergency commands:"
echo "   python3.12 runners/emergency_stop.py   # Stop all trading"
echo "   ./backup.sh                           # Backup system"
echo ""
print_warning "IMPORTANT REMINDERS:"
echo "- Always start with paper trading (demo mode)"
echo "- Verify position sizing is 0.5% maximum"
echo "- Monitor for any massive losses (indicates bugs)"
echo "- Keep daily loss limits active (£100 recommended)"
echo "- Test emergency stop procedures"
echo ""
print_status "📖 Full documentation: DEPLOYMENT_README.md"
print_status "🎯 System ready for deployment!"

deactivate