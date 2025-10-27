"""
Robustness & Edge Case Tests

Evaluates the agent's ability to handle:
- Malformed queries
- Edge cases
- Error recovery
- Invalid inputs
- Ambiguous requests
"""

import time
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory


class RobustnessTests:
    """
    Test suite for robustness and error handling.
    Tests edge cases, invalid inputs, and error recovery.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize robustness tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all robustness tests"""
        results = []
        
        # Test 1: Handle malformed queries
        results.append(self.test_malformed_queries())
        
        # Test 2: Edge case values
        results.append(self.test_edge_case_values())
        
        # Test 3: Error recovery
        results.append(self.test_error_recovery())
        
        # Test 4: Ambiguous queries
        results.append(self.test_ambiguous_queries())
        
        # Test 5: Invalid inputs
        results.append(self.test_invalid_inputs())
        
        # Test 6: Graceful degradation
        results.append(self.test_graceful_degradation())
        
        return results
    
    def test_malformed_queries(self) -> EvaluationResult:
        """Test: Handle malformed/incomplete queries"""
        test_id = "robust_001"
        test_name = "Malformed Query Handling"
        
        start_time = time.time()
        
        malformed_queries = [
            "calculate percentage",  # Missing values
            "reverse",  # Incomplete
            "what is",  # No operation specified
            ""  # Empty query
        ]
        
        handled_gracefully = 0
        crashed = 0
        
        for query in malformed_queries:
            try:
                result = self.orchestrator.process_request(query)
                # Should either succeed with clarification or fail gracefully
                if result.get('response'):
                    handled_gracefully += 1
            except Exception:
                crashed += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        total = len(malformed_queries)
        graceful_rate = handled_gracefully / total if total > 0 else 0.0
        crash_rate = crashed / total if total > 0 else 0.0
        
        # Score: high for graceful handling, low for crashes
        score = graceful_rate * (1.0 - crash_rate)
        passed = crash_rate == 0.0  # Should never crash
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.ROBUSTNESS,
            passed=passed,
            score=score,
            metrics={
                "handled_gracefully": handled_gracefully,
                "crashed": crashed,
                "total_queries": total,
                "graceful_rate": graceful_rate,
                "crash_rate": crash_rate
            },
            execution_time_ms=execution_time
        )
    
    def test_edge_case_values(self) -> EvaluationResult:
        """Test: Handle edge case values"""
        test_id = "robust_002"
        test_name = "Edge Case Value Handling"
        
        start_time = time.time()
        
        edge_cases = [
            ("What is 0% of 100?", "0"),
            ("What is 100% of 50?", "50"),
            ("Calculate factorial of 0", "1"),
            ("Reverse an empty string ''", ""),
            ("Square root of 0", "0")
        ]
        
        handled_correctly = 0
        total = len(edge_cases)
        
        for query, expected in edge_cases:
            try:
                result = self.orchestrator.process_request(query)
                if result.get('success'):
                    response = str(result.get('response', '')).lower()
                    # Check if response contains expected value
                    if expected in response or expected.lower() in response:
                        handled_correctly += 1
            except Exception:
                pass
        
        execution_time = (time.time() - start_time) * 1000
        
        correctness_rate = handled_correctly / total if total > 0 else 0.0
        score = correctness_rate
        passed = correctness_rate >= 0.6  # At least 60% correct
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.ROBUSTNESS,
            passed=passed,
            score=score,
            metrics={
                "handled_correctly": handled_correctly,
                "total_cases": total,
                "correctness_rate": correctness_rate
            },
            execution_time_ms=execution_time
        )
    
    def test_error_recovery(self) -> EvaluationResult:
        """Test: Recover from errors"""
        test_id = "robust_003"
        test_name = "Error Recovery"
        
        start_time = time.time()
        
        try:
            # Try a query that might fail first time
            query = "Calculate the median of [1, 2, 3, 4, 5]"
            
            recovered = False
            final_success = False
            error_occurred = False
            
            try:
                result = self.orchestrator.process_request(query)
                final_success = result.get('success', False)
                
                # Check if synthesis or retry was attempted
                if result.get('synthesized') or result.get('attempts', 1) > 1:
                    recovered = True
                    
            except Exception as e:
                error_occurred = True
            
            execution_time = (time.time() - start_time) * 1000
            
            # Score based on recovery capability
            score = 0.0
            if not error_occurred:
                score += 0.4
            if recovered:
                score += 0.3
            if final_success:
                score += 0.3
            
            passed = not error_occurred and final_success
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.ROBUSTNESS,
                passed=passed,
                score=score,
                metrics={
                    "recovered": recovered,
                    "final_success": final_success,
                    "error_occurred": error_occurred
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.ROBUSTNESS,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_ambiguous_queries(self) -> EvaluationResult:
        """Test: Handle ambiguous queries"""
        test_id = "robust_004"
        test_name = "Ambiguous Query Handling"
        
        start_time = time.time()
        
        ambiguous_queries = [
            "calculate it",  # What to calculate?
            "do the thing",  # What thing?
            "process the data"  # What data, what process?
        ]
        
        handled = 0
        crashed = 0
        
        for query in ambiguous_queries:
            try:
                result = self.orchestrator.process_request(query)
                # Should handle gracefully (maybe ask for clarification or fail gracefully)
                if result is not None:
                    handled += 1
            except Exception:
                crashed += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        total = len(ambiguous_queries)
        handling_rate = handled / total if total > 0 else 0.0
        crash_rate = crashed / total if total > 0 else 0.0
        
        score = handling_rate * (1.0 - crash_rate)
        passed = crash_rate == 0.0
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.ROBUSTNESS,
            passed=passed,
            score=score,
            metrics={
                "handled": handled,
                "crashed": crashed,
                "total_queries": total,
                "handling_rate": handling_rate,
                "crash_rate": crash_rate
            },
            execution_time_ms=execution_time
        )
    
    def test_invalid_inputs(self) -> EvaluationResult:
        """Test: Handle invalid input types"""
        test_id = "robust_005"
        test_name = "Invalid Input Handling"
        
        start_time = time.time()
        
        invalid_queries = [
            "Calculate percentage of abc and xyz",  # Non-numeric
            "Factorial of -5",  # Negative number
            "Square root of -1",  # Invalid for real numbers
            "Divide 10 by 0"  # Division by zero
        ]
        
        handled_safely = 0
        crashed = 0
        
        for query in invalid_queries:
            try:
                result = self.orchestrator.process_request(query)
                # Should either handle gracefully or provide error message
                if result and (not result.get('success') or result.get('error')):
                    handled_safely += 1
                elif result and result.get('success'):
                    # Check if it actually validated the input
                    handled_safely += 0.5  # Partial credit
            except Exception:
                crashed += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        total = len(invalid_queries)
        safety_rate = handled_safely / total if total > 0 else 0.0
        crash_rate = crashed / total if total > 0 else 0.0
        
        score = safety_rate * (1.0 - crash_rate)
        passed = crash_rate == 0.0
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.ROBUSTNESS,
            passed=passed,
            score=score,
            metrics={
                "handled_safely": handled_safely,
                "crashed": crashed,
                "total_queries": total,
                "safety_rate": safety_rate,
                "crash_rate": crash_rate
            },
            execution_time_ms=execution_time
        )
    
    def test_graceful_degradation(self) -> EvaluationResult:
        """Test: Graceful degradation under stress"""
        test_id = "robust_006"
        test_name = "Graceful Degradation"
        
        start_time = time.time()
        
        # Test with increasingly complex queries
        queries = [
            "What is 10% of 100?",  # Simple
            "Calculate 20% of 200 and reverse the result",  # Medium
            "Find 30% of 300, calculate factorial of that, then find square root",  # Complex
            "Process this extremely long and complicated query with multiple steps and dependencies that might be challenging"  # Very complex
        ]
        
        success_count = 0
        partial_success_count = 0
        failures = 0
        
        for query in queries:
            try:
                result = self.orchestrator.process_request(query)
                if result.get('success'):
                    success_count += 1
                elif result.get('response'):
                    partial_success_count += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        total = len(queries)
        full_score = success_count / total
        partial_score = partial_success_count / total * 0.5
        score = full_score + partial_score
        
        passed = failures == 0  # Should handle all gracefully
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.ROBUSTNESS,
            passed=passed,
            score=score,
            metrics={
                "success_count": success_count,
                "partial_success_count": partial_success_count,
                "failures": failures,
                "total_queries": total
            },
            execution_time_ms=execution_time
        )

