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
