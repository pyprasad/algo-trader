# utils/balance_manager.py

"""
💰 Account Balance Management Utility

Provides tools for:
- Setting initial account balance
- Monitoring balance changes
- Balance validation before trades
- P&L tracking across multiple markets

Author: Multi-Market Trading System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import (
    get_account_balance, 
    update_account_balance, 
    check_sufficient_balance,
    get_open_trades,
    trades_collection
)

try:
    from data.account_streamer import get_live_account_data, get_account_streamer
    LIVE_STREAMING_AVAILABLE = True
except ImportError:
    LIVE_STREAMING_AVAILABLE = False
from datetime import datetime, timedelta
import argparse

class BalanceManager:
    def __init__(self):
        self.current_balance = get_account_balance()
    
    def set_initial_balance(self, amount: float):
        """Set initial account balance"""
        update_account_balance(amount)
        self.current_balance = amount
        print(f"💰 Initial balance set to: £{amount}")
        return amount
    
    def get_current_balance(self):
        """Get current account balance"""
        self.current_balance = get_account_balance()
        return self.current_balance
    
    def add_funds(self, amount: float):
        """Add funds to account"""
        current = self.get_current_balance()
        new_balance = current + amount
        update_account_balance(new_balance)
        print(f"💰 Added £{amount} to account. New balance: £{new_balance}")
        return new_balance
    
    def check_margin_requirement(self, required_margin: float):
        """Check if sufficient balance for margin requirement"""
        return check_sufficient_balance(required_margin)
    
    def get_margin_utilization(self):
        """Calculate current margin utilization"""
        current_balance = self.get_current_balance()
        open_trades = get_open_trades()
        
        total_margin_used = sum(trade.get('margin_used', 0) for trade in open_trades)
        
        if current_balance is not None and current_balance + total_margin_used > 0:
            utilization_pct = (total_margin_used / (current_balance + total_margin_used)) * 100
        else:
            utilization_pct = 100.0
        
        return {
            "available_balance": current_balance,
            "margin_used": total_margin_used,
            "utilization_percent": utilization_pct,
            "open_positions": len(open_trades)
        }
    
    def get_pnl_summary(self, days_back: int = 7):
        """Get P&L summary for recent period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        
        # Get closed trades from the period
        closed_trades = list(trades_collection.find({
            "status": "CLOSED",
            "close_timestamp": {"$gte": cutoff_date}
        }))
        
        total_pnl = sum(trade.get('profit_loss', 0) for trade in closed_trades)
        winning_trades = [t for t in closed_trades if t.get('profit_loss', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('profit_loss', 0) < 0]
        
        # Group by market
        market_pnl = {}
        for trade in closed_trades:
            market = trade.get('market', 'Unknown')
            if market not in market_pnl:
                market_pnl[market] = 0
            market_pnl[market] += trade.get('profit_loss', 0)
        
        return {
            "period_days": days_back,
            "total_pnl": total_pnl,
            "total_trades": len(closed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0,
            "avg_win": sum(t.get('profit_loss', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            "avg_loss": sum(t.get('profit_loss', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            "market_breakdown": market_pnl
        }
    
    def get_risk_metrics(self):
        """Calculate risk metrics"""
        open_trades = get_open_trades()
        current_balance = self.get_current_balance()
        
        # Calculate total exposure
        total_exposure = 0
        market_exposure = {}
        
        for trade in open_trades:
            market = trade.get('market', 'Unknown')
            size = trade.get('size', 0)
            entry_price = trade.get('entry_price', 0)
            exposure = size * entry_price
            
            total_exposure += exposure
            if market not in market_exposure:
                market_exposure[market] = 0
            market_exposure[market] += exposure
        
        # Calculate risk per market
        risk_per_market = {}
        for market, exposure in market_exposure.items():
            risk_pct = (exposure / current_balance) * 100 if current_balance is not None and current_balance > 0 else 0
            risk_per_market[market] = {
                "exposure": exposure,
                "risk_percent": risk_pct
            }
        
        return {
            "total_exposure": total_exposure,
            "exposure_to_balance_ratio": (total_exposure / current_balance) * 100 if current_balance is not None and current_balance > 0 else 0,
            "open_positions": len(open_trades),
            "market_risk_breakdown": risk_per_market
        }
    
    def print_account_summary(self):
        """Print comprehensive account summary"""
        print("\n" + "="*60)
        print("💰 ACCOUNT BALANCE SUMMARY")
        print("="*60)
        
        # Show live account data if available
        if LIVE_STREAMING_AVAILABLE:
            try:
                streamer = get_account_streamer()
                if streamer.is_streaming():
                    account_data = get_live_account_data()
                    if account_data.get('last_update'):
                        print("📡 LIVE ACCOUNT DATA (Real-time)")
                        print(f"Available to Deal: £{account_data.get('available_to_deal', 0):,.2f}")
                        print(f"Available Cash: £{account_data.get('available_cash', 0):,.2f}")
                        print(f"Current P&L: £{account_data.get('pnl', 0):,.2f}")
                        print(f"Funds: £{account_data.get('funds', 0):,.2f}")
                        print(f"Equity: £{account_data.get('equity', 0):,.2f}")
                        print(f"Margin Used: £{account_data.get('margin', 0):,.2f}")
                        print(f"Last Update: {account_data.get('last_update', 'N/A')}")
                        
                        # Calculate margin utilization from live data
                        margin_util = streamer.get_margin_utilization()
                        print(f"Live Margin Utilization: {margin_util:.1f}%")
                        print("-" * 60)
                    else:
                        print("📡 Live streaming active but no data yet...")
                else:
                    print("📡 Live streaming available but not active")
            except Exception as e:
                print(f"⚠️ Live streaming error: {e}")
        
        # Current balance (fallback or confirmation)
        balance = self.get_current_balance()
        print(f"Current Trading Balance: £{balance:,.2f}")
        
        # Margin utilization
        margin_info = self.get_margin_utilization()
        print(f"Available Balance: £{margin_info['available_balance']:,.2f}")
        print(f"Margin Used: £{margin_info['margin_used']:,.2f}")
        print(f"Margin Utilization: {margin_info['utilization_percent']:.1f}%")
        print(f"Open Positions: {margin_info['open_positions']}")
        
        # P&L Summary
        print("\n📊 P&L SUMMARY (Last 7 days)")
        print("-" * 40)
        pnl_info = self.get_pnl_summary()
        print(f"Total P&L: £{pnl_info['total_pnl']:,.2f}")
        print(f"Total Trades: {pnl_info['total_trades']}")
        print(f"Win Rate: {pnl_info['win_rate']:.1f}%")
        if pnl_info['avg_win'] > 0:
            print(f"Average Win: £{pnl_info['avg_win']:,.2f}")
        if pnl_info['avg_loss'] < 0:
            print(f"Average Loss: £{pnl_info['avg_loss']:,.2f}")
        
        # Market breakdown
        if pnl_info['market_breakdown']:
            print("\nMarket P&L Breakdown:")
            for market, pnl in pnl_info['market_breakdown'].items():
                print(f"  {market}: £{pnl:,.2f}")
        
        # Risk metrics
        print("\n⚠️ RISK METRICS")
        print("-" * 40)
        risk_info = self.get_risk_metrics()
        print(f"Total Exposure: £{risk_info['total_exposure']:,.2f}")
        print(f"Exposure/Balance Ratio: {risk_info['exposure_to_balance_ratio']:.1f}%")
        
        if risk_info['market_risk_breakdown']:
            print("\nMarket Risk Breakdown:")
            for market, risk in risk_info['market_risk_breakdown'].items():
                print(f"  {market}: £{risk['exposure']:,.2f} ({risk['risk_percent']:.1f}%)")
        
        print("="*60)


def main():
    """Command line interface for balance management"""
    parser = argparse.ArgumentParser(description='Account Balance Manager')
    parser.add_argument('--set-balance', type=float, help='Set initial account balance')
    parser.add_argument('--add-funds', type=float, help='Add funds to account')
    parser.add_argument('--summary', action='store_true', help='Show account summary')
    parser.add_argument('--balance', action='store_true', help='Show current balance')
    
    args = parser.parse_args()
    
    manager = BalanceManager()
    
    if args.set_balance:
        manager.set_initial_balance(args.set_balance)
    elif args.add_funds:
        manager.add_funds(args.add_funds)
    elif args.summary:
        manager.print_account_summary()
    elif args.balance:
        balance = manager.get_current_balance()
        print(f"Current Account Balance: £{balance:,.2f}")
    else:
        manager.print_account_summary()


if __name__ == "__main__":
    main()