"""
Skill Graph - Typed workflow graphs with learned edges and caching
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from supabase import Client, create_client
from config import Config
from dataclasses import dataclass, asdict


@dataclass
class NodeSchema:
    """Schema definition for node inputs/outputs"""
    properties: Dict[str, Dict[str, Any]]  # JSON Schema properties
    required: List[str]
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format"""
        return {
            "type": "object",
            "properties": self.properties,
            "required": self.required
        }
    
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Simple validation of data against schema
        
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        for field in self.required:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Check types
        for field, value in data.items():
            if field in self.properties:
                expected_type = self.properties[field].get("type")
                if expected_type:
                    if expected_type == "string" and not isinstance(value, str):
                        return False, f"Field '{field}' should be string, got {type(value)}"
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        return False, f"Field '{field}' should be number, got {type(value)}"
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        return False, f"Field '{field}' should be boolean, got {type(value)}"
        
        return True, None


@dataclass
class SkillNode:
    """A node in the skill graph representing a tool or composite"""
    id: str
    name: str
    node_type: str  # 'tool', 'composite', 'decision', 'parallel'
    tool_name: Optional[str] = None
    input_schema: Optional[NodeSchema] = None
    output_schema: Optional[NodeSchema] = None
    cost_estimate: int = 0
    avg_latency_ms: int = 0
    success_rate: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SkillEdge:
    """An edge connecting two nodes with learned weights"""
    id: str
    from_node_id: str
    to_node_id: str
    edge_type: str = "sequence"  # 'sequence', 'conditional', 'parallel', 'fallback'
    data_flow_mapping: Optional[Dict[str, str]] = None  # Maps output fields to input fields
    weight: float = 1.0
    frequency: int = 0
    success_rate: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class SkillGraph:
    """
    Manages typed workflow graphs with learned edges, caching, and checkpointing.
    Enables structured, resumable, and cost-aware execution of tool compositions.
    """
    
    def __init__(self, supabase_client: Optional[Client] = None):
        """
        Initialize the skill graph
        
        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client or create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.nodes: Dict[str, SkillNode] = {}
        self.edges: List[SkillEdge] = []
    
    def create_node(
        self,
        name: str,
        node_type: str,
        tool_name: Optional[str] = None,
        input_schema: Optional[NodeSchema] = None,
        output_schema: Optional[NodeSchema] = None
    ) -> SkillNode:
        """
        Create a new node in the skill graph
        
        Args:
            name: Unique node name
            node_type: Type of node
            tool_name: Associated tool name (if applicable)
            input_schema: Input schema definition
            output_schema: Output schema definition
            
        Returns:
            Created SkillNode
        """
        try:
            # Insert into database
            node_data = {
                "node_name": name,
                "node_type": node_type,
                "tool_name": tool_name,
                "input_schema": input_schema.to_json_schema() if input_schema else None,
                "output_schema": output_schema.to_json_schema() if output_schema else None
            }
            
            result = self.supabase.table("skill_graph_nodes").insert(node_data).execute()
            
            if result.data:
                node_id = result.data[0]["id"]
                node = SkillNode(
                    id=node_id,
                    name=name,
                    node_type=node_type,
                    tool_name=tool_name,
                    input_schema=input_schema,
                    output_schema=output_schema
                )
                self.nodes[node_id] = node
                return node
            
            raise Exception("Failed to create node")
            
        except Exception as e:
            raise Exception(f"Failed to create skill graph node: {e}")
    
    def create_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        edge_type: str = "sequence",
        data_flow_mapping: Optional[Dict[str, str]] = None
    ) -> SkillEdge:
        """
        Create an edge between two nodes
        
        Args:
            from_node_id: Source node ID
            to_node_id: Destination node ID
            edge_type: Type of edge
            data_flow_mapping: How to map outputs to inputs
            
        Returns:
            Created SkillEdge
        """
        try:
            edge_data = {
                "from_node_id": from_node_id,
                "to_node_id": to_node_id,
                "edge_type": edge_type,
                "data_flow_mapping": data_flow_mapping or {}
            }
            
            result = self.supabase.table("skill_graph_edges").insert(edge_data).execute()
            
            if result.data:
                edge_id = result.data[0]["id"]
                edge = SkillEdge(
                    id=edge_id,
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    edge_type=edge_type,
                    data_flow_mapping=data_flow_mapping
                )
                self.edges.append(edge)
                return edge
            
            raise Exception("Failed to create edge")
            
        except Exception as e:
            raise Exception(f"Failed to create skill graph edge: {e}")
    
    def load_graph(self, node_ids: Optional[List[str]] = None):
        """
        Load nodes and edges from database
        
        Args:
            node_ids: Specific node IDs to load (None = load all)
        """
        try:
            # Load nodes
            nodes_query = self.supabase.table("skill_graph_nodes").select("*")
            if node_ids:
                nodes_query = nodes_query.in_("id", node_ids)
            
            nodes_result = nodes_query.execute()
            
            if nodes_result.data:
                for node_data in nodes_result.data:
                    # Parse schemas
                    input_schema = None
                    if node_data.get("input_schema"):
                        schema_dict = node_data["input_schema"]
                        input_schema = NodeSchema(
                            properties=schema_dict.get("properties", {}),
                            required=schema_dict.get("required", [])
                        )
                    
                    output_schema = None
                    if node_data.get("output_schema"):
                        schema_dict = node_data["output_schema"]
                        output_schema = NodeSchema(
                            properties=schema_dict.get("properties", {}),
                            required=schema_dict.get("required", [])
                        )
                    
                    node = SkillNode(
                        id=node_data["id"],
                        name=node_data["node_name"],
                        node_type=node_data["node_type"],
                        tool_name=node_data.get("tool_name"),
                        input_schema=input_schema,
                        output_schema=output_schema,
                        cost_estimate=node_data.get("cost_estimate", 0),
                        avg_latency_ms=node_data.get("avg_latency_ms", 0),
                        success_rate=node_data.get("success_rate", 1.0)
                    )
                    self.nodes[node.id] = node
            
            # Load edges
            if self.nodes:
                edges_result = self.supabase.table("skill_graph_edges").select("*").in_(
                    "from_node_id", list(self.nodes.keys())
                ).execute()
                
                if edges_result.data:
                    for edge_data in edges_result.data:
                        edge = SkillEdge(
                            id=edge_data["id"],
                            from_node_id=edge_data["from_node_id"],
                            to_node_id=edge_data["to_node_id"],
                            edge_type=edge_data.get("edge_type", "sequence"),
                            data_flow_mapping=edge_data.get("data_flow_mapping"),
                            weight=edge_data.get("weight", 1.0),
                            frequency=edge_data.get("frequency", 0),
                            success_rate=edge_data.get("success_rate", 1.0)
                        )
                        self.edges.append(edge)
                        
        except Exception as e:
            print(f"Warning: Failed to load skill graph: {e}")
    
    def get_execution_path(
        self,
        start_node_id: str,
        end_node_id: Optional[str] = None
    ) -> List[SkillNode]:
        """
        Get execution path between nodes using learned weights
        
        Args:
            start_node_id: Starting node
            end_node_id: Target node (None = return all reachable)
            
        Returns:
            List of nodes in execution order
        """
        # Simple breadth-first traversal weighted by edge success rates
        visited: Set[str] = set()
        path: List[SkillNode] = []
        queue: List[Tuple[str, List[str]]] = [(start_node_id, [start_node_id])]
        
        while queue:
            current_id, current_path = queue.pop(0)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            if current_id in self.nodes:
                path.append(self.nodes[current_id])
            
            if end_node_id and current_id == end_node_id:
                return path
            
            # Get outgoing edges sorted by weight
            outgoing = [e for e in self.edges if e.from_node_id == current_id]
            outgoing.sort(key=lambda e: e.weight * e.success_rate, reverse=True)
            
            for edge in outgoing:
                if edge.to_node_id not in visited:
                    queue.append((edge.to_node_id, current_path + [edge.to_node_id]))
        
        return path
    
    def check_cache(self, tool_name: str, inputs: Dict[str, Any]) -> Optional[Any]:
        """
        Check if result is cached for given tool and inputs
        
        Args:
            tool_name: Name of the tool
            inputs: Input parameters
            
        Returns:
            Cached output or None
        """
        try:
            # Compute input hash
            input_hash = self._compute_input_hash(inputs)
            
            # Query cache
            result = self.supabase.table("execution_cache").select("*").eq(
                "tool_name", tool_name
            ).eq("input_hash", input_hash).execute()
            
            if result.data and len(result.data) > 0:
                cached = result.data[0]

                # Check if expired
                expires_at = cached.get("expires_at")
                if expires_at:
                    # Parse datetime and make timezone-aware comparison
                    expiry_str = expires_at.replace('Z', '+00:00')
                    expiry = datetime.fromisoformat(expiry_str)
                    # Make current time timezone-aware if expiry is
                    from datetime import timezone
                    if expiry.tzinfo is not None:
                        now = datetime.now(timezone.utc)
                    else:
                        now = datetime.now()
                    if now > expiry:
                        return None
                
                # Update cache hits and last accessed
                self.supabase.table("execution_cache").update({
                    "cache_hits": cached["cache_hits"] + 1,
                    "last_accessed": datetime.now().isoformat()
                }).eq("id", cached["id"]).execute()
                
                return cached["outputs"]
            
            return None
            
        except Exception as e:
            print(f"Warning: Cache check failed: {e}")
            return None
    
    def cache_result(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Any,
        execution_time_ms: int,
        ttl_hours: Optional[int] = None
    ):
        """
        Cache a tool execution result
        
        Args:
            tool_name: Name of the tool
            inputs: Input parameters
            outputs: Output result
            execution_time_ms: Execution time
            ttl_hours: TTL in hours (None = no expiry)
        """
        try:
            input_hash = self._compute_input_hash(inputs)
            
            expires_at = None
            if ttl_hours:
                expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
            
            cache_data = {
                "tool_name": tool_name,
                "input_hash": input_hash,
                "inputs": inputs,
                "outputs": outputs,
                "execution_time_ms": execution_time_ms,
                "expires_at": expires_at
            }
            
            # Upsert (insert or update)
            self.supabase.table("execution_cache").upsert(cache_data).execute()
            
        except Exception as e:
            print(f"Warning: Failed to cache result: {e}")
    
    def _compute_input_hash(self, inputs: Dict[str, Any]) -> str:
        """
        Compute deterministic hash of inputs
        
        Args:
            inputs: Input dictionary
            
        Returns:
            SHA256 hash string
        """
        # Canonicalize JSON (sorted keys)
        canonical = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def update_node_metrics(
        self,
        node_id: str,
        success: bool,
        latency_ms: int,
        cost: int = 0
    ):
        """
        Update node performance metrics based on execution
        
        Args:
            node_id: Node ID
            success: Whether execution succeeded
            latency_ms: Execution latency
            cost: Cost in tokens or other units
        """
        try:
            # Get current metrics
            result = self.supabase.table("skill_graph_nodes").select("*").eq(
                "id", node_id
            ).execute()
            
            if result.data:
                node_data = result.data[0]
                
                # Update success rate (exponential moving average)
                alpha = 0.2
                old_success_rate = node_data.get("success_rate", 1.0)
                new_success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * old_success_rate
                
                # Update average latency
                old_latency = node_data.get("avg_latency_ms", 0)
                new_latency = (old_latency + latency_ms) / 2
                
                # Update cost estimate
                old_cost = node_data.get("cost_estimate", 0)
                new_cost = (old_cost + cost) / 2
                
                # Update database
                self.supabase.table("skill_graph_nodes").update({
                    "success_rate": new_success_rate,
                    "avg_latency_ms": int(new_latency),
                    "cost_estimate": int(new_cost)
                }).eq("id", node_id).execute()
                
        except Exception as e:
            print(f"Warning: Failed to update node metrics: {e}")
    
    def update_edge_metrics(
        self,
        from_node_id: str,
        to_node_id: str,
        success: bool,
        data_quality: float = 1.0
    ):
        """
        Update edge metrics based on execution
        
        Args:
            from_node_id: Source node
            to_node_id: Destination node
            success: Whether transition succeeded
            data_quality: Quality of data flow (0-1)
        """
        try:
            # Get edge
            result = self.supabase.table("skill_graph_edges").select("*").eq(
                "from_node_id", from_node_id
            ).eq("to_node_id", to_node_id).execute()
            
            if result.data:
                edge_data = result.data[0]
                
                # Update metrics
                alpha = 0.2
                old_success = edge_data.get("success_rate", 1.0)
                new_success = alpha * (1.0 if success else 0.0) + (1 - alpha) * old_success
                
                old_quality = edge_data.get("avg_data_quality", 1.0)
                new_quality = alpha * data_quality + (1 - alpha) * old_quality
                
                new_frequency = edge_data.get("frequency", 0) + 1
                
                # Update weight (combine success and data quality)
                new_weight = 0.7 * new_success + 0.3 * new_quality
                
                self.supabase.table("skill_graph_edges").update({
                    "frequency": new_frequency,
                    "success_rate": new_success,
                    "avg_data_quality": new_quality,
                    "weight": new_weight,
                    "last_used": datetime.now().isoformat()
                }).eq("id", edge_data["id"]).execute()
                
        except Exception as e:
            print(f"Warning: Failed to update edge metrics: {e}")


if __name__ == "__main__":
    # Test the skill graph
    graph = SkillGraph()
    
    # Create a sample node
    input_schema = NodeSchema(
        properties={
            "base": {"type": "number", "description": "Base value"},
            "percentage": {"type": "number", "description": "Percentage to calculate"}
        },
        required=["base", "percentage"]
    )
    
    output_schema = NodeSchema(
        properties={
            "result": {"type": "number", "description": "Calculated percentage"}
        },
        required=["result"]
    )
    
    print("Skill Graph module initialized")

