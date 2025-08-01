# utils/trading_monitor.py

import sys
import os
from datetime import datetime, timedelta
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import get_open_trades, trades_collection
from utils.market_hours import get_market_status

def get_trading_stats(days_back=7):
    """Get trading statistics for the past N days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get all trades from the past N days
    recent_trades = list(trades_collection.find({
        "timestamp": {"$gte": cutoff_date}
    }).sort("timestamp", -1))
    
    total_trades = len(recent_trades)
    winning_trades = len([t for t in recent_trades if t.get("profit_loss", 0) > 0])
    losing_trades = len([t for t in recent_trades if t.get("profit_loss", 0) < 0])
    
    total_pnl = sum([t.get("profit_loss", 0) for t in recent_trades])
    
    # Calculate win rate
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Get trade distribution by signal type
    buy_trades = len([t for t in recent_trades if t.get("direction") == "BUY"])
    sell_trades = len([t for t in recent_trades if t.get("direction") == "SELL"])
    
    return {
        "period_days": days_back,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "buy_trades": buy_trades,
        "sell_trades": sell_trades,
        "recent_trades": recent_trades[:10]  # Last 10 trades
    }

def print_trading_dashboard():
    """Print a formatted trading dashboard"""
    print("="*60)
    print("📊 ALGO TRADING DASHBOARD")
    print("="*60)
    
    # Market status
    market_status = get_market_status("FTSE")
    status_emoji = "🟢" if market_status["is_open"] else "🔴"
    print(f"{status_emoji} Market Status: {'OPEN' if market_status['is_open'] else 'CLOSED'}")
    print(f"🕐 Current Time: {market_status['current_time']}")
    print(f"📅 Day: {market_status['weekday']}")
    
    if not market_status["is_open"]:
        if market_status["next_open"]:
            print(f"⏰ Next Open: {market_status['next_open']}")
    else:
        if market_status["next_close"]:
            print(f"⏰ Next Close: {market_status['next_close']}")
    
    print("-" * 60)
    
    # Open positions
    open_trades = get_open_trades("FTSE 100")
    print(f"💼 Open Positions: {len(open_trades)}")
    
    if open_trades:
        for i, trade in enumerate(open_trades[:5], 1):  # Show max 5 open trades
            direction = trade.get("direction", "N/A")
            entry_price = trade.get("entry_price", 0)
            timestamp = trade.get("timestamp", datetime.utcnow())
            deal_ref = trade.get("deal_reference", "N/A")
            
            time_str = timestamp.strftime("%m/%d %H:%M") if isinstance(timestamp, datetime) else str(timestamp)
            print(f"  {i}. {direction} @ {entry_price} | {time_str} | Ref: {deal_ref}")
    
    print("-" * 60)
    
    # Trading statistics
    stats = get_trading_stats(7)  # Last 7 days
    print(f"📈 Trading Stats (Last {stats['period_days']} days)")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Win Rate: {stats['win_rate']}% ({stats['winning_trades']}W / {stats['losing_trades']}L)")
    print(f"  Total P&L: {stats['total_pnl']}")
    print(f"  Buy/Sell Ratio: {stats['buy_trades']}B / {stats['sell_trades']}S")
    
    if stats['recent_trades']:
        print("\n🕐 Recent Trades:")
        for trade in stats['recent_trades'][:5]:
            direction = trade.get("direction", "N/A")
            pnl = trade.get("profit_loss", 0)
            timestamp = trade.get("timestamp", datetime.utcnow())
            status = trade.get("status", "UNKNOWN")
            
            time_str = timestamp.strftime("%m/%d %H:%M") if isinstance(timestamp, datetime) else str(timestamp)
            pnl_emoji = "💚" if pnl > 0 else "❌" if pnl < 0 else "⚪"
            print(f"  {pnl_emoji} {direction} | {time_str} | P&L: {pnl} | {status}")
    
    print("="*60)

def export_trading_report(filename=None):
    """Export detailed trading report to JSON file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trading_report_{timestamp}.json"
    
    # Get comprehensive stats
    stats_7d = get_trading_stats(7)
    stats_30d = get_trading_stats(30)
    open_trades = get_open_trades("FTSE 100")
    market_status = get_market_status("FTSE")
    
    report = {
        "generated_at": datetime.utcnow().isoformat(),
        "market_status": market_status,
        "open_positions": len(open_trades),
        "stats_7_days": stats_7d,
        "stats_30_days": stats_30d,
        "open_trades_detail": [
            {
                "direction": t.get("direction"),
                "entry_price": t.get("entry_price"),
                "timestamp": t.get("timestamp").isoformat() if t.get("timestamp") else None,
                "deal_reference": t.get("deal_reference"),
                "size": t.get("size")
            } for t in open_trades
        ]
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"📄 Trading report exported to: {filename}")
    return filename

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export_trading_report()
    else:
        print_trading_dashboard()