"""
Performance & Efficiency Tests

Evaluates the agent's performance characteristics:
- Response time
- Resource utilization
- Scalability
- Throughput
"""

import time
import psutil
import os
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory


class PerformanceTests:
    """
    Test suite for performance and efficiency.
    Measures speed, resource usage, and scalability.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize performance tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.process = psutil.Process(os.getpid())
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all performance tests"""
        results = []
        
        # Test 1: Simple query response time
        results.append(self.test_simple_query_speed())
        
        # Test 2: Complex query response time
        results.append(self.test_complex_query_speed())
        
        # Test 3: Memory efficiency
        results.append(self.test_memory_efficiency())
        
        # Test 4: Concurrent query handling
        results.append(self.test_throughput())
        
        # Test 5: Synthesis performance
        results.append(self.test_synthesis_performance())
        
        return results
    
    def test_simple_query_speed(self) -> EvaluationResult:
        """Test: Response time for simple queries"""
        test_id = "perf_001"
        test_name = "Simple Query Response Time"
        
        start_time = time.time()
        
        try:
            # Test simple query that uses existing tool
            query = "What is 25% of 100?"
            
            query_start = time.time()
            result = self.orchestrator.process_request(query)
            query_time = (time.time() - query_start) * 1000  # milliseconds
            
            execution_time = (time.time() - start_time) * 1000
            
            # Score based on speed
            # Excellent: < 1s, Good: < 2s, Acceptable: < 3s, Poor: > 3s
            if query_time < 1000:
                speed_score = 1.0
            elif query_time < 2000:
                speed_score = 0.8
            elif query_time < 3000:
                speed_score = 0.6
            else:
                speed_score = 0.4
            
            # Factor in success
            success_bonus = 0.2 if result.get('success') else 0.0
            score = min(1.0, speed_score + success_bonus)
            
            passed = query_time < 3000 and result.get('success', False)
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=passed,
                score=score,
                metrics={
                    "query_time_ms": query_time,
                    "success": result.get('success'),
                    "used_existing_tool": not result.get('synthesized', False)
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_complex_query_speed(self) -> EvaluationResult:
        """Test: Response time for complex queries"""
        test_id = "perf_002"
        test_name = "Complex Query Response Time"
        
        start_time = time.time()
        
        try:
            # Test complex multi-step query
            query = "Calculate 50% of 200, then find the square root of that result"
            
            query_start = time.time()
            result = self.orchestrator.process_request(query)
            query_time = (time.time() - query_start) * 1000
            
            execution_time = (time.time() - start_time) * 1000
            
            # More lenient timing for complex queries
            # Excellent: < 5s, Good: < 10s, Acceptable: < 15s, Poor: > 15s
            if query_time < 5000:
                speed_score = 1.0
            elif query_time < 10000:
                speed_score = 0.8
            elif query_time < 15000:
                speed_score = 0.6
            else:
                speed_score = 0.4
            
            success_bonus = 0.2 if result.get('success') else 0.0
            score = min(1.0, speed_score + success_bonus)
            
            passed = query_time < 15000 and result.get('success', False)
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=passed,
                score=score,
                metrics={
                    "query_time_ms": query_time,
                    "success": result.get('success'),
                    "multi_tool": result.get('multi_tool', False)
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_memory_efficiency(self) -> EvaluationResult:
        """Test: Memory usage efficiency"""
        test_id = "perf_003"
        test_name = "Memory Efficiency"
        
        start_time = time.time()
        
        try:
            # Measure memory before
            mem_before = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Execute several queries
            queries = [
                "Calculate 10% of 100",
                "Reverse the string 'test'",
                "Square root of 144"
            ]
            
            for query in queries:
                try:
                    self.orchestrator.process_request(query)
                except Exception:
                    pass
            
            # Measure memory after
            mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
            mem_increase = mem_after - mem_before
            
            execution_time = (time.time() - start_time) * 1000
            
            # Score based on memory increase
            # Excellent: < 50MB, Good: < 100MB, Acceptable: < 200MB, Poor: > 200MB
            if mem_increase < 50:
                score = 1.0
            elif mem_increase < 100:
                score = 0.8
            elif mem_increase < 200:
                score = 0.6
            else:
                score = 0.4
            
            passed = mem_increase < 200
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=passed,
                score=score,
                metrics={
                    "memory_before_mb": mem_before,
                    "memory_after_mb": mem_after,
                    "memory_increase_mb": mem_increase
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_throughput(self) -> EvaluationResult:
        """Test: Query throughput"""
        test_id = "perf_004"
        test_name = "Query Throughput"
        
        start_time = time.time()
        
        try:
            # Execute multiple queries and measure throughput
            queries = [
                "What is 10% of 100?",
                "What is 20% of 200?",
                "What is 30% of 300?",
                "What is 40% of 400?",
                "What is 50% of 500?"
            ]
            
            successful = 0
            total_query_time = 0
            
            for query in queries:
                query_start = time.time()
                try:
                    result = self.orchestrator.process_request(query)
                    if result.get('success'):
                        successful += 1
                    total_query_time += (time.time() - query_start)
                except Exception:
                    total_query_time += (time.time() - query_start)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Calculate queries per second
            qps = len(queries) / total_query_time if total_query_time > 0 else 0.0
            
            # Score based on throughput and success rate
            success_rate = successful / len(queries)
            
            # Normalize QPS score (target: > 0.5 QPS for synthesis-capable agent)
            qps_score = min(1.0, qps / 0.5) if qps > 0 else 0.0
            
            score = (qps_score * 0.5) + (success_rate * 0.5)
            passed = qps >= 0.3 and success_rate >= 0.8
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=passed,
                score=score,
                metrics={
                    "queries_per_second": qps,
                    "successful_queries": successful,
                    "total_queries": len(queries),
                    "success_rate": success_rate,
                    "total_time_seconds": total_query_time
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_synthesis_performance(self) -> EvaluationResult:
        """Test: Synthesis operation performance"""
        test_id = "perf_005"
        test_name = "Synthesis Performance"
        
        start_time = time.time()
        
        try:
            # Test synthesis with timing
            query = "Create a function to check if a number is even"
            
            synthesis_start = time.time()
            result = self.orchestrator.process_request(query)
            synthesis_time = (time.time() - synthesis_start) * 1000
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if synthesis occurred
            was_synthesized = result.get('synthesized', False)
            was_successful = result.get('success', False)
            
            # Score based on synthesis time
            # Excellent: < 15s, Good: < 30s, Acceptable: < 45s, Poor: > 45s
            if synthesis_time < 15000:
                time_score = 1.0
            elif synthesis_time < 30000:
                time_score = 0.8
            elif synthesis_time < 45000:
                time_score = 0.6
            else:
                time_score = 0.4
            
            # Factor in success and whether it actually synthesized
            if was_successful and was_synthesized:
                score = time_score
            elif was_successful:
                score = 0.5  # Success but didn't synthesize (used existing tool)
            else:
                score = 0.0
            
            passed = synthesis_time < 45000 and was_successful
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=passed,
                score=score,
                metrics={
                    "synthesis_time_ms": synthesis_time,
                    "was_synthesized": was_synthesized,
                    "was_successful": was_successful
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.PERFORMANCE,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

