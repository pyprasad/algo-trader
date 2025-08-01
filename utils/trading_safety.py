# utils/trading_safety.py

"""
🛡️ Trading Safety Manager

Implements safety mechanisms for trading:
- Balance threshold monitoring (30% rule)
- One trade per market limitation
- Risk management controls
- Trade validation

Author: Multi-Market Trading System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.db import get_account_balance, get_open_trades
from utils.market_config_loader import MarketConfigLoader
from datetime import datetime
import threading

class TradingSafetyManager:
    def __init__(self, config_loader: MarketConfigLoader = None):
        """Initialize trading safety manager"""
        self.config_loader = config_loader or MarketConfigLoader()
        self.risk_config = self.config_loader.get_risk_config()
        self.trading_suspended = False
        self.suspension_reason = None
        self.lock = threading.Lock()
        
        # Get safety thresholds
        self.min_balance_percent = self.risk_config.get('minimum_balance_percent', 30)
        self.one_trade_per_market = self.risk_config.get('one_trade_per_market', True)
        self.initial_balance_threshold = self.risk_config.get('initial_balance_threshold', 1000.0)
        
        print(f"🛡️ Trading Safety Manager initialized:")
        print(f"   Minimum balance threshold: {self.min_balance_percent}%")
        print(f"   One trade per market: {self.one_trade_per_market}")
        print(f"   Reference balance: £{self.initial_balance_threshold}")
    
    def check_balance_safety(self) -> tuple[bool, str]:
        """
        Check if current balance is above minimum threshold
        
        Returns:
            tuple: (is_safe, reason)
        """
        try:
            current_balance = get_account_balance()
            
            # Calculate minimum required balance
            min_required_balance = self.initial_balance_threshold * (self.min_balance_percent / 100)
            
            if current_balance < min_required_balance:
                reason = f"Balance £{current_balance:.2f} below {self.min_balance_percent}% threshold (£{min_required_balance:.2f})"
                return False, reason
            
            return True, "Balance above minimum threshold"
            
        except Exception as e:
            return False, f"Error checking balance: {e}"
    
    def check_market_trade_limit(self, market_name: str) -> tuple[bool, str]:
        """
        Check if market already has an open trade
        
        Args:
            market_name: Market to check
            
        Returns:
            tuple: (can_trade, reason)
        """
        if not self.one_trade_per_market:
            return True, "Multiple trades per market allowed"
        
        try:
            open_trades = get_open_trades(market_name)
            
            if len(open_trades) > 0:
                deal_ids = [trade.get('deal_reference', 'Unknown') for trade in open_trades]
                reason = f"Market {market_name} already has {len(open_trades)} open trade(s): {deal_ids}"
                return False, reason
            
            return True, f"No open trades for {market_name}"
            
        except Exception as e:
            return False, f"Error checking market trades: {e}"
    
    def validate_trade(self, market_name: str, direction: str, trade_size: float = None) -> tuple[bool, str]:
        """
        Comprehensive trade validation
        
        Args:
            market_name: Market to trade
            direction: BUY or SELL
            trade_size: Optional trade size for additional checks
            
        Returns:
            tuple: (can_trade, reason)
        """
        with self.lock:
            # Check if trading is globally suspended
            if self.trading_suspended:
                return False, f"Trading suspended: {self.suspension_reason}"
            
            # Check balance safety
            balance_safe, balance_reason = self.check_balance_safety()
            if not balance_safe:
                # Suspend trading if balance is too low
                self.suspend_trading(balance_reason)
                return False, balance_reason
            
            # Check market-specific trade limits
            market_safe, market_reason = self.check_market_trade_limit(market_name)
            if not market_safe:
                return False, market_reason
            
            return True, "All safety checks passed"
    
    def suspend_trading(self, reason: str):
        """Suspend all trading with reason"""
        with self.lock:
            self.trading_suspended = True
            self.suspension_reason = reason
            print(f"🚨 TRADING SUSPENDED: {reason}")
    
    def resume_trading(self):
        """Resume trading if conditions are met"""
        with self.lock:
            # Check if conditions are safe to resume
            balance_safe, balance_reason = self.check_balance_safety()
            
            if balance_safe:
                self.trading_suspended = False
                self.suspension_reason = None
                print(f"✅ Trading resumed: Balance safety restored")
                return True
            else:
                print(f"⚠️ Cannot resume trading: {balance_reason}")
                return False
    
    def get_trading_status(self) -> dict:
        """Get current trading safety status"""
        with self.lock:
            current_balance = get_account_balance()
            min_required = self.initial_balance_threshold * (self.min_balance_percent / 100)
            
            # Count open trades per market
            open_trades_by_market = {}
            try:
                all_open_trades = get_open_trades()
                for trade in all_open_trades:
                    market = trade.get('market', 'Unknown')
                    if market not in open_trades_by_market:
                        open_trades_by_market[market] = 0
                    open_trades_by_market[market] += 1
            except:
                open_trades_by_market = {"Error": "Could not fetch trades"}
            
            return {
                "trading_suspended": self.trading_suspended,
                "suspension_reason": self.suspension_reason,
                "current_balance": current_balance,
                "minimum_required_balance": min_required,
                "balance_safety_margin": current_balance - min_required,
                "balance_percentage": (current_balance / self.initial_balance_threshold) * 100,
                "one_trade_per_market": self.one_trade_per_market,
                "open_trades_by_market": open_trades_by_market,
                "total_open_positions": sum(open_trades_by_market.values()) if isinstance(list(open_trades_by_market.values())[0], int) else 0
            }
    
    def print_safety_status(self):
        """Print comprehensive safety status"""
        status = self.get_trading_status()
        
        print("\n" + "="*60)
        print("🛡️ TRADING SAFETY STATUS")
        print("="*60)
        
        if status["trading_suspended"]:
            print(f"🚨 STATUS: TRADING SUSPENDED")
            print(f"   Reason: {status['suspension_reason']}")
        else:
            print(f"✅ STATUS: TRADING ACTIVE")
        
        print(f"\n💰 Balance Safety:")
        print(f"   Current Balance: £{status['current_balance']:,.2f}")
        print(f"   Minimum Required: £{status['minimum_required_balance']:,.2f}")
        print(f"   Safety Margin: £{status['balance_safety_margin']:,.2f}")
        print(f"   Balance Percentage: {status['balance_percentage']:.1f}%")
        
        print(f"\n📊 Trade Limits:")
        print(f"   One Trade Per Market: {status['one_trade_per_market']}")
        print(f"   Total Open Positions: {status['total_open_positions']}")
        
        if status['open_trades_by_market']:
            print(f"   Open Trades by Market:")
            for market, count in status['open_trades_by_market'].items():
                print(f"     {market}: {count} position(s)")
        
        print("="*60)


# Global safety manager instance
_global_safety_manager = None

def get_trading_safety_manager() -> TradingSafetyManager:
    """Get global trading safety manager (singleton)"""
    global _global_safety_manager
    if _global_safety_manager is None:
        _global_safety_manager = TradingSafetyManager()
    return _global_safety_manager

def validate_trade_safety(market_name: str, direction: str) -> tuple[bool, str]:
    """Convenience function to validate trade safety"""
    safety_manager = get_trading_safety_manager()
    return safety_manager.validate_trade(market_name, direction)

def suspend_all_trading(reason: str):
    """Convenience function to suspend all trading"""
    safety_manager = get_trading_safety_manager()
    safety_manager.suspend_trading(reason)

def get_trading_safety_status() -> dict:
    """Convenience function to get trading status"""
    safety_manager = get_trading_safety_manager()
    return safety_manager.get_trading_status()


if __name__ == "__main__":
    # Test trading safety manager
    print("🧪 Testing Trading Safety Manager")
    print("=" * 50)
    
    safety_manager = TradingSafetyManager()
    
    # Test balance check
    print("\n💰 Testing Balance Safety:")
    safe, reason = safety_manager.check_balance_safety()
    print(f"   Balance Safe: {safe}")
    print(f"   Reason: {reason}")
    
    # Test market trade limits
    print("\n📊 Testing Market Trade Limits:")
    for market in ["FTSE 100", "DAX", "AAPL"]:
        can_trade, reason = safety_manager.check_market_trade_limit(market)
        print(f"   {market}: {'✅' if can_trade else '❌'} {reason}")
    
    # Show full status
    safety_manager.print_safety_status()