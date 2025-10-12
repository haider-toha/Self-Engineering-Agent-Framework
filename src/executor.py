"""
Tool Executor - Dynamically loads and executes agent tools
"""

import sys
import os
import importlib.util
import inspect
from typing import Dict, Any, Optional
from src.llm_client import LLMClient


class ToolExecutor:
    """
    Dynamically loads and executes tools from the registry.
    Uses LLM to extract arguments from natural language prompts.
    """
    
    def __init__(self, llm_client: LLMClient = None):
        """
        Initialize the tool executor
        
        Args:
            llm_client: LLM client for argument extraction
        """
        self.llm_client = llm_client or LLMClient()
    
    def extract_function_signature(self, code: str) -> str:
        """
        Extract function signature from code
        
        Args:
            code: Python function code
            
        Returns:
            Function signature string
        """
        lines = code.strip().split('\n')
        signature_lines = []
        
        for line in lines:
            if line.strip().startswith('def '):
                signature_lines.append(line)
                # Check if signature continues on next lines
                if ':' not in line:
                    continue
                else:
                    break
            elif signature_lines:
                signature_lines.append(line)
                if ':' in line:
                    break
        
        return '\n'.join(signature_lines)
    
    def load_tool_function(self, tool_info: Dict[str, Any]):
        """
        Dynamically load a tool function from file
        
        Args:
            tool_info: Tool information dictionary with 'file_path' and 'name'
            
        Returns:
            Loaded function object
        """
        file_path = tool_info['file_path']
        function_name = tool_info['name']
        
        # Load module from file
        spec = importlib.util.spec_from_file_location(function_name, file_path)
        if spec is None or spec.loader is None:
            raise Exception(f"Failed to load module from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[function_name] = module
        spec.loader.exec_module(module)
        
        # Get the function
        if not hasattr(module, function_name):
            raise Exception(f"Function '{function_name}' not found in module")
        
        return getattr(module, function_name)
    
    def execute_tool(
        self,
        tool_info: Dict[str, Any],
        user_prompt: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a tool with arguments extracted from user prompt
        
        Args:
            tool_info: Tool information dictionary
            user_prompt: User's natural language request
            arguments: Pre-extracted arguments (optional, will extract if not provided)
            
        Returns:
            Result of tool execution
        """
        try:
            # Load the function
            function = self.load_tool_function(tool_info)
            
            # Extract arguments if not provided
            if arguments is None:
                signature = self.extract_function_signature(tool_info['code'])
                arguments = self.llm_client.extract_arguments(user_prompt, signature)
            
            # Check for null arguments, which indicates a mismatch
            if any(v is None for v in arguments.values()):
                missing_keys = [k for k, v in arguments.items() if v is None]
                raise ValueError(f"Argument mismatch: The user's prompt is missing values for: {', '.join(missing_keys)}")

            # Execute the function
            result = function(**arguments)
            
            return result
            
        except TypeError as e:
            # If arguments are missing, it's a mismatch between prompt and tool.
            if 'required positional argument' in str(e) or 'missing' in str(e):
                raise ValueError(f"Argument mismatch: The user's prompt is missing information needed by the tool. Error: {e}")
            raise e
        except Exception as e:
            raise Exception(f"Tool execution failed: {str(e)}")
    
    def execute_with_retry(
        self,
        tool_info: Dict[str, Any],
        user_prompt: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Execute a tool with retry logic for argument extraction
        
        Args:
            tool_info: Tool information dictionary
            user_prompt: User's natural language request
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary with 'success', 'result', and optional 'error' keys
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = self.execute_tool(tool_info, user_prompt)
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1
                }
            except ValueError as e:
                # This is a specific failure case indicating a tool mismatch
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": "ArgumentError",
                    "attempts": attempt + 1
                }
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    # Could implement more sophisticated retry logic here
                    continue
        
        return {
            "success": False,
            "error": last_error,
            "error_type": "ExecutionError",
            "attempts": max_retries + 1
        }


if __name__ == "__main__":
    # Simple test
    executor = ToolExecutor()
    print("Tool Executor initialized")

