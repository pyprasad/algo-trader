#!/usr/bin/env python3
"""
🚨 Enhanced Circuit Breaker System

Advanced safety system with multiple circuit breakers to prevent:
- Overtrading disasters (like August 8th's 262 trades)
- Consecutive loss spirals
- Correlation exposure risks
- System malfunction scenarios
- Market volatility extremes

Institutional-grade protection with granular controls.

Author: Risk Management Team
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import yaml

# Load configuration
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

from data.db import get_account_balance, trades_collection, get_open_trades

@dataclass
class CircuitBreakerStatus:
    """Status of a circuit breaker"""
    name: str
    is_active: bool
    trigger_value: float
    threshold: float
    trigger_time: Optional[datetime]
    description: str
    severity: str  # 'WARNING', 'CRITICAL', 'EMERGENCY'

class CircuitBreakerType(Enum):
    """Types of circuit breakers"""
    DAILY_LOSS = "daily_loss"
    CONSECUTIVE_LOSSES = "consecutive_losses"
    HOURLY_TRADE_LIMIT = "hourly_trade_limit"
    DAILY_TRADE_LIMIT = "daily_trade_limit"
    CORRELATION_EXPOSURE = "correlation_exposure"
    VOLATILITY_SPIKE = "volatility_spike"
    SPREAD_WIDENING = "spread_widening"
    SYSTEM_LATENCY = "system_latency"
    DRAWDOWN_LIMIT = "drawdown_limit"
    POSITION_CONCENTRATION = "position_concentration"
    RAPID_FIRE_TRADING = "rapid_fire_trading"
    MARGIN_UTILIZATION = "margin_utilization"

class EnhancedCircuitBreakers:
    """
    Comprehensive circuit breaker system with multiple safety layers
    """
    
    def __init__(self):
        """Initialize with institutional-grade thresholds"""
        
        # CIRCUIT BREAKER THRESHOLDS
        self.thresholds = {
            # LOSS PROTECTION
            CircuitBreakerType.DAILY_LOSS: 0.05,           # 5% daily loss limit
            CircuitBreakerType.CONSECUTIVE_LOSSES: 5,       # Max 5 consecutive losses
            CircuitBreakerType.DRAWDOWN_LIMIT: 0.15,        # 15% max drawdown from peak
            
            # OVERTRADING PROTECTION  
            CircuitBreakerType.HOURLY_TRADE_LIMIT: 5,       # Max 5 trades per hour
            CircuitBreakerType.DAILY_TRADE_LIMIT: 20,       # Max 20 trades per day
            CircuitBreakerType.RAPID_FIRE_TRADING: 3,       # Max 3 trades in 10 minutes
            
            # RISK CONCENTRATION
            CircuitBreakerType.CORRELATION_EXPOSURE: 0.08,  # Max 8% in correlated markets
            CircuitBreakerType.POSITION_CONCENTRATION: 0.25, # Max 25% in single position
            CircuitBreakerType.MARGIN_UTILIZATION: 0.80,    # Max 80% margin utilization
            
            # MARKET CONDITIONS
            CircuitBreakerType.VOLATILITY_SPIKE: 0.08,      # 8% volatility spike
            CircuitBreakerType.SPREAD_WIDENING: 0.005,      # 0.5% spread cost
            CircuitBreakerType.SYSTEM_LATENCY: 5.0,         # 5 second max latency
        }
        
        # COOLING PERIODS (how long breaker stays active)
        self.cooling_periods = {
            CircuitBreakerType.DAILY_LOSS: timedelta(hours=24),
            CircuitBreakerType.CONSECUTIVE_LOSSES: timedelta(hours=2),
            CircuitBreakerType.HOURLY_TRADE_LIMIT: timedelta(hours=1),
            CircuitBreakerType.DAILY_TRADE_LIMIT: timedelta(hours=24),
            CircuitBreakerType.CORRELATION_EXPOSURE: timedelta(minutes=30),
            CircuitBreakerType.VOLATILITY_SPIKE: timedelta(minutes=15),
            CircuitBreakerType.SPREAD_WIDENING: timedelta(minutes=5),
            CircuitBreakerType.SYSTEM_LATENCY: timedelta(minutes=2),
            CircuitBreakerType.DRAWDOWN_LIMIT: timedelta(hours=4),
            CircuitBreakerType.POSITION_CONCENTRATION: timedelta(minutes=30),
            CircuitBreakerType.RAPID_FIRE_TRADING: timedelta(minutes=30),
            CircuitBreakerType.MARGIN_UTILIZATION: timedelta(minutes=15),
        }
        
        # SEVERITY LEVELS
        self.severity_levels = {
            CircuitBreakerType.DAILY_LOSS: 'EMERGENCY',
            CircuitBreakerType.CONSECUTIVE_LOSSES: 'CRITICAL',
            CircuitBreakerType.DRAWDOWN_LIMIT: 'EMERGENCY',
            CircuitBreakerType.HOURLY_TRADE_LIMIT: 'WARNING',
            CircuitBreakerType.DAILY_TRADE_LIMIT: 'CRITICAL',
            CircuitBreakerType.RAPID_FIRE_TRADING: 'CRITICAL',
            CircuitBreakerType.CORRELATION_EXPOSURE: 'WARNING',
            CircuitBreakerType.POSITION_CONCENTRATION: 'WARNING',
            CircuitBreakerType.MARGIN_UTILIZATION: 'CRITICAL',
            CircuitBreakerType.VOLATILITY_SPIKE: 'WARNING',
            CircuitBreakerType.SPREAD_WIDENING: 'WARNING',
            CircuitBreakerType.SYSTEM_LATENCY: 'CRITICAL',
        }
        
        # State tracking
        self.active_breakers = {}
        self.breaker_history = []
        self.peak_balance = get_account_balance()
        
        print("🚨 Enhanced Circuit Breaker System initialized")
        print(f"   {len(self.thresholds)} circuit breakers configured")
        print(f"   Severity levels: WARNING, CRITICAL, EMERGENCY")
    
    def check_all_circuit_breakers(self, market: str = None, 
                                 trade_data: Dict = None) -> Tuple[bool, List[CircuitBreakerStatus]]:
        """
        Check all circuit breakers - returns (can_trade, active_breakers)
        """
        
        active_breakers = []
        can_trade = True
        
        # Check each circuit breaker type
        for breaker_type in CircuitBreakerType:
            status = self._check_individual_breaker(breaker_type, market, trade_data)
            
            if status.is_active:
                active_breakers.append(status)
                
                # Emergency and Critical breakers block all trading
                if status.severity in ['EMERGENCY', 'CRITICAL']:
                    can_trade = False
                
                # Update active breakers tracking
                self.active_breakers[breaker_type] = status
        
        # Remove expired breakers
        self._clean_expired_breakers()
        
        if active_breakers:
            print(f"🚨 {len(active_breakers)} circuit breakers active:")
            for breaker in active_breakers:
                print(f"   {breaker.severity}: {breaker.name} - {breaker.description}")
        
        return can_trade, active_breakers
    
    def _check_individual_breaker(self, breaker_type: CircuitBreakerType, 
                                market: str, trade_data: Dict) -> CircuitBreakerStatus:
        """Check individual circuit breaker"""
        
        current_time = datetime.utcnow()
        
        # Check if breaker is already active and not expired
        if breaker_type in self.active_breakers:
            existing_breaker = self.active_breakers[breaker_type]
            cooling_period = self.cooling_periods[breaker_type]
            
            if existing_breaker.trigger_time and \
               current_time - existing_breaker.trigger_time < cooling_period:
                return existing_breaker  # Still active
        
        # Check specific breaker conditions
        is_triggered, current_value, description = self._evaluate_breaker_condition(
            breaker_type, market, trade_data)
        
        if is_triggered:
            # Create new active breaker
            status = CircuitBreakerStatus(
                name=breaker_type.value,
                is_active=True,
                trigger_value=current_value,
                threshold=self.thresholds[breaker_type],
                trigger_time=current_time,
                description=description,
                severity=self.severity_levels[breaker_type]
            )
            
            # Log breaker activation
            self._log_breaker_activation(status)
            
            return status
        else:
            # Breaker not triggered
            return CircuitBreakerStatus(
                name=breaker_type.value,
                is_active=False,
                trigger_value=current_value,
                threshold=self.thresholds[breaker_type],
                trigger_time=None,
                description=description,
                severity=self.severity_levels[breaker_type]
            )
    
    def _evaluate_breaker_condition(self, breaker_type: CircuitBreakerType, 
                                  market: str, trade_data: Dict) -> Tuple[bool, float, str]:
        """Evaluate specific breaker condition"""
        
        if breaker_type == CircuitBreakerType.DAILY_LOSS:
            return self._check_daily_loss()
        
        elif breaker_type == CircuitBreakerType.CONSECUTIVE_LOSSES:
            return self._check_consecutive_losses()
        
        elif breaker_type == CircuitBreakerType.HOURLY_TRADE_LIMIT:
            return self._check_hourly_trade_limit()
        
        elif breaker_type == CircuitBreakerType.DAILY_TRADE_LIMIT:
            return self._check_daily_trade_limit()
        
        elif breaker_type == CircuitBreakerType.RAPID_FIRE_TRADING:
            return self._check_rapid_fire_trading(market)
        
        elif breaker_type == CircuitBreakerType.CORRELATION_EXPOSURE:
            return self._check_correlation_exposure()
        
        elif breaker_type == CircuitBreakerType.POSITION_CONCENTRATION:
            return self._check_position_concentration()
        
        elif breaker_type == CircuitBreakerType.MARGIN_UTILIZATION:
            return self._check_margin_utilization()
        
        elif breaker_type == CircuitBreakerType.DRAWDOWN_LIMIT:
            return self._check_drawdown_limit()
        
        elif breaker_type == CircuitBreakerType.VOLATILITY_SPIKE:
            return self._check_volatility_spike(market, trade_data)
        
        elif breaker_type == CircuitBreakerType.SPREAD_WIDENING:
            return self._check_spread_widening(trade_data)
        
        elif breaker_type == CircuitBreakerType.SYSTEM_LATENCY:
            return self._check_system_latency()
        
        else:
            return False, 0.0, "Unknown breaker type"
    
    def _check_daily_loss(self) -> Tuple[bool, float, str]:
        """Check daily loss limit"""
        try:
            # Get today's trades
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = list(trades_collection.find({
                "timestamp": {"$gte": today},
                "profit_loss": {"$exists": True, "$ne": None}
            }))
            
            daily_pnl = sum(trade.get('profit_loss', 0) for trade in today_trades)
            account_balance = get_account_balance()
            daily_loss_percentage = abs(daily_pnl) / account_balance if account_balance > 0 else 0
            
            threshold = self.thresholds[CircuitBreakerType.DAILY_LOSS]
            is_triggered = daily_pnl < 0 and daily_loss_percentage >= threshold
            
            description = f"Daily P&L: £{daily_pnl:.2f} ({daily_loss_percentage:.1%})"
            
            return is_triggered, daily_loss_percentage, description
            
        except Exception as e:
            return False, 0.0, f"Error checking daily loss: {e}"
    
    def _check_consecutive_losses(self) -> Tuple[bool, float, str]:
        """Check consecutive losses"""
        try:
            # Get recent closed trades
            recent_trades = list(trades_collection.find({
                "status": "CLOSED",
                "profit_loss": {"$exists": True, "$ne": None}
            }).sort("timestamp", -1).limit(20))
            
            consecutive_losses = 0
            for trade in recent_trades:
                pnl = trade.get('profit_loss', 0)
                if pnl < 0:
                    consecutive_losses += 1
                else:
                    break  # Stop at first profitable trade
            
            threshold = self.thresholds[CircuitBreakerType.CONSECUTIVE_LOSSES]
            is_triggered = consecutive_losses >= threshold
            
            description = f"{consecutive_losses} consecutive losses"
            
            return is_triggered, consecutive_losses, description
            
        except Exception as e:
            return False, 0.0, f"Error checking consecutive losses: {e}"
    
    def _check_hourly_trade_limit(self) -> Tuple[bool, float, str]:
        """Check hourly trade limit"""
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            hourly_trades = trades_collection.count_documents({
                "timestamp": {"$gte": one_hour_ago}
            })
            
            threshold = self.thresholds[CircuitBreakerType.HOURLY_TRADE_LIMIT]
            is_triggered = hourly_trades >= threshold
            
            description = f"{hourly_trades} trades in last hour"
            
            return is_triggered, hourly_trades, description
            
        except Exception as e:
            return False, 0.0, f"Error checking hourly limit: {e}"
    
    def _check_daily_trade_limit(self) -> Tuple[bool, float, str]:
        """Check daily trade limit"""
        try:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_trades = trades_collection.count_documents({
                "timestamp": {"$gte": today}
            })
            
            threshold = self.thresholds[CircuitBreakerType.DAILY_TRADE_LIMIT]
            is_triggered = daily_trades >= threshold
            
            description = f"{daily_trades} trades today"
            
            return is_triggered, daily_trades, description
            
        except Exception as e:
            return False, 0.0, f"Error checking daily limit: {e}"
    
    def _check_rapid_fire_trading(self, market: str) -> Tuple[bool, float, str]:
        """Check rapid fire trading in single market"""
        try:
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            rapid_trades = trades_collection.count_documents({
                "market": market,
                "timestamp": {"$gte": ten_minutes_ago}
            })
            
            threshold = self.thresholds[CircuitBreakerType.RAPID_FIRE_TRADING]
            is_triggered = rapid_trades >= threshold
            
            description = f"{rapid_trades} {market} trades in 10 minutes"
            
            return is_triggered, rapid_trades, description
            
        except Exception as e:
            return False, 0.0, f"Error checking rapid fire: {e}"
    
    def _check_correlation_exposure(self) -> Tuple[bool, float, str]:
        """Check correlated market exposure"""
        try:
            open_trades = get_open_trades()
            account_balance = get_account_balance()
            
            # Group by correlated markets (FTSE/DAX are highly correlated)
            correlated_groups = {
                'european_indices': ['FTSE 100', 'DAX', 'CAC 40'],
                'us_indices': ['S&P 500', 'NASDAQ', 'DOW'],
                'fx_majors': ['EUR/USD', 'GBP/USD', 'USD/JPY']
            }
            
            max_exposure_percentage = 0
            max_group = ""
            
            for group_name, markets in correlated_groups.items():
                group_exposure = 0
                for trade in open_trades:
                    if trade.get('market') in markets:
                        trade_value = abs(trade.get('entry_price', 0) * trade.get('size', 0))
                        group_exposure += trade_value
                
                exposure_percentage = group_exposure / account_balance if account_balance > 0 else 0
                
                if exposure_percentage > max_exposure_percentage:
                    max_exposure_percentage = exposure_percentage
                    max_group = group_name
            
            threshold = self.thresholds[CircuitBreakerType.CORRELATION_EXPOSURE]
            is_triggered = max_exposure_percentage >= threshold
            
            description = f"{max_exposure_percentage:.1%} exposure in {max_group}"
            
            return is_triggered, max_exposure_percentage, description
            
        except Exception as e:
            return False, 0.0, f"Error checking correlation exposure: {e}"
    
    def _check_position_concentration(self) -> Tuple[bool, float, str]:
        """Check single position concentration"""
        try:
            open_trades = get_open_trades()
            account_balance = get_account_balance()
            
            max_position_percentage = 0
            max_market = ""
            
            for trade in open_trades:
                trade_value = abs(trade.get('entry_price', 0) * trade.get('size', 0))
                position_percentage = trade_value / account_balance if account_balance > 0 else 0
                
                if position_percentage > max_position_percentage:
                    max_position_percentage = position_percentage
                    max_market = trade.get('market', 'Unknown')
            
            threshold = self.thresholds[CircuitBreakerType.POSITION_CONCENTRATION]
            is_triggered = max_position_percentage >= threshold
            
            description = f"{max_position_percentage:.1%} in {max_market}"
            
            return is_triggered, max_position_percentage, description
            
        except Exception as e:
            return False, 0.0, f"Error checking position concentration: {e}"
    
    def _check_margin_utilization(self) -> Tuple[bool, float, str]:
        """Check margin utilization"""
        try:
            # This would integrate with your margin tracking system
            # For now, estimate based on position values
            open_trades = get_open_trades()
            account_balance = get_account_balance()
            
            total_margin_used = 0
            for trade in open_trades:
                # Estimate margin (typically 5-10% of position value)
                trade_value = abs(trade.get('entry_price', 0) * trade.get('size', 0))
                estimated_margin = trade_value * 0.05  # 5% margin requirement estimate
                total_margin_used += estimated_margin
            
            margin_utilization = total_margin_used / account_balance if account_balance > 0 else 0
            
            threshold = self.thresholds[CircuitBreakerType.MARGIN_UTILIZATION]
            is_triggered = margin_utilization >= threshold
            
            description = f"{margin_utilization:.1%} margin utilization"
            
            return is_triggered, margin_utilization, description
            
        except Exception as e:
            return False, 0.0, f"Error checking margin utilization: {e}"
    
    def _check_drawdown_limit(self) -> Tuple[bool, float, str]:
        """Check maximum drawdown from peak"""
        try:
            current_balance = get_account_balance()
            
            # Update peak balance
            if current_balance is not None and current_balance > self.peak_balance:
                self.peak_balance = current_balance
            
            # Calculate drawdown
            drawdown = (self.peak_balance - current_balance) / self.peak_balance
            
            threshold = self.thresholds[CircuitBreakerType.DRAWDOWN_LIMIT]
            is_triggered = drawdown >= threshold
            
            description = f"{drawdown:.1%} drawdown from peak £{self.peak_balance:.2f}"
            
            return is_triggered, drawdown, description
            
        except Exception as e:
            return False, 0.0, f"Error checking drawdown: {e}"
    
    def _check_volatility_spike(self, market: str, trade_data: Dict) -> Tuple[bool, float, str]:
        """Check for volatility spikes"""
        if not trade_data or 'volatility' not in trade_data:
            return False, 0.0, "No volatility data"
        
        current_volatility = trade_data['volatility']
        threshold = self.thresholds[CircuitBreakerType.VOLATILITY_SPIKE]
        is_triggered = current_volatility >= threshold
        
        description = f"{current_volatility:.2%} volatility in {market}"
        
        return is_triggered, current_volatility, description
    
    def _check_spread_widening(self, trade_data: Dict) -> Tuple[bool, float, str]:
        """Check for spread widening"""
        if not trade_data or 'spread_cost' not in trade_data:
            return False, 0.0, "No spread data"
        
        spread_cost = trade_data['spread_cost']
        threshold = self.thresholds[CircuitBreakerType.SPREAD_WIDENING]
        is_triggered = spread_cost >= threshold
        
        description = f"{spread_cost:.3%} spread cost"
        
        return is_triggered, spread_cost, description
    
    def _check_system_latency(self) -> Tuple[bool, float, str]:
        """Check system latency (placeholder - implement with actual latency monitoring)"""
        # This would integrate with actual latency monitoring
        # For now, return false (no latency issues)
        return False, 0.0, "System latency OK"
    
    def _clean_expired_breakers(self):
        """Remove expired circuit breakers"""
        current_time = datetime.utcnow()
        expired_breakers = []
        
        for breaker_type, status in self.active_breakers.items():
            if status.trigger_time:
                cooling_period = self.cooling_periods[breaker_type]
                if current_time - status.trigger_time >= cooling_period:
                    expired_breakers.append(breaker_type)
        
        for breaker_type in expired_breakers:
            del self.active_breakers[breaker_type]
            print(f"🚨 Circuit breaker {breaker_type.value} cooling period expired")
    
    def _log_breaker_activation(self, status: CircuitBreakerStatus):
        """Log circuit breaker activation"""
        log_entry = {
            'timestamp': status.trigger_time,
            'breaker_type': status.name,
            'severity': status.severity,
            'trigger_value': status.trigger_value,
            'threshold': status.threshold,
            'description': status.description
        }
        
        self.breaker_history.append(log_entry)
        
        # Keep only last 100 activations
        if len(self.breaker_history) > 100:
            self.breaker_history = self.breaker_history[-100:]
        
        print(f"🚨 CIRCUIT BREAKER ACTIVATED: {status.severity} - {status.name}")
        print(f"   {status.description}")
    
    def get_system_status(self) -> Dict:
        """Get comprehensive circuit breaker system status"""
        return {
            'active_breakers': len(self.active_breakers),
            'breaker_details': [
                {
                    'name': status.name,
                    'severity': status.severity,
                    'trigger_value': status.trigger_value,
                    'threshold': status.threshold,
                    'description': status.description
                }
                for status in self.active_breakers.values()
            ],
            'total_activations_today': len([
                entry for entry in self.breaker_history
                if entry['timestamp'].date() == datetime.utcnow().date()
            ]),
            'system_health': 'HEALTHY' if not self.active_breakers else 
                           'WARNING' if all(s.severity == 'WARNING' for s in self.active_breakers.values()) else
                           'CRITICAL'
        }

# Global instance
_circuit_breakers = None

def get_circuit_breakers() -> EnhancedCircuitBreakers:
    """Get global circuit breakers instance"""
    global _circuit_breakers
    if _circuit_breakers is None:
        _circuit_breakers = EnhancedCircuitBreakers()
    return _circuit_breakers