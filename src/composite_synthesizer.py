"""
Composite Synthesizer - Automatically creates composite tools from high-confidence patterns
"""

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from supabase import Client, create_client
from config import Config
from src.llm_client import LLMClient
from src.sandbox import SecureSandbox
from src.capability_registry import CapabilityRegistry
from src.policy_store import PolicyStore


class CompositeSynthesizer:
    """
    Detects high-confidence workflow patterns and promotes them to
    first-class composite tools with comprehensive testing.
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        sandbox: Optional[SecureSandbox] = None,
        registry: Optional[CapabilityRegistry] = None,
        policy_store: Optional[PolicyStore] = None,
        supabase_client: Optional[Client] = None
    ):
        """
        Initialize the composite synthesizer
        
        Args:
            llm_client: LLM client for code generation
            sandbox: Sandbox for verification
            registry: Capability registry
            policy_store: Policy store for criteria
            supabase_client: Supabase client
        """
        self.llm_client = llm_client or LLMClient()
        self.sandbox = sandbox or SecureSandbox()
        self.registry = registry or CapabilityRegistry()
        self.policy_store = policy_store or PolicyStore()
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    def scan_for_candidates(self) -> List[Dict[str, Any]]:
        """
        Scan workflow patterns for composite tool candidates
        
        Returns:
            List of candidate patterns
        """
        # Get promotion criteria from policy store
        criteria = self.policy_store.get_policy(
            "composite_promotion_criteria",
            default={
                "min_frequency": 3,
                "min_success_rate": 0.8,
                "min_confidence": 0.7
            }
        )
        
        min_frequency = criteria.get("min_frequency", 3)
        min_success_rate = criteria.get("min_success_rate", 0.8)
        min_confidence = criteria.get("min_confidence", 0.7)
        
        try:
            # Query patterns meeting criteria
            result = self.supabase.table("workflow_patterns").select("*").gte(
                "frequency", min_frequency
            ).gte(
                "avg_success_rate", min_success_rate
            ).order("frequency", desc=True).limit(20).execute()
            
            candidates = []
            if result.data:
                for pattern in result.data:
                    # Calculate confidence score
                    confidence = pattern.get("confidence_score", 0.5)
                    
                    if confidence >= min_confidence:
                        # Check if already promoted
                        existing = self.supabase.table("composite_candidates").select("id").eq(
                            "pattern_id", pattern["id"]
                        ).execute()
                        
                        if not existing.data:
                            candidates.append(pattern)
            
            return candidates
            
        except Exception as e:
            print(f"Warning: Failed to scan for candidates: {e}")
            return []
    
    def create_candidate(
        self,
        pattern: Dict[str, Any],
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Create a composite tool candidate from a pattern
        
        Args:
            pattern: Workflow pattern dictionary
            callback: Progress callback
            
        Returns:
            Result dictionary with success status
        """
        def emit(event: str, data: Any = None):
            if callback:
                callback(event, data)
        
        try:
            pattern_id = pattern["id"]
            tool_sequence = pattern["tool_sequence"]
            
            emit("composite_synthesis_start", {
                "pattern": pattern["pattern_name"],
                "tools": tool_sequence
            })
            
            # Step 1: Register as candidate
            candidate_data = {
                "pattern_id": pattern_id,
                "tool_sequence": tool_sequence,
                "frequency": pattern["frequency"],
                "success_rate": pattern["avg_success_rate"],
                "confidence_score": pattern.get("confidence_score", 0.5),
                "evaluation_status": "pending"
            }
            
            candidate_result = self.supabase.table("composite_candidates").insert(
                candidate_data
            ).execute()
            
            if not candidate_result.data:
                return {"success": False, "error": "Failed to create candidate record"}
            
            candidate_id = candidate_result.data[0]["id"]
            
            emit("composite_candidate_created", {"candidate_id": candidate_id})
            
            # Step 2: Generate composite function specification
            emit("composite_generating_spec", {})
            spec = self._generate_composite_spec(tool_sequence, pattern)
            
            # Step 3: Generate tests (unit + integration)
            emit("composite_generating_tests", {})
            tests = self._generate_composite_tests(spec, tool_sequence)
            
            # Update candidate
            self.supabase.table("composite_candidates").update({
                "tests_generated": True,
                "evaluation_status": "testing"
            }).eq("id", candidate_id).execute()
            
            # Step 4: Generate implementation
            emit("composite_generating_implementation", {})
            implementation = self._generate_composite_implementation(spec, tool_sequence, tests)
            
            # Step 5: Verify in sandbox
            emit("composite_verifying", {})
            verification = self.sandbox.verify_tool(
                spec["function_name"],
                implementation,
                tests
            )
            
            if not verification["success"]:
                self.supabase.table("composite_candidates").update({
                    "evaluation_status": "rejected",
                    "rejection_reason": f"Tests failed: {verification.get('output', 'Unknown error')}"
                }).eq("id", candidate_id).execute()
                
                return {
                    "success": False,
                    "error": "Composite tests failed",
                    "verification_output": verification["output"]
                }
            
            # Step 6: Register as composite tool
            emit("composite_registering", {})
            composite_id = self._register_composite(
                spec=spec,
                implementation=implementation,
                tests=tests,
                tool_sequence=tool_sequence,
                pattern=pattern
            )
            
            # Update candidate as approved
            self.supabase.table("composite_candidates").update({
                "tests_passing": True,
                "evaluation_status": "approved",
                "promoted_to_composite": composite_id,
                "evaluated_at": datetime.now().isoformat()
            }).eq("id", candidate_id).execute()
            
            emit("composite_synthesis_complete", {
                "composite_id": composite_id,
                "name": spec["function_name"]
            })
            
            return {
                "success": True,
                "composite_id": composite_id,
                "composite_name": spec["function_name"],
                "spec": spec,
                "verification": verification
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Composite synthesis failed: {str(e)}"
            }
    
    def _generate_composite_spec(
        self,
        tool_sequence: List[str],
        pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate specification for composite tool"""
        
        # Get individual tool specs
        tool_specs = []
        for tool_name in tool_sequence:
            tool_info = self.registry.get_tool_by_name(tool_name)
            if tool_info:
                tool_specs.append({
                    "name": tool_name,
                    "docstring": tool_info["docstring"]
                })
        
        # Create prompt for LLM
        tools_desc = "\n".join([
            f"- {ts['name']}: {ts['docstring']}"
            for ts in tool_specs
        ])
        
        system_prompt = """You are designing a composite function that chains multiple tools together.
Create a specification for a single function that internally calls these tools in sequence.

Return ONLY a JSON object with this structure:
{
    "function_name": "snake_case_composite_name",
    "parameters": [
        {"name": "param_name", "type": "param_type", "description": "what it does"}
    ],
    "return_type": "return_type",
    "docstring": "Comprehensive description of what this composite function does, including that it's composed of multiple steps."
}

The function should accept the initial inputs needed by the first tool and return the final output."""
        
        user_prompt = f"""Create a composite function specification for this workflow:

Tools in sequence:
{tools_desc}

Pattern description: {pattern.get('description', 'Multi-step workflow')}
Used {pattern['frequency']} times with {pattern['avg_success_rate']:.1%} success rate.

Design a single function that combines these steps."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.llm_client._call_llm(messages, temperature=0.2)
        
        # Parse JSON
        import json
        start = response.find('{')
        end = response.rfind('}') + 1
        spec = json.loads(response[start:end])
        
        return spec
    
    def _generate_composite_tests(
        self,
        spec: Dict[str, Any],
        tool_sequence: List[str]
    ) -> str:
        """Generate comprehensive tests for composite tool"""
        
        system_prompt = """You are writing comprehensive tests for a composite function that chains multiple tools.

Write pytest tests that:
1. Test the end-to-end workflow
2. Test with valid inputs
3. Test edge cases
4. Mock the underlying tool calls if needed

Return ONLY the Python test code."""
        
        params_desc = "\n".join([
            f"  - {p['name']}: {p['type']} - {p['description']}"
            for p in spec['parameters']
        ])
        
        user_content = f"""Function Specification:
Name: {spec['function_name']}
Parameters:
{params_desc}
Return Type: {spec['return_type']}
Description: {spec['docstring']}

Tool sequence: {' -> '.join(tool_sequence)}

Generate comprehensive pytest tests."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.llm_client._call_llm(messages, temperature=0.3, max_tokens=1500)
        
        # Extract code
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        return response
    
    def _generate_composite_implementation(
        self,
        spec: Dict[str, Any],
        tool_sequence: List[str],
        tests: str
    ) -> str:
        """Generate implementation for composite tool"""
        
        # Get tool implementations for context
        tool_imports = []
        for tool_name in tool_sequence:
            tool_imports.append(f"from tools.{tool_name} import {tool_name}")
        
        imports_str = "\n".join(tool_imports)
        
        params_str = ", ".join([
            f"{p['name']}: {p['type']}"
            for p in spec['parameters']
        ])
        
        system_prompt = """You are implementing a composite function that chains multiple tools together.

Write clean, production-quality Python code that:
1. Imports and calls the underlying tools in sequence
2. Properly passes data between tools
3. Handles errors gracefully
4. Returns the final result

Return ONLY the Python function code."""
        
        user_content = f"""Function Specification:
Name: {spec['function_name']}
Signature: def {spec['function_name']}({params_str}) -> {spec['return_type']}
Docstring: {spec['docstring']}

Available imports:
{imports_str}

Tool sequence: {' -> '.join(tool_sequence)}

Tests that must pass:
{tests}

Implement the composite function."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.llm_client._call_llm(messages, temperature=0.2, max_tokens=2000)
        
        # Extract code
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        return response
    
    def _register_composite(
        self,
        spec: Dict[str, Any],
        implementation: str,
        tests: str,
        tool_sequence: List[str],
        pattern: Dict[str, Any]
    ) -> str:
        """Register composite tool in database"""
        
        import os
        
        # Save files
        composite_name = spec["function_name"]
        tool_file = os.path.join(Config.TOOLS_DIR, f"{composite_name}.py")
        test_file = os.path.join(Config.TOOLS_DIR, f"test_{composite_name}.py")
        
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(implementation)
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(tests)
        
        # Generate embedding
        embedding = self.llm_client.generate_embedding(spec["docstring"])
        
        # Create workflow template
        workflow_template = {
            "type": "composite",
            "steps": [{"tool": tool_name, "order": i} for i, tool_name in enumerate(tool_sequence)]
        }
        
        # Insert into composite_tools table
        composite_data = {
            "id": composite_name,
            "name": composite_name,
            "component_tools": tool_sequence,
            "workflow_template": workflow_template,
            "success_rate": pattern["avg_success_rate"],
            "usage_count": 0,
            "auto_generated": True,
            "file_path": tool_file,
            "test_path": test_file,
            "docstring": spec["docstring"],
            "embedding": embedding,
            "metadata": {
                "pattern_id": pattern["id"],
                "pattern_frequency": pattern["frequency"],
                "created_from_pattern": True
            }
        }
        
        result = self.supabase.table("composite_tools").insert(composite_data).execute()
        
        if result.data:
            return result.data[0]["id"]
        
        raise Exception("Failed to register composite tool")
    
    def run_batch_synthesis(
        self,
        max_candidates: int = 5,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Run batch synthesis of composite tools from eligible patterns
        
        Args:
            max_candidates: Maximum number of candidates to process
            callback: Progress callback
            
        Returns:
            Summary of synthesis results
        """
        def emit(event: str, data: Any = None):
            if callback:
                callback(event, data)
        
        emit("batch_synthesis_start", {"max_candidates": max_candidates})
        
        # Scan for candidates
        candidates = self.scan_for_candidates()
        emit("candidates_found", {"count": len(candidates)})
        
        results = {
            "total_candidates": len(candidates),
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "composites_created": []
        }
        
        for i, pattern in enumerate(candidates[:max_candidates]):
            emit("processing_candidate", {
                "index": i + 1,
                "total": min(len(candidates), max_candidates),
                "pattern": pattern["pattern_name"]
            })
            
            result = self.create_candidate(pattern, callback)
            
            results["processed"] += 1
            if result["success"]:
                results["successful"] += 1
                results["composites_created"].append(result["composite_name"])
            else:
                results["failed"] += 1
        
        emit("batch_synthesis_complete", results)
        
        return results


if __name__ == "__main__":
    # Test composite synthesizer
    synthesizer = CompositeSynthesizer()
    
    # Scan for candidates
    candidates = synthesizer.scan_for_candidates()
    print(f"Found {len(candidates)} composite tool candidates")

