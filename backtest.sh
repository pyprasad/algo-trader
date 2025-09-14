#!/bin/bash
# backtest.sh - Simple backtesting command

echo "📊 HISTORICAL BACKTESTING"
echo "========================="

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: ./backtest.sh [data_file]"
    echo ""
    echo "Examples:"
    echo "  ./backtest.sh                           # Test all available data"
    echo "  ./backtest.sh tick_dax_08_18.json      # Test specific file"
    echo "  ./backtest.sh tick_ftse_100_*.json     # Test FTSE files"
    echo ""
    echo "Available data files:"
    ls -1 tick_*.json 2>/dev/null || echo "   No tick data files found"
    exit 0
fi

# Set up environment
source venv/bin/activate 2>/dev/null || echo "⚠️  Virtual environment not found"

if [ $# -eq 0 ]; then
    # Run comprehensive backtest
    echo "🔍 Running comprehensive backtest on all available data..."
    python3.12 runners/historical_backtest.py
else
    # Run FIXED backtest on specific files
    echo "🔍 Running FIXED backtest on: $*"
    echo "✅ Position Size: 0.5% (FIXED from 2% bug)"
    echo "✅ Strategy: MA Crossover optimized"
    echo "✅ Timeframe: 10min candles"
    python3.12 backtest_improved.py "$@"
fi

echo ""
echo "✅ Backtesting complete!"
echo "📁 Results saved in results/ directory"