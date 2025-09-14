#!/bin/bash

echo "🔍 AUTONOMOUS TRADING SYSTEM STATUS"
echo "Time: $(date)"
echo "=================================="

# Check if trader is running
if pgrep -f "autonomous_master.py" > /dev/null; then
    echo "✅ DAX Trader: RUNNING"
    
    # Show recent performance
    echo ""
    echo "📊 Recent Activity:"
    tail -n 10 logs/dax_trader_*.log | grep -E "(TRADE|P&L|Balance|Alert)" | tail -5
    
else
    echo "❌ DAX Trader: STOPPED"
fi

echo ""
echo "💾 System Resources:"
echo "   Disk: $(df -h . | tail -1 | awk '{print $5}') used"
echo "   Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "   Uptime: $(uptime | awk '{print $3,$4}' | sed 's/,//')"

echo ""
echo "📁 Recent Logs:"
ls -lt logs/ | head -5
