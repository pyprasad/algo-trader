# utils/market_config_loader.py

"""
🏪 Market Configuration Loader

Loads market configurations from YAML files and validates them
for multi-market trading system.

Author: Multi-Market Trading System
"""

import yaml
from typing import List, Dict, Optional

class MarketConfigLoader:
    def __init__(self, assets_config_path="configs/assets_comprehensive.yaml", 
                 trading_config_path="configs/trading_config.yaml"):
        self.assets_config_path = assets_config_path
        self.trading_config_path = trading_config_path
        self.assets_config = None
        self.trading_config = None
        self.load_configs()
    
    def load_configs(self):
        """Load both configuration files"""
        try:
            # Load assets configuration
            with open(self.assets_config_path, 'r') as f:
                self.assets_config = yaml.safe_load(f)
            print(f"✅ Loaded assets config: {len(self.assets_config)} markets available")
            
            # Load trading configuration
            with open(self.trading_config_path, 'r') as f:
                self.trading_config = yaml.safe_load(f)
            print(f"✅ Loaded trading config: {len(self.trading_config.get('active_markets', []))} markets selected")
            
        except FileNotFoundError as e:
            print(f"❌ Config file not found: {e}")
            raise
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error: {e}")
            raise
    
    def get_available_markets(self) -> List[str]:
        """Get list of all available markets from assets config"""
        if not self.assets_config:
            return []
        return list(self.assets_config.keys())
    
    def get_active_markets(self) -> List[str]:
        """Get list of markets configured for trading"""
        if not self.trading_config:
            return []
        return self.trading_config.get('active_markets', [])
    
    def get_market_config(self, market_name: str) -> Optional[Dict]:
        """Get configuration for a specific market"""
        if not self.assets_config or market_name not in self.assets_config:
            return None
        return self.assets_config[market_name]
    
    def validate_active_markets(self) -> tuple[List[str], List[str]]:
        """
        Validate that all active markets exist in assets config
        
        Returns:
            tuple: (valid_markets, invalid_markets)
        """
        available_markets = self.get_available_markets()
        active_markets = self.get_active_markets()
        
        valid_markets = []
        invalid_markets = []
        
        for market in active_markets:
            if market in available_markets:
                valid_markets.append(market)
            else:
                invalid_markets.append(market)
        
        return valid_markets, invalid_markets
    
    def get_system_config(self) -> Dict:
        """Get system configuration"""
        if not self.trading_config:
            return {}
        return self.trading_config.get('system', {})
    
    def get_risk_config(self) -> Dict:
        """Get risk management configuration"""
        if not self.trading_config:
            return {}
        return self.trading_config.get('risk_management', {})
    
    def print_market_summary(self):
        """Print summary of market configuration"""
        print("\n" + "="*60)
        print("📊 MARKET CONFIGURATION SUMMARY")
        print("="*60)
        
        available_markets = self.get_available_markets()
        active_markets = self.get_active_markets()
        valid_markets, invalid_markets = self.validate_active_markets()
        
        print(f"Available Markets: {len(available_markets)}")
        for market in available_markets:
            config = self.get_market_config(market)
            epic = config.get('epic', 'N/A') if config else 'N/A'
            currency = config.get('currency', 'N/A') if config else 'N/A'
            print(f"  ✅ {market} ({epic}) - {currency}")
        
        print(f"\nActive Markets: {len(active_markets)}")
        for market in valid_markets:
            config = self.get_market_config(market)
            epic = config.get('epic', 'N/A') if config else 'N/A'
            trade_size = config.get('trade_size', 'N/A') if config else 'N/A'
            print(f"  🎯 {market} ({epic}) - Size: {trade_size}")
        
        if invalid_markets:
            print(f"\nInvalid Markets: {len(invalid_markets)}")
            for market in invalid_markets:
                print(f"  ❌ {market} (not found in assets config)")
        
        # System config
        system_config = self.get_system_config()
        if system_config:
            print(f"\nSystem Configuration:")
            print(f"  Initial Balance: £{system_config.get('initial_balance', 'N/A')}")
            print(f"  Max Concurrent Markets: {system_config.get('max_concurrent_markets', 'N/A')}")
            print(f"  Analysis Interval: {system_config.get('analysis_interval_seconds', 'N/A')}s")
        
        # Risk config
        risk_config = self.get_risk_config()
        if risk_config:
            print(f"\nRisk Management:")
            print(f"  Max Margin Utilization: {risk_config.get('max_margin_utilization_percent', 'N/A')}%")
            print(f"  Max Exposure Per Market: {risk_config.get('max_exposure_per_market_percent', 'N/A')}%")
        
        print("="*60)
    
    def add_market_to_active(self, market_name: str) -> bool:
        """Add a market to active trading list"""
        if market_name not in self.get_available_markets():
            print(f"❌ Market {market_name} not found in assets configuration")
            return False
        
        active_markets = self.get_active_markets()
        if market_name in active_markets:
            print(f"⚠️ Market {market_name} already active")
            return True
        
        active_markets.append(market_name)
        self.trading_config['active_markets'] = active_markets
        
        # Save updated config
        try:
            with open(self.trading_config_path, 'w') as f:
                yaml.dump(self.trading_config, f, default_flow_style=False)
            print(f"✅ Added {market_name} to active markets")
            return True
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            return False
    
    def remove_market_from_active(self, market_name: str) -> bool:
        """Remove a market from active trading list"""
        active_markets = self.get_active_markets()
        if market_name not in active_markets:
            print(f"⚠️ Market {market_name} not in active markets")
            return True
        
        active_markets.remove(market_name)
        self.trading_config['active_markets'] = active_markets
        
        # Save updated config
        try:
            with open(self.trading_config_path, 'w') as f:
                yaml.dump(self.trading_config, f, default_flow_style=False)
            print(f"✅ Removed {market_name} from active markets")
            return True
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            return False


def load_market_config() -> MarketConfigLoader:
    """Convenience function to load market configuration"""
    return MarketConfigLoader()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Configuration Manager')
    parser.add_argument('--summary', action='store_true', help='Show market configuration summary')
    parser.add_argument('--add-market', type=str, help='Add market to active trading list')
    parser.add_argument('--remove-market', type=str, help='Remove market from active trading list')
    parser.add_argument('--list-available', action='store_true', help='List all available markets')
    parser.add_argument('--list-active', action='store_true', help='List active markets')
    
    args = parser.parse_args()
    
    config_loader = MarketConfigLoader()
    
    if args.summary:
        config_loader.print_market_summary()
    elif args.add_market:
        config_loader.add_market_to_active(args.add_market)
    elif args.remove_market:
        config_loader.remove_market_from_active(args.remove_market)
    elif args.list_available:
        markets = config_loader.get_available_markets()
        print("Available Markets:")
        for market in markets:
            print(f"  - {market}")
    elif args.list_active:
        markets = config_loader.get_active_markets()
        print("Active Markets:")
        for market in markets:
            print(f"  - {market}")
    else:
        config_loader.print_market_summary()