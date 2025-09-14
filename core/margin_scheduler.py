# core/margin_scheduler.py

"""
📅 Margin Rate Scheduler

Predictive scheduler that pre-calculates margin rate transitions to minimize 
real-time API calls and ensure accurate position sizing at all times.

Key Features:
- Predictive rate transition scheduling
- Automatic margin rate updates based on market hours
- Background thread management for continuous operation
- Integration with MarginRateManager for seamless operation
- Minimal API usage through intelligent pre-calculation

Author: Advanced Trading Systems
"""

import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import yaml
from dataclasses import dataclass

# Import secure configuration
from core.secure_config import get_secure_config

from core.margin_rate_manager import get_margin_rate_manager, MarketSession

@dataclass
class ScheduledRateChange:
    """Container for scheduled margin rate changes"""
    instrument: str
    change_time: datetime
    from_session: MarketSession
    to_session: MarketSession
    old_rate: float
    new_rate: float
    executed: bool = False

class MarginScheduler:
    """
    Intelligent scheduler that predicts and handles margin rate transitions
    automatically without requiring real-time API calls
    """
    
    def __init__(self):
        """Initialize the margin scheduler"""
        # Load secure configuration
        self.config = get_secure_config()
        margin_config = self.config.get("margin_management", {})
        self.enabled = margin_config.get("enabled", True)
        
        api_config = margin_config.get("api_optimization", {})
        self.bulk_fetch_hour = api_config.get("bulk_fetch_hour", 6)  # UTC
        
        # Scheduler settings
        self.check_interval_minutes = 5  # How often to check for rate changes
        self.preload_window_hours = 24  # How far ahead to schedule changes
        
        # Internal state
        self.scheduled_changes = []  # List of ScheduledRateChange
        self.running = False
        self.scheduler_thread = None
        self.margin_manager = get_margin_rate_manager()
        self.lock = threading.Lock()
        
        # Callbacks for rate changes
        self.rate_change_callbacks = []  # Functions to call when rates change
        
        print(f"📅 Margin Scheduler initialized")
        print(f"   Status: {'✅ ENABLED' if self.enabled else '❌ DISABLED'}")
        if self.enabled:
            print(f"   Check Interval: {self.check_interval_minutes} minutes")
            print(f"   Preload Window: {self.preload_window_hours} hours")
            print(f"   Daily Sync Time: {self.bulk_fetch_hour:02d}:00 UTC")
    
    def start(self):
        """Start the margin rate scheduler"""
        if not self.enabled:
            print("⚠️ Margin Scheduler is disabled")
            return False
        
        print("📅 Starting Margin Scheduler...")
        self.running = True
        
        # Schedule daily bulk operations
        schedule.clear()  # Clear any existing schedules
        schedule.every().day.at(f"{self.bulk_fetch_hour:02d}:00").do(self._daily_sync)
        
        # Start the scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Perform initial sync
        self._daily_sync()
        
        print("✅ Margin Scheduler started")
        return True
    
    def stop(self):
        """Stop the margin scheduler"""
        print("🛑 Stopping Margin Scheduler...")
        self.running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        print("✅ Margin Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Check for rate changes every few minutes
                if datetime.utcnow().minute % self.check_interval_minutes == 0:
                    self._check_scheduled_changes()
                
                # Sleep for a minute
                time.sleep(60)
                
            except Exception as e:
                print(f"❌ Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _daily_sync(self):
        """Daily synchronization of margin rates and schedules"""
        print(f"🔄 Daily margin rate sync starting at {datetime.utcnow().strftime('%H:%M UTC')}")
        
        try:
            # Clear old executed changes
            self._cleanup_old_changes()
            
            # Get active instruments from recent trades or configuration
            active_instruments = self._get_active_instruments()
            
            # Schedule rate changes for the next 24 hours
            scheduled_count = self._schedule_rate_changes(active_instruments)
            
            # Preload current margin rates
            preloaded_count = self.margin_manager.preload_margin_rates(active_instruments)
            
            print(f"✅ Daily sync complete:")
            print(f"   Scheduled {scheduled_count} rate changes")
            print(f"   Preloaded {preloaded_count} margin rates")
            print(f"   API requests used: {self.margin_manager.get_api_usage_status()['requests_used']}")
            
        except Exception as e:
            print(f"❌ Error in daily sync: {e}")
    
    def _get_active_instruments(self) -> List[str]:
        """Get list of currently active trading instruments"""
        try:
            # Try to get from recent trades in database
            from data.db import trades_collection
            
            # Get instruments traded in last 7 days
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_trades = trades_collection.find(
                {"timestamp": {"$gte": week_ago}},
                {"market": 1}
            )
            
            active_instruments = list(set([trade["market"] for trade in recent_trades if trade.get("market")]))
            
            if not active_instruments:
                # Fallback to common instruments
                active_instruments = [
                    "IX.D.FTSE.DAILY.IP",
                    "IX.D.DAX.DAILY.IP", 
                    "CS.D.EURUSD.MINI.IP",
                    "CS.D.GBPUSD.MINI.IP"
                ]
            
            print(f"📊 Found {len(active_instruments)} active instruments")
            return active_instruments
            
        except Exception as e:
            print(f"⚠️ Error getting active instruments: {e}")
            # Return common instruments as fallback
            return [
                "IX.D.FTSE.DAILY.IP",
                "IX.D.DAX.DAILY.IP",
                "CS.D.EURUSD.MINI.IP"
            ]
    
    def _schedule_rate_changes(self, instruments: List[str]) -> int:
        """Schedule rate changes for instruments within the preload window"""
        scheduled_count = 0
        now = datetime.utcnow()
        window_end = now + timedelta(hours=self.preload_window_hours)
        
        with self.lock:
            for instrument in instruments:
                try:
                    # Get next rate change for this instrument
                    next_change = self.margin_manager.get_next_rate_change(instrument)
                    
                    if next_change and next_change[0] <= window_end:
                        change_time, new_session, new_rate = next_change
                        
                        # Get current session and rate for comparison
                        current_session = self.margin_manager._get_current_market_session(instrument)
                        current_rate = self.margin_manager.get_current_margin_rate(instrument)
                        
                        # Create scheduled change
                        scheduled_change = ScheduledRateChange(
                            instrument=instrument,
                            change_time=change_time,
                            from_session=current_session,
                            to_session=new_session,
                            old_rate=current_rate,
                            new_rate=new_rate
                        )
                        
                        # Check if we already have this change scheduled
                        if not self._is_change_already_scheduled(scheduled_change):
                            self.scheduled_changes.append(scheduled_change)
                            scheduled_count += 1
                            
                            print(f"📅 Scheduled: {instrument} rate change at {change_time.strftime('%H:%M UTC')} ({current_rate:.4f} -> {new_rate:.4f})")
                
                except Exception as e:
                    print(f"⚠️ Error scheduling changes for {instrument}: {e}")
        
        return scheduled_count
    
    def _is_change_already_scheduled(self, new_change: ScheduledRateChange) -> bool:
        """Check if a similar change is already scheduled"""
        for existing_change in self.scheduled_changes:
            if (existing_change.instrument == new_change.instrument and
                existing_change.change_time == new_change.change_time and
                not existing_change.executed):
                return True
        return False
    
    def _check_scheduled_changes(self):
        """Check and execute any scheduled rate changes"""
        now = datetime.utcnow()
        executed_changes = []
        
        with self.lock:
            for change in self.scheduled_changes:
                if not change.executed and change.change_time <= now:
                    try:
                        # Execute the rate change
                        self._execute_rate_change(change)
                        change.executed = True
                        executed_changes.append(change)
                        
                    except Exception as e:
                        print(f"❌ Error executing rate change for {change.instrument}: {e}")
        
        # Notify about executed changes
        for change in executed_changes:
            self._notify_rate_change(change)
    
    def _execute_rate_change(self, change: ScheduledRateChange):
        """Execute a scheduled rate change"""
        print(f"🔄 Executing rate change for {change.instrument}:")
        print(f"   Session: {change.from_session.value} -> {change.to_session.value}")
        print(f"   Rate: {change.old_rate:.4f} -> {change.new_rate:.4f}")
        
        # Update the margin manager's cache with the new rate
        self.margin_manager._cache_margin_rate(
            change.instrument, 
            change.to_session, 
            change.new_rate
        )
        
        print(f"✅ Rate change executed for {change.instrument}")
    
    def _notify_rate_change(self, change: ScheduledRateChange):
        """Notify registered callbacks about rate changes"""
        for callback in self.rate_change_callbacks:
            try:
                callback(change)
            except Exception as e:
                print(f"⚠️ Error in rate change callback: {e}")
    
    def _cleanup_old_changes(self):
        """Remove old executed changes to keep memory usage low"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        with self.lock:
            old_count = len(self.scheduled_changes)
            self.scheduled_changes = [
                change for change in self.scheduled_changes 
                if not (change.executed and change.change_time < cutoff_time)
            ]
            removed_count = old_count - len(self.scheduled_changes)
            
            if removed_count > 0:
                print(f"🧹 Cleaned up {removed_count} old rate changes")
    
    def register_rate_change_callback(self, callback: Callable[[ScheduledRateChange], None]):
        """Register a callback function to be called when rates change"""
        self.rate_change_callbacks.append(callback)
        print(f"📞 Registered rate change callback: {callback.__name__}")
    
    def get_upcoming_changes(self, hours: int = 24) -> List[ScheduledRateChange]:
        """Get upcoming rate changes within specified hours"""
        cutoff_time = datetime.utcnow() + timedelta(hours=hours)
        
        with self.lock:
            upcoming = [
                change for change in self.scheduled_changes
                if not change.executed and change.change_time <= cutoff_time
            ]
            
        # Sort by change time
        upcoming.sort(key=lambda x: x.change_time)
        return upcoming
    
    def force_rate_update(self, instrument: str) -> bool:
        """Force an immediate rate update for a specific instrument"""
        try:
            print(f"🔄 Forcing rate update for {instrument}")
            
            # Get current rate (this will refresh the cache)
            current_rate = self.margin_manager.get_current_margin_rate(instrument)
            
            # Schedule next change
            next_change = self.margin_manager.get_next_rate_change(instrument)
            if next_change:
                change_time, new_session, new_rate = next_change
                current_session = self.margin_manager._get_current_market_session(instrument)
                
                with self.lock:
                    # Remove any existing scheduled change for this instrument
                    self.scheduled_changes = [
                        change for change in self.scheduled_changes
                        if change.instrument != instrument or change.executed
                    ]
                    
                    # Add new scheduled change
                    scheduled_change = ScheduledRateChange(
                        instrument=instrument,
                        change_time=change_time,
                        from_session=current_session,
                        to_session=new_session,
                        old_rate=current_rate,
                        new_rate=new_rate
                    )
                    self.scheduled_changes.append(scheduled_change)
                
                print(f"✅ Updated rate for {instrument}: {current_rate:.4f}, next change at {change_time}")
                return True
            
        except Exception as e:
            print(f"❌ Error forcing rate update for {instrument}: {e}")
        
        return False
    
    def get_status(self) -> Dict:
        """Get comprehensive status of the margin scheduler"""
        now = datetime.utcnow()
        
        with self.lock:
            total_changes = len(self.scheduled_changes)
            executed_changes = sum(1 for change in self.scheduled_changes if change.executed)
            pending_changes = total_changes - executed_changes
            
            # Get next change
            next_change = None
            for change in sorted(self.scheduled_changes, key=lambda x: x.change_time):
                if not change.executed:
                    next_change = change
                    break
        
        return {
            "enabled": self.enabled,
            "running": self.running,
            "total_scheduled_changes": total_changes,
            "executed_changes": executed_changes,
            "pending_changes": pending_changes,
            "registered_callbacks": len(self.rate_change_callbacks),
            "next_change": {
                "instrument": next_change.instrument,
                "time": next_change.change_time.isoformat(),
                "rate_change": f"{next_change.old_rate:.4f} -> {next_change.new_rate:.4f}"
            } if next_change else None,
            "next_daily_sync": f"{self.bulk_fetch_hour:02d}:00 UTC"
        }

# Global instance
_margin_scheduler = None

def get_margin_scheduler() -> MarginScheduler:
    """Get global margin scheduler instance"""
    global _margin_scheduler
    if _margin_scheduler is None:
        _margin_scheduler = MarginScheduler()
    return _margin_scheduler

if __name__ == "__main__":
    # Test the margin scheduler
    print("🧪 Testing Margin Scheduler")
    print("=" * 50)
    
    scheduler = MarginScheduler()
    
    # Test callback registration
    def test_callback(change: ScheduledRateChange):
        print(f"📞 Rate change callback: {change.instrument} -> {change.new_rate:.4f}")
    
    scheduler.register_rate_change_callback(test_callback)
    
    # Show upcoming changes
    upcoming = scheduler.get_upcoming_changes(hours=48)
    print(f"📅 Upcoming changes in next 48 hours: {len(upcoming)}")
    for change in upcoming[:5]:  # Show first 5
        print(f"   {change.instrument}: {change.change_time.strftime('%H:%M UTC')} -> {change.new_rate:.4f}")
    
    # Show status
    status = scheduler.get_status()
    print(f"📈 Scheduler Status:")
    for key, value in status.items():
        if key != "next_change":
            print(f"   {key}: {value}")
    
    if status["next_change"]:
        next_change = status["next_change"]
        print(f"   Next change: {next_change['instrument']} at {next_change['time']} ({next_change['rate_change']})")
    
    # Test force update
    test_instrument = "IX.D.FTSE.DAILY.IP"
    success = scheduler.force_rate_update(test_instrument)
    print(f"🔄 Force update for {test_instrument}: {'✅' if success else '❌'}")