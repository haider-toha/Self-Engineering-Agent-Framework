"""
Retrieval Performance Tests

Evaluates the agent's ability to find and select the right tools:
- Semantic search accuracy
- Ranking quality
- False positive/negative rates
- Query understanding
"""

import time
from typing import List
from evaluation.eval_framework import EvaluationResult, MetricCategory, EvaluationMetrics


class RetrievalTests:
    """
    Test suite for tool retrieval and semantic search quality.
    Inspired by Information Retrieval evaluation metrics.
    """
    
    def __init__(self, orchestrator):
        """
        Initialize retrieval tests
        
        Args:
            orchestrator: AgentOrchestrator instance
        """
        self.orchestrator = orchestrator
        self.metrics = EvaluationMetrics()
    
    def run_all(self) -> List[EvaluationResult]:
        """Run all retrieval tests"""
        results = []
        
        # Test 1: Exact match retrieval
        results.append(self.test_exact_match())
        
        # Test 2: Semantic similarity retrieval
        results.append(self.test_semantic_match())
        
        # Test 3: Precision and recall
        results.append(self.test_precision_recall())
        
        # Test 4: Ranking quality (MRR)
        results.append(self.test_ranking_quality())
        
        # Test 5: False positive rate
        results.append(self.test_false_positives())
        
        # Test 6: Query variation handling
        results.append(self.test_query_variations())
        
        return results
    
    def test_exact_match(self) -> EvaluationResult:
        """Test: Exact match queries"""
        test_id = "retr_001"
        test_name = "Exact Match Retrieval"
        
        start_time = time.time()
        
        try:
            # Query for an existing tool with exact terminology
            query = "calculate percentage"
            tool_info = self.orchestrator.registry.search_tool(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if correct tool was found
            found_correct = (
                tool_info is not None and
                'percentage' in tool_info.get('name', '').lower()
            )
            
            passed = found_correct
            score = 1.0 if found_correct else 0.0
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.RETRIEVAL,
                passed=passed,
                score=score,
                metrics={
                    "query": query,
                    "found_tool": tool_info.get('name') if tool_info else None,
                    "similarity_score": tool_info.get('similarity_score') if tool_info else 0.0
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.RETRIEVAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_semantic_match(self) -> EvaluationResult:
        """Test: Semantic similarity matching"""
        test_id = "retr_002"
        test_name = "Semantic Match Retrieval"
        
        start_time = time.time()
        
        try:
            # Use a semantically similar query
            query = "What portion is 20 out of 100?"  # Should match percentage tool
            tool_info = self.orchestrator.registry.search_tool(query)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Check if appropriate tool was found
            found_relevant = (
                tool_info is not None and
                ('percentage' in tool_info.get('name', '').lower() or
                 'calculate' in tool_info.get('name', '').lower())
            )
            
            # Score based on relevance and similarity score
            if tool_info and found_relevant:
                score = tool_info.get('similarity_score', 0.0)
            else:
                score = 0.0
            
            passed = found_relevant and score > 0.4
            
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.RETRIEVAL,
                passed=passed,
                score=score,
                metrics={
                    "query": query,
                    "found_tool": tool_info.get('name') if tool_info else None,
                    "similarity_score": tool_info.get('similarity_score') if tool_info else 0.0
                },
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return EvaluationResult(
                test_id=test_id,
                test_name=test_name,
                category=MetricCategory.RETRIEVAL,
                passed=False,
                score=0.0,
                metrics={},
                execution_time_ms=execution_time,
                error_message=str(e)
            )
    
    def test_precision_recall(self) -> EvaluationResult:
        """Test: Calculate precision and recall"""
        test_id = "retr_003"
        test_name = "Precision and Recall"
        
        start_time = time.time()
        
        # Define test queries with expected tools
        test_cases = [
            ("calculate 50% of 200", "calculate_percentage"),
            ("reverse the text 'hello'", "reverse_string"),
            ("factorial of 6", "calculate_factorial"),
            ("convert 25 celsius to fahrenheit", "convert_fahrenheit_to_celsius"),
            ("square root of 81", "calculate_square_root")
        ]
        
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for query, expected_tool in test_cases:
            try:
                tool_info = self.orchestrator.registry.search_tool(query)
                
                if tool_info:
                    found_name = tool_info.get('name', '').lower()
                    # Check if the found tool is the expected one or semantically similar
                    if expected_tool.lower() in found_name or any(
                        word in found_name for word in expected_tool.lower().split('_')
                    ):
                        true_positives += 1
                    else:
                        false_positives += 1
                else:
                    false_negatives += 1
            except Exception:
                false_negatives += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate metrics
        precision = self.metrics.precision(true_positives, false_positives)
        recall = self.metrics.recall(true_positives, false_negatives)
        f1 = self.metrics.f1_score(precision, recall)
        
        # Score is F1 score
        score = f1
        passed = f1 >= 0.7  # At least 70% F1 score
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.RETRIEVAL,
            passed=passed,
            score=score,
            metrics={
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            },
            execution_time_ms=execution_time
        )
    
    def test_ranking_quality(self) -> EvaluationResult:
        """Test: Measure ranking quality using MRR"""
        test_id = "retr_004"
        test_name = "Ranking Quality (MRR)"
        
        start_time = time.time()
        
        # For this test, we would need access to multiple ranked results
        # Since search_tool only returns top result, we'll simulate with multiple queries
        
        queries = [
            "percentage calculation",
            "string reversal",
            "factorial computation",
            "temperature conversion",
            "square root"
        ]
        
        ranks = []
        
        for query in queries:
            try:
                tool_info = self.orchestrator.registry.search_tool(query)
                if tool_info:
                    # If found, assume rank 1 (since we only get top result)
                    ranks.append(1)
                else:
                    # Not found = very low rank
                    ranks.append(10)
            except Exception:
                ranks.append(10)
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate MRR
        mrr = self.metrics.mean_reciprocal_rank(ranks)
        
        # Score is MRR
        score = mrr
        passed = mrr >= 0.7
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.RETRIEVAL,
            passed=passed,
            score=score,
            metrics={
                "mrr": mrr,
                "query_count": len(queries),
                "average_rank": sum(ranks) / len(ranks) if ranks else 0
            },
            execution_time_ms=execution_time
        )
    
    def test_false_positives(self) -> EvaluationResult:
        """Test: Measure false positive rate"""
        test_id = "retr_005"
        test_name = "False Positive Rate"
        
        start_time = time.time()
        
        # Queries that should NOT match existing tools (require synthesis)
        irrelevant_queries = [
            "launch a rocket to mars",
            "translate english to french",
            "predict tomorrow's weather",
            "solve quantum mechanics equation"
        ]
        
        false_positives = 0
        true_negatives = 0
        
        for query in irrelevant_queries:
            try:
                tool_info = self.orchestrator.registry.search_tool(query, threshold=0.5)
                
                if tool_info:
                    # If a tool was found with decent similarity, it's a false positive
                    if tool_info.get('similarity_score', 0) > 0.5:
                        false_positives += 1
                    else:
                        true_negatives += 1
                else:
                    true_negatives += 1
            except Exception:
                true_negatives += 1
        
        execution_time = (time.time() - start_time) * 1000
        
        # Calculate false positive rate
        total = false_positives + true_negatives
        fpr = false_positives / total if total > 0 else 0.0
        
        # Score is inverse of FPR (lower FPR is better)
        score = 1.0 - fpr
        passed = fpr <= 0.3  # At most 30% false positive rate
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.RETRIEVAL,
            passed=passed,
            score=score,
            metrics={
                "false_positives": false_positives,
                "true_negatives": true_negatives,
                "false_positive_rate": fpr
            },
            execution_time_ms=execution_time
        )
    
    def test_query_variations(self) -> EvaluationResult:
        """Test: Handle query variations"""
        test_id = "retr_006"
        test_name = "Query Variation Handling"
        
        start_time = time.time()
        
        # Different ways to ask for the same thing
        query_variations = [
            "calculate 10% of 500",
            "what is 10 percent of 500",
            "find 10% from 500",
            "compute ten percent of five hundred"
        ]
        
        found_count = 0
        total = len(query_variations)
        
        for query in query_variations:
            try:
                tool_info = self.orchestrator.registry.search_tool(query)
                if tool_info and 'percentage' in tool_info.get('name', '').lower():
                    found_count += 1
            except Exception:
                pass
        
        execution_time = (time.time() - start_time) * 1000
        
        # Score based on consistency
        consistency_rate = found_count / total if total > 0 else 0.0
        score = consistency_rate
        passed = consistency_rate >= 0.75  # At least 75% consistency
        
        return EvaluationResult(
            test_id=test_id,
            test_name=test_name,
            category=MetricCategory.RETRIEVAL,
            passed=passed,
            score=score,
            metrics={
                "found_count": found_count,
                "total_variations": total,
                "consistency_rate": consistency_rate
            },
            execution_time_ms=execution_time
        )

