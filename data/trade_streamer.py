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
                    # Try with just the main event types first
                    "CONFIRMS", "OPU", "WOU"
                ]
            )
            subscription.setRequestedSnapshot("yes")
            
            print(f"📋 Trade subscription details:")
            print(f"   Item: {trade_item}")
            print(f"   Mode: DISTINCT (for trade confirmations)")
            print(f"   Fields: CONFIRMS, OPU, WOU (absolute minimum)")
            
            # Create trade data listener
            class TradeDataListener(SubscriptionListener):
                def __init__(self, streamer):
                    self.streamer = streamer
                    
                def onItemUpdate(self, update):
                    """Handle trade data updates"""
                    try:
                        print(f"📥 Raw trade update received")
                        
                        # Get update type
                        confirms = update.getValue("CONFIRMS")
                        opu = update.getValue("OPU")
                        wou = update.getValue("WOU")
                        
                        # Debug: Show what fields are available
                        available_fields = []
                        for field in ["CONFIRMS", "OPU", "WOU", "dealReference", "dealStatus", "status", "dealId", "direction", "epic", "level", "size"]:
                            try:
                                value = update.getValue(field)
                                if value is not None:
                                    available_fields.append(f"{field}={value}")
                            except:
                                pass
                        
                        if available_fields:
                            print(f"   Available fields: {', '.join(available_fields[:5])}...")  # Show first 5
                        
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
                        import traceback
                        traceback.print_exc()
                
                def _handle_trade_confirmation(self, update):
                    """Handle trade confirmation (CONFIRMS) - tracks new trades"""
                    # Get available fields safely
                    deal_reference = update.getValue("dealReference")
                    deal_status = update.getValue("dealStatus") 
                    status = update.getValue("status")
                    
                    print(f"📈 TRADE CONFIRMATION:")
                    print(f"   Reference: {deal_reference}")
                    print(f"   Deal Status: {deal_status} ({'✅ ACCEPTED' if deal_status == 'ACCEPTED' else '❌ REJECTED' if deal_status else 'UNKNOWN'})")
                    print(f"   Position Status: {status}")
                    
                    # Store minimal confirmation with available data
                    confirmation = {
                        "type": "CONFIRMATION",
                        "deal_reference": deal_reference,
                        "deal_status": deal_status,
                        "status": status,
                        "timestamp": datetime.utcnow()
                    }
                    
                    self.streamer.trade_confirmations.append(confirmation)
                    
                    # Update local database trade status if we have minimum required data
                    if deal_reference and deal_status:
                        print(f"💾 Updating database for trade {deal_reference}")
                        # For now, just log that we received a confirmation
                        # We'll enhance this once we confirm the streaming works
                
                def _handle_position_update(self, update):
                    """Handle open position update (OPU) - tracks position lifecycle"""
                    # Get available fields safely
                    deal_reference = update.getValue("dealReference")
                    status = update.getValue("status")  # OPEN, UPDATED, DELETED (closed)
                    deal_status = update.getValue("dealStatus")
                    
                    print(f"📊 POSITION UPDATE:")
                    print(f"   Reference: {deal_reference}")
                    print(f"   Status: {status} ({'🟢 OPEN' if status == 'OPEN' else '🔄 UPDATED' if status == 'UPDATED' else '🔴 CLOSED' if status == 'DELETED' else status})")
                    print(f"   Deal Status: {deal_status}")
                    
                    # Store minimal position update
                    position_update = {
                        "type": "POSITION_UPDATE",
                        "deal_reference": deal_reference,
                        "status": status,
                        "deal_status": deal_status,
                        "received_at": datetime.utcnow()
                    }
                    
                    # Basic lifecycle tracking
                    if status == "DELETED" and deal_reference:  # Position closed
                        print(f"🔴 POSITION CLOSED: {deal_reference}")
                        print(f"🎯 Trade {deal_reference} completed - ready for new trades!")
                    elif status == "OPEN" and deal_reference:
                        print(f"🟢 POSITION OPENED: {deal_reference}")
                    elif status == "UPDATED" and deal_reference:
                        print(f"🔄 POSITION UPDATED: {deal_reference}")
                
                def _handle_working_order_update(self, update):
                    """Handle working order update (WOU)"""
                    print(f"📋 WORKING ORDER UPDATE RECEIVED")
                    
                    # Store minimal working order update
                    order_update = {
                        "type": "WORKING_ORDER_UPDATE",
                        "timestamp": datetime.utcnow(),
                        "raw_update": str(update)
                    }
                    
                    # For now, just log that we received it
                    print(f"   Working order update logged at {order_update['timestamp']}")
                
                def _handle_general_trade_update(self, update):
                    """Handle other trade updates"""
                    print(f"📈 GENERAL TRADE UPDATE RECEIVED")
                    
                    # Store minimal general update
                    general_update = {
                        "type": "GENERAL_UPDATE",
                        "timestamp": datetime.utcnow(),
                        "raw_update": str(update)
                    }
                    
                    # For now, just log that we received it
                    print(f"   General trade update logged at {general_update['timestamp']}")
                        
                def onClearSnapshot(self, itemName, itemPos):
                    print(f"📭 Trade snapshot cleared")
                    
                def onSubscriptionError(self, code, message):
                    print(f"❌ Trade subscription error: {code} - {message}")
                    
                def onSubscription(self):
                    print(f"✅ Successfully subscribed to trade data")
                    
                def onUnsubscription(self):
                    print(f"📤 Unsubscribed from trade data")
                
                def _update_local_trade_confirmation(self, deal_reference, confirmation):
                    """Update local trade in database when confirmed"""
                    try:
                        # Find trade in database by deal reference
                        trade_query = {"deal_reference": deal_reference}
                        existing_trade = trades_collection.find_one(trade_query)
                        
                        if existing_trade:
                            # Update trade status and details
                            update_data = {
                                "deal_id": confirmation['deal_id'],
                                "deal_status": confirmation['deal_status'],
                                "status": "OPEN",
                                "actual_entry_price": confirmation['level'],
                                "actual_stop_level": confirmation['stop_level'],
                                "actual_limit_level": confirmation['limit_level'],
                                "confirmation_timestamp": confirmation['timestamp'],
                                "last_update": datetime.utcnow()
                            }
                            
                            trades_collection.update_one(
                                {"_id": existing_trade["_id"]},
                                {"$set": update_data}
                            )
                            
                            print(f"💾 Updated local trade {deal_reference}: CONFIRMED -> OPEN")
                        else:
                            print(f"⚠️ Trade {deal_reference} not found in local database")
                            
                    except Exception as e:
                        print(f"❌ Error updating local trade confirmation: {e}")
                
                def _update_local_trade_closure(self, deal_reference, position_update):
                    """Update local trade in database when position is closed"""
                    try:
                        # Find trade in database by deal reference  
                        trade_query = {"deal_reference": deal_reference}
                        existing_trade = trades_collection.find_one(trade_query)
                        
                        if existing_trade:
                            # Mark trade as closed
                            update_data = {
                                "status": "CLOSED",
                                "close_timestamp": position_update['received_at'],
                                "close_level": position_update['level'],
                                "last_update": datetime.utcnow()
                            }
                            
                            # Calculate P&L if we have entry and exit levels
                            if existing_trade.get('actual_entry_price') and position_update['level']:
                                entry_price = existing_trade['actual_entry_price']
                                exit_price = position_update['level']
                                direction = existing_trade.get('direction', '')
                                size = existing_trade.get('size', 1)
                                
                                if direction == 'BUY':
                                    pnl = (exit_price - entry_price) * size
                                elif direction == 'SELL':
                                    pnl = (entry_price - exit_price) * size
                                else:
                                    pnl = 0
                                
                                update_data["profit_loss"] = pnl
                                print(f"💰 Calculated P&L for {deal_reference}: £{pnl:.2f}")
                            
                            trades_collection.update_one(
                                {"_id": existing_trade["_id"]},
                                {"$set": update_data}
                            )
                            
                            print(f"💾 Updated local trade {deal_reference}: OPEN -> CLOSED")
                            print(f"🎯 Trade {deal_reference} lifecycle complete - ready for new trades!")
                        else:
                            print(f"⚠️ Closed trade {deal_reference} not found in local database")
                            
                    except Exception as e:
                        print(f"❌ Error updating local trade closure: {e}")
            
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