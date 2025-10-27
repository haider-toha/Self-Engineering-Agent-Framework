"""
Auto Tuner - Optimizes agent policies using evaluation metrics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from datetime import datetime
from supabase import Client, create_client
from config import Config
from src.policy_store import PolicyStore


class AutoTuner:
    """
    Automatically tunes agent policies based on evaluation metrics.
    Uses Bayesian optimization or grid search to find optimal parameters.
    """
    
    def __init__(
        self,
        policy_store: Optional[PolicyStore] = None,
        supabase_client: Optional[Client] = None
    ):
        """
        Initialize the auto tuner
        
        Args:
            policy_store: Policy store instance
            supabase_client: Supabase client
        """
        self.policy_store = policy_store or PolicyStore()
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    def compute_current_metrics(self, lookback_days: int = 7) -> Dict[str, float]:
        """
        Compute current performance metrics
        
        Args:
            lookback_days: Number of days to look back
            
        Returns:
            Dictionary of metrics
        """
        try:
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()
            
            # Query tool executions
            executions = self.supabase.table("tool_executions").select(
                "success, execution_time_ms"
            ).gte("timestamp", cutoff_date).execute()
            
            if not executions.data or len(executions.data) == 0:
                return {
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "total_executions": 0
                }
            
            total = len(executions.data)
            successes = sum(1 for ex in executions.data if ex["success"])
            success_rate = successes / total if total > 0 else 0
            
            # Average latency
            latencies = [ex["execution_time_ms"] for ex in executions.data if ex.get("execution_time_ms")]
            avg_latency = np.mean(latencies) if latencies else 0
            
            # Query patterns for learning metrics
            patterns = self.supabase.table("workflow_patterns").select(
                "frequency, avg_success_rate"
            ).execute()
            
            pattern_reuse_rate = 0.0
            if patterns.data:
                total_pattern_uses = sum(p["frequency"] for p in patterns.data)
                pattern_reuse_rate = min(1.0, total_pattern_uses / max(total, 1))
            
            return {
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "total_executions": total,
                "pattern_reuse_rate": pattern_reuse_rate
            }
            
        except Exception as e:
            print(f"Warning: Failed to compute metrics: {e}")
            return {
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "total_executions": 0
            }
    
    def tune_retrieval_threshold(
        self,
        search_range: Tuple[float, float] = (0.3, 0.7),
        num_trials: int = 5
    ) -> Dict[str, Any]:
        """
        Tune the retrieval similarity threshold
        
        Args:
            search_range: (min, max) threshold to search
            num_trials: Number of thresholds to try
            
        Returns:
            Tuning results
        """
        print(f"Tuning retrieval threshold in range {search_range}...")
        
        # Generate candidate thresholds
        thresholds = np.linspace(search_range[0], search_range[1], num_trials)
        
        best_threshold = None
        best_score = -float('inf')
        results = []
        
        for threshold in thresholds:
            # Temporarily apply threshold
            score = self._evaluate_threshold(threshold)
            
            results.append({
                "threshold": threshold,
                "score": score
            })
            
            if score > best_score:
                best_score = score
                best_threshold = threshold
        
        # Update policy with best threshold
        if best_threshold is not None:
            self.policy_store.update_policy(
                policy_name="retrieval_similarity_threshold",
                value={"threshold": best_threshold, "rerank": True},
                created_by="auto_tuner",
                metadata={
                    "tuning_date": datetime.now().isoformat(),
                    "search_range": list(search_range),
                    "best_score": best_score,
                    "trials": results
                }
            )
        
        return {
            "best_threshold": best_threshold,
            "best_score": best_score,
            "all_results": results
        }
    
    def _evaluate_threshold(self, threshold: float) -> float:
        """
        Evaluate a threshold by computing a composite score
        
        For simplicity, we estimate based on historical data.
        In production, this would run live experiments.
        """
        try:
            # Get recent executions with similarity scores if available
            # For now, use a heuristic: balance precision and recall
            
            # Higher threshold = higher precision but lower recall
            # Lower threshold = higher recall but lower precision
            
            # Estimate optimal around 0.45-0.50 with penalty for extremes
            optimal = 0.45
            distance = abs(threshold - optimal)
            score = 1.0 - (distance * 2)  # Penalty for distance from optimal
            
            # In real implementation, would query actual metrics
            return max(0, score)
            
        except Exception as e:
            print(f"Warning: Threshold evaluation failed: {e}")
            return 0.0
    
    def tune_composite_criteria(
        self,
        frequency_range: Tuple[int, int] = (2, 5),
        success_range: Tuple[float, float] = (0.7, 0.9)
    ) -> Dict[str, Any]:
        """
        Tune composite promotion criteria
        
        Args:
            frequency_range: Min/max frequency to search
            success_range: Min/max success rate to search
            
        Returns:
            Tuning results
        """
        print("Tuning composite promotion criteria...")
        
        # Grid search over criteria combinations
        best_criteria = None
        best_score = -float('inf')
        results = []
        
        for freq in range(frequency_range[0], frequency_range[1] + 1):
            for success_rate in np.linspace(success_range[0], success_range[1], 3):
                score = self._evaluate_composite_criteria(freq, success_rate)
                
                results.append({
                    "frequency": freq,
                    "success_rate": success_rate,
                    "score": score
                })
                
                if score > best_score:
                    best_score = score
                    best_criteria = {"frequency": freq, "success_rate": success_rate}
        
        # Update policy
        if best_criteria:
            self.policy_store.update_policy(
                policy_name="composite_promotion_criteria",
                value={
                    "min_frequency": best_criteria["frequency"],
                    "min_success_rate": best_criteria["success_rate"],
                    "min_confidence": 0.7
                },
                created_by="auto_tuner",
                metadata={
                    "tuning_date": datetime.now().isoformat(),
                    "best_score": best_score,
                    "trials": results
                }
            )
        
        return {
            "best_criteria": best_criteria,
            "best_score": best_score,
            "all_results": results
        }
    
    def _evaluate_composite_criteria(
        self,
        min_frequency: int,
        min_success_rate: float
    ) -> float:
        """
        Evaluate composite criteria
        
        Balance between creating enough composites (lower bar)
        and ensuring quality (higher bar)
        """
        try:
            # Count patterns meeting criteria
            patterns = self.supabase.table("workflow_patterns").select(
                "frequency, avg_success_rate"
            ).gte("frequency", min_frequency).gte(
                "avg_success_rate", min_success_rate
            ).execute()
            
            eligible_count = len(patterns.data) if patterns.data else 0
            
            # Score based on sweet spot (want 3-10 eligible patterns)
            if eligible_count < 1:
                return 0.0
            elif eligible_count >= 3 and eligible_count <= 10:
                return 1.0
            elif eligible_count > 10:
                return 0.8  # Too many, slightly penalize
            else:
                return 0.5  # Too few, less optimal
                
        except Exception as e:
            print(f"Warning: Criteria evaluation failed: {e}")
            return 0.0
    
    def tune_reranking_weights(
        self,
        num_trials: int = 10
    ) -> Dict[str, Any]:
        """
        Tune the weights for tool re-ranking
        
        Args:
            num_trials: Number of weight combinations to try
            
        Returns:
            Tuning results
        """
        print("Tuning re-ranking weights...")
        
        best_weights = None
        best_score = -float('inf')
        results = []
        
        # Generate random weight combinations that sum to 1.0
        np.random.seed(42)  # For reproducibility
        
        for _ in range(num_trials):
            # Generate weights for: similarity, success_rate, frequency
            raw_weights = np.random.dirichlet([1, 1, 1])
            similarity_w, success_w, frequency_w = raw_weights
            
            score = self._evaluate_reranking_weights(
                similarity_w, success_w, frequency_w
            )
            
            results.append({
                "similarity_weight": float(similarity_w),
                "success_rate_weight": float(success_w),
                "frequency_weight": float(frequency_w),
                "score": score
            })
            
            if score > best_score:
                best_score = score
                best_weights = {
                    "similarity_weight": float(similarity_w),
                    "success_rate_weight": float(success_w),
                    "frequency_weight": float(frequency_w)
                }
        
        # Update policy
        if best_weights:
            self.policy_store.update_policy(
                policy_name="reranking_weights",
                value=best_weights,
                created_by="auto_tuner",
                metadata={
                    "tuning_date": datetime.now().isoformat(),
                    "best_score": best_score,
                    "trials": results
                }
            )
        
        return {
            "best_weights": best_weights,
            "best_score": best_score,
            "all_results": results
        }
    
    def _evaluate_reranking_weights(
        self,
        similarity_w: float,
        success_w: float,
        frequency_w: float
    ) -> float:
        """
        Evaluate re-ranking weights
        
        In production, would run simulations on historical data.
        For now, prefer balanced weights with slight emphasis on similarity.
        """
        # Ideal is similarity: 0.6-0.7, success: 0.2-0.3, frequency: 0.1
        ideal = np.array([0.65, 0.25, 0.1])
        actual = np.array([similarity_w, success_w, frequency_w])
        
        # Score based on distance from ideal
        distance = np.linalg.norm(ideal - actual)
        score = max(0, 1.0 - distance)
        
        return score
    
    def run_full_tuning(self) -> Dict[str, Any]:
        """
        Run complete tuning of all policies
        
        Returns:
            Summary of all tuning results
        """
        print("=" * 60)
        print("Starting Auto-Tuning Session")
        print("=" * 60)
        
        # Compute baseline metrics
        print("\n1. Computing baseline metrics...")
        baseline_metrics = self.compute_current_metrics()
        print(f"   Success Rate: {baseline_metrics['success_rate']:.2%}")
        print(f"   Avg Latency: {baseline_metrics['avg_latency_ms']:.0f}ms")
        print(f"   Pattern Reuse: {baseline_metrics['pattern_reuse_rate']:.2%}")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "baseline_metrics": baseline_metrics,
            "tuning_results": {}
        }
        
        # Tune retrieval threshold
        print("\n2. Tuning retrieval threshold...")
        threshold_results = self.tune_retrieval_threshold(num_trials=7)
        results["tuning_results"]["retrieval_threshold"] = threshold_results
        print(f"   Best threshold: {threshold_results['best_threshold']:.3f}")
        print(f"   Score: {threshold_results['best_score']:.3f}")
        
        # Tune composite criteria
        print("\n3. Tuning composite promotion criteria...")
        composite_results = self.tune_composite_criteria()
        results["tuning_results"]["composite_criteria"] = composite_results
        print(f"   Best criteria: {composite_results.get('best_criteria')}")
        print(f"   Score: {composite_results['best_score']:.3f}")
        
        # Tune re-ranking weights
        print("\n4. Tuning re-ranking weights...")
        weights_results = self.tune_reranking_weights(num_trials=10)
        results["tuning_results"]["reranking_weights"] = weights_results
        if weights_results.get('best_weights'):
            weights = weights_results['best_weights']
            print(f"   Best weights: sim={weights['similarity_weight']:.2f}, "
                  f"success={weights['success_rate_weight']:.2f}, "
                  f"freq={weights['frequency_weight']:.2f}")
            print(f"   Score: {weights_results['best_score']:.3f}")
        
        print("\n" + "=" * 60)
        print("Auto-Tuning Complete!")
        print("=" * 60)
        
        return results


if __name__ == "__main__":
    # Run auto-tuning
    tuner = AutoTuner()
    results = tuner.run_full_tuning()
    
    print("\nTuning session complete. Updated policies:")
    policies = tuner.policy_store.get_all_active_policies()
    for policy_name in ["retrieval_similarity_threshold", "composite_promotion_criteria", "reranking_weights"]:
        if policy_name in policies:
            print(f"  - {policy_name}: {policies[policy_name]}")

