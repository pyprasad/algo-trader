#!/bin/bash
# scripts/start_trading.sh
# Startup script for the algorithmic trading system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"

echo -e "${BLUE}🚀 Starting Algorithmic Trading System${NC}"
echo "📂 Project Directory: $PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}❌ Virtual environment not found at $VENV_DIR${NC}"
    echo "Please create and activate virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if MongoDB is running
if ! pgrep -x "mongod" > /dev/null; then
    echo -e "${YELLOW}⚠️  MongoDB not detected. Starting MongoDB...${NC}"
    # Attempt to start MongoDB (adjust command based on your system)
    if command -v brew &> /dev/null; then
        brew services start mongodb-community
    elif command -v systemctl &> /dev/null; then
        sudo systemctl start mongod
    else
        echo -e "${RED}❌ Please start MongoDB manually${NC}"
        exit 1
    fi
    sleep 3
fi

# Check MongoDB connection
echo -e "${BLUE}🔍 Checking MongoDB connection...${NC}"
if ! $PYTHON -c "
import sys
sys.path.append('$PROJECT_DIR')
from pymongo import MongoClient
import yaml

with open('$PROJECT_DIR/configs/global.yaml', 'r') as f:
    config = yaml.safe_load(f)

try:
    client = MongoClient(config['mongodb']['uri'])
    client.admin.command('ping')
    print('✅ MongoDB connection successful')
except Exception as e:
    print(f'❌ MongoDB connection failed: {e}')
    sys.exit(1)
"; then
    echo -e "${RED}❌ MongoDB connection check failed${NC}"
    exit 1
fi

# Show current trading dashboard
echo -e "${BLUE}📊 Current Trading Status:${NC}"
$PYTHON "$PROJECT_DIR/utils/trading_monitor.py"

# Ask user which mode to run
echo ""
echo -e "${YELLOW}Select trading mode:${NC}"
echo "1. Single Strategy Run (test)"
echo "2. Continuous Trading (live)"
echo "3. Monitor Only (dashboard)"
echo "4. Export Trading Report"

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}🧪 Running single strategy test...${NC}"
        $PYTHON "$PROJECT_DIR/runners/run_strategy.py"
        ;;
    2)
        echo -e "${GREEN}🔄 Starting continuous trading...${NC}"
        echo -e "${YELLOW}⚠️  Press Ctrl+C to stop gracefully${NC}"
        $PYTHON "$PROJECT_DIR/runners/run_continuous.py"
        ;;
    3)
        echo -e "${GREEN}📊 Monitoring mode - refreshing every 30s${NC}"
        echo -e "${YELLOW}⚠️  Press Ctrl+C to exit${NC}"
        while true; do
            clear
            $PYTHON "$PROJECT_DIR/utils/trading_monitor.py"
            sleep 30
        done
        ;;
    4)
        echo -e "${GREEN}📄 Exporting trading report...${NC}"
        $PYTHON "$PROJECT_DIR/utils/trading_monitor.py" export
        ;;
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac