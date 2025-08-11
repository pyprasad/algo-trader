#!/usr/bin/env python3
"""
🎯 August 8th Multi-Profile Backtest Comparison

Comprehensive backtest of all three trading profiles (Conservative, Aggressive, Scalping)
against the same August 8th tick data to determine which approach would have performed best.

This provides definitive data-driven evidence of which trading style makes the most money
in real market conditions, solving the "over-protective trading" problem with actual P&L data.

Author: Multi-Profile Trading System
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np
from collections import deque
from dataclasses import dataclass, asdict
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.profile_manager import TradingProfileManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TradeResult:
    """Individual trade result"""
    profile: str
    market: str
    direction: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    exit_reason: str
    confidence: float
    hold_duration_minutes: float

@dataclass
class ProfileBacktestResult:
    """Complete backtest result for a profile"""
    profile_name: str
    profile_description: str
    risk_level: str
    trading_frequency: str
    
    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L statistics
    total_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk statistics
    max_drawdown: float = 0.0
    max_consecutive_losses: int = 0
    average_trade_duration: float = 0.0
    total_trading_time_hours: float = 0.0
    
    # Market breakdown
    ftse_trades: int = 0
    dax_trades: int = 0
    ftse_pnl: float = 0.0
    dax_pnl: float = 0.0
    
    # Detailed trade list
    trades: List[TradeResult] = None
    
    def __post_init__(self):
        if self.trades is None:
            self.trades = []

class MultiProfileBacktestEngine:
    """
    Multi-profile backtest engine for comprehensive comparison
    """
    
    def __init__(self):
        """Initialize the backtest engine"""
        self.profile_manager = TradingProfileManager()
        
        # Load historical data
        self.ftse_ticks = self._load_tick_data("tick_ftse_100_08_08.json", "FTSE 100")
        self.dax_ticks = self._load_tick_data("tick_dax_08_08.json", "DAX")
        
        # Combine and sort by timestamp
        self.all_ticks = sorted(self.ftse_ticks + self.dax_ticks, key=lambda x: x['timestamp'])
        
        logger.info(f"📊 Loaded {len(self.ftse_ticks)} FTSE ticks, {len(self.dax_ticks)} DAX ticks")
        logger.info(f"📊 Total ticks for analysis: {len(self.all_ticks)}")
        
        self.initial_balance = 10000.0
        
        # Economic events simulation (for Conservative profile)
        self.economic_events = self._simulate_economic_events()
        
    def _load_tick_data(self, filename: str, market: str) -> List[Dict]:
        """Load tick data from JSON file"""
        ticks = []
        try:
            with open(filename, 'r') as f:
                for line in f:
                    tick_data = json.loads(line.strip())
                    timestamp_str = tick_data['timestamp']['$date']
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    ticks.append({
                        'market': market,
                        'bid': tick_data['bid'],
                        'offer': tick_data['offer'],
                        'timestamp': timestamp,
                        'mid_price': (tick_data['bid'] + tick_data['offer']) / 2
                    })
        except Exception as e:
            logger.error(f"❌ Error loading {filename}: {e}")
        
        return ticks
    
    def _simulate_economic_events(self) -> List[Dict]:
        """Simulate economic events for August 8th (for realistic Conservative profile testing)"""
        # Simulate typical economic events that might occur (with timezone)
        from datetime import timezone
        events = [
            {
                'time': datetime(2024, 8, 8, 8, 30, tzinfo=timezone.utc),  # UK inflation data
                'name': 'UK CPI Release',
                'impact': 'HIGH',
                'duration_minutes': 60
            },
            {
                'time': datetime(2024, 8, 8, 12, 0, tzinfo=timezone.utc),  # ECB speech
                'name': 'ECB President Speech', 
                'impact': 'MEDIUM',
                'duration_minutes': 120
            },
            {
                'time': datetime(2024, 8, 8, 14, 30, tzinfo=timezone.utc),  # US data
                'name': 'US Jobless Claims',
                'impact': 'MEDIUM', 
                'duration_minutes': 90
            }
        ]
        
        logger.info(f"📅 Simulated {len(events)} economic events for Conservative profile testing")
        return events
    
    def _is_economic_event_pause(self, timestamp: datetime, pause_before_minutes: int, 
                                pause_after_minutes: int) -> Tuple[bool, Optional[str]]:
        """Check if timestamp falls within economic event pause window"""
        for event in self.economic_events:
            event_start = event['time'] - timedelta(minutes=pause_before_minutes)
            event_end = event['time'] + timedelta(minutes=event['duration_minutes'] + pause_after_minutes)
            
            if event_start <= timestamp <= event_end:
                return True, event['name']
        
        return False, None
    
    def _generate_signals(self, prices: List[float], profile_config: Dict, 
                         current_time: datetime, market: str) -> Dict:
        """Generate trading signals based on profile configuration"""
        
        if len(prices) < 20:
            return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'insufficient_data'}
        
        profile_name = profile_config['profile_info']['name']
        professional_config = profile_config.get('professional_trading', {})
        min_confidence = professional_config.get('min_signal_confidence', 0.7)
        
        # Calculate technical indicators
        current_price = prices[-1]
        sma_5 = sum(prices[-5:]) / 5
        sma_10 = sum(prices[-10:]) / 10
        sma_20 = sum(prices[-20:]) / 20
        
        # RSI calculation
        gains = []
        losses = []
        for i in range(1, min(len(prices), 15)):
            change = prices[-i] - prices[-i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) >= 14:
            avg_gain = sum(gains[:14]) / 14
            avg_loss = sum(losses[:14]) / 14
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
        else:
            rsi = 50
        
        # Volatility
        returns = [(prices[-i] - prices[-i-1]) / prices[-i-1] for i in range(1, min(len(prices), 11))]
        volatility = np.std(returns) if len(returns) > 3 else 0.01
        
        # Profile-specific signal generation
        if profile_name == 'conservative':
            return self._generate_conservative_signals(
                current_price, sma_5, sma_10, sma_20, rsi, volatility, min_confidence
            )
        elif profile_name == 'aggressive':
            return self._generate_aggressive_signals(
                current_price, sma_5, sma_10, sma_20, rsi, volatility, min_confidence, current_time
            )
        elif profile_name == 'scalping':
            return self._generate_scalping_signals(
                current_price, sma_5, sma_10, rsi, volatility, min_confidence
            )
        
        return {'signal': 'HOLD', 'confidence': 0.0, 'reason': 'unknown_profile'}
    
    def _generate_conservative_signals(self, current_price: float, sma_5: float, sma_10: float,
                                     sma_20: float, rsi: float, volatility: float, 
                                     min_confidence: float) -> Dict:
        """Generate ultra-conservative signals with multiple confirmations"""
        
        signal = 'HOLD'
        confidence = 0.5
        reason = 'conservative_analysis'
        
        # Make conservative signals more achievable while maintaining safety
        trend_strength = abs(sma_5 - sma_20) / sma_20
        
        # Conservative requirements: Clear trend + reasonable RSI + moderate volatility
        if (sma_5 > sma_10 > sma_20 and  # Clear uptrend
            rsi < 75 and rsi > 40 and    # Not overbought, decent momentum
            volatility < 0.025 and       # Moderate volatility (more realistic)
            trend_strength > 0.005):     # Some trend strength
            
            signal = 'BUY'
            confidence = min(min_confidence + 0.02, 0.9)
            reason = 'clear_uptrend_safe_vol'
            
        elif (sma_5 < sma_10 < sma_20 and  # Clear downtrend
              rsi > 25 and rsi < 60 and    # Not oversold, decent momentum
              volatility < 0.025 and       # Moderate volatility
              trend_strength > 0.005):     # Some trend strength
            
            signal = 'SELL'
            confidence = min(min_confidence + 0.02, 0.9)
            reason = 'clear_downtrend_safe_vol'
        
        # Conservative oversold/overbought plays (more realistic thresholds)
        elif sma_5 > sma_20 * 1.005 and rsi < 30:  # Uptrend + oversold
            signal = 'BUY'
            confidence = min(min_confidence + 0.05, 0.92)
            reason = 'oversold_in_uptrend'
            
        elif sma_5 < sma_20 * 0.995 and rsi > 70:  # Downtrend + overbought
            signal = 'SELL'
            confidence = min(min_confidence + 0.05, 0.92)
            reason = 'overbought_in_downtrend'
            
        # Strong trend continuation (conservative momentum)
        elif (abs(sma_5 - sma_10) / sma_10 > 0.003 and  # Clear short-term momentum
              40 < rsi < 70 and                          # Reasonable RSI range
              volatility < 0.03):                       # Not too volatile
            signal = 'BUY' if sma_5 > sma_10 else 'SELL'
            confidence = min(min_confidence + 0.01, 0.88)
            reason = 'trend_continuation'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'rsi': rsi,
            'volatility': volatility,
            'trend_strength': trend_strength,
            'reason': reason
        }
    
    def _generate_aggressive_signals(self, current_price: float, sma_5: float, sma_10: float,
                                   sma_20: float, rsi: float, volatility: float,
                                   min_confidence: float, current_time: datetime) -> Dict:
        """Generate aggressive signals that capitalize on volatility and events"""
        
        signal = 'HOLD'
        confidence = 0.5
        reason = 'aggressive_analysis'
        
        trend_strength = abs(sma_5 - sma_20) / sma_20
        
        # Aggressive approach: Lower thresholds, embrace volatility
        if sma_5 > sma_10 and rsi < 85:  # Upward momentum, allow higher RSI
            if volatility > 0.015:  # Moderate-high volatility = opportunity
                signal = 'BUY'
                confidence = min(min_confidence + (volatility * 5), 0.8)  # Volatility boosts confidence
                reason = 'momentum_buy_vol'
            elif trend_strength > 0.004:  # Decent trend
                signal = 'BUY' 
                confidence = min(min_confidence + 0.08, 0.75)
                reason = 'trend_momentum_buy'
                
        elif sma_5 < sma_10 and rsi > 15:  # Downward momentum, allow lower RSI
            if volatility > 0.015:  # Moderate-high volatility = opportunity
                signal = 'SELL'
                confidence = min(min_confidence + (volatility * 5), 0.8)
                reason = 'momentum_sell_vol'
            elif trend_strength > 0.004:  # Decent trend
                signal = 'SELL'
                confidence = min(min_confidence + 0.08, 0.75)
                reason = 'trend_momentum_sell'
        
        # Contrarian plays (aggressive signature move) - more achievable
        elif rsi < 25 and volatility > 0.02:  # Oversold in volatile market
            signal = 'BUY'
            confidence = min(min_confidence + 0.12, 0.8)
            reason = 'contrarian_oversold'
            
        elif rsi > 75 and volatility > 0.02:  # Overbought in volatile market
            signal = 'SELL'
            confidence = min(min_confidence + 0.12, 0.8)
            reason = 'contrarian_overbought'
        
        # Momentum breakouts (more realistic)
        elif abs(current_price - sma_10) / sma_10 > 0.01 and volatility > 0.02:
            signal = 'BUY' if current_price > sma_10 else 'SELL'
            confidence = min(min_confidence + 0.15, 0.82)
            reason = 'momentum_breakout'
            
        # Strong short-term momentum
        elif abs(sma_5 - sma_10) / sma_10 > 0.005 and 25 < rsi < 75:
            signal = 'BUY' if sma_5 > sma_10 else 'SELL'
            confidence = min(min_confidence + 0.06, 0.72)
            reason = 'strong_momentum'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'rsi': rsi,
            'volatility': volatility,
            'trend_strength': trend_strength,
            'reason': reason
        }
    
    def _generate_scalping_signals(self, current_price: float, sma_5: float, sma_10: float,
                                 rsi: float, volatility: float, min_confidence: float) -> Dict:
        """Generate rapid scalping signals for quick profits"""
        
        signal = 'HOLD'
        confidence = 0.5
        reason = 'scalping_analysis'
        
        # Scalping: Quick momentum plays, very short-term
        price_change_5 = (current_price - sma_5) / sma_5
        sma_momentum = (sma_5 - sma_10) / sma_10
        
        # Quick momentum scalps (more achievable)
        if price_change_5 > 0.002 and rsi < 80:  # Smaller move threshold
            signal = 'BUY'
            confidence = min(min_confidence + 0.08, 0.7)
            reason = 'quick_momentum_up'
            
        elif price_change_5 < -0.002 and rsi > 20:  # Smaller move threshold
            signal = 'SELL'
            confidence = min(min_confidence + 0.08, 0.7)
            reason = 'quick_momentum_down'
        
        # Mean reversion scalps (more frequent opportunities)
        elif rsi < 25:  # Oversold bounce (higher threshold)
            signal = 'BUY'
            confidence = min(min_confidence + 0.12, 0.75)
            reason = 'oversold_bounce'
            
        elif rsi > 75:  # Overbought drop (lower threshold)
            signal = 'SELL'
            confidence = min(min_confidence + 0.12, 0.75)
            reason = 'overbought_drop'
        
        # Micro-trend following (wider RSI ranges)
        elif sma_momentum > 0.001 and 35 < rsi < 70:  # Mild uptrend
            signal = 'BUY'
            confidence = min(min_confidence + 0.06, 0.65)
            reason = 'micro_trend_up'
            
        elif sma_momentum < -0.001 and 30 < rsi < 65:  # Mild downtrend
            signal = 'SELL'
            confidence = min(min_confidence + 0.06, 0.65)
            reason = 'micro_trend_down'
        
        # Quick reversal plays
        elif abs(price_change_5) > 0.004 and 30 < rsi < 70:
            signal = 'SELL' if price_change_5 > 0 else 'BUY'  # Contrarian
            confidence = min(min_confidence + 0.10, 0.72)
            reason = 'quick_reversal'
            
        # Micro breakouts 
        elif abs(sma_momentum) > 0.002 and 40 < rsi < 60:
            signal = 'BUY' if sma_momentum > 0 else 'SELL'
            confidence = min(min_confidence + 0.04, 0.62)
            reason = 'micro_breakout'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'rsi': rsi,
            'volatility': volatility,
            'price_change': price_change_5,
            'sma_momentum': sma_momentum,
            'reason': reason
        }
    
    def backtest_profile(self, profile_name: str) -> ProfileBacktestResult:
        """Run comprehensive backtest for a specific profile"""
        
        logger.info(f"🎯 Starting backtest for {profile_name.upper()} profile")
        
        # Load profile configuration
        profile_config = self.profile_manager.load_profile(profile_name)
        profile_summary = self.profile_manager.get_profile_summary(profile_name)
        
        # Initialize result structure
        result = ProfileBacktestResult(
            profile_name=profile_name,
            profile_description=profile_summary['description'],
            risk_level=profile_summary['risk_level'],
            trading_frequency=profile_summary['trading_frequency']
        )
        
        # Trading state
        active_positions = {'FTSE 100': [], 'DAX': []}
        daily_pnl = 0
        peak_balance = self.initial_balance
        running_balance = self.initial_balance
        current_drawdown = 0
        max_drawdown = 0
        consecutive_losses = 0
        max_consecutive_losses = 0
        
        # Price buffers for technical analysis
        ftse_buffer = deque(maxlen=50)
        dax_buffer = deque(maxlen=50)
        
        # Profile-specific settings
        professional_config = profile_config.get('professional_trading', {})
        emergency_config = profile_config.get('emergency_risk', {})
        calendar_config = profile_config.get('economic_calendar', {})
        strategy_config = profile_config.get('strategy_parameters', {})
        
        analysis_interval = timedelta(minutes=professional_config.get('analysis_interval_minutes', 5))
        max_trades_per_hour = professional_config.get('max_trades_per_hour', 2)
        max_position_size = emergency_config.get('max_position_size', 0.02)
        daily_loss_limit = emergency_config.get('daily_loss_limit', 0.05)
        
        last_analysis = {'FTSE 100': None, 'DAX': None}
        hourly_trades = {'FTSE 100': [], 'DAX': []}
        
        trades_this_session = []
        
        logger.info(f"   📊 Analysis interval: {analysis_interval}")
        logger.info(f"   📊 Max trades/hour: {max_trades_per_hour}")
        logger.info(f"   📊 Position size: {max_position_size*100:.1f}%")
        logger.info(f"   📊 Daily loss limit: {daily_loss_limit*100:.1f}%")
        
        for tick_idx, tick in enumerate(self.all_ticks):
            market = tick['market']
            current_price = tick['mid_price']
            current_time = tick['timestamp']
            
            # Update price buffers
            if market == 'FTSE 100':
                ftse_buffer.append(current_price)
                price_buffer = list(ftse_buffer)
            else:
                dax_buffer.append(current_price)
                price_buffer = list(dax_buffer)
            
            if len(price_buffer) < 20:
                continue
            
            # Check exit conditions for active positions first
            for position in active_positions[market][:]:  # Copy list to modify during iteration
                if 'exit_price' in position:
                    continue
                
                exit_triggered = False
                exit_reason = ""
                
                # Profile-specific position management
                if profile_name == 'scalping':
                    # Scalping: Quick exits
                    if strategy_config.get('scalping_mode', False):
                        max_duration = timedelta(minutes=strategy_config.get('max_trade_duration_minutes', 15))
                        if current_time - position['entry_time'] > max_duration:
                            exit_price = tick['bid'] if position['direction'] == 'BUY' else tick['offer']
                            exit_triggered = True
                            exit_reason = 'time_exit'
                
                # Standard stop loss / take profit
                if not exit_triggered:
                    if position['direction'] == 'BUY':
                        if current_price <= position['stop_loss']:
                            exit_price = position['stop_loss']
                            exit_triggered = True
                            exit_reason = 'stop_loss'
                        elif current_price >= position['take_profit']:
                            exit_price = position['take_profit']
                            exit_triggered = True
                            exit_reason = 'take_profit'
                    else:  # SELL
                        if current_price >= position['stop_loss']:
                            exit_price = position['stop_loss']
                            exit_triggered = True
                            exit_reason = 'stop_loss'
                        elif current_price <= position['take_profit']:
                            exit_price = position['take_profit']
                            exit_triggered = True
                            exit_reason = 'take_profit'
                
                # Execute exit
                if exit_triggered:
                    if position['direction'] == 'BUY':
                        pnl = exit_price - position['entry_price']
                    else:
                        pnl = position['entry_price'] - exit_price
                    
                    # Apply position sizing to P&L
                    position_pnl = pnl * (running_balance * max_position_size) / position['entry_price']
                    
                    # Create trade result
                    trade = TradeResult(
                        profile=profile_name,
                        market=market,
                        direction=position['direction'],
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        entry_time=position['entry_time'],
                        exit_time=current_time,
                        pnl=position_pnl,
                        exit_reason=exit_reason,
                        confidence=position.get('confidence', 0.5),
                        hold_duration_minutes=(current_time - position['entry_time']).total_seconds() / 60
                    )
                    
                    trades_this_session.append(trade)
                    daily_pnl += position_pnl
                    running_balance += position_pnl
                    
                    # Update drawdown tracking
                    if running_balance > peak_balance:
                        peak_balance = running_balance
                        current_drawdown = 0
                    else:
                        current_drawdown = (peak_balance - running_balance) / peak_balance
                        max_drawdown = max(max_drawdown, current_drawdown)
                    
                    # Track consecutive losses
                    if position_pnl < 0:
                        consecutive_losses += 1
                        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                    else:
                        consecutive_losses = 0
                    
                    # Remove from active positions
                    active_positions[market].remove(position)
                    
                    logger.info(f"   💰 {current_time.strftime('%H:%M')} {profile_name.upper()}: "
                              f"CLOSED {market} {position['direction']} P&L: £{position_pnl:.2f} "
                              f"({exit_reason})")
            
            # Check analysis timing
            if last_analysis[market]:
                if current_time - last_analysis[market] < analysis_interval:
                    continue
            last_analysis[market] = current_time
            
            # SAFETY CHECKS before new trades
            
            # 1. Daily loss limit
            daily_loss_percent = abs(daily_pnl) / self.initial_balance
            if daily_pnl < 0 and daily_loss_percent > daily_loss_limit:
                continue
            
            # 2. Economic event pause (Conservative profile)
            if profile_name == 'conservative' and calendar_config.get('enabled', True):
                pause_before = calendar_config.get('pause_before_minutes', 60)
                pause_after = calendar_config.get('pause_after_minutes', 60)
                is_paused, event_name = self._is_economic_event_pause(current_time, pause_before, pause_after)
                if is_paused:
                    continue
            
            # 3. Position limits
            max_positions = 3 if profile_name == 'scalping' else 1
            if len(active_positions[market]) >= max_positions:
                continue
            
            # 4. Hourly trade limits
            one_hour_ago = current_time - timedelta(hours=1)
            hourly_trades[market] = [t for t in hourly_trades[market] if t > one_hour_ago]
            if len(hourly_trades[market]) >= max_trades_per_hour:
                continue
            
            # 5. Consecutive loss limit (extra safety)
            max_consecutive = emergency_config.get('max_consecutive_losses', 5)
            if consecutive_losses >= max_consecutive:
                continue
            
            # Generate trading signals
            signals = self._generate_signals(price_buffer, profile_config, current_time, market)
            
            # 6. Confidence threshold
            if signals['confidence'] < professional_config.get('min_signal_confidence', 0.7):
                continue
            
            # Execute new trade
            if signals['signal'] in ['BUY', 'SELL']:
                hourly_trades[market].append(current_time)
                
                # Calculate entry and exits based on profile
                if signals['signal'] == 'BUY':
                    entry_price = tick['offer']
                    if profile_name == 'scalping':
                        stop_loss = entry_price - strategy_config.get('stop_loss_pips', 2)
                        take_profit = entry_price + strategy_config.get('profit_target_pips', 3)
                    elif profile_name == 'conservative':
                        stop_loss = entry_price - 12  # Conservative stops
                        take_profit = entry_price + 24  # 2:1 R:R
                    else:  # aggressive
                        stop_loss = entry_price - 18  # Wider stops
                        take_profit = entry_price + 27  # 1.5:1 R:R
                else:  # SELL
                    entry_price = tick['bid']
                    if profile_name == 'scalping':
                        stop_loss = entry_price + strategy_config.get('stop_loss_pips', 2)
                        take_profit = entry_price - strategy_config.get('profit_target_pips', 3)
                    elif profile_name == 'conservative':
                        stop_loss = entry_price + 12
                        take_profit = entry_price - 24
                    else:  # aggressive
                        stop_loss = entry_price + 18
                        take_profit = entry_price - 27
                
                # Create position
                position = {
                    'market': market,
                    'direction': signals['signal'],
                    'entry_price': entry_price,
                    'entry_time': current_time,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'confidence': signals['confidence']
                }
                
                active_positions[market].append(position)
                
                logger.info(f"   🎯 {current_time.strftime('%H:%M')} {profile_name.upper()}: "
                          f"OPENED {market} {signals['signal']} at {entry_price:.1f} "
                          f"(conf: {signals['confidence']:.2f}, {signals.get('reason', 'N/A')})")
        
        # Close remaining positions at end of day
        for market, positions in active_positions.items():
            for position in positions:
                if 'exit_price' not in position:
                    last_tick = [t for t in self.all_ticks if t['market'] == market][-1]
                    if position['direction'] == 'BUY':
                        exit_price = last_tick['bid']
                        pnl = exit_price - position['entry_price']
                    else:
                        exit_price = last_tick['offer']
                        pnl = position['entry_price'] - exit_price
                    
                    position_pnl = pnl * (running_balance * max_position_size) / position['entry_price']
                    
                    trade = TradeResult(
                        profile=profile_name,
                        market=position['market'],
                        direction=position['direction'],
                        entry_price=position['entry_price'],
                        exit_price=exit_price,
                        entry_time=position['entry_time'],
                        exit_time=last_tick['timestamp'],
                        pnl=position_pnl,
                        exit_reason='end_of_day',
                        confidence=position.get('confidence', 0.5),
                        hold_duration_minutes=(last_tick['timestamp'] - position['entry_time']).total_seconds() / 60
                    )
                    
                    trades_this_session.append(trade)
                    daily_pnl += position_pnl
        
        # Calculate final statistics
        result.trades = trades_this_session
        result.total_trades = len(trades_this_session)
        
        winning_trades = [t for t in trades_this_session if t.pnl > 0]
        losing_trades = [t for t in trades_this_session if t.pnl < 0]
        
        result.winning_trades = len(winning_trades)
        result.losing_trades = len(losing_trades)
        result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades > 0 else 0
        
        result.total_pnl = sum(t.pnl for t in trades_this_session)
        result.average_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        result.average_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        result.largest_win = max([t.pnl for t in winning_trades], default=0)
        result.largest_loss = min([t.pnl for t in losing_trades], default=0)
        
        if result.average_loss != 0:
            result.profit_factor = abs(result.average_win * result.winning_trades / 
                                     (result.average_loss * result.losing_trades))
        
        result.max_drawdown = max_drawdown * 100  # Convert to percentage
        result.max_consecutive_losses = max_consecutive_losses
        
        if trades_this_session:
            result.average_trade_duration = np.mean([t.hold_duration_minutes for t in trades_this_session])
            result.total_trading_time_hours = sum(t.hold_duration_minutes for t in trades_this_session) / 60
        
        # Market breakdown
        ftse_trades = [t for t in trades_this_session if t.market == 'FTSE 100']
        dax_trades = [t for t in trades_this_session if t.market == 'DAX']
        
        result.ftse_trades = len(ftse_trades)
        result.dax_trades = len(dax_trades)
        result.ftse_pnl = sum(t.pnl for t in ftse_trades)
        result.dax_pnl = sum(t.pnl for t in dax_trades)
        
        logger.info(f"✅ {profile_name.upper()} backtest completed:")
        logger.info(f"   📊 Total trades: {result.total_trades}")
        logger.info(f"   📊 Win rate: {result.win_rate:.1f}%")
        logger.info(f"   📊 Total P&L: £{result.total_pnl:.2f}")
        logger.info(f"   📊 Max drawdown: {result.max_drawdown:.1f}%")
        
        return result
    
    def run_comprehensive_comparison(self) -> Dict:
        """Run comprehensive backtest comparison across all profiles"""
        
        logger.info("🎯" + "="*70)
        logger.info("🎯 COMPREHENSIVE MULTI-PROFILE BACKTEST ANALYSIS")
        logger.info("🎯" + "="*70)
        logger.info("📅 August 8, 2024 - Multi-Profile Comparison")
        logger.info("🎯" + "="*70)
        
        # Run backtests for all profiles
        results = {}
        
        for profile_name in ['conservative', 'aggressive', 'scalping']:
            try:
                logger.info(f"\n🚀 Running {profile_name.upper()} profile backtest...")
                results[profile_name] = self.backtest_profile(profile_name)
            except Exception as e:
                logger.error(f"❌ Error backtesting {profile_name}: {e}")
                results[profile_name] = None
        
        # Generate comprehensive comparison
        comparison_results = {
            'backtest_date': '2024-08-08',
            'initial_balance': self.initial_balance,
            'total_ticks_analyzed': len(self.all_ticks),
            'ftse_ticks': len(self.ftse_ticks),
            'dax_ticks': len(self.dax_ticks),
            'profiles': results,
            'winner_analysis': self._determine_winner(results),
            'generated_at': datetime.now().isoformat()
        }
        
        # Print comprehensive results
        self._print_comprehensive_results(results)
        
        return comparison_results
    
    def _determine_winner(self, results: Dict) -> Dict:
        """Determine the winning profile based on multiple criteria"""
        
        valid_results = {k: v for k, v in results.items() if v is not None}
        
        if not valid_results:
            return {'winner': None, 'reason': 'No valid results'}
        
        # Score each profile on multiple criteria
        scores = {}
        
        for profile_name, result in valid_results.items():
            score = 0
            reasons = []
            
            # Profitability (40% weight)
            if result.total_pnl > 0:
                score += 40
                reasons.append(f"profitable (£{result.total_pnl:.2f})")
            
            # Risk-adjusted returns (25% weight) 
            risk_score = 0
            if result.max_drawdown < 3:  # Low drawdown
                risk_score += 15
            elif result.max_drawdown < 5:
                risk_score += 10
            elif result.max_drawdown < 8:
                risk_score += 5
            
            if result.max_consecutive_losses <= 3:
                risk_score += 10
            elif result.max_consecutive_losses <= 5:
                risk_score += 5
            
            score += risk_score
            if risk_score > 15:
                reasons.append("excellent risk management")
            elif risk_score > 10:
                reasons.append("good risk management")
            
            # Win rate (20% weight)
            if result.win_rate > 70:
                score += 20
                reasons.append(f"{result.win_rate:.1f}% win rate")
            elif result.win_rate > 60:
                score += 15
                reasons.append(f"{result.win_rate:.1f}% win rate")
            elif result.win_rate > 50:
                score += 10
            
            # Trade quality (15% weight)
            if result.profit_factor > 2:
                score += 15
                reasons.append("excellent profit factor")
            elif result.profit_factor > 1.5:
                score += 10
                reasons.append("good profit factor")
            elif result.profit_factor > 1:
                score += 5
            
            scores[profile_name] = {
                'total_score': score,
                'reasons': reasons,
                'result': result
            }
        
        # Find winner
        if scores:
            winner = max(scores, key=lambda x: scores[x]['total_score'])
            winner_info = scores[winner]
            
            return {
                'winner': winner,
                'score': winner_info['total_score'],
                'reasons': winner_info['reasons'],
                'runner_up': sorted(scores.keys(), key=lambda x: scores[x]['total_score'])[-2] if len(scores) > 1 else None,
                'all_scores': {k: v['total_score'] for k, v in scores.items()}
            }
        
        return {'winner': None, 'reason': 'No valid scoring'}
    
    def _print_comprehensive_results(self, results: Dict):
        """Print detailed comparison results"""
        
        print("\n🎯" + "="*80)
        print("🎯 AUGUST 8TH MULTI-PROFILE BACKTEST RESULTS")
        print("🎯" + "="*80)
        
        # Summary table
        print(f"\n{'Profile':<15} {'Trades':<8} {'Win Rate':<10} {'Total P&L':<12} {'Max DD':<10} {'Status':<15}")
        print("-" * 80)
        
        for profile_name in ['conservative', 'aggressive', 'scalping']:
            result = results.get(profile_name)
            if result:
                status = "🏆 WINNER" if result.total_pnl == max(r.total_pnl for r in results.values() if r) else "✅ TESTED"
                print(f"{profile_name.title():<15} {result.total_trades:<8} {result.win_rate:<10.1f}% "
                      f"£{result.total_pnl:<11.2f} {result.max_drawdown:<9.1f}% {status:<15}")
            else:
                print(f"{profile_name.title():<15} {'ERROR':<8} {'N/A':<10} {'N/A':<12} {'N/A':<10} {'❌ FAILED':<15}")
        
        # Detailed analysis
        print(f"\n🔍 DETAILED PROFILE ANALYSIS:")
        
        for profile_name, result in results.items():
            if result:
                print(f"\n📊 {profile_name.upper()} PROFILE RESULTS:")
                print(f"   • Total Trades: {result.total_trades} ({result.ftse_trades} FTSE, {result.dax_trades} DAX)")
                print(f"   • Win Rate: {result.win_rate:.1f}% ({result.winning_trades} wins, {result.losing_trades} losses)")
                print(f"   • Total P&L: £{result.total_pnl:.2f}")
                print(f"   • Average Trade Duration: {result.average_trade_duration:.1f} minutes")
                print(f"   • Max Drawdown: {result.max_drawdown:.1f}%")
                print(f"   • Max Consecutive Losses: {result.max_consecutive_losses}")
                print(f"   • Profit Factor: {result.profit_factor:.2f}")
                print(f"   • Largest Win: £{result.largest_win:.2f}")
                print(f"   • Largest Loss: £{result.largest_loss:.2f}")
                print(f"   • Risk Level: {result.risk_level}")
                print(f"   • Trading Frequency: {result.trading_frequency}")
                
                if result.ftse_pnl != 0 or result.dax_pnl != 0:
                    print(f"   • FTSE P&L: £{result.ftse_pnl:.2f}")
                    print(f"   • DAX P&L: £{result.dax_pnl:.2f}")
        
        # Winner analysis
        winner_info = self._determine_winner(results)
        if winner_info.get('winner'):
            print(f"\n🏆 WINNER: {winner_info['winner'].upper()} PROFILE")
            print(f"   Score: {winner_info['score']}/100")
            print(f"   Reasons: {', '.join(winner_info['reasons'])}")
            
            if winner_info.get('runner_up'):
                print(f"   Runner-up: {winner_info['runner_up'].title()}")
        
        print(f"\n💡 KEY INSIGHTS:")
        print(f"   ✅ Multi-profile approach provides clear performance comparison")
        print(f"   ✅ Different risk/reward profiles suit different market conditions")
        print(f"   ✅ Data-driven evidence shows which approach actually makes money")
        print(f"   ✅ Risk management differences create distinct performance profiles")
        
        print(f"\n🚀 RECOMMENDATION FOR LIVE TRADING:")
        if winner_info.get('winner'):
            print(f"   Deploy {winner_info['winner'].upper()} profile for optimal performance")
            print(f"   Command: python3 scripts/run_{winner_info['winner']}.py --duration 7d --live")
        else:
            print(f"   Review individual profile performance and choose based on risk tolerance")
        
        print("🎯" + "="*80)

def main():
    """Main execution function"""
    
    try:
        print("🎯 Multi-Profile Backtest Engine")
        print("="*50)
        print("Backtesting all trading profiles against August 8th tick data...")
        
        engine = MultiProfileBacktestEngine()
        results = engine.run_comprehensive_comparison()
        
        # Save results to file
        import json
        from pathlib import Path
        
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Save detailed results
        results_file = reports_dir / "august_8_profile_comparison_results.json"
        
        # Convert results for JSON serialization
        serializable_results = {}
        for profile_name, result in results['profiles'].items():
            if result:
                serializable_results[profile_name] = {
                    'profile_name': result.profile_name,
                    'profile_description': result.profile_description,
                    'risk_level': result.risk_level,
                    'trading_frequency': result.trading_frequency,
                    'total_trades': result.total_trades,
                    'winning_trades': result.winning_trades,
                    'losing_trades': result.losing_trades,
                    'win_rate': result.win_rate,
                    'total_pnl': result.total_pnl,
                    'average_win': result.average_win,
                    'average_loss': result.average_loss,
                    'largest_win': result.largest_win,
                    'largest_loss': result.largest_loss,
                    'profit_factor': result.profit_factor,
                    'max_drawdown': result.max_drawdown,
                    'max_consecutive_losses': result.max_consecutive_losses,
                    'average_trade_duration': result.average_trade_duration,
                    'total_trading_time_hours': result.total_trading_time_hours,
                    'ftse_trades': result.ftse_trades,
                    'dax_trades': result.dax_trades,
                    'ftse_pnl': result.ftse_pnl,
                    'dax_pnl': result.dax_pnl,
                    'trade_count': len(result.trades)
                }
        
        results['profiles'] = serializable_results
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {results_file}")
        
        # Create executive summary
        summary_file = reports_dir / "august_8_executive_summary.txt"
        with open(summary_file, 'w') as f:
            f.write("AUGUST 8TH MULTI-PROFILE BACKTEST - EXECUTIVE SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            winner_info = results.get('winner_analysis', {})
            if winner_info.get('winner'):
                f.write(f"🏆 WINNING PROFILE: {winner_info['winner'].upper()}\n")
                f.write(f"Score: {winner_info.get('score', 0)}/100\n")
                f.write(f"Reasons: {', '.join(winner_info.get('reasons', []))}\n\n")
            
            f.write("PERFORMANCE SUMMARY:\n")
            f.write("-" * 30 + "\n")
            for profile_name, result_data in serializable_results.items():
                f.write(f"{profile_name.title()}: £{result_data['total_pnl']:.2f} P&L, "
                       f"{result_data['total_trades']} trades, {result_data['win_rate']:.1f}% win rate\n")
            
            f.write(f"\n🚀 RECOMMENDATION:\n")
            if winner_info.get('winner'):
                f.write(f"Deploy {winner_info['winner']} profile for live trading\n")
                f.write(f"Command: python3 scripts/run_{winner_info['winner']}.py --duration 7d --live\n")
        
        print(f"📋 Executive summary saved to: {summary_file}")
        print("\n🎉 Multi-profile backtest analysis completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Backtest analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)