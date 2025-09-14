# core/api_request_optimizer.py

"""
⚡ API Request Optimizer

Intelligently manages and optimizes API requests to stay within IG Markets' 
daily limits while ensuring critical trading operations always have priority.

Key Features:
- Request batching and prioritization 
- Daily budget tracking with reserves for emergencies
- Intelligent request queuing and throttling
- Circuit breaker pattern for API protection
- Comprehensive logging and monitoring

Author: Advanced Trading Systems
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
import yaml
import json
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue, Empty
import functools

# Import secure configuration
from core.secure_config import get_secure_config

class RequestPriority(Enum):
    """Priority levels for API requests"""
    EMERGENCY = 0      # Emergency position management
    CRITICAL = 1       # Active trade management
    HIGH = 2          # New trade validation
    NORMAL = 3        # Margin rate updates
    LOW = 4           # Background sync operations

class RequestType(Enum):
    """Types of API requests for tracking"""
    POSITION_UPDATE = "position_update"
    POSITION_CLOSE = "position_close"
    MARGIN_RATE = "margin_rate"
    MARKET_DATA = "market_data"
    ACCOUNT_INFO = "account_info"
    AUTHENTICATION = "authentication"
    BULK_SYNC = "bulk_sync"

@dataclass
class APIRequest:
    """Container for API request information"""
    request_id: str
    request_type: RequestType
    priority: RequestPriority
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value

@dataclass
class RequestStats:
    """Statistics for API request tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limited_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    daily_budget_used: int = 0
    daily_budget_limit: int = 800

class APIRequestOptimizer:
    """
    Advanced API request optimizer that ensures efficient use of daily API limits
    while maintaining high availability for critical trading operations
    """
    
    def __init__(self):
        """Initialize the API request optimizer"""
        # Load secure configuration
        self.config = get_secure_config()
        margin_config = self.config.get("margin_management", {})
        api_config = margin_config.get("api_optimization", {})
        
        self.enabled = margin_config.get("enabled", True)
        self.daily_limit = api_config.get("daily_request_limit", 800)
        self.emergency_reserve = api_config.get("emergency_api_reserve", 50)
        
        # Request throttling settings
        self.min_request_interval = 0.1  # Minimum 100ms between requests
        self.batch_size = 5  # Maximum requests per batch
        self.batch_timeout = 2.0  # Maximum wait time for batch completion
        
        # Circuit breaker settings
        self.circuit_breaker_enabled = True
        self.failure_threshold = 5  # Failures before opening circuit
        self.circuit_timeout = 300  # 5 minutes before trying again
        
        # Internal state
        self.request_queue = PriorityQueue()
        self.stats = RequestStats(daily_budget_limit=self.daily_limit)
        self.running = False
        self.processor_thread = None
        self.last_request_time = 0
        self.circuit_breaker_state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure = None
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Request history for analysis
        self.request_history = []  # Keep last 1000 requests
        self.response_times = []  # Keep last 100 response times
        
        print(f"⚡ API Request Optimizer initialized")
        print(f"   Status: {'✅ ENABLED' if self.enabled else '❌ DISABLED'}")
        if self.enabled:
            print(f"   Daily Limit: {self.daily_limit} requests")
            print(f"   Emergency Reserve: {self.emergency_reserve} requests")
            print(f"   Min Interval: {self.min_request_interval}s")
            print(f"   Batch Size: {self.batch_size}")
    
    def start(self):
        """Start the API request processor"""
        if not self.enabled:
            print("⚠️ API Request Optimizer is disabled")
            return False
        
        print("⚡ Starting API Request Optimizer...")
        self.running = True
        
        # Start the processor thread
        self.processor_thread = threading.Thread(target=self._process_requests, daemon=True)
        self.processor_thread.start()
        
        # Reset daily stats if new day
        self._check_and_reset_daily_stats()
        
        print("✅ API Request Optimizer started")
        return True
    
    def stop(self):
        """Stop the API request processor"""
        print("🛑 Stopping API Request Optimizer...")
        self.running = False
        
        if self.processor_thread:
            self.processor_thread.join(timeout=10)
        
        print("✅ API Request Optimizer stopped")
    
    def submit_request(self, request_type: RequestType, priority: RequestPriority, 
                      function: Callable, *args, **kwargs) -> str:
        """
        Submit an API request for optimized processing
        
        Args:
            request_type: Type of the request
            priority: Priority level  
            function: Function to call for the API request
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Request ID for tracking
        """
        if not self.enabled:
            # If disabled, execute immediately
            try:
                return function(*args, **kwargs)
            except Exception as e:
                print(f"❌ Direct API request failed: {e}")
                return None
        
        # Generate unique request ID
        request_id = f"{request_type.value}_{int(time.time() * 1000)}"
        
        # Create request object
        api_request = APIRequest(
            request_id=request_id,
            request_type=request_type,
            priority=priority,
            function=function,
            args=args,
            kwargs=kwargs
        )
        
        # Check if we can make the request
        if not self._can_make_request(priority):
            print(f"❌ Request rejected: {request_id} (budget exceeded)")
            return None
        
        # Check circuit breaker
        if not self._check_circuit_breaker():
            print(f"❌ Request rejected: {request_id} (circuit breaker open)")
            return None
        
        # Add to queue
        self.request_queue.put(api_request)
        print(f"📤 Queued request: {request_id} (priority: {priority.name})")
        
        return request_id
    
    def submit_request_sync(self, request_type: RequestType, priority: RequestPriority,
                           function: Callable, *args, timeout: float = 30.0, **kwargs) -> Any:
        """
        Submit a synchronous API request and wait for result
        
        Args:
            request_type: Type of the request
            priority: Priority level
            function: Function to call
            timeout: Maximum wait time for result
            *args, **kwargs: Function arguments
            
        Returns:
            Result of the API call or None if failed/timeout
        """
        if not self.enabled:
            # If disabled, execute immediately
            try:
                return function(*args, **kwargs)
            except Exception as e:
                print(f"❌ Direct sync API request failed: {e}")
                return None
        
        # For critical and emergency requests, execute immediately
        if priority in [RequestPriority.EMERGENCY, RequestPriority.CRITICAL]:
            if self._can_make_request(priority) and self._check_circuit_breaker():
                return self._execute_request_immediately(request_type, function, args, kwargs)
            else:
                print(f"❌ Critical request blocked by safety limits")
                return None
        
        # For other requests, use the queue (this is a simplified sync implementation)
        # In production, you'd want a more sophisticated synchronous handling
        request_id = self.submit_request(request_type, priority, function, *args, **kwargs)
        if not request_id:
            return None
        
        # Wait for the request to be processed (simplified implementation)
        start_time = time.time()
        while time.time() - start_time < timeout:
            # In a real implementation, you'd use proper synchronization
            time.sleep(0.1)
            # For now, return None as we don't have result tracking implemented
        
        print(f"⏰ Sync request timeout: {request_id}")
        return None
    
    def _process_requests(self):
        """Main request processing loop"""
        batch = []
        
        while self.running:
            try:
                # Try to get a request from queue
                try:
                    request = self.request_queue.get(timeout=1.0)
                    batch.append(request)
                except Empty:
                    # Process any pending batch
                    if batch:
                        self._process_batch(batch)
                        batch = []
                    continue
                
                # Process batch when full or timeout reached
                if len(batch) >= self.batch_size:
                    self._process_batch(batch)
                    batch = []
                
            except Exception as e:
                print(f"❌ Error in request processor: {e}")
                time.sleep(1.0)
        
        # Process any remaining requests
        if batch:
            self._process_batch(batch)
    
    def _process_batch(self, batch: List[APIRequest]):
        """Process a batch of API requests"""
        if not batch:
            return
        
        print(f"⚡ Processing batch of {len(batch)} requests")
        
        # Sort batch by priority (already done by queue, but ensure)
        batch.sort(key=lambda x: x.priority.value)
        
        for request in batch:
            if not self.running:
                break
                
            try:
                # Check if still within budget
                if not self._can_make_request(request.priority):
                    print(f"❌ Skipping request {request.request_id}: budget exceeded")
                    continue
                
                # Execute the request
                self._execute_request(request)
                
                # Respect rate limiting
                time.sleep(self.min_request_interval)
                
            except Exception as e:
                print(f"❌ Error processing request {request.request_id}: {e}")
                self._record_request_failure(request)
    
    def _execute_request(self, request: APIRequest):
        """Execute a single API request"""
        start_time = time.time()
        
        try:
            # Update last request time
            self.last_request_time = time.time()
            
            # Execute the function
            result = request.function(*request.args, **request.kwargs)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Record success
            self._record_request_success(request, response_time)
            
            print(f"✅ Request completed: {request.request_id} ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Handle specific error types
            if "rate limit" in str(e).lower() or "429" in str(e):
                self._record_rate_limit(request)
                print(f"🚦 Rate limited: {request.request_id}")
                
                # Wait longer before next request
                time.sleep(5.0)
                
                # Retry if attempts remaining
                if request.retry_count < request.max_retries:
                    request.retry_count += 1
                    self.request_queue.put(request)
                    return
            
            # Record failure
            self._record_request_failure(request, response_time, str(e))
            print(f"❌ Request failed: {request.request_id} - {e}")
            
            # Retry logic for non-rate-limit failures
            if request.retry_count < request.max_retries:
                request.retry_count += 1
                # Add exponential backoff delay
                delay = min(60, 2 ** request.retry_count)
                time.sleep(delay)
                self.request_queue.put(request)
            
            return None
    
    def _execute_request_immediately(self, request_type: RequestType, function: Callable, 
                                   args: tuple, kwargs: dict) -> Any:
        """Execute a critical request immediately"""
        start_time = time.time()
        
        try:
            print(f"🚨 Executing immediate request: {request_type.value}")
            
            # Respect minimum interval
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)
            
            self.last_request_time = time.time()
            
            # Execute the function
            result = function(*args, **kwargs)
            
            # Record stats
            response_time = time.time() - start_time
            with self.lock:
                self.stats.total_requests += 1
                self.stats.successful_requests += 1
                self.stats.daily_budget_used += 1
                self._update_average_response_time(response_time)
            
            print(f"✅ Immediate request completed ({response_time:.2f}s)")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            with self.lock:
                self.stats.total_requests += 1
                self.stats.failed_requests += 1
                self.stats.daily_budget_used += 1
                
                # Update circuit breaker
                self.circuit_breaker_failures += 1
                self.circuit_breaker_last_failure = datetime.utcnow()
                
                if self.circuit_breaker_failures >= self.failure_threshold:
                    self.circuit_breaker_state = "OPEN"
                    print(f"🚨 Circuit breaker opened due to failures")
            
            print(f"❌ Immediate request failed: {e}")
            return None
    
    def _can_make_request(self, priority: RequestPriority) -> bool:
        """Check if we can make a request within budget constraints"""
        with self.lock:
            # Always allow emergency requests within circuit breaker limits
            if priority == RequestPriority.EMERGENCY:
                return self.stats.daily_budget_used < self.daily_limit
            
            # Check if we have budget excluding emergency reserve
            available_budget = self.daily_limit - self.emergency_reserve
            return self.stats.daily_budget_used < available_budget
    
    def _check_circuit_breaker(self) -> bool:
        """Check circuit breaker state"""
        if not self.circuit_breaker_enabled:
            return True
        
        with self.lock:
            if self.circuit_breaker_state == "CLOSED":
                return True
            elif self.circuit_breaker_state == "OPEN":
                # Check if timeout has passed
                if (self.circuit_breaker_last_failure and 
                    datetime.utcnow() - self.circuit_breaker_last_failure > timedelta(seconds=self.circuit_timeout)):
                    self.circuit_breaker_state = "HALF_OPEN"
                    self.circuit_breaker_failures = 0
                    print(f"🔄 Circuit breaker half-open - testing requests")
                    return True
                return False
            elif self.circuit_breaker_state == "HALF_OPEN":
                return True
        
        return False
    
    def _record_request_success(self, request: APIRequest, response_time: float):
        """Record a successful request"""
        with self.lock:
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.daily_budget_used += 1
            self.stats.last_request_time = datetime.utcnow()
            
            # Update response time
            self._update_average_response_time(response_time)
            
            # Circuit breaker success handling
            if self.circuit_breaker_state == "HALF_OPEN":
                self.circuit_breaker_state = "CLOSED"
                self.circuit_breaker_failures = 0
                print(f"✅ Circuit breaker closed - normal operation resumed")
            
            # Add to history (keep last 1000)
            self.request_history.append({
                "request_id": request.request_id,
                "type": request.request_type.value,
                "priority": request.priority.value,
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": response_time,
                "status": "success"
            })
            
            if len(self.request_history) > 1000:
                self.request_history = self.request_history[-1000:]
    
    def _record_request_failure(self, request: APIRequest, response_time: float = 0, error: str = ""):
        """Record a failed request"""
        with self.lock:
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.daily_budget_used += 1
            self.stats.last_request_time = datetime.utcnow()
            
            # Update response time if available
            if response_time > 0:
                self._update_average_response_time(response_time)
            
            # Circuit breaker failure handling
            self.circuit_breaker_failures += 1
            self.circuit_breaker_last_failure = datetime.utcnow()
            
            if self.circuit_breaker_failures >= self.failure_threshold:
                self.circuit_breaker_state = "OPEN"
                print(f"🚨 Circuit breaker opened - {self.circuit_breaker_failures} failures")
            
            # Add to history
            self.request_history.append({
                "request_id": request.request_id,
                "type": request.request_type.value,
                "priority": request.priority.value,
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": response_time,
                "status": "failed",
                "error": error
            })
            
            if len(self.request_history) > 1000:
                self.request_history = self.request_history[-1000:]
    
    def _record_rate_limit(self, request: APIRequest):
        """Record a rate limited request"""
        with self.lock:
            self.stats.rate_limited_requests += 1
    
    def _update_average_response_time(self, response_time: float):
        """Update average response time calculation"""
        self.response_times.append(response_time)
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        
        self.stats.average_response_time = sum(self.response_times) / len(self.response_times)
    
    def _check_and_reset_daily_stats(self):
        """Reset daily statistics if new day"""
        today = datetime.utcnow().date()
        
        with self.lock:
            if (not hasattr(self, '_last_reset_date') or 
                self._last_reset_date != today):
                
                print(f"🔄 Resetting daily API stats for {today}")
                self.stats.daily_budget_used = 0
                self.stats.rate_limited_requests = 0
                self._last_reset_date = today
                
                # Reset circuit breaker if it was open due to daily issues
                if self.circuit_breaker_state == "OPEN":
                    self.circuit_breaker_state = "CLOSED"
                    self.circuit_breaker_failures = 0
    
    def get_status(self) -> Dict:
        """Get comprehensive status of the API optimizer"""
        with self.lock:
            queue_size = self.request_queue.qsize()
            
            # Calculate success rate
            total_requests = self.stats.total_requests
            success_rate = (self.stats.successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Budget utilization
            budget_utilization = (self.stats.daily_budget_used / self.daily_limit * 100) if self.daily_limit > 0 else 0
            
        return {
            "enabled": self.enabled,
            "running": self.running,
            "queue_size": queue_size,
            "daily_budget": {
                "used": self.stats.daily_budget_used,
                "limit": self.daily_limit,
                "remaining": self.daily_limit - self.stats.daily_budget_used,
                "utilization_percent": budget_utilization
            },
            "statistics": {
                "total_requests": self.stats.total_requests,
                "successful_requests": self.stats.successful_requests,
                "failed_requests": self.stats.failed_requests,
                "rate_limited_requests": self.stats.rate_limited_requests,
                "success_rate_percent": success_rate,
                "average_response_time": self.stats.average_response_time
            },
            "circuit_breaker": {
                "state": self.circuit_breaker_state,
                "failures": self.circuit_breaker_failures,
                "enabled": self.circuit_breaker_enabled
            },
            "last_request": self.stats.last_request_time.isoformat() if self.stats.last_request_time else None
        }
    
    def get_request_history(self, limit: int = 50) -> List[Dict]:
        """Get recent request history"""
        with self.lock:
            return self.request_history[-limit:] if self.request_history else []

# Global instance
_api_request_optimizer = None

def get_api_request_optimizer() -> APIRequestOptimizer:
    """Get global API request optimizer instance"""
    global _api_request_optimizer
    if _api_request_optimizer is None:
        _api_request_optimizer = APIRequestOptimizer()
    return _api_request_optimizer

# Decorator for optimized API calls
def optimized_api_call(request_type: RequestType, priority: RequestPriority = RequestPriority.NORMAL):
    """
    Decorator to automatically optimize API calls
    
    Usage:
    @optimized_api_call(RequestType.MARGIN_RATE, RequestPriority.HIGH)
    def get_margin_rate(instrument):
        # Your API call here
        pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            optimizer = get_api_request_optimizer()
            return optimizer.submit_request_sync(request_type, priority, func, *args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    # Test the API request optimizer
    print("🧪 Testing API Request Optimizer")
    print("=" * 50)
    
    optimizer = APIRequestOptimizer()
    
    # Test function
    def mock_api_call(param1, param2="default"):
        time.sleep(0.1)  # Simulate API call
        print(f"📡 Mock API call: {param1}, {param2}")
        return f"result_{param1}"
    
    # Test sync request
    result = optimizer.submit_request_sync(
        RequestType.MARGIN_RATE,
        RequestPriority.HIGH,
        mock_api_call,
        "test_param",
        param2="custom"
    )
    print(f"Sync result: {result}")
    
    # Test async requests
    for i in range(5):
        request_id = optimizer.submit_request(
            RequestType.MARKET_DATA,
            RequestPriority.NORMAL,
            mock_api_call,
            f"async_param_{i}"
        )
        print(f"Submitted async request: {request_id}")
    
    # Start processor to handle queued requests
    optimizer.start()
    
    # Wait a bit for processing
    time.sleep(2)
    
    # Show status
    status = optimizer.get_status()
    print(f"📈 Optimizer Status:")
    for key, value in status.items():
        print(f"   {key}: {value}")
    
    # Show history
    history = optimizer.get_request_history(limit=5)
    print(f"📜 Recent Request History ({len(history)} requests):")
    for req in history:
        print(f"   {req['timestamp']}: {req['type']} -> {req['status']} ({req.get('response_time', 0):.2f}s)")
    
    optimizer.stop()