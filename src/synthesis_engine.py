"""
Capability Synthesis Engine - Creates new tools using Test-Driven Development
"""

from typing import Dict, Any, Optional, Callable
from src.llm_client import LLMClient
from src.sandbox import SecureSandbox
from src.capability_registry import CapabilityRegistry


class CapabilitySynthesisEngine:
    """
    Synthesizes new agent capabilities using a Test-Driven Development workflow.
    
    Process:
    1. Generate function specification from user prompt
    2. Generate comprehensive test suite
    3. Implement function to pass tests
    4. Verify in secure sandbox
    5. Register in capability registry
    """
    
    def __init__(
        self,
        llm_client: LLMClient = None,
        sandbox: SecureSandbox = None,
        registry: CapabilityRegistry = None
    ):
        """
        Initialize the synthesis engine
        
        Args:
            llm_client: LLM client for code generation
            sandbox: Secure sandbox for verification
            registry: Capability registry for storage
        """
        self.llm_client = llm_client or LLMClient()
        self.sandbox = sandbox or SecureSandbox()
        self.registry = registry or CapabilityRegistry()
    
    def synthesize_capability(
        self,
        user_prompt: str,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Synthesize a new capability from a user prompt
        
        Args:
            user_prompt: Natural language description of desired functionality
            callback: Optional callback function(event_type, data) for progress updates
            
        Returns:
            Dictionary with synthesis result and tool information
        """
        
        def emit(event_type: str, data: Any = None):
            """Helper to emit events via callback"""
            if callback:
                callback(event_type, data)
        
        try:
            # Step 1: Generate Specification
            emit("synthesis_step", {"step": "specification", "status": "in_progress"})
            
            try:
                spec = self.llm_client.generate_spec(user_prompt)
                emit("synthesis_step", {
                    "step": "specification",
                    "status": "complete",
                    "data": spec
                })
            except Exception as e:
                emit("synthesis_step", {
                    "step": "specification",
                    "status": "failed",
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Failed to generate specification: {str(e)}",
                    "step": "specification"
                }
            
            # Step 2: Generate Tests
            emit("synthesis_step", {"step": "tests", "status": "in_progress"})
            
            try:
                tests = self.llm_client.generate_tests(spec)
                emit("synthesis_step", {
                    "step": "tests",
                    "status": "complete",
                    "data": {"test_count": tests.count("def test_")}
                })
            except Exception as e:
                emit("synthesis_step", {
                    "step": "tests",
                    "status": "failed",
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Failed to generate tests: {str(e)}",
                    "step": "tests"
                }
            
            # Step 3: Generate Implementation
            emit("synthesis_step", {"step": "implementation", "status": "in_progress"})
            
            try:
                implementation = self.llm_client.generate_implementation(spec, tests)
                emit("synthesis_step", {
                    "step": "implementation",
                    "status": "complete",
                    "data": {"function_name": spec['function_name']}
                })
            except Exception as e:
                emit("synthesis_step", {
                    "step": "implementation",
                    "status": "failed",
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Failed to generate implementation: {str(e)}",
                    "step": "implementation"
                }
            
            # Step 4: Verify in Sandbox
            emit("synthesis_step", {"step": "verification", "status": "in_progress"})
            
            try:
                verification_result = self.sandbox.verify_tool(
                    function_name=spec['function_name'],
                    function_code=implementation,
                    test_code=tests
                )
                
                if not verification_result['success']:
                    emit("synthesis_step", {
                        "step": "verification",
                        "status": "failed",
                        "error": "Tests failed",
                        "output": verification_result['output']
                    })
                    return {
                        "success": False,
                        "error": "Generated code failed tests",
                        "step": "verification",
                        "test_output": verification_result['output']
                    }
                
                emit("synthesis_step", {
                    "step": "verification",
                    "status": "complete",
                    "data": {"tests_passed": True}
                })
                
            except Exception as e:
                emit("synthesis_step", {
                    "step": "verification",
                    "status": "failed",
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Verification failed: {str(e)}",
                    "step": "verification"
                }
            
            # Step 5: Register Tool
            emit("synthesis_step", {"step": "registration", "status": "in_progress"})
            
            try:
                tool_metadata = self.registry.add_tool(
                    name=spec['function_name'],
                    code=implementation,
                    tests=tests,
                    docstring=spec['docstring']
                )
                
                emit("synthesis_step", {
                    "step": "registration",
                    "status": "complete",
                    "data": {"tool_name": spec['function_name']}
                })
                
            except Exception as e:
                emit("synthesis_step", {
                    "step": "registration",
                    "status": "failed",
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Failed to register tool: {str(e)}",
                    "step": "registration"
                }
            
            # Success!
            emit("synthesis_complete", {
                "tool_name": spec['function_name'],
                "tool_metadata": tool_metadata
            })
            
            return {
                "success": True,
                "tool_name": spec['function_name'],
                "spec": spec,
                "code": implementation,
                "tests": tests,
                "metadata": tool_metadata
            }
            
        except Exception as e:
            emit("synthesis_error", {"error": str(e)})
            return {
                "success": False,
                "error": f"Unexpected error during synthesis: {str(e)}",
                "step": "unknown"
            }


if __name__ == "__main__":
    # Simple test
    engine = CapabilitySynthesisEngine()
    print("Capability Synthesis Engine initialized")
    
    # Test synthesis
    result = engine.synthesize_capability("Calculate the factorial of a number")
    
    if result['success']:
        print(f"✓ Successfully synthesized tool: {result['tool_name']}")
    else:
        print(f"✗ Synthesis failed at {result.get('step', 'unknown')}: {result.get('error', 'Unknown error')}")

