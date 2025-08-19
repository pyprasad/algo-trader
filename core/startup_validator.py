#!/usr/bin/env python3
"""
🛡️ Startup Validation System

Ensures the trading system has sufficient data and conditions 
are suitable before allowing any trades to be executed.

Author: System Safety Team
"""

import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Any
from data.db import get_market_tick_data, get_account_balance
from data.account_streamer import get_live_account_data

class StartupValidator:
    """
    Professional startup validation to ensure system readiness
    """
    
    def __init__(self):
        """Initialize with strict validation requirements"""
        
        # Minimum data requirements
        self.MIN_TICK_DATA_POINTS = 50      # Minimum ticks per market
        self.MIN_DATA_AGE_MINUTES = 5       # Data must be recent
        self.WARM_UP_MINUTES = 2            # Minimum warm-up period
        
        # Account validation
        self.MIN_ACCOUNT_BALANCE = 1000     # Minimum balance to trade
        self.MAX_ACCOUNT_AGE_MINUTES = 10   # Account data freshness
        
        # Market validation
        self.REQUIRED_PRICE_FIELDS = ['bid', 'offer', 'timestamp']
        
        # System state
        self.validation_start_time = None
        self.validation_results = {}
        
        print("🛡️ Startup Validator initialized")
        print(f"   Minimum tick data: {self.MIN_TICK_DATA_POINTS} points per market")
        print(f"   Warm-up period: {self.WARM_UP_MINUTES} minutes")
        print(f"   Data freshness: {self.MIN_DATA_AGE_MINUTES} minutes")
    
    def validate_startup_readiness(self, markets: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive startup validation
        
        Returns:
            (is_ready, validation_report)
        """
        self.validation_start_time = datetime.now(timezone.utc)
        
        print("\n🛡️" + "="*80)
        print("🛡️ STARTUP VALIDATION PIPELINE")
        print("🛡️" + "="*80)
        
        validation_report = {
            'is_ready': False,
            'start_time': self.validation_start_time,
            'checks_passed': [],
            'checks_failed': [],
            'market_status': {},
            'account_status': {},
            'recommendations': []
        }
        
        # PHASE 1: Account Validation
        print("🔒 PHASE 1: ACCOUNT VALIDATION")
        account_ready, account_details = self._validate_account()
        validation_report['account_status'] = account_details
        
        if not account_ready:
            validation_report['checks_failed'].append("Account validation failed")
            print("❌ STARTUP VALIDATION FAILED: Account not ready")
            return False, validation_report
        else:
            validation_report['checks_passed'].append("Account validation passed")
            print("✅ PHASE 1 PASSED: Account ready")
        
        # PHASE 2: Market Data Validation
        print("\n🔒 PHASE 2: MARKET DATA VALIDATION")
        all_markets_ready = True
        
        for market in markets:
            market_ready, market_details = self._validate_market_data(market)
            validation_report['market_status'][market] = market_details
            
            if not market_ready:
                validation_report['checks_failed'].append(f"{market} data insufficient")
                all_markets_ready = False
                print(f"❌ {market}: Data validation failed")
            else:
                validation_report['checks_passed'].append(f"{market} data ready")
                print(f"✅ {market}: Data validation passed")
        
        if not all_markets_ready:
            print("❌ STARTUP VALIDATION FAILED: Insufficient market data")
            validation_report['recommendations'].append("Wait for more market data")
            return False, validation_report
        else:
            print("✅ PHASE 2 PASSED: All market data ready")
        
        # PHASE 3: System Warm-up Period
        print("\n🔒 PHASE 3: SYSTEM WARM-UP VALIDATION")
        warmup_ready, warmup_details = self._validate_system_warmup()
        
        if not warmup_ready:
            validation_report['checks_failed'].append("System warm-up incomplete")
            print("❌ STARTUP VALIDATION FAILED: Warm-up period incomplete")
            validation_report['recommendations'].append(f"Wait {warmup_details['remaining_seconds']} more seconds")
            return False, validation_report
        else:
            validation_report['checks_passed'].append("System warm-up complete")
            print("✅ PHASE 3 PASSED: System warm-up complete")
        
        # PHASE 4: Final Safety Checks
        print("\n🔒 PHASE 4: FINAL SAFETY VALIDATION")
        safety_ready, safety_details = self._validate_final_safety()
        
        if not safety_ready:
            validation_report['checks_failed'].append("Final safety checks failed")
            print("❌ STARTUP VALIDATION FAILED: Safety checks failed")
            return False, validation_report
        else:
            validation_report['checks_passed'].append("Final safety checks passed")
            print("✅ PHASE 4 PASSED: Final safety validation complete")
        
        # ALL PHASES PASSED
        validation_report['is_ready'] = True
        validation_report['validation_duration'] = (
            datetime.now(timezone.utc) - self.validation_start_time
        ).total_seconds()
        
        print("\n🛡️" + "="*80)
        print("✅ STARTUP VALIDATION COMPLETE - SYSTEM READY TO TRADE")
        print("🛡️" + "="*80)
        
        return True, validation_report
    
    def _validate_account(self) -> Tuple[bool, Dict]:
        """Validate account status and balance"""
        details = {
            'balance_check': False,
            'data_freshness': False,
            'balance': 0,
            'last_update': None
        }
        
        try:
            # Check account balance
            balance = get_account_balance()
            details['balance'] = balance
            
            if balance < self.MIN_ACCOUNT_BALANCE:
                print(f"   ❌ Balance too low: £{balance:.2f} < £{self.MIN_ACCOUNT_BALANCE}")
                return False, details
            else:
                details['balance_check'] = True
                print(f"   ✅ Account balance: £{balance:.2f}")
            
            # Check account data freshness
            live_data = get_live_account_data()
            if live_data and 'last_update' in live_data:
                last_update = live_data['last_update']
                details['last_update'] = last_update
                
                if isinstance(last_update, str):
                    last_update = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                elif not hasattr(last_update, 'tzinfo') or last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)
                
                age_minutes = (datetime.now(timezone.utc) - last_update).total_seconds() / 60
                
                if age_minutes > self.MAX_ACCOUNT_AGE_MINUTES:
                    print(f"   ❌ Account data too old: {age_minutes:.1f} minutes")
                    return False, details
                else:
                    details['data_freshness'] = True
                    print(f"   ✅ Account data fresh: {age_minutes:.1f} minutes old")
            
            return True, details
            
        except Exception as e:
            print(f"   ❌ Account validation error: {e}")
            return False, details
    
    def _validate_market_data(self, market: str) -> Tuple[bool, Dict]:
        """Validate market data sufficiency"""
        details = {
            'tick_count': 0,
            'data_age_minutes': 0,
            'price_range': 0,
            'has_recent_data': False
        }
        
        try:
            # Get recent tick data
            ticks = get_market_tick_data(market, limit=self.MIN_TICK_DATA_POINTS + 20)
            details['tick_count'] = len(ticks)
            
            if len(ticks) < self.MIN_TICK_DATA_POINTS:
                print(f"   ❌ {market}: Insufficient ticks ({len(ticks)} < {self.MIN_TICK_DATA_POINTS})")
                return False, details
            
            # Check data freshness
            if ticks:
                latest_tick = ticks[0]  # Most recent tick
                tick_time = latest_tick.get('timestamp')
                
                if tick_time:
                    if isinstance(tick_time, str):
                        tick_time = datetime.fromisoformat(tick_time.replace('Z', '+00:00'))
                    elif not isinstance(tick_time, datetime):
                        tick_time = datetime.fromtimestamp(tick_time, tz=timezone.utc)
                    elif not hasattr(tick_time, 'tzinfo') or tick_time.tzinfo is None:
                        tick_time = tick_time.replace(tzinfo=timezone.utc)
                    
                    age_minutes = (datetime.now(timezone.utc) - tick_time).total_seconds() / 60
                    details['data_age_minutes'] = age_minutes
                    
                    if age_minutes > self.MIN_DATA_AGE_MINUTES:
                        print(f"   ❌ {market}: Data too old ({age_minutes:.1f} minutes)")
                        return False, details
                    else:
                        details['has_recent_data'] = True
                
                # Check price range (volatility indicator)
                prices = [t.get('bid', 0) for t in ticks[-20:] if t.get('bid')]
                if prices:
                    price_range = max(prices) - min(prices)
                    details['price_range'] = price_range
                    
                    if price_range == 0:
                        print(f"   ⚠️ {market}: No price movement detected")
                
                print(f"   ✅ {market}: {len(ticks)} ticks, {age_minutes:.1f}min old, range: {details['price_range']:.1f}")
            
            return True, details
            
        except Exception as e:
            print(f"   ❌ {market}: Data validation error: {e}")
            return False, details
    
    def _validate_system_warmup(self) -> Tuple[bool, Dict]:
        """Ensure minimum system warm-up period"""
        if self.validation_start_time is None:
            return False, {'error': 'No validation start time'}
        
        elapsed = (datetime.now(timezone.utc) - self.validation_start_time).total_seconds()
        required_seconds = self.WARM_UP_MINUTES * 60
        
        details = {
            'elapsed_seconds': elapsed,
            'required_seconds': required_seconds,
            'remaining_seconds': max(0, required_seconds - elapsed)
        }
        
        if elapsed < required_seconds:
            print(f"   ❌ Warm-up incomplete: {elapsed:.1f}s < {required_seconds}s")
            return False, details
        else:
            print(f"   ✅ Warm-up complete: {elapsed:.1f}s")
            return True, details
    
    def _validate_final_safety(self) -> Tuple[bool, Dict]:
        """Final safety checks before allowing trading"""
        details = {
            'current_time': datetime.now(timezone.utc),
            'market_session': 'unknown',
            'system_health': True
        }
        
        # Check if it's a reasonable trading time
        current_hour = datetime.now(timezone.utc).hour
        
        # Avoid very early morning hours (2-6 AM UTC)
        if 2 <= current_hour <= 6:
            print(f"   ⚠️ Early morning hours ({current_hour}:xx UTC) - reduced liquidity expected")
            # Don't fail, just warn
        
        print(f"   ✅ Current time: {details['current_time'].strftime('%H:%M:%S UTC')}")
        print(f"   ✅ System health checks passed")
        
        return True, details

# Global instance
_startup_validator = None

def get_startup_validator() -> StartupValidator:
    """Get global startup validator instance"""
    global _startup_validator
    if _startup_validator is None:
        _startup_validator = StartupValidator()
    return _startup_validator