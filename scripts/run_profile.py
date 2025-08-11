#!/usr/bin/env python3
"""
🚀 Profile-Based Trading System Runner

Executes trading with specific profiles (Conservative, Aggressive, Scalping)
and tracks performance for weekly A/B testing and comparison.

Usage:
    python3 scripts/run_profile.py --profile conservative --duration 7d
    python3 scripts/run_profile.py --profile aggressive --duration 1w --live
    python3 scripts/run_profile.py --profile scalping --duration 24h --paper

Author: Multi-Profile Trading System
"""

import os
import sys
import argparse
import signal
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.profile_manager import TradingProfileManager
from runners.run_multi_market import MultiMarketTradingSystem
from utils.market_config_loader import MarketConfigLoader
from data.db import trades_collection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProfileTradingRunner:
    """Profile-based trading system runner"""
    
    def __init__(self, profile_name: str, duration_str: str = "1d", live_mode: bool = False):
        """Initialize profile runner"""
        
        self.profile_name = profile_name
        self.live_mode = live_mode
        self.duration = self._parse_duration(duration_str)
        self.start_time = datetime.now()
        self.end_time = self.start_time + self.duration
        
        # Initialize profile manager
        self.profile_manager = TradingProfileManager()
        self.profile_config = None
        self.trading_system = None
        
        # Performance tracking
        self.initial_balance = None
        self.trades_at_start = 0
        
        # Graceful shutdown
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"🚀 Profile Trading Runner initialized")
        logger.info(f"   Profile: {profile_name}")
        logger.info(f"   Duration: {duration_str} ({self.duration})")
        logger.info(f"   Mode: {'LIVE' if live_mode else 'DEMO'}")
        logger.info(f"   End time: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _parse_duration(self, duration_str: str) -> timedelta:
        """Parse duration string (e.g., '7d', '1w', '24h')"""
        
        duration_str = duration_str.lower().strip()
        
        if duration_str.endswith('d'):
            days = int(duration_str[:-1])
            return timedelta(days=days)
        elif duration_str.endswith('w'):
            weeks = int(duration_str[:-1]) 
            return timedelta(weeks=weeks)
        elif duration_str.endswith('h'):
            hours = int(duration_str[:-1])
            return timedelta(hours=hours)
        elif duration_str.endswith('m'):
            minutes = int(duration_str[:-1])
            return timedelta(minutes=minutes)
        else:
            # Default to hours
            try:
                hours = int(duration_str)
                return timedelta(hours=hours)
            except ValueError:
                raise ValueError(f"Invalid duration format: {duration_str}. Use format like '7d', '1w', '24h'")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"📤 Received shutdown signal ({signum})")
        self.shutdown_requested = True
    
    def load_profile(self):
        """Load and apply the trading profile"""
        
        try:
            # Load profile configuration
            self.profile_config = self.profile_manager.load_profile(self.profile_name)
            
            # Apply profile to global configuration
            self._apply_profile_to_system()
            
            logger.info(f"✅ Profile {self.profile_name} loaded and applied")
            
        except Exception as e:
            logger.error(f"❌ Error loading profile {self.profile_name}: {e}")
            raise
    
    def _apply_profile_to_system(self):
        """Apply profile configuration to trading system"""
        
        # This would modify the global configuration or pass profile-specific
        # parameters to the trading system. For now, we'll store it for
        # the trading system to use.
        
        profile_summary = self.profile_manager.get_profile_summary(self.profile_name)
        
        logger.info(f"📊 Applied profile configuration:")
        logger.info(f"   Risk Level: {profile_summary['risk_level']}")
        logger.info(f"   Trading Frequency: {profile_summary['trading_frequency']}")
        logger.info(f"   Event Strategy: {profile_summary['event_strategy']}")
    
    def initialize_trading_system(self):
        """Initialize the multi-market trading system with profile"""
        
        try:
            # Initialize config loader
            config_loader = MarketConfigLoader()
            
            # Initialize trading system
            self.trading_system = MultiMarketTradingSystem(config_loader)
            
            # Store profile information in trading system
            self.trading_system.active_profile = self.profile_name
            self.trading_system.profile_config = self.profile_config
            
            # Apply profile-specific settings
            self._apply_profile_settings()
            
            logger.info(f"✅ Trading system initialized with {self.profile_name} profile")
            
        except Exception as e:
            logger.error(f"❌ Error initializing trading system: {e}")
            raise
    
    def _apply_profile_settings(self):
        """Apply profile-specific settings to trading system components"""
        
        if not self.profile_config:
            return
        
        try:
            # Apply emergency risk settings
            emergency_risk = self.profile_config.get('emergency_risk', {})
            if emergency_risk:
                risk_manager = self.trading_system.emergency_risk_manager
                
                # Update risk parameters
                risk_manager.MAX_LOSS_PER_TRADE = emergency_risk.get('max_loss_per_trade', risk_manager.MAX_LOSS_PER_TRADE)
                risk_manager.DAILY_LOSS_LIMIT = emergency_risk.get('daily_loss_limit', risk_manager.DAILY_LOSS_LIMIT)
                risk_manager.MAX_POSITION_SIZE = emergency_risk.get('max_position_size', risk_manager.MAX_POSITION_SIZE)
                risk_manager.MAX_TOTAL_EXPOSURE = emergency_risk.get('max_total_exposure', risk_manager.MAX_TOTAL_EXPOSURE)
                risk_manager.MAX_CONSECUTIVE_LOSSES = emergency_risk.get('max_consecutive_losses', risk_manager.MAX_CONSECUTIVE_LOSSES)
                
                logger.info(f"🛡️ Applied emergency risk settings:")
                logger.info(f"   Max position size: {risk_manager.MAX_POSITION_SIZE:.1%}")
                logger.info(f"   Daily loss limit: {risk_manager.DAILY_LOSS_LIMIT:.1%}")
            
            # Apply professional trading settings
            professional_settings = self.profile_config.get('professional_trading', {})
            if professional_settings:
                strategy_engine = self.trading_system.professional_strategy
                
                # Update confidence threshold
                min_confidence = professional_settings.get('min_signal_confidence', 0.6)
                if hasattr(strategy_engine, 'min_signal_strength'):
                    strategy_engine.min_signal_strength = min_confidence
                
                logger.info(f"📈 Applied professional trading settings:")
                logger.info(f"   Min signal confidence: {min_confidence:.1%}")
            
            # Apply economic calendar settings
            calendar_settings = self.profile_config.get('economic_calendar', {})
            if calendar_settings:
                calendar_monitor = self.trading_system.economic_calendar_monitor
                
                # Update pause settings
                calendar_monitor.enabled = calendar_settings.get('enabled', True)
                calendar_monitor.pause_before_minutes = calendar_settings.get('pause_before_minutes', 120)
                calendar_monitor.pause_after_minutes = calendar_settings.get('pause_after_minutes', 120)
                
                logger.info(f"📅 Applied economic calendar settings:")
                logger.info(f"   Enabled: {calendar_monitor.enabled}")
                logger.info(f"   Pause window: {calendar_monitor.pause_before_minutes}min before, {calendar_monitor.pause_after_minutes}min after")
            
        except Exception as e:
            logger.warning(f"⚠️ Error applying some profile settings: {e}")
    
    def start_performance_tracking(self):
        """Start tracking performance for this profile run"""
        
        try:
            # Get initial balance and trade count
            from data.db import get_account_balance
            self.initial_balance = get_account_balance()
            
            # Count trades at start
            self.trades_at_start = trades_collection.count_documents({})
            
            # Start profile performance tracking
            self.profile_manager.start_profile_performance_tracking(self.profile_name)
            
            logger.info(f"📊 Performance tracking started:")
            logger.info(f"   Initial balance: £{self.initial_balance:.2f}")
            logger.info(f"   Trades at start: {self.trades_at_start}")
            
        except Exception as e:
            logger.error(f"❌ Error starting performance tracking: {e}")
    
    def run_trading_session(self):
        """Run the main trading session"""
        
        try:
            # Start the trading system
            logger.info(f"🚀 Starting trading session with {self.profile_name} profile...")
            
            # Start data collection and trading
            self.trading_system.start_trading()
            
            # Main trading loop
            logger.info(f"⏰ Trading session will run until {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            while datetime.now() < self.end_time and not self.shutdown_requested:
                # Check system health
                self._check_system_health()
                
                # Log periodic status
                self._log_periodic_status()
                
                # Sleep for a bit
                import time
                time.sleep(60)  # Check every minute
            
            logger.info("⏹️ Trading session completed")
            
        except Exception as e:
            logger.error(f"❌ Error during trading session: {e}")
            raise
        finally:
            # Always try to stop gracefully
            self._stop_trading_system()
    
    def _check_system_health(self):
        """Check trading system health"""
        
        try:
            if not self.trading_system or not self.trading_system.running:
                logger.warning("⚠️ Trading system not running")
                return False
            
            # Check emergency risk manager status
            risk_status = self.trading_system.emergency_risk_manager.get_risk_status()
            if risk_status.get('trading_halted', False):
                logger.warning(f"⚠️ Trading halted: {risk_status.get('halt_reason', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error checking system health: {e}")
            return False
    
    def _log_periodic_status(self):
        """Log periodic status updates"""
        
        current_time = datetime.now()
        
        # Log every hour on the hour
        if current_time.minute == 0:
            try:
                # Get current performance
                time_remaining = self.end_time - current_time
                
                # Get trade count
                total_trades = trades_collection.count_documents({})
                session_trades = total_trades - self.trades_at_start
                
                # Get current balance
                from data.db import get_account_balance
                current_balance = get_account_balance()
                balance_change = current_balance - self.initial_balance if self.initial_balance else 0
                
                logger.info(f"📊 Hourly Status ({current_time.strftime('%H:%M')}):")
                logger.info(f"   Profile: {self.profile_name}")
                logger.info(f"   Time remaining: {time_remaining}")
                logger.info(f"   Session trades: {session_trades}")
                logger.info(f"   Balance change: £{balance_change:.2f}")
                
            except Exception as e:
                logger.error(f"❌ Error logging periodic status: {e}")
    
    def _stop_trading_system(self):
        """Stop the trading system gracefully"""
        
        try:
            if self.trading_system:
                logger.info("🛑 Stopping trading system...")
                self.trading_system.stop_trading()
                logger.info("✅ Trading system stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping trading system: {e}")
    
    def finalize_performance_tracking(self):
        """Finalize performance tracking and generate report"""
        
        try:
            # Get trades from this session
            session_trades = list(trades_collection.find({
                'timestamp': {
                    '$gte': self.start_time,
                    '$lte': datetime.now()
                }
            }))
            
            # Stop performance tracking
            performance = self.profile_manager.stop_profile_performance_tracking(
                self.profile_name, 
                session_trades
            )
            
            # Generate session report
            self._generate_session_report(performance, session_trades)
            
        except Exception as e:
            logger.error(f"❌ Error finalizing performance tracking: {e}")
    
    def _generate_session_report(self, performance, trades):
        """Generate final session report"""
        
        try:
            # Calculate metrics
            final_balance = None
            try:
                from data.db import get_account_balance
                final_balance = get_account_balance()
            except:
                final_balance = self.initial_balance
            
            balance_change = final_balance - self.initial_balance if self.initial_balance else 0
            balance_change_pct = (balance_change / self.initial_balance * 100) if self.initial_balance else 0
            
            # Create report
            report = {
                'profile': self.profile_name,
                'session_info': {
                    'start_time': self.start_time.isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration': str(datetime.now() - self.start_time),
                    'mode': 'LIVE' if self.live_mode else 'DEMO'
                },
                'performance': {
                    'initial_balance': self.initial_balance,
                    'final_balance': final_balance,
                    'balance_change': balance_change,
                    'balance_change_percent': balance_change_pct,
                    'total_trades': len(trades),
                    'winning_trades': len([t for t in trades if t.get('profit_loss', 0) > 0]),
                    'losing_trades': len([t for t in trades if t.get('profit_loss', 0) < 0]),
                    'win_rate': performance.win_rate if performance else 0,
                    'total_pnl': performance.total_pnl if performance else balance_change
                }
            }
            
            # Save report
            report_filename = f"reports/session_report_{self.profile_name}_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(report_filename), exist_ok=True)
            
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2)
            
            # Print summary
            print(f"\n{'='*60}")
            print(f"📊 TRADING SESSION SUMMARY - {self.profile_name.upper()} PROFILE")
            print(f"{'='*60}")
            print(f"Duration: {datetime.now() - self.start_time}")
            print(f"Total Trades: {report['performance']['total_trades']}")
            print(f"Win Rate: {report['performance']['win_rate']:.1f}%")
            print(f"Balance Change: £{balance_change:.2f} ({balance_change_pct:+.2f}%)")
            print(f"Report saved: {report_filename}")
            print(f"{'='*60}")
            
        except Exception as e:
            logger.error(f"❌ Error generating session report: {e}")

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="Run trading with specific profile")
    parser.add_argument("--profile", "-p", required=True, 
                       choices=["conservative", "aggressive", "scalping"],
                       help="Trading profile to use")
    parser.add_argument("--duration", "-d", default="1d",
                       help="Duration to run (e.g., 1d, 7d, 1w, 24h)")
    parser.add_argument("--live", action="store_true",
                       help="Run in live mode (default: demo)")
    parser.add_argument("--paper", action="store_true", 
                       help="Force paper trading mode")
    
    args = parser.parse_args()
    
    # Override live mode if paper trading requested
    live_mode = args.live and not args.paper
    
    print(f"🚀 Starting Profile-Based Trading Session")
    print(f"Profile: {args.profile.upper()}")
    print(f"Duration: {args.duration}")
    print(f"Mode: {'LIVE' if live_mode else 'DEMO/PAPER'}")
    print("")
    
    try:
        # Initialize runner
        runner = ProfileTradingRunner(
            profile_name=args.profile,
            duration_str=args.duration,
            live_mode=live_mode
        )
        
        # Load profile
        runner.load_profile()
        
        # Initialize trading system
        runner.initialize_trading_system()
        
        # Start performance tracking
        runner.start_performance_tracking()
        
        # Run trading session
        runner.run_trading_session()
        
        # Finalize and report
        runner.finalize_performance_tracking()
        
        print("✅ Trading session completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Trading session interrupted by user")
    except Exception as e:
        print(f"❌ Error during trading session: {e}")
        logger.error(f"Trading session error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()