#!/usr/bin/env python3
"""
📏 Dynamic Position Sizing Module

Implements sophisticated position sizing algorithms including:
- Kelly Criterion for optimal position sizing
- Volatility-adjusted sizing
- Risk percentage-based sizing  
- Account balance scaling

Prevents the fixed-size disaster that led to August 8th overtrading.

Author: Risk Management Team
"""

import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import yaml
from dataclasses import dataclass

# Load configuration
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

from data.db import get_account_balance, trades_collection

@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    recommended_size: float
    max_size: float
    risk_amount: float
    sizing_method: str
    confidence: float
    warnings: List[str]

class DynamicPositionSizer:
    """
    Professional-grade position sizing system
    """
    
    def __init__(self):
        """Initialize position sizer with conservative defaults"""
        
        # RISK PARAMETERS - Conservative institutional settings
        self.MAX_RISK_PER_TRADE = 0.01      # 1% max risk per trade
        self.MAX_POSITION_SIZE = 0.02       # 2% max position size  
        self.MAX_TOTAL_EXPOSURE = 0.10      # 10% max total exposure
        self.MIN_KELLY_FRACTION = 0.001     # Minimum Kelly fraction
        self.MAX_KELLY_FRACTION = 0.025     # Maximum Kelly fraction (cap at 2.5%)
        self.VOLATILITY_SCALING_FACTOR = 2.0 # Scale position inverse to volatility
        
        # ACCOUNT PROTECTION
        self.MIN_ACCOUNT_BALANCE = 1000.0   # Minimum balance to trade
        self.EMERGENCY_BALANCE_RATIO = 0.20 # Stop trading if balance < 20% of peak
        
        # POSITION SIZING METHODS
        self.DEFAULT_METHOD = "kelly_volatility_hybrid"
        
        print("📏 Dynamic Position Sizer initialized")
        print(f"   Max risk per trade: {self.MAX_RISK_PER_TRADE:.1%}")
        print(f"   Max position size: {self.MAX_POSITION_SIZE:.1%}")
        print(f"   Kelly fraction range: {self.MIN_KELLY_FRACTION:.1%} - {self.MAX_KELLY_FRACTION:.1%}")
    
    def calculate_optimal_size(self, 
                             market: str,
                             direction: str,
                             current_price: float,
                             stop_loss: float,
                             take_profit: float,
                             signal_confidence: float = 0.7,
                             volatility: Optional[float] = None) -> PositionSizeResult:
        """
        Calculate optimal position size using multiple methods
        """
        print(f"📏 Calculating optimal position size for {market}")
        
        warnings = []
        account_balance = get_account_balance()
        
        # Validate inputs
        if account_balance < self.MIN_ACCOUNT_BALANCE:
            warnings.append(f"Account balance too low: £{account_balance:.2f}")
            return self._create_zero_size_result("insufficient_balance", warnings)
        
        if current_price <= 0 or stop_loss <= 0:
            warnings.append("Invalid price or stop loss")
            return self._create_zero_size_result("invalid_inputs", warnings)
        
        # Calculate position risk
        if direction.upper() == "BUY":
            risk_per_unit = abs(current_price - stop_loss)
            reward_per_unit = abs(take_profit - current_price)
        else:  # SELL
            risk_per_unit = abs(stop_loss - current_price)
            reward_per_unit = abs(current_price - take_profit)
        
        if risk_per_unit <= 0:
            warnings.append("Invalid risk calculation - stop loss too close")
            return self._create_zero_size_result("invalid_risk", warnings)
        
        risk_reward_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
        
        print(f"   Risk per unit: £{risk_per_unit:.2f}")
        print(f"   Reward per unit: £{reward_per_unit:.2f}")
        print(f"   Risk/Reward ratio: {risk_reward_ratio:.2f}:1")
        
        # Get market volatility if not provided
        if volatility is None:
            volatility = self._calculate_market_volatility(market)
        
        print(f"   Market volatility: {volatility:.2%}")
        print(f"   Signal confidence: {signal_confidence:.1%}")
        
        # Calculate sizes using different methods
        size_calculations = {}
        
        # Method 1: Fixed risk percentage
        size_calculations['fixed_risk'] = self._calculate_fixed_risk_size(
            account_balance, risk_per_unit)
        
        # Method 2: Kelly Criterion
        size_calculations['kelly'] = self._calculate_kelly_size(
            market, account_balance, risk_per_unit, reward_per_unit, signal_confidence)
        
        # Method 3: Volatility-adjusted
        size_calculations['volatility_adjusted'] = self._calculate_volatility_adjusted_size(
            account_balance, risk_per_unit, volatility)
        
        # Method 4: Hybrid approach (recommended)
        size_calculations['kelly_volatility_hybrid'] = self._calculate_hybrid_size(
            size_calculations, signal_confidence, volatility)
        
        # Select optimal size
        recommended_method = self.DEFAULT_METHOD
        recommended_size = size_calculations[recommended_method]
        
        # Apply constraints
        max_size_by_risk = (account_balance * self.MAX_RISK_PER_TRADE) / risk_per_unit
        max_size_by_position = account_balance * self.MAX_POSITION_SIZE / current_price
        max_size_by_exposure = self._calculate_max_size_by_exposure(account_balance, current_price)
        
        max_size = min(max_size_by_risk, max_size_by_position, max_size_by_exposure)
        final_size = min(recommended_size, max_size)
        
        # Final safety checks
        if final_size < 0.1:  # Minimum viable position
            warnings.append("Position size too small to be viable")
            final_size = 0
        
        # Calculate actual risk amount
        risk_amount = final_size * risk_per_unit
        
        print(f"   Recommended method: {recommended_method}")
        print(f"   Calculated sizes: {[(k, f'{v:.2f}') for k, v in size_calculations.items()]}")
        print(f"   Max size constraints: Risk: {max_size_by_risk:.2f}, Position: {max_size_by_position:.2f}, Exposure: {max_size_by_exposure:.2f}")
        print(f"   Final size: {final_size:.2f} units")
        print(f"   Risk amount: £{risk_amount:.2f} ({risk_amount/account_balance:.1%} of account)")
        
        return PositionSizeResult(
            recommended_size=final_size,
            max_size=max_size,
            risk_amount=risk_amount,
            sizing_method=recommended_method,
            confidence=signal_confidence,
            warnings=warnings
        )
    
    def _calculate_fixed_risk_size(self, account_balance: float, risk_per_unit: float) -> float:
        """Calculate position size based on fixed risk percentage"""
        max_risk_amount = account_balance * self.MAX_RISK_PER_TRADE
        return max_risk_amount / risk_per_unit
    
    def _calculate_kelly_size(self, market: str, account_balance: float, 
                            risk_per_unit: float, reward_per_unit: float,
                            signal_confidence: float) -> float:
        """Calculate Kelly Criterion position size"""
        
        # Get historical win rate for this market
        win_rate = self._get_historical_win_rate(market)
        
        # Adjust win rate based on signal confidence
        adjusted_win_rate = win_rate * signal_confidence
        
        # Kelly formula: f = (bp - q) / b
        # where b = reward/risk ratio, p = win rate, q = loss rate (1-p)
        if risk_per_unit > 0:
            b = reward_per_unit / risk_per_unit
            p = adjusted_win_rate
            q = 1 - p
            
            kelly_fraction = (b * p - q) / b if b > 0 else 0
        else:
            kelly_fraction = 0
        
        # Cap Kelly fraction for safety
        kelly_fraction = max(self.MIN_KELLY_FRACTION, 
                           min(kelly_fraction, self.MAX_KELLY_FRACTION))
        
        kelly_size = (account_balance * kelly_fraction) / risk_per_unit
        
        print(f"   Kelly calculation: Win rate: {win_rate:.1%}, Adjusted: {adjusted_win_rate:.1%}")
        print(f"   Kelly fraction: {kelly_fraction:.1%}, Kelly size: {kelly_size:.2f}")
        
        return kelly_size
    
    def _calculate_volatility_adjusted_size(self, account_balance: float, 
                                          risk_per_unit: float, volatility: float) -> float:
        """Calculate position size adjusted for market volatility"""
        # Higher volatility = smaller position size
        base_size = self._calculate_fixed_risk_size(account_balance, risk_per_unit)
        
        # Volatility adjustment factor (inverse relationship)
        volatility_factor = 1 / (1 + volatility * self.VOLATILITY_SCALING_FACTOR)
        
        adjusted_size = base_size * volatility_factor
        
        print(f"   Volatility adjustment: Factor: {volatility_factor:.2f}, Size: {adjusted_size:.2f}")
        
        return adjusted_size
    
    def _calculate_hybrid_size(self, size_calculations: Dict[str, float], 
                             signal_confidence: float, volatility: float) -> float:
        """Calculate hybrid size combining multiple methods"""
        
        # Weight different methods based on market conditions
        kelly_weight = signal_confidence  # Higher confidence = more Kelly
        volatility_weight = min(volatility * 2, 0.5)  # Higher vol = more vol adjustment
        fixed_weight = 1 - kelly_weight - volatility_weight
        fixed_weight = max(0.2, fixed_weight)  # Minimum base weight
        
        # Normalize weights
        total_weight = kelly_weight + volatility_weight + fixed_weight
        kelly_weight /= total_weight
        volatility_weight /= total_weight
        fixed_weight /= total_weight
        
        # Calculate weighted average
        hybrid_size = (
            size_calculations['kelly'] * kelly_weight +
            size_calculations['volatility_adjusted'] * volatility_weight +
            size_calculations['fixed_risk'] * fixed_weight
        )
        
        print(f"   Hybrid weights: Kelly: {kelly_weight:.1%}, Vol: {volatility_weight:.1%}, Fixed: {fixed_weight:.1%}")
        
        return hybrid_size
    
    def _calculate_max_size_by_exposure(self, account_balance: float, current_price: float) -> float:
        """Calculate maximum size based on total exposure limits"""
        
        # Get current total exposure
        current_exposure = self._get_current_total_exposure()
        max_total_exposure = account_balance * self.MAX_TOTAL_EXPOSURE
        remaining_exposure = max_total_exposure - current_exposure
        
        if remaining_exposure <= 0:
            return 0
        
        max_size_by_exposure = remaining_exposure / current_price
        
        print(f"   Exposure limits: Current: £{current_exposure:.2f}, Max: £{max_total_exposure:.2f}")
        print(f"   Remaining exposure: £{remaining_exposure:.2f}")
        
        return max_size_by_exposure
    
    def _get_current_total_exposure(self) -> float:
        """Calculate current total exposure from open positions"""
        try:
            # Get all open positions
            open_positions = list(trades_collection.find({"status": "OPEN"}))
            
            total_exposure = 0
            for position in open_positions:
                entry_price = position.get('entry_price', 0)
                size = position.get('size', 0)
                if entry_price and size:
                    position_value = abs(entry_price * size)
                    total_exposure += position_value
            
            return total_exposure
            
        except Exception as e:
            print(f"⚠️ Error calculating current exposure: {e}")
            return 0
    
    def _get_historical_win_rate(self, market: str, lookback_days: int = 30) -> float:
        """Get historical win rate for the market"""
        try:
            # Look back 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Get closed trades for this market
            historical_trades = list(trades_collection.find({
                "market": market,
                "status": "CLOSED",
                "timestamp": {"$gte": cutoff_date},
                "profit_loss": {"$exists": True}
            }))
            
            if len(historical_trades) < 10:  # Need minimum sample size
                return 0.5  # Default to 50% if insufficient data
            
            winning_trades = [t for t in historical_trades if t.get('profit_loss', 0) > 0]
            win_rate = len(winning_trades) / len(historical_trades)
            
            print(f"   Historical data: {len(historical_trades)} trades, {len(winning_trades)} wins, {win_rate:.1%} win rate")
            
            return win_rate
            
        except Exception as e:
            print(f"⚠️ Error calculating win rate: {e}")
            return 0.5  # Default fallback
    
    def _calculate_market_volatility(self, market: str, lookback_periods: int = 20) -> float:
        """Calculate recent market volatility"""
        try:
            from data.db import get_market_tick_data
            
            # Get recent tick data
            recent_ticks = get_market_tick_data(market, limit=lookback_periods * 5)
            
            if len(recent_ticks) < lookback_periods:
                return 0.02  # Default 2% volatility
            
            # Calculate returns from bid prices
            prices = [tick['bid'] for tick in recent_ticks[-lookback_periods:]]
            returns = []
            
            for i in range(1, len(prices)):
                return_pct = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(return_pct)
            
            if returns:
                volatility = np.std(returns)
                return max(0.001, min(0.1, volatility))  # Cap between 0.1% and 10%
            else:
                return 0.02
                
        except Exception as e:
            print(f"⚠️ Error calculating volatility: {e}")
            return 0.02  # Default fallback
    
    def _create_zero_size_result(self, reason: str, warnings: List[str]) -> PositionSizeResult:
        """Create a zero-size result for invalid conditions"""
        return PositionSizeResult(
            recommended_size=0.0,
            max_size=0.0,
            risk_amount=0.0,
            sizing_method=reason,
            confidence=0.0,
            warnings=warnings
        )
    
    def validate_position_size(self, size: float, market: str, current_price: float) -> Tuple[bool, str]:
        """Validate if a position size is acceptable"""
        
        account_balance = get_account_balance()
        
        # Check minimum account balance
        if account_balance < self.MIN_ACCOUNT_BALANCE:
            return False, f"Account balance too low: £{account_balance:.2f}"
        
        # Check maximum position size
        position_value = size * current_price
        position_percentage = position_value / account_balance
        
        if position_percentage > self.MAX_POSITION_SIZE:
            return False, f"Position size {position_percentage:.1%} exceeds maximum {self.MAX_POSITION_SIZE:.1%}"
        
        # Check total exposure
        current_exposure = self._get_current_total_exposure()
        total_exposure = current_exposure + position_value
        max_total_exposure = account_balance * self.MAX_TOTAL_EXPOSURE
        
        if total_exposure > max_total_exposure:
            return False, f"Total exposure £{total_exposure:.2f} would exceed maximum £{max_total_exposure:.2f}"
        
        return True, "Position size validated"

# Global instance
_position_sizer = None

def get_position_sizer() -> DynamicPositionSizer:
    """Get global position sizer instance"""
    global _position_sizer
    if _position_sizer is None:
        _position_sizer = DynamicPositionSizer()
    return _position_sizer