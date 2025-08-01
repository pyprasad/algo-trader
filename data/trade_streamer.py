# data/trade_streamer.py

"""
📈 Real-time Trade Streaming Manager

Streams live trade confirmations and position updates from IG API:
- Trade confirmations (CONFIRMS)
- Open position updates (OPU) 
- Working order updates (WOU)
- Local trade storage and management

Author: Multi-Market Trading System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lightstreamer.client import LightstreamerClient, Subscription, SubscriptionListener, ConsoleLoggerProvider, ConsoleLogLevel
from utils.auth_helper import authenticate
from data.db import update_trade_status, trades_collection
from datetime import datetime
import threading
import time

# Set up Lightstreamer logger
logger_provider = ConsoleLoggerProvider(ConsoleLogLevel.INFO)
LightstreamerClient.setLoggerProvider(logger_provider)

class TradeStreamer:
    def __init__(self):
        """Initialize trade streamer"""
        # Get session tokens and endpoint
        self.CST, self.XST, self.LS_ENDPOINT, self.ACCOUNT_ID = authenticate()
        
        # Initialize Lightstreamer client
        self.client = LightstreamerClient(self.LS_ENDPOINT, "DEFAULT")
        self.client.connectionDetails.setUser(self.ACCOUNT_ID)
        self.client.connectionDetails.setPassword(f"CST-{self.CST}|XST-{self.XST}")
        
        self.subscription = None
        self.running = False
        
        # Trade data storage
        self.active_trades = {}
        self.trade_confirmations = []
        
        print(f"📈 Trade streamer initialized for account: {self.ACCOUNT_ID}")
    
    def create_trade_subscription(self):
        """Create subscription for trade data"""
        try:
            # Create trade subscription
            trade_item = f"TRADE:{self.ACCOUNT_ID}"
            
            subscription = Subscription(
                mode="DISTINCT",  # DISTINCT mode for trade updates
                items=[trade_item],
                fields=[
                    # Core trade confirmation fields (confirmed working fields)
                    "CONFIRMS", "OPU", "WOU",
                    "dealId", "dealReference", "dealStatus", "status",
                    "direction", "epic", "level", "size",
                    "stopLevel", "limitLevel", "timestamp"
                ]
            )
            subscription.setRequestedSnapshot("yes")
            
            print(f"📋 Trade subscription details:")
            print(f"   Item: {trade_item}")
            print(f"   Mode: DISTINCT (for trade confirmations)")
            print(f"   Fields: CONFIRMS, OPU, WOU, dealId, dealReference, dealStatus, status, direction, epic, level, size, stopLevel, limitLevel, timestamp")
            
            # Create trade data listener
            class TradeDataListener(SubscriptionListener):
                def __init__(self, streamer):
                    self.streamer = streamer
                    
                def onItemUpdate(self, update):
                    """Handle trade data updates"""
                    try:
                        # Get update type
                        confirms = update.getValue("CONFIRMS")
                        opu = update.getValue("OPU")
                        wou = update.getValue("WOU")
                        
                        if confirms:
                            self._handle_trade_confirmation(update)
                        elif opu:
                            self._handle_position_update(update)
                        elif wou:
                            self._handle_working_order_update(update)
                        else:
                            # General trade update
                            self._handle_general_trade_update(update)
                            
                    except Exception as e:
                        print(f"❌ Error processing trade update: {e}")
                
                def _handle_trade_confirmation(self, update):
                    """Handle trade confirmation (CONFIRMS)"""
                    deal_id = update.getValue("dealId")
                    deal_reference = update.getValue("dealReference")
                    deal_status = update.getValue("dealStatus")
                    direction = update.getValue("direction")
                    epic = update.getValue("epic")
                    level = update.getValue("level")
                    size = update.getValue("size")
                    status = update.getValue("status")
                    
                    print(f"📈 TRADE CONFIRMATION:")
                    print(f"   Deal ID: {deal_id}")
                    print(f"   Reference: {deal_reference}")
                    print(f"   Status: {deal_status}")
                    print(f"   Direction: {direction}")
                    print(f"   Epic: {epic}")
                    print(f"   Level: {level}")
                    print(f"   Size: {size}")
                    print(f"   Position Status: {status}")
                    
                    # Store confirmation
                    confirmation = {
                        "type": "CONFIRMATION",
                        "deal_id": deal_id,
                        "deal_reference": deal_reference,
                        "deal_status": deal_status,
                        "direction": direction,
                        "epic": epic,
                        "level": float(level) if level else None,
                        "size": float(size) if size else None,
                        "status": status,
                        "timestamp": datetime.utcnow()
                    }
                    
                    self.streamer.trade_confirmations.append(confirmation)
                    
                    # Update local database if we have this trade
                    if deal_reference:
                        self._update_local_trade(deal_reference, confirmation)
                
                def _handle_position_update(self, update):
                    """Handle open position update (OPU)"""
                    deal_id = update.getValue("dealId")
                    direction = update.getValue("direction")
                    epic = update.getValue("epic")
                    level = update.getValue("level")
                    size = update.getValue("size")
                    status = update.getValue("status")
                    timestamp = update.getValue("timestamp")
                    
                    print(f"📊 POSITION UPDATE:")
                    print(f"   Deal ID: {deal_id}")
                    print(f"   Direction: {direction}")
                    print(f"   Epic: {epic}")
                    print(f"   Level: {level}")
                    print(f"   Size: {size}")
                    print(f"   Status: {status}")
                    print(f"   Timestamp: {timestamp}")
                    
                    # Update active trades
                    if deal_id:
                        self.streamer.active_trades[deal_id] = {
                            "type": "POSITION_UPDATE",
                            "deal_id": deal_id,
                            "direction": direction,
                            "epic": epic,
                            "level": float(level) if level else None,
                            "size": float(size) if size else None,
                            "status": status,
                            "timestamp": timestamp,
                            "last_update": datetime.utcnow()
                        }
                
                def _handle_working_order_update(self, update):
                    """Handle working order update (WOU)"""
                    deal_id = update.getValue("dealId")
                    direction = update.getValue("direction")
                    epic = update.getValue("epic")
                    level = update.getValue("level")
                    size = update.getValue("size")
                    status = update.getValue("status")
                    order_type = update.getValue("orderType")
                    
                    print(f"📋 WORKING ORDER UPDATE:")
                    print(f"   Deal ID: {deal_id}")
                    print(f"   Direction: {direction}")
                    print(f"   Epic: {epic}")
                    print(f"   Level: {level}")
                    print(f"   Size: {size}")
                    print(f"   Status: {status}")
                    print(f"   Order Type: {order_type}")
                
                def _handle_general_trade_update(self, update):
                    """Handle other trade updates"""
                    deal_id = update.getValue("dealId")
                    status = update.getValue("status")
                    deal_status = update.getValue("dealStatus")
                    
                    if deal_id:
                        print(f"📈 Trade Update - Deal ID: {deal_id}, Status: {status}, Deal Status: {deal_status}")
                
                def _update_local_trade(self, deal_reference, confirmation):
                    """Update local trade in database"""
                    try:
                        # Find trade in database by deal reference
                        trade_query = {"deal_reference": deal_reference}
                        existing_trade = trades_collection.find_one(trade_query)
                        
                        if existing_trade:
                            # Update trade status based on confirmation
                            new_status = "OPEN" if confirmation['deal_status'] == "ACCEPTED" else "REJECTED"
                            
                            update_data = {
                                "deal_status": confirmation['deal_status'],
                                "status": new_status,
                                "confirmation_timestamp": confirmation['timestamp']
                            }
                            
                            if confirmation.get('level'):
                                update_data["actual_entry_price"] = confirmation['level']
                            
                            trades_collection.update_one(
                                {"_id": existing_trade["_id"]},
                                {"$set": update_data}
                            )
                            
                            print(f"💾 Updated local trade {deal_reference}: {new_status}")
                        else:
                            print(f"⚠️ Trade {deal_reference} not found in local database")
                            
                    except Exception as e:
                        print(f"❌ Error updating local trade: {e}")
                        
                def onClearSnapshot(self, itemName, itemPos):
                    print(f"📭 Trade snapshot cleared")
                    
                def onSubscriptionError(self, code, message):
                    print(f"❌ Trade subscription error: {code} - {message}")
                    
                def onSubscription(self):
                    print(f"✅ Successfully subscribed to trade data")
                    
                def onUnsubscription(self):
                    print(f"📤 Unsubscribed from trade data")
            
            subscription.addListener(TradeDataListener(self))
            return subscription
            
        except Exception as e:
            print(f"❌ Failed to create trade subscription: {e}")
            return None
    
    def start_streaming(self):
        """Start streaming trade data"""
        print(f"📡 Starting trade streaming...")
        
        # Create trade subscription
        self.subscription = self.create_trade_subscription()
        if not self.subscription:
            print("❌ Failed to create trade subscription")
            return False
        
        # Connect to Lightstreamer
        try:
            self.client.subscribe(self.subscription)
            self.client.connect()
            self.running = True
            print("🚀 Trade streaming started!")
            return True
        except Exception as e:
            print(f"❌ Failed to start trade streaming: {e}")
            return False
    
    def stop_streaming(self):
        """Stop streaming and cleanup"""
        print("🛑 Stopping trade streaming...")
        self.running = False
        
        if self.subscription:
            self.client.unsubscribe(self.subscription)
            print("📤 Unsubscribed from trade data")
        
        self.client.disconnect()
        print("✅ Trade streaming stopped")
    
    def get_active_trades(self):
        """Get current active trades"""
        return self.active_trades.copy()
    
    def get_trade_confirmations(self, limit=50):
        """Get recent trade confirmations"""
        return self.trade_confirmations[-limit:] if self.trade_confirmations else []
    
    def is_streaming(self):
        """Check if streamer is running"""
        return self.running


# Global trade streamer instance
_global_trade_streamer = None

def get_trade_streamer():
    """Get global trade streamer instance (singleton)"""
    global _global_trade_streamer
    if _global_trade_streamer is None:
        _global_trade_streamer = TradeStreamer()
    return _global_trade_streamer

def start_trade_streaming():
    """Start global trade streaming"""
    streamer = get_trade_streamer()
    return streamer.start_streaming()

def stop_trade_streaming():
    """Stop global trade streaming"""
    global _global_trade_streamer
    if _global_trade_streamer:
        _global_trade_streamer.stop_streaming()
        _global_trade_streamer = None

def get_live_trade_confirmations():
    """Get current live trade confirmations"""
    streamer = get_trade_streamer()
    return streamer.get_trade_confirmations()

def get_live_active_trades():
    """Get all current active trades"""
    streamer = get_trade_streamer()
    return streamer.get_active_trades()


if __name__ == "__main__":
    # Test trade streaming
    print("🧪 Testing Trade Streaming")
    print("=" * 50)
    
    streamer = TradeStreamer()
    
    try:
        streamer.start_streaming()
        
        # Stream for 60 seconds
        print("⏳ Streaming trade data for 60 seconds...")
        time.sleep(60)
        
        # Show confirmations
        confirmations = streamer.get_trade_confirmations()
        print(f"\n📊 Received {len(confirmations)} trade confirmations")
        
        # Show active trades
        active_trades = streamer.get_active_trades()
        print(f"📈 Active trades: {len(active_trades)}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        streamer.stop_streaming()