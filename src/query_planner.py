"""
Query Planner - Analyzes queries and plans multi-tool execution strategies
"""

from typing import Dict, Any, List, Optional, Tuple
from src.llm_client import LLMClient
from src.capability_registry import CapabilityRegistry
from supabase import Client
from config import Config
from src.utils import extract_json_from_response
import json


class QueryPlanner:
    """
    Analyzes user queries to determine complexity, decompose requirements,
    and plan optimal tool execution strategies.
    """
    
    def __init__(
        self,
        llm_client: LLMClient = None,
        registry: CapabilityRegistry = None,
        supabase_client: Client = None
    ):
        """
        Initialize the query planner
        
        Args:
            llm_client: LLM client for query analysis
            registry: Capability registry for tool lookup
            supabase_client: Supabase client for pattern matching
        """
        self.llm_client = llm_client or LLMClient()
        self.registry = registry or CapabilityRegistry()

        # Supabase already imported at module level (line 8)
        if supabase_client is None:
            from supabase import create_client
            self.supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        else:
            self.supabase = supabase_client
    
    def analyze_query(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze a user query to determine if it requires multiple tools
        
        Args:
            user_prompt: User's natural language request
            
        Returns:
            Dictionary with query analysis including:
            - is_complex: Whether query requires multiple tools
            - sub_tasks: List of identified sub-tasks
            - requires_composition: Whether to compose tools
            - execution_strategy: 'single', 'sequential', or 'composition'
        """
        system_prompt = """You are a query analysis expert. Analyze user requests to determine if they require multiple steps or tools.

IMPORTANT: Before breaking a request into multiple steps, consider if a SINGLE TOOL might handle the entire request.
For example:
- "Load CSV and calculate profit margins" = Single tool that loads and calculates
- "Read file and process data" = Single tool operation  
- "Get data and analyze it" = Single tool operation

Your task is to identify:
1. Whether the request is simple (single tool) or complex (multiple tools/steps)
2. If complex, break it down into specific sub-tasks ONLY if they truly need separate tools
3. Determine if tools need to be chained (output of one feeds into another)

Return ONLY a JSON object with this structure:
{
    "is_complex": boolean,
    "sub_tasks": [
        {
            "task": "description of sub-task",
            "order": 1,
            "depends_on": null or task_number
        }
    ],
    "requires_composition": boolean,
    "execution_strategy": "single" | "sequential" | "composition",
    "reasoning": "brief explanation"
}

Examples:

User: "What is 25% of 100?"
Response: {
    "is_complex": false,
    "sub_tasks": [{"task": "Calculate percentage", "order": 1, "depends_on": null}],
    "requires_composition": false,
    "execution_strategy": "single",
    "reasoning": "Simple single calculation"
}

User: "Load CSV file and calculate profit margins"
Response: {
    "is_complex": false,
    "sub_tasks": [{"task": "Load CSV file and calculate profit margins", "order": 1, "depends_on": null}],
    "requires_composition": false,
    "execution_strategy": "single",
    "reasoning": "Single operation - loading and calculating can be done by one tool"
}

User: "Calculate 25% of 100, then reverse the result as a string"
Response: {
    "is_complex": true,
    "sub_tasks": [
        {"task": "Calculate 25% of 100", "order": 1, "depends_on": null},
        {"task": "Convert result to string and reverse it", "order": 2, "depends_on": 1}
    ],
    "requires_composition": true,
    "execution_strategy": "composition",
    "reasoning": "Two operations where second depends on first result"
}

User: "Convert 20 Celsius to Fahrenheit and also calculate the square root of 144"
Response: {
    "is_complex": true,
    "sub_tasks": [
        {"task": "Convert 20 Celsius to Fahrenheit", "order": 1, "depends_on": null},
        {"task": "Calculate square root of 144", "order": 2, "depends_on": null}
    ],
    "requires_composition": false,
    "execution_strategy": "sequential",
    "reasoning": "Two independent operations"
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_client._call_llm(messages, temperature=0.1, max_tokens=800)

            # Parse JSON response
            json_str = extract_json_from_response(response)
            analysis = json.loads(json_str)

            # Add the original prompt
            analysis['original_prompt'] = user_prompt

            return analysis

        except Exception as e:
            print(f"Query analysis failed: {str(e)}")
            # Fallback to simple execution
            return {
                "is_complex": False,
                "sub_tasks": [{"task": user_prompt, "order": 1, "depends_on": None}],
                "requires_composition": False,
                "execution_strategy": "single",
                "reasoning": "Fallback to simple execution due to analysis error",
                "original_prompt": user_prompt
            }
    
    def find_matching_workflow_pattern(
        self,
        user_prompt: str,
        threshold: float = 0.6
    ) -> Optional[Dict[str, Any]]:
        """
        Search for existing workflow patterns that match the query
        
        Args:
            user_prompt: User's request
            threshold: Similarity threshold
            
        Returns:
            Matching workflow pattern or None
        """
        try:
            # Generate embedding for the query
            query_embedding = self.llm_client.generate_embedding(user_prompt)
            
            # Search for similar patterns
            result = self.supabase.rpc(
                'search_workflow_patterns',
                {
                    'query_embedding': query_embedding,
                    'similarity_threshold': threshold,
                    'match_count': 1
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                pattern = result.data[0]
                return {
                    'pattern_id': pattern['id'],
                    'pattern_name': pattern['pattern_name'],
                    'tool_sequence': pattern['tool_sequence'],
                    'frequency': pattern['frequency'],
                    'success_rate': pattern['avg_success_rate'],
                    'complexity': pattern['complexity_score'],
                    'similarity': pattern['similarity']
                }
            
            return None
            
        except Exception as e:
            print(f"Pattern search failed: {str(e)}")
            return None
    
    def find_matching_composite_tool(
        self,
        user_prompt: str,
        threshold: float = 0.5
    ) -> Optional[Dict[str, Any]]:
        """
        Search for existing composite tools that match the query
        
        Args:
            user_prompt: User's request
            threshold: Similarity threshold
            
        Returns:
            Matching composite tool or None
        """
        try:
            # Generate embedding for the query
            query_embedding = self.llm_client.generate_embedding(user_prompt)
            
            # Search for similar composite tools
            result = self.supabase.rpc(
                'search_composite_tools',
                {
                    'query_embedding': query_embedding,
                    'similarity_threshold': threshold,
                    'match_count': 1
                }
            ).execute()
            
            if result.data and len(result.data) > 0:
                composite = result.data[0]
                return {
                    'tool_id': composite['id'],
                    'tool_name': composite['name'],
                    'component_tools': composite['component_tools'],
                    'success_rate': composite['success_rate'],
                    'usage_count': composite['usage_count'],
                    'similarity': composite['similarity']
                }
            
            return None
            
        except Exception as e:
            print(f"Composite tool search failed: {str(e)}")
            return None
    
    def plan_execution(
        self,
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        Create a complete execution plan for a query
        
        Args:
            user_prompt: User's request
            
        Returns:
            Execution plan with strategy and tool selections
        """
        # First, check for existing composite tool
        composite_match = self.find_matching_composite_tool(user_prompt)
        if composite_match and composite_match['similarity'] > 0.7:
            return {
                'strategy': 'composite_tool',
                'composite_tool': composite_match,
                'reasoning': f"Found existing composite tool '{composite_match['tool_name']}' with {composite_match['similarity']:.2%} similarity"
            }
        
        # Check for workflow pattern
        pattern_match = self.find_matching_workflow_pattern(user_prompt)
        if pattern_match and pattern_match['similarity'] > 0.7:
            return {
                'strategy': 'workflow_pattern',
                'pattern': pattern_match,
                'reasoning': f"Found workflow pattern '{pattern_match['pattern_name']}' with {pattern_match['similarity']:.2%} similarity"
            }
        
        # Analyze the query complexity
        analysis = self.analyze_query(user_prompt)
        
        if not analysis['is_complex']:
            # Simple single-tool execution
            return {
                'strategy': 'single_tool',
                'analysis': analysis,
                'reasoning': 'Query requires single tool execution'
            }
        
        # Before proceeding with multi-tool execution, check if a single tool can handle it
        single_tool_match = self.registry.search_tool(user_prompt)
        if single_tool_match and single_tool_match['similarity_score'] > 0.6:
            # A single tool can handle this better than decomposing
            return {
                'strategy': 'single_tool',
                'analysis': {
                    'is_complex': False,
                    'sub_tasks': [{'task': user_prompt, 'order': 1, 'depends_on': None}],
                    'requires_composition': False,
                    'execution_strategy': 'single',
                    'reasoning': f'Single tool found that can handle the request'
                },
                'reasoning': f'Found single tool "{single_tool_match["name"]}" that can handle the entire request'
            }
        
        # Complex query - need multi-tool execution
        if analysis['requires_composition']:
            return {
                'strategy': 'multi_tool_composition',
                'analysis': analysis,
                'sub_tasks': analysis['sub_tasks'],
                'reasoning': 'Query requires multiple tools with data flow between them'
            }
        else:
            return {
                'strategy': 'multi_tool_sequential',
                'analysis': analysis,
                'sub_tasks': analysis['sub_tasks'],
                'reasoning': 'Query requires multiple independent tools'
            }
    
    def extract_sub_task_arguments(
        self,
        sub_task: Dict[str, Any],
        previous_results: List[Any],
        user_prompt: str
    ) -> Dict[str, Any]:
        """
        Extract arguments for a sub-task, potentially using previous results
        
        Args:
            sub_task: Sub-task definition
            previous_results: Results from previous sub-tasks
            user_prompt: Original user prompt
            
        Returns:
            Arguments dictionary for the sub-task
        """
        depends_on = sub_task.get('depends_on')
        
        if depends_on is not None and depends_on > 0:
            # This task depends on a previous result
            if depends_on <= len(previous_results):
                previous_result = previous_results[depends_on - 1]
                
                # Ask LLM to extract arguments including the previous result
                system_prompt = f"""Extract arguments for the sub-task. The previous step produced: {previous_result}
                
Use this result as needed for the current task. Return a JSON object with the arguments."""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Sub-task: {sub_task['task']}\nOriginal prompt: {user_prompt}"}
                ]
                
                try:
                    response = self.llm_client._call_llm(messages, temperature=0.0, max_tokens=300)
                    json_str = extract_json_from_response(response)
                    args = json.loads(json_str)
                    return args
                except (ValueError, json.JSONDecodeError):
                    pass
        
        # Fallback: just extract from the sub-task description
        return {}


if __name__ == "__main__":
    # Test the query planner
    planner = QueryPlanner()
    
    test_queries = [
        "What is 25% of 100?",
        "Calculate 15% of 300 and then reverse the result",
        "Convert 20 Celsius to Fahrenheit and calculate square root of 144"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        plan = planner.plan_execution(query)
        print(f"Strategy: {plan['strategy']}")
        print(f"Reasoning: {plan['reasoning']}")
        if 'analysis' in plan:
            print(f"Is Complex: {plan['analysis']['is_complex']}")
            print(f"Sub-tasks: {len(plan['analysis']['sub_tasks'])}")

