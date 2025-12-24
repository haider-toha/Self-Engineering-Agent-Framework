"""
Reflection Engine - Analyzes failures and generates fixes
"""

import os
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from supabase import Client, create_client
from config import Config
from src.llm_client import LLMClient
from src.sandbox import SecureSandbox
from src.capability_registry import CapabilityRegistry
from src.utils import extract_code_from_markdown


class ReflectionEngine:
    """
    Analyzes tool execution failures, generates root-cause analyses,
    proposes fixes, and implements self-repair workflows.
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        sandbox: Optional[SecureSandbox] = None,
        registry: Optional[CapabilityRegistry] = None,
        supabase_client: Optional[Client] = None
    ):
        """
        Initialize the reflection engine
        
        Args:
            llm_client: LLM client for analysis
            sandbox: Sandbox for verification
            registry: Capability registry
            supabase_client: Supabase client
        """
        self.llm_client = llm_client or LLMClient()
        self.sandbox = sandbox or SecureSandbox()
        self.registry = registry or CapabilityRegistry()
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    def analyze_failure(
        self,
        tool_name: str,
        error_message: str,
        inputs: Dict[str, Any],
        user_prompt: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a tool execution failure and generate root cause
        
        Args:
            tool_name: Name of the failed tool
            error_message: Error message from execution
            inputs: Input parameters that caused failure
            user_prompt: Original user prompt
            execution_id: ID of the execution record
            
        Returns:
            Analysis dictionary with root cause and proposed fix
        """
        # Get tool code for context
        tool_info = self.registry.get_tool_by_name(tool_name)
        if not tool_info:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry"
            }
        
        # Classify failure type
        failure_type = self._classify_failure(error_message, inputs)
        
        # Generate root cause analysis
        root_cause = self._generate_root_cause_analysis(
            tool_name=tool_name,
            tool_code=tool_info["code"],
            error_message=error_message,
            inputs=inputs,
            failure_type=failure_type,
            user_prompt=user_prompt
        )
        
        # Generate proposed fix
        proposed_fix = self._generate_fix_proposal(
            tool_name=tool_name,
            tool_code=tool_info["code"],
            test_code=self._get_tool_tests(tool_info["test_path"]),
            root_cause=root_cause,
            error_message=error_message,
            failure_type=failure_type
        )
        
        # Log reflection
        reflection_id = self._log_reflection(
            execution_id=execution_id,
            tool_name=tool_name,
            failure_type=failure_type,
            error_message=error_message,
            root_cause=root_cause,
            proposed_fix=proposed_fix,
            metadata={
                "inputs": inputs,
                "user_prompt": user_prompt
            }
        )
        
        return {
            "success": True,
            "reflection_id": reflection_id,
            "failure_type": failure_type,
            "root_cause": root_cause,
            "proposed_fix": proposed_fix
        }
    
    def apply_fix(
        self,
        reflection_id: str,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Apply a proposed fix and verify it works
        
        Args:
            reflection_id: ID of the reflection record
            callback: Progress callback
            
        Returns:
            Result dictionary with fix success status
        """
        def emit(event: str, data: Any = None):
            if callback:
                callback(event, data)
        
        try:
            # Get reflection record
            result = self.supabase.table("reflection_log").select("*").eq(
                "id", reflection_id
            ).execute()
            
            if not result.data:
                return {"success": False, "error": "Reflection record not found"}
            
            reflection = result.data[0]
            tool_name = reflection["tool_name"]
            proposed_fix = reflection["proposed_fix"]
            
            emit("fix_applying", {"tool": tool_name})
            
            # Get current tool info
            tool_info = self.registry.get_tool_by_name(tool_name)
            if not tool_info:
                return {"success": False, "error": f"Tool '{tool_name}' not found"}
            
            # Generate minimal failing test if not exists
            emit("generating_test", {})
            failing_test = self._generate_minimal_failing_test(
                tool_name=tool_name,
                tool_code=tool_info["code"],
                error_message=reflection["error_message"],
                metadata=reflection.get("metadata", {})
            )
            
            # Get existing tests
            existing_tests = self._get_tool_tests(tool_info["test_path"])
            
            # Combine tests
            combined_tests = f"{existing_tests}\n\n# Regression test from reflection\n{failing_test}"
            
            # Verify fix in sandbox
            emit("verifying_fix", {})
            verification = self.sandbox.verify_tool(
                function_name=tool_name,
                function_code=proposed_fix,
                test_code=combined_tests
            )
            
            if verification["success"]:
                # Fix passed! Create new version
                emit("fix_verified", {})
                
                # Save new version
                self._save_tool_version(
                    tool_name=tool_name,
                    code=proposed_fix,
                    tests=combined_tests,
                    docstring=tool_info["docstring"],
                    change_reason=f"Self-repair from reflection {reflection_id}",
                    created_by="reflection"
                )
                
                # Update tool in registry
                with open(tool_info["file_path"], 'w', encoding='utf-8') as f:
                    f.write(proposed_fix)
                
                with open(tool_info["test_path"], 'w', encoding='utf-8') as f:
                    f.write(combined_tests)
                
                # Mark reflection as resolved
                self.supabase.table("reflection_log").update({
                    "fix_applied": True,
                    "fix_successful": True,
                    "resolved_at": datetime.now().isoformat()
                }).eq("id", reflection_id).execute()
                
                emit("fix_complete", {"tool": tool_name})
                
                return {
                    "success": True,
                    "tool_name": tool_name,
                    "verification_output": verification["output"]
                }
            else:
                # Fix failed
                emit("fix_failed", {"output": verification["output"]})
                
                self.supabase.table("reflection_log").update({
                    "fix_applied": True,
                    "fix_successful": False,
                    "resolved_at": datetime.now().isoformat()
                }).eq("id", reflection_id).execute()
                
                return {
                    "success": False,
                    "error": "Fix did not pass tests",
                    "verification_output": verification["output"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to apply fix: {str(e)}"
            }
    
    def _classify_failure(self, error_message: str, inputs: Dict[str, Any]) -> str:
        """Classify the type of failure"""
        error_lower = error_message.lower()
        
        if "missing" in error_lower or "required" in error_lower:
            return "argument_mismatch"
        elif "typeerror" in error_lower or "type" in error_lower:
            return "type_error"
        elif "valueerror" in error_lower:
            return "value_error"
        elif "zerodivision" in error_lower:
            return "arithmetic_error"
        elif "key" in error_lower or "index" in error_lower:
            return "data_access_error"
        elif "timeout" in error_lower or "performance" in error_lower:
            return "performance_degradation"
        else:
            return "execution_error"
    
    def _generate_root_cause_analysis(
        self,
        tool_name: str,
        tool_code: str,
        error_message: str,
        inputs: Dict[str, Any],
        failure_type: str,
        user_prompt: Optional[str]
    ) -> str:
        """Generate root cause analysis using LLM"""
        
        system_prompt = """You are a debugging expert analyzing why a tool execution failed.

Provide a concise root cause analysis explaining:
1. What went wrong
2. Why it happened
3. What conditions triggered the failure

Be specific and technical."""
        
        user_content = f"""Tool: {tool_name}
Failure Type: {failure_type}

Tool Code:
{tool_code}

Error Message:
{error_message}

Inputs:
{inputs}

User Prompt: {user_prompt or 'N/A'}

Analyze the root cause of this failure."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        return self.llm_client._call_llm(messages, temperature=0.3, max_tokens=500)
    
    def _generate_fix_proposal(
        self,
        tool_name: str,
        tool_code: str,
        test_code: str,
        root_cause: str,
        error_message: str,
        failure_type: str
    ) -> str:
        """Generate a proposed fix for the tool"""
        
        system_prompt = """You are a code repair expert. Fix the broken code based on the root cause analysis.

Requirements:
1. Fix ONLY the specific issue identified
2. Preserve all existing functionality
3. Add proper error handling if missing
4. Ensure all existing tests still pass
5. Return ONLY the complete fixed Python function code

Do not add explanations, only code."""
        
        user_content = f"""Tool: {tool_name}
Failure Type: {failure_type}

Original Code:
{tool_code}

Root Cause Analysis:
{root_cause}

Error Message:
{error_message}

Existing Tests:
{test_code}

Generate the fixed code."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.llm_client._call_llm(messages, temperature=0.2, max_tokens=2000)

        # Extract code
        return extract_code_from_markdown(response)
    
    def _generate_minimal_failing_test(
        self,
        tool_name: str,
        tool_code: str,
        error_message: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Generate a minimal test case that reproduces the failure"""
        
        inputs = metadata.get("inputs", {})
        
        system_prompt = """You are a test engineer. Write a minimal pytest test case that reproduces this specific failure.

The test should:
1. Be as simple as possible
2. Reproduce the exact error
3. Serve as a regression test
4. Include assertions

Return ONLY the test function code."""
        
        user_content = f"""Tool: {tool_name}

Tool Code:
{tool_code}

Error Message:
{error_message}

Inputs that caused failure:
{inputs}

Generate a minimal failing test case."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self.llm_client._call_llm(messages, temperature=0.2, max_tokens=800)

        # Extract code
        return extract_code_from_markdown(response)
    
    def _get_tool_tests(self, test_path: str) -> str:
        """Read tool test file"""
        try:
            with open(test_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def _log_reflection(
        self,
        execution_id: Optional[str],
        tool_name: str,
        failure_type: str,
        error_message: str,
        root_cause: str,
        proposed_fix: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Log reflection to database"""
        
        reflection_data = {
            "execution_id": execution_id,
            "tool_name": tool_name,
            "failure_type": failure_type,
            "error_message": error_message,
            "root_cause_analysis": root_cause,
            "proposed_fix": proposed_fix,
            "metadata": metadata
        }
        
        result = self.supabase.table("reflection_log").insert(reflection_data).execute()
        
        return result.data[0]["id"] if result.data else None
    
    def _save_tool_version(
        self,
        tool_name: str,
        code: str,
        tests: str,
        docstring: str,
        change_reason: str,
        created_by: str
    ):
        """Save a new version of a tool"""
        
        # Get current version number
        versions_result = self.supabase.table("tool_versions").select("version").eq(
            "tool_name", tool_name
        ).order("version", desc=True).limit(1).execute()
        
        next_version = 1
        if versions_result.data:
            next_version = versions_result.data[0]["version"] + 1
        
        # Mark all previous versions as not current
        self.supabase.table("tool_versions").update({
            "is_current": False
        }).eq("tool_name", tool_name).execute()
        
        # Insert new version
        version_data = {
            "tool_name": tool_name,
            "version": next_version,
            "code": code,
            "tests": tests,
            "docstring": docstring,
            "file_path": os.path.join(Config.TOOLS_DIR, f"{tool_name}.py"),
            "test_path": os.path.join(Config.TOOLS_DIR, f"test_{tool_name}.py"),
            "created_by": created_by,
            "change_reason": change_reason,
            "is_current": True
        }
        
        self.supabase.table("tool_versions").insert(version_data).execute()
    
    def get_unresolved_reflections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get unresolved reflection records"""
        
        result = self.supabase.table("reflection_log").select("*").is_(
            "resolved_at", "null"
        ).order("created_at", desc=True).limit(limit).execute()
        
        return result.data if result.data else []


if __name__ == "__main__":
    # Test reflection engine
    engine = ReflectionEngine()
    
    # Get unresolved reflections
    unresolved = engine.get_unresolved_reflections()
    print(f"Found {len(unresolved)} unresolved reflections")

