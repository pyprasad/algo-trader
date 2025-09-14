#!/bin/bash
# deploy_server.sh - Quick server deployment script

echo "🚀 AUTONOMOUS TRADING SYSTEM - SERVER DEPLOYMENT"
echo "================================================"

# Set deployment variables
TRADER_USER="trader"
PROJECT_DIR="/home/$TRADER_USER/algo-trader"
PYTHON_VERSION="python3.12"

echo "📋 Deployment Configuration:"
echo "   User: $TRADER_USER"
echo "   Directory: $PROJECT_DIR"
echo "   Python: $PYTHON_VERSION"
echo "   Architecture: One Trader Per Market"
echo ""

# Function to create DAX trader service
create_dax_trader_service() {
    echo "🎯 Creating DAX Trader Service..."
    
    # Create run script
    cat > run_dax_trader.sh << 'EOF'
#!/bin/bash
cd /home/trader/algo-trader
source venv/bin/activate

echo "🚀 DAX Autonomous Trader Starting..."
echo "Time: $(date)"
echo "Market: DAX | Strategy: SuperTrend Improved | Size: 0.5%"
echo "=============================================="

python3.12 runners/autonomous_master.py \
    --config configs/autonomous_config.yaml \
    --strategy supertrend_improved \
    --timeframe 10min \
    --market DAX \
    --no-dashboard \
    2>&1 | tee logs/dax_trader_$(date +%Y%m%d_%H%M%S).log
EOF
    
    chmod +x run_dax_trader.sh
    echo "   ✅ DAX trader script created"
}

# Function to create monitoring script
create_monitoring() {
    echo "🔍 Creating Monitoring System..."
    
    cat > monitor_system.sh << 'EOF'
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
EOF

    chmod +x monitor_system.sh
    echo "   ✅ Monitoring script created"
}

# Function to create emergency controls
create_emergency_controls() {
    echo "🚨 Creating Emergency Controls..."
    
    cat > emergency_stop.sh << 'EOF'
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
EOF

    chmod +x emergency_stop.sh
    echo "   ✅ Emergency stop script created"
}

# Main deployment
echo "🔧 Creating Deployment Scripts..."
create_dax_trader_service
create_monitoring  
create_emergency_controls

echo ""
echo "✅ DEPLOYMENT SCRIPTS CREATED"
echo "=============================="
echo ""
echo "📋 MANUAL DEPLOYMENT STEPS ON YOUR SERVER:"
echo ""
echo "1. Copy this entire folder to your server:"
echo "   scp -r algo-trader/ user@your-server:/home/trader/"
echo ""
echo "2. On your server, run setup:"
echo "   cd /home/trader/algo-trader"
echo "   python3.12 -m venv venv"
echo "   source venv/bin/activate" 
echo "   pip install pandas numpy pyyaml scikit-learn requests python-dateutil"
echo ""
echo "3. Create required directories:"
echo "   mkdir -p logs results models/autonomous_models backups"
echo ""
echo "4. Configure email alerts in configs/autonomous_config.yaml"
echo ""
echo "5. Start DAX trader:"
echo "   ./run_dax_trader.sh"
echo ""
echo "🔍 MONITORING COMMANDS:"
echo "   ./monitor_system.sh     # Check status"
echo "   ./emergency_stop.sh     # Emergency stop"
echo ""
echo "📊 LIVE TRADING COMMAND:"
echo "   ./run_dax_trader.sh &   # Run in background"
echo ""
echo "⚠️  IMPORTANT: Start with demo mode and monitor for 1 week before live trading!"
echo ""
echo "📧 Don't forget to configure email alerts in autonomous_config.yaml"