"""
Comprehensive Evaluation Framework for Self-Engineering Agent

This framework evaluates the agent across multiple dimensions using ML-inspired methods:
1. Functional Correctness
2. Synthesis Quality 
3. Tool Retrieval Performance
4. Workflow Execution
5. Learning & Adaptation
6. Robustness & Edge Cases
7. Performance & Efficiency
"""

import time
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class MetricCategory(Enum):
    """Categories of evaluation metrics"""
    FUNCTIONAL = "functional"
    SYNTHESIS = "synthesis"
    RETRIEVAL = "retrieval"
    WORKFLOW = "workflow"
    LEARNING = "learning"
    ROBUSTNESS = "robustness"
    PERFORMANCE = "performance"


@dataclass
class EvaluationResult:
    """Result of a single evaluation test"""
    test_id: str
    test_name: str
    category: MetricCategory
    passed: bool
    score: float  # 0.0 to 1.0
    metrics: Dict[str, Any]
    execution_time_ms: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['category'] = self.category.value
        return result


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across all tests"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    average_score: float
    category_scores: Dict[str, float]
    total_execution_time_ms: float
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class EvaluationMetrics:
    """
    Core metrics computation for agent evaluation.
    Inspired by ML evaluation practices:
    - Precision, Recall, F1 for retrieval
    - Success Rate for functional tasks
    - Perplexity-like metrics for synthesis quality
    - Learning curves for adaptation
    """
    
    @staticmethod
    def precision(true_positives: int, false_positives: int) -> float:
        """Calculate precision"""
        total = true_positives + false_positives
        return true_positives / total if total > 0 else 0.0
    
    @staticmethod
    def recall(true_positives: int, false_negatives: int) -> float:
        """Calculate recall"""
        total = true_positives + false_negatives
        return true_positives / total if total > 0 else 0.0
    
    @staticmethod
    def f1_score(precision: float, recall: float) -> float:
        """Calculate F1 score"""
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)
    
    @staticmethod
    def accuracy(correct: int, total: int) -> float:
        """Calculate accuracy"""
        return correct / total if total > 0 else 0.0
    
    @staticmethod
    def mean_reciprocal_rank(ranks: List[int]) -> float:
        """
        Calculate Mean Reciprocal Rank (MRR)
        Used for retrieval quality - measures how high the correct result ranks
        """
        if not ranks:
            return 0.0
        reciprocals = [1.0 / rank for rank in ranks if rank > 0]
        return np.mean(reciprocals) if reciprocals else 0.0
    
    @staticmethod
    def normalized_discounted_cumulative_gain(relevances: List[float], k: int = 10) -> float:
        """
        Calculate NDCG@k
        Measures ranking quality for retrieval systems
        """
        if not relevances:
            return 0.0
        
        # DCG
        dcg = relevances[0] + sum(
            rel / np.log2(i + 2) for i, rel in enumerate(relevances[1:k])
        )
        
        # IDCG (ideal DCG)
        sorted_relevances = sorted(relevances, reverse=True)
        idcg = sorted_relevances[0] + sum(
            rel / np.log2(i + 2) for i, rel in enumerate(sorted_relevances[1:k])
        )
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings
        Used for code similarity evaluation
        """
        if len(s1) < len(s2):
            return EvaluationMetrics.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def code_similarity(code1: str, code2: str) -> float:
        """
        Calculate normalized similarity between two code snippets
        Returns value between 0.0 and 1.0
        """
        distance = EvaluationMetrics.levenshtein_distance(code1, code2)
        max_len = max(len(code1), len(code2))
        return 1.0 - (distance / max_len) if max_len > 0 else 1.0
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = np.sqrt(sum(a * a for a in vec1))
        magnitude2 = np.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


class EvaluationFramework:
    """
    Main evaluation framework for the Self-Engineering Agent.
    Orchestrates all evaluation tests and aggregates results.
    """
    
    def __init__(self, orchestrator=None, results_dir: str = "./evaluation/results"):
        """
        Initialize the evaluation framework
        
        Args:
            orchestrator: AgentOrchestrator instance to evaluate
            results_dir: Directory to save evaluation results
        """
        self.orchestrator = orchestrator
        self.results_dir = results_dir
        self.results: List[EvaluationResult] = []
        self.start_time = None
        self.end_time = None
        
        # Create results directory
        import os
        os.makedirs(results_dir, exist_ok=True)
    
    def run_evaluation(
        self,
        test_suite: Optional[List[str]] = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        Run complete evaluation suite
        
        Args:
            test_suite: List of test categories to run (None = all)
            save_results: Whether to save results to disk
            
        Returns:
            Dictionary with aggregated results
        """
        self.start_time = time.time()
        self.results = []
        
        print("=" * 80)
        print("STARTING COMPREHENSIVE AGENT EVALUATION")
        print("=" * 80)
        
        # Determine which test suites to run
        all_suites = [
            MetricCategory.FUNCTIONAL,
            MetricCategory.SYNTHESIS,
            MetricCategory.RETRIEVAL,
            MetricCategory.WORKFLOW,
            MetricCategory.LEARNING,
            MetricCategory.ROBUSTNESS,
            MetricCategory.PERFORMANCE
        ]
        
        suites_to_run = all_suites if not test_suite else [
            cat for cat in all_suites if cat.value in test_suite
        ]
        
        # Run each test suite
        for category in suites_to_run:
            print(f"\n{'=' * 80}")
            print(f"Running {category.value.upper()} Tests")
            print(f"{'=' * 80}")
            
            suite_results = self._run_test_category(category)
            self.results.extend(suite_results)
            
            # Print category summary
            passed = sum(1 for r in suite_results if r.passed)
            total = len(suite_results)
            avg_score = np.mean([r.score for r in suite_results]) if suite_results else 0.0
            
            print(f"\n{category.value.upper()} Summary:")
            print(f"  Passed: {passed}/{total}")
            print(f"  Average Score: {avg_score:.3f}")
        
        self.end_time = time.time()
        
        # Aggregate results
        aggregated = self._aggregate_results()
        
        # Print final summary
        self._print_summary(aggregated)
        
        # Save results
        if save_results:
            self._save_results(aggregated)
        
        return aggregated
    
    def _run_test_category(self, category: MetricCategory) -> List[EvaluationResult]:
        """Run all tests for a specific category"""
        results = []
        
        # Import test modules dynamically
        if category == MetricCategory.FUNCTIONAL:
            from evaluation.tests.test_functional import FunctionalTests
            tests = FunctionalTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.SYNTHESIS:
            from evaluation.tests.test_synthesis import SynthesisTests
            tests = SynthesisTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.RETRIEVAL:
            from evaluation.tests.test_retrieval import RetrievalTests
            tests = RetrievalTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.WORKFLOW:
            from evaluation.tests.test_workflow import WorkflowTests
            tests = WorkflowTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.LEARNING:
            from evaluation.tests.test_learning import LearningTests
            tests = LearningTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.ROBUSTNESS:
            from evaluation.tests.test_robustness import RobustnessTests
            tests = RobustnessTests(self.orchestrator)
            results = tests.run_all()
        
        elif category == MetricCategory.PERFORMANCE:
            from evaluation.tests.test_performance import PerformanceTests
            tests = PerformanceTests(self.orchestrator)
            results = tests.run_all()
        
        return results
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """Aggregate all evaluation results"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        average_score = np.mean([r.score for r in self.results]) if self.results else 0.0
        
        # Calculate category-wise scores
        category_scores = {}
        for category in MetricCategory:
            cat_results = [r for r in self.results if r.category == category]
            if cat_results:
                category_scores[category.value] = np.mean([r.score for r in cat_results])
            else:
                category_scores[category.value] = None
        
        total_time = (self.end_time - self.start_time) * 1000 if self.end_time else 0.0
        
        metrics = AggregatedMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            pass_rate=pass_rate,
            average_score=average_score,
            category_scores=category_scores,
            total_execution_time_ms=total_time,
            timestamp=datetime.now().isoformat()
        )
        
        return {
            "summary": metrics.to_dict(),
            "detailed_results": [r.to_dict() for r in self.results]
        }
    
    def _print_summary(self, aggregated: Dict[str, Any]):
        """Print evaluation summary"""
        summary = aggregated['summary']
        
        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Pass Rate: {summary['pass_rate']:.1%}")
        print(f"Average Score: {summary['average_score']:.3f}")
        print(f"Total Time: {summary['total_execution_time_ms']:.2f}ms")
        
        print("\nCategory Scores:")
        for category, score in summary['category_scores'].items():
            if score is not None:
                print(f"  {category.capitalize()}: {score:.3f}")
            else:
                print(f"  {category.capitalize()}: N/A")
        
        print("\n" + "=" * 80)
    
    def _save_results(self, aggregated: Dict[str, Any]):
        """Save evaluation results to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.results_dir}/evaluation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(aggregated, f, indent=2)
        
        print(f"\nResults saved to: {filename}")
    
    def compare_runs(self, run1_path: str, run2_path: str) -> Dict[str, Any]:
        """
        Compare two evaluation runs
        
        Args:
            run1_path: Path to first evaluation results
            run2_path: Path to second evaluation results
            
        Returns:
            Comparison metrics
        """
        with open(run1_path, 'r') as f:
            run1 = json.load(f)
        
        with open(run2_path, 'r') as f:
            run2 = json.load(f)
        
        comparison = {
            "run1": {
                "timestamp": run1['summary']['timestamp'],
                "pass_rate": run1['summary']['pass_rate'],
                "average_score": run1['summary']['average_score']
            },
            "run2": {
                "timestamp": run2['summary']['timestamp'],
                "pass_rate": run2['summary']['pass_rate'],
                "average_score": run2['summary']['average_score']
            },
            "improvements": {
                "pass_rate_delta": run2['summary']['pass_rate'] - run1['summary']['pass_rate'],
                "score_delta": run2['summary']['average_score'] - run1['summary']['average_score']
            },
            "category_comparison": {}
        }
        
        # Compare category scores
        for category in MetricCategory:
            cat_name = category.value
            score1 = run1['summary']['category_scores'].get(cat_name)
            score2 = run2['summary']['category_scores'].get(cat_name)
            
            if score1 is not None and score2 is not None:
                comparison['category_comparison'][cat_name] = {
                    "run1": score1,
                    "run2": score2,
                    "delta": score2 - score1
                }
        
        return comparison


if __name__ == "__main__":
    print("Evaluation Framework Module Loaded")
    print("Import this module and use EvaluationFramework class to run evaluations")

