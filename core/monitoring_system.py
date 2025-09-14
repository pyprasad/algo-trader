# core/monitoring_system.py

import json
import time
import smtplib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
import yaml
import os

@dataclass
class PerformanceMetrics:
    """Performance metrics for autonomous trading monitoring"""
    timestamp: datetime
    balance: float
    daily_pnl: float
    total_pnl: float
    open_positions: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    trades_today: int
    avg_trade_duration: float
    current_strategy: str
    market_regime: str
    volatility_level: str
    risk_score: float
    confidence_level: float

@dataclass
class Alert:
    """Alert notification for autonomous trading"""
    timestamp: datetime
    level: str  # INFO, WARNING, CRITICAL, EMERGENCY
    category: str  # PERFORMANCE, RISK, SYSTEM, TRADE, LEARNING
    message: str
    data: Dict[str, Any]
    action_required: bool = False
    acknowledged: bool = False

class AutonomousMonitoringSystem:
    """
    Real-time monitoring and alerting system for autonomous trading
    
    Features:
    - Real-time performance tracking with ML confidence scoring
    - Advanced risk monitoring with emergency shutdown
    - System health checks and adaptive learning monitoring
    - Multi-channel alerting (console, file, email)
    - Performance benchmarking and optimization tracking
    - Emergency response procedures
    """
    
    def __init__(self, config_path: str = 'configs/monitoring_config.yaml'):
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            # Default configuration if file doesn't exist
            self.config = self._get_default_config()
        
        # Initialize logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.metrics_history: List[PerformanceMetrics] = []
        self.alerts: List[Alert] = []
        self.last_health_check = datetime.now()
        self.system_status = "HEALTHY"
        self.emergency_triggered = False
        
        # Performance tracking
        self.trade_history = []
        self.daily_stats = {}
        self.benchmark_metrics = {}
        
        # Alert configuration
        self.alert_config = self.config.get('alerts', {})
        
        # Email configuration
        self.email_config = self.config.get('email', {})
        
        # Performance benchmarks
        self.benchmarks = self.config.get('benchmarks', {})
        
        self.logger.info("🔍 Autonomous Trading Monitoring System Initialized")
        self.logger.info(f"   Alert Thresholds: {len(self.alert_config)} configured")
        self.logger.info(f"   Email Alerts: {'Enabled' if self.email_config.get('enabled') else 'Disabled'}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('logging', {}).get('level', 'INFO'))
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/autonomous_monitoring.log'),
                logging.StreamHandler()
            ]
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Default monitoring configuration"""
        return {
            'alerts': {
                'max_daily_loss': 500,
                'max_drawdown': 15.0,
                'min_balance': 8000,
                'max_positions': 3,
                'max_daily_trades': 12,
                'min_win_rate': 35.0,
                'min_confidence': 0.6,
                'max_risk_score': 0.8
            },
            'email': {'enabled': False},
            'benchmarks': {
                'target_daily_return': 2.0,
                'target_win_rate': 55.0,
                'target_profit_factor': 1.8,
                'max_acceptable_drawdown': 10.0
            },
            'logging': {'level': 'INFO'}
        }
    
    def update_metrics(self, trading_data: Dict[str, Any]):
        """Update performance metrics with latest trading data"""
        
        try:
            # Calculate current metrics
            metrics = self._calculate_metrics(trading_data)
            self.metrics_history.append(metrics)
            
            # Keep only recent metrics (configurable retention)
            retention_hours = self.config.get('monitoring', {}).get('metrics_retention_hours', 168)
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            self.metrics_history = [m for m in self.metrics_history 
                                  if m.timestamp > cutoff_time]
            
            # Check for alerts
            self._check_performance_alerts(metrics)
            self._check_risk_alerts(metrics)
            self._check_learning_alerts(metrics, trading_data)
            
            # Update system status
            self._update_system_status(metrics)
            
            # Log metrics with more detail
            self.logger.info(
                f"📊 Metrics - Balance: £{metrics.balance:.2f} | "
                f"P&L: £{metrics.daily_pnl:+.2f} | "
                f"Positions: {metrics.open_positions} | "
                f"Strategy: {metrics.current_strategy} | "
                f"Confidence: {metrics.confidence_level:.1%} | "
                f"Risk: {metrics.risk_score:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error updating metrics: {e}")
            self._create_alert("CRITICAL", "SYSTEM", f"Metrics update failed: {e}", 
                             action_required=True)
    
    def _calculate_metrics(self, data: Dict[str, Any]) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        balance = data.get('balance', 10000)
        positions = data.get('positions', {})
        trades = data.get('trades', [])
        
        # Store trades for history
        self.trade_history.extend(trades)
        
        # Calculate daily P&L
        today = datetime.now().date()
        daily_trades = [t for t in trades if t.get('timestamp', datetime.now()).date() == today]
        daily_pnl = sum(t.get('pnl', 0) for t in daily_trades)
        
        # Calculate total P&L
        total_pnl = sum(t.get('pnl', 0) for t in self.trade_history)
        
        # Win rate calculation
        if self.trade_history:
            winning_trades = [t for t in self.trade_history if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(self.trade_history) * 100
        else:
            win_rate = 0
        
        # Profit factor
        total_wins = sum(t.get('pnl', 0) for t in self.trade_history if t.get('pnl', 0) > 0)
        total_losses = abs(sum(t.get('pnl', 0) for t in self.trade_history if t.get('pnl', 0) < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Drawdown calculation
        if self.trade_history:
            equity_curve = []
            running_balance = 10000  # Starting balance
            for trade in sorted(self.trade_history, key=lambda x: x.get('timestamp', datetime.min)):
                running_balance += trade.get('pnl', 0)
                equity_curve.append(running_balance)
            
            if equity_curve:
                peak = equity_curve[0]
                max_drawdown = 0
                for value in equity_curve:
                    if value > peak:
                        peak = value
                    if peak > 0:
                        drawdown = (peak - value) / peak * 100
                        max_drawdown = max(max_drawdown, drawdown)
        else:
            max_drawdown = 0
        
        # Sharpe ratio (simplified)
        if len(self.trade_history) > 10:
            returns = [t.get('pnl', 0) for t in self.trade_history]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Average trade duration
        durations = [t.get('duration', 0) for t in self.trade_history if 'duration' in t]
        avg_duration = np.mean(durations) if durations else 0
        
        # Risk score calculation (0-1, higher = more risky)
        risk_score = self._calculate_risk_score(data, max_drawdown, len(positions))
        
        # Confidence level from ML system
        confidence_level = data.get('confidence_level', 0.5)
        
        return PerformanceMetrics(
            timestamp=datetime.now(),
            balance=balance,
            daily_pnl=daily_pnl,
            total_pnl=total_pnl,
            open_positions=len(positions),
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades_today=len(daily_trades),
            avg_trade_duration=avg_duration,
            current_strategy=data.get('current_strategy', 'Unknown'),
            market_regime=data.get('market_regime', 'Unknown'),
            volatility_level=data.get('volatility_level', 'Normal'),
            risk_score=risk_score,
            confidence_level=confidence_level
        )
    
    def _calculate_risk_score(self, data: Dict[str, Any], drawdown: float, positions: int) -> float:
        """Calculate current risk score (0-1)"""
        
        risk_factors = []
        
        # Drawdown risk
        max_acceptable_dd = self.benchmarks.get('max_acceptable_drawdown', 10.0)
        risk_factors.append(min(drawdown / max_acceptable_dd, 1.0))
        
        # Position concentration risk
        max_positions = self.alert_config.get('max_positions', 3)
        risk_factors.append(positions / max_positions)
        
        # Volatility risk
        vol_level = data.get('volatility_level', 'Normal')
        vol_risk = {'Low': 0.2, 'Normal': 0.5, 'High': 0.8, 'Extreme': 1.0}.get(vol_level, 0.5)
        risk_factors.append(vol_risk)
        
        # Confidence risk (inverse)
        confidence = data.get('confidence_level', 0.5)
        risk_factors.append(1.0 - confidence)
        
        return np.mean(risk_factors)
    
    def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance-related alerts"""
        
        # Daily loss limit
        max_daily_loss = self.alert_config.get('max_daily_loss', 500)
        if metrics.daily_pnl <= -max_daily_loss:
            self._create_alert("EMERGENCY", "RISK", 
                             f"EMERGENCY: Daily loss limit exceeded: £{metrics.daily_pnl:.2f}",
                             {'limit': max_daily_loss, 'actual': metrics.daily_pnl},
                             action_required=True)
        
        # Low win rate with sufficient trades
        min_win_rate = self.alert_config.get('min_win_rate', 35)
        if metrics.win_rate < min_win_rate and len(self.trade_history) > 20:
            self._create_alert("WARNING", "PERFORMANCE", 
                             f"Win rate below threshold: {metrics.win_rate:.1f}% (target: {min_win_rate}%)",
                             {'win_rate': metrics.win_rate, 'threshold': min_win_rate})
        
        # High drawdown
        max_drawdown_threshold = self.alert_config.get('max_drawdown', 15)
        if metrics.max_drawdown > max_drawdown_threshold:
            self._create_alert("CRITICAL", "RISK", 
                             f"Maximum drawdown exceeded: {metrics.max_drawdown:.1f}% (limit: {max_drawdown_threshold}%)",
                             {'drawdown': metrics.max_drawdown, 'limit': max_drawdown_threshold},
                             action_required=True)
        
        # Balance threshold
        min_balance = self.alert_config.get('min_balance', 8000)
        if metrics.balance < min_balance:
            self._create_alert("CRITICAL", "RISK", 
                             f"Balance below critical threshold: £{metrics.balance:.2f}",
                             {'balance': metrics.balance, 'threshold': min_balance})
        
        # Poor profit factor
        min_profit_factor = self.alert_config.get('min_profit_factor', 0.8)
        if metrics.profit_factor < min_profit_factor and len(self.trade_history) > 10:
            self._create_alert("WARNING", "PERFORMANCE",
                             f"Profit factor below target: {metrics.profit_factor:.2f}",
                             {'profit_factor': metrics.profit_factor, 'target': min_profit_factor})
    
    def _check_risk_alerts(self, metrics: PerformanceMetrics):
        """Check for risk-related alerts"""
        
        # Too many positions
        max_positions = self.alert_config.get('max_positions', 3)
        if metrics.open_positions > max_positions:
            self._create_alert("WARNING", "RISK", 
                             f"Too many open positions: {metrics.open_positions}/{max_positions}")
        
        # Too many trades in a day
        max_daily_trades = self.alert_config.get('max_daily_trades', 12)
        if metrics.trades_today > max_daily_trades:
            self._create_alert("WARNING", "RISK", 
                             f"Daily trade limit approaching: {metrics.trades_today}/{max_daily_trades}")
        
        # High risk score
        max_risk_score = self.alert_config.get('max_risk_score', 0.8)
        if metrics.risk_score > max_risk_score:
            self._create_alert("CRITICAL", "RISK",
                             f"Risk score elevated: {metrics.risk_score:.2f} (limit: {max_risk_score})",
                             {'risk_score': metrics.risk_score, 'limit': max_risk_score})
        
        # Rapid trading detection
        if len(self.metrics_history) >= 2:
            recent_trades = metrics.trades_today - self.metrics_history[-2].trades_today
            if recent_trades > 3:  # More than 3 trades in update interval
                self._create_alert("WARNING", "RISK", 
                                 f"Rapid trading detected: {recent_trades} trades in short period")
    
    def _check_learning_alerts(self, metrics: PerformanceMetrics, data: Dict[str, Any]):
        """Check for adaptive learning system alerts"""
        
        # Low ML confidence
        min_confidence = self.alert_config.get('min_confidence', 0.6)
        if metrics.confidence_level < min_confidence:
            self._create_alert("WARNING", "LEARNING",
                             f"ML confidence below threshold: {metrics.confidence_level:.1%}")
        
        # Strategy adaptation alerts
        if 'strategy_changed' in data and data['strategy_changed']:
            self._create_alert("INFO", "LEARNING",
                             f"Strategy adapted: {data.get('old_strategy')} → {metrics.current_strategy}")
        
        # Market regime change
        if 'regime_changed' in data and data['regime_changed']:
            self._create_alert("INFO", "LEARNING",
                             f"Market regime detected: {metrics.market_regime}")
    
    def _create_alert(self, level: str, category: str, message: str, 
                     data: Dict = None, action_required: bool = False):
        """Create and process alert"""
        
        alert = Alert(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            data=data or {},
            action_required=action_required
        )
        
        self.alerts.append(alert)
        
        # Log alert with appropriate level
        log_func = {
            'INFO': self.logger.info,
            'WARNING': self.logger.warning,
            'CRITICAL': self.logger.error,
            'EMERGENCY': self.logger.critical
        }.get(level, self.logger.warning)
        
        log_func(f"🚨 {level} ALERT [{category}]: {message}")
        
        # Send notification for critical/emergency alerts
        if level in ["CRITICAL", "EMERGENCY"]:
            self._send_notification(alert)
        
        # Trigger emergency shutdown for emergency alerts
        if level == "EMERGENCY":
            self._trigger_emergency_response(alert)
    
    def _send_notification(self, alert: Alert):
        """Send alert notification via configured channels"""
        
        try:
            # Email notification
            if self.email_config.get('enabled', False):
                self._send_email_alert(alert)
            
            # Console notification (always active for critical alerts)
            print(f"\n{'='*80}")
            print(f"🚨 {alert.level} ALERT - {alert.category}")
            print(f"{'='*80}")
            print(f"Time: {alert.timestamp}")
            print(f"Message: {alert.message}")
            if alert.data:
                print(f"Data: {json.dumps(alert.data, indent=2)}")
            if alert.action_required:
                print("⚠️  IMMEDIATE ACTION REQUIRED")
            print(f"{'='*80}\n")
            
            # Future: Add webhook, SMS, Slack notifications here
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send notification: {e}")
    
    def _send_email_alert(self, alert: Alert):
        """Send email alert notification"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = f"🚨 Autonomous Trading Alert - {alert.level}"
            
            body = f"""
            Autonomous Trading System Alert
            
            Level: {alert.level}
            Category: {alert.category}
            Time: {alert.timestamp}
            Action Required: {'YES' if alert.action_required else 'NO'}
            
            Message: {alert.message}
            
            System Data:
            {json.dumps(alert.data, indent=2)}
            
            System Status: {self.system_status}
            Active Positions: {self.metrics_history[-1].open_positions if self.metrics_history else 'N/A'}
            Current Balance: £{self.metrics_history[-1].balance:.2f if self.metrics_history else 'N/A'}
            
            Please check your autonomous trading system immediately.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            text = msg.as_string()
            server.sendmail(self.email_config['from_email'], self.email_config['to_email'], text)
            server.quit()
            
            self.logger.info("📧 Email alert sent successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to send email: {e}")
    
    def _trigger_emergency_response(self, alert: Alert):
        """Trigger emergency response procedures"""
        
        self.logger.critical(f"🚨 EMERGENCY RESPONSE TRIGGERED: {alert.message}")
        
        # Set emergency status
        self.system_status = "EMERGENCY_SHUTDOWN"
        self.emergency_triggered = True
        
        # Create emergency log
        emergency_log = {
            'timestamp': datetime.now().isoformat(),
            'alert': asdict(alert),
            'system_status': self.system_status,
            'last_metrics': asdict(self.metrics_history[-1]) if self.metrics_history else None,
            'emergency_procedures': [
                'System set to emergency shutdown mode',
                'All new trades blocked',
                'Existing positions flagged for review',
                'Notifications sent to all channels',
                'Manual intervention required'
            ]
        }
        
        # Write emergency log
        with open('logs/emergency_response.log', 'a') as f:
            f.write(json.dumps(emergency_log, indent=2) + '\n')
        
        # Emergency notification
        print(f"\n{'🚨' * 40}")
        print("EMERGENCY SHUTDOWN ACTIVATED")
        print(f"Reason: {alert.message}")
        print("All trading operations suspended")
        print("Manual intervention required")
        print(f"{'🚨' * 40}\n")
    
    def _update_system_status(self, metrics: PerformanceMetrics):
        """Update overall system status based on current conditions"""
        
        if self.emergency_triggered:
            return  # Keep emergency status
        
        # Check various health indicators
        critical_alerts = [a for a in self.alerts[-10:] if a.level == "CRITICAL" and not a.acknowledged]
        
        if critical_alerts:
            self.system_status = "DEGRADED"
        elif metrics.risk_score > 0.7:
            self.system_status = "HIGH_RISK"
        elif metrics.confidence_level < 0.3:
            self.system_status = "LOW_CONFIDENCE"
        else:
            self.system_status = "HEALTHY"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        recent_metrics = self.metrics_history[-1] if self.metrics_history else None
        
        return {
            'system_status': self.system_status,
            'emergency_triggered': self.emergency_triggered,
            'last_update': self.last_health_check.isoformat(),
            'active_alerts': len([a for a in self.alerts if not a.acknowledged]),
            'critical_alerts': len([a for a in self.alerts if a.level in ["CRITICAL", "EMERGENCY"] and not a.acknowledged]),
            'recent_metrics': asdict(recent_metrics) if recent_metrics else None,
            'uptime_hours': (datetime.now() - self.last_health_check).total_seconds() / 3600,
            'total_trades': len(self.trade_history),
            'monitoring_health': 'ACTIVE'
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent = self.metrics_history[-1]
        
        # Calculate trends
        trend_data = {}
        if len(self.metrics_history) >= 24:  # Last 24 updates
            trend_start = self.metrics_history[-24]
            trend_data = {
                'balance_change_24h': recent.balance - trend_start.balance,
                'pnl_change_24h': recent.total_pnl - trend_start.total_pnl,
                'win_rate_trend': recent.win_rate - trend_start.win_rate,
                'confidence_trend': recent.confidence_level - trend_start.confidence_level
            }
        
        # Benchmark comparison
        benchmark_comparison = {}
        benchmarks = self.benchmarks
        if benchmarks:
            benchmark_comparison = {
                'daily_return_vs_target': (recent.daily_pnl / 10000 * 100) - benchmarks.get('target_daily_return', 2.0),
                'win_rate_vs_target': recent.win_rate - benchmarks.get('target_win_rate', 55.0),
                'profit_factor_vs_target': recent.profit_factor - benchmarks.get('target_profit_factor', 1.8)
            }
        
        return {
            'current_performance': asdict(recent),
            'trends': trend_data,
            'benchmark_comparison': benchmark_comparison,
            'alerts_summary': {
                'total_alerts': len(self.alerts),
                'critical_alerts': len([a for a in self.alerts if a.level == "CRITICAL"]),
                'emergency_alerts': len([a for a in self.alerts if a.level == "EMERGENCY"]),
                'unacknowledged': len([a for a in self.alerts if not a.acknowledged])
            },
            'system_health': {
                'status': self.system_status,
                'emergency_mode': self.emergency_triggered,
                'last_check': self.last_health_check.isoformat(),
                'uptime': (datetime.now() - self.last_health_check).total_seconds() / 3600
            },
            'risk_assessment': {
                'current_risk_score': recent.risk_score,
                'risk_level': 'HIGH' if recent.risk_score > 0.7 else 'MEDIUM' if recent.risk_score > 0.4 else 'LOW',
                'confidence_level': recent.confidence_level,
                'recommendation': self._get_risk_recommendation(recent)
            }
        }
    
    def _get_risk_recommendation(self, metrics: PerformanceMetrics) -> str:
        """Get risk-based recommendation"""
        
        if metrics.risk_score > 0.8:
            return "REDUCE POSITION SIZE - High risk detected"
        elif metrics.risk_score > 0.6:
            return "MONITOR CLOSELY - Elevated risk"
        elif metrics.confidence_level < 0.4:
            return "LOW CONFIDENCE - Consider strategy review"
        elif metrics.win_rate < 30 and len(self.trade_history) > 20:
            return "POOR PERFORMANCE - Strategy optimization needed"
        else:
            return "NORMAL OPERATIONS - Continue monitoring"
    
    def acknowledge_alert(self, alert_index: int) -> bool:
        """Acknowledge an alert"""
        if 0 <= alert_index < len(self.alerts):
            self.alerts[alert_index].acknowledged = True
            self.logger.info(f"✅ Alert {alert_index} acknowledged: {self.alerts[alert_index].message}")
            return True
        return False
    
    def reset_emergency_status(self) -> bool:
        """Reset emergency status after manual intervention"""
        if self.system_status == "EMERGENCY_SHUTDOWN":
            self.system_status = "HEALTHY"
            self.emergency_triggered = False
            self.logger.warning("🔄 Emergency status reset - System returned to HEALTHY")
            
            # Log emergency reset
            with open('logs/emergency_response.log', 'a') as f:
                f.write(json.dumps({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'EMERGENCY_RESET',
                    'operator': 'MANUAL',
                    'new_status': self.system_status
                }) + '\n')
            
            return True
        return False
    
    def export_metrics(self, filename: str):
        """Export metrics history to CSV for analysis"""
        if self.metrics_history:
            df = pd.DataFrame([asdict(m) for m in self.metrics_history])
            df.to_csv(filename, index=False)
            self.logger.info(f"📁 Metrics exported to {filename}")
        else:
            self.logger.warning("No metrics available for export")
    
    def get_emergency_procedures(self) -> Dict[str, Any]:
        """Get emergency response procedures and status"""
        
        return {
            'emergency_active': self.emergency_triggered,
            'procedures': [
                "1. Stop all new trade execution",
                "2. Close risky positions if safe to do so",
                "3. Notify system administrator immediately",
                "4. Review system logs and alerts",
                "5. Determine root cause of emergency",
                "6. Implement corrective measures",
                "7. Reset emergency status only after verification"
            ],
            'contact_info': {
                'primary': "System Administrator",
                'emergency': "Risk Management Team"
            },
            'logs_location': "logs/emergency_response.log",
            'reset_procedure': "Call reset_emergency_status() after manual verification"
        }

class AutonomousDashboard:
    """
    Real-time dashboard for autonomous trading monitoring
    """
    
    def __init__(self, monitoring_system: AutonomousMonitoringSystem):
        self.monitor = monitoring_system
    
    def display_real_time_dashboard(self):
        """Display comprehensive real-time dashboard"""
        
        status = self.monitor.get_system_status()
        report = self.monitor.get_performance_report()
        
        print("\n" + "="*100)
        print("🤖 AUTONOMOUS TRADING SYSTEM - REAL-TIME DASHBOARD")
        print("="*100)
        
        # System Status
        status_icon = "🚨" if status['emergency_triggered'] else "🟢" if status['system_status'] == "HEALTHY" else "🟡"
        print(f"{status_icon} SYSTEM STATUS: {status['system_status']}")
        if status['emergency_triggered']:
            print("   ⚠️  EMERGENCY MODE ACTIVE - Manual intervention required")
        print()
        
        if 'current_performance' in report:
            perf = report['current_performance']
            
            # Performance Section
            print(f"💰 PERFORMANCE METRICS:")
            print(f"   Balance: £{perf['balance']:,.2f}")
            pnl_color = "+" if perf['daily_pnl'] >= 0 else ""
            print(f"   Daily P&L: £{pnl_color}{perf['daily_pnl']:,.2f}")
            total_color = "+" if perf['total_pnl'] >= 0 else ""
            print(f"   Total P&L: £{total_color}{perf['total_pnl']:,.2f}")
            print(f"   Win Rate: {perf['win_rate']:.1f}%")
            print(f"   Profit Factor: {perf['profit_factor']:.2f}")
            print(f"   Max Drawdown: {perf['max_drawdown']:.1f}%")
            print()
            
            # Risk Assessment
            risk_info = report.get('risk_assessment', {})
            risk_level = risk_info.get('risk_level', 'UNKNOWN')
            risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(risk_level, "❓")
            print(f"⚖️  RISK ASSESSMENT:")
            print(f"   Risk Level: {risk_icon} {risk_level}")
            print(f"   Risk Score: {perf['risk_score']:.2f}/1.0")
            print(f"   Confidence: {perf['confidence_level']:.1%}")
            print(f"   Recommendation: {risk_info.get('recommendation', 'N/A')}")
            print()
            
            # Trading Activity
            print(f"📈 TRADING ACTIVITY:")
            print(f"   Open Positions: {perf['open_positions']}")
            print(f"   Trades Today: {perf['trades_today']}")
            print(f"   Current Strategy: {perf['current_strategy']}")
            print(f"   Market Regime: {perf['market_regime']}")
            print(f"   Volatility: {perf['volatility_level']}")
            print()
            
            # Benchmark Comparison
            if 'benchmark_comparison' in report and report['benchmark_comparison']:
                bench = report['benchmark_comparison']
                print(f"🎯 BENCHMARK PERFORMANCE:")
                for metric, value in bench.items():
                    status_symbol = "✅" if value >= 0 else "❌"
                    print(f"   {status_symbol} {metric.replace('_', ' ').title()}: {value:+.2f}")
                print()
            
            # Trends (if available)
            if 'trends' in report and report['trends']:
                trends = report['trends']
                print(f"📊 24-HOUR TRENDS:")
                for trend, value in trends.items():
                    if 'change' in trend:
                        print(f"   {trend.replace('_', ' ').title()}: £{value:+.2f}")
                    else:
                        print(f"   {trend.replace('_', ' ').title()}: {value:+.2f}")
                print()
        
        # Alerts Section
        alerts_summary = report.get('alerts_summary', {})
        total_alerts = alerts_summary.get('total_alerts', 0)
        critical_alerts = alerts_summary.get('critical_alerts', 0)
        emergency_alerts = alerts_summary.get('emergency_alerts', 0)
        
        print(f"🚨 ALERTS SUMMARY:")
        print(f"   Total Alerts: {total_alerts}")
        if emergency_alerts > 0:
            print(f"   🚨 Emergency: {emergency_alerts}")
        if critical_alerts > 0:
            print(f"   ⚠️  Critical: {critical_alerts}")
        print(f"   Unacknowledged: {alerts_summary.get('unacknowledged', 0)}")
        
        # Recent Alerts
        recent_alerts = [a for a in self.monitor.alerts[-5:] if not a.acknowledged]
        if recent_alerts:
            print(f"\n   Recent Alerts:")
            for alert in recent_alerts[-3:]:  # Show last 3
                icon = {"INFO": "ℹ️", "WARNING": "⚠️", "CRITICAL": "🚨", "EMERGENCY": "🆘"}.get(alert.level, "❓")
                print(f"   {icon} {alert.level}: {alert.message}")
        print()
        
        print("="*100)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
              f"Uptime: {status['uptime_hours']:.1f}h")
        print("="*100)
    
    def generate_performance_summary(self) -> str:
        """Generate concise performance summary"""
        
        report = self.monitor.get_performance_report()
        if 'error' in report:
            return "⚠️ No performance data available"
        
        perf = report['current_performance']
        status = self.monitor.get_system_status()
        
        summary = f"""
🤖 Autonomous Trading Summary
Status: {status['system_status']} | Balance: £{perf['balance']:,.2f} | P&L: £{perf['total_pnl']:+.2f}
Win Rate: {perf['win_rate']:.1f}% | Risk: {perf['risk_score']:.2f} | Confidence: {perf['confidence_level']:.1%}
Strategy: {perf['current_strategy']} | Positions: {perf['open_positions']} | Trades Today: {perf['trades_today']}
        """.strip()
        
        return summary