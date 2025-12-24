"""
Utility functions for the Self-Engineering Agent Framework
"""


def extract_code_from_markdown(response: str) -> str:
    """
    Extract Python code from markdown code blocks

    Args:
        response: Text response that may contain markdown code blocks

    Returns:
        Extracted code string, or original response if no code blocks found
    """
    # Try to find python code block first
    if "```python" in response:
        parts = response.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0].strip()
            return code

    # Try generic code block
    elif "```" in response:
        parts = response.split("```")
        if len(parts) >= 3:
            # Take the first code block (index 1)
            code = parts[1].strip()
            return code

    # No code blocks found, return as-is
    return response.strip()


def extract_json_from_response(response: str) -> str:
    """
    Extract JSON object from text response

    Args:
        response: Text response that may contain JSON

    Returns:
        Extracted JSON string

    Raises:
        ValueError: If no JSON object found
    """
    start = response.find('{')
    end = response.rfind('}') + 1

    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")

    return response[start:end]


def summarize_result(result) -> str:
    """
    Create a concise summary of tool execution result for activity logs.
    
    Args:
        result: The result to summarize (any type)
        
    Returns:
        A concise string summary
    """
    if result is None:
        return "None"
    
    result_str = str(result)
    
    # If it's a list, show count and type info
    if isinstance(result, list):
        if len(result) == 0:
            return "Empty list"
        elif len(result) <= 3:
            return result_str
        else:
            # Show count and preview of first item
            first_item = str(result[0])[:100]
            if len(first_item) == 100:
                first_item += "..."
            return f"List of {len(result)} items. First: {first_item}"
    
    # If it's a dict, show key count
    elif isinstance(result, dict):
        if len(result) <= 5:
            return result_str
        else:
            keys = list(result.keys())[:3]
            return f"Dict with {len(result)} keys: {keys}..."
    
    # For strings/numbers, truncate if too long
    elif len(result_str) > 200:
        return result_str[:200] + "..."
    
    return result_str