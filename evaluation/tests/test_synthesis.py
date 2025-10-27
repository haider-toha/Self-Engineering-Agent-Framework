"""
Synthesis Quality Tests

Evaluates the quality of synthesized tools:
- Code correctness
- Test coverage
- Code quality metrics
- TDD process adherence
"""

import time
import ast
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory, EvaluationMetrics


class SynthesisTests:
    """
    Test suite for evaluating synthesis engine quality.
    Measures code generation, test quality, and TDD adherence.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize synthesis tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.metrics = EvaluationMetrics()
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all synthesis tests"""
        results = []
        
        # Test 1: Synthesis success rate
        results.append(self.test_synthesis_success_rate())
        
        # Test 2: Generated code quality
        results.append(self.test_code_quality())
        
        # Test 3: Test coverage
        results.append(self.test_coverage_quality())
        
        # Test 4: TDD process adherence
        results.append(self.test_tdd_process())
        
        # Test 5: Code parsability
        results.append(self.test_code_parsability())
        
        # Test 6: Synthesis time
        results.append(self.test_synthesis_time())
        
        return results
    
    def test_synthesis_success_rate(self) -> EvaluationResult:
        """Test: Measure synthesis success rate"""
        test_id = "synth_001"
        test_name = "Synthesis Success Rate"
        
        start_time = time.time()
        
        # Test synthesis with various tasks
        tasks = [
            "Calculate the GCD of two numbers",
            "Check if a number is prime",
            "Convert a string to title case"
        ]
        
        successful = 0
        total = len(tasks)
        
        for task in tasks:
            try:
                result = self.orchestrator.process_request(task)
                if result.get('success') and result.get('synthesized'):
                    successful += 1
            except Exception:
                pass
        
        execution_time = (time.time() - start_time) * 1000
        
        success_rate = successful / total if total > 0 else 0.0
        passed = success_rate >= 0.7  # At least 70% success
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.SYNTHESIS,
            passed=passed,
            score=success_rate,
            metrics={
                "successful": successful,
                "total": total,
                "success_rate": success_rate
            },
            execution_time_ms=execution_time
        )
    
    def test_code_quality(self) -> EvaluationResult:
        """Test: Evaluate generated code quality"""
        test_id = "synth_002"
        test_name = "Generated Code Quality"
        
        start_time = time.time()
        
        try:
            # Synthesize a tool
            result = self.orchestrator.process_request("Calculate the LCM of two numbers")
            execution_time = (time.time() - start_time) * 1000
            
            if not result.get('success') or not result.get('synthesized'):
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Synthesis failed"
                )
            
            # Get the tool
            tool_name = result.get('tool_name')
            if not tool_name:
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Tool name not found"
                )
            
            tool_info = self.orchestrator.registry.get_tool_by_name(tool_name)
            if not tool_info:
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Tool not found in registry"
                )
            
            code = tool_info['code']
            
            # Analyze code quality
            quality_metrics = self._analyze_code_quality(code)
            
            # Calculate score based on multiple factors
            score = (
                quality_metrics['has_docstring'] * 0.3 +
                quality_metrics['has_type_hints'] * 0.3 +
                quality_metrics['proper_structure'] * 0.2 +
                quality_metrics['no_syntax_errors'] * 0.2
            )
            
            passed = score >= 0.7
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=passed,
                score=score,
                metrics=quality_metrics,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_coverage_quality(self) -> EvaluationResult:
        """Test: Evaluate test coverage quality"""
        test_id = "synth_003"
        test_name = "Test Coverage Quality"
        
        start_time = time.time()
        
        try:
            # Synthesize a tool
            result = self.orchestrator.process_request("Calculate fibonacci number")
            execution_time = (time.time() - start_time) * 1000
            
            if not result.get('success') or not result.get('synthesized'):
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Synthesis failed"
                )
            
            tool_name = result.get('tool_name')
            tool_info = self.orchestrator.registry.get_tool_by_name(tool_name)
            
            if not tool_info:
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Tool not found"
                )
            
            # Read test file
            try:
                with open(tool_info['test_path'], 'r') as f:
                    test_code = f.read()
            except Exception:
                test_code = ""
            
            # Analyze test quality
            test_metrics = self._analyze_test_quality(test_code)
            
            score = (
                test_metrics['has_tests'] * 0.3 +
                min(test_metrics['test_count'] / 3, 1.0) * 0.3 +  # Normalize to max 3 tests
                test_metrics['tests_edge_cases'] * 0.2 +
                test_metrics['tests_normal_cases'] * 0.2
            )
            
            passed = score >= 0.6
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=passed,
                score=score,
                metrics=test_metrics,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_tdd_process(self) -> EvaluationResult:
        """Test: Verify TDD process is followed"""
        test_id = "synth_004"
        test_name = "TDD Process Adherence"
        
        start_time = time.time()
        
        # Track synthesis steps
        synthesis_steps = {
            'specification': False,
            'tests': False,
            'implementation': False,
            'verification': False,
            'registration': False
        }
        
        def track_callback(event_type, data):
            """Track synthesis steps"""
            if event_type == "synthesis_step":
                step = data.get('step')
                status = data.get('status')
                if step and status == 'complete':
                    synthesis_steps[step] = True
        
        try:
            result = self.orchestrator.process_request(
                "Calculate the power of a number",
                callback=track_callback
            )
            execution_time = (time.time() - start_time) * 1000
            
            # Check if all TDD steps were followed
            all_steps_complete = all(synthesis_steps.values())
            
            # Calculate score based on steps completed
            steps_completed = sum(synthesis_steps.values())
            score = steps_completed / len(synthesis_steps)
            
            passed = all_steps_complete and result.get('success', False)
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=passed,
                score=score,
                metrics={
                    "steps_completed": steps_completed,
                    "total_steps": len(synthesis_steps),
                    "step_details": synthesis_steps
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=False,
                score=0.0,
                metrics={"steps": synthesis_steps},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_code_parsability(self) -> EvaluationResult:
        """Test: Verify generated code is syntactically correct"""
        test_id = "synth_005"
        test_name = "Code Parsability"
        
        start_time = time.time()
        
        try:
            result = self.orchestrator.process_request("Generate a palindrome checker")
            execution_time = (time.time() - start_time) * 1000
            
            if not result.get('success') or not result.get('synthesized'):
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.5,  # Partial credit if tool wasn't synthesized
                    metrics={},
                    execution_time_ms=execution_time
                )
            
            tool_name = result.get('tool_name')
            tool_info = self.orchestrator.registry.get_tool_by_name(tool_name)
            
            if not tool_info:
                return EvaluationResult(
                    test_id=test_id,
                    test_name=test_name,
                    category=MetricCategory.SYNTHESIS,
                    passed=False,
                    score=0.0,
                    metrics={},
                    execution_time_ms=execution_time,
                    error_message="Tool not found"
                )
            
            code = tool_info['code']
            
            # Try to parse the code
            try:
                ast.parse(code)
                parsable = True
                error = None
            except SyntaxError as e:
                parsable = False
                error = str(e)
            
            passed = parsable
            score = 1.0 if parsable else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=passed,
                score=score,
                metrics={"parsable": parsable},
                execution_time_ms=execution_time,
                error_message=error
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_synthesis_time(self) -> EvaluationResult:
        """Test: Measure synthesis time performance"""
        test_id = "synth_006"
        test_name = "Synthesis Time Performance"
        
        start_time = time.time()
        
        try:
            result = self.orchestrator.process_request("Create a function to check even numbers")
            execution_time = (time.time() - start_time) * 1000
            
            # Score based on time (faster is better)
            # Excellent: < 10s, Good: < 20s, Acceptable: < 30s, Poor: > 30s
            if execution_time < 10000:
                score = 1.0
            elif execution_time < 20000:
                score = 0.8
            elif execution_time < 30000:
                score = 0.6
            else:
                score = 0.4
            
            passed = result.get('success', False) and execution_time < 30000
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=passed,
                score=score,
                metrics={
                    "synthesis_time_ms": execution_time,
                    "success": result.get('success'),
                    "synthesized": result.get('synthesized')
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.SYNTHESIS,
                passed=False,
                score=0.0,
                metrics={"synthesis_time_ms": execution_time},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def _analyze_code_quality(self, code: str) -> dict:
        """Analyze code quality metrics"""
        try:
            tree = ast.parse(code)
            
            has_docstring = False
            has_type_hints = False
            function_count = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    function_count += 1
                    # Check for docstring
                    if ast.get_docstring(node):
                        has_docstring = True
                    # Check for type hints
                    if node.returns or any(arg.annotation for arg in node.args.args):
                        has_type_hints = True
            
            return {
                'has_docstring': 1.0 if has_docstring else 0.0,
                'has_type_hints': 1.0 if has_type_hints else 0.0,
                'proper_structure': 1.0 if function_count > 0 else 0.0,
                'no_syntax_errors': 1.0,
                'function_count': function_count
            }
        except SyntaxError:
            return {
                'has_docstring': 0.0,
                'has_type_hints': 0.0,
                'proper_structure': 0.0,
                'no_syntax_errors': 0.0,
                'function_count': 0
            }
    
    def _analyze_test_quality(self, test_code: str) -> dict:
        """Analyze test quality metrics"""
        test_count = test_code.count('def test_')
        
        # Check for common test patterns
        has_edge_cases = any([
            'edge' in test_code.lower(),
            'empty' in test_code.lower(),
            'zero' in test_code.lower(),
            'none' in test_code.lower()
        ])
        
        has_normal_cases = 'def test_' in test_code
        
        return {
            'has_tests': 1.0 if test_count > 0 else 0.0,
            'test_count': test_count,
            'tests_edge_cases': 1.0 if has_edge_cases else 0.0,
            'tests_normal_cases': 1.0 if has_normal_cases else 0.0
        }

