#!/usr/bin/env python3
# test_account_streaming.py - Test real-time account balance streaming

import sys
import os
import time
sys.path.append(os.path.abspath('.'))

from data.account_streamer import AccountBalanceStreamer, start_account_streaming, stop_account_streaming, get_live_account_data
from data.db import get_account_balance

def test_account_streaming():
    """Test account balance streaming functionality"""
    print("🧪 Testing Real-time Account Balance Streaming")
    print("=" * 70)
    
    try:
        # Test 1: Create streamer instance
        print("\n📊 Step 1: Creating Account Streamer")
        streamer = AccountBalanceStreamer()
        print(f"   ✅ Streamer created for account: {streamer.ACCOUNT_ID}")
        
        # Test 2: Start streaming
        print("\n📡 Step 2: Starting Account Streaming")
        success = streamer.start_streaming()
        
        if not success:
            print("   ❌ Failed to start account streaming")
            return False
        
        print("   ✅ Account streaming started successfully")
        
        # Test 3: Wait for initial data
        print("\n⏳ Step 3: Waiting for Account Data (30 seconds)")
        for i in range(30):
            time.sleep(1)
            account_data = streamer.get_account_data()
            
            if account_data.get('last_update'):
                print(f"   📊 Data received after {i+1} seconds!")
                break
            
            if i % 5 == 4:  # Every 5 seconds
                print(f"   ⏳ Waiting... ({i+1}/30)")
        
        # Test 4: Display account data
        print(f"\n💰 Step 4: Current Account Data")
        account_data = streamer.get_account_data()
        
        if account_data.get('last_update'):
            print(f"   📈 Available to Deal: £{account_data.get('available_to_deal', 0):,.2f}")
            print(f"   💵 Available Cash: £{account_data.get('available_cash', 0):,.2f}")
            print(f"   📊 Current P&L: £{account_data.get('pnl', 0):,.2f}")
            print(f"   💎 Equity: £{account_data.get('equity', 0):,.2f}")
            print(f"   🏦 Funds: £{account_data.get('funds', 0):,.2f}")
            print(f"   ⚖️ Margin Used: £{account_data.get('margin', 0):,.2f}")
            print(f"   ⏰ Last Update: {account_data.get('last_update')}")
            
            # Test margin utilization calculation
            margin_util = streamer.get_margin_utilization()
            print(f"   📈 Margin Utilization: {margin_util:.1f}%")
            
        else:
            print("   ⚠️ No account data received yet")
        
        # Test 5: Test database integration
        print(f"\n💾 Step 5: Testing Database Integration")
        db_balance = get_account_balance()
        live_balance = streamer.get_available_balance()
        
        print(f"   Database Balance: £{db_balance:,.2f}")
        print(f"   Live Stream Balance: £{live_balance:,.2f}")
        
        if live_balance > 0:
            print("   ✅ Live balance integration working")
        else:
            print("   ⚠️ Live balance not available")
        
        # Test 6: Monitor for additional updates
        print(f"\n👀 Step 6: Monitoring for Updates (15 seconds)")
        initial_update_time = account_data.get('last_update')
        
        for i in range(15):
            time.sleep(1)
            current_data = streamer.get_account_data()
            current_update_time = current_data.get('last_update')
            
            if current_update_time != initial_update_time:
                print(f"   📊 Account data updated after {i+1} seconds!")
                print(f"   💰 New Available to Deal: £{current_data.get('available_to_deal', 0):,.2f}")
                break
            
            if i % 5 == 4:
                print(f"   ⏳ Monitoring... ({i+1}/15)")
        
        print(f"\n✅ Account streaming test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print(f"\n🧹 Cleanup: Stopping account streaming...")
        try:
            streamer.stop_streaming()
            print("   ✅ Streaming stopped")
        except:
            pass
    
    return True

def test_global_streaming():
    """Test global streaming functions"""
    print("\n🧪 Testing Global Account Streaming Functions")
    print("=" * 70)
    
    try:
        # Test global start
        print("\n📡 Starting global account streaming...")
        success = start_account_streaming()
        
        if success:
            print("✅ Global streaming started")
            
            # Wait for data
            time.sleep(10)
            
            # Test global data access
            account_data = get_live_account_data()
            if account_data.get('last_update'):
                print(f"💰 Global account data: £{account_data.get('available_to_deal', 0):,.2f}")
            
            # Test global stop
            print("🛑 Stopping global streaming...")
            stop_account_streaming()
            print("✅ Global streaming stopped")
            
        else:
            print("❌ Global streaming failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Global streaming test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 Real-time Account Balance Streaming Test Suite")
        print("=" * 80)
        
        # Test individual streamer
        success1 = test_account_streaming()
        
        # Test global functions  
        success2 = test_global_streaming()
        
        print("\n" + "=" * 80)
        if success1 and success2:
            print("🎉 All account streaming tests passed!")
            print("\n💡 Usage:")
            print("   python3.13 runners/run_multi_market.py  # Uses live streaming")
            print("   python3.13 utils/balance_manager.py --summary  # Shows live data")
        else:
            print("❌ Some tests failed. Check the output above.")
        
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)