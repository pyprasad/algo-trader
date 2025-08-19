#!/usr/bin/env python3
"""
🚨 Emergency Risk Management System

Critical risk controls to prevent catastrophic losses:
- Hard stop losses on all positions
- Daily loss limits with trading halt
- Position concentration limits
- Consecutive loss protection
- Volatility-based circuit breakers

Author: Professional Risk Management System
"""

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional
import numpy as np
from collections import deque
import yaml

# Load configuration
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

from data.db import trades_collection, get_account_balance
from utils.config_loader import load_global_config

# Economic calendar integration (lazy import to avoid circular dependencies)
_economic_calendar_monitor = None

class EmergencyRiskManager:
    """
    Professional-grade risk management system with multiple safety layers
    """
    
    def __init__(self):
        """Initialize emergency risk management system"""
        
        # Load risk parameters from config
        emergency_config = config.get('professional_trading', {}).get('emergency_risk', {})
        
        # CRITICAL RISK PARAMETERS - From config with defaults
        self.MAX_LOSS_PER_TRADE = emergency_config.get('max_loss_per_trade', 0.05)
        self.DAILY_LOSS_LIMIT = emergency_config.get('daily_loss_limit', 0.10)
        self.MAX_POSITION_SIZE = emergency_config.get('max_position_size', 0.10)
        self.MAX_TOTAL_EXPOSURE = emergency_config.get('max_total_exposure', 0.20)
        self.MAX_CONSECUTIVE_LOSSES = emergency_config.get('max_consecutive_losses', 5)
        self.MAX_CORRELATION_EXPOSURE = emergency_config.get('max_correlation_exposure', 0.03)
        
        # Volatility thresholds
        self.HIGH_VOLATILITY_THRESHOLD = emergency_config.get('high_volatility_threshold', 0.03)
        self.EXTREME_VOLATILITY_THRESHOLD = emergency_config.get('extreme_volatility_threshold', 0.05)
        
        # Trading state
        self.trading_halted = False
        self.halt_reason = None
        self.halt_timestamp = None
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_trades = []
        self.active_positions = {}
        
        # Performance tracking
        self.max_drawdown = 0.0
        self.peak_balance = get_account_balance()
        self.last_balance_check = datetime.now()
        
        # Circuit breaker states
        self.circuit_breakers = {
            'daily_loss': False,
            'consecutive_losses': False,
            'volatility': False,
            'correlation': False,
            'drawdown': False,
            'economic_event': False
        }
        
        # Initialize monitoring
        self.monitoring_thread = None
        self.monitoring_active = False
        
        print("🚨 Emergency Risk Manager initialized")
        print(f"   Max loss per trade: {self.MAX_LOSS_PER_TRADE*100:.1f}%")
        print(f"   Daily loss limit: {self.DAILY_LOSS_LIMIT*100:.1f}%")
        print(f"   Max position size: {self.MAX_POSITION_SIZE*100:.1f}%")
        print(f"   Circuit breakers: ACTIVE")
    
    def validate_trade(self, market: str, direction: str, size: float, 
                      current_price: float, stop_loss: float = None) -> Tuple[bool, str]:
        """
        Validate a trade against all risk parameters
        Returns: (can_trade, reason)
        """
        
        # Check if trading is halted
        if self.trading_halted:
            return False, f"Trading halted: {self.halt_reason}"
        
        # Check for economic event-based trading pause
        economic_pause_active, economic_reason = self._check_economic_event_pause(market)
        if economic_pause_active:
            return False, f"Economic event pause: {economic_reason}"
        
        # Get current account balance
        account_balance = get_account_balance()
        
        # 1. CHECK POSITION SIZE LIMIT
        # For Spread Betting, size is in £ per point, not full contract value
        # Calculate actual risk based on stop loss
        if stop_loss is None:
            return False, "CRITICAL: All trades must have stop loss defined"
        
        # Calculate potential loss (this is the actual risk/exposure)
        if direction == "BUY":
            potential_loss = abs(current_price - stop_loss) * size
        else:  # SELL
            potential_loss = abs(stop_loss - current_price) * size
        
        # Use potential loss as position value for spread betting
        position_value = potential_loss
        position_percentage = position_value / account_balance
        
        if position_percentage > self.MAX_POSITION_SIZE:
            return False, f"Position size {position_percentage:.2%} exceeds limit {self.MAX_POSITION_SIZE:.2%}"
        
        # 2. CHECK MAX LOSS PER TRADE
        loss_percentage = potential_loss / account_balance
        
        if loss_percentage > self.MAX_LOSS_PER_TRADE:
            return False, f"Potential loss {loss_percentage:.2%} exceeds limit {self.MAX_LOSS_PER_TRADE:.2%}"
        
        # 3. CHECK TOTAL EXPOSURE (sum of all position risks)
        total_exposure = sum(pos['value'] for pos in self.active_positions.values())
        new_total_exposure = total_exposure + position_value
        exposure_percentage = new_total_exposure / account_balance
        
        if exposure_percentage > self.MAX_TOTAL_EXPOSURE:
            return False, f"Total exposure {exposure_percentage:.2%} would exceed limit {self.MAX_TOTAL_EXPOSURE:.2%}"
        
        # 4. CRITICAL CHECK DAILY LOSS LIMIT - REAL-TIME CALCULATION
        print("💰 Calculating real-time daily P&L...")
        real_daily_pnl = self._calculate_real_daily_pnl()
        print(f"   Today's actual P&L: £{real_daily_pnl:.2f}")
        
        # Update internal tracking
        self.daily_pnl = real_daily_pnl
        
        daily_loss_percentage = abs(real_daily_pnl) / account_balance if account_balance > 0 else 0
        print(f"   Daily loss percentage: {daily_loss_percentage:.2%} (limit: {self.DAILY_LOSS_LIMIT:.2%})")
        
        if real_daily_pnl < 0 and daily_loss_percentage >= self.DAILY_LOSS_LIMIT:
            self._trigger_circuit_breaker('daily_loss', f"Daily loss £{real_daily_pnl:.2f} ({daily_loss_percentage:.2%}) exceeds limit {self.DAILY_LOSS_LIMIT:.2%}")
            return False, f"CRITICAL: Daily loss £{real_daily_pnl:.2f} exceeds limit {self.DAILY_LOSS_LIMIT:.2%}"
        
        # 5. CHECK CONSECUTIVE LOSSES
        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            self._trigger_circuit_breaker('consecutive_losses', "Too many consecutive losses")
            return False, f"Consecutive losses ({self.consecutive_losses}) exceed limit"
        
        # 6. CHECK CORRELATION LIMITS (DAX/FTSE)
        if not self._check_correlation_limits(market, position_value, account_balance):
            return False, "Correlation exposure limit exceeded"
        
        # 7. CHECK VOLATILITY CONDITIONS
        volatility_check, volatility_reason = self._check_volatility_conditions(market)
        if not volatility_check:
            return False, volatility_reason
        
        # ALL CHECKS PASSED
        return True, "Trade validated"
    
    def _check_correlation_limits(self, market: str, new_position_value: float, 
                                 account_balance: float) -> bool:
        """Check correlation-based position limits"""
        
        # Get current DAX and FTSE exposure
        dax_exposure = sum(pos['value'] for m, pos in self.active_positions.items() 
                          if 'DAX' in m)
        ftse_exposure = sum(pos['value'] for m, pos in self.active_positions.items() 
                           if 'FTSE' in m)
        
        # Add new position
        if 'DAX' in market:
            dax_exposure += new_position_value
        elif 'FTSE' in market:
            ftse_exposure += new_position_value
        
        # Check combined exposure during high correlation
        combined_exposure = dax_exposure + ftse_exposure
        combined_percentage = combined_exposure / account_balance
        
        # During normal times, allow up to 10% combined
        # During high correlation (>0.7), limit to 3%
        correlation = self._calculate_market_correlation()
        
        if correlation > 0.7:
            if combined_percentage > self.MAX_CORRELATION_EXPOSURE:
                return False
        
        return True
    
    def _calculate_market_correlation(self) -> float:
        """Calculate rolling correlation between DAX and FTSE"""
        try:
            from data.db import get_market_tick_data
            
            # Get recent tick data
            dax_ticks = get_market_tick_data("DAX", limit=100)
            ftse_ticks = get_market_tick_data("FTSE 100", limit=100)
            
            if len(dax_ticks) < 30 or len(ftse_ticks) < 30:
                return 0.5  # Default moderate correlation
            
            # Calculate returns
            dax_prices = [t['bid'] for t in dax_ticks]
            ftse_prices = [t['bid'] for t in ftse_ticks]
            
            dax_returns = np.diff(dax_prices) / dax_prices[:-1]
            ftse_returns = np.diff(ftse_prices) / ftse_prices[:-1]
            
            # Calculate correlation
            if len(dax_returns) > 0 and len(ftse_returns) > 0:
                correlation = np.corrcoef(dax_returns[-30:], ftse_returns[-30:])[0, 1]
                return abs(correlation)
            
        except Exception as e:
            print(f"⚠️ Correlation calculation error: {e}")
        
        return 0.5  # Default moderate correlation
    
    def _check_volatility_conditions(self, market: str) -> Tuple[bool, str]:
        """Check if volatility conditions are safe for trading"""
        try:
            from data.db import get_market_tick_data
            
            # Get recent price data
            ticks = get_market_tick_data(market, limit=50)
            if len(ticks) < 20:
                return True, "Insufficient data for volatility check"
            
            prices = [t['bid'] for t in ticks]
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns)
            
            # Check volatility thresholds
            if volatility > self.EXTREME_VOLATILITY_THRESHOLD:
                self._trigger_circuit_breaker('volatility', f"Extreme volatility: {volatility:.2%}")
                return False, f"Extreme volatility detected: {volatility:.2%}"
            
            if volatility > self.HIGH_VOLATILITY_THRESHOLD:
                # Allow trading but with reduced size
                return True, f"High volatility warning: {volatility:.2%}"
            
            return True, "Normal volatility"
            
        except Exception as e:
            print(f"⚠️ Volatility check error: {e}")
            return True, "Volatility check bypassed"
    
    def record_trade_result(self, trade_id: str, market: str, pnl: float, 
                          is_winner: bool):
        """Record trade result and update risk metrics"""
        
        # Update daily P&L
        self.daily_pnl += pnl
        self.daily_trades.append({
            'trade_id': trade_id,
            'market': market,
            'pnl': pnl,
            'timestamp': datetime.now()
        })
        
        # Update consecutive losses
        if is_winner:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Update drawdown
        current_balance = get_account_balance()
        if current_balance is not None and current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Check for circuit breaker conditions
        self._check_circuit_breakers()
    
    def _check_circuit_breakers(self):
        """Check all circuit breaker conditions"""
        
        account_balance = get_account_balance()
        
        # 1. Daily loss limit
        if abs(self.daily_pnl) / account_balance >= self.DAILY_LOSS_LIMIT:
            self._trigger_circuit_breaker('daily_loss', 
                f"Daily loss {self.daily_pnl:.2f} exceeds limit")
        
        # 2. Consecutive losses
        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            self._trigger_circuit_breaker('consecutive_losses', 
                f"{self.consecutive_losses} consecutive losses")
        
        # 3. Maximum drawdown (20% emergency stop)
        if self.max_drawdown >= 0.20:
            self._trigger_circuit_breaker('drawdown', 
                f"Maximum drawdown {self.max_drawdown:.2%} reached")
    
    def _trigger_circuit_breaker(self, breaker_type: str, reason: str):
        """Trigger a circuit breaker and halt trading"""
        
        self.circuit_breakers[breaker_type] = True
        self.trading_halted = True
        self.halt_reason = reason
        self.halt_timestamp = datetime.now()
        
        print(f"🚨🚨🚨 CIRCUIT BREAKER TRIGGERED 🚨🚨🚨")
        print(f"   Type: {breaker_type}")
        print(f"   Reason: {reason}")
        print(f"   Trading HALTED at {self.halt_timestamp}")
        
        # Send alert (implement your alert system here)
        self._send_emergency_alert(breaker_type, reason)
    
    def _send_emergency_alert(self, breaker_type: str, reason: str):
        """Send emergency alert when circuit breaker triggers"""
        # Implement your alert system (email, SMS, etc.)
        alert_message = f"""
        EMERGENCY TRADING HALT
        
        Circuit Breaker: {breaker_type}
        Reason: {reason}
        Time: {datetime.now()}
        Daily P&L: {self.daily_pnl:.2f}
        Consecutive Losses: {self.consecutive_losses}
        Max Drawdown: {self.max_drawdown:.2%}
        
        Trading has been automatically halted.
        Manual intervention required to resume.
        """
        
        print(alert_message)
        # Add email/SMS notification here
    
    def add_position(self, position_id: str, market: str, size: float, 
                    entry_price: float, stop_loss: float):
        """Add a position to tracking"""
        # For spread betting, the actual exposure is the maximum loss, not size * price
        max_loss = abs(entry_price - stop_loss) * size
        self.active_positions[position_id] = {
            'market': market,
            'size': size,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'value': max_loss,  # Changed: Use max loss as the position value for spread betting
            'max_loss': max_loss
        }
    
    def remove_position(self, position_id: str, exit_price: float = None):
        """Remove a closed position"""
        if position_id in self.active_positions:
            position = self.active_positions[position_id]
            
            # Calculate P&L if exit price provided
            if exit_price:
                pnl = (exit_price - position['entry_price']) * position['size']
                self.record_trade_result(position_id, position['market'], 
                                       pnl, pnl > 0)
            
            del self.active_positions[position_id]
    
    def _calculate_real_daily_pnl(self) -> float:
        """
        Calculate REAL daily P&L from database trades
        This is the bulletproof method that actually queries the database
        """
        from datetime import datetime, timedelta, timezone
        
        # Get start of current trading day (00:00 UTC)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            # Query all trades for today
            daily_trades = list(trades_collection.find({
                "timestamp": {"$gte": today},
                "profit_loss": {"$exists": True}
            }))
            
            # Calculate total P&L from all today's trades
            total_pnl = 0.0
            profit_count = 0
            loss_count = 0
            
            for trade in daily_trades:
                pnl = trade.get('profit_loss', 0)
                # Handle None values
                if pnl is None:
                    pnl = 0
                if pnl != 0:  # Only count trades with actual P&L
                    total_pnl += pnl
                    if pnl > 0:
                        profit_count += 1
                    else:
                        loss_count += 1
            
            print(f"   📊 Daily trades analysis:")
            print(f"      Total trades: {len(daily_trades)}")
            print(f"      Profitable: {profit_count}, Losses: {loss_count}")
            print(f"      Calculated P&L: £{total_pnl:.2f}")
            
            return total_pnl
            
        except Exception as e:
            print(f"❌ Error calculating daily P&L: {e}")
            # FAIL-SAFE: If we can't calculate P&L, assume worst case
            return -999.0  # This will trigger the safety limits
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of trading day)"""
        self.daily_pnl = 0.0
        self.daily_trades = []
        self.consecutive_losses = 0
        
        # Reset daily loss circuit breaker
        self.circuit_breakers['daily_loss'] = False
        
        # Only reset halt if it was due to daily loss
        if self.halt_reason and 'daily loss' in self.halt_reason.lower():
            self.trading_halted = False
            self.halt_reason = None
            print("📊 Daily metrics reset - Trading resumed")
    
    def get_risk_status(self) -> Dict:
        """Get current risk management status with real-time calculations"""
        account_balance = get_account_balance()
        total_exposure = sum(pos['value'] for pos in self.active_positions.values())
        
        # Always use real-time daily P&L calculation
        real_daily_pnl = self._calculate_real_daily_pnl()
        self.daily_pnl = real_daily_pnl  # Update internal state
        
        return {
            'trading_halted': self.trading_halted,
            'halt_reason': self.halt_reason,
            'daily_pnl': real_daily_pnl,
            'daily_pnl_percentage': real_daily_pnl / account_balance if account_balance > 0 else 0,
            'consecutive_losses': self.consecutive_losses,
            'total_exposure': total_exposure,
            'exposure_percentage': total_exposure / account_balance if account_balance > 0 else 0,
            'max_drawdown': self.max_drawdown,
            'active_positions': len(self.active_positions),
            'circuit_breakers': self.circuit_breakers,
            'can_trade': not self.trading_halted
        }
    
    def calculate_safe_position_size(self, market: str, current_price: float, 
                                    stop_loss: float, volatility: float = None) -> float:
        """
        Calculate safe position size using Kelly Criterion with volatility adjustment
        """
        account_balance = get_account_balance()
        
        # Base position size (1% of account)
        base_size = account_balance * self.MAX_POSITION_SIZE
        
        # Adjust for stop loss distance
        if stop_loss > 0:
            stop_distance = abs(current_price - stop_loss) / current_price
            
            # Risk per trade (2% max)
            risk_amount = account_balance * self.MAX_LOSS_PER_TRADE
            
            # Position size based on stop loss
            position_value = risk_amount / stop_distance
            
            # Take the smaller of base size and stop-loss adjusted size
            safe_position_value = min(base_size, position_value)
        else:
            safe_position_value = base_size
        
        # Adjust for volatility if provided
        if volatility:
            if volatility > self.HIGH_VOLATILITY_THRESHOLD:
                volatility_multiplier = 0.5  # Reduce size by 50% in high volatility
            elif volatility > self.HIGH_VOLATILITY_THRESHOLD * 0.5:
                volatility_multiplier = 0.75  # Reduce by 25% in moderate volatility
            else:
                volatility_multiplier = 1.0
            
            safe_position_value *= volatility_multiplier
        
        # Convert to position size (shares/contracts)
        safe_size = safe_position_value / current_price
        
        return safe_size
    
    def start_monitoring(self):
        """Start continuous risk monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            print("✅ Risk monitoring started")
    
    def stop_monitoring(self):
        """Stop risk monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("🛑 Risk monitoring stopped")
    
    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                # Check circuit breakers every 10 seconds
                self._check_circuit_breakers()
                
                # Reset daily metrics at market open
                current_time = datetime.now()
                if current_time.hour == 8 and current_time.minute == 0:
                    self.reset_daily_metrics()
                
                time.sleep(10)
                
            except Exception as e:
                print(f"❌ Risk monitoring error: {e}")
                time.sleep(10)
    
    def _check_economic_event_pause(self, market: str = None) -> Tuple[bool, Optional[str]]:
        """Check if trading should be paused due to economic events"""
        
        try:
            # Lazy import to avoid circular dependencies
            global _economic_calendar_monitor
            if _economic_calendar_monitor is None:
                try:
                    from core.economic_calendar_monitor import get_economic_calendar_monitor
                    _economic_calendar_monitor = get_economic_calendar_monitor()
                except ImportError:
                    # Economic calendar not available
                    return False, None
            
            # Check if calendar monitoring is enabled and active
            if not _economic_calendar_monitor or not _economic_calendar_monitor.enabled:
                return False, None
            
            # Check for active trading pause
            is_paused, reason = _economic_calendar_monitor.is_trading_paused(market)
            
            if is_paused:
                # Trigger economic event circuit breaker if not already triggered
                if not self.circuit_breakers.get('economic_event', False):
                    self.circuit_breakers['economic_event'] = True
                    print(f"📅 Economic event trading pause activated: {reason}")
                
                return True, reason
            else:
                # Reset economic event circuit breaker if it was active
                if self.circuit_breakers.get('economic_event', False):
                    self.circuit_breakers['economic_event'] = False
                    print("📅 Economic event trading pause lifted")
                
                return False, None
                
        except Exception as e:
            print(f"❌ Error checking economic event pause: {e}")
            return False, None
    
    def get_economic_calendar_status(self) -> Dict:
        """Get current economic calendar status"""
        
        try:
            global _economic_calendar_monitor
            if _economic_calendar_monitor is None:
                try:
                    from core.economic_calendar_monitor import get_economic_calendar_monitor
                    _economic_calendar_monitor = get_economic_calendar_monitor()
                except ImportError:
                    return {'available': False, 'error': 'Economic calendar not installed'}
            
            if not _economic_calendar_monitor:
                return {'available': False, 'error': 'Economic calendar not initialized'}
            
            # Get calendar summary
            summary = _economic_calendar_monitor.get_calendar_summary()
            
            return {
                'available': True,
                'monitoring_active': summary.get('monitoring_active', False),
                'is_paused': summary.get('current_pause', {}).get('is_paused', False),
                'pause_reason': summary.get('current_pause', {}).get('reason'),
                'next_pause': summary.get('next_pause'),
                'upcoming_events_24h': summary.get('upcoming_events', {}).get('next_24h', 0),
                'last_update': summary.get('last_update')
            }
            
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def should_close_positions_before_event(self) -> Tuple[bool, Optional[str]]:
        """Check if positions should be closed before upcoming high-impact event"""
        
        try:
            global _economic_calendar_monitor
            if _economic_calendar_monitor is None:
                try:
                    from core.economic_calendar_monitor import get_economic_calendar_monitor
                    _economic_calendar_monitor = get_economic_calendar_monitor()
                except ImportError:
                    return False, None
            
            if not _economic_calendar_monitor or not _economic_calendar_monitor.enabled:
                return False, None
            
            # Check for upcoming high-impact events in next 2 hours
            next_pause = _economic_calendar_monitor.get_next_pause_info()
            
            if next_pause:
                time_until_pause = next_pause['time_until_pause']
                
                # If pause starts within 30 minutes, recommend closing positions
                if time_until_pause.total_seconds() <= 1800:  # 30 minutes
                    reason = f"High-impact {next_pause['event_name']} in {time_until_pause.total_seconds()/60:.0f} minutes"
                    return True, reason
            
            return False, None
            
        except Exception as e:
            print(f"❌ Error checking position closure recommendation: {e}")
            return False, None

# Global instance
_emergency_risk_manager = None

def get_emergency_risk_manager() -> EmergencyRiskManager:
    """Get global emergency risk manager instance"""
    global _emergency_risk_manager
    if _emergency_risk_manager is None:
        _emergency_risk_manager = EmergencyRiskManager()
    return _emergency_risk_manager

if __name__ == "__main__":
    # Test the emergency risk manager
    print("🧪 Testing Emergency Risk Manager")
    print("=" * 50)
    
    risk_manager = EmergencyRiskManager()
    
    # Test trade validation
    can_trade, reason = risk_manager.validate_trade(
        market="DAX",
        direction="BUY",
        size=1,
        current_price=15000,
        stop_loss=14900
    )
    
    print(f"Trade validation: {can_trade}")
    print(f"Reason: {reason}")
    
    # Get risk status
    status = risk_manager.get_risk_status()
    print(f"\nRisk Status: {status}")