"""
Workflow Tracker - Tracks tool execution patterns and session management
"""

import uuid
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from supabase import Client
from config import Config


class WorkflowTracker:
    """
    Tracks tool executions, manages sessions, and logs usage patterns
    for learning workflow relationships and compositions.
    """
    
    def __init__(self, supabase_client: Client = None):
        """
        Initialize the workflow tracker
        
        Args:
            supabase_client: Supabase client instance
        """
        from supabase import create_client
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.current_session_id = None
        self.session_tools = []  # Tools executed in current session
        self.session_start_time = None
    
    def start_session(self) -> str:
        """
        Start a new tracking session
        
        Returns:
            Session ID
        """
        self.current_session_id = str(uuid.uuid4())
        self.session_tools = []
        self.session_start_time = time.time()
        return self.current_session_id
    
    def end_session(self):
        """End the current tracking session and analyze patterns"""
        if self.current_session_id and len(self.session_tools) > 1:
            # Analyze the session for patterns
            self._analyze_session_patterns()
        
        self.current_session_id = None
        self.session_tools = []
        self.session_start_time = None
    
    def log_execution(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Any,
        success: bool,
        error_details: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        user_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Log a tool execution
        
        Args:
            tool_name: Name of the tool executed
            inputs: Input parameters
            outputs: Output result
            success: Whether execution was successful
            error_details: Error message if failed
            execution_time_ms: Execution time in milliseconds
            user_prompt: Original user prompt
            
        Returns:
            Execution record
        """
        # Ensure we have a session
        if not self.current_session_id:
            self.start_session()
        
        execution_order = len(self.session_tools)
        
        # Prepare data for database
        execution_data = {
            "session_id": self.current_session_id,
            "tool_name": tool_name,
            "execution_order": execution_order,
            "inputs": json.dumps(inputs) if inputs else None,
            "outputs": json.dumps(self._serialize_output(outputs)) if outputs is not None else None,
            "success": success,
            "error_details": error_details,
            "execution_time_ms": execution_time_ms,
            "user_prompt": user_prompt,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Insert into database
            result = self.supabase.table("tool_executions").insert(execution_data).execute()
            
            # Track in session
            self.session_tools.append({
                "tool_name": tool_name,
                "success": success,
                "order": execution_order
            })
            
            # Update relationships if there's a previous tool
            if execution_order > 0:
                previous_tool = self.session_tools[execution_order - 1]
                self._update_tool_relationship(
                    previous_tool["tool_name"],
                    tool_name,
                    success
                )
            
            return result.data[0] if result.data else execution_data
            
        except Exception as e:
            print(f"Warning: Failed to log execution: {str(e)}")
            return execution_data
    
    def _serialize_output(self, output: Any) -> Any:
        """Convert output to JSON-serializable format"""
        if isinstance(output, (str, int, float, bool, type(None))):
            return output
        elif isinstance(output, (list, tuple)):
            return [self._serialize_output(item) for item in output]
        elif isinstance(output, dict):
            return {k: self._serialize_output(v) for k, v in output.items()}
        else:
            return str(output)
    
    def _update_tool_relationship(
        self,
        tool_a: str,
        tool_b: str,
        success: bool
    ):
        """
        Update relationship between two tools
        
        Args:
            tool_a: First tool name
            tool_b: Second tool name
            success: Whether the sequence was successful
        """
        try:
            self.supabase.rpc(
                'update_tool_relationship',
                {
                    'p_tool_a': tool_a,
                    'p_tool_b': tool_b,
                    'p_relationship_type': 'sequence',
                    'p_success': success
                }
            ).execute()
        except Exception as e:
            print(f"Warning: Failed to update tool relationship: {str(e)}")
    
    def _analyze_session_patterns(self):
        """Analyze current session for workflow patterns"""
        if len(self.session_tools) < 2:
            return
        
        # Extract tool sequence
        tool_sequence = [tool["tool_name"] for tool in self.session_tools]
        
        # Check if this pattern exists
        try:
            # Search for existing pattern with matching tool sequence
            # Note: We need to compare arrays properly in PostgreSQL
            all_patterns = self.supabase.table("workflow_patterns").select("*").execute()
            
            existing_pattern = None
            if all_patterns.data:
                for pattern in all_patterns.data:
                    if pattern.get("tool_sequence") == tool_sequence:
                        existing_pattern = pattern
                        break
            
            result = type('obj', (object,), {'data': [existing_pattern] if existing_pattern else []})()

            
            if result.data:
                # Update existing pattern
                pattern = result.data[0]
                new_frequency = pattern["frequency"] + 1
                
                # Calculate success rate
                successful_tools = sum(1 for tool in self.session_tools if tool["success"])
                session_success_rate = successful_tools / len(self.session_tools)
                
                # Update average success rate
                new_success_rate = (
                    (pattern["avg_success_rate"] * pattern["frequency"] + session_success_rate) / 
                    new_frequency
                )
                
                # Update sessions list
                sessions = pattern.get("user_sessions", []) or []
                if self.current_session_id not in sessions:
                    sessions.append(self.current_session_id)
                
                self.supabase.table("workflow_patterns").update({
                    "frequency": new_frequency,
                    "avg_success_rate": new_success_rate,
                    "user_sessions": sessions,
                    "last_seen": datetime.now().isoformat()
                }).eq("id", pattern["id"]).execute()
                
            else:
                # Create new pattern
                pattern_name = "_to_".join(tool_sequence)
                successful_tools = sum(1 for tool in self.session_tools if tool["success"])
                success_rate = successful_tools / len(self.session_tools)
                
                pattern_data = {
                    "pattern_name": pattern_name,
                    "tool_sequence": tool_sequence,
                    "frequency": 1,
                    "avg_success_rate": success_rate,
                    "user_sessions": [self.current_session_id],
                    "complexity_score": len(tool_sequence),
                    "description": f"Workflow pattern: {' -> '.join(tool_sequence)}"
                }
                
                self.supabase.table("workflow_patterns").insert(pattern_data).execute()
                
        except Exception as e:
            print(f"Warning: Failed to analyze session patterns: {str(e)}")
    
    def get_tool_relationships(
        self,
        tool_name: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get tool relationships
        
        Args:
            tool_name: Filter by specific tool (optional)
            min_confidence: Minimum confidence score
            
        Returns:
            List of relationships
        """
        try:
            query = self.supabase.table("tool_relationships").select("*")
            
            if tool_name:
                query = query.or_(f"tool_a.eq.{tool_name},tool_b.eq.{tool_name}")
            
            query = query.gte("confidence_score", min_confidence)
            query = query.order("confidence_score", desc=True)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Warning: Failed to get tool relationships: {str(e)}")
            return []
    
    def get_workflow_patterns(
        self,
        min_frequency: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get detected workflow patterns
        
        Args:
            min_frequency: Minimum frequency threshold
            limit: Maximum number of patterns to return
            
        Returns:
            List of workflow patterns
        """
        try:
            result = self.supabase.table("workflow_patterns").select("*").gte(
                "frequency", min_frequency
            ).order("frequency", desc=True).limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Warning: Failed to get workflow patterns: {str(e)}")
            return []
    
    def get_session_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for a session
        
        Args:
            session_id: Session ID (uses current if not provided)
            limit: Maximum number of records
            
        Returns:
            List of executions
        """
        sid = session_id or self.current_session_id
        if not sid:
            return []
        
        try:
            result = self.supabase.table("tool_executions").select("*").eq(
                "session_id", sid
            ).order("execution_order").limit(limit).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Warning: Failed to get session history: {str(e)}")
            return []


if __name__ == "__main__":
    # Test the workflow tracker
    tracker = WorkflowTracker()
    
    # Start a session
    session_id = tracker.start_session()
    print(f"Started session: {session_id}")
    
    # Log some executions
    tracker.log_execution(
        tool_name="calculate_percentage",
        inputs={"base": 100, "percentage": 25},
        outputs=25.0,
        success=True,
        execution_time_ms=10
    )
    
    tracker.log_execution(
        tool_name="reverse_string",
        inputs={"s": "test"},
        outputs="tset",
        success=True,
        execution_time_ms=5
    )
    
    # End session
    tracker.end_session()
    print("Session ended and patterns analyzed")

