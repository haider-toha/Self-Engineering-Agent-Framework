"""
Agent Orchestrator - Central decision-making component that coordinates all subsystems
"""

from typing import Dict, Any, Optional, Callable
from src.capability_registry import CapabilityRegistry
from src.synthesis_engine import CapabilitySynthesisEngine
from src.executor import ToolExecutor
from src.response_synthesizer import ResponseSynthesizer
from src.llm_client import LLMClient
from src.sandbox import SecureSandbox


class AgentOrchestrator:
    """
    The brain of the agent. Coordinates the entire flow from user request to response.
    
    Flow:
    1. Search for existing capability
    2. If found: execute it
    3. If not found: synthesize new capability, then execute it
    4. Synthesize natural language response
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry = None,
        synthesis_engine: CapabilitySynthesisEngine = None,
        executor: ToolExecutor = None,
        synthesizer: ResponseSynthesizer = None
    ):
        """
        Initialize the orchestrator
        
        Args:
            registry: Capability registry
            synthesis_engine: Synthesis engine for creating new tools
            executor: Tool executor
            synthesizer: Response synthesizer
        """
        # Initialize shared components
        llm_client = LLMClient()
        sandbox = SecureSandbox()
        
        # Initialize subsystems
        self.registry = registry or CapabilityRegistry()
        self.synthesis_engine = synthesis_engine or CapabilitySynthesisEngine(
            llm_client=llm_client,
            sandbox=sandbox,
            registry=self.registry
        )
        self.executor = executor or ToolExecutor(llm_client=llm_client)
        self.synthesizer = synthesizer or ResponseSynthesizer(llm_client=llm_client)
    
    def process_request(
        self,
        user_prompt: str,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request from start to finish
        
        Args:
            user_prompt: User's natural language request
            callback: Optional callback function(event_type, data) for progress updates
            
        Returns:
            Dictionary with 'success', 'response', and optional metadata
        """
        
        def emit(event_type: str, data: Any = None):
            """Helper to emit events via callback"""
            if callback:
                callback(event_type, data)
        
        try:
            # Step 1: Search for existing capability
            emit("searching", {"query": user_prompt})
            
            tool_info = self.registry.search_tool(user_prompt)
            
            # Step 2a: If a tool is found, try to execute it
            if tool_info:
                emit("tool_found", {
                    "tool_name": tool_info['name'],
                    "similarity": tool_info['similarity_score']
                })
                
                emit("executing", {"tool_name": tool_info['name']})
                
                execution_result = self.executor.execute_with_retry(
                    tool_info=tool_info,
                    user_prompt=user_prompt
                )
                
                # If execution is successful, we are done
                if execution_result['success']:
                    tool_result = execution_result['result']
                    emit("execution_complete", {
                        "tool_name": tool_info['name'],
                        "result": str(tool_result)
                    })
                    
                    emit("synthesizing_response", {})
                    final_response = self.synthesizer.synthesize(user_prompt, tool_result)
                    emit("complete", {"response": final_response})
                    
                    return {
                        "success": True,
                        "response": final_response,
                        "tool_name": tool_info['name'],
                        "tool_result": tool_result,
                        "synthesized": False
                    }

                # If execution failed because of an argument mismatch, invalidate the tool and proceed to synthesis
                elif execution_result.get("error_type") == "ArgumentError":
                    emit("tool_mismatch", {
                        "tool_name": tool_info['name'],
                        "error": "Tool found, but arguments in your prompt do not match its requirements. Attempting to synthesize a new tool."
                    })
                    tool_info = None  # Invalidate the found tool to trigger synthesis
                
                # For any other execution error, fail the request
                else:
                    error = execution_result['error']
                    emit("execution_failed", {"error": error})
                    error_response = self.synthesizer.synthesize_error(user_prompt, error)
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "tool_name": tool_info.get('name') if tool_info else 'unknown'
                    }

            # Step 2b: If no tool was found OR it was a mismatch, enter synthesis mode
            if not tool_info:
                emit("no_tool_found", {"query": user_prompt})
                emit("entering_synthesis_mode", {})
                
                # Synthesize new capability
                synthesis_result = self.synthesis_engine.synthesize_capability(
                    user_prompt=user_prompt,
                    callback=callback
                )
                
                if not synthesis_result['success']:
                    error = synthesis_result.get('error', 'Unknown error')
                    emit("synthesis_failed", {
                        "error": error,
                        "step": synthesis_result.get('step', 'unknown')
                    })
                    error_response = self.synthesizer.synthesize_error(
                        user_prompt,
                        f"Failed to create new capability: {error}"
                    )
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "synthesis_failed": True
                    }
                
                # Synthesis successful - now execute the new tool
                tool_name = synthesis_result['tool_name']
                emit("synthesis_successful", {"tool_name": tool_name})
                
                new_tool_info = self.registry.get_tool_by_name(tool_name)
                
                emit("executing", {"tool_name": tool_name})
                
                execution_result = self.executor.execute_with_retry(
                    tool_info=new_tool_info,
                    user_prompt=user_prompt
                )
                
                if not execution_result['success']:
                    error = execution_result['error']
                    emit("execution_failed", {"error": error})
                    error_response = self.synthesizer.synthesize_error(user_prompt, error)
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "tool_name": tool_name,
                        "synthesized": True
                    }
                
                tool_result = execution_result['result']
                
                emit("execution_complete", {
                    "tool_name": tool_name,
                    "result": str(tool_result)
                })
                
                emit("synthesizing_response", {})
                final_response = self.synthesizer.synthesize_synthesis_result(
                    tool_name, user_prompt, tool_result
                )
                
                emit("complete", {"response": final_response})
                
                return {
                    "success": True,
                    "response": final_response,
                    "tool_name": tool_name,
                    "tool_result": tool_result,
                    "synthesized": True
                }
        
        except Exception as e:
            emit("error", {"error": str(e)})
            error_response = self.synthesizer.synthesize_error(
                user_prompt,
                f"An unexpected error occurred: {str(e)}"
            )
            return {
                "success": False,
                "response": error_response,
                "error": str(e)
            }
    
    def get_all_tools(self):
        """Get list of all available tools"""
        return self.registry.get_all_tools()
    
    def get_tool_count(self):
        """Get the total number of available tools"""
        return self.registry.count_tools()


if __name__ == "__main__":
    # Simple test
    orchestrator = AgentOrchestrator()
    print(f"Agent Orchestrator initialized with {orchestrator.get_tool_count()} tools")
    
    # Test with a simple request
    def print_callback(event_type, data):
        print(f"[{event_type}] {data}")
    
    result = orchestrator.process_request(
        "What is 2 plus 2?",
        callback=print_callback
    )
    
    print(f"\nFinal response: {result['response']}")

