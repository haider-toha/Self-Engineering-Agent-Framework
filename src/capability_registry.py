"""
Capability Registry - Vector database storage and retrieval for agent tools
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import chromadb
from chromadb.config import Settings
from config import Config


class CapabilityRegistry:
    """
    Manages the storage, indexing, and retrieval of agent capabilities using ChromaDB.
    Tools are stored as Python files with metadata in a vector database for semantic search.
    """
    
    def __init__(self, persist_dir: str = None, collection_name: str = "agent_tools"):
        """
        Initialize the capability registry
        
        Args:
            persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection
        """
        self.persist_dir = persist_dir or Config.CHROMA_PERSIST_DIR
        self.collection_name = collection_name
        self.tools_dir = Config.TOOLS_DIR
        
        # Ensure directories exist
        os.makedirs(self.persist_dir, exist_ok=True)
        os.makedirs(self.tools_dir, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
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
        
        # Create metadata
        metadata = {
            "name": name,
            "file_path": tool_file,
            "test_path": test_file,
            "timestamp": datetime.now().isoformat(),
            "docstring": docstring
        }
        
        # Add to vector database (ChromaDB automatically generates embeddings)
        self.collection.add(
            documents=[docstring],  # The text to embed
            metadatas=[metadata],
            ids=[name]
        )
        
        return metadata
    
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
        
        # Check if collection is empty
        if self.collection.count() == 0:
            return None
        
        # Query the vector database
        results = self.collection.query(
            query_texts=[query],
            n_results=1
        )
        
        # Check if we have results
        if not results['ids'] or not results['ids'][0]:
            return None
        
        # Get the best match
        tool_id = results['ids'][0][0]
        metadata = results['metadatas'][0][0]
        distance = results['distances'][0][0]
        
        # Convert distance to similarity score (ChromaDB returns cosine distance)
        similarity = 1 - distance
        
        # Check threshold
        if similarity < threshold:
            return None
        
        # Load the tool code
        with open(metadata['file_path'], 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Return enriched tool info
        return {
            "name": metadata['name'],
            "code": code,
            "file_path": metadata['file_path'],
            "test_path": metadata['test_path'],
            "docstring": metadata['docstring'],
            "timestamp": metadata['timestamp'],
            "similarity_score": similarity
        }
    
    def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific tool by name
        
        Args:
            name: Tool function name
            
        Returns:
            Tool information dictionary if found, None otherwise
        """
        try:
            result = self.collection.get(ids=[name])
            
            if not result['ids']:
                return None
            
            metadata = result['metadatas'][0]
            
            # Load the tool code
            with open(metadata['file_path'], 'r', encoding='utf-8') as f:
                code = f.read()
            
            return {
                "name": metadata['name'],
                "code": code,
                "file_path": metadata['file_path'],
                "test_path": metadata['test_path'],
                "docstring": metadata['docstring'],
                "timestamp": metadata['timestamp']
            }
        except Exception:
            return None
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered tools
        
        Returns:
            List of tool metadata dictionaries
        """
        if self.collection.count() == 0:
            return []
        
        # Get all items from collection
        results = self.collection.get()
        
        tools = []
        for i, tool_id in enumerate(results['ids']):
            metadata = results['metadatas'][i]
            tools.append({
                "name": metadata['name'],
                "docstring": metadata['docstring'],
                "timestamp": metadata['timestamp'],
                "file_path": metadata['file_path']
            })
        
        # Sort by timestamp (newest first)
        tools.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return tools
    
    def delete_tool(self, name: str) -> bool:
        """
        Delete a tool from the registry
        
        Args:
            name: Tool function name
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Get metadata first
            tool = self.get_tool_by_name(name)
            if not tool:
                return False
            
            # Delete from vector database
            self.collection.delete(ids=[name])
            
            # Delete files
            if os.path.exists(tool['file_path']):
                os.remove(tool['file_path'])
            if os.path.exists(tool['test_path']):
                os.remove(tool['test_path'])
            
            return True
        except Exception:
            return False
    
    def cleanup_orphaned_tools(self) -> int:
        """
        Remove tools from ChromaDB that no longer have corresponding files
        
        Returns:
            Number of orphaned tools removed
        """
        removed_count = 0
        
        if self.collection.count() == 0:
            return 0
        
        # Get all tools from ChromaDB
        all_results = self.collection.get()
        
        for i, tool_id in enumerate(all_results['ids']):
            metadata = all_results['metadatas'][i]
            file_path = metadata['file_path']
            
            # Check if the file still exists
            if not os.path.exists(file_path):
                print(f"Removing orphaned tool: {tool_id} (file not found: {file_path})")
                try:
                    self.collection.delete(ids=[tool_id])
                    removed_count += 1
                except Exception as e:
                    print(f"Failed to remove {tool_id}: {e}")
        
        return removed_count

    def count_tools(self) -> int:
        """
        Get the total number of registered tools
        
        Returns:
            Number of tools
        """
        return self.collection.count()


if __name__ == "__main__":
    # Simple test
    registry = CapabilityRegistry()
    print(f"Capability Registry initialized with {registry.count_tools()} tools")

