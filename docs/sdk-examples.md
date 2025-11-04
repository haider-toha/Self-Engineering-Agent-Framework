# SDK and Client Library Examples

## Overview

This document provides complete SDK and client library examples in multiple languages for integrating with the Self-Engineering Agent Framework. Each example demonstrates common workflows including session management, query submission, and tool retrieval.

## Table of Contents

1. [Python SDK](#python-sdk)
2. [JavaScript SDK](#javascript-sdk)
3. [cURL Examples](#curl-examples)
4. [Common Workflows](#common-workflows)

---

## Python SDK

### Installation

```bash
pip install requests python-socketio
```

### Complete Python Client Library

```python
"""
Self-Engineering Agent Framework - Python SDK
"""

import socketio
import requests
from typing import Callable, Optional, Dict, List, Any
import time


class AgentClient:
    """
    Python SDK for the Self-Engineering Agent Framework.
    
    Features:
    - Session management with conversational memory
    - Real-time query submission via WebSocket
    - Tool retrieval and inspection
    - Analytics and pattern discovery
    - Comprehensive error handling
    
    Example:
        >>> client = AgentClient('http://localhost:5001')
        >>> client.connect()
        >>> session_id = client.create_session()
        >>> result = client.submit_query_sync('Calculate profit margins from data.csv')
        >>> print(result['response'])
        >>> client.disconnect()
    """
    
    def __init__(self, base_url: str = 'http://localhost:5001'):
        """
        Initialize the agent client.
        
        Args:
            base_url: Base URL of the agent server
        """
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.sio = socketio.Client()
        self._setup_socket_handlers()
        self._query_result = None
        self._query_complete = False
        
    def _setup_socket_handlers(self):
        """Set up Socket.IO event handlers."""
        
        @self.sio.on('connect')
        def on_connect():
            print(f'Connected to agent at {self.base_url}')
            
        @self.sio.on('disconnect')
        def on_disconnect():
            print('Disconnected from agent')
            
        @self.sio.on('agent_event')
        def on_agent_event(data):
            if hasattr(self, '_event_callback') and self._event_callback:
                self._event_callback(data['event_type'], data['data'])
                
        @self.sio.on('query_complete')
        def on_query_complete(data):
            self._query_result = data
            self._query_complete = True
            if hasattr(self, '_complete_callback') and self._complete_callback:
                self._complete_callback(data)
                
        @self.sio.on('error')
        def on_error(data):
            print(f"Socket error: {data['message']}")
    
    def connect(self) -> None:
        """Connect to the agent server."""
        try:
            self.sio.connect(self.base_url)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}")
        
    def disconnect(self) -> None:
        """Disconnect from the agent server."""
        if self.sio.connected:
            self.sio.disconnect()
    
    def create_session(self) -> str:
        """
        Create a new conversational session.
        
        Returns:
            Session ID (UUID string)
            
        Raises:
            Exception: If session creation fails
        """
        response = requests.post(f'{self.base_url}/api/session')
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def submit_query(self, prompt: str, 
                    event_callback: Optional[Callable] = None,
                    complete_callback: Optional[Callable] = None) -> None:
        """
        Submit a query to the agent (async).
        
        Args:
            prompt: Natural language query
            event_callback: Function called for each agent event
            complete_callback: Function called when query completes
            
        Raises:
            Exception: If no active session
        """
        if not self.session_id:
            raise Exception("No active session. Call create_session() first.")
        
        self._event_callback = event_callback
        self._complete_callback = complete_callback
        self._query_complete = False
        self._query_result = None
        
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': self.session_id
        })
    
    def submit_query_sync(self, prompt: str, 
                         event_callback: Optional[Callable] = None,
                         timeout: int = 300) -> Dict:
        """
        Submit a query and wait for completion (sync).
        
        Args:
            prompt: Natural language query
            event_callback: Function called for each agent event
            timeout: Maximum wait time in seconds
            
        Returns:
            Query result dictionary
            
        Raises:
            TimeoutError: If query doesn't complete within timeout
        """
        self.submit_query(prompt, event_callback=event_callback)
        
        start_time = time.time()
        while not self._query_complete:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Query timed out after {timeout}s")
            time.sleep(0.1)
        
        return self._query_result
    
    def get_tools(self) -> List[Dict]:
        """
        Get all available tools.
        
        Returns:
            List of tool dictionaries
        """
        response = requests.get(f'{self.base_url}/api/tools')
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['tools']
        else:
            raise Exception(f"Failed to get tools: {data['error']}")
    
    def get_tool_details(self, tool_name: str) -> Dict:
        """
        Get detailed information about a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool details dictionary
        """
        response = requests.get(f'{self.base_url}/api/tools/{tool_name}')
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['tool']
        else:
            raise Exception(f"Failed to get tool: {data['error']}")
    
    def get_session_messages(self, limit: int = 10) -> List[Dict]:
        """
        Get recent messages from the current session.
        
        Args:
            limit: Maximum number of messages to return
            
        Returns:
            List of message dictionaries
        """
        if not self.session_id:
            raise Exception("No active session")
        
        response = requests.get(
            f'{self.base_url}/api/session/{self.session_id}/messages',
            params={'limit': limit}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['messages']
        else:
            raise Exception(f"Failed to get messages: {data['error']}")
    
    def get_workflow_patterns(self, min_frequency: int = 2, 
                             limit: int = 10) -> List[Dict]:
        """
        Get detected workflow patterns.
        
        Args:
            min_frequency: Minimum pattern occurrence count
            limit: Maximum patterns to return
            
        Returns:
            List of pattern dictionaries
        """
        response = requests.get(
            f'{self.base_url}/api/analytics/patterns',
            params={'min_frequency': min_frequency, 'limit': limit}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['patterns']
        else:
            raise Exception(f"Failed to get patterns: {data['error']}")
    
    def get_tool_relationships(self, tool_name: Optional[str] = None,
                              min_confidence: float = 0.5) -> List[Dict]:
        """
        Get tool relationship analytics.
        
        Args:
            tool_name: Filter for specific tool (optional)
            min_confidence: Minimum confidence score
            
        Returns:
            List of relationship dictionaries
        """
        params = {'min_confidence': min_confidence}
        if tool_name:
            params['tool_name'] = tool_name
            
        response = requests.get(
            f'{self.base_url}/api/analytics/relationships',
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['relationships']
        else:
            raise Exception(f"Failed to get relationships: {data['error']}")
    
    def get_workflow_stats(self) -> Dict:
        """
        Get overall workflow statistics.
        
        Returns:
            Statistics dictionary
        """
        response = requests.get(f'{self.base_url}/api/analytics/stats')
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['stats']
        else:
            raise Exception(f"Failed to get stats: {data['error']}")
    
    def wait(self) -> None:
        """Wait for all Socket.IO events to complete."""
        self.sio.wait()
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Usage Examples

def example_basic_query():
    """Example: Basic query submission."""
    client = AgentClient('http://localhost:5001')
    client.connect()
    
    # Create session
    session_id = client.create_session()
    print(f"Session: {session_id}")
    
    # Submit query
    result = client.submit_query_sync(
        'Calculate profit margins from data/ecommerce_products.csv'
    )
    
    if result['success']:
        print(f"Response: {result['response']}")
        print(f"Tool: {result['metadata']['tool_name']}")
    else:
        print(f"Error: {result['response']}")
    
    client.disconnect()


def example_with_events():
    """Example: Query with event tracking."""
    client = AgentClient('http://localhost:5001')
    client.connect()
    client.create_session()
    
    def on_event(event_type, data):
        print(f"[{event_type}] {data}")
    
    result = client.submit_query_sync(
        'Analyze sales trends from data.csv',
        event_callback=on_event
    )
    
    print(f"\nFinal result: {result['response']}")
    client.disconnect()


def example_context_manager():
    """Example: Using context manager."""
    with AgentClient('http://localhost:5001') as client:
        client.create_session()
        
        result = client.submit_query_sync('Load data from sales.csv')
        print(result['response'])


def example_tool_inspection():
    """Example: Inspecting available tools."""
    client = AgentClient('http://localhost:5001')
    client.connect()
    
    # Get all tools
    tools = client.get_tools()
    print(f"Available tools: {len(tools)}")
    
    for tool in tools[:5]:  # Show first 5
        print(f"\n{tool['name']}")
        print(f"  Description: {tool['docstring']}")
        
        # Get detailed info
        details = client.get_tool_details(tool['name'])
        print(f"  Lines of code: {len(details['code'].split(chr(10)))}")
    
    client.disconnect()


def example_analytics():
    """Example: Accessing analytics."""
    client = AgentClient('http://localhost:5001')
    client.connect()
    
    # Get workflow patterns
    patterns = client.get_workflow_patterns(min_frequency=3)
    print("Workflow patterns:")
    for pattern in patterns:
        print(f"  {pattern['pattern_name']}: {pattern['tool_sequence']}")
        print(f"    Frequency: {pattern['frequency']}, Success: {pattern['avg_success_rate']:.1%}")
    
    # Get tool relationships
    relationships = client.get_tool_relationships(min_confidence=0.7)
    print(f"\nTool relationships: {len(relationships)}")
    
    # Get overall stats
    stats = client.get_workflow_stats()
    print(f"\nTotal patterns: {stats['total_patterns']}")
    print(f"Total relationships: {stats['total_relationships']}")
    
    client.disconnect()


if __name__ == '__main__':
    # Run examples
    example_basic_query()
```

### Save as `agent_sdk.py`

To use the SDK:

```python
from agent_sdk import AgentClient

# Create client
client = AgentClient('http://localhost:5001')
client.connect()

# Create session
session_id = client.create_session()

# Submit query
result = client.submit_query_sync('Calculate profit margins from data.csv')
print(result['response'])

# Clean up
client.disconnect()
```

---

## JavaScript SDK

### Installation

```bash
npm install socket.io-client axios
```

### Complete JavaScript Client Library

```javascript
/**
 * Self-Engineering Agent Framework - JavaScript SDK
 */

const io = require('socket.io-client');
const axios = require('axios');

class AgentClient {
  /**
   * JavaScript SDK for the Self-Engineering Agent Framework.
   * 
   * @param {string} baseUrl - Base URL of the agent server
   * 
   * @example
   * const client = new AgentClient('http://localhost:5001');
   * await client.connect();
   * const sessionId = await client.createSession();
   * const result = await client.submitQuery('Calculate profit margins');
   * console.log(result.response);
   * client.disconnect();
   */
  constructor(baseUrl = 'http://localhost:5001') {
    this.baseUrl = baseUrl;
    this.sessionId = null;
    this.socket = null;
    this.eventCallback = null;
    this.completeCallback = null;
  }

  /**
   * Connect to the agent server.
   */
  connect() {
    return new Promise((resolve, reject) => {
      this.socket = io(this.baseUrl);

      this.socket.on('connect', () => {
        console.log(`Connected to agent at ${this.baseUrl}`);
        resolve();
      });

      this.socket.on('connect_error', (error) => {
        reject(new Error(`Connection failed: ${error.message}`));
      });

      this.socket.on('disconnect', () => {
        console.log('Disconnected from agent');
      });

      this.socket.on('agent_event', (data) => {
        if (this.eventCallback) {
          this.eventCallback(data.event_type, data.data);
        }
      });

      this.socket.on('query_complete', (data) => {
        if (this.completeCallback) {
          this.completeCallback(data);
        }
      });

      this.socket.on('error', (data) => {
        console.error(`Socket error: ${data.message}`);
      });
    });
  }

  /**
   * Disconnect from the agent server.
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }

  /**
   * Create a new conversational session.
   * 
   * @returns {Promise<string>} Session ID
   */
  async createSession() {
    try {
      const response = await axios.post(`${this.baseUrl}/api/session`);
      
      if (response.data.success) {
        this.sessionId = response.data.session_id;
        return this.sessionId;
      } else {
        throw new Error(`Failed to create session: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Session creation failed: ${error.message}`);
    }
  }

  /**
   * Submit a query to the agent.
   * 
   * @param {string} prompt - Natural language query
   * @param {Function} eventCallback - Callback for agent events
   * @returns {Promise<Object>} Query result
   */
  submitQuery(prompt, eventCallback = null) {
    return new Promise((resolve, reject) => {
      if (!this.sessionId) {
        reject(new Error('No active session. Call createSession() first.'));
        return;
      }

      this.eventCallback = eventCallback;
      this.completeCallback = (data) => {
        resolve(data);
      };

      this.socket.emit('query', {
        prompt: prompt,
        session_id: this.sessionId
      });
    });
  }

  /**
   * Get all available tools.
   * 
   * @returns {Promise<Array>} List of tools
   */
  async getTools() {
    try {
      const response = await axios.get(`${this.baseUrl}/api/tools`);
      
      if (response.data.success) {
        return response.data.tools;
      } else {
        throw new Error(`Failed to get tools: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get tools failed: ${error.message}`);
    }
  }

  /**
   * Get detailed information about a tool.
   * 
   * @param {string} toolName - Name of the tool
   * @returns {Promise<Object>} Tool details
   */
  async getToolDetails(toolName) {
    try {
      const response = await axios.get(`${this.baseUrl}/api/tools/${toolName}`);
      
      if (response.data.success) {
        return response.data.tool;
      } else {
        throw new Error(`Failed to get tool: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get tool details failed: ${error.message}`);
    }
  }

  /**
   * Get recent messages from the current session.
   * 
   * @param {number} limit - Maximum messages to return
   * @returns {Promise<Array>} List of messages
   */
  async getSessionMessages(limit = 10) {
    if (!this.sessionId) {
      throw new Error('No active session');
    }

    try {
      const response = await axios.get(
        `${this.baseUrl}/api/session/${this.sessionId}/messages`,
        { params: { limit } }
      );
      
      if (response.data.success) {
        return response.data.messages;
      } else {
        throw new Error(`Failed to get messages: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get messages failed: ${error.message}`);
    }
  }

  /**
   * Get detected workflow patterns.
   * 
   * @param {number} minFrequency - Minimum pattern occurrence
   * @param {number} limit - Maximum patterns to return
   * @returns {Promise<Array>} List of patterns
   */
  async getWorkflowPatterns(minFrequency = 2, limit = 10) {
    try {
      const response = await axios.get(
        `${this.baseUrl}/api/analytics/patterns`,
        { params: { min_frequency: minFrequency, limit } }
      );
      
      if (response.data.success) {
        return response.data.patterns;
      } else {
        throw new Error(`Failed to get patterns: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get patterns failed: ${error.message}`);
    }
  }

  /**
   * Get tool relationship analytics.
   * 
   * @param {string} toolName - Filter for specific tool (optional)
   * @param {number} minConfidence - Minimum confidence score
   * @returns {Promise<Array>} List of relationships
   */
  async getToolRelationships(toolName = null, minConfidence = 0.5) {
    try {
      const params = { min_confidence: minConfidence };
      if (toolName) {
        params.tool_name = toolName;
      }

      const response = await axios.get(
        `${this.baseUrl}/api/analytics/relationships`,
        { params }
      );
      
      if (response.data.success) {
        return response.data.relationships;
      } else {
        throw new Error(`Failed to get relationships: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get relationships failed: ${error.message}`);
    }
  }

  /**
   * Get overall workflow statistics.
   * 
   * @returns {Promise<Object>} Statistics
   */
  async getWorkflowStats() {
    try {
      const response = await axios.get(`${this.baseUrl}/api/analytics/stats`);
      
      if (response.data.success) {
        return response.data.stats;
      } else {
        throw new Error(`Failed to get stats: ${response.data.error}`);
      }
    } catch (error) {
      throw new Error(`Get stats failed: ${error.message}`);
    }
  }
}

// Usage Examples

async function exampleBasicQuery() {
  const client = new AgentClient('http://localhost:5001');
  
  try {
    await client.connect();
    
    const sessionId = await client.createSession();
    console.log(`Session: ${sessionId}`);
    
    const result = await client.submitQuery(
      'Calculate profit margins from data/ecommerce_products.csv'
    );
    
    if (result.success) {
      console.log(`Response: ${result.response}`);
      console.log(`Tool: ${result.metadata.tool_name}`);
    } else {
      console.error(`Error: ${result.response}`);
    }
  } finally {
    client.disconnect();
  }
}

async function exampleWithEvents() {
  const client = new AgentClient('http://localhost:5001');
  
  try {
    await client.connect();
    await client.createSession();
    
    const result = await client.submitQuery(
      'Analyze sales trends from data.csv',
      (eventType, data) => {
        console.log(`[${eventType}]`, data);
      }
    );
    
    console.log(`\nFinal result: ${result.response}`);
  } finally {
    client.disconnect();
  }
}

async function exampleToolInspection() {
  const client = new AgentClient('http://localhost:5001');
  
  try {
    await client.connect();
    
    const tools = await client.getTools();
    console.log(`Available tools: ${tools.length}`);
    
    for (const tool of tools.slice(0, 5)) {
      console.log(`\n${tool.name}`);
      console.log(`  Description: ${tool.docstring}`);
      
      const details = await client.getToolDetails(tool.name);
      console.log(`  Lines of code: ${details.code.split('\n').length}`);
    }
  } finally {
    client.disconnect();
  }
}

async function exampleAnalytics() {
  const client = new AgentClient('http://localhost:5001');
  
  try {
    await client.connect();
    
    const patterns = await client.getWorkflowPatterns(3);
    console.log('Workflow patterns:');
    for (const pattern of patterns) {
      console.log(`  ${pattern.pattern_name}: ${pattern.tool_sequence.join(' → ')}`);
      console.log(`    Frequency: ${pattern.frequency}, Success: ${(pattern.avg_success_rate * 100).toFixed(1)}%`);
    }
    
    const relationships = await client.getToolRelationships(null, 0.7);
    console.log(`\nTool relationships: ${relationships.length}`);
    
    const stats = await client.getWorkflowStats();
    console.log(`\nTotal patterns: ${stats.total_patterns}`);
    console.log(`Total relationships: ${stats.total_relationships}`);
  } finally {
    client.disconnect();
  }
}

// Export for use as module
module.exports = AgentClient;

// Run examples if executed directly
if (require.main === module) {
  exampleBasicQuery().catch(console.error);
}
```

### Save as `agent-sdk.js`

To use the SDK:

```javascript
const AgentClient = require('./agent-sdk');

(async () => {
  const client = new AgentClient('http://localhost:5001');
  
  await client.connect();
  const sessionId = await client.createSession();
  
  const result = await client.submitQuery('Calculate profit margins from data.csv');
  console.log(result.response);
  
  client.disconnect();
})();
```

---

## cURL Examples

### Create Session

```bash
# Create a new session
curl -X POST http://localhost:5001/api/session \
  -H "Content-Type: application/json"

# Response:
# {
#   "success": true,
#   "session_id": "550e8400-e29b-41d4-a716-446655440000"
# }
```

### Get Session Messages

```bash
# Get recent messages from a session
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

curl "http://localhost:5001/api/session/${SESSION_ID}/messages?limit=10"

# Response:
# {
#   "success": true,
#   "count": 2,
#   "messages": [
#     {
#       "role": "user",
#       "content": "Calculate profit margins",
#       "message_index": 0,
#       "created_at": "2025-11-04T10:30:00Z"
#     },
#     {
#       "role": "assistant",
#       "content": "The average profit margin is 23.5%",
#       "message_index": 1,
#       "created_at": "2025-11-04T10:30:15Z"
#     }
#   ]
# }
```

### Get All Tools

```bash
# List all available tools
curl http://localhost:5001/api/tools

# Response:
# {
#   "success": true,
#   "count": 15,
#   "tools": [
#     {
#       "name": "calculate_profit_margins",
#       "docstring": "Calculate profit margins from a CSV file",
#       "file_path": "tools/calculate_profit_margins.py",
#       "test_path": "tools/test_calculate_profit_margins.py",
#       "timestamp": "2025-11-04T10:30:00Z"
#     }
#   ]
# }
```

### Get Tool Details

```bash
# Get detailed information about a specific tool
TOOL_NAME="calculate_profit_margins"

curl "http://localhost:5001/api/tools/${TOOL_NAME}"

# Response:
# {
#   "success": true,
#   "tool": {
#     "name": "calculate_profit_margins",
#     "code": "import pandas as pd\n\ndef calculate_profit_margins(csv_path):\n    ...",
#     "test_code": "import pytest\n...",
#     "docstring": "Calculate profit margins from a CSV file",
#     "timestamp": "2025-11-04T10:30:00Z",
#     "file_path": "tools/calculate_profit_margins.py",
#     "test_path": "tools/test_calculate_profit_margins.py"
#   }
# }
```

### Get Workflow Patterns

```bash
# Get detected workflow patterns
curl "http://localhost:5001/api/analytics/patterns?min_frequency=2&limit=10"

# Response:
# {
#   "success": true,
#   "count": 5,
#   "patterns": [
#     {
#       "pattern_name": "data_analysis_workflow",
#       "tool_sequence": ["load_csv_data", "calculate_profit_margins", "generate_report"],
#       "frequency": 8,
#       "avg_success_rate": 0.95,
#       "confidence_score": 0.88
#     }
#   ]
# }
```

### Get Tool Relationships

```bash
# Get tool relationship analytics
curl "http://localhost:5001/api/analytics/relationships?min_confidence=0.5"

# With specific tool filter
TOOL_NAME="calculate_profit_margins"
curl "http://localhost:5001/api/analytics/relationships?tool_name=${TOOL_NAME}&min_confidence=0.7"

# Response:
# {
#   "success": true,
#   "count": 8,
#   "relationships": [
#     {
#       "tool_a": "calculate_profit_margins",
#       "tool_b": "analyze_sales_trends",
#       "confidence_score": 0.85,
#       "frequency": 12
#     }
#   ]
# }
```

### Get Session History

```bash
# Get execution history for a session
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

curl "http://localhost:5001/api/analytics/sessions/${SESSION_ID}?limit=100"

# Response:
# {
#   "success": true,
#   "session_id": "550e8400-e29b-41d4-a716-446655440000",
#   "count": 3,
#   "executions": [
#     {
#       "tool_name": "calculate_profit_margins",
#       "execution_order": 1,
#       "inputs": {"csv_path": "data/sales.csv"},
#       "outputs": {"average_margin": 23.5},
#       "success": true,
#       "execution_time_ms": 145,
#       "timestamp": "2025-11-04T10:30:15Z"
#     }
#   ]
# }
```

### Get Workflow Statistics

```bash
# Get overall workflow statistics
curl http://localhost:5001/api/analytics/stats

# Response:
# {
#   "success": true,
#   "stats": {
#     "total_patterns": 15,
#     "total_relationships": 42,
#     "most_frequent_pattern": {
#       "name": "data_analysis_workflow",
#       "frequency": 8,
#       "tools": ["load_csv_data", "calculate_profit_margins", "generate_report"]
#     },
#     "most_connected_tools": [
#       {"tool": "calculate_profit_margins", "connections": 12},
#       {"tool": "load_csv_data", "connections": 10}
#     ]
#   }
# }
```

### Complete Workflow Script

```bash
#!/bin/bash

# Complete workflow using cURL

BASE_URL="http://localhost:5001"

echo "Creating session..."
SESSION_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/session")
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')
echo "Session ID: ${SESSION_ID}"

echo -e "\nGetting available tools..."
TOOLS=$(curl -s "${BASE_URL}/api/tools")
TOOL_COUNT=$(echo $TOOLS | jq -r '.count')
echo "Available tools: ${TOOL_COUNT}"

echo -e "\nFirst 3 tools:"
echo $TOOLS | jq -r '.tools[:3][] | "  - \(.name): \(.docstring)"'

echo -e "\nGetting workflow patterns..."
PATTERNS=$(curl -s "${BASE_URL}/api/analytics/patterns?min_frequency=2")
echo $PATTERNS | jq -r '.patterns[] | "  \(.pattern_name): \(.tool_sequence | join(" → "))"'

echo -e "\nGetting workflow statistics..."
STATS=$(curl -s "${BASE_URL}/api/analytics/stats")
echo "Total patterns: $(echo $STATS | jq -r '.stats.total_patterns')"
echo "Total relationships: $(echo $STATS | jq -r '.stats.total_relationships')"

echo -e "\nDone!"
```

Save as `workflow.sh` and run:

```bash
chmod +x workflow.sh
./workflow.sh
```

---

## Common Workflows

### Workflow 1: Tool Synthesis (Python)

```python
from agent_sdk import AgentClient

client = AgentClient()
client.connect()
client.create_session()

# Request new tool synthesis
result = client.submit_query_sync(
    'Create a function to calculate compound interest with principal, rate, and time parameters',
    event_callback=lambda t, d: print(f"[{t}] {d}")
)

print(f"Tool created: {result['metadata']['tool_name']}")
print(f"Response: {result['response']}")

client.disconnect()
```

### Workflow 2: Multi-Tool Workflow (JavaScript)

```javascript
const AgentClient = require('./agent-sdk');

(async () => {
  const client = new AgentClient();
  await client.connect();
  await client.createSession();
  
  // Multi-step workflow
  const result = await client.submitQuery(
    'Load data from sales.csv, calculate profit margins, and generate a summary report',
    (eventType, data) => console.log(`[${eventType}]`, data)
  );
  
  console.log(`Result: ${result.response}`);
  client.disconnect();
})();
```

### Workflow 3: Conversational Interaction (cURL)

```bash
#!/bin/bash

BASE_URL="http://localhost:5001"

# Create session
SESSION_ID=$(curl -s -X POST "${BASE_URL}/api/session" | jq -r '.session_id')
echo "Session: ${SESSION_ID}"

# Note: For actual query submission, use WebSocket (Socket.IO)
# cURL is best for REST endpoints only

# Get conversation history
curl -s "${BASE_URL}/api/session/${SESSION_ID}/messages?limit=10" | jq '.messages'
```

### Workflow 4: Analytics Dashboard (Python)

```python
from agent_sdk import AgentClient
import json

client = AgentClient()
client.connect()

# Get comprehensive analytics
patterns = client.get_workflow_patterns(min_frequency=2)
relationships = client.get_tool_relationships(min_confidence=0.6)
stats = client.get_workflow_stats()
tools = client.get_tools()

# Create analytics report
report = {
    'total_tools': len(tools),
    'total_patterns': len(patterns),
    'total_relationships': len(relationships),
    'top_patterns': patterns[:5],
    'top_relationships': relationships[:10],
    'overall_stats': stats
}

print(json.dumps(report, indent=2))

client.disconnect()
```

---

## Additional Resources

- [REST API Documentation](openapi.yaml)
- [WebSocket Events Reference](websocket-events.md)
- [Python API Reference](python-api-reference.md)
- [Integration Guide](integration-guide.md)
- [GitHub Repository](https://github.com/haider-toha/Self-Engineering-Agent-Framework)
