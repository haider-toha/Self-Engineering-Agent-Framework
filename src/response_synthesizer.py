"""
Response Synthesizer - Converts tool outputs to natural language responses
"""

from typing import Any
from src.llm_client import LLMClient


class ResponseSynthesizer:
    """
    Synthesizes natural, conversational responses from tool execution results.
    """
    
    def __init__(self, llm_client: LLMClient = None):
        """
        Initialize the response synthesizer
        
        Args:
            llm_client: LLM client for response generation
        """
        self.llm_client = llm_client or LLMClient()
    
    def synthesize(self, user_prompt: str, tool_result: Any) -> str:
        """
        Synthesize a natural language response
        
        Args:
            user_prompt: Original user prompt
            tool_result: Result from tool execution
            
        Returns:
            Natural, conversational response string
        """
        try:
            response = self.llm_client.synthesize_response(user_prompt, tool_result)
            return response
        except Exception as e:
            # Fallback to simple formatting if LLM fails
            return f"Result: {tool_result}"
    
    def synthesize_error(self, user_prompt: str, error_message: str) -> str:
        """
        Synthesize a user-friendly error message
        
        Args:
            user_prompt: Original user prompt
            error_message: Technical error message
            
        Returns:
            User-friendly error explanation
        """
        try:
            error_prompt = f"The following error occurred while processing the request: {error_message}"
            response = self.llm_client.synthesize_response(user_prompt, error_prompt)
            return response
        except Exception:
            # Fallback
            return f"I encountered an error: {error_message}"
    
    def synthesize_synthesis_result(self, tool_name: str, user_prompt: str, tool_result: Any) -> str:
        """
        Synthesize response for a newly created and executed tool
        
        Args:
            tool_name: Name of the newly synthesized tool
            user_prompt: Original user prompt
            tool_result: Result from executing the new tool
            
        Returns:
            Natural response mentioning the new capability
        """
        enhanced_prompt = f"{user_prompt}\n\nNote: I just created a new capability called '{tool_name}' to answer this."
        return self.synthesize(enhanced_prompt, tool_result)


if __name__ == "__main__":
    # Simple test
    synthesizer = ResponseSynthesizer()
    print("Response Synthesizer initialized")
    
    # Test synthesis
    response = synthesizer.synthesize("What is 15% of 300?", 45.0)
    print(f"Sample response: {response}")

