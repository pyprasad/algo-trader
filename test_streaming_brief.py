#!/usr/bin/env python3
# test_streaming_brief.py - Brief test of multi-market streaming

import sys
import os
import time
import threading
sys.path.append(os.path.abspath('.'))

from utils.market_config_loader import MarketConfigLoader
from data.multi_market_collector import MultiMarketCollector

def test_brief_streaming():
    """Test streaming for a short period"""
    print("🧪 Testing Multi-Market Streaming (15 seconds)")
    print("=" * 60)
    
    # Load configuration
    config_loader = MarketConfigLoader()
    valid_markets, invalid_markets = config_loader.validate_active_markets()
    
    if invalid_markets:
        print(f"⚠️ Invalid markets: {invalid_markets}")
    
    if not valid_markets:
        print("❌ No valid markets configured!")
        return False
    
    print(f"📊 Testing markets: {valid_markets}")
    
    # Create collector
    collector = MultiMarketCollector(valid_markets)
    
    # Start streaming in a separate thread
    def stream_data():
        try:
            collector.start_streaming()
        except Exception as e:
            print(f"❌ Streaming error: {e}")
    
    streaming_thread = threading.Thread(target=stream_data)
    streaming_thread.daemon = True
    streaming_thread.start()
    
    # Let it run for 15 seconds
    print("⏳ Streaming for 15 seconds...")
    time.sleep(15)
    
    # Stop streaming
    print("🛑 Stopping streaming...")
    collector.stop_streaming()
    
    print("✅ Brief streaming test completed!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_brief_streaming()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)