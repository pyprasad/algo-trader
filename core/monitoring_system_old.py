# core/monitoring_system.py

"""
📊 Comprehensive Monitoring and Alerting System

Provides real-time monitoring, alerting, and health checks for the margin system
with support for multiple alert channels and customizable thresholds.

Key Features:
- Real-time metric collection and aggregation
- Multi-channel alert delivery (email, webhook, log)
- Health check endpoints
- Performance metrics tracking
- Alert suppression and throttling
- Dashboard data generation

Author: Operations Team
"""

import time
import threading
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import statistics
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics to monitor"""
    GAUGE = "gauge"          # Point-in-time value
    COUNTER = "counter"      # Cumulative count
    HISTOGRAM = "histogram"  # Distribution of values
    RATE = "rate"           # Rate of change

class AlertPriority(Enum):
    """Alert priority levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertChannel(Enum):
    """Alert delivery channels"""
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"
    SLACK = "slack"

@dataclass
class Metric:
    """Container for metric data"""
    name: str
    type: MetricType
    value: Union[float, int]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None

@dataclass
class Alert:
    """Container for alert information"""
    id: str
    name: str
    priority: AlertPriority
    message: str
    timestamp: datetime
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    channels: List[AlertChannel] = field(default_factory=list)
    suppressed: bool = False

@dataclass
class HealthCheck:
    """Health check result"""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

class MetricCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, retention_minutes: int = 60):
        """
        Initialize metric collector
        
        Args:
            retention_minutes: How long to retain metrics
        """
        self.retention_minutes = retention_minutes
        self.metrics = defaultdict(lambda: deque(maxlen=retention_minutes * 60))  # 1 per second
        self.counters = defaultdict(int)
        self.gauges = {}
        self.histograms = defaultdict(list)
        self.lock = threading.Lock()
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record gauge metric"""
        with self.lock:
            metric = Metric(name, MetricType.GAUGE, value, datetime.now(), tags or {})
            self.metrics[name].append(metric)
            self.gauges[name] = value
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment counter metric"""
        with self.lock:
            self.counters[name] += value
            metric = Metric(name, MetricType.COUNTER, self.counters[name], datetime.now(), tags or {})
            self.metrics[name].append(metric)
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record histogram metric"""
        with self.lock:
            self.histograms[name].append(value)
            # Keep only recent values
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]
            
            metric = Metric(name, MetricType.HISTOGRAM, value, datetime.now(), tags or {})
            self.metrics[name].append(metric)
    
    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value"""
        return self.gauges.get(name)
    
    def get_counter(self, name: str) -> int:
        """Get counter value"""
        return self.counters.get(name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics"""
        values = self.histograms.get(name, [])
        if not values:
            return {}
        
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": statistics.quantiles(values, n=20)[18] if len(values) > 20 else max(values),
            "p99": statistics.quantiles(values, n=100)[98] if len(values) > 100 else max(values)
        }
    
    def get_rate(self, name: str, window_seconds: int = 60) -> float:
        """Calculate rate of change"""
        with self.lock:
            metrics = list(self.metrics.get(name, []))
            if len(metrics) < 2:
                return 0.0
            
            cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
            recent_metrics = [m for m in metrics if m.timestamp > cutoff_time]
            
            if len(recent_metrics) < 2:
                return 0.0
            
            time_diff = (recent_metrics[-1].timestamp - recent_metrics[0].timestamp).total_seconds()
            if time_diff == 0:
                return 0.0
            
            value_diff = recent_metrics[-1].value - recent_metrics[0].value
            return value_diff / time_diff

class AlertManager:
    """Manages alert generation and delivery"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.alert_rules = []
        self.alert_history = deque(maxlen=1000)
        self.alert_suppression = {}  # alert_name -> suppression_end_time
        self.alert_channels = {}
        self.lock = threading.Lock()
        
        # Alert throttling
        self.alert_counts = defaultdict(list)  # alert_name -> list of timestamps
        self.max_alerts_per_minute = 5
    
    def add_rule(self, name: str, condition: Callable[[], bool], 
                 priority: AlertPriority, message: str,
                 channels: List[AlertChannel], suppress_minutes: int = 5):
        """
        Add alert rule
        
        Args:
            name: Alert name
            condition: Function that returns True when alert should fire
            priority: Alert priority
            message: Alert message
            channels: Delivery channels
            suppress_minutes: Minutes to suppress repeat alerts
        """
        self.alert_rules.append({
            "name": name,
            "condition": condition,
            "priority": priority,
            "message": message,
            "channels": channels,
            "suppress_minutes": suppress_minutes
        })
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert rules"""
        for rule in self.alert_rules:
            try:
                if rule["condition"](metrics):
                    self._trigger_alert(rule, metrics)
            except Exception as e:
                logger.error(f"Error checking alert rule {rule['name']}: {e}")
    
    def _trigger_alert(self, rule: Dict[str, Any], metrics: Dict[str, Any]):
        """Trigger an alert"""
        with self.lock:
            # Check suppression
            if self._is_suppressed(rule["name"]):
                return
            
            # Check throttling
            if not self._check_throttle(rule["name"]):
                return
            
            # Create alert
            alert = Alert(
                id=f"ALERT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{rule['name']}",
                name=rule["name"],
                priority=rule["priority"],
                message=rule["message"],
                timestamp=datetime.now(),
                channels=rule["channels"]
            )
            
            # Store in history
            self.alert_history.append(alert)
            
            # Send alert
            self._send_alert(alert)
            
            # Set suppression
            self.alert_suppression[rule["name"]] = datetime.now() + timedelta(minutes=rule["suppress_minutes"])
    
    def _is_suppressed(self, alert_name: str) -> bool:
        """Check if alert is suppressed"""
        if alert_name in self.alert_suppression:
            if datetime.now() < self.alert_suppression[alert_name]:
                return True
            else:
                del self.alert_suppression[alert_name]
        return False
    
    def _check_throttle(self, alert_name: str) -> bool:
        """Check alert throttling"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Clean old timestamps
        self.alert_counts[alert_name] = [
            ts for ts in self.alert_counts[alert_name] if ts > cutoff
        ]
        
        # Check count
        if len(self.alert_counts[alert_name]) >= self.max_alerts_per_minute:
            return False
        
        # Record this alert
        self.alert_counts[alert_name].append(now)
        return True
    
    def _send_alert(self, alert: Alert):
        """Send alert through configured channels"""
        for channel in alert.channels:
            try:
                if channel == AlertChannel.LOG:
                    self._send_log_alert(alert)
                elif channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert)
                elif channel == AlertChannel.SLACK:
                    self._send_slack_alert(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")
    
    def _send_log_alert(self, alert: Alert):
        """Send alert to log"""
        if alert.priority == AlertPriority.CRITICAL:
            logger.critical(f"🚨 {alert.message}")
        elif alert.priority == AlertPriority.ERROR:
            logger.error(f"❌ {alert.message}")
        elif alert.priority == AlertPriority.WARNING:
            logger.warning(f"⚠️ {alert.message}")
        else:
            logger.info(f"ℹ️ {alert.message}")
    
    def _send_email_alert(self, alert: Alert):
        """Send email alert (placeholder)"""
        # In production, would use actual email configuration
        logger.info(f"📧 Email alert: {alert.message}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert (placeholder)"""
        # In production, would send actual webhook
        logger.info(f"🔗 Webhook alert: {alert.message}")
    
    def _send_slack_alert(self, alert: Alert):
        """Send Slack alert (placeholder)"""
        # In production, would use Slack API
        logger.info(f"💬 Slack alert: {alert.message}")

class MonitoringSystem:
    """
    Complete monitoring system with metrics, alerts, and health checks
    """
    
    def __init__(self):
        """Initialize monitoring system"""
        self.metric_collector = MetricCollector()
        self.alert_manager = AlertManager()
        self.health_checks = {}
        self.monitoring_thread = None
        self.running = False
        
        # Initialize default alerts
        self._initialize_default_alerts()
        
        # Initialize health checks
        self._initialize_health_checks()
        
        logger.info("📊 Monitoring System initialized")
    
    def _initialize_default_alerts(self):
        """Initialize default alert rules"""
        
        # Margin utilization alerts
        self.alert_manager.add_rule(
            name="margin_utilization_critical",
            condition=lambda m: m.get("margin_utilization", 0) > 0.9,
            priority=AlertPriority.CRITICAL,
            message="Margin utilization above 90%",
            channels=[AlertChannel.LOG, AlertChannel.EMAIL],
            suppress_minutes=5
        )
        
        self.alert_manager.add_rule(
            name="margin_utilization_warning",
            condition=lambda m: m.get("margin_utilization", 0) > 0.8,
            priority=AlertPriority.WARNING,
            message="Margin utilization above 80%",
            channels=[AlertChannel.LOG],
            suppress_minutes=10
        )
        
        # API usage alerts
        self.alert_manager.add_rule(
            name="api_budget_low",
            condition=lambda m: m.get("api_requests_remaining", 1000) < 100,
            priority=AlertPriority.WARNING,
            message="API budget low - less than 100 requests remaining",
            channels=[AlertChannel.LOG],
            suppress_minutes=30
        )
        
        # Cache performance alerts
        self.alert_manager.add_rule(
            name="cache_hit_rate_low",
            condition=lambda m: m.get("cache_hit_rate", 1.0) < 0.8,
            priority=AlertPriority.WARNING,
            message="Cache hit rate below 80%",
            channels=[AlertChannel.LOG],
            suppress_minutes=15
        )
        
        # Circuit breaker alerts
        self.alert_manager.add_rule(
            name="circuit_breaker_open",
            condition=lambda m: any(cb.get("state") == "open" for cb in m.get("circuit_breakers", {}).values()),
            priority=AlertPriority.ERROR,
            message="Circuit breaker is open",
            channels=[AlertChannel.LOG, AlertChannel.WEBHOOK],
            suppress_minutes=5
        )
    
    def _initialize_health_checks(self):
        """Initialize health check functions"""
        
        def check_margin_system():
            """Check margin system health"""
            try:
                from core.margin_rate_manager import get_margin_rate_manager
                manager = get_margin_rate_manager()
                status = manager.get_status()
                
                if not status["enabled"]:
                    return HealthCheck("margin_system", "unhealthy", "Margin system disabled", datetime.now())
                elif status["fallback_mode"]:
                    return HealthCheck("margin_system", "degraded", "Running in fallback mode", datetime.now(), status)
                else:
                    return HealthCheck("margin_system", "healthy", "Margin system operational", datetime.now(), status)
            except Exception as e:
                return HealthCheck("margin_system", "unhealthy", f"Error: {e}", datetime.now())
        
        def check_api_optimization():
            """Check API optimization health"""
            try:
                from core.api_request_optimizer import get_api_request_optimizer
                optimizer = get_api_request_optimizer()
                status = optimizer.get_status()
                
                budget_used = status["daily_budget"]["used"]
                budget_limit = status["daily_budget"]["limit"]
                utilization = budget_used / budget_limit if budget_limit > 0 else 0
                
                if utilization > 0.9:
                    return HealthCheck("api_optimization", "unhealthy", f"API budget critical: {utilization*100:.1f}%", datetime.now(), status)
                elif utilization > 0.7:
                    return HealthCheck("api_optimization", "degraded", f"API budget high: {utilization*100:.1f}%", datetime.now(), status)
                else:
                    return HealthCheck("api_optimization", "healthy", f"API budget normal: {utilization*100:.1f}%", datetime.now(), status)
            except Exception as e:
                return HealthCheck("api_optimization", "unhealthy", f"Error: {e}", datetime.now())
        
        self.health_checks["margin_system"] = check_margin_system
        self.health_checks["api_optimization"] = check_api_optimization
    
    def start(self):
        """Start monitoring system"""
        if self.running:
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("📊 Monitoring system started")
    
    def stop(self):
        """Stop monitoring system"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("📊 Monitoring system stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect metrics
                metrics = self._collect_system_metrics()
                
                # Check alerts
                self.alert_manager.check_alerts(metrics)
                
                # Sleep
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {}
        
        try:
            # Collect margin metrics
            from core.margin_rate_manager import get_margin_rate_manager
            margin_manager = get_margin_rate_manager()
            margin_status = margin_manager.get_status()
            
            metrics["margin_cached_rates"] = margin_status.get("cached_rates", 0)
            metrics["margin_fallback_mode"] = margin_status.get("fallback_mode", False)
            
            # Collect API metrics
            from core.api_request_optimizer import get_api_request_optimizer
            api_optimizer = get_api_request_optimizer()
            api_status = api_optimizer.get_status()
            
            metrics["api_requests_used"] = api_status["daily_budget"]["used"]
            metrics["api_requests_remaining"] = api_status["daily_budget"]["remaining"]
            metrics["api_success_rate"] = api_status["statistics"]["success_rate_percent"]
            
            # Collect circuit breaker status
            metrics["circuit_breakers"] = api_status.get("circuit_breaker", {})
            
            # Calculate derived metrics
            metrics["cache_hit_rate"] = self._calculate_cache_hit_rate()
            metrics["margin_utilization"] = self._get_margin_utilization()
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        # Placeholder - would calculate from actual cache statistics
        return 0.92
    
    def _get_margin_utilization(self) -> float:
        """Get current margin utilization"""
        try:
            from core.enhanced_margin_calculator import get_margin_calculator
            calculator = get_margin_calculator()
            # Would get actual positions here
            positions = []
            status = calculator.calculate_account_margin_status(positions)
            return status.margin_utilization
        except:
            return 0.0
    
    def record_metric(self, name: str, value: float, metric_type: MetricType = MetricType.GAUGE):
        """Record a metric"""
        if metric_type == MetricType.GAUGE:
            self.metric_collector.record_gauge(name, value)
        elif metric_type == MetricType.COUNTER:
            self.metric_collector.increment_counter(name, int(value))
        elif metric_type == MetricType.HISTOGRAM:
            self.metric_collector.record_histogram(name, value)
    
    def get_health_status(self) -> Dict[str, HealthCheck]:
        """Get all health check statuses"""
        results = {}
        for name, check_func in self.health_checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = HealthCheck(name, "unhealthy", f"Check failed: {e}", datetime.now())
        return results
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        health_status = self.get_health_status()
        metrics = self._collect_system_metrics()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "health": {
                name: {
                    "status": check.status,
                    "message": check.message,
                    "timestamp": check.timestamp.isoformat()
                }
                for name, check in health_status.items()
            },
            "metrics": metrics,
            "alerts": {
                "recent": [
                    {
                        "name": alert.name,
                        "priority": alert.priority.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    }
                    for alert in list(self.alert_manager.alert_history)[-10:]
                ],
                "suppressed": list(self.alert_manager.alert_suppression.keys())
            },
            "statistics": {
                "total_alerts": len(self.alert_manager.alert_history),
                "api_success_rate": metrics.get("api_success_rate", 0),
                "cache_hit_rate": metrics.get("cache_hit_rate", 0),
                "margin_utilization": metrics.get("margin_utilization", 0)
            }
        }

# Global instance
_monitoring_system = None

def get_monitoring_system() -> MonitoringSystem:
    """Get global monitoring system instance"""
    global _monitoring_system
    if _monitoring_system is None:
        _monitoring_system = MonitoringSystem()
    return _monitoring_system

if __name__ == "__main__":
    # Test the monitoring system
    print("📊 Testing Monitoring System")
    print("=" * 50)
    
    monitor = MonitoringSystem()
    
    # Start monitoring
    monitor.start()
    
    # Record some test metrics
    monitor.record_metric("test_gauge", 42.5, MetricType.GAUGE)
    monitor.record_metric("test_counter", 1, MetricType.COUNTER)
    monitor.record_metric("test_histogram", 100, MetricType.HISTOGRAM)
    
    # Get health status
    print("\n🏥 Health Status:")
    health = monitor.get_health_status()
    for name, check in health.items():
        print(f"  {name}: {check.status} - {check.message}")
    
    # Get dashboard data
    print("\n📊 Dashboard Data:")
    dashboard = monitor.get_dashboard_data()
    print(f"  Timestamp: {dashboard['timestamp']}")
    print(f"  Health Checks: {len(dashboard['health'])}")
    print(f"  Recent Alerts: {len(dashboard['alerts']['recent'])}")
    print(f"  Statistics: {dashboard['statistics']}")
    
    # Stop monitoring
    monitor.stop()
    
    print("\n✅ Monitoring system test complete")