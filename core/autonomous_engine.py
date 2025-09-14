# core/autonomous_engine.py

"""
AUTONOMOUS ALGORITHMIC TRADING ENGINE

Features:
- Self-optimizing parameters
- Advanced risk management
- Multi-strategy portfolio
- Real-time adaptation
- Profit maximization algorithms
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml
import json
import logging
from typing import Dict, List, Tuple, Optional
import threading
import time
from dataclasses import dataclass
from enum import Enum

class TradingState(Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    OPTIMIZATION = "OPTIMIZATION"

@dataclass
class Position:
    market: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    timestamp: datetime
    strategy: str
    confidence: float
    max_risk: float

@dataclass
class Trade:
    position: Position
    exit_price: float
    exit_reason: str
    pnl: float
    duration_hours: float
    exit_timestamp: datetime

class AdvancedRiskManager:
    """Advanced risk management with dynamic adjustment"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.daily_losses = {}
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.equity_high = 0.0
        self.volatility_multiplier = 1.0
        
    def calculate_position_size(self, balance: float, market: str, volatility: float) -> float:
        """Dynamic position sizing based on market conditions and performance"""
        
        # Base position size from config
        base_size = self.config.get('base_position_size', 0.02)  # 2% of balance
        
        # Adjust for volatility
        vol_adjustment = min(2.0, max(0.5, 1.0 / volatility)) if volatility > 0 else 1.0
        
        # Adjust for recent performance
        performance_multiplier = self._calculate_performance_multiplier()
        
        # Adjust for drawdown
        drawdown_multiplier = max(0.5, 1.0 - (self.current_drawdown / 0.2))  # Reduce size during drawdown
        
        # Final position size
        position_size = base_size * vol_adjustment * performance_multiplier * drawdown_multiplier
        
        # Cap at maximum risk
        max_size = self.config.get('max_position_size', 0.05)  # 5% max
        position_size = min(position_size, max_size)
        
        return position_size
    
    def _calculate_performance_multiplier(self) -> float:
        """Calculate multiplier based on recent trading performance"""
        today = datetime.now().date()
        recent_days = [today - timedelta(days=i) for i in range(5)]
        
        recent_performance = sum([self.daily_losses.get(day, 0) for day in recent_days])
        
        if recent_performance > 0:  # Profitable
            return min(1.5, 1.0 + (recent_performance / 1000))  # Increase size up to 50%
        else:  # Losing
            return max(0.5, 1.0 + (recent_performance / 2000))  # Reduce size down to 50%
    
    def should_trade(self, balance: float, current_positions: int) -> Tuple[bool, str]:
        """Determine if conditions allow trading"""
        
        # Daily loss limit
        today = datetime.now().date()
        daily_loss = self.daily_losses.get(today, 0)
        max_daily_loss = balance * self.config.get('max_daily_loss_pct', 0.05)  # 5%
        
        if daily_loss <= -max_daily_loss:
            return False, f"Daily loss limit exceeded: £{daily_loss:.2f}"
        
        # Maximum drawdown check
        max_allowed_dd = self.config.get('max_drawdown_pct', 0.15)  # 15%
        if self.current_drawdown >= max_allowed_dd:
            return False, f"Maximum drawdown exceeded: {self.current_drawdown:.1%}"
        
        # Position limit
        max_positions = self.config.get('max_concurrent_positions', 3)
        if current_positions >= max_positions:
            return False, f"Maximum positions reached: {current_positions}/{max_positions}"
        
        # Time-based restrictions
        current_hour = datetime.now().hour
        restricted_hours = self.config.get('restricted_hours', [0, 1, 2, 3, 4, 5])  # Asian session
        if current_hour in restricted_hours:
            return False, f"Trading restricted during hour {current_hour}"
        
        return True, "All risk checks passed"
    
    def update_performance(self, pnl: float, balance: float):
        """Update risk metrics with latest performance"""
        today = datetime.now().date()
        self.daily_losses[today] = self.daily_losses.get(today, 0) + pnl
        
        # Update drawdown
        if balance > self.equity_high:
            self.equity_high = balance
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.equity_high - balance) / self.equity_high

class StrategyOptimizer:
    """Continuously optimize strategy parameters"""
    
    def __init__(self):
        self.performance_history = []
        self.parameter_history = []
        self.optimization_interval = 100  # Optimize every 100 trades
        
    def record_performance(self, trades: List[Trade], parameters: Dict):
        """Record performance for optimization"""
        if not trades:
            return
        
        total_pnl = sum(trade.pnl for trade in trades)
        win_rate = len([t for t in trades if t.pnl > 0]) / len(trades)
        avg_duration = sum(trade.duration_hours for trade in trades) / len(trades)
        
        performance = {
            'timestamp': datetime.now(),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'trade_count': len(trades),
            'avg_duration': avg_duration,
            'profit_factor': self._calculate_profit_factor(trades)
        }
        
        self.performance_history.append(performance)
        self.parameter_history.append(parameters.copy())
        
        # Keep only recent data
        if len(self.performance_history) > 500:
            self.performance_history = self.performance_history[-500:]
            self.parameter_history = self.parameter_history[-500:]
    
    def _calculate_profit_factor(self, trades: List[Trade]) -> float:
        """Calculate profit factor"""
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in trades if t.pnl <= 0]
        
        if not losses:
            return float('inf')
        if not wins:
            return 0.0
        
        return sum(wins) / sum(losses)
    
    def optimize_parameters(self, current_params: Dict) -> Dict:
        """Optimize parameters based on performance history"""
        if len(self.performance_history) < 10:
            return current_params
        
        # Find best performing parameter sets
        recent_performance = self.performance_history[-50:]  # Last 50 records
        recent_params = self.parameter_history[-50:]
        
        # Sort by total PnL
        sorted_data = sorted(zip(recent_performance, recent_params), 
                           key=lambda x: x[0]['total_pnl'], reverse=True)
        
        # Get top 10% performing parameters
        top_count = max(1, len(sorted_data) // 10)
        top_performers = sorted_data[:top_count]
        
        # Average the best parameters
        optimized_params = current_params.copy()
        
        for key in current_params:
            if key in ['stop_loss_pips', 'take_profit_pips', 'fast_ma', 'slow_ma']:
                values = [params[key] for _, params in top_performers if key in params]
                if values:
                    optimized_params[key] = int(np.mean(values))
        
        return optimized_params

class ProfitMaximizer:
    """Algorithms to maximize profit and minimize risk"""
    
    def __init__(self):
        self.market_correlations = {}
        self.volatility_patterns = {}
        self.session_performance = {}
        
    def analyze_market_conditions(self, market_data: Dict) -> Dict:
        """Analyze current market conditions for optimal trading"""
        
        analysis = {
            'volatility_regime': self._detect_volatility_regime(market_data),
            'trend_strength': self._calculate_trend_strength(market_data),
            'session_favorability': self._get_session_favorability(),
            'risk_reward_ratio': self._optimal_risk_reward(market_data)
        }
        
        return analysis
    
    def _detect_volatility_regime(self, market_data: Dict) -> str:
        """Detect current volatility regime"""
        current_vol = market_data.get('atr', 10)
        vol_percentile = market_data.get('atr_percentile', 0.5)
        
        if vol_percentile > 0.8:
            return 'HIGH_VOLATILITY'
        elif vol_percentile < 0.2:
            return 'LOW_VOLATILITY'
        else:
            return 'NORMAL_VOLATILITY'
    
    def _calculate_trend_strength(self, market_data: Dict) -> float:
        """Calculate trend strength (0-1)"""
        ma_fast = market_data.get('ma_fast', 0)
        ma_slow = market_data.get('ma_slow', 0)
        current_price = market_data.get('close', 0)
        
        if ma_slow == 0:
            return 0.5
        
        # Distance between MAs relative to price
        ma_separation = abs(ma_fast - ma_slow) / current_price
        return min(1.0, ma_separation * 100)  # Scale to 0-1
    
    def _get_session_favorability(self) -> float:
        """Get favorability score for current trading session"""
        current_hour = datetime.now().hour
        
        # London session (7-16 UTC) and NY session (13-22 UTC) are best
        if 7 <= current_hour <= 16 or 13 <= current_hour <= 22:
            return 1.0  # High favorability
        elif 16 <= current_hour <= 22:
            return 0.8  # Medium favorability
        else:
            return 0.3  # Low favorability
    
    def _optimal_risk_reward(self, market_data: Dict) -> float:
        """Calculate optimal risk-reward ratio based on conditions"""
        volatility = market_data.get('atr', 10)
        trend_strength = self._calculate_trend_strength(market_data)
        
        # Higher trend strength allows for better risk-reward
        base_rr = 2.0  # Base 1:2 risk-reward
        trend_bonus = trend_strength * 1.0  # Up to 1:1 bonus
        vol_adjustment = min(1.5, max(0.5, volatility / 10))  # Adjust for volatility
        
        optimal_rr = base_rr + trend_bonus * vol_adjustment
        return min(4.0, max(1.5, optimal_rr))  # Cap between 1.5:1 and 4:1

class AutonomousEngine:
    """Main autonomous trading engine"""
    
    def __init__(self, config_path: str = 'configs/autonomous_config.yaml'):
        self.load_config(config_path)
        
        # Core components
        self.risk_manager = AdvancedRiskManager(self.config['risk_management'])
        self.optimizer = StrategyOptimizer()
        self.profit_maximizer = ProfitMaximizer()
        
        # Trading state
        self.state = TradingState.ACTIVE
        self.balance = self.config.get('starting_balance', 10000.0)
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
        # Strategy parameters (will be optimized)
        self.strategy_params = self.config['strategy']['parameters'].copy()
        
        # Monitoring
        self.setup_logging()
        self.performance_metrics = {
            'total_pnl': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'max_drawdown': 0.0
        }
        
        print("🤖 AUTONOMOUS TRADING ENGINE INITIALIZED")
        print(f"   💰 Starting Balance: £{self.balance:,.2f}")
        print(f"   🎯 Target: Autonomous profit maximization")
        print(f"   🛡️  Advanced risk management active")
    
    def load_config(self, config_path: str):
        """Load configuration"""
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            # Create default config if not found
            self.config = self._create_default_config()
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            print(f"📝 Created default config: {config_path}")
    
    def _create_default_config(self) -> Dict:
        """Create default autonomous configuration"""
        return {
            'starting_balance': 10000.0,
            'strategy': {
                'primary_algorithm': 'adaptive_ma_crossover',
                'backup_algorithm': 'supertrend',
                'timeframe': '10min',
                'parameters': {
                    'fast_ma': 8,
                    'slow_ma': 21,
                    'stop_loss_pips': 12,
                    'take_profit_pips': 24,
                    'atr_period': 14,
                    'trend_filter': True
                }
            },
            'risk_management': {
                'base_position_size': 0.02,
                'max_position_size': 0.05,
                'max_daily_loss_pct': 0.03,
                'max_drawdown_pct': 0.15,
                'max_concurrent_positions': 3,
                'restricted_hours': [0, 1, 2, 3, 4, 5]
            },
            'optimization': {
                'enabled': True,
                'optimization_frequency': 50,
                'parameter_ranges': {
                    'fast_ma': [5, 15],
                    'slow_ma': [15, 30],
                    'stop_loss_pips': [8, 20],
                    'take_profit_pips': [16, 40]
                }
            },
            'monitoring': {
                'alert_on_loss_streak': 3,
                'alert_on_drawdown_pct': 0.10,
                'performance_review_trades': 25
            }
        }
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('autonomous_trading.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AutonomousEngine')
    
    def analyze_signal(self, market_data: Dict, market_name: str) -> Tuple[str, float]:
        """Analyze market data and generate trading signal with confidence"""
        
        # Get market conditions analysis
        conditions = self.profit_maximizer.analyze_market_conditions(market_data)
        
        # Primary strategy: MA Crossover with enhancements
        signal = self._ma_crossover_signal(market_data)
        
        # Calculate confidence based on multiple factors
        confidence = self._calculate_signal_confidence(market_data, conditions, signal)
        
        # Filter weak signals
        min_confidence = self.config.get('min_signal_confidence', 0.6)
        if confidence < min_confidence:
            return 'HOLD', confidence
        
        return signal, confidence
    
    def _ma_crossover_signal(self, market_data: Dict) -> str:
        """Enhanced MA crossover signal"""
        fast_ma = market_data.get('ma_fast')
        slow_ma = market_data.get('ma_slow')
        prev_fast = market_data.get('prev_ma_fast')
        prev_slow = market_data.get('prev_ma_slow')
        
        if not all([fast_ma, slow_ma, prev_fast, prev_slow]):
            return 'HOLD'
        
        # Crossover detection
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            return 'BUY'
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            return 'SELL'
        
        return 'HOLD'
    
    def _calculate_signal_confidence(self, market_data: Dict, conditions: Dict, signal: str) -> float:
        """Calculate signal confidence (0-1)"""
        confidence_factors = []
        
        # Trend strength
        trend_strength = conditions.get('trend_strength', 0.5)
        confidence_factors.append(trend_strength)
        
        # Session favorability
        session_score = conditions.get('session_favorability', 0.5)
        confidence_factors.append(session_score)
        
        # Volatility regime
        vol_regime = conditions.get('volatility_regime', 'NORMAL_VOLATILITY')
        vol_score = 0.8 if vol_regime == 'NORMAL_VOLATILITY' else 0.6
        confidence_factors.append(vol_score)
        
        # MA separation (stronger signals have better separation)
        fast_ma = market_data.get('ma_fast', 0)
        slow_ma = market_data.get('ma_slow', 0)
        current_price = market_data.get('close', 1)
        
        if slow_ma and current_price:
            ma_separation = abs(fast_ma - slow_ma) / current_price
            separation_score = min(1.0, ma_separation * 200)  # Scale to 0-1
            confidence_factors.append(separation_score)
        
        # Recent performance (boost confidence if recent trades are winning)
        recent_performance = self._get_recent_performance_score()
        confidence_factors.append(recent_performance)
        
        # Average all factors
        return np.mean(confidence_factors)
    
    def _get_recent_performance_score(self) -> float:
        """Get performance score from recent trades"""
        if len(self.trades) < 5:
            return 0.5  # Neutral if insufficient history
        
        recent_trades = self.trades[-10:]  # Last 10 trades
        wins = len([t for t in recent_trades if t.pnl > 0])
        win_rate = wins / len(recent_trades)
        
        # Convert win rate to confidence score
        return min(1.0, max(0.2, win_rate + 0.2))
    
    def execute_trade(self, signal: str, market_data: Dict, market_name: str, confidence: float) -> bool:
        """Execute trade with advanced risk management"""
        
        # Risk management checks
        can_trade, reason = self.risk_manager.should_trade(self.balance, len(self.positions))
        if not can_trade:
            self.logger.info(f"Trade blocked: {reason}")
            return False
        
        # Calculate optimal position size
        volatility = market_data.get('atr', 10)
        position_size = self.risk_manager.calculate_position_size(self.balance, market_name, volatility)
        
        # Adjust size based on confidence
        position_size *= confidence  # Reduce size for lower confidence signals
        
        # Calculate entry price and risk parameters
        if signal == 'BUY':
            entry_price = market_data.get('offer', market_data.get('close', 0))
        else:
            entry_price = market_data.get('bid', market_data.get('close', 0))
        
        # Dynamic stop loss and take profit
        conditions = self.profit_maximizer.analyze_market_conditions(market_data)
        optimal_rr = conditions.get('risk_reward_ratio', 2.0)
        
        # Base risk from ATR
        base_risk = volatility * 1.5  # 1.5x ATR for stop loss
        stop_loss_distance = base_risk * (2.0 - confidence)  # Tighter stops for high confidence
        take_profit_distance = stop_loss_distance * optimal_rr
        
        if signal == 'BUY':
            stop_loss = entry_price - stop_loss_distance
            take_profit = entry_price + take_profit_distance
        else:
            stop_loss = entry_price + stop_loss_distance
            take_profit = entry_price - take_profit_distance
        
        # Create position
        position = Position(
            market=market_name,
            direction=signal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            size=position_size,
            timestamp=datetime.now(),
            strategy='autonomous_ma_crossover',
            confidence=confidence,
            max_risk=base_risk
        )
        
        self.positions[market_name] = position
        
        self.logger.info(f"🤖 AUTONOMOUS TRADE EXECUTED")
        self.logger.info(f"   Market: {market_name}")
        self.logger.info(f"   Signal: {signal} (Confidence: {confidence:.1%})")
        self.logger.info(f"   Entry: £{entry_price:.2f}")
        self.logger.info(f"   Stop Loss: £{stop_loss:.2f}")
        self.logger.info(f"   Take Profit: £{take_profit:.2f}")
        self.logger.info(f"   Position Size: {position_size:.1%}")
        self.logger.info(f"   Risk-Reward: 1:{optimal_rr:.1f}")
        
        return True
    
    def check_exits(self, market_data: Dict, market_name: str) -> Optional[Trade]:
        """Check if position should be closed"""
        if market_name not in self.positions:
            return None
        
        position = self.positions[market_name]
        current_price = market_data.get('close', 0)
        current_low = market_data.get('low', current_price)
        current_high = market_data.get('high', current_price)
        
        exit_triggered = False
        exit_price = None
        exit_reason = None
        
        # Stop loss / take profit checks
        if position.direction == 'BUY':
            if current_low <= position.stop_loss:
                exit_triggered = True
                exit_price = position.stop_loss
                exit_reason = 'STOP_LOSS'
            elif current_high >= position.take_profit:
                exit_triggered = True
                exit_price = position.take_profit
                exit_reason = 'TAKE_PROFIT'
        else:  # SELL
            if current_high >= position.stop_loss:
                exit_triggered = True
                exit_price = position.stop_loss
                exit_reason = 'STOP_LOSS'
            elif current_low <= position.take_profit:
                exit_triggered = True
                exit_price = position.take_profit
                exit_reason = 'TAKE_PROFIT'
        
        # Trailing stop logic (optional enhancement)
        if not exit_triggered:
            exit_price, exit_reason = self._check_trailing_stop(position, market_data)
            if exit_price:
                exit_triggered = True
        
        if exit_triggered:
            return self._close_position(position, exit_price, exit_reason, datetime.now())
        
        return None
    
    def _check_trailing_stop(self, position: Position, market_data: Dict) -> Tuple[Optional[float], Optional[str]]:
        """Check trailing stop conditions"""
        # Simple trailing stop: move stop loss in profit direction
        current_price = market_data.get('close', 0)
        
        if position.direction == 'BUY':
            if current_price > position.entry_price * 1.01:  # 1% profit
                new_stop = position.entry_price + (position.max_risk * 0.5)  # Move to 50% of max risk
                if new_stop > position.stop_loss:
                    # Update position (would need to be persisted in real system)
                    pass
        
        return None, None
    
    def _close_position(self, position: Position, exit_price: float, exit_reason: str, exit_time: datetime) -> Trade:
        """Close position and calculate P&L"""
        
        # Calculate P&L
        if position.direction == 'BUY':
            pnl = (exit_price - position.entry_price) * position.size * self.balance
        else:
            pnl = (position.entry_price - exit_price) * position.size * self.balance
        
        # Account for spread costs
        spread_cost = 2.0  # Assume £2 spread cost
        pnl -= spread_cost
        
        # Update balance
        self.balance += pnl
        
        # Create trade record
        trade = Trade(
            position=position,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            duration_hours=(exit_time - position.timestamp).total_seconds() / 3600,
            exit_timestamp=exit_time
        )
        
        # Record trade
        self.trades.append(trade)
        
        # Update performance tracking
        self.risk_manager.update_performance(pnl, self.balance)
        
        # Remove position
        del self.positions[position.market]
        
        self.logger.info(f"🔚 POSITION CLOSED: {position.market}")
        self.logger.info(f"   Exit: £{exit_price:.2f} ({exit_reason})")
        self.logger.info(f"   P&L: £{pnl:.2f}")
        self.logger.info(f"   Duration: {trade.duration_hours:.1f} hours")
        self.logger.info(f"   New Balance: £{self.balance:.2f}")
        
        # Trigger optimization if needed
        if len(self.trades) % self.config['optimization']['optimization_frequency'] == 0:
            self._optimize_strategy()
        
        return trade
    
    def _optimize_strategy(self):
        """Optimize strategy parameters based on performance"""
        if not self.config['optimization']['enabled']:
            return
        
        self.logger.info("🔧 OPTIMIZING STRATEGY PARAMETERS...")
        
        old_params = self.strategy_params.copy()
        self.strategy_params = self.optimizer.optimize_parameters(self.strategy_params)
        
        # Log parameter changes
        changes = []
        for key, new_val in self.strategy_params.items():
            if key in old_params and old_params[key] != new_val:
                changes.append(f"{key}: {old_params[key]} → {new_val}")
        
        if changes:
            self.logger.info(f"   Parameter updates: {', '.join(changes)}")
        else:
            self.logger.info("   No parameter changes needed")
        
        # Record performance for future optimization
        recent_trades = self.trades[-50:] if len(self.trades) >= 50 else self.trades
        self.optimizer.record_performance(recent_trades, self.strategy_params)
    
    def get_status_report(self) -> Dict:
        """Generate comprehensive status report"""
        
        # Calculate performance metrics
        if self.trades:
            wins = [t for t in self.trades if t.pnl > 0]
            total_pnl = sum(t.pnl for t in self.trades)
            win_rate = len(wins) / len(self.trades) * 100
            
            win_pnl = sum(t.pnl for t in wins) if wins else 0
            loss_pnl = sum(t.pnl for t in self.trades if t.pnl <= 0)
            profit_factor = abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf')
        else:
            total_pnl = 0
            win_rate = 0
            profit_factor = 0
        
        return {
            'timestamp': datetime.now(),
            'state': self.state.value,
            'balance': self.balance,
            'total_pnl': total_pnl,
            'return_pct': ((self.balance - self.config['starting_balance']) / self.config['starting_balance']) * 100,
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'open_positions': len(self.positions),
            'current_drawdown': self.risk_manager.current_drawdown,
            'strategy_params': self.strategy_params,
            'daily_pnl': self.risk_manager.daily_losses.get(datetime.now().date(), 0)
        }
    
    def emergency_stop(self, reason: str):
        """Emergency stop all trading"""
        self.state = TradingState.EMERGENCY_STOP
        self.logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")
        
        # Close all positions at market (would be implemented in live system)
        for position in self.positions.values():
            self.logger.critical(f"   Emergency closing {position.market} {position.direction}")
    
    def pause_trading(self, reason: str):
        """Pause trading temporarily"""
        self.state = TradingState.PAUSED
        self.logger.warning(f"⏸️  TRADING PAUSED: {reason}")
    
    def resume_trading(self):
        """Resume trading"""
        self.state = TradingState.ACTIVE
        self.logger.info("▶️  TRADING RESUMED")
        
    def process_market_data(self, market_data: Dict, market_name: str):
        """Main processing function for new market data"""
        
        if self.state != TradingState.ACTIVE:
            return
        
        try:
            # Check for exits first
            trade = self.check_exits(market_data, market_name)
            
            # Analyze for new signals
            signal, confidence = self.analyze_signal(market_data, market_name)
            
            # Execute trade if signal is strong enough
            if signal in ['BUY', 'SELL'] and market_name not in self.positions:
                self.execute_trade(signal, market_data, market_name, confidence)
            
            # Monitor for emergency conditions
            self._monitor_emergency_conditions()
            
        except Exception as e:
            self.logger.error(f"Error processing {market_name}: {e}")
    
    def _monitor_emergency_conditions(self):
        """Monitor for conditions that require emergency action"""
        
        # Excessive drawdown
        if self.risk_manager.current_drawdown >= 0.20:  # 20% drawdown
            self.emergency_stop("Excessive drawdown detected")
            return
        
        # Consecutive losses
        if len(self.trades) >= 5:
            recent_trades = self.trades[-5:]
            if all(t.pnl <= 0 for t in recent_trades):
                self.pause_trading("5 consecutive losses detected")
                return
        
        # Daily loss limit
        today = datetime.now().date()
        daily_loss = self.risk_manager.daily_losses.get(today, 0)
        if daily_loss <= -self.balance * 0.08:  # 8% daily loss
            self.pause_trading("Daily loss limit exceeded")
            return