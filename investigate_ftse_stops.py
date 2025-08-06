#!/usr/bin/env python3
"""
Investigation Script: FTSE Stop Limits & Dynamic Trading
Analyzes database records and system status to identify issues
"""

import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from data.db import trades_collection, db
from core.dynamic_position_manager import get_dynamic_position_manager
from core.trade_executor import get_market_details
from utils.config_loader import load_global_config, load_asset_config
import traceback

def investigate_ftse_stops():
    """Check recent FTSE trades for stop_loss values"""
    print("=== INVESTIGATING FTSE STOP LIMITS ===")
    
    try:
        # Get recent FTSE trades (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        ftse_trades = list(trades_collection.find({
            "market": {"$in": ["FTSE 100", "FTSE100", "FTSE"]},
            "timestamp": {"$gte": week_ago}
        }).sort("timestamp", -1).limit(20))
        
        print(f"\n📊 Found {len(ftse_trades)} recent FTSE trades")
        
        if not ftse_trades:
            print("❌ No recent FTSE trades found in database")
            return
        
        # Analyze stop_loss values
        trades_with_stops = 0
        trades_without_stops = 0
        stop_values = []
        
        print("\n🔍 FTSE Trade Analysis:")
        print("-" * 80)
        
        for i, trade in enumerate(ftse_trades[:10]):  # Show first 10
            trade_time = trade.get('timestamp', 'Unknown')
            market = trade.get('market', 'Unknown')
            direction = trade.get('direction', 'Unknown')
            stop_loss = trade.get('stop_loss', None)
            take_profit = trade.get('take_profit', None)
            status = trade.get('deal_status', trade.get('status', 'Unknown'))
            
            if stop_loss is not None:
                trades_with_stops += 1
                stop_values.append(stop_loss)
                stop_status = f"✅ {stop_loss} pips"
            else:
                trades_without_stops += 1
                stop_status = "❌ NO STOP"
            
            tp_status = f"✅ {take_profit} pips" if take_profit is not None else "❌ NO TP"
            
            print(f"{i+1:2d}. {trade_time} | {market} {direction} | Stop: {stop_status} | TP: {tp_status} | Status: {status}")
        
        # Summary statistics
        print("\n📈 FTSE STOP LIMIT SUMMARY:")
        print(f"   Trades with stops: {trades_with_stops}/{len(ftse_trades)} ({trades_with_stops/len(ftse_trades)*100:.1f}%)")
        print(f"   Trades without stops: {trades_without_stops}/{len(ftse_trades)} ({trades_without_stops/len(ftse_trades)*100:.1f}%)")
        
        if stop_values:
            avg_stop = sum(stop_values) / len(stop_values)
            print(f"   Average stop distance: {avg_stop:.1f} pips")
            print(f"   Stop range: {min(stop_values):.1f} - {max(stop_values):.1f} pips")
        
        return trades_with_stops, trades_without_stops, stop_values
        
    except Exception as e:
        print(f"❌ Error investigating FTSE stops: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        return 0, 0, []

def check_dax_comparison():
    """Compare DAX trades to see if they have stops"""
    print("\n=== COMPARING WITH DAX TRADES ===")
    
    try:
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        dax_trades = list(trades_collection.find({
            "market": {"$in": ["DAX", "Germany 40", "GER30"]},
            "timestamp": {"$gte": week_ago}
        }).sort("timestamp", -1).limit(10))
        
        print(f"\n📊 Found {len(dax_trades)} recent DAX trades")
        
        if not dax_trades:
            print("❌ No recent DAX trades found")
            return
        
        dax_with_stops = 0
        dax_without_stops = 0
        
        print("\n🔍 DAX Trade Analysis (First 5):")
        print("-" * 60)
        
        for i, trade in enumerate(dax_trades[:5]):
            trade_time = trade.get('timestamp', 'Unknown')
            market = trade.get('market', 'Unknown')
            direction = trade.get('direction', 'Unknown')
            stop_loss = trade.get('stop_loss', None)
            
            if stop_loss is not None:
                dax_with_stops += 1
                stop_status = f"✅ {stop_loss} pips"
            else:
                dax_without_stops += 1
                stop_status = "❌ NO STOP"
            
            print(f"{i+1}. {trade_time} | {market} {direction} | Stop: {stop_status}")
        
        print(f"\n📈 DAX STOP COMPARISON:")
        print(f"   DAX trades with stops: {dax_with_stops}/{len(dax_trades)} ({dax_with_stops/len(dax_trades)*100:.1f}%)")
        
        return dax_with_stops, dax_without_stops
        
    except Exception as e:
        print(f"❌ Error checking DAX trades: {e}")
        return 0, 0

def check_dynamic_trading_status():
    """Verify dynamic trading is working for both markets"""
    print("\n=== DYNAMIC TRADING STATUS CHECK ===")
    
    try:
        # Check dynamic position manager
        dpm = get_dynamic_position_manager()
        status = dpm.get_status()
        
        print(f"\n🚀 Dynamic Position Manager:")
        print(f"   Enabled: {status.get('enabled', False)}")
        print(f"   Running: {status.get('running', False)}")
        print(f"   Positions Managed: {status.get('positions_managed', 0)}")
        print(f"   Update Interval: {status.get('update_interval', 'Unknown')}s")
        
        # Check adjustment history
        try:
            history = dpm.get_adjustment_history()
            print(f"   Total Adjustments Made: {len(history)}")
            
            if history:
                print(f"\n📊 Recent Adjustments (Last 5):")
                for i, adj in enumerate(history[-5:]):
                    timestamp = adj.get('timestamp', 'Unknown')
                    market = adj.get('market', 'Unknown')
                    action = adj.get('action', 'Unknown')
                    print(f"   {i+1}. {timestamp} | {market} | {action}")
        except Exception as e:
            print(f"   ⚠️ Could not get adjustment history: {e}")
        
        # Check emergency protection status
        print(f"\n🛡️ Emergency Protection:")
        print(f"   Emergency Enabled: {getattr(dpm, 'emergency_enabled', 'Unknown')}")
        print(f"   Loss Threshold: {getattr(dpm, 'immediate_loss_threshold', 'Unknown')} pips")
        
        return status
        
    except Exception as e:
        print(f"❌ Error checking dynamic trading: {e}")
        print(f"Stack trace: {traceback.format_exc()}")
        return {}

def check_market_configurations():
    """Check current market configurations for stops"""
    print("\n=== MARKET CONFIGURATION CHECK ===")
    
    try:
        # Global config
        global_config = load_global_config()
        print(f"\n🌍 Global Configuration:")
        print(f"   Stop Loss Pips: {global_config['strategy']['stop_loss_pips']}")
        print(f"   Take Profit Pips: {global_config['strategy']['take_profit_pips']}")
        print(f"   Dynamic ATR SL/TP: {global_config['strategy']['dynamic_atr_sltp']}")
        
        # Market-specific configs
        markets = ["FTSE 100", "DAX"]
        for market in markets:
            try:
                print(f"\n📊 {market} Configuration:")
                
                # Try to load asset config
                try:
                    asset_config = load_asset_config(market)
                    print(f"   Epic: {asset_config.get('epic', 'Not found')}")
                    print(f"   Trade Size: {asset_config.get('trade_size', 'Not found')}")
                except Exception as e:
                    print(f"   ⚠️ Asset config error: {e}")
                
                # Check if we can get market details
                try:
                    if market == "FTSE 100":
                        epic = "IX.D.FTSE.DAILY.IP"  # Common FTSE epic
                    else:  # DAX
                        epic = "IX.D.DAX.DAILY.IP"   # Common DAX epic
                    
                    details = get_market_details(epic)
                    print(f"   Market Status: {details.get('marketStatus', 'Unknown')}")
                    print(f"   Min Distance: {details.get('minDistance', 'Unknown')} pips")
                    print(f"   Margin Requirement: {details.get('marginRequirement', 'Unknown')}%")
                    
                except Exception as e:
                    print(f"   ⚠️ Market details error: {e}")
                    
            except Exception as e:
                print(f"   ❌ Configuration error for {market}: {e}")
        
    except Exception as e:
        print(f"❌ Error checking configurations: {e}")

def main():
    """Run complete investigation"""
    print("=" * 80)
    print("FTSE STOP LIMITS & DYNAMIC TRADING INVESTIGATION")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Phase 1: Database analysis
    ftse_with_stops, ftse_without_stops, stop_values = investigate_ftse_stops()
    dax_with_stops, dax_without_stops = check_dax_comparison()
    
    # Phase 2: Dynamic trading check
    dynamic_status = check_dynamic_trading_status()
    
    # Phase 3: Configuration verification
    check_market_configurations()
    
    # Phase 4: Summary and recommendations
    print("\n" + "=" * 80)
    print("🎯 INVESTIGATION SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    # FTSE stops analysis
    if ftse_with_stops == 0 and ftse_without_stops > 0:
        print("🚨 CRITICAL ISSUE: FTSE trades have NO stop limits")
        print("   Recommendation: Fix trade execution logic for FTSE")
    elif ftse_without_stops > ftse_with_stops:
        print("⚠️ PARTIAL ISSUE: Many FTSE trades missing stops")
        print("   Recommendation: Investigate intermittent stop placement failures")
    else:
        print("✅ FTSE stops appear to be working correctly")
    
    # Dynamic trading analysis
    if dynamic_status.get('enabled') and dynamic_status.get('running'):
        print("✅ Dynamic trading is ACTIVE for both markets")
    elif dynamic_status.get('enabled'):
        print("⚠️ Dynamic trading ENABLED but not running - needs restart")
    else:
        print("❌ Dynamic trading is DISABLED")
    
    # Final recommendations
    print(f"\n🎯 NEXT STEPS:")
    if ftse_without_stops > 0:
        print("   1. 🔧 Fix FTSE stop limit placement in trade_executor.py")
        print("   2. 🧪 Test stop placement with paper trades")
        print("   3. 📊 Monitor next few FTSE trades for proper stops")
    
    if not (dynamic_status.get('enabled') and dynamic_status.get('running')):
        print("   4. 🚀 Restart dynamic position manager")
        print("   5. ✅ Verify dynamic trading activates for both markets")
    
    print("   6. 📈 Continue monitoring system performance")
    
    return {
        'ftse_stops_working': ftse_with_stops > ftse_without_stops,
        'dynamic_trading_active': dynamic_status.get('enabled') and dynamic_status.get('running'),
        'issues_found': ftse_without_stops > 0 or not (dynamic_status.get('enabled') and dynamic_status.get('running'))
    }

if __name__ == "__main__":
    results = main()
    
    if results['issues_found']:
        print(f"\n🚨 ISSUES DETECTED - Manual intervention recommended")
        sys.exit(1)
    else:
        print(f"\n✅ All systems appear to be working correctly")
        sys.exit(0)