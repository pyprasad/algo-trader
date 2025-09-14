# core/ig_margin_api.py

"""
🌐 IG Markets Margin API Integration

Provides real integration with IG Markets API for fetching actual margin rates,
account information, and position details with proper error handling and caching.

Key Features:
- Real-time margin rate fetching from IG API
- Account balance and margin status retrieval  
- Position margin requirement calculations
- Automatic session management
- Request optimization and caching
- Fallback to configured rates on failure

Author: API Integration Team
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import hashlib
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependencies
from core.secure_config import get_secure_config
from core.error_handler import get_error_handler, ErrorCategory, ErrorSeverity, with_error_handling
from core.api_request_optimizer import get_api_request_optimizer, RequestType, RequestPriority

@dataclass
class IGSession:
    """IG API session information"""
    cst: str
    x_security_token: str
    account_id: str
    created_at: datetime
    expires_at: datetime
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return datetime.now() < self.expires_at

@dataclass
class IGMarginInfo:
    """IG margin information for an instrument"""
    instrument: str
    margin_factor: float  # As percentage
    min_controlled_risk_stop_distance: float
    min_stop_distance: float
    currency: str
    margin_deposit_bands: List[Dict[str, float]]  # Tiered margin bands
    
class IGMarginAPI:
    """
    Real IG Markets API integration for margin data
    """
    
    def __init__(self):
        """Initialize IG API client"""
        self.config = get_secure_config()
        self.error_handler = get_error_handler()
        self.api_optimizer = get_api_request_optimizer()
        
        # API configuration
        self.base_url = self.config.get("ig.base_url", "https://demo-api.ig.com/gateway/deal")
        self.api_version = "3"
        
        # Session management
        self.session: Optional[IGSession] = None
        self.session_cache_file = "cache/ig_session.json"
        
        # Request caching
        self.margin_cache = {}  # instrument -> (margin_info, expiry_time)
        self.cache_duration = timedelta(minutes=15)
        
        # Initialize session
        self._load_cached_session()
        
        logger.info("🌐 IG Margin API initialized")
    
    def _load_cached_session(self):
        """Load cached session if available"""
        try:
            with open(self.session_cache_file, 'r') as f:
                data = json.load(f)
                self.session = IGSession(
                    cst=data["cst"],
                    x_security_token=data["x_security_token"],
                    account_id=data["account_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"])
                )
                
                if self.session.is_valid():
                    logger.info("✅ Loaded valid cached IG session")
                else:
                    logger.info("⏰ Cached session expired")
                    self.session = None
                    
        except Exception as e:
            logger.debug(f"No cached session available: {e}")
            self.session = None
    
    def _save_session(self):
        """Save session to cache"""
        if not self.session:
            return
        
        try:
            import os
            os.makedirs(os.path.dirname(self.session_cache_file), exist_ok=True)
            
            with open(self.session_cache_file, 'w') as f:
                json.dump({
                    "cst": self.session.cst,
                    "x_security_token": self.session.x_security_token,
                    "account_id": self.session.account_id,
                    "created_at": self.session.created_at.isoformat(),
                    "expires_at": self.session.expires_at.isoformat()
                }, f)
                
            logger.debug("💾 Session saved to cache")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    @with_error_handling(
        category=ErrorCategory.AUTHENTICATION_ERROR,
        severity=ErrorSeverity.HIGH,
        use_retry=True
    )
    def authenticate(self) -> bool:
        """
        Authenticate with IG API
        
        Returns:
            True if authentication successful
        """
        # Check if we have a valid session
        if self.session and self.session.is_valid():
            return True
        
        logger.info("🔐 Authenticating with IG API...")
        
        # Get credentials
        ig_creds = self.config.get_ig_credentials()
        
        # Prepare authentication request
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "VERSION": self.api_version,
            "X-IG-API-KEY": ig_creds["api_key"]
        }
        
        data = {
            "identifier": ig_creds["username"],
            "password": ig_creds["password"]
        }
        
        # Make authentication request
        response = requests.post(
            f"{self.base_url}/session",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            # Extract session tokens
            self.session = IGSession(
                cst=response.headers.get("CST"),
                x_security_token=response.headers.get("X-SECURITY-TOKEN"),
                account_id=response.json().get("currentAccountId"),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=6)  # IG sessions last 6 hours
            )
            
            # Save session
            self._save_session()
            
            logger.info(f"✅ Authentication successful - Account: {self.session.account_id}")
            return True
        else:
            logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests"""
        if not self.session:
            raise Exception("Not authenticated")
        
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "VERSION": self.api_version,
            "X-IG-API-KEY": self.config.get("ig.api_key"),
            "CST": self.session.cst,
            "X-SECURITY-TOKEN": self.session.x_security_token
        }
    
    @with_error_handling(
        category=ErrorCategory.API_ERROR,
        severity=ErrorSeverity.MEDIUM,
        use_retry=True
    )
    def get_market_details(self, instrument: str) -> Optional[Dict[str, Any]]:
        """
        Get market details including margin information
        
        Args:
            instrument: Market epic (e.g., "IX.D.FTSE.DAILY.IP")
            
        Returns:
            Market details dictionary or None
        """
        # Check cache first
        if instrument in self.margin_cache:
            cached_info, expiry = self.margin_cache[instrument]
            if datetime.now() < expiry:
                logger.debug(f"📦 Using cached market details for {instrument}")
                return cached_info
        
        # Ensure authenticated
        if not self.authenticate():
            return None
        
        logger.info(f"📡 Fetching market details for {instrument}")
        
        # Make API request through optimizer
        def fetch():
            response = requests.get(
                f"{self.base_url}/markets/{instrument}",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API error: {response.status_code} - {response.text}")
        
        try:
            # Submit through API optimizer
            result = self.api_optimizer.submit_request_sync(
                RequestType.MARGIN_RATE,
                RequestPriority.NORMAL,
                fetch
            )
            
            if result:
                # Cache the result
                self.margin_cache[instrument] = (result, datetime.now() + self.cache_duration)
                return result
                
        except Exception as e:
            logger.error(f"Failed to get market details for {instrument}: {e}")
            
        return None
    
    def get_margin_rate(self, instrument: str, position_size: float = 0) -> Optional[float]:
        """
        Get current margin rate for an instrument
        
        Args:
            instrument: Market epic
            position_size: Position size for tiered margin calculation
            
        Returns:
            Margin rate as decimal (e.g., 0.01 for 1%) or None
        """
        market_details = self.get_market_details(instrument)
        
        if not market_details:
            return None
        
        try:
            # Extract margin information
            instrument_data = market_details.get("instrument", {})
            margin_factor = instrument_data.get("marginFactor")
            
            if margin_factor:
                # Convert from percentage to decimal
                base_rate = float(margin_factor) / 100
                
                # Check for tiered margins
                margin_bands = instrument_data.get("marginDepositBands", [])
                if margin_bands and position_size > 0:
                    # Apply tiered margin based on position size
                    for band in margin_bands:
                        if position_size <= band.get("max", float('inf')):
                            band_margin = band.get("margin")
                            if band_margin:
                                return float(band_margin) / 100
                
                return base_rate
                
        except Exception as e:
            logger.error(f"Error parsing margin data: {e}")
        
        return None
    
    @with_error_handling(
        category=ErrorCategory.API_ERROR,
        severity=ErrorSeverity.MEDIUM,
        use_retry=True
    )
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information including balance and margin
        
        Returns:
            Account information dictionary or None
        """
        # Ensure authenticated
        if not self.authenticate():
            return None
        
        logger.info("💰 Fetching account information")
        
        try:
            response = requests.get(
                f"{self.base_url}/accounts",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                accounts = response.json().get("accounts", [])
                
                # Find current account
                for account in accounts:
                    if account.get("accountId") == self.session.account_id:
                        return {
                            "account_id": account.get("accountId"),
                            "account_name": account.get("accountName"),
                            "balance": account.get("balance", {}).get("balance", 0),
                            "available": account.get("balance", {}).get("available", 0),
                            "deposit": account.get("balance", {}).get("deposit", 0),
                            "profit_loss": account.get("balance", {}).get("profitLoss", 0),
                            "currency": account.get("currency", "GBP")
                        }
                        
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
        
        return None
    
    @with_error_handling(
        category=ErrorCategory.API_ERROR,
        severity=ErrorSeverity.MEDIUM,
        use_retry=True
    )
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions with margin information
        
        Returns:
            List of position dictionaries
        """
        # Ensure authenticated
        if not self.authenticate():
            return []
        
        logger.info("📊 Fetching open positions")
        
        try:
            response = requests.get(
                f"{self.base_url}/positions",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                positions_data = response.json().get("positions", [])
                positions = []
                
                for pos_data in positions_data:
                    position = pos_data.get("position", {})
                    market = pos_data.get("market", {})
                    
                    positions.append({
                        "deal_id": position.get("dealId"),
                        "instrument": market.get("epic"),
                        "direction": position.get("direction"),
                        "size": position.get("size"),
                        "level": position.get("level"),  # Entry price
                        "currency": position.get("currency"),
                        "controlled_risk": position.get("controlledRisk"),
                        "stop_level": position.get("stopLevel"),
                        "limit_level": position.get("limitLevel"),
                        "created_date": position.get("createdDate"),
                        "margin_requirement": self._calculate_position_margin(
                            market.get("epic"),
                            position.get("size", 0),
                            market.get("bid", position.get("level", 0))
                        )
                    })
                
                return positions
                
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
        
        return []
    
    def _calculate_position_margin(self, instrument: str, size: float, price: float) -> float:
        """
        Calculate margin requirement for a position
        
        Args:
            instrument: Market epic
            size: Position size
            price: Current price
            
        Returns:
            Margin requirement in account currency
        """
        margin_rate = self.get_margin_rate(instrument, size * price)
        
        if margin_rate:
            return size * price * margin_rate
        
        # Fallback to conservative estimate
        return size * price * 0.05  # 5% default
    
    def get_margin_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive margin summary
        
        Returns:
            Dictionary with margin information
        """
        account_info = self.get_account_info()
        positions = self.get_positions()
        
        if not account_info:
            return {
                "status": "error",
                "message": "Failed to get account information"
            }
        
        total_margin = sum(pos.get("margin_requirement", 0) for pos in positions)
        available_funds = account_info.get("available", 0)
        balance = account_info.get("balance", 0)
        
        margin_utilization = total_margin / balance if balance > 0 else 0
        
        return {
            "status": "success",
            "account_balance": balance,
            "available_funds": available_funds,
            "total_margin_required": total_margin,
            "margin_utilization": margin_utilization,
            "positions_count": len(positions),
            "can_open_positions": margin_utilization < 0.8,
            "currency": account_info.get("currency", "GBP"),
            "timestamp": datetime.now().isoformat()
        }
    
    def bulk_fetch_margin_rates(self, instruments: List[str]) -> Dict[str, float]:
        """
        Fetch margin rates for multiple instruments efficiently
        
        Args:
            instruments: List of market epics
            
        Returns:
            Dictionary of instrument -> margin rate
        """
        rates = {}
        
        for instrument in instruments:
            rate = self.get_margin_rate(instrument)
            if rate:
                rates[instrument] = rate
            else:
                # Use fallback rate
                rates[instrument] = 0.02  # 2% default
        
        logger.info(f"📦 Fetched margin rates for {len(rates)}/{len(instruments)} instruments")
        return rates
    
    def test_connection(self) -> bool:
        """
        Test IG API connection
        
        Returns:
            True if connection successful
        """
        try:
            # Try to authenticate
            if self.authenticate():
                # Try to get account info
                account = self.get_account_info()
                if account:
                    logger.info(f"✅ IG API connection successful - Account: {account.get('account_name')}")
                    return True
        except Exception as e:
            logger.error(f"❌ IG API connection failed: {e}")
        
        return False

# Global instance
_ig_margin_api = None

def get_ig_margin_api() -> IGMarginAPI:
    """Get global IG margin API instance"""
    global _ig_margin_api
    if _ig_margin_api is None:
        _ig_margin_api = IGMarginAPI()
    return _ig_margin_api

if __name__ == "__main__":
    # Test the IG Margin API
    print("🌐 Testing IG Margin API")
    print("=" * 50)
    
    api = IGMarginAPI()
    
    # Test connection
    print("\n🔌 Testing Connection:")
    if api.test_connection():
        print("✅ Connection successful")
        
        # Get account info
        print("\n💰 Account Information:")
        account = api.get_account_info()
        if account:
            print(f"  Balance: {account['currency']} {account['balance']:,.2f}")
            print(f"  Available: {account['currency']} {account['available']:,.2f}")
        
        # Test margin rate fetching
        print("\n📊 Margin Rates:")
        test_instruments = [
            "IX.D.FTSE.DAILY.IP",
            "IX.D.DAX.DAILY.IP",
            "CS.D.EURUSD.MINI.IP"
        ]
        
        for instrument in test_instruments:
            rate = api.get_margin_rate(instrument)
            if rate:
                print(f"  {instrument}: {rate*100:.2f}%")
            else:
                print(f"  {instrument}: Not available")
        
        # Get margin summary
        print("\n📈 Margin Summary:")
        summary = api.get_margin_summary()
        if summary["status"] == "success":
            print(f"  Margin Utilization: {summary['margin_utilization']*100:.1f}%")
            print(f"  Positions: {summary['positions_count']}")
            print(f"  Can Open Positions: {summary['can_open_positions']}")
    else:
        print("❌ Connection failed - check credentials")