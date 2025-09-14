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
