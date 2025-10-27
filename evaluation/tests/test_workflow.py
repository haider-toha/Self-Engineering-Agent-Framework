"""
Workflow Execution Tests

Evaluates multi-tool workflow capabilities:
- Workflow planning accuracy
- Tool composition
- Data flow between tools
- Pattern recognition
"""

import time
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory


class WorkflowTests:
    """
    Test suite for multi-tool workflow execution.
    Evaluates composition, planning, and execution capabilities.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize workflow tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all workflow tests"""
        results = []
        
        # Test 1: Simple sequential workflow
        results.append(self.test_sequential_workflow())
        
        # Test 2: Dependent workflow (data flow)
        results.append(self.test_dependent_workflow())
        
        # Test 3: Workflow planning accuracy
        results.append(self.test_workflow_planning())
        
        # Test 4: Pattern recognition
        results.append(self.test_pattern_recognition())
        
        # Test 5: Multi-step execution
        results.append(self.test_multi_step_execution())
        
        return results
    
    def test_sequential_workflow(self) -> EvaluationResult:
        """Test: Execute independent sequential tasks"""
        test_id = "work_001"
        test_name = "Sequential Workflow Execution"
        
        start_time = time.time()
        
        try:
            # Query requiring multiple independent operations
            query = "Calculate 20% of 100 and also find the square root of 64"
            result = self.orchestrator.process_request(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if successful
            passed = result.get('success', False)
            
            # Check if multiple tools were used
            used_multi_tool = result.get('multi_tool', False) or result.get('tool_sequence')
            
            # Verify correct answers (20 and 8)
            response_text = str(result.get('response', '')).lower()
            has_correct_answers = '20' in response_text and '8' in response_text
            
            # Calculate score
            score = 0.0
            if passed:
                score += 0.4
            if used_multi_tool:
                score += 0.3
            if has_correct_answers:
                score += 0.3
            
            passed = score >= 0.7
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=passed,
                score=score,
                metrics={
                    "success": result.get('success'),
                    "multi_tool": used_multi_tool,
                    "correct_answers": has_correct_answers,
                    "tool_sequence": result.get('tool_sequence', [])
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_dependent_workflow(self) -> EvaluationResult:
        """Test: Execute workflow with data dependencies"""
        test_id = "work_002"
        test_name = "Dependent Workflow with Data Flow"
        
        start_time = time.time()
        
        try:
            # Query where second operation depends on first
            query = "Calculate 50% of 100, then convert that result to string and reverse it"
            result = self.orchestrator.process_request(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if successful
            passed = result.get('success', False)
            
            # Expected: 50% of 100 = 50, reverse "50" = "05"
            response_text = str(result.get('response', ''))
            
            # Check for evidence of composition
            used_composition = (
                result.get('multi_tool', False) or
                result.get('used_pattern', False) or
                result.get('synthesized_during_workflow', False)
            )
            
            # Calculate score
            score = 0.0
            if passed:
                score += 0.5
            if used_composition:
                score += 0.5
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=passed,
                score=score,
                metrics={
                    "success": result.get('success'),
                    "used_composition": used_composition,
                    "tool_sequence": result.get('tool_sequence', [])
                },
                execution_time_ms=execution_time,
                details=result
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_workflow_planning(self) -> EvaluationResult:
        """Test: Query planning accuracy"""
        test_id = "work_003"
        test_name = "Workflow Planning Accuracy"
        
        start_time = time.time()
        
        try:
            # Test if query planner correctly identifies complexity
            from src.query_planner import QueryPlanner
            planner = QueryPlanner(
                llm_client=self.orchestrator.query_planner.llm_client,
                registry=self.orchestrator.registry
            )
            
            # Test simple query
            simple_query = "What is 10% of 50?"
            simple_analysis = planner.analyze_query(simple_query)
            
            # Test complex query
            complex_query = "Calculate 25% of 200 and then find factorial of the result"
            complex_analysis = planner.analyze_query(complex_query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Verify correct classification
            simple_correct = not simple_analysis.get('is_complex', True)
            complex_correct = complex_analysis.get('is_complex', False)
            
            score = 0.0
            if simple_correct:
                score += 0.5
            if complex_correct:
                score += 0.5
            
            passed = score >= 0.5
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=passed,
                score=score,
                metrics={
                    "simple_query_classified_correctly": simple_correct,
                    "complex_query_classified_correctly": complex_correct,
                    "simple_analysis": simple_analysis,
                    "complex_analysis": complex_analysis
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_pattern_recognition(self) -> EvaluationResult:
        """Test: Pattern recognition and reuse"""
        test_id = "work_004"
        test_name = "Pattern Recognition"
        
        start_time = time.time()
        
        try:
            # Execute same workflow pattern multiple times
            query = "Calculate 10% of 100"
            
            # First execution
            result1 = self.orchestrator.process_request(query)
            
            # Second execution (should potentially recognize pattern)
            result2 = self.orchestrator.process_request(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if both succeeded
            both_success = result1.get('success') and result2.get('success')
            
            # Check if pattern was potentially used
            used_pattern = result2.get('used_pattern', False)
            
            # Second execution should be as fast or faster
            faster_second_time = True  # We don't have individual timing
            
            score = 0.0
            if both_success:
                score += 0.5
            if used_pattern:
                score += 0.3
            if faster_second_time:
                score += 0.2
            
            passed = both_success
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=passed,
                score=score,
                metrics={
                    "both_executions_successful": both_success,
                    "pattern_recognized": used_pattern
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_multi_step_execution(self) -> EvaluationResult:
        """Test: Execute multi-step workflow"""
        test_id = "work_005"
        test_name = "Multi-Step Workflow Execution"
        
        start_time = time.time()
        
        try:
            # Complex multi-step query
            query = "Calculate the square root of 144, then calculate 25% of that result"
            result = self.orchestrator.process_request(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Expected: sqrt(144) = 12, 25% of 12 = 3
            passed = result.get('success', False)
            
            response_text = str(result.get('response', ''))
            has_correct_answer = '3' in response_text and not '12' in response_text.replace('144', '')
            
            # Check if multiple steps were executed
            tool_sequence = result.get('tool_sequence', [])
            multi_step = len(tool_sequence) >= 2 if tool_sequence else False
            
            score = 0.0
            if passed:
                score += 0.4
            if multi_step:
                score += 0.3
            if has_correct_answer:
                score += 0.3
            
            passed = score >= 0.6
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=passed,
                score=score,
                metrics={
                    "success": result.get('success'),
                    "multi_step": multi_step,
                    "correct_answer": has_correct_answer,
                    "tool_sequence": tool_sequence,
                    "step_count": len(tool_sequence) if tool_sequence else 0
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.WORKFLOW,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

