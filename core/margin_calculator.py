# core/margin_calculator.py

"""
Dynamic Margin Calculator

Handles:
- Real-time margin requirement calculations
- Position sizing based on available margin
- After-hours margin adjustments
- Risk-based position limits

Author: Algo Trading System
"""

from typing import Dict, Optional, Tuple
from data.account_streamer import get_live_account_data
from utils.after_hours_manager import get_after_hours_manager
from utils.config_loader import load_asset_config, load_global_config

class MarginCalculator:
    """Calculates and manages margin requirements dynamically"""
    
    def __init__(self):
        """Initialize margin calculator with risk parameters"""
        self.global_config = load_global_config()
        self.after_hours_manager = get_after_hours_manager()
        
        # Risk parameters
        self.max_margin_utilization = 0.80  # 80% max margin usage
        self.warning_margin_threshold = 0.70  # Warning at 70%
        self.emergency_close_threshold = 0.85  # Emergency close at 85%
        self.max_position_per_market = 0.20  # Max 20% per market
        
        # After-hours specific limits
        self.after_hours_margin_limit = 0.60  # Lower limit during after-hours
        self.after_hours_position_limit = 0.10  # Max 10% per position after-hours
    
    def get_current_margin_status(self) -> Dict:
        """
        Get current margin utilization status
        
        Returns:
            Dict with margin status information
        """
        account_data = get_live_account_data()
        
        margin_used = account_data.get('margin', 0.0)
        available_cash = account_data.get('available_cash', 0.0)
        available_to_deal = account_data.get('available_to_deal', 0.0)
        equity = account_data.get('equity', 0.0)
        
        # Calculate utilization
        total_available = available_cash + margin_used
        utilization = (margin_used / total_available * 100) if total_available > 0 else 0
        
        # Determine status
        status = "NORMAL"
        if utilization >= self.emergency_close_threshold * 100:
            status = "CRITICAL"
        elif utilization >= self.warning_margin_threshold * 100:
            status = "WARNING"
        elif utilization >= self.max_margin_utilization * 100:
            status = "HIGH"
        
        return {
            "margin_used": margin_used,
            "available_cash": available_cash,
            "available_to_deal": available_to_deal,
            "equity": equity,
            "total_available": total_available,
            "utilization_percent": utilization,
            "status": status,
            "can_open_new": utilization < (self.max_margin_utilization * 100),
            "requires_reduction": utilization >= (self.emergency_close_threshold * 100)
        }
    
    def calculate_required_margin(self, market_name: str, trade_size: float, 
                                 epic: str = None) -> Dict:
        """
        Calculate required margin for a trade
        
        Args:
            market_name: Name of the market
            trade_size: Size of the trade
            epic: Market EPIC (optional)
            
        Returns:
            Dict with margin calculations
        """
        # Get session parameters
        session_params = self.after_hours_manager.get_session_parameters(market_name, epic)
        
        # Base margin from API or config
        base_margin = session_params.get("base_margin", 1.0)
        
        # Apply session multiplier
        margin_multiplier = session_params.get("margin_multiplier", 1.0)
        
        # Calculate total required margin
        required_margin = trade_size * base_margin * margin_multiplier
        
        return {
            "market": market_name,
            "trade_size": trade_size,
            "base_margin": base_margin,
            "session": session_params.get("session", "unknown"),
            "margin_multiplier": margin_multiplier,
            "required_margin": required_margin,
            "is_after_hours": session_params.get("session") in ["pre_market", "after_hours", "weekend"]
        }
    
    def calculate_safe_position_size(self, market_name: str, available_balance: float,
                                    epic: str = None) -> Dict:
        """
        Calculate safe position size based on available balance and risk limits
        
        Args:
            market_name: Name of the market
            available_balance: Available trading balance
            epic: Market EPIC (optional)
            
        Returns:
            Dict with position sizing recommendations
        """
        # Get current margin status
        margin_status = self.get_current_margin_status()
        
        # Get session information
        session_params = self.after_hours_manager.get_session_parameters(market_name, epic)
        session = session_params.get("session", "unknown")
        is_after_hours = session in ["pre_market", "after_hours", "weekend"]
        
        # Determine maximum allowed margin usage
        if margin_status["status"] in ["HIGH", "CRITICAL"]:
            max_allowed_margin = 0  # No new positions
        elif margin_status["status"] == "WARNING":
            max_allowed_margin = available_balance * 0.5  # Reduced size
        elif is_after_hours:
            max_allowed_margin = available_balance * self.after_hours_position_limit
        else:
            max_allowed_margin = available_balance * self.max_position_per_market
        
        # Apply position size multiplier from after-hours manager
        position_multiplier = self.after_hours_manager.get_position_size_multiplier(session)
        
        # Load asset config for default trade size
        try:
            asset_config = load_asset_config(market_name)
            default_trade_size = asset_config.get("trade_size", 1)
        except:
            default_trade_size = 1
        
        # Calculate recommended position size
        base_margin = session_params.get("base_margin", 1.0)
        margin_multiplier = session_params.get("margin_multiplier", 1.0)
        
        if base_margin * margin_multiplier > 0:
            max_position_size = max_allowed_margin / (base_margin * margin_multiplier)
        else:
            max_position_size = 0
        
        # Apply position multiplier
        recommended_size = min(default_trade_size * position_multiplier, max_position_size)
        
        return {
            "market": market_name,
            "session": session,
            "is_after_hours": is_after_hours,
            "available_balance": available_balance,
            "max_allowed_margin": max_allowed_margin,
            "default_trade_size": default_trade_size,
            "position_multiplier": position_multiplier,
            "recommended_size": max(0, recommended_size),  # Ensure non-negative
            "margin_status": margin_status["status"],
            "can_trade": recommended_size > 0 and margin_status["can_open_new"]
        }
    
    def validate_trade_margin(self, market_name: str, trade_size: float, 
                             epic: str = None) -> Tuple[bool, Dict]:
        """
        Validate if a trade can be placed given margin constraints
        
        Args:
            market_name: Name of the market
            trade_size: Proposed trade size
            epic: Market EPIC (optional)
            
        Returns:
            Tuple of (can_trade, validation_details)
        """
        # Get current margin status
        margin_status = self.get_current_margin_status()
        
        # Calculate required margin
        margin_calc = self.calculate_required_margin(market_name, trade_size, epic)
        required_margin = margin_calc["required_margin"]
        
        # Check if we have enough available margin
        available_margin = margin_status["available_to_deal"]
        has_sufficient_margin = required_margin <= available_margin
        
        # Check utilization limits
        new_utilization = ((margin_status["margin_used"] + required_margin) / 
                          margin_status["total_available"] * 100) if margin_status["total_available"] > 0 else 100
        
        # Determine if trade is allowed
        is_after_hours = margin_calc["is_after_hours"]
        max_utilization = self.after_hours_margin_limit if is_after_hours else self.max_margin_utilization
        within_limits = new_utilization <= (max_utilization * 100)
        
        can_trade = (
            has_sufficient_margin and 
            within_limits and 
            margin_status["can_open_new"] and
            not margin_status["requires_reduction"]
        )
        
        validation = {
            "can_trade": can_trade,
            "required_margin": required_margin,
            "available_margin": available_margin,
            "current_utilization": margin_status["utilization_percent"],
            "new_utilization": new_utilization,
            "max_allowed_utilization": max_utilization * 100,
            "has_sufficient_margin": has_sufficient_margin,
            "within_limits": within_limits,
            "margin_status": margin_status["status"],
            "is_after_hours": is_after_hours,
            "reasons": []
        }
        
        # Add rejection reasons
        if not has_sufficient_margin:
            validation["reasons"].append(f"Insufficient margin: need £{required_margin:.2f}, have £{available_margin:.2f}")
        if not within_limits:
            validation["reasons"].append(f"Would exceed margin limit: {new_utilization:.1f}% > {max_utilization * 100:.0f}%")
        if margin_status["requires_reduction"]:
            validation["reasons"].append("Emergency margin reduction required")
        if not margin_status["can_open_new"]:
            validation["reasons"].append("Margin utilization too high for new positions")
        
        return can_trade, validation
    
    def get_margin_alert_level(self) -> str:
        """
        Get current margin alert level
        
        Returns:
            Alert level: "NORMAL", "WARNING", "HIGH", or "CRITICAL"
        """
        status = self.get_current_margin_status()
        return status["status"]
    
    def should_close_positions(self) -> bool:
        """
        Determine if positions should be closed due to margin pressure
        
        Returns:
            True if emergency closure needed
        """
        status = self.get_current_margin_status()
        return status["requires_reduction"]


# Global instance
_global_margin_calculator = None

def get_margin_calculator() -> MarginCalculator:
    """Get global margin calculator instance"""
    global _global_margin_calculator
    if _global_margin_calculator is None:
        _global_margin_calculator = MarginCalculator()
    return _global_margin_calculator


if __name__ == "__main__":
    print("💰 Testing Margin Calculator")
    print("=" * 50)
    
    calculator = MarginCalculator()
    
    # Test margin status
    print("\n📊 Current Margin Status:")
    status = calculator.get_current_margin_status()
    print(f"   Margin Used: £{status['margin_used']:.2f}")
    print(f"   Available: £{status['available_to_deal']:.2f}")
    print(f"   Utilization: {status['utilization_percent']:.1f}%")
    print(f"   Status: {status['status']}")
    print(f"   Can Open New: {status['can_open_new']}")
    
    # Test position sizing
    markets = ["FTSE 100", "S&P 500"]
    for market in markets:
        print(f"\n📈 {market} Position Sizing:")
        sizing = calculator.calculate_safe_position_size(market, 10000)
        print(f"   Session: {sizing['session']}")
        print(f"   Recommended Size: {sizing['recommended_size']:.2f}")
        print(f"   Can Trade: {sizing['can_trade']}")
        
        # Test margin validation
        can_trade, validation = calculator.validate_trade_margin(market, sizing['recommended_size'])
        print(f"   Validation: {'✅ PASS' if can_trade else '❌ FAIL'}")
        if validation["reasons"]:
            for reason in validation["reasons"]:
                print(f"      • {reason}")