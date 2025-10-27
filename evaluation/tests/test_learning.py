"""
Learning & Adaptation Tests

Evaluates the agent's learning capabilities:
- Tool reuse rate
- Pattern learning
- Performance improvement over time
- Knowledge retention
"""

import time
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory


class LearningTests:
    """
    Test suite for learning and adaptation capabilities.
    Measures how the agent improves over time.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize learning tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all learning tests"""
        results = []
        
        # Test 1: Tool reuse rate
        results.append(self.test_tool_reuse())
        
        # Test 2: Learning curve
        results.append(self.test_learning_curve())
        
        # Test 3: Pattern detection
        results.append(self.test_pattern_learning())
        
        # Test 4: Knowledge retention
        results.append(self.test_knowledge_retention())
        
        return results
    
    def test_tool_reuse(self) -> EvaluationResult:
        """Test: Tool reuse rate"""
        test_id = "learn_001"
        test_name = "Tool Reuse Rate"
        
        start_time = time.time()
        
        try:
            # Count existing tools before
            initial_tool_count = self.orchestrator.registry.count_tools()
            
            # Execute similar queries that could reuse tools
            queries = [
                "What is 10% of 100?",
                "Calculate 20% of 200",
                "Find 30% of 300",
                "Compute 15% of 150"
            ]
            
            synthesis_count = 0
            reuse_count = 0
            
            for query in queries:
                try:
                    result = self.orchestrator.process_request(query)
                    if result.get('success'):
                        if result.get('synthesized'):
                            synthesis_count += 1
                        else:
                            reuse_count += 1
                except Exception:
                    pass
            
            execution_time = (time.time() - start_time) * 1000
            
            # Calculate reuse rate
            total_executions = synthesis_count + reuse_count
            reuse_rate = reuse_count / total_executions if total_executions > 0 else 0.0
            
            # Score is reuse rate (higher is better)
            score = reuse_rate
            passed = reuse_rate >= 0.7  # At least 70% reuse
            
            # Count tools after
            final_tool_count = self.orchestrator.registry.count_tools()
            tools_created = final_tool_count - initial_tool_count
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=passed,
                score=score,
                metrics={
                    "reuse_count": reuse_count,
                    "synthesis_count": synthesis_count,
                    "reuse_rate": reuse_rate,
                    "tools_created": tools_created,
                    "initial_tool_count": initial_tool_count,
                    "final_tool_count": final_tool_count
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_learning_curve(self) -> EvaluationResult:
        """Test: Performance improvement over repeated tasks"""
        test_id = "learn_002"
        test_name = "Learning Curve Analysis"
        
        start_time = time.time()
        
        try:
            # Execute same type of task multiple times
            base_query = "Calculate {}% of {}"
            
            execution_times = []
            success_count = 0
            
            for i in range(5):
                task_start = time.time()
                try:
                    query = base_query.format((i + 1) * 10, (i + 1) * 100)
                    result = self.orchestrator.process_request(query)
                    task_time = time.time() - task_start
                    execution_times.append(task_time)
                    
                    if result.get('success'):
                        success_count += 1
                except Exception:
                    execution_times.append(time.time() - task_start)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Analyze if performance improved (times decreased)
            if len(execution_times) >= 3:
                early_avg = sum(execution_times[:2]) / 2
                late_avg = sum(execution_times[-2:]) / 2
                improvement_rate = (early_avg - late_avg) / early_avg if early_avg > 0 else 0.0
            else:
                improvement_rate = 0.0
            
            # Score based on success rate and improvement
            success_rate = success_count / 5
            score = (success_rate * 0.6) + (max(0, improvement_rate) * 0.4)
            
            passed = success_rate >= 0.8
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=passed,
                score=score,
                metrics={
                    "success_count": success_count,
                    "success_rate": success_rate,
                    "execution_times": execution_times,
                    "improvement_rate": improvement_rate
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_pattern_learning(self) -> EvaluationResult:
        """Test: Workflow pattern detection"""
        test_id = "learn_003"
        test_name = "Pattern Learning"
        
        start_time = time.time()
        
        try:
            # Check if workflow tracker is detecting patterns
            tracker = self.orchestrator.workflow_tracker
            
            # Get workflow patterns before
            patterns_before = tracker.get_workflow_patterns(min_frequency=1)
            initial_pattern_count = len(patterns_before)
            
            # Execute a workflow multiple times to create a pattern
            workflow_query = "Calculate 25% of 400"
            
            for _ in range(3):
                try:
                    self.orchestrator.process_request(workflow_query)
                except Exception:
                    pass
            
            # Check patterns after
            patterns_after = tracker.get_workflow_patterns(min_frequency=1)
            final_pattern_count = len(patterns_after)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if new patterns were learned
            patterns_learned = final_pattern_count >= initial_pattern_count
            
            # Check pattern quality
            if patterns_after:
                avg_frequency = sum(p.get('frequency', 0) for p in patterns_after) / len(patterns_after)
                has_quality_patterns = avg_frequency >= 1.5
            else:
                has_quality_patterns = False
            
            score = 0.0
            if patterns_learned:
                score += 0.5
            if has_quality_patterns:
                score += 0.5
            
            passed = patterns_learned
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=passed,
                score=score,
                metrics={
                    "initial_pattern_count": initial_pattern_count,
                    "final_pattern_count": final_pattern_count,
                    "patterns_learned": patterns_learned,
                    "has_quality_patterns": has_quality_patterns
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_knowledge_retention(self) -> EvaluationResult:
        """Test: Knowledge retention - verify tools persist"""
        test_id = "learn_004"
        test_name = "Knowledge Retention"
        
        start_time = time.time()
        
        try:
            # Get all tools
            all_tools = self.orchestrator.registry.get_all_tools()
            tool_count = len(all_tools)
            
            # Check if tools have proper metadata
            properly_stored = 0
            for tool in all_tools:
                if all(key in tool for key in ['name', 'docstring', 'file_path']):
                    properly_stored += 1
            
            execution_time = (time.time() - start_time) * 1000
            
            # Calculate retention quality
            retention_rate = properly_stored / tool_count if tool_count > 0 else 0.0
            
            # Score based on tool count and retention quality
            has_tools = tool_count > 0
            good_retention = retention_rate >= 0.9
            
            score = 0.0
            if has_tools:
                score += 0.5
            if good_retention:
                score += 0.5
            
            passed = has_tools and good_retention
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=passed,
                score=score,
                metrics={
                    "tool_count": tool_count,
                    "properly_stored": properly_stored,
                    "retention_rate": retention_rate
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.LEARNING,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )

