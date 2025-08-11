#!/usr/bin/env python3
"""
📊 Trading Profile Manager

Manages different trading profiles (Conservative, Aggressive, Scalping) and handles
profile switching, validation, and configuration management for A/B testing.

Author: Multi-Profile Trading System
"""

import os
import yaml
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProfilePerformance:
    """Profile performance metrics"""
    profile_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    max_profit: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_trade_duration: str = "0m"
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    def update_metrics(self, trades_data: List[Dict]):
        """Update performance metrics from trades data"""
        if not trades_data:
            return
        
        self.total_trades = len(trades_data)
        winning_trades = [t for t in trades_data if t.get('profit_loss', 0) > 0]
        losing_trades = [t for t in trades_data if t.get('profit_loss', 0) < 0]
        
        self.winning_trades = len(winning_trades)
        self.losing_trades = len(losing_trades)
        self.total_pnl = sum(t.get('profit_loss', 0) for t in trades_data)
        self.win_rate = (self.winning_trades / self.total_trades) * 100 if self.total_trades > 0 else 0
        
        if winning_trades:
            self.largest_win = max(t.get('profit_loss', 0) for t in winning_trades)
        if losing_trades:
            self.largest_loss = min(t.get('profit_loss', 0) for t in losing_trades)

class TradingProfileManager:
    """Manages trading profiles and configurations"""
    
    def __init__(self, profiles_dir: str = "configs/profiles"):
        """Initialize profile manager"""
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Current active profile
        self.active_profile = None
        self.active_config = None
        
        # Profile performance tracking
        self.performance_history = {}
        
        # Available profiles
        self.available_profiles = [
            "conservative",
            "aggressive", 
            "scalping"
        ]
        
        logger.info(f"📊 Profile Manager initialized")
        logger.info(f"   Profiles directory: {self.profiles_dir}")
        logger.info(f"   Available profiles: {', '.join(self.available_profiles)}")
    
    def create_default_profiles(self):
        """Create default profile configurations if they don't exist"""
        
        profiles_config = {
            "conservative": self._get_conservative_profile(),
            "aggressive": self._get_aggressive_profile(),
            "scalping": self._get_scalping_profile()
        }
        
        for profile_name, config in profiles_config.items():
            profile_path = self.profiles_dir / f"{profile_name}.yaml"
            
            if not profile_path.exists():
                with open(profile_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                logger.info(f"✅ Created default profile: {profile_name}")
            else:
                logger.info(f"📄 Profile already exists: {profile_name}")
    
    def _get_conservative_profile(self) -> Dict:
        """Get conservative profile configuration - Ultra-safe capital preservation"""
        return {
            'profile_info': {
                'name': 'conservative',
                'description': 'Ultra-safe capital preservation with maximum risk controls',
                'target_audience': 'Risk-averse traders prioritizing capital protection',
                'expected_characteristics': {
                    'trades_per_day': '1-3',
                    'win_rate_target': '70-80%',
                    'max_daily_risk': '2%',
                    'avg_trade_duration': '4-8 hours'
                }
            },
            
            # Economic Calendar - Maximum pause windows
            'economic_calendar': {
                'enabled': True,
                'pause_before_minutes': 180,  # 3 hours before events
                'pause_after_minutes': 180,   # 3 hours after events
                'high_impact_events': [
                    'FOMC Meeting',
                    'Interest Rate Decision',
                    'ECB Meeting',
                    'BOE Meeting',
                    'Non-Farm Payrolls',
                    'CPI',
                    'GDP',
                    'Central Bank Speech'
                ]
            },
            
            # Emergency Risk Management - Ultra conservative
            'emergency_risk': {
                'max_loss_per_trade': 0.01,     # 1% max loss per trade
                'daily_loss_limit': 0.02,       # 2% daily loss limit
                'max_position_size': 0.005,     # 0.5% position size
                'max_total_exposure': 0.02,     # 2% total exposure
                'max_consecutive_losses': 3,     # Stop after 3 losses
                'high_volatility_threshold': 0.02,  # 2% volatility = high
                'extreme_volatility_threshold': 0.03  # 3% volatility = extreme
            },
            
            # Professional Trading Settings
            'professional_trading': {
                'enabled': True,
                'system_mode': 'conservative',
                'min_signal_confidence': 0.85,     # Very high confidence required
                'analysis_interval_minutes': 10,    # Slower analysis
                'max_trades_per_hour': 0.25,       # 1 trade every 4 hours
                'daily_loss_limit': 200,
                'trade_frequency': 'very_low',
                
                # Smart Money - Conservative settings
                'smart_money': {
                    'enabled': True,
                    'min_confidence': 0.8,
                    'require_confluence': True  # Need multiple confirmations
                }
            },
            
            # Sentiment Analysis - Respect all negative sentiment
            'sentiment_analysis': {
                'enabled': True,
                'min_confidence_threshold': 0.8,  # High threshold
                'respect_negative_sentiment': True,
                'pause_on_uncertainty': True
            },
            
            # Conservative strategy parameters
            'strategy_parameters': {
                'stop_loss_multiplier': 0.8,      # Tighter stops
                'take_profit_multiplier': 2.0,    # Higher R:R ratio
                'trend_confirmation_required': True,
                'multiple_timeframe_confirmation': True,
                'avoid_news_times': True
            }
        }
    
    def _get_aggressive_profile(self) -> Dict:
        """Get aggressive profile configuration - Event-based volatility trading"""
        return {
            'profile_info': {
                'name': 'aggressive',
                'description': 'Event-based volatility trading with higher risk tolerance',
                'target_audience': 'Experienced traders comfortable with volatility',
                'expected_characteristics': {
                    'trades_per_day': '5-15',
                    'win_rate_target': '55-65%',
                    'max_daily_risk': '8%',
                    'avg_trade_duration': '30min-2hours'
                }
            },
            
            # Economic Calendar - Trade the volatility
            'economic_calendar': {
                'enabled': True,
                'strategy': 'event_trading',
                'pause_before_minutes': 15,      # Minimal pause
                'pause_after_minutes': 30,      # Short pause after
                'trade_during_events': True,    # Trade INTO volatility
                'event_opportunity_multiplier': 1.5,  # Bigger positions during events
                'high_impact_events': [
                    'FOMC Meeting',
                    'Interest Rate Decision', 
                    'ECB Meeting',
                    'BOE Meeting',
                    'Non-Farm Payrolls'
                ]
            },
            
            # Emergency Risk Management - Higher risk tolerance  
            'emergency_risk': {
                'max_loss_per_trade': 0.04,     # 4% max loss per trade
                'daily_loss_limit': 0.08,       # 8% daily loss limit
                'max_position_size': 0.03,      # 3% position size
                'max_total_exposure': 0.15,     # 15% total exposure
                'max_consecutive_losses': 6,     # More tolerance for streaks
                'high_volatility_threshold': 0.05,  # Higher volatility tolerance
                'extreme_volatility_threshold': 0.08
            },
            
            # Professional Trading Settings
            'professional_trading': {
                'enabled': True,
                'system_mode': 'aggressive',
                'min_signal_confidence': 0.55,     # Lower confidence threshold
                'analysis_interval_minutes': 2,     # Faster analysis
                'max_trades_per_hour': 5,          # More frequent trading
                'daily_loss_limit': 800,
                'trade_frequency': 'high',
                
                # Smart Money - Aggressive settings
                'smart_money': {
                    'enabled': True,
                    'min_confidence': 0.6,
                    'require_confluence': False  # Single strong signal OK
                }
            },
            
            # Sentiment Analysis - Less restrictive
            'sentiment_analysis': {
                'enabled': True,
                'min_confidence_threshold': 0.5,  # Lower threshold
                'respect_negative_sentiment': False, # Trade against sentiment
                'contrarian_trading': True         # Fade the crowd
            },
            
            # Aggressive strategy parameters
            'strategy_parameters': {
                'stop_loss_multiplier': 1.2,      # Wider stops
                'take_profit_multiplier': 1.5,    # Quick profits
                'trend_confirmation_required': False, # Trade breakouts
                'momentum_trading': True,
                'news_reaction_trading': True,    # Trade news reactions
                'volatility_breakout_trading': True
            }
        }
    
    def _get_scalping_profile(self) -> Dict:
        """Get scalping profile configuration - High-frequency rapid trading"""
        return {
            'profile_info': {
                'name': 'scalping',
                'description': 'High-frequency rapid trading with quick entries/exits',
                'target_audience': 'Active traders comfortable with high-frequency trading',
                'expected_characteristics': {
                    'trades_per_day': '20-100',
                    'win_rate_target': '52-62%',
                    'max_daily_risk': '12%',
                    'avg_trade_duration': '2-15 minutes'
                }
            },
            
            # Economic Calendar - Disabled for maximum trading time
            'economic_calendar': {
                'enabled': False,  # No event restrictions
                'ignore_all_events': True
            },
            
            # Emergency Risk Management - Scalping focused
            'emergency_risk': {
                'max_loss_per_trade': 0.02,     # 2% max loss per trade (tight stops)
                'daily_loss_limit': 0.12,       # 12% daily loss limit
                'max_position_size': 0.04,      # 4% position size
                'max_total_exposure': 0.20,     # 20% total exposure
                'max_consecutive_losses': 8,     # Higher tolerance
                'rapid_loss_protection': True,   # Special scalping protection
                'max_rapid_losses': 5,          # 5 losses in 30 min = pause
                'rapid_loss_timeframe': 1800    # 30 minutes
            },
            
            # Professional Trading Settings
            'professional_trading': {
                'enabled': True,
                'system_mode': 'scalping',
                'min_signal_confidence': 0.52,     # Low confidence for volume
                'analysis_interval_minutes': 0.5,   # 30-second analysis
                'max_trades_per_hour': 20,         # High frequency
                'daily_loss_limit': 1200,
                'trade_frequency': 'ultra_high',
                
                # Smart Money - Scalping optimized
                'smart_money': {
                    'enabled': True,
                    'min_confidence': 0.55,
                    'quick_scalp_signals': True
                }
            },
            
            # Sentiment Analysis - Minimal impact
            'sentiment_analysis': {
                'enabled': False,  # Don't let sentiment slow us down
                'ignore_sentiment': True
            },
            
            # Scalping strategy parameters
            'strategy_parameters': {
                'scalping_mode': True,
                'profit_target_pips': 3,        # Quick 3-pip profits
                'stop_loss_pips': 2,           # Tight 2-pip stops
                'max_trade_duration_minutes': 15, # Exit after 15 minutes
                'min_trade_gap_seconds': 30,   # 30 seconds between trades
                'trend_scalping': True,        # Scalp with trend
                'range_scalping': True,        # Scalp in ranges
                'news_scalping': False,        # Avoid news times
                'tight_spread_required': True  # Need tight spreads
            }
        }
    
    def load_profile(self, profile_name: str) -> Dict:
        """Load a specific trading profile"""
        
        if profile_name not in self.available_profiles:
            raise ValueError(f"Profile '{profile_name}' not available. Options: {self.available_profiles}")
        
        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        
        if not profile_path.exists():
            logger.warning(f"Profile file not found: {profile_path}")
            logger.info("Creating default profile...")
            self.create_default_profiles()
        
        try:
            with open(profile_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.active_profile = profile_name
            self.active_config = config
            
            logger.info(f"✅ Loaded profile: {profile_name}")
            logger.info(f"   Description: {config.get('profile_info', {}).get('description', 'N/A')}")
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading profile {profile_name}: {e}")
            raise
    
    def save_profile(self, profile_name: str, config: Dict):
        """Save a profile configuration"""
        
        profile_path = self.profiles_dir / f"{profile_name}.yaml"
        
        try:
            with open(profile_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"✅ Saved profile: {profile_name}")
            
        except Exception as e:
            logger.error(f"Error saving profile {profile_name}: {e}")
            raise
    
    def get_profile_summary(self, profile_name: str) -> Dict:
        """Get summary information about a profile"""
        
        config = self.load_profile(profile_name)
        profile_info = config.get('profile_info', {})
        
        return {
            'name': profile_name,
            'description': profile_info.get('description', 'N/A'),
            'target_audience': profile_info.get('target_audience', 'N/A'),
            'expected_characteristics': profile_info.get('expected_characteristics', {}),
            'risk_level': self._assess_risk_level(config),
            'trading_frequency': self._assess_trading_frequency(config),
            'event_strategy': self._assess_event_strategy(config)
        }
    
    def _assess_risk_level(self, config: Dict) -> str:
        """Assess risk level of a profile"""
        
        emergency_risk = config.get('emergency_risk', {})
        max_position_size = emergency_risk.get('max_position_size', 0.01)
        daily_loss_limit = emergency_risk.get('daily_loss_limit', 0.02)
        
        if max_position_size <= 0.01 and daily_loss_limit <= 0.03:
            return "VERY_LOW"
        elif max_position_size <= 0.02 and daily_loss_limit <= 0.06:
            return "LOW"
        elif max_position_size <= 0.03 and daily_loss_limit <= 0.10:
            return "MEDIUM"
        elif max_position_size <= 0.05 and daily_loss_limit <= 0.15:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _assess_trading_frequency(self, config: Dict) -> str:
        """Assess trading frequency of a profile"""
        
        professional = config.get('professional_trading', {})
        max_trades_per_hour = professional.get('max_trades_per_hour', 1)
        
        if max_trades_per_hour <= 0.5:
            return "VERY_LOW"
        elif max_trades_per_hour <= 2:
            return "LOW"
        elif max_trades_per_hour <= 5:
            return "MEDIUM"
        elif max_trades_per_hour <= 10:
            return "HIGH"
        else:
            return "VERY_HIGH"
    
    def _assess_event_strategy(self, config: Dict) -> str:
        """Assess economic event strategy"""
        
        calendar_config = config.get('economic_calendar', {})
        
        if not calendar_config.get('enabled', True):
            return "IGNORE_EVENTS"
        elif calendar_config.get('trade_during_events', False):
            return "TRADE_EVENTS"
        elif calendar_config.get('pause_before_minutes', 60) > 60:
            return "AVOID_EVENTS"
        else:
            return "CAUTIOUS"
    
    def compare_profiles(self) -> Dict:
        """Compare all available profiles"""
        
        comparison = {}
        
        for profile_name in self.available_profiles:
            try:
                summary = self.get_profile_summary(profile_name)
                comparison[profile_name] = summary
            except Exception as e:
                logger.error(f"Error comparing profile {profile_name}: {e}")
                comparison[profile_name] = {'error': str(e)}
        
        return comparison
    
    def start_profile_performance_tracking(self, profile_name: str):
        """Start performance tracking for a profile"""
        
        self.performance_history[profile_name] = ProfilePerformance(
            profile_name=profile_name,
            start_time=datetime.now()
        )
        
        logger.info(f"📊 Started performance tracking for profile: {profile_name}")
    
    def stop_profile_performance_tracking(self, profile_name: str, trades_data: List[Dict] = None):
        """Stop performance tracking and calculate final metrics"""
        
        if profile_name not in self.performance_history:
            logger.warning(f"No performance tracking found for profile: {profile_name}")
            return
        
        performance = self.performance_history[profile_name]
        performance.end_time = datetime.now()
        
        if trades_data:
            performance.update_metrics(trades_data)
        
        logger.info(f"📊 Stopped performance tracking for profile: {profile_name}")
        logger.info(f"   Duration: {performance.end_time - performance.start_time}")
        logger.info(f"   Total trades: {performance.total_trades}")
        logger.info(f"   Win rate: {performance.win_rate:.1f}%")
        logger.info(f"   Total P&L: £{performance.total_pnl:.2f}")
        
        return performance
    
    def get_active_profile_info(self) -> Dict:
        """Get information about the currently active profile"""
        
        if not self.active_profile:
            return {'error': 'No active profile'}
        
        return {
            'active_profile': self.active_profile,
            'config_loaded': self.active_config is not None,
            'summary': self.get_profile_summary(self.active_profile) if self.active_profile else None
        }

def get_profile_manager() -> TradingProfileManager:
    """Get global profile manager instance"""
    return TradingProfileManager()

def test_profile_manager():
    """Test the profile manager functionality"""
    print("🧪 Testing Trading Profile Manager")
    print("=" * 50)
    
    # Initialize manager
    manager = TradingProfileManager()
    
    # Create default profiles
    manager.create_default_profiles()
    print("✅ Default profiles created")
    
    # Test loading each profile
    for profile_name in manager.available_profiles:
        try:
            config = manager.load_profile(profile_name)
            summary = manager.get_profile_summary(profile_name)
            
            print(f"\n📊 Profile: {profile_name.upper()}")
            print(f"   Description: {summary['description']}")
            print(f"   Risk Level: {summary['risk_level']}")
            print(f"   Trading Frequency: {summary['trading_frequency']}")
            print(f"   Event Strategy: {summary['event_strategy']}")
            
        except Exception as e:
            print(f"❌ Error testing profile {profile_name}: {e}")
    
    # Test profile comparison
    print(f"\n📈 Profile Comparison:")
    comparison = manager.compare_profiles()
    
    for profile, info in comparison.items():
        if 'error' not in info:
            expected_chars = info.get('expected_characteristics', {})
            print(f"   {profile}: {expected_chars.get('trades_per_day', 'N/A')} trades/day, "
                  f"{expected_chars.get('win_rate_target', 'N/A')} win rate")
    
    print("\n🎉 Profile Manager test completed!")

if __name__ == "__main__":
    test_profile_manager()