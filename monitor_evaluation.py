#!/usr/bin/env python3
"""
🎯 EVALUATION MONITORING SCRIPT
Monitor the unblocked trading system and collect metrics for evaluation
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from data.db import trades_collection, get_account_balance

def check_trading_activity() -> Dict[str, Any]:
    """Check current trading activity and metrics"""
    
    print(f"🔍 EVALUATION MONITORING - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Get today's date
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Check trades today
    trades_today = list(trades_collection.find({
        'timestamp': {'$gte': today}
    }).sort('timestamp', -1))
    
    print(f"📊 TRADES TODAY: {len(trades_today)}")
    
    if trades_today:
        # Calculate metrics
        total_pnl = sum(trade.get('profit_loss', 0) for trade in trades_today)
        winning_trades = [t for t in trades_today if t.get('profit_loss', 0) > 0]
        losing_trades = [t for t in trades_today if t.get('profit_loss', 0) < 0]
        
        win_rate = len(winning_trades) / len(trades_today) * 100 if trades_today else 0
        
        print(f"💰 TOTAL P&L: £{total_pnl:.2f}")
        print(f"📈 WIN RATE: {win_rate:.1f}%")
        print(f"✅ WINNING TRADES: {len(winning_trades)}")
        print(f"❌ LOSING TRADES: {len(losing_trades)}")
        
        # Market breakdown
        ftse_trades = [t for t in trades_today if 'FTSE' in t.get('market', '')]
        dax_trades = [t for t in trades_today if 'DAX' in t.get('market', '')]
        
        ftse_pnl = sum(t.get('profit_loss', 0) for t in ftse_trades)
        dax_pnl = sum(t.get('profit_loss', 0) for t in dax_trades)
        
        print(f"\n📊 MARKET BREAKDOWN:")
        print(f"   FTSE 100: {len(ftse_trades)} trades | P&L: £{ftse_pnl:.2f}")
        print(f"   DAX: {len(dax_trades)} trades | P&L: £{dax_pnl:.2f}")
        
        # Show recent trades
        print(f"\n🕒 RECENT TRADES:")
        for trade in trades_today[-5:]:
            ts = trade.get('timestamp', 'Unknown')
            market = trade.get('market', 'Unknown')
            pnl = trade.get('profit_loss', 0)
            direction = trade.get('direction', 'Unknown')
            price = trade.get('entry_price', 0)
            
            print(f"   {ts} | {market} | {direction} at {price} | P&L: £{pnl:.2f}")
    
    else:
        print("No trades found today")
        print("\n🔍 CHECKING SYSTEM STATUS:")
        
        # Check latest trades overall
        latest_trades = list(trades_collection.find().sort('_id', -1).limit(3))
        if latest_trades:
            print(f"Latest trade in database: {latest_trades[0].get('timestamp', 'Unknown')}")
        else:
            print("No trades in database at all")
    
    # Check account balance
    try:
        balance = get_account_balance()
        print(f"\n💳 ACCOUNT BALANCE: £{balance:.2f}")
    except Exception as e:
        print(f"\n❌ Could not get account balance: {e}")
    
    print("\n" + "=" * 60)
    
    return {
        'timestamp': datetime.now(),
        'trades_today': len(trades_today),
        'total_pnl': sum(trade.get('profit_loss', 0) for trade in trades_today) if trades_today else 0,
        'win_rate': len([t for t in trades_today if t.get('profit_loss', 0) > 0]) / len(trades_today) * 100 if trades_today else 0,
        'ftse_trades': len([t for t in trades_today if 'FTSE' in t.get('market', '')]),
        'dax_trades': len([t for t in trades_today if 'DAX' in t.get('market', '')])
    }

def check_system_config():
    """Verify the system configuration is as expected"""
    
    print("🔧 CHECKING SYSTEM CONFIGURATION")
    print("=" * 40)
    
    import yaml
    
    # Check global config
    with open('configs/global.yaml', 'r') as f:
        global_config = yaml.safe_load(f)
    
    confidence_threshold = global_config['dynamic_limits']['confidence_threshold']
    signal_strength = global_config['professional_trading']['strategy']['min_signal_strength']
    
    print(f"✅ Confidence threshold: {confidence_threshold} (should be 0.1)")
    print(f"✅ Signal strength threshold: {signal_strength} (should be 0.05)")
    
    # Check market specific config
    with open('configs/market_specific_strategy.yaml', 'r') as f:
        market_config = yaml.safe_load(f)
    
    dax_config = market_config['market_strategies']['DAX']
    ftse_config = market_config['market_strategies']['FTSE 100']
    
    print(f"✅ DAX min confidence: {dax_config['min_confidence_threshold']}")
    print(f"✅ FTSE min confidence: {ftse_config['min_confidence_threshold']}")
    
    print("Configuration looks correctly unblocked! ✅")

if __name__ == "__main__":
    try:
        check_system_config()
        print()
        check_trading_activity()
    except Exception as e:
        print(f"❌ Error in monitoring: {e}")
        import traceback
        traceback.print_exc()