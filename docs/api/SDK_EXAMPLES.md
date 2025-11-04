# SDK/Client Library Examples

This document provides complete SDK implementations and usage examples for integrating with the Self-Engineering Agent Framework in Python and JavaScript.

## Table of Contents

1. [Python SDK](#python-sdk)
2. [JavaScript SDK](#javascript-sdk)
3. [Usage Examples](#usage-examples)
4. [Advanced Features](#advanced-features)

---

## Python SDK

### Installation

```bash
pip install requests python-socketio[client]
```

### Complete SDK Implementation

```python
"""
Self-Engineering Agent Framework Python SDK

A comprehensive client library for interacting with the Self-Engineering Agent Framework API.
"""

import requests
import socketio
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Agent event types"""
    SEARCHING = "searching"
    TOOL_FOUND = "tool_found"
    NO_TOOL_FOUND = "no_tool_found"
    EXECUTING = "executing"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_FAILED = "execution_failed"
    SYNTHESIS_STEP = "synthesis_step"
    SYNTHESIS_SUCCESSFUL = "synthesis_successful"
    SYNTHESIS_FAILED = "synthesis_failed"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_STEP = "workflow_step"
    WORKFLOW_COMPLETE = "workflow_complete"
    ERROR = "error"


@dataclass
class QueryResult:
    """Result of a query execution"""
    success: bool
    response: str
    tool_name: Optional[str] = None
    tool_result: Optional[Any] = None
    synthesized: bool = False
    session_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Tool:
    """Tool information"""
    name: str
    docstring: str
    created_at: str
    file_path: str
    code: Optional[str] = None
    test_code: Optional[str] = None
    timestamp: Optional[str] = None
    test_path: Optional[str] = None


class AgentSDK:
    """
    Python SDK for Self-Engineering Agent Framework
    
    Example:
        >>> sdk = AgentSDK("http://localhost:5001")
        >>> sdk.connect()
        >>> session_id = sdk.create_session()
        >>> result = sdk.submit_query("Calculate factorial of 5", session_id)
        >>> print(result.response)
        >>> sdk.disconnect()
    """
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        """
        Initialize the SDK
        
        Args:
            base_url: Base URL of the agent server
        """
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = None
        self.sio = socketio.Client()
        self._event_handlers = {}
        self._query_results = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Setup default Socket.IO event handlers"""
        
        @self.sio.on('connect')
        def on_connect():
            self._trigger_event('connect', {})
        
        @self.sio.on('connected')
        def on_connected(data):
            self._trigger_event('connected', data)
        
        @self.sio.on('tool_count')
        def on_tool_count(data):
            self._trigger_event('tool_count', data)
        
        @self.sio.on('agent_event')
        def on_agent_event(event):
            self._trigger_event('agent_event', event)
        
        @self.sio.on('query_complete')
        def on_query_complete(result):
            query_id = result.get('session_id', 'default')
            self._query_results[query_id] = result
            self._trigger_event('query_complete', result)
        
        @self.sio.on('session_memory')
        def on_session_memory(data):
            self._trigger_event('session_memory', data)
        
        @self.sio.on('error')
        def on_error(error):
            self._trigger_event('error', error)
    
    def on(self, event: str, handler: Callable):
        """
        Register an event handler
        
        Args:
            event: Event name
            handler: Callback function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    def _trigger_event(self, event: str, data: Any):
        """Trigger registered event handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def connect(self, timeout: int = 5) -> bool:
        """
        Connect to the agent server
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected successfully
        """
        try:
            self.sio.connect(self.base_url, wait_timeout=timeout)
            time.sleep(0.5)  # Wait for connection to stabilize
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.base_url}: {e}")
    
    def disconnect(self):
        """Disconnect from the agent server"""
        if self.sio.connected:
            self.sio.disconnect()
    
    def create_session(self) -> str:
        """
        Create a new session for conversational memory
        
        Returns:
            Session identifier
        """
        response = requests.post(f"{self.api_url}/session")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def submit_query(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        wait: bool = True,
        timeout: int = 30
    ) -> QueryResult:
        """
        Submit a query to the agent
        
        Args:
            prompt: User's natural language request
            session_id: Session identifier (uses default if not provided)
            wait: Whether to wait for completion
            timeout: Maximum wait time in seconds
            
        Returns:
            QueryResult object
        """
        sid = session_id or self.session_id
        if not sid:
            raise Exception("No active session. Call create_session() first.")
        
        # Clear previous result
        if sid in self._query_results:
            del self._query_results[sid]
        
        # Submit query
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': sid
        })
        
        if not wait:
            return None
        
        # Wait for result
        start_time = time.time()
        while sid not in self._query_results:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Query timed out after {timeout} seconds")
            time.sleep(0.1)
        
        result = self._query_results[sid]
        return QueryResult(
            success=result['success'],
            response=result['response'],
            tool_name=result['metadata'].get('tool_name'),
            tool_result=result['metadata'].get('tool_result'),
            synthesized=result['metadata'].get('synthesized', False),
            session_id=result.get('session_id'),
            error=result.get('error')
        )
    
    def get_tools(self) -> List[Tool]:
        """
        Get list of all available tools
        
        Returns:
            List of Tool objects
        """
        response = requests.get(f"{self.api_url}/tools")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return [Tool(**tool) for tool in data['tools']]
        else:
            raise Exception(f"Failed to get tools: {data['error']}")
    
    def get_tool(self, tool_name: str) -> Tool:
        """
        Get detailed information about a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool object with code and tests
        """
        response = requests.get(f"{self.api_url}/tools/{tool_name}")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return Tool(**data['tool'])
        else:
            raise Exception(f"Failed to get tool: {data['error']}")
    
    def get_session_messages(
        self,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages for a session
        
        Args:
            session_id: Session identifier (uses default if not provided)
            limit: Maximum number of messages
            
        Returns:
            List of message dictionaries
        """
        sid = session_id or self.session_id
        if not sid:
            raise Exception("No active session")
        
        response = requests.get(
            f"{self.api_url}/session/{sid}/messages",
            params={'limit': limit}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['messages']
        else:
            raise Exception(f"Failed to get messages: {data['error']}")
    
    def get_workflow_patterns(
        self,
        min_frequency: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get detected workflow patterns
        
        Args:
            min_frequency: Minimum pattern frequency
            limit: Maximum number of patterns
            
        Returns:
            List of workflow pattern dictionaries
        """
        response = requests.get(
            f"{self.api_url}/analytics/patterns",
            params={'min_frequency': min_frequency, 'limit': limit}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['patterns']
        else:
            raise Exception(f"Failed to get patterns: {data['error']}")
    
    def get_tool_relationships(
        self,
        tool_name: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get tool relationship analytics
        
        Args:
            tool_name: Filter by specific tool
            min_confidence: Minimum confidence score
            
        Returns:
            List of relationship dictionaries
        """
        params = {'min_confidence': min_confidence}
        if tool_name:
            params['tool_name'] = tool_name
        
        response = requests.get(
            f"{self.api_url}/analytics/relationships",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['relationships']
        else:
            raise Exception(f"Failed to get relationships: {data['error']}")
    
    def get_session_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for a session
        
        Args:
            session_id: Session identifier (uses default if not provided)
            limit: Maximum number of executions
            
        Returns:
            List of execution dictionaries
        """
        sid = session_id or self.session_id
        if not sid:
            raise Exception("No active session")
        
        response = requests.get(
            f"{self.api_url}/analytics/sessions/{sid}",
            params={'limit': limit}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['executions']
        else:
            raise Exception(f"Failed to get history: {data['error']}")
    
    def get_workflow_stats(self) -> Dict[str, Any]:
        """
        Get overall workflow statistics
        
        Returns:
            Statistics dictionary
        """
        response = requests.get(f"{self.api_url}/analytics/stats")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['stats']
        else:
            raise Exception(f"Failed to get stats: {data['error']}")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# Convenience function
def create_client(base_url: str = "http://localhost:5001") -> AgentSDK:
    """
    Create and connect an agent client
    
    Args:
        base_url: Base URL of the agent server
        
    Returns:
        Connected AgentSDK instance
    """
    sdk = AgentSDK(base_url)
    sdk.connect()
    return sdk
```

### Python Usage Examples

#### Basic Usage

```python
from agent_sdk import AgentSDK

# Initialize SDK
sdk = AgentSDK("http://localhost:5001")

try:
    # Connect to server
    sdk.connect()
    
    # Create a session
    session_id = sdk.create_session()
    print(f"Session created: {session_id}")
    
    # Submit a query
    result = sdk.submit_query(
        "Calculate profit margins from data/products.csv",
        session_id=session_id
    )
    
    if result.success:
        print(f"Success: {result.response}")
        print(f"Tool used: {result.tool_name}")
        print(f"Synthesized: {result.synthesized}")
    else:
        print(f"Error: {result.error}")
    
finally:
    sdk.disconnect()
```

#### Using Context Manager

```python
from agent_sdk import AgentSDK

with AgentSDK("http://localhost:5001") as sdk:
    session_id = sdk.create_session()
    
    result = sdk.submit_query(
        "Calculate factorial of 10",
        session_id=session_id
    )
    
    print(result.response)
```

#### Event Handling

```python
from agent_sdk import AgentSDK

sdk = AgentSDK("http://localhost:5001")

# Register event handlers
@sdk.on('agent_event')
def handle_agent_event(event):
    event_type = event['event_type']
    data = event['data']
    print(f"[{event_type}] {data}")

@sdk.on('query_complete')
def handle_completion(result):
    print(f"Query complete: {result['success']}")

sdk.connect()
session_id = sdk.create_session()
sdk.submit_query("Calculate fibonacci sequence", session_id)
```

---

## JavaScript SDK

### Installation

```bash
npm install socket.io-client axios
```

### Complete SDK Implementation

```javascript
/**
 * Self-Engineering Agent Framework JavaScript SDK
 * 
 * A comprehensive client library for interacting with the Self-Engineering Agent Framework API.
 */

const io = require('socket.io-client');
const axios = require('axios');

class QueryResult {
  constructor(data) {
    this.success = data.success;
    this.response = data.response;
    this.toolName = data.metadata?.tool_name;
    this.toolResult = data.metadata?.tool_result;
    this.synthesized = data.metadata?.synthesized || false;
    this.sessionId = data.session_id;
    this.error = data.error;
  }
}

class Tool {
  constructor(data) {
    this.name = data.name;
    this.docstring = data.docstring;
    this.createdAt = data.created_at;
    this.filePath = data.file_path;
    this.code = data.code;
    this.testCode = data.test_code;
    this.timestamp = data.timestamp;
    this.testPath = data.test_path;
  }
}

class AgentSDK {
  /**
   * JavaScript SDK for Self-Engineering Agent Framework
   * 
   * @param {string} baseUrl - Base URL of the agent server
   * 
   * @example
   * const sdk = new AgentSDK('http://localhost:5001');
   * await sdk.connect();
   * const sessionId = await sdk.createSession();
   * const result = await sdk.submitQuery('Calculate factorial of 5', sessionId);
   * console.log(result.response);
   * sdk.disconnect();
   */
  constructor(baseUrl = 'http://localhost:5001') {
    this.baseUrl = baseUrl;
    this.apiUrl = `${baseUrl}/api`;
    this.sessionId = null;
    this.socket = null;
    this.eventHandlers = {};
    this.queryResults = {};
  }

  /**
   * Connect to the agent server
   * 
   * @returns {Promise<void>}
   */
  connect() {
    return new Promise((resolve, reject) => {
      this.socket = io(this.baseUrl);
      
      this.socket.on('connect', () => {
        this._triggerEvent('connect', {});
      });
      
      this.socket.on('connected', (data) => {
        this._triggerEvent('connected', data);
        resolve();
      });
      
      this.socket.on('connect_error', (error) => {
        reject(new Error(`Failed to connect: ${error.message}`));
      });
      
      this.socket.on('tool_count', (data) => {
        this._triggerEvent('tool_count', data);
      });
      
      this.socket.on('agent_event', (event) => {
        this._triggerEvent('agent_event', event);
      });
      
      this.socket.on('query_complete', (result) => {
        const queryId = result.session_id || 'default';
        this.queryResults[queryId] = result;
        this._triggerEvent('query_complete', result);
      });
      
      this.socket.on('session_memory', (data) => {
        this._triggerEvent('session_memory', data);
      });
      
      this.socket.on('error', (error) => {
        this._triggerEvent('error', error);
      });
    });
  }

  /**
   * Disconnect from the agent server
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }

  /**
   * Register an event handler
   * 
   * @param {string} event - Event name
   * @param {Function} handler - Callback function
   */
  on(event, handler) {
    if (!this.eventHandlers[event]) {
      this.eventHandlers[event] = [];
    }
    this.eventHandlers[event].push(handler);
  }

  /**
   * Trigger registered event handlers
   * @private
   */
  _triggerEvent(event, data) {
    if (this.eventHandlers[event]) {
      this.eventHandlers[event].forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler: ${error.message}`);
        }
      });
    }
  }

  /**
   * Create a new session for conversational memory
   * 
   * @returns {Promise<string>} Session identifier
   */
  async createSession() {
    const response = await axios.post(`${this.apiUrl}/session`);
    
    if (response.data.success) {
      this.sessionId = response.data.session_id;
      return this.sessionId;
    } else {
      throw new Error(`Failed to create session: ${response.data.error}`);
    }
  }

  /**
   * Submit a query to the agent
   * 
   * @param {string} prompt - User's natural language request
   * @param {string} sessionId - Session identifier (uses default if not provided)
   * @param {boolean} wait - Whether to wait for completion
   * @param {number} timeout - Maximum wait time in milliseconds
   * @returns {Promise<QueryResult>} Query result
   */
  async submitQuery(prompt, sessionId = null, wait = true, timeout = 30000) {
    const sid = sessionId || this.sessionId;
    if (!sid) {
      throw new Error('No active session. Call createSession() first.');
    }
    
    // Clear previous result
    delete this.queryResults[sid];
    
    // Submit query
    this.socket.emit('query', {
      prompt: prompt,
      session_id: sid
    });
    
    if (!wait) {
      return null;
    }
    
    // Wait for result
    const startTime = Date.now();
    while (!this.queryResults[sid]) {
      if (Date.now() - startTime > timeout) {
        throw new Error(`Query timed out after ${timeout}ms`);
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    return new QueryResult(this.queryResults[sid]);
  }

  /**
   * Get list of all available tools
   * 
   * @returns {Promise<Tool[]>} List of tools
   */
  async getTools() {
    const response = await axios.get(`${this.apiUrl}/tools`);
    
    if (response.data.success) {
      return response.data.tools.map(tool => new Tool(tool));
    } else {
      throw new Error(`Failed to get tools: ${response.data.error}`);
    }
  }

  /**
   * Get detailed information about a specific tool
   * 
   * @param {string} toolName - Name of the tool
   * @returns {Promise<Tool>} Tool object with code and tests
   */
  async getTool(toolName) {
    const response = await axios.get(`${this.apiUrl}/tools/${toolName}`);
    
    if (response.data.success) {
      return new Tool(response.data.tool);
    } else {
      throw new Error(`Failed to get tool: ${response.data.error}`);
    }
  }

  /**
   * Get recent messages for a session
   * 
   * @param {string} sessionId - Session identifier (uses default if not provided)
   * @param {number} limit - Maximum number of messages
   * @returns {Promise<Object[]>} List of messages
   */
  async getSessionMessages(sessionId = null, limit = 20) {
    const sid = sessionId || this.sessionId;
    if (!sid) {
      throw new Error('No active session');
    }
    
    const response = await axios.get(
      `${this.apiUrl}/session/${sid}/messages`,
      { params: { limit } }
    );
    
    if (response.data.success) {
      return response.data.messages;
    } else {
      throw new Error(`Failed to get messages: ${response.data.error}`);
    }
  }

  /**
   * Get detected workflow patterns
   * 
   * @param {number} minFrequency - Minimum pattern frequency
   * @param {number} limit - Maximum number of patterns
   * @returns {Promise<Object[]>} List of workflow patterns
   */
  async getWorkflowPatterns(minFrequency = 2, limit = 10) {
    const response = await axios.get(
      `${this.apiUrl}/analytics/patterns`,
      { params: { min_frequency: minFrequency, limit } }
    );
    
    if (response.data.success) {
      return response.data.patterns;
    } else {
      throw new Error(`Failed to get patterns: ${response.data.error}`);
    }
  }

  /**
   * Get tool relationship analytics
   * 
   * @param {string} toolName - Filter by specific tool
   * @param {number} minConfidence - Minimum confidence score
   * @returns {Promise<Object[]>} List of relationships
   */
  async getToolRelationships(toolName = null, minConfidence = 0.5) {
    const params = { min_confidence: minConfidence };
    if (toolName) {
      params.tool_name = toolName;
    }
    
    const response = await axios.get(
      `${this.apiUrl}/analytics/relationships`,
      { params }
    );
    
    if (response.data.success) {
      return response.data.relationships;
    } else {
      throw new Error(`Failed to get relationships: ${response.data.error}`);
    }
  }

  /**
   * Get execution history for a session
   * 
   * @param {string} sessionId - Session identifier (uses default if not provided)
   * @param {number} limit - Maximum number of executions
   * @returns {Promise<Object[]>} List of executions
   */
  async getSessionHistory(sessionId = null, limit = 100) {
    const sid = sessionId || this.sessionId;
    if (!sid) {
      throw new Error('No active session');
    }
    
    const response = await axios.get(
      `${this.apiUrl}/analytics/sessions/${sid}`,
      { params: { limit } }
    );
    
    if (response.data.success) {
      return response.data.executions;
    } else {
      throw new Error(`Failed to get history: ${response.data.error}`);
    }
  }

  /**
   * Get overall workflow statistics
   * 
   * @returns {Promise<Object>} Statistics object
   */
  async getWorkflowStats() {
    const response = await axios.get(`${this.apiUrl}/analytics/stats`);
    
    if (response.data.success) {
      return response.data.stats;
    } else {
      throw new Error(`Failed to get stats: ${response.data.error}`);
    }
  }
}

// Export
module.exports = { AgentSDK, QueryResult, Tool };

// Convenience function
async function createClient(baseUrl = 'http://localhost:5001') {
  const sdk = new AgentSDK(baseUrl);
  await sdk.connect();
  return sdk;
}

module.exports.createClient = createClient;
```

### JavaScript Usage Examples

#### Basic Usage

```javascript
const { AgentSDK } = require('./agent-sdk');

async function main() {
  const sdk = new AgentSDK('http://localhost:5001');
  
  try {
    // Connect to server
    await sdk.connect();
    
    // Create a session
    const sessionId = await sdk.createSession();
    console.log(`Session created: ${sessionId}`);
    
    // Submit a query
    const result = await sdk.submitQuery(
      'Calculate profit margins from data/products.csv',
      sessionId
    );
    
    if (result.success) {
      console.log(`Success: ${result.response}`);
      console.log(`Tool used: ${result.toolName}`);
      console.log(`Synthesized: ${result.synthesized}`);
    } else {
      console.error(`Error: ${result.error}`);
    }
    
  } finally {
    sdk.disconnect();
  }
}

main().catch(console.error);
```

#### Event Handling

```javascript
const { AgentSDK } = require('./agent-sdk');

async function main() {
  const sdk = new AgentSDK('http://localhost:5001');
  
  // Register event handlers
  sdk.on('agent_event', (event) => {
    const { event_type, data } = event;
    console.log(`[${event_type}]`, data);
  });
  
  sdk.on('query_complete', (result) => {
    console.log(`Query complete: ${result.success}`);
  });
  
  await sdk.connect();
  const sessionId = await sdk.createSession();
  await sdk.submitQuery('Calculate fibonacci sequence', sessionId);
}

main().catch(console.error);
```

#### Using Convenience Function

```javascript
const { createClient } = require('./agent-sdk');

async function main() {
  const sdk = await createClient('http://localhost:5001');
  
  try {
    const sessionId = await sdk.createSession();
    const result = await sdk.submitQuery('Calculate factorial of 10', sessionId);
    console.log(result.response);
  } finally {
    sdk.disconnect();
  }
}

main().catch(console.error);
```

---

## Usage Examples

### Multi-Query Conversation

```python
from agent_sdk import AgentSDK

with AgentSDK() as sdk:
    session_id = sdk.create_session()
    
    # First query
    result1 = sdk.submit_query(
        "Load sales data from data/sales.csv",
        session_id
    )
    print(result1.response)
    
    # Follow-up query (uses context)
    result2 = sdk.submit_query(
        "Calculate the average profit margin",
        session_id
    )
    print(result2.response)
    
    # Another follow-up
    result3 = sdk.submit_query(
        "Show me the top 5 products",
        session_id
    )
    print(result3.response)
```

### Tool Discovery

```python
from agent_sdk import AgentSDK

with AgentSDK() as sdk:
    # Get all tools
    tools = sdk.get_tools()
    
    print(f"Available tools: {len(tools)}")
    for tool in tools[:10]:
        print(f"  - {tool.name}: {tool.docstring[:60]}...")
    
    # Get specific tool details
    tool = sdk.get_tool("calculate_profit_margins")
    print(f"\nTool: {tool.name}")
    print(f"Code:\n{tool.code}")
    print(f"\nTests:\n{tool.test_code}")
```

### Analytics and Insights

```python
from agent_sdk import AgentSDK

with AgentSDK() as sdk:
    # Get workflow patterns
    patterns = sdk.get_workflow_patterns(min_frequency=3)
    print("Workflow Patterns:")
    for pattern in patterns:
        print(f"  {pattern['pattern_name']}: {' → '.join(pattern['tool_sequence'])}")
        print(f"    Frequency: {pattern['frequency']}, Success: {pattern['avg_success_rate']:.1%}")
    
    # Get tool relationships
    relationships = sdk.get_tool_relationships(min_confidence=0.7)
    print("\nTool Relationships:")
    for rel in relationships[:10]:
        print(f"  {rel['tool_a']} ↔ {rel['tool_b']} (confidence: {rel['confidence_score']:.2f})")
    
    # Get overall stats
    stats = sdk.get_workflow_stats()
    print(f"\nTotal patterns: {stats['total_patterns']}")
    print(f"Total relationships: {stats['total_relationships']}")
```

---

## Advanced Features

### Custom Event Monitoring

```python
from agent_sdk import AgentSDK, EventType

class ProgressMonitor:
    def __init__(self, sdk: AgentSDK):
        self.sdk = sdk
        self.stages = []
        
        sdk.on('agent_event', self.handle_event)
    
    def handle_event(self, event):
        event_type = event['event_type']
        data = event['data']
        
        if event_type == 'synthesis_step':
            self.stages.append({
                'step': data['step'],
                'status': data['status']
            })
            print(f"Synthesis: {data['step']} - {data['status']}")
        
        elif event_type == 'workflow_step':
            print(f"Workflow: Step {data['step']}/{data['total']} - {data['task']}")

# Usage
with AgentSDK() as sdk:
    monitor = ProgressMonitor(sdk)
    session_id = sdk.create_session()
    result = sdk.submit_query("Create a function to calculate fibonacci", session_id)
```

### Batch Processing

```python
from agent_sdk import AgentSDK
from concurrent.futures import ThreadPoolExecutor

def process_query(sdk, query, session_id):
    return sdk.submit_query(query, session_id)

with AgentSDK() as sdk:
    session_id = sdk.create_session()
    
    queries = [
        "Calculate profit margins",
        "Analyze sales trends",
        "Generate monthly report"
    ]
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(
            lambda q: process_query(sdk, q, session_id),
            queries
        ))
    
    for query, result in zip(queries, results):
        print(f"{query}: {result.success}")
```

### Error Handling and Retry

```python
from agent_sdk import AgentSDK
import time

def submit_with_retry(sdk, prompt, session_id, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = sdk.submit_query(prompt, session_id)
            if result.success:
                return result
            print(f"Attempt {attempt + 1} failed: {result.error}")
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    raise Exception(f"Failed after {max_retries} attempts")

# Usage
with AgentSDK() as sdk:
    session_id = sdk.create_session()
    result = submit_with_retry(sdk, "Calculate factorial of 100", session_id)
    print(result.response)
```
