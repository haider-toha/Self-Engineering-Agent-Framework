"""
Functional Correctness Tests

Evaluates whether the agent produces correct outputs for various tasks.
Tests both existing tools and synthesized tools.
"""

import time
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory


class FunctionalTests:
    """
    Functional correctness test suite.
    Tests the agent's ability to correctly execute tasks.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize functional tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all functional tests"""
        results = []
        
        # Test 1: Basic arithmetic (existing tool)
        results.append(self.test_percentage_calculation())
        
        # Test 2: String manipulation (may need synthesis)
        results.append(self.test_string_reversal())
        
        # Test 3: Mathematical function (may need synthesis)
        results.append(self.test_factorial())
        
        # Test 4: Temperature conversion
        results.append(self.test_temperature_conversion())
        
        # Test 5: Square root calculation
        results.append(self.test_square_root())
        
        # Test 6: Complex query with multiple values
        results.append(self.test_multiple_percentages())
        
        # Test 7: Edge case - zero values
        results.append(self.test_edge_case_zero())
        
        # Test 8: Large numbers
        results.append(self.test_large_numbers())
        
        return results
    
    def test_percentage_calculation(self) -> EvaluationResult:
        """Test: Calculate percentage"""
        test_id = "func_001"
        test_name = "Basic Percentage Calculation"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("What is 25% of 100?")
            execution_time = (time.time() - start_time) * 1000
            
            # Check if result is successful
            passed = result.get('success', False)
            
            # Check if answer is correct (expecting 25)
            if passed:
                response_text = str(result.get('response', '')).lower()
                # Look for the number 25 in the response
                correct_answer = '25' in response_text or 'twenty-five' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 25,
                    "got_success": result.get('success'),
                    "used_existing_tool": not result.get('synthesized', False)
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_string_reversal(self) -> EvaluationResult:
        """Test: Reverse a string"""
        test_id = "func_002"
        test_name = "String Reversal"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("Reverse the string 'hello'")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', '')).lower()
                # Look for reversed string 'olleh'
                correct_answer = 'olleh' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": "olleh",
                    "got_success": result.get('success'),
                    "synthesized": result.get('synthesized', False)
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_factorial(self) -> EvaluationResult:
        """Test: Calculate factorial"""
        test_id = "func_003"
        test_name = "Factorial Calculation"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("Calculate the factorial of 5")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', '')).lower()
                # Factorial of 5 is 120
                correct_answer = '120' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 120,
                    "got_success": result.get('success'),
                    "synthesized": result.get('synthesized', False)
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_temperature_conversion(self) -> EvaluationResult:
        """Test: Convert temperature"""
        test_id = "func_004"
        test_name = "Temperature Conversion"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("Convert 0 Celsius to Fahrenheit")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', ''))
                # 0°C = 32°F
                correct_answer = '32' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": "32",
                    "got_success": result.get('success')
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_square_root(self) -> EvaluationResult:
        """Test: Calculate square root"""
        test_id = "func_005"
        test_name = "Square Root Calculation"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("What is the square root of 144?")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', ''))
                # Square root of 144 is 12
                correct_answer = '12' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 12,
                    "got_success": result.get('success')
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_multiple_percentages(self) -> EvaluationResult:
        """Test: Handle query with specific values"""
        test_id = "func_006"
        test_name = "Specific Percentage Values"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("Calculate 15 percent of 300")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', ''))
                # 15% of 300 is 45
                correct_answer = '45' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 45,
                    "got_success": result.get('success')
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_edge_case_zero(self) -> EvaluationResult:
        """Test: Edge case with zero"""
        test_id = "func_007"
        test_name = "Edge Case - Zero Value"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("What is 0% of 100?")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', ''))
                # 0% of 100 is 0
                correct_answer = ' 0' in response_text or 'zero' in response_text.lower()
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 0,
                    "got_success": result.get('success')
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_large_numbers(self) -> EvaluationResult:
        """Test: Handle large numbers"""
        test_id = "func_008"
        test_name = "Large Numbers"
        
        start_time = time.time()
        try:
            result = self.orchestrator.process_request("What is 50% of 10000?")
            execution_time = (time.time() - start_time) * 1000
            
            passed = result.get('success', False)
            
            if passed:
                response_text = str(result.get('response', ''))
                # 50% of 10000 is 5000
                correct_answer = '5000' in response_text
                passed = correct_answer
            
            score = 1.0 if passed else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=passed,
                score=score,
                metrics={
                    "expected": 5000,
                    "got_success": result.get('success')
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.FUNCTIONAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

