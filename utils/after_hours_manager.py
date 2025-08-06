# utils/after_hours_manager.py

"""
After-Hours Trading Manager

Handles:
- Market state detection (regular/after-hours/weekend)
- Dynamic margin requirements
- Spread adjustments for after-hours
- Market status via IG API

Author: Algo Trading System
"""

from datetime import datetime, time, timedelta
import pytz
import requests
from typing import Dict, Optional, Tuple
from utils.auth_helper import authenticate
from utils.config_loader import load_global_config

class AfterHoursManager:
    """Manages after-hours trading operations and market state detection"""
    
    def __init__(self):
        """Initialize after-hours manager with IG API credentials"""
        self.global_config = load_global_config()
        self.api_key = self.global_config["ig"]["api_key"]
        self.base_url = self.global_config["ig"]["base_url"]
        
        # Get authentication tokens
        self.cst, self.xst, _, _ = authenticate()
        self.headers = {
            "X-IG-API-KEY": self.api_key,
            "CST": self.cst,
            "X-SECURITY-TOKEN": self.xst,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Market hours definitions
        self.market_hours = {
            "FTSE 100": {
                "timezone": "Europe/London",
                "regular": {"open": time(8, 0), "close": time(16, 30)},
                "extended": None,  # No extended hours
                "weekend_epic": "IX.D.FTSE.WEEKEND.IP"
            },
            "S&P 500": {
                "timezone": "US/Eastern",
                "regular": {"open": time(9, 30), "close": time(16, 0)},
                "extended": {
                    "pre_market": {"open": time(4, 0), "close": time(9, 30)},
                    "after_hours": {"open": time(16, 0), "close": time(20, 0)}
                },
                "weekend_epic": "IX.D.SPTRD.WEEKEND.IP"
            },
            "NASDAQ 100": {
                "timezone": "US/Eastern",
                "regular": {"open": time(9, 30), "close": time(16, 0)},
                "extended": {
                    "pre_market": {"open": time(4, 0), "close": time(9, 30)},
                    "after_hours": {"open": time(16, 0), "close": time(20, 0)}
                },
                "weekend_epic": "IX.D.NASDAQ.WEEKEND.IP"
            },
            "DAX": {
                "timezone": "Europe/Berlin",
                "regular": {"open": time(8, 0), "close": time(16, 30)},
                "extended": {
                    "pre_market": {"open": time(7, 0), "close": time(8, 0)},
                    "after_hours": {"open": time(16, 30), "close": time(22, 0)}
                },
                "weekend_epic": "IX.D.DAX.WEEKEND.IP"
            }
        }
        
        # Margin multipliers for different trading sessions
        self.margin_multipliers = {
            "regular": 1.0,
            "pre_market": 1.5,
            "after_hours": 1.5,
            "weekend": 2.0
        }
        
        # Spread multipliers
        self.spread_multipliers = {
            "regular": 1.0,
            "pre_market": 2.0,
            "after_hours": 2.0,
            "weekend": 3.0
        }
    
    def get_market_status_from_api(self, epic: str) -> Dict:
        """
        Fetch real-time market status from IG API
        
        Args:
            epic: Market EPIC identifier
            
        Returns:
            Dict with market status information
        """
        try:
            url = f"{self.base_url}/markets/{epic}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            snapshot = data.get("snapshot", {})
            dealing_rules = data.get("dealingRules", {})
            
            return {
                "marketStatus": snapshot.get("marketStatus", "UNKNOWN"),
                "updateTime": snapshot.get("updateTime"),
                "bid": snapshot.get("bid"),
                "offer": snapshot.get("offer"),
                "delayTime": snapshot.get("delayTime", 0),
                "streamingPricesAvailable": snapshot.get("streamingPricesAvailable", False),
                "minDistance": float(dealing_rules.get("minControlledRiskStopDistance", {}).get("value", 1)),
                "marginRequirement": float(data.get("marginDepositBands", [{}])[0].get("margin", 1))
            }
        except Exception as e:
            print(f"⚠️ Failed to get market status for {epic}: {e}")
            return {"marketStatus": "UNKNOWN", "error": str(e)}
    
    def detect_trading_session(self, market_name: str) -> str:
        """
        Detect current trading session for a market
        
        Args:
            market_name: Name of the market
            
        Returns:
            Session type: "regular", "pre_market", "after_hours", "weekend", or "closed"
        """
        if market_name not in self.market_hours:
            return "unknown"
        
        market_info = self.market_hours[market_name]
        tz = pytz.timezone(market_info["timezone"])
        now = datetime.now(tz)
        current_time = now.time()
        weekday = now.weekday()
        
        # Check if weekend
        if weekday >= 5:  # Saturday or Sunday
            return "weekend"
        
        # Check regular hours
        regular = market_info["regular"]
        if regular["open"] <= current_time <= regular["close"]:
            return "regular"
        
        # Check extended hours if available
        if market_info.get("extended"):
            extended = market_info["extended"]
            
            # Pre-market
            if "pre_market" in extended:
                pre = extended["pre_market"]
                if pre["open"] <= current_time < pre["close"]:
                    return "pre_market"
            
            # After-hours
            if "after_hours" in extended:
                after = extended["after_hours"]
                if after["open"] <= current_time <= after["close"]:
                    return "after_hours"
        
        return "closed"
    
    def get_session_parameters(self, market_name: str, epic: str = None) -> Dict:
        """
        Get trading parameters for current session
        
        Args:
            market_name: Name of the market
            epic: Market EPIC (optional, for API status check)
            
        Returns:
            Dict with session parameters including margins and spreads
        """
        session = self.detect_trading_session(market_name)
        
        # Get API status if EPIC provided
        api_status = {}
        if epic:
            api_status = self.get_market_status_from_api(epic)
        
        # Determine if market is actually tradeable
        is_tradeable = False
        if api_status.get("marketStatus") == "TRADEABLE":
            is_tradeable = True
        elif session in ["regular", "pre_market", "after_hours", "weekend"]:
            # Market should be open based on time
            is_tradeable = True
        
        # Get appropriate EPIC for weekend trading
        effective_epic = epic
        if session == "weekend" and market_name in self.market_hours:
            weekend_epic = self.market_hours[market_name].get("weekend_epic")
            if weekend_epic:
                effective_epic = weekend_epic
        
        return {
            "market": market_name,
            "session": session,
            "is_tradeable": is_tradeable,
            "margin_multiplier": self.margin_multipliers.get(session, 1.0),
            "spread_multiplier": self.spread_multipliers.get(session, 1.0),
            "effective_epic": effective_epic,
            "api_status": api_status.get("marketStatus", "UNKNOWN"),
            "min_distance": api_status.get("minDistance", 1),
            "base_margin": api_status.get("marginRequirement", 1),
            "adjusted_margin": api_status.get("marginRequirement", 1) * self.margin_multipliers.get(session, 1.0),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def calculate_adjusted_stops(self, base_stop: float, base_limit: float, session: str) -> Tuple[float, float]:
        """
        Calculate adjusted stop-loss and take-profit for session
        
        Args:
            base_stop: Base stop-loss distance
            base_limit: Base take-profit distance
            session: Trading session type
            
        Returns:
            Tuple of (adjusted_stop, adjusted_limit)
        """
        spread_mult = self.spread_multipliers.get(session, 1.0)
        
        # Wider stops during after-hours due to increased volatility
        adjusted_stop = base_stop * spread_mult
        adjusted_limit = base_limit * spread_mult
        
        return adjusted_stop, adjusted_limit
    
    def should_reduce_position_size(self, session: str) -> bool:
        """
        Determine if position size should be reduced
        
        Args:
            session: Trading session type
            
        Returns:
            True if position should be reduced
        """
        return session in ["pre_market", "after_hours", "weekend"]
    
    def get_position_size_multiplier(self, session: str) -> float:
        """
        Get position size multiplier for session
        
        Args:
            session: Trading session type
            
        Returns:
            Position size multiplier (0.5 for after-hours, 1.0 for regular)
        """
        if session in ["pre_market", "after_hours", "weekend"]:
            return 0.5  # 50% position size
        return 1.0  # Full position size
    
    def is_high_risk_period(self, market_name: str) -> bool:
        """
        Check if current time is a high-risk trading period
        
        Args:
            market_name: Name of the market
            
        Returns:
            True if high risk period
        """
        session = self.detect_trading_session(market_name)
        
        # High risk during weekends and extended hours
        if session in ["weekend", "pre_market", "after_hours"]:
            return True
        
        # Also check for market events (can be extended with news API)
        # For now, just check session type
        return False
    
    def get_trading_recommendation(self, market_name: str, epic: str = None) -> Dict:
        """
        Get comprehensive trading recommendation for current conditions
        
        Args:
            market_name: Name of the market
            epic: Market EPIC (optional)
            
        Returns:
            Dict with trading recommendations
        """
        params = self.get_session_parameters(market_name, epic)
        session = params["session"]
        
        recommendation = {
            "market": market_name,
            "session": session,
            "can_trade": params["is_tradeable"],
            "position_size_adjustment": self.get_position_size_multiplier(session),
            "margin_adjustment": params["margin_multiplier"],
            "spread_adjustment": params["spread_multiplier"],
            "is_high_risk": self.is_high_risk_period(market_name),
            "effective_epic": params["effective_epic"],
            "recommendations": []
        }
        
        # Add specific recommendations
        if session == "closed":
            recommendation["can_trade"] = False
            recommendation["recommendations"].append("Market is closed")
        elif session == "weekend":
            recommendation["recommendations"].append("Use weekend EPIC for trading")
            recommendation["recommendations"].append("Expect wider spreads (3x normal)")
            recommendation["recommendations"].append("Reduce position size by 50%")
        elif session in ["pre_market", "after_hours"]:
            recommendation["recommendations"].append("Extended hours trading - increased volatility")
            recommendation["recommendations"].append("Wider spreads expected (2x normal)")
            recommendation["recommendations"].append("Reduce position size by 50%")
        else:
            recommendation["recommendations"].append("Regular trading hours - normal conditions")
        
        return recommendation


# Global instance
_global_after_hours_manager = None

def get_after_hours_manager() -> AfterHoursManager:
    """Get global after-hours manager instance"""
    global _global_after_hours_manager
    if _global_after_hours_manager is None:
        _global_after_hours_manager = AfterHoursManager()
    return _global_after_hours_manager


if __name__ == "__main__":
    print("🌙 Testing After-Hours Trading Manager")
    print("=" * 50)
    
    manager = AfterHoursManager()
    
    # Test market detection
    markets = ["FTSE 100", "S&P 500", "NASDAQ 100", "DAX"]
    
    for market in markets:
        print(f"\n📊 {market}:")
        session = manager.detect_trading_session(market)
        print(f"   Current session: {session}")
        
        params = manager.get_session_parameters(market)
        print(f"   Margin multiplier: {params['margin_multiplier']}x")
        print(f"   Spread multiplier: {params['spread_multiplier']}x")
        print(f"   Is tradeable: {params['is_tradeable']}")
        
        recommendation = manager.get_trading_recommendation(market)
        print(f"   Recommendations:")
        for rec in recommendation["recommendations"]:
            print(f"      • {rec}")