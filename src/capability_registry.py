"""
Capability Registry - Supabase database storage and retrieval for agent tools
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import numpy as np
from config import Config


class CapabilityRegistry:
    """
    Manages the storage, indexing, and retrieval of agent capabilities using Supabase.
    Tools are stored as Python files with metadata in a Supabase database with vector search.
    """
    
    def __init__(self):
        """
        Initialize the capability registry with Supabase
        """
        self.tools_dir = Config.TOOLS_DIR
        
        # Ensure tools directory exists
        os.makedirs(self.tools_dir, exist_ok=True)
        
        # Initialize Supabase client
        self.supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Initialize sentence transformer for embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize database tables if needed
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """
        Ensure the required tables exist in Supabase
        """
        # This would be done via Supabase dashboard or migration
        # The table structure should be:
        # CREATE TABLE agent_tools (
        #   id TEXT PRIMARY KEY,
        #   name TEXT NOT NULL,
        #   file_path TEXT NOT NULL,
        #   test_path TEXT NOT NULL,
        #   docstring TEXT NOT NULL,
        #   timestamp TIMESTAMP NOT NULL,
        #   embedding VECTOR(384)  -- for all-MiniLM-L6-v2 model
        # );
        # CREATE INDEX ON agent_tools USING ivfflat (embedding vector_cosine_ops);
        pass
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        embedding = self.encoder.encode(text)
        return embedding.tolist()
    
    def add_tool(self, name: str, code: str, tests: str, docstring: str) -> Dict[str, Any]:
        """
        Add a new tool to the registry
        
        Args:
            name: Function name (snake_case)
            code: Python function implementation
            tests: Pytest test code
            docstring: Descriptive documentation
            
        Returns:
            Dictionary with tool metadata
        """
        # Create file paths
        tool_file = os.path.join(self.tools_dir, f"{name}.py")
        test_file = os.path.join(self.tools_dir, f"test_{name}.py")
        
        # Save code files
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(tests)
        
        # Generate embedding for the docstring
        embedding = self._generate_embedding(docstring)
        
        # Create metadata
        metadata = {
            "id": name,
            "name": name,
            "file_path": tool_file,
            "test_path": test_file,
            "created_at": datetime.now().isoformat(),
            "docstring": docstring,
            "embedding": embedding
        }
        
        # Insert into Supabase
        result = self.supabase.table("agent_tools").upsert(metadata).execute()
        
        if result.data:
            return metadata
        else:
            raise Exception(f"Failed to add tool to database: {result}")
    
    def search_tool(self, query: str, threshold: float = None) -> Optional[Dict[str, Any]]:
        """
        Search for a tool using semantic similarity
        
        Args:
            query: Natural language query
            threshold: Minimum similarity score (0-1), defaults to Config.SIMILARITY_THRESHOLD
            
        Returns:
            Tool information dictionary if found above threshold, None otherwise
        """
        threshold = threshold or Config.SIMILARITY_THRESHOLD
        
        # Generate embedding for query
        query_embedding = self._generate_embedding(query)
        
        # Search for similar tools using RPC function (you'll need to create this in Supabase)
        result = self.supabase.rpc(
            'search_tools', 
            {
                'query_embedding': query_embedding,
                'similarity_threshold': threshold,
                'match_count': 1
            }
        ).execute()
        
        if not result.data:
            return None
        
        tool_data = result.data[0]
        
        # Load the tool code
        try:
            with open(tool_data['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
        except FileNotFoundError:
            # Tool file missing, clean up database entry
            self.supabase.table("agent_tools").delete().eq("id", tool_data['id']).execute()
            return None
        
        # Return enriched tool info
        return {
            "name": tool_data['name'],
            "code": code,
            "file_path": tool_data['file_path'],
            "test_path": tool_data['test_path'],
            "docstring": tool_data['docstring'],
            "timestamp": tool_data['created_at'],
            "similarity_score": tool_data.get('similarity', 0)
        }
    
    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific tool by name
        
        Args:
            name: Tool function name
            
        Returns:
            Tool information dictionary if found, None otherwise
        """
        result = self.supabase.table("agent_tools").select("*").eq("name", name).execute()
        
        if not result.data:
            return None
        
        tool_data = result.data[0]
        
        # Load the tool code
        try:
            with open(tool_data['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
        except FileNotFoundError:
            # Tool file missing, clean up database entry
            self.supabase.table("agent_tools").delete().eq("id", name).execute()
            return None
        
        return {
            "name": tool_data['name'],
            "code": code,
            "file_path": tool_data['file_path'],
            "test_path": tool_data['test_path'],
            "docstring": tool_data['docstring'],
            "timestamp": tool_data['created_at']
        }
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered tools
        
        Returns:
            List of tool metadata dictionaries
        """
        result = self.supabase.table("agent_tools").select(
            "name, docstring, created_at, file_path"
        ).order("created_at", desc=True).execute()
        
        return result.data if result.data else []
    
    def delete_tool(self, name: str) -> bool:
        """
        Delete a tool from the registry
        
        Args:
            name: Tool function name
            
        Returns:
            True if deleted, False if not found
        """
        # Get tool info first
        tool = self.get_tool_by_name(name)
        if not tool:
            return False
        
        # Delete from database
        result = self.supabase.table("agent_tools").delete().eq("name", name).execute()
        
        # Delete files
        try:
            if os.path.exists(tool['file_path']):
                os.remove(tool['file_path'])
            if os.path.exists(tool['test_path']):
                os.remove(tool['test_path'])
        except Exception:
            pass  # Files might not exist
        
        return len(result.data) > 0
    
    def cleanup_orphaned_tools(self) -> int:
        """
        Remove tools from database that no longer have corresponding files
        
        Returns:
            Number of orphaned tools removed
        """
        removed_count = 0
        
        # Get all tools from database
        result = self.supabase.table("agent_tools").select("*").execute()
        
        if not result.data:
            return 0
        
        for tool_data in result.data:
            file_path = tool_data['file_path']
            
            # Check if the file still exists
            if not os.path.exists(file_path):
                print(f"Removing orphaned tool: {tool_data['name']} (file not found: {file_path})")
                try:
                    self.supabase.table("agent_tools").delete().eq("id", tool_data['id']).execute()
                    removed_count += 1
                except Exception as e:
                    print(f"Failed to remove {tool_data['name']}: {e}")
        
        return removed_count

    def count_tools(self) -> int:
        """
        Get the total number of registered tools
        
        Returns:
            Number of tools
        """
        result = self.supabase.table("agent_tools").select("id", count="exact").execute()
        return result.count if result.count else 0


if __name__ == "__main__":
    # Simple test
    registry = CapabilityRegistry()
    print(f"Capability Registry initialized with {registry.count_tools()} tools")

