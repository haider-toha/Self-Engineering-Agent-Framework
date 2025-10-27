"""
Policy Store - Manages versioned configuration and auto-tuning parameters
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from supabase import Client, create_client
from config import Config


class PolicyStore:
    """
    Manages agent policies with versioning and A/B testing support.
    Policies control behavior like retrieval thresholds, planning strategies,
    cost limits, and other tunable parameters.
    """
    
    # Default policy values
    DEFAULT_POLICIES = {
        "retrieval_similarity_threshold": {
            "type": "retrieval_threshold",
            "value": {"threshold": 0.4, "rerank": True}
        },
        "composite_promotion_criteria": {
            "type": "planner_config",
            "value": {
                "min_frequency": 3,
                "min_success_rate": 0.8,
                "min_confidence": 0.7
            }
        },
        "workflow_complexity_thresholds": {
            "type": "planner_config",
            "value": {
                "simple_max_tools": 1,
                "sequential_max_tools": 3,
                "requires_synthesis_threshold": 5
            }
        },
        "cost_limits": {
            "type": "cost_limit",
            "value": {
                "max_tokens_per_request": 10000,
                "max_synthesis_attempts": 3,
                "max_llm_calls_per_request": 20
            }
        },
        "cache_ttl": {
            "type": "performance",
            "value": {"ttl_seconds": 3600, "enabled": True}
        },
        "reranking_weights": {
            "type": "retrieval_threshold",
            "value": {
                "similarity_weight": 0.7,
                "success_rate_weight": 0.2,
                "frequency_weight": 0.1
            }
        }
    }
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize the policy store
        
        Args:
            supabase_client: Supabase client instance (optional)
        """
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self._ensure_default_policies()
    
    def _ensure_default_policies(self):
        """Ensure default policies exist in database"""
        try:
            for policy_name, policy_config in self.DEFAULT_POLICIES.items():
                # Check if policy exists
                result = self.supabase.table("agent_policies").select("*").eq(
                    "policy_name", policy_name
                ).eq("is_active", True).execute()
                
                if not result.data:
                    # Create default policy
                    self.supabase.table("agent_policies").insert({
                        "policy_name": policy_name,
                        "policy_type": policy_config["type"],
                        "value": policy_config["value"],
                        "created_by": "system",
                        "is_active": True
                    }).execute()
        except Exception as e:
            print(f"Warning: Failed to ensure default policies: {e}")
    
    def get_policy(self, policy_name: str, default: Any = None) -> Any:
        """
        Get the current active value of a policy
        
        Args:
            policy_name: Name of the policy
            default: Default value if policy not found
            
        Returns:
            Policy value (typically a dict)
        """
        try:
            result = self.supabase.rpc("get_policy", {"p_policy_name": policy_name}).execute()
            
            if result.data:
                return result.data
            
            # Fallback to default policies
            if policy_name in self.DEFAULT_POLICIES:
                return self.DEFAULT_POLICIES[policy_name]["value"]
            
            return default
            
        except Exception as e:
            print(f"Warning: Failed to get policy '{policy_name}': {e}")
            # Return from default policies if available
            if policy_name in self.DEFAULT_POLICIES:
                return self.DEFAULT_POLICIES[policy_name]["value"]
            return default
    
    def update_policy(
        self,
        policy_name: str,
        value: Dict[str, Any],
        policy_type: Optional[str] = None,
        created_by: str = "auto_tuner",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Update a policy with a new value (creates new version)
        
        Args:
            policy_name: Name of the policy
            value: New policy value
            policy_type: Policy type (optional, inferred if existing)
            created_by: Who/what updated this policy
            metadata: Additional context about the update
            
        Returns:
            Policy ID
        """
        # If policy type not provided, try to infer from defaults or existing
        if not policy_type:
            if policy_name in self.DEFAULT_POLICIES:
                policy_type = self.DEFAULT_POLICIES[policy_name]["type"]
            else:
                policy_type = "custom"
        
        try:
            result = self.supabase.rpc(
                "update_policy",
                {
                    "p_policy_name": policy_name,
                    "p_policy_type": policy_type,
                    "p_value": json.dumps(value),
                    "p_created_by": created_by
                }
            ).execute()
            
            # Add metadata if provided
            if metadata and result.data:
                self.supabase.table("agent_policies").update({
                    "metadata": metadata
                }).eq("id", result.data).execute()
            
            return result.data
            
        except Exception as e:
            raise Exception(f"Failed to update policy '{policy_name}': {e}")
    
    def get_policy_history(
        self,
        policy_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get version history for a policy
        
        Args:
            policy_name: Name of the policy
            limit: Maximum number of versions to return
            
        Returns:
            List of policy versions
        """
        try:
            result = self.supabase.table("agent_policies").select("*").eq(
                "policy_name", policy_name
            ).order("version", desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Warning: Failed to get policy history for '{policy_name}': {e}")
            return []
    
    def rollback_policy(self, policy_name: str, version: int) -> bool:
        """
        Rollback a policy to a previous version
        
        Args:
            policy_name: Name of the policy
            version: Version number to rollback to
            
        Returns:
            True if successful
        """
        try:
            # Get the old version
            result = self.supabase.table("agent_policies").select("*").eq(
                "policy_name", policy_name
            ).eq("version", version).execute()
            
            if not result.data:
                return False
            
            old_policy = result.data[0]
            
            # Create new version with old value
            self.update_policy(
                policy_name=policy_name,
                value=old_policy["value"],
                policy_type=old_policy["policy_type"],
                created_by="rollback",
                metadata={"rollback_from_version": version}
            )
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to rollback policy '{policy_name}': {e}")
            return False
    
    def get_all_active_policies(self) -> Dict[str, Any]:
        """
        Get all currently active policies
        
        Returns:
            Dictionary mapping policy names to values
        """
        try:
            result = self.supabase.table("agent_policies").select(
                "policy_name, value"
            ).eq("is_active", True).execute()
            
            if result.data:
                return {p["policy_name"]: p["value"] for p in result.data}
            
            return {}
            
        except Exception as e:
            print(f"Warning: Failed to get all active policies: {e}")
            return {}
    
    def create_ab_experiment(
        self,
        experiment_name: str,
        variant_a_policy: Dict[str, Any],
        variant_b_policy: Dict[str, Any],
        metric_name: str,
        traffic_split: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an A/B test experiment for policy optimization
        
        Args:
            experiment_name: Name of the experiment
            variant_a_policy: Policy configuration for variant A
            variant_b_policy: Policy configuration for variant B
            metric_name: Metric to optimize (e.g., 'success_rate', 'avg_latency')
            traffic_split: Fraction of traffic to variant A (0.0-1.0)
            metadata: Additional experiment context
            
        Returns:
            Experiment ID
        """
        try:
            result = self.supabase.table("ab_experiments").insert({
                "experiment_name": experiment_name,
                "variant_a_policy": variant_a_policy,
                "variant_b_policy": variant_b_policy,
                "metric_name": metric_name,
                "traffic_split": traffic_split,
                "is_active": True,
                "metadata": metadata or {}
            }).execute()
            
            return result.data[0]["id"] if result.data else None
            
        except Exception as e:
            raise Exception(f"Failed to create A/B experiment: {e}")
    
    def get_experiment_variant(self, experiment_name: str, session_id: str) -> str:
        """
        Determine which variant to use for a given session (deterministic)
        
        Args:
            experiment_name: Name of the experiment
            session_id: Session identifier
            
        Returns:
            'a' or 'b'
        """
        try:
            # Get experiment
            result = self.supabase.table("ab_experiments").select("*").eq(
                "experiment_name", experiment_name
            ).eq("is_active", True).execute()
            
            if not result.data:
                return 'a'  # Default to variant A
            
            experiment = result.data[0]
            traffic_split = experiment.get("traffic_split", 0.5)
            
            # Deterministic assignment based on session_id hash
            hash_value = hash(session_id) % 100
            return 'a' if hash_value < (traffic_split * 100) else 'b'
            
        except Exception as e:
            print(f"Warning: Failed to get experiment variant: {e}")
            return 'a'
    
    def record_experiment_result(
        self,
        experiment_name: str,
        variant: str,
        metric_value: float
    ):
        """
        Record a result for an A/B experiment
        
        Args:
            experiment_name: Name of the experiment
            variant: 'a' or 'b'
            metric_value: Value of the metric being optimized
        """
        try:
            # Get experiment
            result = self.supabase.table("ab_experiments").select("*").eq(
                "experiment_name", experiment_name
            ).eq("is_active", True).execute()
            
            if not result.data:
                return
            
            experiment = result.data[0]
            
            # Update running average for the variant
            if variant == 'a':
                current = experiment.get("variant_a_metric", metric_value)
                new_value = (current + metric_value) / 2  # Simple average
                self.supabase.table("ab_experiments").update({
                    "variant_a_metric": new_value
                }).eq("id", experiment["id"]).execute()
            else:
                current = experiment.get("variant_b_metric", metric_value)
                new_value = (current + metric_value) / 2
                self.supabase.table("ab_experiments").update({
                    "variant_b_metric": new_value
                }).eq("id", experiment["id"]).execute()
                
        except Exception as e:
            print(f"Warning: Failed to record experiment result: {e}")


if __name__ == "__main__":
    # Test the policy store
    store = PolicyStore()
    
    # Get a policy
    threshold = store.get_policy("retrieval_similarity_threshold")
    print(f"Current similarity threshold: {threshold}")
    
    # Get all policies
    all_policies = store.get_all_active_policies()
    print(f"\nAll active policies: {list(all_policies.keys())}")

