"""
Composition Planner - Plans and executes multi-tool workflows
"""

from typing import Dict, Any, List, Optional, Callable
from src.capability_registry import CapabilityRegistry
from src.executor import ToolExecutor
from src.llm_client import LLMClient
from src.utils import extract_json_from_response
import json


class CompositionPlanner:
    """
    Plans and executes workflows involving multiple tools,
    handling data flow and dependencies between tools.
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry = None,
        executor: ToolExecutor = None,
        llm_client: LLMClient = None
    ):
        """
        Initialize the composition planner
        
        Args:
            registry: Capability registry for tool lookup
            executor: Tool executor
            llm_client: LLM client for planning
        """
        self.registry = registry or CapabilityRegistry()
        self.executor = executor or ToolExecutor()
        self.llm_client = llm_client or LLMClient()
    
    def execute_workflow(
        self,
        sub_tasks: List[Dict[str, Any]],
        user_prompt: str,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a multi-tool workflow based on sub-tasks
        
        Args:
            sub_tasks: List of sub-task definitions
            user_prompt: Original user prompt
            callback: Optional callback for progress updates
            
        Returns:
            Dictionary with execution results
        """
        def emit(event_type: str, data: Any = None):
            """Helper to emit events"""
            if callback:
                callback(event_type, data)
        
        results = []
        tool_sequence = []
        
        emit("workflow_start", {
            "total_steps": len(sub_tasks),
            "tasks": [task['task'] for task in sub_tasks]
        })
        
        for idx, sub_task in enumerate(sub_tasks):
            step_num = idx + 1
            task_desc = sub_task['task']
            depends_on = sub_task.get('depends_on')
            
            emit("workflow_step", {
                "step": step_num,
                "total": len(sub_tasks),
                "task": task_desc,
                "depends_on": depends_on
            })
            
            try:
                # Find appropriate tool for this sub-task
                tool_info = self.registry.search_tool(task_desc)
                
                if not tool_info:
                    # Tool not found, need to synthesize
                    emit("workflow_step_needs_synthesis", {
                        "step": step_num,
                        "task": task_desc
                    })
                    return {
                        "success": False,
                        "error": f"No tool found for sub-task: {task_desc}",
                        "step_failed": step_num,
                        "needs_synthesis": True,
                        "partial_results": results
                    }
                
                emit("workflow_step_tool_found", {
                    "step": step_num,
                    "tool_name": tool_info['name'],
                    "similarity": tool_info['similarity_score']
                })
                
                # Prepare arguments for this sub-task
                arguments = self._prepare_arguments(
                    sub_task=sub_task,
                    tool_info=tool_info,
                    previous_results=results,
                    user_prompt=user_prompt
                )
                
                emit("workflow_step_executing", {
                    "step": step_num,
                    "tool_name": tool_info['name'],
                    "arguments": arguments
                })
                
                # Execute the tool
                execution_result = self.executor.execute_tool(
                    tool_info=tool_info,
                    user_prompt=task_desc,
                    arguments=arguments
                )
                
                # Store result
                results.append(execution_result)
                tool_sequence.append(tool_info['name'])
                
                emit("workflow_step_complete", {
                    "step": step_num,
                    "tool_name": tool_info['name'],
                    "result": str(execution_result)
                })
                
            except Exception as e:
                emit("workflow_step_failed", {
                    "step": step_num,
                    "error": str(e)
                })
                return {
                    "success": False,
                    "error": f"Step {step_num} failed: {str(e)}",
                    "step_failed": step_num,
                    "partial_results": results,
                    "tool_sequence": tool_sequence
                }
        
        emit("workflow_complete", {
            "total_steps": len(sub_tasks),
            "results_count": len(results),
            "tool_sequence": tool_sequence
        })
        
        return {
            "success": True,
            "results": results,
            "tool_sequence": tool_sequence,
            "final_result": results[-1] if results else None
        }
    
    def _prepare_arguments(
        self,
        sub_task: Dict[str, Any],
        tool_info: Dict[str, Any],
        previous_results: List[Any],
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        Prepare arguments for a tool execution, potentially using previous results
        
        Args:
            sub_task: Sub-task definition
            tool_info: Tool information
            previous_results: Results from previous steps
            user_prompt: Original user prompt
            
        Returns:
            Arguments dictionary
        """
        depends_on = sub_task.get('depends_on')
        
        # If this task depends on a previous result, we need to incorporate it
        if depends_on is not None and depends_on > 0 and depends_on <= len(previous_results):
            previous_result = previous_results[depends_on - 1]
            
            # Use LLM to intelligently extract arguments, incorporating previous result
            system_prompt = f"""You are an argument extraction expert. Extract function arguments from the user's request.

The previous step produced this result: {previous_result}

You may need to use this previous result as one of the arguments for the current function.

Return ONLY a JSON object mapping parameter names to values.

Example:
If the function needs a string parameter and the previous result was a number,
you might need to convert it: {{"s": "{previous_result}"}}

**CRITICAL**: Return null for any parameter whose value is not clear from the context."""
            
            user_content = f"""Function Signature:
{self.executor.extract_function_signature(tool_info['code'])}

Current Task: {sub_task['task']}
Original Prompt: {user_prompt}
Previous Result: {previous_result}

Extract the arguments as JSON."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            try:
                response = self.llm_client._call_llm(messages, temperature=0.0, max_tokens=500)
                json_str = extract_json_from_response(response)
                arguments = json.loads(json_str)
                return arguments
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Warning: Failed to extract arguments with context: {str(e)}")
        
        # Fallback to standard argument extraction
        signature = self.executor.extract_function_signature(tool_info['code'])
        return self.llm_client.extract_arguments(sub_task['task'], signature)
    
    def execute_pattern(
        self,
        pattern: Dict[str, Any],
        user_prompt: str,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a known workflow pattern
        
        Args:
            pattern: Workflow pattern definition
            user_prompt: User's request
            callback: Progress callback
            
        Returns:
            Execution results
        """
        tool_sequence = pattern['tool_sequence']
        
        def emit(event_type: str, data: Any = None):
            if callback:
                callback(event_type, data)
        
        emit("pattern_execution_start", {
            "pattern_name": pattern.get('pattern_name'),
            "tool_sequence": tool_sequence
        })
        
        results = []
        
        for idx, tool_name in enumerate(tool_sequence):
            step_num = idx + 1
            
            emit("pattern_step", {
                "step": step_num,
                "total": len(tool_sequence),
                "tool_name": tool_name
            })
            
            try:
                # Get tool info
                tool_info = self.registry.get_tool_by_name(tool_name)
                
                if not tool_info:
                    return {
                        "success": False,
                        "error": f"Tool '{tool_name}' from pattern not found",
                        "step_failed": step_num,
                        "partial_results": results
                    }
                
                # Extract arguments (considering previous results)
                if idx == 0:
                    # First tool - extract from original prompt
                    arguments = self.llm_client.extract_arguments(
                        user_prompt,
                        self.executor.extract_function_signature(tool_info['code'])
                    )
                else:
                    # Subsequent tools - consider previous result
                    previous_result = results[-1]
                    
                    system_prompt = f"""Extract arguments for this function, using the previous result: {previous_result}

Return ONLY a JSON object with the arguments."""
                    
                    user_content = f"""Function: {self.executor.extract_function_signature(tool_info['code'])}
User Request: {user_prompt}
Previous Result: {previous_result}

Extract arguments as JSON."""
                    
                    try:
                        response = self.llm_client._call_llm(
                            [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": user_content}],
                            temperature=0.0
                        )
                        json_str = extract_json_from_response(response)
                        arguments = json.loads(json_str)
                    except (ValueError, json.JSONDecodeError):
                        arguments = {}
                
                # Execute tool
                result = self.executor.execute_tool(
                    tool_info=tool_info,
                    user_prompt=user_prompt,
                    arguments=arguments
                )
                
                results.append(result)
                
                emit("pattern_step_complete", {
                    "step": step_num,
                    "tool_name": tool_name,
                    "result": str(result)
                })
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Pattern execution failed at step {step_num}: {str(e)}",
                    "step_failed": step_num,
                    "partial_results": results
                }
        
        emit("pattern_execution_complete", {
            "pattern_name": pattern.get('pattern_name'),
            "steps_completed": len(results)
        })
        
        return {
            "success": True,
            "results": results,
            "tool_sequence": tool_sequence,
            "final_result": results[-1] if results else None,
            "pattern_used": pattern.get('pattern_name')
        }
    
    def should_create_composite(
        self,
        tool_sequence: List[str],
        success_rate: float,
        frequency: int
    ) -> bool:
        """
        Determine if a tool sequence should be turned into a composite tool
        
        Args:
            tool_sequence: Sequence of tool names
            success_rate: Success rate of the sequence
            frequency: How often this sequence has been used
            
        Returns:
            Whether to create a composite tool
        """
        # Create composite if:
        # - Sequence has 2+ tools
        # - Used at least 3 times
        # - Success rate above 80%
        return (
            len(tool_sequence) >= 2 and
            frequency >= 3 and
            success_rate >= 0.8
        )


if __name__ == "__main__":
    # Test the composition planner
    planner = CompositionPlanner()
    
    # Test workflow execution
    sub_tasks = [
        {"task": "Calculate 25% of 100", "order": 1, "depends_on": None},
        {"task": "Reverse the result as a string", "order": 2, "depends_on": 1}
    ]
    
    result = planner.execute_workflow(
        sub_tasks=sub_tasks,
        user_prompt="Calculate 25% of 100 and reverse the result"
    )
    
    print(f"Workflow Success: {result['success']}")
    if result['success']:
        print(f"Tool Sequence: {result['tool_sequence']}")
        print(f"Final Result: {result['final_result']}")

