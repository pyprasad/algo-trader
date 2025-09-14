# core/error_handler.py

"""
🛡️ Comprehensive Error Handler

Provides robust error handling with circuit breakers, retry logic,
graceful fallbacks, and comprehensive logging for the margin system.

Key Features:
- Circuit breaker pattern implementation
- Exponential backoff retry logic
- Graceful degradation strategies
- Error categorization and routing
- Performance impact monitoring
- Alert generation for critical errors

Author: Reliability Engineering Team
"""

import time
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading
from collections import deque
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"          # Log only
    MEDIUM = "medium"    # Log and alert
    HIGH = "high"        # Immediate action required
    CRITICAL = "critical" # System shutdown may be required

class ErrorCategory(Enum):
    """Error categorization for routing"""
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    CALCULATION_ERROR = "calculation_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    MARGIN_ERROR = "margin_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorContext:
    """Context information for errors"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception]
    traceback: Optional[str]
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CircuitBreakerState:
    """Circuit breaker state tracking"""
    state: str  # "closed", "open", "half_open"
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    open_until: Optional[datetime]

class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures
    """
    
    def __init__(self, name: str, failure_threshold: int = 5, 
                 success_threshold: int = 2, timeout: int = 60):
        """
        Initialize circuit breaker
        
        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening
            success_threshold: Successes to close from half-open
            timeout: Seconds to wait before half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self.state = "closed"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.open_until = None
        
        self.lock = threading.Lock()
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker
        
        Args:
            func: Function to call
            *args, **kwargs: Function arguments
            
        Returns:
            Function result or raises exception
        """
        with self.lock:
            if self.state == "open":
                if datetime.now() < self.open_until:
                    raise Exception(f"Circuit breaker {self.name} is open")
                else:
                    # Transition to half-open
                    self.state = "half_open"
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} entering half-open state")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            self.last_success_time = datetime.now()
            
            if self.state == "half_open":
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info(f"Circuit breaker {self.name} closed")
            elif self.state == "closed":
                self.failure_count = 0  # Reset on success
    
    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.state == "closed":
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    self.open_until = datetime.now() + timedelta(seconds=self.timeout)
                    logger.warning(f"Circuit breaker {self.name} opened until {self.open_until}")
            elif self.state == "half_open":
                self.state = "open"
                self.open_until = datetime.now() + timedelta(seconds=self.timeout)
                self.failure_count = 0
                logger.warning(f"Circuit breaker {self.name} reopened")
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        with self.lock:
            return CircuitBreakerState(
                state=self.state,
                failure_count=self.failure_count,
                success_count=self.success_count,
                last_failure_time=self.last_failure_time,
                last_success_time=self.last_success_time,
                open_until=self.open_until
            )
    
    def reset(self):
        """Reset circuit breaker"""
        with self.lock:
            self.state = "closed"
            self.failure_count = 0
            self.success_count = 0
            self.open_until = None
            logger.info(f"Circuit breaker {self.name} reset")

class RetryStrategy:
    """
    Retry strategy with exponential backoff
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0):
        """
        Initialize retry strategy
        
        Args:
            max_retries: Maximum retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result or raises final exception
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

class ErrorHandler:
    """
    Comprehensive error handler with multiple strategies
    """
    
    def __init__(self):
        """Initialize error handler"""
        self.circuit_breakers = {}
        self.retry_strategies = {}
        self.error_history = deque(maxlen=1000)
        self.error_callbacks = []
        self.fallback_handlers = {}
        
        # Error statistics
        self.error_counts = {}
        self.last_errors = {}
        
        # Initialize default circuit breakers
        self._initialize_default_circuit_breakers()
        
        # Initialize default retry strategies
        self._initialize_default_retry_strategies()
        
        logger.info("🛡️ Error Handler initialized")
    
    def _initialize_default_circuit_breakers(self):
        """Initialize default circuit breakers"""
        self.circuit_breakers["api"] = CircuitBreaker("API", failure_threshold=5, timeout=60)
        self.circuit_breakers["database"] = CircuitBreaker("Database", failure_threshold=3, timeout=30)
        self.circuit_breakers["calculation"] = CircuitBreaker("Calculation", failure_threshold=10, timeout=10)
        self.circuit_breakers["margin"] = CircuitBreaker("Margin", failure_threshold=3, timeout=120)
    
    def _initialize_default_retry_strategies(self):
        """Initialize default retry strategies"""
        self.retry_strategies["api"] = RetryStrategy(max_retries=3, base_delay=1.0)
        self.retry_strategies["database"] = RetryStrategy(max_retries=5, base_delay=0.5)
        self.retry_strategies["network"] = RetryStrategy(max_retries=3, base_delay=2.0)
        self.retry_strategies["calculation"] = RetryStrategy(max_retries=2, base_delay=0.1)
    
    def handle_error(self, error: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """
        Handle an error with appropriate strategy
        
        Args:
            error: Exception that occurred
            category: Error category
            severity: Error severity
            context: Additional context
            
        Returns:
            ErrorContext with handling details
        """
        # Create error context
        error_context = ErrorContext(
            error_id=self._generate_error_id(),
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            message=str(error),
            exception=error,
            traceback=traceback.format_exc(),
            metadata=context or {}
        )
        
        # Log error
        self._log_error(error_context)
        
        # Update statistics
        self._update_error_statistics(error_context)
        
        # Store in history
        self.error_history.append(error_context)
        
        # Execute callbacks
        self._execute_callbacks(error_context)
        
        # Handle based on severity
        if severity == ErrorSeverity.CRITICAL:
            self._handle_critical_error(error_context)
        elif severity == ErrorSeverity.HIGH:
            self._handle_high_severity_error(error_context)
        
        return error_context
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        return f"ERR_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id(threading.current_thread())}"
    
    def _log_error(self, context: ErrorContext):
        """Log error based on severity"""
        log_message = f"[{context.error_id}] {context.category.value}: {context.message}"
        
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_message)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        if context.traceback:
            logger.debug(f"Traceback: {context.traceback}")
    
    def _update_error_statistics(self, context: ErrorContext):
        """Update error statistics"""
        category_key = context.category.value
        
        if category_key not in self.error_counts:
            self.error_counts[category_key] = 0
        
        self.error_counts[category_key] += 1
        self.last_errors[category_key] = context.timestamp
    
    def _execute_callbacks(self, context: ErrorContext):
        """Execute registered error callbacks"""
        for callback in self.error_callbacks:
            try:
                callback(context)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def _handle_critical_error(self, context: ErrorContext):
        """Handle critical errors"""
        logger.critical(f"CRITICAL ERROR: {context.error_id}")
        
        # Send immediate alert
        self._send_alert(context, "CRITICAL")
        
        # Check if system shutdown is needed
        if context.category == ErrorCategory.MARGIN_ERROR:
            logger.critical("Critical margin error - considering emergency shutdown")
            # Would trigger emergency position closure here
    
    def _handle_high_severity_error(self, context: ErrorContext):
        """Handle high severity errors"""
        logger.error(f"HIGH SEVERITY ERROR: {context.error_id}")
        
        # Send alert
        self._send_alert(context, "HIGH")
        
        # Apply circuit breaker if applicable
        if context.category == ErrorCategory.API_ERROR:
            self.circuit_breakers["api"]._on_failure()
    
    def _send_alert(self, context: ErrorContext, level: str):
        """Send alert for error (placeholder for actual alerting)"""
        alert_message = f"""
        🚨 {level} ALERT
        Error ID: {context.error_id}
        Category: {context.category.value}
        Message: {context.message}
        Time: {context.timestamp}
        """
        logger.critical(alert_message)
        # In production, would send to monitoring system
    
    def register_callback(self, callback: Callable[[ErrorContext], None]):
        """Register error callback"""
        self.error_callbacks.append(callback)
    
    def register_fallback(self, category: ErrorCategory, handler: Callable):
        """Register fallback handler for error category"""
        self.fallback_handlers[category] = handler
    
    def get_fallback_handler(self, category: ErrorCategory) -> Optional[Callable]:
        """Get fallback handler for category"""
        return self.fallback_handlers.get(category)
    
    def with_error_handling(self, category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           use_circuit_breaker: bool = False,
                           use_retry: bool = False):
        """
        Decorator for error handling
        
        Args:
            category: Error category
            severity: Error severity
            use_circuit_breaker: Use circuit breaker
            use_retry: Use retry logic
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    # Apply circuit breaker if requested
                    if use_circuit_breaker and category.value in self.circuit_breakers:
                        return self.circuit_breakers[category.value].call(func, *args, **kwargs)
                    
                    # Apply retry if requested
                    if use_retry and category.value in self.retry_strategies:
                        return self.retry_strategies[category.value].execute_with_retry(func, *args, **kwargs)
                    
                    # Normal execution
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    # Handle error
                    context = self.handle_error(e, category, severity)
                    
                    # Try fallback
                    fallback = self.get_fallback_handler(category)
                    if fallback:
                        logger.info(f"Executing fallback for {category.value}")
                        return fallback(*args, **kwargs)
                    
                    # Re-raise if no fallback
                    raise
            
            return wrapper
        return decorator
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "errors_by_category": self.error_counts.copy(),
            "last_errors": self.last_errors.copy(),
            "circuit_breakers": {
                name: cb.get_state().__dict__ 
                for name, cb in self.circuit_breakers.items()
            },
            "recent_errors": len(self.error_history)
        }
    
    def reset_circuit_breaker(self, name: str):
        """Reset specific circuit breaker"""
        if name in self.circuit_breakers:
            self.circuit_breakers[name].reset()
            logger.info(f"Circuit breaker {name} reset")
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        self.error_counts.clear()
        self.last_errors.clear()
        logger.info("Error history cleared")

# Global instance
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

# Convenience decorators
def with_error_handling(category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       use_circuit_breaker: bool = False,
                       use_retry: bool = False):
    """Convenience decorator for error handling"""
    handler = get_error_handler()
    return handler.with_error_handling(category, severity, use_circuit_breaker, use_retry)

# Example fallback functions
def api_fallback_handler(*args, **kwargs):
    """Fallback handler for API errors"""
    logger.warning("Using cached data due to API error")
    # Return cached or default data
    return {"status": "fallback", "data": None}

def calculation_fallback_handler(*args, **kwargs):
    """Fallback handler for calculation errors"""
    logger.warning("Using conservative calculation due to error")
    # Return conservative estimate
    return 0.05  # 5% margin rate as conservative default

if __name__ == "__main__":
    # Test the error handler
    print("🛡️ Testing Error Handler")
    print("=" * 50)
    
    handler = ErrorHandler()
    
    # Register fallback handlers
    handler.register_fallback(ErrorCategory.API_ERROR, api_fallback_handler)
    handler.register_fallback(ErrorCategory.CALCULATION_ERROR, calculation_fallback_handler)
    
    # Test error handling
    @with_error_handling(
        category=ErrorCategory.API_ERROR,
        severity=ErrorSeverity.HIGH,
        use_retry=True
    )
    def test_api_call():
        raise Exception("API connection failed")
    
    # Test with fallback
    try:
        result = test_api_call()
    except Exception as e:
        print(f"Error caught: {e}")
    
    # Show statistics
    stats = handler.get_error_statistics()
    print(f"\n📊 Error Statistics:")
    print(f"Total Errors: {stats['total_errors']}")
    print(f"By Category: {stats['errors_by_category']}")
    
    # Test circuit breaker
    print("\n🔌 Testing Circuit Breaker:")
    cb = handler.circuit_breakers["api"]
    
    for i in range(7):
        try:
            cb.call(lambda: 1/0)  # Will always fail
        except:
            print(f"Attempt {i+1}: Circuit breaker state = {cb.state}")
    
    print("\n✅ Error handler test complete")