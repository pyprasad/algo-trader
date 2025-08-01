# data/multi_market_collector.py

from lightstreamer.client import LightstreamerClient, Subscription, SubscriptionListener, ConsoleLoggerProvider, ConsoleLogLevel
from utils.auth_helper import authenticate
from utils.config_loader import load_asset_config
from data.db import log_tick

# Set up Lightstreamer logger
logger_provider = ConsoleLoggerProvider(ConsoleLogLevel.INFO)
LightstreamerClient.setLoggerProvider(logger_provider)

# Get session tokens and endpoint
CST, XST, LS_ENDPOINT, ACCOUNT_ID = authenticate()

class MultiMarketCollector:
    def __init__(self, markets_list):
        """
        Initialize multi-market collector
        
        Args:
            markets_list (list): List of market names to track (e.g., ['AAPL', 'GOOGL', 'FTSE 100'])
        """
        self.markets = markets_list
        self.client = LightstreamerClient(LS_ENDPOINT, "DEFAULT")
        self.client.connectionDetails.setUser(ACCOUNT_ID)
        self.client.connectionDetails.setPassword(f"CST-{CST}|XST-{XST}")
        self.subscriptions = {}
        self.running = False
        
    def create_market_subscription(self, market_name):
        """Create subscription for a specific market"""
        try:
            asset_config = load_asset_config(market_name)
            
            if not asset_config:
                print(f"❌ No configuration found for market: {market_name}")
                return None
                
            if "epic" not in asset_config:
                print(f"❌ Missing 'epic' field in configuration for market: {market_name}")
                print(f"   Available fields: {list(asset_config.keys())}")
                return None
                
            epic = asset_config["epic"]
            print(f"🔗 Creating subscription for {market_name} with epic: {epic}")
            
            subscription = Subscription(
                mode="MERGE",
                items=[f"MARKET:{epic}"],
                fields=["BID", "OFFER", "HIGH", "LOW", "UPDATE_TIME", "CHANGE"]
            )
            subscription.setRequestedSnapshot("yes")
            
            print(f"📋 Subscription details for {market_name}:")
            print(f"   Mode: MERGE")
            print(f"   Items: MARKET:{epic}")
            print(f"   Fields: BID, OFFER, HIGH, LOW, UPDATE_TIME, CHANGE")
            
            # Create market-specific listener
            class MarketTickListener(SubscriptionListener):
                def __init__(self, market_name):
                    self.market_name = market_name
                    
                def onItemUpdate(self, update):
                    bid = update.getValue("BID")
                    offer = update.getValue("OFFER")
                    
                    if bid and offer:
                        try:
                            log_tick(self.market_name, float(bid), float(offer))
                        except ValueError as e:
                            print(f"❌ Error logging tick for {self.market_name}: {e}")
                            
                def onClearSnapshot(self, itemName, itemPos):
                    print(f"📭 Snapshot cleared for {self.market_name}")
                    
                def onCommandSecondLevelItemLostUpdates(self, lostUpdates, key):
                    print(f"⚠️ Lost updates for {self.market_name}: {lostUpdates}")
                    
                def onCommandSecondLevelSubscriptionError(self, code, message, key):
                    print(f"❌ Subscription error for {self.market_name}: {code} - {message}")
                    
                def onEndOfSnapshot(self, itemName, itemPos):
                    print(f"📸 End of snapshot for {self.market_name}")
                    
                def onItemLostUpdates(self, itemName, itemPos, lostUpdates):
                    print(f"⚠️ Item lost updates for {self.market_name}: {lostUpdates}")
                    
                def onSubscriptionError(self, code, message):
                    print(f"❌ Subscription error for {self.market_name}: {code} - {message}")
                    
                def onSubscription(self):
                    print(f"✅ Successfully subscribed to {self.market_name}")
                    
                def onUnsubscription(self):
                    print(f"📤 Unsubscribed from {self.market_name}")
            
            subscription.addListener(MarketTickListener(market_name))
            return subscription
            
        except Exception as e:
            print(f"❌ Failed to create subscription for {market_name}: {e}")
            return None
    
    def start_streaming(self):
        """Start streaming data for all configured markets"""
        print(f"📡 Connecting to Lightstreamer @ {LS_ENDPOINT}")
        print(f"📊 Starting multi-market streaming for: {', '.join(self.markets)}")
        
        # Create subscriptions for all markets
        for market_name in self.markets:
            subscription = self.create_market_subscription(market_name)
            if subscription:
                self.subscriptions[market_name] = subscription
                self.client.subscribe(subscription)
                print(f"🎯 Subscribed to {market_name}")
            else:
                print(f"⚠️ Failed to subscribe to {market_name}")
        
        # Connect to Lightstreamer
        self.client.connect()
        self.running = True
        print("🚀 Multi-market streaming started!")
        
    def stop_streaming(self):
        """Stop streaming and cleanup"""
        print("🛑 Stopping multi-market streaming...")
        self.running = False
        
        # Unsubscribe from all markets
        for market_name, subscription in self.subscriptions.items():
            self.client.unsubscribe(subscription)
            print(f"📤 Unsubscribed from {market_name}")
        
        # Disconnect client
        self.client.disconnect()
        print("✅ Multi-market streaming stopped")
    
    def add_market(self, market_name):
        """Dynamically add a new market to streaming"""
        if market_name not in self.markets:
            subscription = self.create_market_subscription(market_name)
            if subscription and self.running:
                self.subscriptions[market_name] = subscription
                self.client.subscribe(subscription)
                self.markets.append(market_name)
                print(f"➕ Added {market_name} to streaming")
            else:
                print(f"❌ Failed to add {market_name}")
        else:
            print(f"⚠️ {market_name} already being tracked")
    
    def remove_market(self, market_name):
        """Dynamically remove a market from streaming"""
        if market_name in self.markets:
            if market_name in self.subscriptions:
                self.client.unsubscribe(self.subscriptions[market_name])
                del self.subscriptions[market_name]
            self.markets.remove(market_name)
            print(f"➖ Removed {market_name} from streaming")
        else:
            print(f"⚠️ {market_name} not currently tracked")
    
    def get_streaming_markets(self):
        """Get list of currently streaming markets"""
        return self.markets.copy()
    
    def is_running(self):
        """Check if collector is running"""
        return self.running


def start_multi_market_streaming(markets_list):
    """
    Convenience function to start multi-market streaming
    
    Args:
        markets_list (list): List of market names to track
        
    Returns:
        MultiMarketCollector: The collector instance
    """
    collector = MultiMarketCollector(markets_list)
    collector.start_streaming()
    return collector


if __name__ == "__main__":
    # Example usage - stream multiple markets
    markets_to_track = ["AAPL", "GOOGL", "FTSE 100"]
    
    collector = start_multi_market_streaming(markets_to_track)
    
    try:
        input("🛑 Press Enter to stop streaming...\n")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        collector.stop_streaming()