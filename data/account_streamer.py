# data/account_streamer.py

"""
💰 Real-time Account Balance Streamer

Streams live account information from IG API including:
- Available cash to trade
- Profit/Loss
- Margin requirements
- Equity and balance

Author: Multi-Market Trading System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lightstreamer.client import LightstreamerClient, Subscription, SubscriptionListener, ConsoleLoggerProvider, ConsoleLogLevel
from utils.auth_helper import authenticate
from data.db import update_account_balance
from datetime import datetime
import threading
import time

# Set up Lightstreamer logger
logger_provider = ConsoleLoggerProvider(ConsoleLogLevel.INFO)
LightstreamerClient.setLoggerProvider(logger_provider)

class AccountBalanceStreamer:
    def __init__(self):
        """Initialize account balance streamer"""
        # Get session tokens and endpoint
        self.CST, self.XST, self.LS_ENDPOINT, self.ACCOUNT_ID = authenticate()
        
        # Initialize Lightstreamer client
        self.client = LightstreamerClient(self.LS_ENDPOINT, "DEFAULT")
        self.client.connectionDetails.setUser(self.ACCOUNT_ID)
        self.client.connectionDetails.setPassword(f"CST-{self.CST}|XST-{self.XST}")
        
        self.subscription = None
        self.running = False
        self.last_balance_update = None
        
        # Account data storage
        self.account_data = {
            'available_cash': 0.0,
            'pnl': 0.0,
            'margin': 0.0,
            'equity': 0.0,
            'funds': 0.0,
            'available_to_deal': 0.0,
            'last_update': None
        }
        
        print(f"💰 Account streamer initialized for account: {self.ACCOUNT_ID}")
    
    def create_account_subscription(self):
        """Create subscription for account balance data"""
        try:
            # Create account subscription
            account_item = f"ACCOUNT:{self.ACCOUNT_ID}"
            
            subscription = Subscription(
                mode="MERGE",
                items=[account_item],
                fields=[
                    "PNL", "DEPOSIT", "AVAILABLE_CASH", "PNL_LR", "PNL_NLR",
                    "FUNDS", "MARGIN", "MARGIN_LR", "MARGIN_NLR", 
                    "AVAILABLE_TO_DEAL", "EQUITY", "EQUITY_USED"
                ]
            )
            subscription.setRequestedSnapshot("yes")
            
            print(f"📋 Account subscription details:")
            print(f"   Item: {account_item}")
            print(f"   Fields: PNL, AVAILABLE_CASH, FUNDS, MARGIN, EQUITY, etc.")
            
            # Create account data listener
            class AccountDataListener(SubscriptionListener):
                def __init__(self, streamer):
                    self.streamer = streamer
                    
                def onItemUpdate(self, update):
                    """Handle account data updates"""
                    try:
                        # Extract account data
                        available_cash = update.getValue("AVAILABLE_CASH")
                        pnl = update.getValue("PNL")
                        margin = update.getValue("MARGIN")
                        margin_lr = update.getValue("MARGIN_LR")
                        margin_nlr = update.getValue("MARGIN_NLR")
                        equity = update.getValue("EQUITY")
                        equity_used = update.getValue("EQUITY_USED")
                        funds = update.getValue("FUNDS")
                        available_to_deal = update.getValue("AVAILABLE_TO_DEAL")
                        
                        # Update account data
                        if available_cash:
                            self.streamer.account_data['available_cash'] = float(available_cash)
                        if pnl:
                            self.streamer.account_data['pnl'] = float(pnl)
                        if margin:
                            self.streamer.account_data['margin'] = float(margin)
                        if margin_lr:
                            self.streamer.account_data['margin_lr'] = float(margin_lr)
                        if margin_nlr:
                            self.streamer.account_data['margin_nlr'] = float(margin_nlr)
                        if equity:
                            self.streamer.account_data['equity'] = float(equity)
                        if equity_used:
                            self.streamer.account_data['equity_used'] = float(equity_used)
                        if funds:
                            self.streamer.account_data['funds'] = float(funds)
                        if available_to_deal:
                            self.streamer.account_data['available_to_deal'] = float(available_to_deal)
                        
                        self.streamer.account_data['last_update'] = datetime.utcnow()
                        
                        # Use available_to_deal as the primary balance for trading
                        primary_balance = self.streamer.account_data.get('available_to_deal', 0.0)
                        
                        # Update database with available trading balance
                        if primary_balance > 0:
                            update_account_balance(primary_balance)
                            self.streamer.last_balance_update = datetime.utcnow()
                        
                        # Log account update
                        print(f"💰 Account Update:")
                        print(f"   Available to Deal: £{self.streamer.account_data.get('available_to_deal', 0):.2f}")
                        print(f"   Available Cash: £{self.streamer.account_data.get('available_cash', 0):.2f}")
                        print(f"   P&L: £{self.streamer.account_data.get('pnl', 0):.2f}")
                        print(f"   Margin Used: £{self.streamer.account_data.get('margin', 0):.2f}")
                        print(f"   Equity: £{self.streamer.account_data.get('equity', 0):.2f}")
                        
                        # Check for margin alerts
                        self.streamer.check_margin_alerts()
                        
                    except ValueError as e:
                        print(f"❌ Error processing account update: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error in account update: {e}")
                        
                def onClearSnapshot(self, itemName, itemPos):
                    print(f"📭 Account snapshot cleared")
                    
                def onSubscriptionError(self, code, message):
                    print(f"❌ Account subscription error: {code} - {message}")
                    
                def onSubscription(self):
                    print(f"✅ Successfully subscribed to account data")
                    
                def onUnsubscription(self):
                    print(f"📤 Unsubscribed from account data")
            
            subscription.addListener(AccountDataListener(self))
            return subscription
            
        except Exception as e:
            print(f"❌ Failed to create account subscription: {e}")
            return None
    
    def start_streaming(self):
        """Start streaming account balance data"""
        print(f"📡 Starting account balance streaming...")
        
        # Create account subscription
        self.subscription = self.create_account_subscription()
        if not self.subscription:
            print("❌ Failed to create account subscription")
            return False
        
        # Connect to Lightstreamer
        try:
            self.client.subscribe(self.subscription)
            self.client.connect()
            self.running = True
            print("🚀 Account balance streaming started!")
            return True
        except Exception as e:
            print(f"❌ Failed to start account streaming: {e}")
            return False
    
    def stop_streaming(self):
        """Stop streaming and cleanup"""
        print("🛑 Stopping account balance streaming...")
        self.running = False
        
        if self.subscription:
            self.client.unsubscribe(self.subscription)
            print("📤 Unsubscribed from account data")
        
        self.client.disconnect()
        print("✅ Account balance streaming stopped")
    
    def get_account_data(self):
        """Get current account data"""
        return self.account_data.copy()
    
    def get_available_balance(self):
        """Get available balance for trading"""
        return self.account_data.get('available_to_deal', 0.0)
    
    def is_streaming(self):
        """Check if streamer is running"""
        return self.running
    
    def get_margin_utilization(self):
        """Calculate current margin utilization percentage"""
        margin_used = self.account_data.get('margin', 0.0)
        available_cash = self.account_data.get('available_cash', 0.0)
        total_available = available_cash + margin_used
        
        if total_available > 0:
            return (margin_used / total_available) * 100
        return 0.0
    
    def check_margin_alerts(self):
        """Check for margin-related alerts and warnings"""
        utilization = self.get_margin_utilization()
        alerts = []
        
        # Define thresholds
        WARNING_THRESHOLD = 70.0
        HIGH_THRESHOLD = 80.0
        CRITICAL_THRESHOLD = 85.0
        
        if utilization >= CRITICAL_THRESHOLD:
            alerts.append({
                "level": "CRITICAL",
                "message": f"Margin utilization CRITICAL: {utilization:.1f}%",
                "action": "Close positions immediately"
            })
            print(f"🚨 CRITICAL: Margin utilization at {utilization:.1f}% - CLOSE POSITIONS NOW!")
        elif utilization >= HIGH_THRESHOLD:
            alerts.append({
                "level": "HIGH",
                "message": f"Margin utilization HIGH: {utilization:.1f}%",
                "action": "No new positions allowed"
            })
            print(f"⚠️ HIGH: Margin utilization at {utilization:.1f}% - No new trades!")
        elif utilization >= WARNING_THRESHOLD:
            alerts.append({
                "level": "WARNING",
                "message": f"Margin utilization WARNING: {utilization:.1f}%",
                "action": "Reduce position sizes"
            })
            print(f"⚠️ WARNING: Margin utilization at {utilization:.1f}% - Trade carefully!")
        
        return alerts
    
    def get_detailed_margin_info(self):
        """Get detailed margin information"""
        return {
            "margin_total": self.account_data.get('margin', 0.0),
            "margin_lr": self.account_data.get('margin_lr', 0.0),  # Limited Risk
            "margin_nlr": self.account_data.get('margin_nlr', 0.0),  # Non-Limited Risk
            "available_cash": self.account_data.get('available_cash', 0.0),
            "available_to_deal": self.account_data.get('available_to_deal', 0.0),
            "equity": self.account_data.get('equity', 0.0),
            "equity_used": self.account_data.get('equity_used', 0.0),
            "utilization_percent": self.get_margin_utilization(),
            "alerts": self.check_margin_alerts(),
            "last_update": self.account_data.get('last_update')
        }


# Global account streamer instance
_global_account_streamer = None

def get_account_streamer():
    """Get global account streamer instance (singleton)"""
    global _global_account_streamer
    if _global_account_streamer is None:
        _global_account_streamer = AccountBalanceStreamer()
    return _global_account_streamer

def start_account_streaming():
    """Start global account streaming"""
    streamer = get_account_streamer()
    return streamer.start_streaming()

def stop_account_streaming():
    """Stop global account streaming"""
    global _global_account_streamer
    if _global_account_streamer:
        _global_account_streamer.stop_streaming()
        _global_account_streamer = None

def get_live_account_balance():
    """Get current live account balance"""
    streamer = get_account_streamer()
    return streamer.get_available_balance()

def get_live_account_data():
    """Get all current account data"""
    streamer = get_account_streamer()
    return streamer.get_account_data()


if __name__ == "__main__":
    # Test account streaming
    print("🧪 Testing Account Balance Streaming")
    print("=" * 50)
    
    streamer = AccountBalanceStreamer()
    
    try:
        streamer.start_streaming()
        
        # Stream for 30 seconds
        print("⏳ Streaming account data for 30 seconds...")
        time.sleep(30)
        
        # Show final account data
        account_data = streamer.get_account_data()
        print(f"\n📊 Final Account Data:")
        for key, value in account_data.items():
            if key != 'last_update':
                print(f"   {key}: £{value:.2f}")
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        streamer.stop_streaming()