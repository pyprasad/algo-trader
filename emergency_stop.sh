#!/bin/bash
echo "🚨 EMERGENCY STOP ACTIVATED"
echo "Time: $(date)"

# Kill all autonomous trading processes
pkill -f "autonomous_master.py"

# Check if stopped
sleep 2
if ! pgrep -f "autonomous_master.py" > /dev/null; then
    echo "✅ All traders stopped successfully"
else
    echo "⚠️  Some processes may still be running"
    ps aux | grep autonomous_master
fi

echo ""
echo "📊 Final Status Check:"
./monitor_system.sh
