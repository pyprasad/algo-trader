# data/collector.py

from lightstreamer.client import LightstreamerClient, Subscription, SubscriptionListener, ConsoleLoggerProvider, ConsoleLogLevel
from utils.auth_helper import authenticate
from data.db import log_tick

# Set up Lightstreamer logger
logger_provider = ConsoleLoggerProvider(ConsoleLogLevel.INFO)
LightstreamerClient.setLoggerProvider(logger_provider)

# Get session tokens and endpoint
CST, XST, LS_ENDPOINT, ACCOUNT_ID = authenticate()

# Initialize Lightstreamer client
client = LightstreamerClient(LS_ENDPOINT, "DEFAULT")
client.connectionDetails.setUser(ACCOUNT_ID)
client.connectionDetails.setPassword(f"CST-{CST}|XST-{XST}")

# Market EPIC (e.g., FTSE100 Daily)
EPIC = "IX.D.FTSE.DAILY.IP"

# Subscribe to live tick updates
subscription = Subscription(
    mode="MERGE",
    items=[f"MARKET:{EPIC}"],
    fields=["BID", "OFFER", "HIGH", "LOW", "UPDATE_TIME", "CHANGE"]
)
subscription.setRequestedSnapshot("yes")

class MarketTickListener(SubscriptionListener):
    def onItemUpdate(self, update):
        bid = update.getValue("BID")
        offer = update.getValue("OFFER")
        update_time = update.getValue("UPDATE_TIME")
        print(f"📈 Tick: {update_time} | Bid: {bid} | Offer: {offer}")
        if bid and offer:
            log_tick("FTSE 100", float(bid), float(offer))

subscription.addListener(MarketTickListener())

# Connect and subscribe
def start_streaming():
    print(f"📡 Connecting to Lightstreamer @ {LS_ENDPOINT}")
    client.subscribe(subscription)
    client.connect()
