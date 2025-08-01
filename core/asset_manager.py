# core/asset_manager.py

import yaml
import pandas as pd
from datetime import datetime, time
import pytz
from typing import Dict, List, Optional
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.market_hours import is_market_open

class AssetManager:
    """
    Manages multiple assets, their configurations, and market-specific logic.
    """
    
    def __init__(self, config_file: str = "configs/assets_comprehensive.yaml"):
        """Initialize the asset manager with configuration."""
        self.config_file = config_file
        self.assets = self._load_asset_config()
        
    def _load_asset_config(self) -> Dict:
        """Load asset configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ Asset config file {self.config_file} not found. Using default FTSE config.")
            return {"FTSE 100": {
                "epic": "IX.D.FTSE.DAILY.IP",
                "trade_size": 1,
                "min_stop_distance": 1,
                "currency": "GBP",
                "sector": "Index",
                "volatility_factor": 1.0
            }}
    
    def get_asset_config(self, asset_name: str) -> Dict:
        """Get configuration for a specific asset."""
        return self.assets.get(asset_name, {})
    
    def get_tradeable_assets(self) -> List[str]:
        """Get list of all configured assets."""
        return list(self.assets.keys())
    
    def get_assets_by_sector(self, sector: str) -> List[str]:
        """Get assets filtered by sector (Technology, Index, Forex, etc.)."""
        return [
            asset for asset, config in self.assets.items()
            if config.get("sector", "").lower() == sector.lower()
        ]
    
    def is_asset_tradeable_now(self, asset_name: str) -> bool:
        """Check if an asset is currently tradeable based on market hours."""
        config = self.get_asset_config(asset_name)
        
        # For Forex and Crypto, typically 24/7 except weekends
        if config.get("sector") in ["Forex", "Cryptocurrency"]:
            now = datetime.now()
            return now.weekday() < 5  # Monday=0, Friday=4
        
        # For stocks and indices, use market hours
        market_hours = config.get("market_hours", {})
        if not market_hours:
            return True  # Default to always tradeable if no hours specified
        
        try:
            timezone = pytz.timezone(market_hours.get("timezone", "UTC"))
            now = datetime.now(timezone)
            
            # Check if it's a weekday
            if now.weekday() >= 5:  # Weekend
                return False
            
            # Parse market hours
            open_time = time.fromisoformat(market_hours.get("open", "00:00"))
            close_time = time.fromisoformat(market_hours.get("close", "23:59"))
            
            current_time = now.time()
            return open_time <= current_time <= close_time
            
        except Exception as e:
            print(f"⚠️ Error checking market hours for {asset_name}: {e}")
            return True  # Default to tradeable on error
    
    def get_position_size(self, asset_name: str, account_balance: float, risk_percent: float = 2.0) -> float:
        """
        Calculate position size based on account balance and risk management.
        
        Parameters:
        - asset_name: Name of the asset
        - account_balance: Current account balance
        - risk_percent: Percentage of account to risk per trade (default: 2%)
        
        Returns:
        - Calculated position size
        """
        config = self.get_asset_config(asset_name)
        base_size = config.get("trade_size", 1)
        volatility_factor = config.get("volatility_factor", 1.0)
        
        # Calculate risk-adjusted position size
        risk_amount = account_balance * (risk_percent / 100)
        
        # Adjust for volatility (higher volatility = smaller position)
        adjusted_size = base_size * (risk_amount / 1000) / volatility_factor
        
        # Apply sector-specific adjustments
        sector = config.get("sector", "")
        if sector == "Cryptocurrency":
            adjusted_size *= 0.5  # Reduce crypto positions due to high volatility
        elif sector == "Forex":
            adjusted_size *= 1.2  # Slightly increase forex positions
        
        return max(adjusted_size, base_size * 0.1)  # Minimum 10% of base size
    
    def get_stop_loss_distance(self, asset_name: str, atr_value: Optional[float] = None) -> float:
        """
        Calculate appropriate stop loss distance for an asset.
        
        Parameters:
        - asset_name: Name of the asset
        - atr_value: Current ATR value for dynamic stop loss
        
        Returns:
        - Stop loss distance
        """
        config = self.get_asset_config(asset_name)
        min_distance = config.get("min_stop_distance", 1.0)
        volatility_factor = config.get("volatility_factor", 1.0)
        
        if atr_value:
            # Dynamic stop loss based on ATR
            dynamic_distance = atr_value * volatility_factor * 2
            return max(dynamic_distance, min_distance)
        else:
            # Static stop loss
            return min_distance * volatility_factor
    
    def get_take_profit_distance(self, asset_name: str, stop_loss_distance: float, reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit distance based on stop loss and reward ratio.
        
        Parameters:
        - asset_name: Name of the asset
        - stop_loss_distance: Stop loss distance
        - reward_ratio: Risk-reward ratio (default: 2:1)
        
        Returns:
        - Take profit distance
        """
        config = self.get_asset_config(asset_name)
        min_distance = config.get("min_stop_distance", 1.0)
        
        calculated_tp = stop_loss_distance * reward_ratio
        return max(calculated_tp, min_distance)
    
    def get_trading_summary(self) -> Dict:
        """Get a summary of all configured assets and their current status."""
        summary = {
            "total_assets": len(self.assets),
            "tradeable_now": 0,
            "by_sector": {},
            "assets": []
        }
        
        for asset_name, config in self.assets.items():
            is_tradeable = self.is_asset_tradeable_now(asset_name)
            sector = config.get("sector", "Unknown")
            
            if is_tradeable:
                summary["tradeable_now"] += 1
            
            if sector not in summary["by_sector"]:
                summary["by_sector"][sector] = {"total": 0, "tradeable": 0}
            
            summary["by_sector"][sector]["total"] += 1
            if is_tradeable:
                summary["by_sector"][sector]["tradeable"] += 1
            
            summary["assets"].append({
                "name": asset_name,
                "sector": sector,
                "currency": config.get("currency", "USD"),
                "tradeable": is_tradeable,
                "volatility": config.get("volatility_factor", 1.0)
            })
        
        return summary

# Global instance
asset_manager = AssetManager()