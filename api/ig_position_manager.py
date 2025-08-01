# api/ig_position_manager.py

"""
🔧 IG Position Management API

Handles real-time position limit updates via IG's REST API.
Supports dynamic adjustment of stop loss and take profit levels.

Based on IG Labs API documentation:
https://labs.ig.com/rest-trading-api-reference
"""

import requests
import json
from datetime import datetime
from typing import Dict, Optional, List
import yaml

# Load configuration
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

class IGPositionManager:
    """
    Manages position updates via IG's REST API
    """
    
    def __init__(self):
        """Initialize IG API client"""
        self.ig_config = config["ig"]
        self.base_url = self.ig_config["base_url"]
        self.api_key = self.ig_config["api_key"]
        self.username = self.ig_config["username"]
        self.password = self.ig_config["password"]
        
        # Session tokens
        self.session_token = None
        self.cst_token = None
        self.account_id = None
        
        print("🔧 IG Position Manager initialized")
    
    def authenticate(self) -> bool:
        """Authenticate with IG API and get session tokens"""
        try:
            auth_url = f"{self.base_url}/session"
            
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json; charset=UTF-8",
                "X-IG-API-KEY": self.api_key,
                "Version": "2"
            }
            
            payload = {
                "identifier": self.username,
                "password": self.password
            }
            
            response = requests.post(auth_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                # Extract tokens from headers
                self.session_token = response.headers.get("X-SECURITY-TOKEN")
                self.cst_token = response.headers.get("CST")
                
                # Extract account ID from response
                response_data = response.json()
                accounts = response_data.get("accounts", [])
                if accounts:
                    self.account_id = accounts[0].get("accountId")
                
                print(f"✅ IG API authenticated successfully")
                print(f"   Account ID: {self.account_id}")
                return True
            else:
                print(f"❌ IG API authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error authenticating with IG API: {e}")
            return False
    
    def get_authenticated_headers(self) -> Dict[str, str]:
        """Get headers with authentication tokens"""
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json; charset=UTF-8",
            "X-IG-API-KEY": self.api_key,
            "X-SECURITY-TOKEN": self.session_token,
            "CST": self.cst_token,
            "Version": "2"
        }
    
    def get_position_details(self, deal_id: str) -> Optional[Dict]:
        """Get detailed information about a specific position"""
        try:
            if not self.session_token:
                if not self.authenticate():
                    return None
            
            positions_url = f"{self.base_url}/positions"
            headers = self.get_authenticated_headers()
            
            response = requests.get(positions_url, headers=headers)
            
            if response.status_code == 200:
                positions_data = response.json()
                positions = positions_data.get("positions", [])
                
                # Find the specific position by deal ID
                for position in positions:
                    if position.get("position", {}).get("dealId") == deal_id:
                        return position
                
                print(f"⚠️ Position with deal ID {deal_id} not found")
                return None
            else:
                print(f"❌ Failed to get positions: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting position details: {e}")
            return None
    
    def update_position_limits(self, deal_id: str, new_stop_level: Optional[float] = None, 
                              new_limit_level: Optional[float] = None) -> bool:
        """
        Update stop loss and/or take profit levels for a position
        
        Args:
            deal_id: IG deal identifier
            new_stop_level: New stop loss level (optional)
            new_limit_level: New take profit level (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_token:
                if not self.authenticate():
                    return False
            
            # First get current position details
            position = self.get_position_details(deal_id)
            if not position:
                return False
            
            # Extract current position info
            position_data = position.get("position", {})
            market_data = position.get("market", {})
            
            current_stop_level = position_data.get("stopLevel")
            current_limit_level = position_data.get("limitLevel")
            
            # Prepare update payload
            update_url = f"{self.base_url}/positions/otc/{deal_id}"
            headers = self.get_authenticated_headers()
            
            payload = {}
            
            # Add stop level if provided
            if new_stop_level is not None:
                payload["stopLevel"] = new_stop_level
                print(f"   Stop Level: {current_stop_level} → {new_stop_level}")
            
            # Add limit level if provided
            if new_limit_level is not None:
                payload["limitLevel"] = new_limit_level
                print(f"   Limit Level: {current_limit_level} → {new_limit_level}")
            
            if not payload:
                print("⚠️ No updates provided")
                return False
            
            print(f"🔧 Updating position {deal_id}:")
            
            # Make the API call
            response = requests.put(update_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                deal_status = response_data.get("dealStatus", "UNKNOWN")
                
                if deal_status == "ACCEPTED":
                    print(f"✅ Position {deal_id} updated successfully")
                    return True
                else:
                    print(f"❌ Position update rejected: {deal_status}")
                    reason = response_data.get("reason", "Unknown reason")
                    print(f"   Reason: {reason}")
                    return False
            else:
                print(f"❌ API call failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating position limits: {e}")
            return False
    
    def update_take_profit_only(self, deal_id: str, new_limit_level: float) -> bool:
        """Convenience method to update only take profit level"""
        return self.update_position_limits(deal_id, new_limit_level=new_limit_level)
    
    def update_stop_loss_only(self, deal_id: str, new_stop_level: float) -> bool:
        """Convenience method to update only stop loss level"""
        return self.update_position_limits(deal_id, new_stop_level=new_stop_level)
    
    def close_position(self, deal_id: str, size: Optional[float] = None) -> bool:
        """
        Close a position (full or partial)
        
        Args:
            deal_id: IG deal identifier
            size: Size to close (None for full closure)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_token:
                if not self.authenticate():
                    return False
            
            # Get position details first
            position = self.get_position_details(deal_id)
            if not position:
                return False
            
            position_data = position.get("position", {})
            current_size = position_data.get("size", 0)
            direction = position_data.get("direction")
            epic = position_data.get("epic")
            
            # Determine close size
            close_size = size if size is not None else current_size
            
            # Opposite direction for closing
            close_direction = "SELL" if direction == "BUY" else "BUY"
            
            close_url = f"{self.base_url}/positions/otc"
            headers = self.get_authenticated_headers()
            
            payload = {
                "deal_id": deal_id,
                "epic": epic,
                "direction": close_direction,
                "size": close_size,
                "order_type": "MARKET",
                "quote_id": None
            }
            
            print(f"🔴 Closing position {deal_id}: {close_size} units")
            
            response = requests.delete(close_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                deal_status = response_data.get("dealStatus", "UNKNOWN")
                
                if deal_status == "ACCEPTED":
                    print(f"✅ Position {deal_id} closed successfully")
                    return True
                else:
                    print(f"❌ Position close rejected: {deal_status}")
                    return False
            else:
                print(f"❌ Close API call failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error closing position: {e}")
            return False
    
    def get_all_positions(self) -> List[Dict]:
        """Get all current positions"""
        try:
            if not self.session_token:
                if not self.authenticate():
                    return []
            
            positions_url = f"{self.base_url}/positions"
            headers = self.get_authenticated_headers()
            
            response = requests.get(positions_url, headers=headers)
            
            if response.status_code == 200:
                positions_data = response.json()
                return positions_data.get("positions", [])
            else:
                print(f"❌ Failed to get positions: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting all positions: {e}")
            return []

# Global instance
_ig_position_manager = None

def get_ig_position_manager() -> IGPositionManager:
    """Get global IG position manager instance"""
    global _ig_position_manager
    if _ig_position_manager is None:
        _ig_position_manager = IGPositionManager()
    return _ig_position_manager

if __name__ == "__main__":
    # Test the IG position manager
    print("🧪 Testing IG Position Manager")
    print("=" * 50)
    
    manager = IGPositionManager()
    
    # Test authentication
    if manager.authenticate():
        print("✅ Authentication successful")
        
        # Get all positions
        positions = manager.get_all_positions()
        print(f"📊 Found {len(positions)} positions")
        
        if positions:
            # Show first position details
            first_position = positions[0]
            deal_id = first_position.get("position", {}).get("dealId")
            print(f"   Example position: {deal_id}")
            
            # Test getting specific position
            details = manager.get_position_details(deal_id)
            if details:
                print(f"   ✅ Got position details for {deal_id}")
    else:
        print("❌ Authentication failed")