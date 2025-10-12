"""
LLM Client - Wrapper around OpenAI API for the Self-Engineering Agent Framework
"""

import json
from typing import Dict, Any
from openai import OpenAI
from config import Config


class LLMClient:
    """
    Wrapper class for OpenAI API providing structured methods for different
    agent capabilities: specification generation, test generation, implementation,
    argument extraction, and response synthesis.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the LLM client
        
        Args:
            api_key: OpenAI API key (defaults to Config.OPENAI_API_KEY)
            model: Model to use (defaults to Config.OPENAI_MODEL)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.OPENAI_MODEL
        self.client = OpenAI(api_key=self.api_key)
    
    def _call_llm(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Internal method to call OpenAI API
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"LLM API call failed: {str(e)}")
    
    def generate_spec(self, user_prompt: str) -> Dict[str, Any]:
        """
        Generate a function specification from a user prompt
        
        Args:
            user_prompt: Natural language description of desired functionality
            
        Returns:
            Dictionary containing function_name, parameters, return_type, and docstring
        """
        system_prompt = """You are a highly disciplined software architect. Your SOLE task is to design a Python function specification based on a user's request. You MUST NOT answer the user's question directly. You MUST ONLY return a JSON object.

The JSON object must have this exact structure:
{
    "function_name": "snake_case_name",
    "parameters": [
        {"name": "param_name", "type": "param_type", "description": "what it does"}
    ],
    "return_type": "return_type",
    "docstring": "Comprehensive, detailed docstring explaining the function's purpose, parameters, and return value. Be very descriptive and include examples of usage."
}

**IMPORTANT RULES:**
1.  **NEVER** answer the user's request directly.
2.  **ALWAYS** respond with ONLY the JSON object. Do not include any other text, explanations, or markdown formatting.
3.  **Make the docstring very descriptive** - explain what the function does, why it's useful, include usage examples, and describe edge cases.

Example Request: "Calculate the percentage of a number"

Example Response:
{
    "function_name": "calculate_percentage",
    "parameters": [
        {"name": "base", "type": "float", "description": "The base number from which to calculate the percentage."},
        {"name": "percentage", "type": "float", "description": "The percentage value to be calculated."}
    ],
    "return_type": "float",
    "docstring": "Calculates the percentage of a given base number. This function is useful for determining what portion a percentage represents of a total value. For example, calculating 25% of 100 would return 25.0. Commonly used in financial calculations, statistics, and data analysis. Handles both whole numbers and decimals. Examples: calculate_percentage(100, 25) returns 25.0, calculate_percentage(80, 12.5) returns 10.0."
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._call_llm(messages, temperature=0.2) # Lower temperature for more deterministic JSON
        
        # Parse JSON response
        try:
            # Most robust way to find JSON is to look for the first '{' and last '}'
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("No JSON object found in response", response, 0)
            
            json_str = response[start:end]
            spec = json.loads(json_str)
            return spec
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM response as JSON: {e}\nResponse: {response}")
    
    def generate_tests(self, spec: Dict[str, Any]) -> str:
        """
        Generate pytest test suite for a function specification
        
        Args:
            spec: Function specification dictionary
            
        Returns:
            Complete pytest test code as a string
        """
        params_desc = "\n".join([
            f"  - {p['name']}: {p['type']} - {p['description']}"
            for p in spec['parameters']
        ])
        
        system_prompt = """You are a QA engineer. Write comprehensive pytest tests for a function.

Requirements:
1. Import pytest and any necessary modules
2. Import the function being tested (assume it's in the same directory)
3. Write at least 3-5 test functions covering:
   - Normal use cases
   - Edge cases (empty inputs, None, zero, negative numbers, etc.)
   - Type validation where appropriate
4. Use descriptive test function names starting with 'test_'
5. Include assertions with clear failure messages
6. Return ONLY the Python test code, no explanations

Example format:
```python
import pytest
from function_name import function_name

def test_function_normal_case():
    result = function_name(arg1, arg2)
    assert result == expected, "Description of what should happen"

def test_function_edge_case():
    # Test edge case
    ...
```"""
        
        user_content = f"""Function Specification:
Name: {spec['function_name']}
Parameters:
{params_desc}
Return Type: {spec['return_type']}
Description: {spec['docstring']}

Generate comprehensive pytest tests for this function."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self._call_llm(messages, temperature=0.3, max_tokens=1500)
        
        # Extract code from markdown blocks if present
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        return response
    
    def generate_implementation(self, spec: Dict[str, Any], tests: str) -> str:
        """
        Generate function implementation that passes the provided tests
        
        Args:
            spec: Function specification dictionary
            tests: Test code that the implementation must pass
            
        Returns:
            Complete function implementation code as a string
        """
        params_str = ", ".join([
            f"{p['name']}: {p['type']}"
            for p in spec['parameters']
        ])
        
        system_prompt = """You are a Python developer. Implement a function that passes ALL provided tests.

Requirements:
1. Write clean, efficient, production-quality code
2. Include proper type hints
3. Add the provided docstring
4. Handle edge cases appropriately
5. Ensure the code passes ALL tests
6. Return ONLY the Python function code, no explanations or test code

Example format:
```python
def function_name(param1: type1, param2: type2) -> return_type:
    \"\"\"
    Docstring here
    \"\"\"
    # Implementation
    return result
```"""
        
        user_content = f"""Function Specification:
Name: {spec['function_name']}
Signature: def {spec['function_name']}({params_str}) -> {spec['return_type']}
Docstring: {spec['docstring']}

Tests that must pass:
{tests}

Implement the function to pass ALL tests."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self._call_llm(messages, temperature=0.2, max_tokens=2000)
        
        # Extract code from markdown blocks if present
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        return response
    
    def extract_arguments(self, prompt: str, function_signature: str) -> Dict[str, Any]:
        """
        Extract function arguments from a natural language prompt
        
        Args:
            prompt: User's natural language request
            function_signature: Function signature with parameter info
            
        Returns:
            Dictionary mapping parameter names to extracted values
        """
        system_prompt = """You are a precise parameter extraction model. Your task is to extract argument values from a user's request based on a given function signature.

**CRITICAL RULES:**
1.  **ONLY extract values that are explicitly present in the user's request.**
2.  If a parameter's value is **NOT** in the request, return `null` for that parameter's value.
3.  You **MUST** return a JSON object. Do not include any other text or explanations.

Example 1:
Function: `def calculate_percentage(base: float, percentage: float) -> float`
User: "What is 15 percent of 300?"
Response: `{"base": 300.0, "percentage": 15.0}`

Example 2:
Function: `def celsius_to_fahrenheit(celsius: float) -> float`
User: "Convert 100 degrees Fahrenheit to Celsius"
Response: `{"celsius": null}`

Return ONLY the JSON object."""
        
        user_content = f"""Function Signature:
{function_signature}

User Request:
{prompt}

Extract the arguments as JSON."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self._call_llm(messages, temperature=0.0, max_tokens=500)
        
        # Parse JSON response
        try:
            # Most robust way to find JSON is to look for the first '{' and last '}'
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("No JSON object found in response", response, 0)
            
            json_str = response[start:end]
            args = json.loads(json_str)
            return args
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse argument extraction as JSON: {e}\nResponse: {response}")
    
    def synthesize_response(self, prompt: str, tool_result: Any) -> str:
        """
        Synthesize a natural language response from tool execution result
        
        Args:
            prompt: Original user prompt
            tool_result: Result returned by the tool
            
        Returns:
            Natural, conversational response string
        """
        system_prompt = """You are a helpful assistant. Given a user's question and a computed result, provide a natural, conversational response.

Keep it concise and friendly. Don't over-explain."""
        
        user_content = f"""User asked: {prompt}

Result: {tool_result}

Provide a helpful response."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = self._call_llm(messages, temperature=0.7, max_tokens=300)
        return response


if __name__ == "__main__":
    # Simple test
    client = LLMClient()
    print("LLM Client initialized successfully")

