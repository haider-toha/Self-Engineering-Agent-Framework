"""
LLM Client - Wrapper around OpenAI API for the Self-Engineering Agent Framework
"""

import json
from typing import Dict, Any, List
from openai import OpenAI
from config import Config
from src.utils import extract_code_from_markdown, extract_json_from_response


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
        system_prompt = """You are a highly disciplined software architect focused on ROBUST, PRODUCTION-READY code. Your SOLE task is to design a Python function specification based on a user's request. You MUST NOT answer the user's question directly. You MUST ONLY return a JSON object.

The JSON object must have this exact structure:
{
    "function_name": "snake_case_name",
    "parameters": [
        {"name": "param_name", "type": "param_type", "description": "what it does"}
    ],
    "return_type": "return_type",
    "docstring": "Comprehensive, detailed docstring explaining the function's purpose, parameters, and return value. Be very descriptive and include examples of usage."
}

**CRITICAL DESIGN PRINCIPLES:**
1.  **NEVER** answer the user's request directly.
2.  **ALWAYS** respond with ONLY the JSON object. No other text, explanations, or markdown formatting.
3.  **FLEXIBLE INPUT DESIGN**: For CSV/data operations:
    - Accept `Union[str, pd.DataFrame]` to support both file paths AND in-memory DataFrames
    - This enables both real-world usage (file paths) and easy testing (DataFrames)
    - Example: `data_source: Union[str, pd.DataFrame]` instead of just `file_path: str`
4.  **EDGE CASE FIRST THINKING**: Before designing the function, mentally consider ALL potential edge cases:
    - **Division by zero**: What if denominators are zero?
    - **Empty/null data**: What if inputs are empty, None, or missing?
    - **Invalid data types**: What if wrong types are passed?
    - **File operations**: What if files don't exist or are corrupted?
    - **Mathematical operations**: What about negative numbers, infinity, NaN?
    - **Data boundaries**: What about extremely large/small values?
5.  **ROBUST RETURN TYPES**: Design return types that can handle partial success/failure
6.  **COMPREHENSIVE DOCSTRING**: Must explain the function's purpose, parameters, return value, AND explicitly mention how edge cases are handled

Example Request: "Calculate the percentage of a number"

Example Response:
{
    "function_name": "calculate_percentage",
    "parameters": [
        {"name": "base", "type": "float", "description": "The base number from which to calculate the percentage."},
        {"name": "percentage", "type": "float", "description": "The percentage value to be calculated."}
    ],
    "return_type": "Dict[str, Any]",
    "docstring": "Calculates the percentage of a given base number with robust error handling. Returns a dictionary containing 'result' (float or None), 'success' (bool), and 'error' (str or None). Handles edge cases: zero/negative base numbers, extreme percentage values, invalid inputs. For example, calculate_percentage(100, 25) returns {'result': 25.0, 'success': True, 'error': None}. Used in financial calculations, statistics, and data analysis where reliability is crucial."
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self._call_llm(messages, temperature=0.2) # Lower temperature for more deterministic JSON

        # Parse JSON response
        try:
            json_str = extract_json_from_response(response)
            spec = json.loads(json_str)
            return spec
        except (json.JSONDecodeError, ValueError) as e:
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
        
        system_prompt = """You are an EXPERT QA engineer focused on BULLETPROOF testing. Write comprehensive pytest tests that are CONSISTENT with robust, production-ready implementations.

**CRITICAL PRINCIPLE: ROBUST FUNCTIONS HANDLE EDGE CASES GRACEFULLY**
- Modern production functions should NOT crash on edge cases
- They should return meaningful results or handle errors elegantly
- Division by zero should return NaN/inf, NOT raise exceptions
- Missing data should be handled with appropriate defaults
- Your tests must match this ROBUST behavior expectation

**MANDATORY EDGE CASE COVERAGE:**
1. **Mathematical Edge Cases**: Division by zero (expect NaN/inf, NOT errors), negative numbers, infinity, NaN
2. **Data Edge Cases**: Empty inputs, None values, missing data, invalid data types  
3. **File/CSV Edge Cases**: Missing columns, zero/negative values (handled gracefully)
4. **Boundary Cases**: Minimum/maximum values, empty datasets (should work, not fail)
5. **True Error Conditions**: Only test for errors when inputs are fundamentally invalid (None for required params, wrong types)

**REQUIREMENTS:**
1. Import ALL required modules: pytest, pandas as pd, numpy as np, from io import StringIO
2. Import the function being tested
3. Write 7-10 test functions covering:
   - **Normal use cases** (2-3 tests) - assert success == True
   - **Mathematical edge cases** - expect graceful handling (NaN for division by zero, NOT errors)
   - **Data edge cases** - expect graceful handling with appropriate defaults
   - **Only test failures for truly invalid inputs** (None for required params, fundamentally wrong types)
4. Use descriptive test function names: `test_function_edge_case_description`
5. **CONSISTENT ASSERTIONS**: If function returns dict with 'success' key, test BOTH success and result fields
6. Return ONLY the Python test code, no explanations

**CRITICAL FILE TESTING RULES:**
- The test environment is READ-ONLY - you CANNOT write any files
- For file-based functions: Pass the file path directly (e.g., "data/ecommerce_products.csv")
- For edge case testing: Create DataFrames in memory and pass them directly to the function
- NEVER use df.to_csv() or any file writing operations in tests
- If the function requires a file path parameter, test with existing files only
- If the function can accept DataFrames, create test DataFrames in memory

Example format:
```python
import pytest
import pandas as pd
from io import StringIO
from function_name import function_name

def test_function_with_real_csv_file():
    # Test with actual file that exists in the sandbox
    result = function_name("data/ecommerce_products.csv")
    assert result is not None, "Should process existing CSV file"
    if not result.get('success'):
        print(f"Debug - Error: {result.get('error')}")
        print(f"Debug - Full result: {result}")
    assert result['success'] == True, f"Should successfully load file. Error: {result.get('error', 'unknown')}"

def test_function_with_edge_case_data():
    # For edge cases: Create DataFrame in memory (don't write to file)
    test_data = pd.DataFrame({
        'col1': [0, -1, 100],
        'col2': [1, 2, 0]  # Edge case: zero values
    })
    # If function accepts DataFrame, pass it directly
    result = function_name(test_data)
    assert result is not None, "Should handle edge case data"

def test_function_division_by_zero():
    # Test edge case with in-memory data
    zero_data = pd.DataFrame({'price': [0], 'cost': [10]})
    result = function_name(zero_data)
    assert result['success'] == False or result['error'] is not None, "Should handle division by zero"
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
        test_code = extract_code_from_markdown(response)
        
        # Ensure required imports are present
        test_code = self._ensure_test_imports(test_code)
        
        return test_code
    
    def _ensure_test_imports(self, test_code: str) -> str:
        """
        Ensure that required imports are present in test code
        
        Args:
            test_code: Generated test code
            
        Returns:
            Test code with required imports added if missing
        """
        required_imports = [
            "import pytest",
            "import pandas as pd",
            "import numpy as np", 
            "from io import StringIO"
        ]
        
        # Check which imports are missing
        missing_imports = []
        for imp in required_imports:
            if imp not in test_code:
                missing_imports.append(imp)
        
        # Add missing imports at the beginning
        if missing_imports:
            import_section = "\n".join(missing_imports) + "\n\n"
            # Find the first non-import line to insert before it
            lines = test_code.split('\n')
            insert_index = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith(('import ', 'from ')):
                    insert_index = i
                    break
            
            lines.insert(insert_index, import_section)
            test_code = '\n'.join(lines)
        
        return test_code
    
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
        
        system_prompt = """You are a SENIOR Python developer specializing in PRODUCTION-READY, BULLETPROOF code. Implement a function that passes ALL provided tests with ROBUST error handling.

**CRITICAL IMPLEMENTATION PRINCIPLES:**
1. **FLEXIBLE INPUT HANDLING**: For file/data operations, check if input is a file path (str) or DataFrame
   - If str: Load the file with pd.read_csv() with proper error handling
   - If DataFrame: Use directly
   - Example: `if isinstance(data_source, str): df = pd.read_csv(data_source) else: df = data_source`
2. **EDGE-CASE FIRST DESIGN**: Handle ALL edge cases explicitly before normal cases
3. **DEFENSIVE PROGRAMMING**: Validate ALL inputs, assume nothing about data quality
4. **GRACEFUL FAILURE**: Never crash - return structured error information instead
5. **MATHEMATICAL SAFETY**: Check for division by zero, NaN, infinity before calculations
6. **DATA VALIDATION**: Verify data types, check for None/empty values, validate ranges
7. **FILE SAFETY**: Handle missing files, corrupted data, malformed CSV gracefully

**MANDATORY ERROR HANDLING PATTERNS:**
- **Try-catch blocks** around ALL risky operations (file I/O, math, data access)
- **Input validation** at function start (type checks, None checks, range validation)
- **Safe mathematical operations** (check denominators before division)
- **Structured return values** that include success/error information
- **Clear error messages** that help diagnose the specific problem

**REQUIREMENTS:**
1. Write clean, efficient, production-quality code that NEVER crashes
2. Include proper type hints for ALL parameters and return values
3. Add the provided docstring exactly
4. Handle edge cases with explicit checks and safe fallbacks
5. Ensure the code passes ALL tests (including edge case tests)
6. Return ONLY the Python function code, no explanations or test code

Example format:
```python
def function_name(param1: type1, param2: type2) -> Dict[str, Any]:
    \"\"\"
    Docstring here
    \"\"\"
    # Input validation
    if param1 is None:
        return {"success": False, "result": None, "error": "param1 cannot be None"}
    
    try:
        # Safe operations with edge case handling
        if param2 == 0:  # Division by zero check
            return {"success": False, "result": None, "error": "Division by zero"}
        
        # Main logic
        result = param1 / param2
        
        return {"success": True, "result": result, "error": None}
    
    except Exception as e:
        return {"success": False, "result": None, "error": f"Unexpected error: {str(e)}"}
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
        return extract_code_from_markdown(response)
    
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
            json_str = extract_json_from_response(response)
            args = json.loads(json_str)
            return args
        except (json.JSONDecodeError, ValueError) as e:
            raise Exception(f"Failed to parse argument extraction as JSON: {e}\nResponse: {response}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text using OpenAI's embedding model
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding (1536 dimensions)
        """
        try:
            response = self.client.embeddings.create(
                model=Config.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"Embedding generation failed: {str(e)}")
    
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

