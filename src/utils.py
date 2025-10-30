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
