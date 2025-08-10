#!/usr/bin/env python3
"""
📊 Professional Trading Monitor & Performance Analytics

Advanced monitoring system with:
- Real-time performance tracking
- Risk-adjusted metrics (Sharpe ratio, Calmar ratio)
- Drawdown analysis and alerts
- Trade quality scoring
- Performance attribution analysis
- Automated reporting

Author: Professional Trading Analytics
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict
import numpy as np
from collections import deque, defaultdict

from data.db import trades_collection, get_account_balance
from core.emergency_risk_manager import get_emergency_risk_manager

class ProfessionalTradingMonitor:
    """
    Professional-grade trading performance monitoring and analytics
    """
    
    def __init__(self):
        """Initialize professional trading monitor"""
        
        # Performance tracking
        self.performance_history = deque(maxlen=1000)
        self.daily_metrics = {}
        self.weekly_metrics = {}
        self.monthly_metrics = {}
        
        # Risk metrics
        self.max_drawdown = 0.0
        initial_balance = get_account_balance()
        self.peak_balance = initial_balance if initial_balance is not None else 0.0
        self.current_drawdown = 0.0
        
        # Trade quality tracking
        self.trade_quality_scores = deque(maxlen=100)
        self.win_rate_by_market = defaultdict(list)
        self.win_rate_by_timeframe = defaultdict(list)
        
        # Performance attribution
        self.strategy_performance = defaultdict(dict)
        self.market_performance = defaultdict(dict)
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.last_alert_time = {}
        
        # Alert thresholds
        self.DRAWDOWN_WARNING = 0.05    # 5% drawdown warning
        self.DRAWDOWN_CRITICAL = 0.10   # 10% drawdown critical
        self.MIN_SHARPE_RATIO = 1.0     # Minimum acceptable Sharpe ratio
        self.MIN_WIN_RATE = 0.4         # Minimum acceptable win rate
        
        print("📊 Professional Trading Monitor initialized")
        print(f"   Drawdown alerts: {self.DRAWDOWN_WARNING:.1%} warning, {self.DRAWDOWN_CRITICAL:.1%} critical")
        print(f"   Performance targets: Sharpe >{self.MIN_SHARPE_RATIO:.1f}, Win rate >{self.MIN_WIN_RATE:.1%}")
    
    def start_monitoring(self):
        """Start continuous performance monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            print("📈 Professional monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("📊 Professional monitoring stopped")
    
    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.monitoring_active:
            try:
                # Update performance metrics every 30 seconds
                self.update_performance_metrics()
                
                # Check for alerts every 30 seconds
                self.check_performance_alerts()
                
                # Generate reports every hour
                current_time = datetime.now()
                if current_time.minute == 0:
                    self.generate_hourly_report()
                
                time.sleep(30)
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                time.sleep(30)
    
    def update_performance_metrics(self):
        """Update all performance metrics"""
        
        # Get current account balance
        current_balance = get_account_balance()
        
        # Handle None values
        if current_balance is None:
            print("⚠️ Warning: Unable to get account balance")
            return
            
        # Initialize peak_balance if it's None
        if self.peak_balance is None:
            self.peak_balance = current_balance
        
        # Update peak and drawdown
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance if self.peak_balance > 0 else 0.0
            
        if self.current_drawdown > self.max_drawdown:
            self.max_drawdown = self.current_drawdown
        
        # Calculate daily P&L
        today = datetime.now().date()
        daily_trades = list(trades_collection.find({
            "timestamp": {
                "$gte": datetime.combine(today, datetime.min.time()),
                "$lt": datetime.combine(today + timedelta(days=1), datetime.min.time())
            },
            "status": {"$in": ["CLOSED", "OPEN"]}
        }))
        
        daily_pnl = sum(trade.get('profit_loss', 0) for trade in daily_trades)
        
        # Update performance history
        self.performance_history.append({
            'timestamp': datetime.now(),
            'balance': current_balance,
            'daily_pnl': daily_pnl,
            'drawdown': self.current_drawdown,
            'open_trades': len([t for t in daily_trades if t.get('status') == 'OPEN'])
        })
        
        # Calculate risk metrics
        self._calculate_risk_metrics()
        
        # Update trade quality scores
        self._update_trade_quality()
    
    def _calculate_risk_metrics(self):
        """Calculate risk-adjusted performance metrics"""
        
        if len(self.performance_history) < 10:
            return
        
        # Get returns series
        balances = [p['balance'] for p in self.performance_history]
        # Ensure no division by zero
        balances_array = np.array(balances[:-1])
        balances_array[balances_array == 0] = 1e-10  # Replace zeros with small value
        returns = np.diff(balances) / balances_array
        
        # Calculate Sharpe ratio (annualized)
        if len(returns) > 0 and np.std(returns) > 0:
            daily_sharpe = np.mean(returns) / np.std(returns)
            annualized_sharpe = daily_sharpe * np.sqrt(252)  # 252 trading days
        else:
            annualized_sharpe = 0
        
        # Calculate Calmar ratio (return / max drawdown)
        if self.max_drawdown > 0:
            annual_return = (balances[-1] / balances[0] - 1) if len(balances) > 1 else 0
            calmar_ratio = annual_return / self.max_drawdown
        else:
            calmar_ratio = float('inf') if len(balances) > 1 and balances[-1] > balances[0] else 0
        
        # Calculate win rate
        recent_trades = list(trades_collection.find({
            "timestamp": {"$gte": datetime.now() - timedelta(days=30)},
            "status": "CLOSED",
            "profit_loss": {"$exists": True}
        }))
        
        if recent_trades:
            winners = [t for t in recent_trades if t['profit_loss'] > 0]
            win_rate = len(winners) / len(recent_trades)
        else:
            win_rate = 0.5
        
        # Store metrics
        self.daily_metrics = {
            'sharpe_ratio': annualized_sharpe,
            'calmar_ratio': calmar_ratio,
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'win_rate': win_rate,
            'total_trades': len(recent_trades),
            'balance': balances[-1] if balances else 0
        }
    
    def _update_trade_quality(self):
        """Update trade quality scoring"""
        
        # Get recent trades
        recent_trades = list(trades_collection.find({
            "timestamp": {"$gte": datetime.now() - timedelta(days=7)},
            "status": "CLOSED"
        }).sort("timestamp", -1).limit(20))
        
        for trade in recent_trades:
            quality_score = self._calculate_trade_quality_score(trade)
            self.trade_quality_scores.append({
                'timestamp': trade.get('timestamp'),
                'market': trade.get('market'),
                'score': quality_score,
                'pnl': trade.get('profit_loss', 0)
            })
    
    def _calculate_trade_quality_score(self, trade: Dict) -> float:
        """
        Calculate trade quality score (0-1) based on:
        - Risk-reward ratio achieved
        - Time to profit/loss
        - Signal strength at entry
        - Market conditions
        """
        
        score = 0.5  # Base score
        
        # Factor 1: Risk-reward ratio
        entry_price = trade.get('entry_price', 0)
        stop_loss = trade.get('stop_loss', 0)
        profit_loss = trade.get('profit_loss', 0)
        
        if entry_price and stop_loss and entry_price != 0 and stop_loss != 0:
            risk_amount = abs(entry_price - stop_loss) * trade.get('size', 1)
            if risk_amount > 0 and profit_loss is not None:
                actual_rr = profit_loss / risk_amount
                if actual_rr > 1:
                    score += 0.2  # Good risk-reward
                elif actual_rr < -1:
                    score -= 0.3  # Poor risk management
        
        # Factor 2: Signal strength
        if trade.get('professional_risk'):
            score += 0.1  # Used professional risk management
            
        if trade.get('confidence', 0) > 0.7:
            score += 0.1  # High confidence signal
        elif trade.get('confidence', 0) < 0.5:
            score -= 0.1  # Low confidence signal
        
        # Factor 3: Execution quality
        execution_time = trade.get('execution_time', 0)
        if execution_time > 0 and execution_time < 2:  # Fast execution
            score += 0.1
        
        return max(0, min(1, score))
    
    def check_performance_alerts(self):
        """Check for performance alerts and warnings"""
        
        # Drawdown alerts
        if self.current_drawdown >= self.DRAWDOWN_CRITICAL:
            self._send_alert('CRITICAL_DRAWDOWN', 
                           f'Critical drawdown: {self.current_drawdown:.2%}', 
                           'critical')
        elif self.current_drawdown >= self.DRAWDOWN_WARNING:
            self._send_alert('DRAWDOWN_WARNING', 
                           f'Drawdown warning: {self.current_drawdown:.2%}', 
                           'warning')
        
        # Performance alerts
        if 'sharpe_ratio' in self.daily_metrics:
            sharpe = self.daily_metrics['sharpe_ratio']
            if sharpe is not None and sharpe < 0.5 and len(self.performance_history) > 100:
                self._send_alert('LOW_SHARPE', 
                               f'Low Sharpe ratio: {sharpe:.2f}', 
                               'warning')
        
        # Win rate alerts
        if 'win_rate' in self.daily_metrics:
            win_rate = self.daily_metrics['win_rate']
            if win_rate is not None and win_rate < self.MIN_WIN_RATE and self.daily_metrics.get('total_trades', 0) > 10:
                self._send_alert('LOW_WIN_RATE', 
                               f'Low win rate: {win_rate:.1%}', 
                               'warning')
        
        # Trade quality alerts
        if len(self.trade_quality_scores) >= 10:
            avg_quality = np.mean([s['score'] for s in self.trade_quality_scores])
            if avg_quality < 0.4:
                self._send_alert('POOR_TRADE_QUALITY', 
                               f'Poor trade quality: {avg_quality:.2f}/1.0', 
                               'warning')
    
    def _send_alert(self, alert_type: str, message: str, severity: str):
        """Send performance alert"""
        
        # Rate limiting - don't send same alert more than once per hour
        now = datetime.now()
        if alert_type in self.last_alert_time:
            if now - self.last_alert_time[alert_type] < timedelta(hours=1):
                return
        
        self.last_alert_time[alert_type] = now
        
        # Format alert
        alert = f"🚨 TRADING ALERT [{severity.upper()}] 🚨\n"
        alert += f"Type: {alert_type}\n"
        alert += f"Message: {message}\n"
        alert += f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if severity == 'critical':
            alert += "\n⚠️ IMMEDIATE ACTION MAY BE REQUIRED ⚠️"
        
        print(alert)
        
        # TODO: Add email/SMS notification here
        # self._send_email_alert(alert)
        # self._send_sms_alert(alert)
    
    def generate_hourly_report(self):
        """Generate hourly performance report"""
        
        current_time = datetime.now()
        
        # Get emergency risk manager status
        try:
            risk_manager = get_emergency_risk_manager()
            risk_status = risk_manager.get_risk_status()
        except:
            risk_status = {}
        
        print(f"\n📊 HOURLY PERFORMANCE REPORT ({current_time.strftime('%H:%M')})")
        print("=" * 60)
        
        # Account status
        current_balance = get_account_balance()
        print(f"💰 Account Balance: £{current_balance:.2f}")
        print(f"📈 Peak Balance: £{self.peak_balance:.2f}")
        print(f"📉 Current Drawdown: {self.current_drawdown:.2%}")
        print(f"📉 Max Drawdown: {self.max_drawdown:.2%}")
        
        # Risk management status
        print(f"\n🛡️ Risk Management:")
        print(f"   Trading Status: {'✅ ACTIVE' if not risk_status.get('trading_halted') else '❌ HALTED'}")
        if risk_status.get('trading_halted'):
            print(f"   Halt Reason: {risk_status.get('halt_reason')}")
        print(f"   Daily P&L: £{risk_status.get('daily_pnl', 0):.2f}")
        print(f"   Open Positions: {risk_status.get('active_positions', 0)}")
        print(f"   Consecutive Losses: {risk_status.get('consecutive_losses', 0)}")
        
        # Performance metrics
        if 'sharpe_ratio' in self.daily_metrics:
            print(f"\n📊 Performance Metrics:")
            print(f"   Sharpe Ratio: {self.daily_metrics['sharpe_ratio']:.2f}")
            print(f"   Calmar Ratio: {self.daily_metrics['calmar_ratio']:.2f}")
            print(f"   Win Rate: {self.daily_metrics['win_rate']:.1%}")
            print(f"   Total Trades: {self.daily_metrics['total_trades']}")
        
        # Trade quality
        if self.trade_quality_scores:
            avg_quality = np.mean([s['score'] for s in self.trade_quality_scores[-10:]])
            print(f"\n⭐ Trade Quality:")
            print(f"   Average Score: {avg_quality:.2f}/1.0")
            print(f"   Recent Trades: {len(self.trade_quality_scores)}")
        
        print("=" * 60)
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        
        current_balance = get_account_balance()
        
        # Calculate returns
        if len(self.performance_history) > 1:
            initial_balance = self.performance_history[0]['balance']
            if initial_balance is not None and initial_balance > 0:
                total_return = (current_balance - initial_balance) / initial_balance
            else:
                total_return = 0
        else:
            total_return = 0
        
        # Get recent trade statistics
        recent_trades = list(trades_collection.find({
            "timestamp": {"$gte": datetime.now() - timedelta(days=30)},
            "status": "CLOSED"
        }))
        
        winners = [t for t in recent_trades if t.get('profit_loss') is not None and t.get('profit_loss', 0) > 0]
        losers = [t for t in recent_trades if t.get('profit_loss') is not None and t.get('profit_loss', 0) < 0]
        
        return {
            'account_balance': current_balance,
            'peak_balance': self.peak_balance,
            'total_return': total_return,
            'max_drawdown': self.max_drawdown,
            'current_drawdown': self.current_drawdown,
            'sharpe_ratio': self.daily_metrics.get('sharpe_ratio', 0),
            'calmar_ratio': self.daily_metrics.get('calmar_ratio', 0),
            'win_rate': len(winners) / len(recent_trades) if recent_trades else 0,
            'total_trades': len(recent_trades),
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'avg_win': np.mean([t['profit_loss'] for t in winners if t.get('profit_loss') is not None]) if winners else 0,
            'avg_loss': np.mean([t['profit_loss'] for t in losers if t.get('profit_loss') is not None]) if losers else 0,
            'avg_trade_quality': np.mean([s['score'] for s in self.trade_quality_scores]) if self.trade_quality_scores else 0.5,
            'monitoring_active': self.monitoring_active
        }

# Global instance
_professional_monitor = None

def get_professional_monitor() -> ProfessionalTradingMonitor:
    """Get global professional trading monitor instance"""
    global _professional_monitor
    if _professional_monitor is None:
        _professional_monitor = ProfessionalTradingMonitor()
    return _professional_monitor

if __name__ == "__main__":
    # Test the professional monitor
    print("🧪 Testing Professional Trading Monitor")
    print("=" * 50)
    
    monitor = ProfessionalTradingMonitor()
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    
    print(f"Performance Summary:")
    for key, value in summary.items():
        if isinstance(value, float):
            if 'ratio' in key or 'return' in key:
                print(f"   {key}: {value:.2f}")
            elif 'rate' in key:
                print(f"   {key}: {value:.1%}")
            else:
                print(f"   {key}: £{value:.2f}" if 'balance' in key else f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    
    # Test alert system
    monitor._send_alert('TEST_ALERT', 'This is a test alert', 'info')