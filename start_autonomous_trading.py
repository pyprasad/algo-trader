#!/usr/bin/env python3
"""
🚀 Autonomous Trading System Startup Script

This script ensures all components run automatically:
- Dynamic Position Manager (for consistent stop loss management)
- News Sentiment Analysis (configurable hourly checks)
- Main trading system

Usage: python start_autonomous_trading.py

Author: Enhanced Autonomous Trading System
"""

import sys
import os
import time
import threading
from datetime import datetime
import signal

# Add current directory to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import required modules
from core.dynamic_position_manager import get_dynamic_position_manager
from data.news_sentiment import get_sentiment_engine
from utils.config_loader import load_global_config

# Load configuration
config = load_global_config()

class AutonomousTradingSystem:
    """Main orchestrator for autonomous trading system"""
    
    def __init__(self):
        self.running = False
        self.components = {}
        
        # Initialize components
        self.dynamic_position_manager = get_dynamic_position_manager()
        self.sentiment_engine = get_sentiment_engine()
        
        # Configuration
        self.sentiment_config = config.get("sentiment_analysis", {})
        self.markets = self.sentiment_config.get("markets", ["DAX", "FTSE"])
        
        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def start(self):
        """Start all autonomous trading components"""
        print("🚀 Starting Autonomous Trading System")
        print("=" * 50)
        
        self.running = True
        
        # 1. Start Dynamic Position Manager (for consistent stop loss management)
        print("\n📊 Starting Dynamic Position Manager...")
        if self.dynamic_position_manager.enabled:
            success = self.dynamic_position_manager.start()
            if success:
                print("✅ Dynamic Position Manager started successfully")
                self.components["dynamic_position_manager"] = True
            else:
                print("❌ Failed to start Dynamic Position Manager")
                self.components["dynamic_position_manager"] = False
        else:
            print("⚠️ Dynamic Position Manager is disabled in configuration")
            self.components["dynamic_position_manager"] = False
        
        # 2. Start Sentiment Analysis (configurable hourly)
        print("\n📰 Starting Sentiment Analysis...")
        if self.sentiment_config.get("enabled", True):
            interval_minutes = self.sentiment_config.get("check_interval_minutes", 60)
            print(f"   Configured for every {interval_minutes} minutes")
            print(f"   Markets: {self.markets}")
            print(f"   Respects market hours: {self.sentiment_config.get('respect_market_hours', True)}")
            
            self.sentiment_engine.start_continuous_monitoring(
                markets=self.markets,
                interval_minutes=interval_minutes
            )
            self.components["sentiment_analysis"] = True
            print("✅ Sentiment Analysis started successfully")
        else:
            print("⚠️ Sentiment Analysis is disabled in configuration")
            self.components["sentiment_analysis"] = False
        
        # 3. System Status Report
        print("\n📈 System Status:")
        print(f"   🎯 Dynamic Position Manager: {'✅ RUNNING' if self.components.get('dynamic_position_manager') else '❌ DISABLED'}")
        print(f"   📰 Sentiment Analysis: {'✅ RUNNING' if self.components.get('sentiment_analysis') else '❌ DISABLED'}")
        
        # 4. Show configuration summary
        self._show_configuration_summary()
        
        # 5. Start monitoring loop
        print("\n🔄 Starting system monitoring...")
        self._start_system_monitoring()
        
    def _show_configuration_summary(self):
        """Show current system configuration"""
        print("\n⚙️ Configuration Summary:")
        
        # Dynamic Position Manager config
        if self.dynamic_position_manager.enabled:
            print("   🎯 Dynamic Position Manager:")
            print(f"      • Update interval: {self.dynamic_position_manager.update_interval}s")
            print(f"      • Confidence threshold: {self.dynamic_position_manager.confidence_threshold}")
            print(f"      • Limit range: {self.dynamic_position_manager.min_decrease}x - {self.dynamic_position_manager.max_increase}x")
            if self.dynamic_position_manager.emergency_enabled:
                print(f"      • Emergency protection: ACTIVE ({self.dynamic_position_manager.immediate_loss_threshold} pips threshold)")
        
        # Sentiment Analysis config
        if self.sentiment_config.get("enabled"):
            print("   📰 Sentiment Analysis:")
            print(f"      • Check interval: {self.sentiment_config.get('check_interval_minutes', 60)} minutes")
            print(f"      • Markets: {self.markets}")
            print(f"      • Market hours: {self.sentiment_config.get('market_hours', {}).get('start_hour', 7)}:00 - {self.sentiment_config.get('market_hours', {}).get('end_hour', 18)}:00")
            print(f"      • Skip weekends: {self.sentiment_config.get('market_hours', {}).get('skip_weekends', True)}")
        
    def _start_system_monitoring(self):
        """Start system health monitoring"""
        def monitoring_loop():
            while self.running:
                try:
                    # Check system health every 5 minutes
                    time.sleep(300)
                    if self.running:
                        self._check_system_health()
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
        
        monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # Keep main thread alive
        print("✅ Autonomous Trading System is now running")
        print("📍 Press Ctrl+C to stop gracefully")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown()
    
    def _check_system_health(self):
        """Perform system health checks"""
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Check Dynamic Position Manager
        dpm_status = self.dynamic_position_manager.get_status() if self.dynamic_position_manager.enabled else None
        
        # Basic health report
        print(f"\n💓 System Health Check ({current_time}):")
        
        if dpm_status:
            print(f"   🎯 Dynamic Position Manager: {'✅ RUNNING' if dpm_status['running'] else '❌ STOPPED'}")
            if dpm_status['running']:
                print(f"      • Positions managed: {dpm_status['positions_managed']}")
                print(f"      • Total adjustments: {dpm_status['total_adjustments']}")
        
        print(f"   📰 Sentiment Analysis: {'✅ RUNNING' if self.sentiment_engine.running else '❌ STOPPED'}")
        
        # Check if we need to restart any components
        if self.dynamic_position_manager.enabled and dpm_status and not dpm_status['running']:
            print("🔄 Attempting to restart Dynamic Position Manager...")
            self.dynamic_position_manager.start()
        
        if self.sentiment_config.get("enabled") and not self.sentiment_engine.running:
            print("🔄 Attempting to restart Sentiment Analysis...")
            self.sentiment_engine.start_continuous_monitoring(
                markets=self.markets,
                interval_minutes=self.sentiment_config.get("check_interval_minutes", 60)
            )
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        self._shutdown()
    
    def _shutdown(self):
        """Gracefully shutdown all components"""
        print("\n🛑 Shutting down Autonomous Trading System...")
        
        self.running = False
        
        # Stop Dynamic Position Manager
        if self.dynamic_position_manager.enabled and hasattr(self.dynamic_position_manager, 'running'):
            print("   Stopping Dynamic Position Manager...")
            self.dynamic_position_manager.stop()
        
        # Stop Sentiment Analysis
        if hasattr(self.sentiment_engine, 'running'):
            print("   Stopping Sentiment Analysis...")
            self.sentiment_engine.stop_monitoring()
        
        print("✅ Autonomous Trading System shutdown complete")
        sys.exit(0)

def main():
    """Main entry point"""
    print("🎯 Initializing Autonomous Trading System...")
    
    # Create and start the system
    trading_system = AutonomousTradingSystem()
    trading_system.start()

if __name__ == "__main__":
    main()