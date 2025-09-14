# core/enhanced_margin_calculator.py

"""
📊 Enhanced Margin Calculator

Provides accurate margin utilization calculations with real account balance integration.
Handles time-based margin rate changes and position-specific margin requirements.

Key Features:
- Complete margin utilization calculation
- Account balance integration
- Position-specific margin requirements
- Risk-based position sizing
- Margin buffer management

Author: Risk Management Team
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import yaml

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import secure configuration
from core.secure_config import get_secure_config

@dataclass
class MarginRequirement:
    """Container for position margin requirements"""
    instrument: str
    position_value: float
    margin_rate: float
    margin_required: float
    margin_currency: str = "GBP"
    
@dataclass
class AccountMarginStatus:
    """Container for account margin status"""
    account_balance: float
    available_margin: float
    used_margin: float
    margin_utilization: float
    positions_count: int
    total_exposure: float
    margin_buffer: float
    margin_remaining: float
    status: str  # "healthy", "warning", "critical"
    can_open_positions: bool
    max_additional_exposure: float

class EnhancedMarginCalculator:
    """
    Advanced margin calculator that provides accurate margin utilization
    calculations with account balance integration.
    """
    
    def __init__(self, margin_rate_manager=None):
        """
        Initialize the enhanced margin calculator
        
        Args:
            margin_rate_manager: Instance of MarginRateManager for rate lookups
        """
        # Load configuration
        self.config = get_secure_config()
        margin_config = self.config.get("margin_management", {})
        risk_config = margin_config.get("risk_integration", {})
        
        self.margin_buffer_percent = risk_config.get("margin_buffer_percent", 10) / 100
        self.max_margin_utilization = risk_config.get("max_margin_utilization", 80) / 100
        self.margin_call_threshold = risk_config.get("margin_call_threshold", 90) / 100
        self.emergency_close_threshold = risk_config.get("emergency_close_threshold", 95) / 100
        
        # Margin rate manager for getting current rates
        self.margin_rate_manager = margin_rate_manager
        
        # Cache for account balance (would be updated from IG API)
        self._account_balance_cache = None
        self._balance_cache_time = None
        self._balance_cache_ttl = 60  # seconds
        
        logger.info("📊 Enhanced Margin Calculator initialized")
        logger.info(f"   Margin Buffer: {self.margin_buffer_percent*100:.0f}%")
        logger.info(f"   Max Utilization: {self.max_margin_utilization*100:.0f}%")
        logger.info(f"   Warning Threshold: {self.margin_call_threshold*100:.0f}%")
        logger.info(f"   Critical Threshold: {self.emergency_close_threshold*100:.0f}%")
    
    def calculate_position_margin(self, instrument: str, size: float, 
                                 current_price: float, direction: str = "BUY") -> MarginRequirement:
        """
        Calculate margin requirement for a specific position
        
        Args:
            instrument: Trading instrument (e.g., "IX.D.FTSE.DAILY.IP")
            size: Position size
            current_price: Current market price
            direction: Position direction ("BUY" or "SELL")
            
        Returns:
            MarginRequirement object with detailed margin information
        """
        # Calculate position value
        position_value = size * current_price
        
        # Get current margin rate from manager or use default
        if self.margin_rate_manager:
            margin_rate = self.margin_rate_manager.get_current_margin_rate(instrument, position_value)
        else:
            # Fallback to default rates
            margin_rate = self._get_default_margin_rate(instrument)
        
        # Calculate margin required
        margin_required = position_value * margin_rate
        
        return MarginRequirement(
            instrument=instrument,
            position_value=position_value,
            margin_rate=margin_rate,
            margin_required=margin_required
        )
    
    def calculate_account_margin_status(self, positions: List[Dict], 
                                       account_balance: Optional[float] = None) -> AccountMarginStatus:
        """
        Calculate comprehensive account margin status
        
        Args:
            positions: List of open positions
            account_balance: Current account balance (will fetch if not provided)
            
        Returns:
            AccountMarginStatus with complete margin utilization details
        """
        # Get account balance
        if account_balance is None:
            account_balance = self._get_account_balance()
        
        # Calculate total margin requirements
        total_margin_required = 0
        total_exposure = 0
        margin_requirements = []
        
        for position in positions:
            instrument = position.get('instrument', position.get('market', 'Unknown'))
            size = position.get('size', 0)
            current_price = position.get('current_price', position.get('bid', 0))
            
            if size > 0 and current_price > 0:
                margin_req = self.calculate_position_margin(instrument, size, current_price)
                margin_requirements.append(margin_req)
                total_margin_required += margin_req.margin_required
                total_exposure += margin_req.position_value
        
        # Calculate available margin (with buffer)
        available_margin = account_balance * (1 - self.margin_buffer_percent)
        
        # Calculate utilization
        margin_utilization = (total_margin_required / available_margin) if available_margin > 0 else 1.0
        margin_utilization = min(margin_utilization, 1.0)  # Cap at 100%
        
        # Calculate remaining margin
        margin_remaining = max(0, available_margin - total_margin_required)
        
        # Determine status
        if margin_utilization >= self.emergency_close_threshold:
            status = "critical"
        elif margin_utilization >= self.margin_call_threshold:
            status = "warning"
        else:
            status = "healthy"
        
        # Check if can open new positions
        can_open_positions = (margin_utilization < self.max_margin_utilization and 
                             status == "healthy")
        
        # Calculate maximum additional exposure allowed
        if can_open_positions and margin_remaining > 0:
            # Estimate average margin rate (simplified)
            avg_margin_rate = total_margin_required / total_exposure if total_exposure > 0 else 0.02
            max_additional_margin = available_margin * self.max_margin_utilization - total_margin_required
            max_additional_exposure = max_additional_margin / avg_margin_rate if avg_margin_rate > 0 else 0
        else:
            max_additional_exposure = 0
        
        return AccountMarginStatus(
            account_balance=account_balance,
            available_margin=available_margin,
            used_margin=total_margin_required,
            margin_utilization=margin_utilization,
            positions_count=len(positions),
            total_exposure=total_exposure,
            margin_buffer=account_balance * self.margin_buffer_percent,
            margin_remaining=margin_remaining,
            status=status,
            can_open_positions=can_open_positions,
            max_additional_exposure=max_additional_exposure
        )
    
    def calculate_position_size_for_risk(self, instrument: str, current_price: float,
                                        risk_amount: float, stop_loss_pips: float,
                                        account_balance: Optional[float] = None) -> Dict[str, float]:
        """
        Calculate optimal position size based on risk amount and margin constraints
        
        Args:
            instrument: Trading instrument
            current_price: Current market price
            risk_amount: Maximum risk amount in account currency
            stop_loss_pips: Stop loss distance in pips
            account_balance: Account balance (will fetch if not provided)
            
        Returns:
            Dictionary with recommended position size and margin details
        """
        if account_balance is None:
            account_balance = self._get_account_balance()
        
        # Calculate position size based on risk
        # Risk = Position Size × Stop Loss in Price
        stop_loss_price = stop_loss_pips  # Simplified - would need pip value calculation
        risk_based_size = risk_amount / stop_loss_price if stop_loss_price > 0 else 0
        
        # Get margin rate for this size
        test_value = risk_based_size * current_price
        if self.margin_rate_manager:
            margin_rate = self.margin_rate_manager.get_current_margin_rate(instrument, test_value)
        else:
            margin_rate = self._get_default_margin_rate(instrument)
        
        # Calculate margin requirement for risk-based size
        margin_required = test_value * margin_rate
        
        # Check margin constraints
        available_margin = account_balance * (1 - self.margin_buffer_percent) * self.max_margin_utilization
        
        if margin_required > available_margin:
            # Reduce size to fit margin constraints
            max_position_value = available_margin / margin_rate
            margin_based_size = max_position_value / current_price
            final_size = margin_based_size
            size_limited_by = "margin"
        else:
            final_size = risk_based_size
            size_limited_by = "risk"
        
        return {
            'recommended_size': final_size,
            'risk_based_size': risk_based_size,
            'margin_rate': margin_rate,
            'margin_required': final_size * current_price * margin_rate,
            'position_value': final_size * current_price,
            'size_limited_by': size_limited_by,
            'risk_amount': min(risk_amount, final_size * stop_loss_price),
            'margin_utilization_impact': (margin_required / (account_balance * (1 - self.margin_buffer_percent))) * 100
        }
    
    def check_margin_breach(self, positions: List[Dict], 
                           account_balance: Optional[float] = None) -> Dict[str, any]:
        """
        Check for margin breaches and recommend actions
        
        Args:
            positions: List of open positions
            account_balance: Current account balance
            
        Returns:
            Dictionary with breach status and recommended actions
        """
        margin_status = self.calculate_account_margin_status(positions, account_balance)
        
        breach_info = {
            'has_breach': False,
            'breach_type': None,
            'margin_utilization': margin_status.margin_utilization,
            'recommended_actions': [],
            'positions_to_close': []
        }
        
        if margin_status.margin_utilization >= self.emergency_close_threshold:
            breach_info['has_breach'] = True
            breach_info['breach_type'] = 'emergency'
            breach_info['recommended_actions'].append('IMMEDIATE: Close positions to reduce margin')
            
            # Calculate how much margin needs to be freed
            target_margin = margin_status.available_margin * self.margin_call_threshold
            margin_to_free = margin_status.used_margin - target_margin
            
            # Recommend positions to close (simplified - would need more sophisticated logic)
            breach_info['positions_to_close'] = self._recommend_positions_to_close(
                positions, margin_to_free
            )
            
        elif margin_status.margin_utilization >= self.margin_call_threshold:
            breach_info['has_breach'] = True
            breach_info['breach_type'] = 'warning'
            breach_info['recommended_actions'].extend([
                'WARNING: Approaching margin limit',
                'Consider closing some positions',
                'Do not open new positions'
            ])
        
        return breach_info
    
    def _recommend_positions_to_close(self, positions: List[Dict], 
                                     margin_to_free: float) -> List[Dict]:
        """
        Recommend which positions to close to free up margin
        
        Args:
            positions: List of open positions
            margin_to_free: Amount of margin that needs to be freed
            
        Returns:
            List of positions recommended for closure
        """
        recommendations = []
        total_margin_freed = 0
        
        # Sort positions by P&L (close losing positions first)
        sorted_positions = sorted(positions, key=lambda p: p.get('unrealized_pnl', 0))
        
        for position in sorted_positions:
            if total_margin_freed >= margin_to_free:
                break
            
            margin_req = self.calculate_position_margin(
                position.get('instrument', 'Unknown'),
                position.get('size', 0),
                position.get('current_price', 0)
            )
            
            recommendations.append({
                'deal_reference': position.get('deal_reference'),
                'instrument': position.get('instrument'),
                'margin_freed': margin_req.margin_required,
                'unrealized_pnl': position.get('unrealized_pnl', 0)
            })
            
            total_margin_freed += margin_req.margin_required
        
        return recommendations
    
    def _get_account_balance(self) -> float:
        """
        Get current account balance (with caching)
        
        Returns:
            Account balance in base currency
        """
        # Check cache
        if (self._account_balance_cache is not None and 
            self._balance_cache_time is not None):
            cache_age = (datetime.now() - self._balance_cache_time).total_seconds()
            if cache_age < self._balance_cache_ttl:
                return self._account_balance_cache
        
        # In production, this would call IG API
        # For now, return a default value
        default_balance = 10000.0  # £10,000 default
        
        # Update cache
        self._account_balance_cache = default_balance
        self._balance_cache_time = datetime.now()
        
        return default_balance
    
    def update_account_balance(self, balance: float):
        """
        Update cached account balance
        
        Args:
            balance: New account balance
        """
        self._account_balance_cache = balance
        self._balance_cache_time = datetime.now()
        logger.info(f"💰 Account balance updated: £{balance:,.2f}")
    
    def _get_default_margin_rate(self, instrument: str) -> float:
        """
        Get default margin rate for instrument
        
        Args:
            instrument: Trading instrument
            
        Returns:
            Default margin rate
        """
        # Simple classification based on instrument code
        instrument_upper = instrument.upper()
        
        if "IX.D." in instrument_upper:  # Indices
            return 0.02  # 2% default
        elif "CS.D." in instrument_upper:  # Forex
            return 0.033  # 3.3% default
        elif "CC.D." in instrument_upper:  # Commodities
            return 0.05  # 5% default
        else:
            return 0.05  # 5% conservative default
    
    def get_margin_health_report(self, positions: List[Dict], 
                                account_balance: Optional[float] = None) -> str:
        """
        Generate a formatted margin health report
        
        Args:
            positions: List of open positions
            account_balance: Account balance
            
        Returns:
            Formatted string report
        """
        status = self.calculate_account_margin_status(positions, account_balance)
        
        # Determine emoji based on status
        if status.status == "critical":
            status_emoji = "🚨"
        elif status.status == "warning":
            status_emoji = "⚠️"
        else:
            status_emoji = "✅"
        
        report = f"""
╔══════════════════════════════════════════════════════╗
║           MARGIN HEALTH REPORT                        ║
╠══════════════════════════════════════════════════════╣
║ Status: {status_emoji} {status.status.upper():<43}║
║                                                       ║
║ Account Balance:     £{status.account_balance:>15,.2f}        ║
║ Available Margin:    £{status.available_margin:>15,.2f}        ║
║ Used Margin:         £{status.used_margin:>15,.2f}        ║
║ Margin Buffer:       £{status.margin_buffer:>15,.2f}        ║
║ Margin Remaining:    £{status.margin_remaining:>15,.2f}        ║
║                                                       ║
║ Margin Utilization:  {status.margin_utilization*100:>15.1f}%        ║
║ Total Exposure:      £{status.total_exposure:>15,.2f}        ║
║ Open Positions:      {status.positions_count:>16}        ║
║                                                       ║
║ Can Open Positions:  {str(status.can_open_positions):>16}        ║
║ Max New Exposure:    £{status.max_additional_exposure:>15,.2f}        ║
╚══════════════════════════════════════════════════════╝
"""
        return report

# Global instance
_margin_calculator = None

def get_margin_calculator(margin_rate_manager=None) -> EnhancedMarginCalculator:
    """Get global margin calculator instance"""
    global _margin_calculator
    if _margin_calculator is None:
        _margin_calculator = EnhancedMarginCalculator(margin_rate_manager)
    return _margin_calculator

if __name__ == "__main__":
    # Test the enhanced margin calculator
    print("🧪 Testing Enhanced Margin Calculator")
    print("=" * 50)
    
    calculator = EnhancedMarginCalculator()
    
    # Test position margin calculation
    print("\n📊 Single Position Margin Calculation:")
    margin_req = calculator.calculate_position_margin(
        instrument="IX.D.FTSE.DAILY.IP",
        size=10,
        current_price=7500
    )
    print(f"Position Value: £{margin_req.position_value:,.2f}")
    print(f"Margin Rate: {margin_req.margin_rate*100:.2f}%")
    print(f"Margin Required: £{margin_req.margin_required:,.2f}")
    
    # Test account margin status
    print("\n💰 Account Margin Status:")
    test_positions = [
        {'instrument': 'IX.D.FTSE.DAILY.IP', 'size': 10, 'current_price': 7500},
        {'instrument': 'IX.D.DAX.DAILY.IP', 'size': 5, 'current_price': 15000},
        {'instrument': 'CS.D.EURUSD.MINI.IP', 'size': 100, 'current_price': 1.1000}
    ]
    
    status = calculator.calculate_account_margin_status(test_positions, account_balance=10000)
    print(f"Margin Utilization: {status.margin_utilization*100:.1f}%")
    print(f"Status: {status.status}")
    print(f"Can Open Positions: {status.can_open_positions}")
    print(f"Max Additional Exposure: £{status.max_additional_exposure:,.2f}")
    
    # Test position sizing
    print("\n📏 Position Size Calculation:")
    size_calc = calculator.calculate_position_size_for_risk(
        instrument="IX.D.FTSE.DAILY.IP",
        current_price=7500,
        risk_amount=100,  # Risk £100
        stop_loss_pips=10,
        account_balance=10000
    )
    print(f"Recommended Size: {size_calc['recommended_size']:.2f}")
    print(f"Size Limited By: {size_calc['size_limited_by']}")
    print(f"Margin Impact: {size_calc['margin_utilization_impact']:.1f}%")
    
    # Generate health report
    print("\n📋 Margin Health Report:")
    print(calculator.get_margin_health_report(test_positions, 10000))