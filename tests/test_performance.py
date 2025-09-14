# tests/test_performance.py

"""
⚡ Performance Tests for Margin System

Tests performance characteristics of margin system components to ensure
they meet production requirements for latency, throughput, and resource usage.

Author: Performance Engineering Team
"""

import unittest
import time
import threading
import statistics
import sys
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.margin_rate_manager import MarginRateManager
from core.enhanced_margin_calculator import EnhancedMarginCalculator
from core.timezone_manager import EnhancedTimezoneManager
from core.enhanced_session_detector import EnhancedSessionDetector

class PerformanceTestCase(unittest.TestCase):
    """Base class for performance tests"""
    
    def assertLatencyBelow(self, latency_ms: float, threshold_ms: float, operation: str):
        """Assert that latency is below threshold"""
        self.assertLess(
            latency_ms, threshold_ms,
            f"{operation} latency {latency_ms:.2f}ms exceeds threshold {threshold_ms}ms"
        )
    
    def assertThroughputAbove(self, operations_per_sec: float, threshold: float, operation: str):
        """Assert that throughput is above threshold"""
        self.assertGreater(
            operations_per_sec, threshold,
            f"{operation} throughput {operations_per_sec:.2f} ops/sec below threshold {threshold}"
        )

class TestMarginRateManagerPerformance(PerformanceTestCase):
    """Performance tests for MarginRateManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = MarginRateManager()
        self.test_instruments = [
            "IX.D.FTSE.DAILY.IP",
            "IX.D.DAX.DAILY.IP", 
            "IX.D.SPX.DAILY.IP",
            "CS.D.EURUSD.MINI.IP",
            "CS.D.GBPUSD.MINI.IP"
        ]
    
    def test_margin_rate_lookup_latency(self):
        """Test margin rate lookup latency"""
        # Warm up
        for _ in range(10):
            self.manager.get_current_margin_rate("IX.D.FTSE.DAILY.IP", 10000)
        
        # Measure latency
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            self.manager.get_current_margin_rate("IX.D.FTSE.DAILY.IP", 10000)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Assert performance requirements
        self.assertLatencyBelow(avg_latency, 10, "Average margin rate lookup")
        self.assertLatencyBelow(p95_latency, 50, "P95 margin rate lookup")
        
        print(f"Margin rate lookup - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
    
    def test_concurrent_rate_lookups(self):
        """Test concurrent margin rate lookups"""
        def lookup_rate(instrument):
            start = time.perf_counter()
            self.manager.get_current_margin_rate(instrument, 10000)
            return time.perf_counter() - start
        
        # Run concurrent lookups
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.perf_counter()
            
            futures = []
            for _ in range(100):
                instrument = self.test_instruments[_ % len(self.test_instruments)]
                futures.append(executor.submit(lookup_rate, instrument))
            
            latencies = [future.result() * 1000 for future in as_completed(futures)]
            total_time = time.perf_counter() - start_time
        
        # Calculate throughput
        throughput = len(futures) / total_time
        avg_latency = statistics.mean(latencies)
        
        # Assert performance requirements
        self.assertThroughputAbove(throughput, 100, "Concurrent margin rate lookups")
        self.assertLatencyBelow(avg_latency, 100, "Concurrent lookup latency")
        
        print(f"Concurrent lookups - Throughput: {throughput:.1f} ops/sec, Avg latency: {avg_latency:.2f}ms")
    
    def test_cache_performance(self):
        """Test cache hit performance vs miss performance"""
        instrument = "IX.D.FTSE.DAILY.IP"
        
        # Measure cache miss (first call)
        start = time.perf_counter()
        self.manager.get_current_margin_rate(instrument, 10000)
        cache_miss_time = (time.perf_counter() - start) * 1000
        
        # Measure cache hits
        cache_hit_times = []
        for _ in range(50):
            start = time.perf_counter()
            self.manager.get_current_margin_rate(instrument, 10000)
            cache_hit_times.append((time.perf_counter() - start) * 1000)
        
        avg_cache_hit_time = statistics.mean(cache_hit_times)
        
        # Cache hits should be significantly faster
        self.assertLess(avg_cache_hit_time, cache_miss_time / 2)
        self.assertLatencyBelow(avg_cache_hit_time, 1, "Cache hit")
        
        print(f"Cache performance - Miss: {cache_miss_time:.2f}ms, Hit: {avg_cache_hit_time:.2f}ms")
    
    def test_memory_usage_bulk_operations(self):
        """Test memory usage during bulk operations"""
        import psutil
        process = psutil.Process()
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform bulk operations
        for i in range(1000):
            instrument = self.test_instruments[i % len(self.test_instruments)]
            self.manager.get_current_margin_rate(instrument, 10000 + i)
        
        # Check memory after operations
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory
        
        # Should not increase memory significantly
        self.assertLess(memory_increase, 50, f"Memory usage increased by {memory_increase:.1f}MB")
        
        print(f"Memory usage - Baseline: {baseline_memory:.1f}MB, Final: {final_memory:.1f}MB")

class TestMarginCalculatorPerformance(PerformanceTestCase):
    """Performance tests for EnhancedMarginCalculator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.calculator = EnhancedMarginCalculator()
    
    def test_position_margin_calculation_latency(self):
        """Test position margin calculation latency"""
        latencies = []
        
        for _ in range(100):
            start = time.perf_counter()
            self.calculator.calculate_position_margin(
                "IX.D.FTSE.DAILY.IP", 10, 7500
            )
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        
        self.assertLatencyBelow(avg_latency, 5, "Position margin calculation")
        self.assertLatencyBelow(p95_latency, 20, "P95 position margin calculation")
        
        print(f"Position margin calc - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
    
    def test_account_status_calculation_with_many_positions(self):
        """Test account status calculation with many positions"""
        # Create many positions
        positions = []
        for i in range(100):
            positions.append({
                'instrument': f'IX.D.FTSE.DAILY.IP',
                'size': 10 + i,
                'current_price': 7500 + (i * 10)
            })
        
        # Measure calculation time
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            self.calculator.calculate_account_margin_status(positions, 1000000)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        # Should handle 100 positions efficiently
        self.assertLatencyBelow(avg_latency, 100, "Account status with 100 positions")
        
        print(f"Account status (100 positions) - Avg: {avg_latency:.2f}ms")
    
    def test_concurrent_calculations(self):
        """Test concurrent margin calculations"""
        def calculate_margin():
            return self.calculator.calculate_position_margin(
                "IX.D.FTSE.DAILY.IP", 10, 7500
            )
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            start_time = time.perf_counter()
            
            futures = [executor.submit(calculate_margin) for _ in range(200)]
            results = [future.result() for future in as_completed(futures)]
            
            total_time = time.perf_counter() - start_time
        
        throughput = len(futures) / total_time
        
        self.assertThroughputAbove(throughput, 500, "Concurrent margin calculations")
        self.assertEqual(len(results), 200)  # All should complete
        
        print(f"Concurrent margin calculations - Throughput: {throughput:.1f} ops/sec")

class TestTimezoneManagerPerformance(PerformanceTestCase):
    """Performance tests for EnhancedTimezoneManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tz_manager = EnhancedTimezoneManager()
    
    def test_timezone_conversion_latency(self):
        """Test timezone conversion performance"""
        test_time = datetime(2024, 6, 15, 12, 0, 0)
        
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            self.tz_manager.convert_time(test_time, "UTC", "Europe/London")
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        self.assertLatencyBelow(avg_latency, 1, "Timezone conversion")
        
        print(f"Timezone conversion - Avg: {avg_latency:.3f}ms")
    
    def test_market_status_detection_latency(self):
        """Test market status detection performance"""
        latencies = []
        
        for _ in range(100):
            start = time.perf_counter()
            self.tz_manager.get_market_status("IX.D.FTSE.DAILY.IP")
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        self.assertLatencyBelow(avg_latency, 10, "Market status detection")
        
        print(f"Market status detection - Avg: {avg_latency:.2f}ms")

class TestSessionDetectorPerformance(PerformanceTestCase):
    """Performance tests for EnhancedSessionDetector"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = EnhancedSessionDetector()
    
    def test_session_detection_latency(self):
        """Test session detection performance"""
        latencies = []
        
        for _ in range(100):
            start = time.perf_counter()
            self.detector.detect_current_session("IX.D.FTSE.DAILY.IP")
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        
        self.assertLatencyBelow(avg_latency, 20, "Session detection")
        
        print(f"Session detection - Avg: {avg_latency:.2f}ms")

class TestSystemPerformance(PerformanceTestCase):
    """End-to-end system performance tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = MarginRateManager()
        self.calculator = EnhancedMarginCalculator(self.manager)
        self.tz_manager = EnhancedTimezoneManager()
        self.detector = EnhancedSessionDetector()
    
    def test_complete_margin_workflow_latency(self):
        """Test complete margin calculation workflow"""
        latencies = []
        
        for _ in range(50):
            start = time.perf_counter()
            
            # Complete workflow
            instrument = "IX.D.FTSE.DAILY.IP"
            size = 10
            price = 7500
            
            # 1. Get current session
            session = self.detector.detect_current_session(instrument)
            
            # 2. Get margin rate
            rate = self.manager.get_current_margin_rate(instrument, size * price)
            
            # 3. Calculate position margin
            margin_req = self.calculator.calculate_position_margin(instrument, size, price)
            
            # 4. Calculate account status
            positions = [{'instrument': instrument, 'size': size, 'current_price': price}]
            status = self.calculator.calculate_account_margin_status(positions, 100000)
            
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18]
        
        # Complete workflow should be fast
        self.assertLatencyBelow(avg_latency, 100, "Complete margin workflow")
        self.assertLatencyBelow(p95_latency, 200, "P95 complete margin workflow")
        
        print(f"Complete workflow - Avg: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
    
    def test_system_throughput_under_load(self):
        """Test system throughput under load"""
        def margin_workflow():
            instrument = "IX.D.FTSE.DAILY.IP"
            rate = self.manager.get_current_margin_rate(instrument, 75000)
            margin_req = self.calculator.calculate_position_margin(instrument, 10, 7500)
            return rate, margin_req
        
        # Test with multiple concurrent users
        with ThreadPoolExecutor(max_workers=50) as executor:
            start_time = time.perf_counter()
            
            # Submit 500 operations
            futures = [executor.submit(margin_workflow) for _ in range(500)]
            results = [future.result() for future in as_completed(futures)]
            
            total_time = time.perf_counter() - start_time
        
        throughput = len(futures) / total_time
        
        self.assertThroughputAbove(throughput, 200, "System under load")
        self.assertEqual(len(results), 500)  # All operations should complete
        
        print(f"System under load - Throughput: {throughput:.1f} workflows/sec")

if __name__ == '__main__':
    print("⚡ Running Performance Tests")
    print("=" * 60)
    
    # Run performance tests
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 60)
    print("Performance test summary:")
    print("• Margin rate lookup should be <10ms average, <50ms P95")
    print("• Cache hits should be <1ms")  
    print("• Position calculations should be <5ms average")
    print("• Complete workflow should be <100ms average")
    print("• System should handle >200 workflows/sec under load")
    print("• Concurrent operations should maintain low latency")
    print("• Memory usage should remain stable during bulk operations")