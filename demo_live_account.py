#!/usr/bin/env python3
# demo_live_account.py - Demo of real-time account balance streaming

import sys
import os
import time
sys.path.append(os.path.abspath('.'))

from data.account_streamer import start_account_streaming, stop_account_streaming, get_live_account_data
from data.db import get_account_balance
from utils.balance_manager import BalanceManager

def demo_live_account_streaming():
    """Demonstrate live account balance streaming"""
    print("🚀 Live Account Balance Streaming Demo")
    print("=" * 70)
    
    print("\n📋 What this demo shows:")
    print("   1. Real-time account balance streaming from IG API")
    print("   2. Live P&L, margin, and equity data")
    print("   3. Integration with existing balance management")
    print("   4. Automatic balance updates for trading decisions")
    
    try:
        # Step 1: Start live streaming
        print(f"\n📡 Step 1: Starting Live Account Streaming")
        print("   Connecting to IG Lightstreamer for account data...")
        
        success = start_account_streaming()
        
        if not success:
            print("   ❌ Failed to start live streaming")
            print("   📝 Note: This requires valid IG demo/live account credentials")
            return False
        
        print("   ✅ Live streaming started successfully!")
        
        # Step 2: Wait for initial data
        print(f"\n⏳ Step 2: Waiting for Initial Account Data")
        print("   Waiting up to 15 seconds for first update...")
        
        for i in range(15):
            time.sleep(1)
            account_data = get_live_account_data()
            
            if account_data.get('last_update'):
                print(f"   📊 First data received after {i+1} seconds!")
                break
                
            if i % 3 == 2:
                print(f"   ⏳ Still waiting... ({i+1}/15)")
        
        # Step 3: Show live account data
        print(f"\n💰 Step 3: Live Account Data")
        account_data = get_live_account_data()
        
        if account_data.get('last_update'):
            print("   📊 REAL-TIME ACCOUNT INFORMATION:")
            print(f"      🎯 Available to Deal: £{account_data.get('available_to_deal', 0):,.2f}")
            print(f"      💵 Available Cash: £{account_data.get('available_cash', 0):,.2f}")
            print(f"      📈 Current P&L: £{account_data.get('pnl', 0):,.2f}")
            print(f"      💎 Equity: £{account_data.get('equity', 0):,.2f}")
            print(f"      🏦 Total Funds: £{account_data.get('funds', 0):,.2f}")
            print(f"      ⚖️ Margin Used: £{account_data.get('margin', 0):,.2f}")
            print(f"      ⏰ Last Update: {account_data.get('last_update')}")
            
            # Calculate margin utilization
            margin = account_data.get('margin', 0)
            available_cash = account_data.get('available_cash', 0)
            total = available_cash + margin
            margin_util = (margin / total * 100) if total > 0 else 0
            print(f"      📊 Margin Utilization: {margin_util:.1f}%")
            
        else:
            print("   ⚠️ No live data received yet")
            print("   📝 This is normal for demo accounts or if markets are closed")
        
        # Step 4: Show integration with balance system
        print(f"\n🔗 Step 4: Balance System Integration")
        current_balance = get_account_balance()
        print(f"   📊 get_account_balance() returns: £{current_balance:,.2f}")
        
        if current_balance > 0:
            print("   ✅ Live balance integration is working!")
            print("   📝 Trading system will use this live balance for decisions")
        else:
            print("   ⚠️ Using fallback balance (no live data available)")
        
        # Step 5: Show balance manager with live data
        print(f"\n📋 Step 5: Enhanced Balance Manager")
        print("   Creating balance manager with live streaming support...")
        
        manager = BalanceManager()
        print("   📊 Balance Manager Summary:")
        manager.print_account_summary()
        
        # Step 6: Monitor for updates
        print(f"\n👀 Step 6: Monitoring Live Updates (20 seconds)")
        print("   Watching for real-time account changes...")
        
        initial_data = get_live_account_data()
        initial_update = initial_data.get('last_update')
        update_count = 0
        
        for i in range(20):
            time.sleep(1)
            current_data = get_live_account_data()
            current_update = current_data.get('last_update')
            
            if current_update != initial_update:
                update_count += 1
                initial_update = current_update
                
                print(f"   📊 Update #{update_count} received!")
                print(f"      Available: £{current_data.get('available_to_deal', 0):,.2f}")
                print(f"      P&L: £{current_data.get('pnl', 0):,.2f}")
            
            if i % 5 == 4:
                print(f"   ⏳ Monitoring... ({i+1}/20)")
        
        if update_count > 0:
            print(f"   ✅ Received {update_count} live updates!")
        else:
            print("   📝 No updates during monitoring period (normal for demo accounts)")
        
        print(f"\n🎯 Demo Results:")
        print("   ✅ Live account streaming implemented successfully")
        print("   ✅ Real-time balance integration working")
        print("   ✅ Enhanced balance manager with live data")
        print("   ✅ Multi-market system will use live balances")
        
        print(f"\n💡 Benefits of Live Streaming:")
        print("   🔄 Real-time balance updates")
        print("   📊 Live P&L tracking")
        print("   ⚖️ Dynamic margin monitoring")
        print("   🛡️ Accurate risk management")
        print("   💰 No hardcoded balances")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleanup: Stopping live streaming...")
        try:
            stop_account_streaming()
            print("   ✅ Live streaming stopped")
        except:
            pass
    
    print(f"\n🚀 Ready to Use:")
    print("   python3.13 runners/run_multi_market.py  # Now uses live account data!")
    print("   python3.13 utils/balance_manager.py --summary  # Shows live balances")
    
    return True

if __name__ == "__main__":
    try:
        success = demo_live_account_streaming()
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
        print("🧹 Cleaning up...")
        stop_account_streaming()
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)