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
