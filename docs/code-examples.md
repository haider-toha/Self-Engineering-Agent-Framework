# Code Examples

This document provides comprehensive code examples in Python and JavaScript demonstrating common integration patterns with the Self-Engineering Agent Framework API.

## Table of Contents

1. [Python Examples](#python-examples)
   - [Basic Client](#basic-python-client)
   - [Advanced Client with Event Handling](#advanced-python-client)
   - [Batch Processing](#batch-processing-python)
   - [Tool Synthesis Request](#tool-synthesis-request-python)
   - [Semantic Tool Search](#semantic-tool-search-python)
2. [JavaScript Examples](#javascript-examples)
   - [Basic Client](#basic-javascript-client)
   - [React Integration](#react-integration)
   - [Node.js Backend Integration](#nodejs-backend-integration)
   - [Tool Synthesis Request](#tool-synthesis-request-javascript)
   - [Real-time Dashboard](#real-time-dashboard)

---

## Python Examples

### Basic Python Client

A simple client for submitting queries and receiving responses:

```python
#!/usr/bin/env python3
"""
Basic Agent Client - Simple query submission and response handling
"""

import requests
import socketio
import sys

class BasicAgentClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.session_id = None
        self.sio = socketio.Client()
        self.response_received = False
        self.final_response = None
        
    def create_session(self):
        """Create a new conversational session"""
        try:
            response = requests.post(f'{self.base_url}/api/session')
            data = response.json()
            
            if data['success']:
                self.session_id = data['session_id']
                print(f"✓ Session created: {self.session_id}")
                return True
            else:
                print(f"✗ Failed to create session: {data.get('error')}")
                return False
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def submit_query(self, prompt):
        """Submit a query and wait for response"""
        if not self.session_id:
            print("✗ No active session. Create a session first.")
            return None
        
        # Setup event handlers
        @self.sio.on('connect')
        def on_connect():
            print("✓ Connected to agent")
            self.sio.emit('query', {
                'prompt': prompt,
                'session_id': self.session_id
            })
        
        @self.sio.on('query_complete')
        def on_query_complete(data):
            self.response_received = True
            if data['success']:
                self.final_response = data['response']
                print(f"\n✓ Response: {data['response']}")
                print(f"\nMetadata:")
                print(f"  Tool: {data['metadata']['tool_name']}")
                print(f"  Synthesized: {data['metadata']['synthesized']}")
            else:
                print(f"\n✗ Query failed: {data['response']}")
            self.sio.disconnect()
        
        @self.sio.on('error')
        def on_error(data):
            print(f"✗ Error: {data['message']}")
            self.sio.disconnect()
        
        # Connect and wait
        try:
            self.sio.connect(self.base_url)
            while not self.response_received:
                self.sio.sleep(0.1)
            return self.final_response
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python basic_client.py 'Your query here'")
        sys.exit(1)
    
    prompt = sys.argv[1]
    
    client = BasicAgentClient()
    if client.create_session():
        client.submit_query(prompt)

if __name__ == '__main__':
    main()
```

**Usage:**
```bash
python basic_client.py "Calculate profit margins from data/ecommerce_products.csv"
```

---

### Advanced Python Client

A comprehensive client with full event handling and progress tracking:

```python
#!/usr/bin/env python3
"""
Advanced Agent Client - Full event handling with progress tracking
"""

import requests
import socketio
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    SEARCHING = "searching"
    TOOL_FOUND = "tool_found"
    NO_TOOL_FOUND = "no_tool_found"
    SYNTHESIS_MODE = "entering_synthesis_mode"
    SYNTHESIS_STEP = "synthesis_step"
    SYNTHESIS_SUCCESS = "synthesis_successful"
    EXECUTING = "executing"
    EXECUTION_COMPLETE = "execution_complete"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_STEP = "workflow_step"
    WORKFLOW_COMPLETE = "workflow_complete"

@dataclass
class QueryResult:
    success: bool
    response: str
    tool_name: Optional[str]
    synthesized: bool
    tool_result: Any
    session_id: str

class AdvancedAgentClient:
    def __init__(self, base_url='http://localhost:5001', verbose=True):
        self.base_url = base_url
        self.session_id = None
        self.sio = socketio.Client()
        self.verbose = verbose
        self.event_log = []
        self.result = None
        
    def create_session(self) -> Optional[str]:
        """Create a new conversational session"""
        try:
            response = requests.post(f'{self.base_url}/api/session')
            data = response.json()
            
            if data['success']:
                self.session_id = data['session_id']
                if self.verbose:
                    print(f"✓ Session created: {self.session_id}")
                return self.session_id
            else:
                if self.verbose:
                    print(f"✗ Failed to create session: {data.get('error')}")
                return None
        except Exception as e:
            if self.verbose:
                print(f"✗ Connection error: {e}")
            return None
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event for later analysis"""
        self.event_log.append({
            'timestamp': time.time(),
            'event_type': event_type,
            'data': data
        })
    
    def _handle_agent_event(self, data: Dict[str, Any]):
        """Handle agent lifecycle events"""
        event_type = data['event_type']
        event_data = data.get('data', {})
        
        self._log_event(event_type, event_data)
        
        if not self.verbose:
            return
        
        if event_type == EventType.SEARCHING.value:
            print("🔍 Searching for existing tool...")
        
        elif event_type == EventType.TOOL_FOUND.value:
            tool_name = event_data.get('tool_name', 'Unknown')
            similarity = event_data.get('similarity', 0)
            print(f"✓ Found tool: {tool_name} ({similarity:.1%} match)")
        
        elif event_type == EventType.NO_TOOL_FOUND.value:
            print("⚠ No matching tool found")
        
        elif event_type == EventType.SYNTHESIS_MODE.value:
            print("🔧 Creating new tool...")
        
        elif event_type == EventType.SYNTHESIS_STEP.value:
            step = event_data.get('step', 'unknown')
            status = event_data.get('status', 'unknown')
            
            step_names = {
                'specification': 'Generating specification',
                'tests': 'Generating tests',
                'implementation': 'Implementing function',
                'verification': 'Verifying in sandbox',
                'registration': 'Registering tool'
            }
            
            step_name = step_names.get(step, step)
            
            if status == 'in_progress':
                print(f"  ⏳ {step_name}...")
            elif status == 'complete':
                print(f"  ✓ {step_name} complete")
            elif status == 'failed':
                error = event_data.get('error', 'Unknown error')
                print(f"  ✗ {step_name} failed: {error}")
        
        elif event_type == EventType.SYNTHESIS_SUCCESS.value:
            tool_name = event_data.get('tool_name', 'Unknown')
            print(f"✓ Tool synthesized: {tool_name}")
        
        elif event_type == EventType.EXECUTING.value:
            tool_name = event_data.get('tool_name', 'Unknown')
            print(f"▶ Executing: {tool_name}")
        
        elif event_type == EventType.EXECUTION_COMPLETE.value:
            result = event_data.get('result', '')
            if len(str(result)) > 100:
                result = str(result)[:100] + '...'
            print(f"✓ Execution complete: {result}")
        
        elif event_type == EventType.WORKFLOW_START.value:
            total_steps = event_data.get('total_steps', 0)
            tasks = event_data.get('tasks', [])
            print(f"\n🔄 Starting workflow ({total_steps} steps):")
            for i, task in enumerate(tasks, 1):
                print(f"  {i}. {task}")
        
        elif event_type == EventType.WORKFLOW_STEP.value:
            step = event_data.get('step', 0)
            total = event_data.get('total', 0)
            task = event_data.get('task', '')
            print(f"\n📍 Step {step}/{total}: {task}")
        
        elif event_type == EventType.WORKFLOW_COMPLETE.value:
            tool_sequence = event_data.get('tool_sequence', [])
            print(f"\n✓ Workflow complete!")
            print(f"  Tool sequence: {' → '.join(tool_sequence)}")
    
    def submit_query(self, prompt: str, timeout: int = 300) -> Optional[QueryResult]:
        """Submit a query with full event handling"""
        if not self.session_id:
            if self.verbose:
                print("✗ No active session. Create a session first.")
            return None
        
        self.result = None
        self.event_log = []
        
        @self.sio.on('connect')
        def on_connect():
            if self.verbose:
                print("✓ Connected to agent\n")
            self.sio.emit('query', {
                'prompt': prompt,
                'session_id': self.session_id
            })
        
        @self.sio.on('agent_event')
        def on_agent_event(data):
            self._handle_agent_event(data)
        
        @self.sio.on('query_complete')
        def on_query_complete(data):
            self.result = QueryResult(
                success=data['success'],
                response=data['response'],
                tool_name=data['metadata'].get('tool_name'),
                synthesized=data['metadata'].get('synthesized', False),
                tool_result=data['metadata'].get('tool_result'),
                session_id=data.get('session_id', self.session_id)
            )
            
            if self.verbose:
                if data['success']:
                    print(f"\n{'='*60}")
                    print(f"✓ Query Complete")
                    print(f"{'='*60}")
                    print(f"\n{data['response']}\n")
                else:
                    print(f"\n✗ Query failed: {data['response']}")
            
            self.sio.disconnect()
        
        @self.sio.on('error')
        def on_error(data):
            if self.verbose:
                print(f"✗ Error: {data['message']}")
            self.sio.disconnect()
        
        try:
            self.sio.connect(self.base_url, wait_timeout=10)
            
            start_time = time.time()
            while self.result is None:
                if time.time() - start_time > timeout:
                    if self.verbose:
                        print(f"\n✗ Query timed out after {timeout}s")
                    self.sio.disconnect()
                    return None
                self.sio.sleep(0.1)
            
            return self.result
        
        except Exception as e:
            if self.verbose:
                print(f"✗ Connection error: {e}")
            return None
    
    def get_event_log(self):
        """Get the event log for analysis"""
        return self.event_log
    
    def get_tools(self):
        """Get list of all available tools"""
        try:
            response = requests.get(f'{self.base_url}/api/tools')
            data = response.json()
            return data.get('tools', []) if data['success'] else []
        except Exception as e:
            if self.verbose:
                print(f"✗ Error fetching tools: {e}")
            return []
    
    def get_tool_details(self, tool_name: str):
        """Get detailed information about a specific tool"""
        try:
            response = requests.get(f'{self.base_url}/api/tools/{tool_name}')
            data = response.json()
            return data.get('tool') if data['success'] else None
        except Exception as e:
            if self.verbose:
                print(f"✗ Error fetching tool details: {e}")
            return None

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python advanced_client.py 'Your query here'")
        sys.exit(1)
    
    prompt = sys.argv[1]
    
    client = AdvancedAgentClient(verbose=True)
    
    if client.create_session():
        result = client.submit_query(prompt)
        
        if result:
            print(f"\nQuery Statistics:")
            print(f"  Events logged: {len(client.get_event_log())}")
            print(f"  Tool used: {result.tool_name}")
            print(f"  New tool: {result.synthesized}")

if __name__ == '__main__':
    main()
```

**Usage:**
```bash
python advanced_client.py "Calculate profit margins from data/ecommerce_products.csv"
```

---

### Batch Processing (Python)

Process multiple queries in sequence:

```python
#!/usr/bin/env python3
"""
Batch Query Processor - Process multiple queries in a single session
"""

import requests
import socketio
import time
from typing import List, Dict, Any

class BatchProcessor:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.session_id = None
        self.sio = socketio.Client()
        self.current_result = None
        self.results = []
        
    def create_session(self):
        response = requests.post(f'{self.base_url}/api/session')
        data = response.json()
        if data['success']:
            self.session_id = data['session_id']
            return True
        return False
    
    def process_query(self, prompt: str) -> Dict[str, Any]:
        """Process a single query"""
        self.current_result = None
        
        @self.sio.on('connect')
        def on_connect():
            self.sio.emit('query', {
                'prompt': prompt,
                'session_id': self.session_id
            })
        
        @self.sio.on('query_complete')
        def on_query_complete(data):
            self.current_result = {
                'prompt': prompt,
                'success': data['success'],
                'response': data['response'],
                'tool_name': data['metadata'].get('tool_name'),
                'synthesized': data['metadata'].get('synthesized', False)
            }
            self.sio.disconnect()
        
        try:
            self.sio.connect(self.base_url)
            while self.current_result is None:
                self.sio.sleep(0.1)
            return self.current_result
        except Exception as e:
            return {
                'prompt': prompt,
                'success': False,
                'error': str(e)
            }
    
    def process_batch(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """Process multiple queries in sequence"""
        if not self.session_id:
            if not self.create_session():
                print("Failed to create session")
                return []
        
        results = []
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] Processing: {prompt}")
            result = self.process_query(prompt)
            results.append(result)
            
            if result['success']:
                print(f"  ✓ Success: {result['tool_name']}")
            else:
                print(f"  ✗ Failed")
            
            # Small delay between queries
            time.sleep(1)
        
        return results

def main():
    queries = [
        "Load data from data/ecommerce_products.csv",
        "Calculate the average profit margin",
        "Find the top 5 products by profit margin",
        "Generate a summary report"
    ]
    
    processor = BatchProcessor()
    results = processor.process_batch(queries)
    
    print(f"\n{'='*60}")
    print("Batch Processing Complete")
    print(f"{'='*60}")
    print(f"Total queries: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    print(f"New tools synthesized: {sum(1 for r in results if r.get('synthesized', False))}")

if __name__ == '__main__':
    main()
```

---

### Tool Synthesis Request (Python)

Explicitly request tool synthesis:

```python
#!/usr/bin/env python3
"""
Tool Synthesis Request - Explicitly create a new tool
"""

import socketio

def synthesize_tool(tool_description: str, base_url='http://localhost:5001'):
    """
    Request synthesis of a new tool
    
    Args:
        tool_description: Natural language description of the desired tool
        base_url: Agent server URL
    """
    sio = socketio.Client()
    result = None
    
    @sio.on('connect')
    def on_connect():
        print("Connected to agent")
        # Use explicit synthesis request format
        prompt = f"Create a function that {tool_description}"
        sio.emit('query', {
            'prompt': prompt,
            'session_id': session_id
        })
    
    @sio.on('agent_event')
    def on_agent_event(data):
        event_type = data['event_type']
        event_data = data.get('data', {})
        
        if event_type == 'synthesis_step':
            step = event_data.get('step')
            status = event_data.get('status')
            print(f"  {step}: {status}")
        
        elif event_type == 'synthesis_successful':
            tool_name = event_data.get('tool_name')
            print(f"\n✓ Tool created: {tool_name}")
    
    @sio.on('query_complete')
    def on_query_complete(data):
        nonlocal result
        result = data
        sio.disconnect()
    
    # Create session
    import requests
    response = requests.post(f'{base_url}/api/session')
    session_id = response.json()['session_id']
    
    # Connect and synthesize
    sio.connect(base_url)
    while result is None:
        sio.sleep(0.1)
    
    return result

# Example usage
if __name__ == '__main__':
    result = synthesize_tool(
        "calculates the compound annual growth rate (CAGR) given initial value, final value, and number of years"
    )
    
    if result['success']:
        print(f"\nTool synthesized successfully!")
        print(f"Tool name: {result['metadata']['tool_name']}")
    else:
        print(f"\nSynthesis failed: {result['response']}")
```

---

### Semantic Tool Search (Python)

Search for tools using semantic similarity:

```python
#!/usr/bin/env python3
"""
Semantic Tool Search - Find tools using natural language queries
"""

import requests
from typing import List, Dict, Any

def search_tools(query: str, base_url='http://localhost:5001') -> List[Dict[str, Any]]:
    """
    Search for tools using semantic similarity
    
    Args:
        query: Natural language search query
        base_url: Agent server URL
    
    Returns:
        List of matching tools with similarity scores
    """
    # Get all tools
    response = requests.get(f'{base_url}/api/tools')
    data = response.json()
    
    if not data['success']:
        return []
    
    tools = data['tools']
    
    # Filter tools by keyword matching (client-side)
    # The agent uses vector similarity internally
    query_lower = query.lower()
    matching_tools = []
    
    for tool in tools:
        name_match = query_lower in tool['name'].lower()
        doc_match = query_lower in tool['docstring'].lower()
        
        if name_match or doc_match:
            matching_tools.append(tool)
    
    return matching_tools

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python search_tools.py 'search query'")
        sys.exit(1)
    
    query = sys.argv[1]
    tools = search_tools(query)
    
    print(f"Found {len(tools)} matching tools for '{query}':\n")
    
    for tool in tools:
        print(f"• {tool['name']}")
        print(f"  {tool['docstring']}")
        print(f"  File: {tool['file_path']}")
        print()

if __name__ == '__main__':
    main()
```

---

## JavaScript Examples

### Basic JavaScript Client

A simple Node.js client for submitting queries:

```javascript
#!/usr/bin/env node
/**
 * Basic Agent Client - Simple query submission and response handling
 */

const io = require('socket.io-client');
const axios = require('axios');

class BasicAgentClient {
    constructor(baseUrl = 'http://localhost:5001') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
        this.socket = null;
    }
    
    async createSession() {
        try {
            const response = await axios.post(`${this.baseUrl}/api/session`);
            
            if (response.data.success) {
                this.sessionId = response.data.session_id;
                console.log(`✓ Session created: ${this.sessionId}`);
                return true;
            } else {
                console.error(`✗ Failed to create session: ${response.data.error}`);
                return false;
            }
        } catch (error) {
            console.error(`✗ Connection error: ${error.message}`);
            return false;
        }
    }
    
    submitQuery(prompt) {
        return new Promise((resolve, reject) => {
            if (!this.sessionId) {
                reject(new Error('No active session'));
                return;
            }
            
            this.socket = io(this.baseUrl);
            
            this.socket.on('connect', () => {
                console.log('✓ Connected to agent');
                this.socket.emit('query', {
                    prompt: prompt,
                    session_id: this.sessionId
                });
            });
            
            this.socket.on('query_complete', (data) => {
                if (data.success) {
                    console.log(`\n✓ Response: ${data.response}`);
                    console.log(`\nMetadata:`);
                    console.log(`  Tool: ${data.metadata.tool_name}`);
                    console.log(`  Synthesized: ${data.metadata.synthesized}`);
                    resolve(data);
                } else {
                    console.error(`\n✗ Query failed: ${data.response}`);
                    reject(new Error(data.response));
                }
                this.socket.disconnect();
            });
            
            this.socket.on('error', (data) => {
                console.error(`✗ Error: ${data.message}`);
                this.socket.disconnect();
                reject(new Error(data.message));
            });
            
            this.socket.on('connect_error', (error) => {
                console.error(`✗ Connection error: ${error.message}`);
                reject(error);
            });
        });
    }
}

async function main() {
    const prompt = process.argv[2];
    
    if (!prompt) {
        console.log('Usage: node basic_client.js "Your query here"');
        process.exit(1);
    }
    
    const client = new BasicAgentClient();
    
    if (await client.createSession()) {
        try {
            await client.submitQuery(prompt);
        } catch (error) {
            console.error(`Query failed: ${error.message}`);
            process.exit(1);
        }
    }
}

if (require.main === module) {
    main();
}

module.exports = BasicAgentClient;
```

**Usage:**
```bash
node basic_client.js "Calculate profit margins from data/ecommerce_products.csv"
```

---

### React Integration

Integrate the agent into a React application:

```javascript
/**
 * React Hook for Agent Integration
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import io from 'socket.io-client';
import axios from 'axios';

export const useAgent = (baseUrl = 'http://localhost:5001') => {
    const [sessionId, setSessionId] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [events, setEvents] = useState([]);
    const [response, setResponse] = useState(null);
    const [error, setError] = useState(null);
    
    const socketRef = useRef(null);
    
    // Create session
    const createSession = useCallback(async () => {
        try {
            const res = await axios.post(`${baseUrl}/api/session`);
            if (res.data.success) {
                setSessionId(res.data.session_id);
                return res.data.session_id;
            } else {
                setError(res.data.error);
                return null;
            }
        } catch (err) {
            setError(err.message);
            return null;
        }
    }, [baseUrl]);
    
    // Initialize socket connection
    useEffect(() => {
        if (!sessionId) return;
        
        const socket = io(baseUrl);
        socketRef.current = socket;
        
        socket.on('connect', () => {
            setIsConnected(true);
            setError(null);
        });
        
        socket.on('disconnect', () => {
            setIsConnected(false);
        });
        
        socket.on('agent_event', (data) => {
            setEvents(prev => [...prev, {
                timestamp: Date.now(),
                type: data.event_type,
                data: data.data
            }]);
        });
        
        socket.on('query_complete', (data) => {
            setIsProcessing(false);
            if (data.success) {
                setResponse(data);
                setError(null);
            } else {
                setError(data.response);
            }
        });
        
        socket.on('error', (data) => {
            setIsProcessing(false);
            setError(data.message);
        });
        
        return () => {
            socket.disconnect();
        };
    }, [sessionId, baseUrl]);
    
    // Submit query
    const submitQuery = useCallback((prompt) => {
        if (!socketRef.current || !sessionId) {
            setError('No active session');
            return;
        }
        
        setIsProcessing(true);
        setEvents([]);
        setResponse(null);
        setError(null);
        
        socketRef.current.emit('query', {
            prompt: prompt,
            session_id: sessionId
        });
    }, [sessionId]);
    
    // Get tools
    const getTools = useCallback(async () => {
        try {
            const res = await axios.get(`${baseUrl}/api/tools`);
            return res.data.success ? res.data.tools : [];
        } catch (err) {
            setError(err.message);
            return [];
        }
    }, [baseUrl]);
    
    return {
        sessionId,
        isConnected,
        isProcessing,
        events,
        response,
        error,
        createSession,
        submitQuery,
        getTools
    };
};

// Example React Component
export const AgentChat = () => {
    const {
        sessionId,
        isConnected,
        isProcessing,
        events,
        response,
        error,
        createSession,
        submitQuery,
        getTools
    } = useAgent();
    
    const [prompt, setPrompt] = useState('');
    const [tools, setTools] = useState([]);
    
    useEffect(() => {
        createSession();
    }, [createSession]);
    
    useEffect(() => {
        if (sessionId) {
            getTools().then(setTools);
        }
    }, [sessionId, getTools]);
    
    const handleSubmit = (e) => {
        e.preventDefault();
        if (prompt.trim()) {
            submitQuery(prompt);
            setPrompt('');
        }
    };
    
    return (
        <div className="agent-chat">
            <div className="status">
                Status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
                {sessionId && ` | Session: ${sessionId.substring(0, 8)}...`}
            </div>
            
            <div className="tools">
                <h3>Available Tools ({tools.length})</h3>
                <ul>
                    {tools.map(tool => (
                        <li key={tool.name}>{tool.name}</li>
                    ))}
                </ul>
            </div>
            
            <div className="events">
                <h3>Activity Log</h3>
                {events.map((event, i) => (
                    <div key={i} className="event">
                        [{event.type}] {JSON.stringify(event.data)}
                    </div>
                ))}
            </div>
            
            {response && (
                <div className="response">
                    <h3>Response</h3>
                    <p>{response.response}</p>
                    <small>Tool: {response.metadata.tool_name}</small>
                </div>
            )}
            
            {error && (
                <div className="error">
                    Error: {error}
                </div>
            )}
            
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter your query..."
                    disabled={!sessionId || isProcessing}
                />
                <button type="submit" disabled={!sessionId || isProcessing}>
                    {isProcessing ? 'Processing...' : 'Submit'}
                </button>
            </form>
        </div>
    );
};
```

---

### Node.js Backend Integration

Integrate the agent into an Express.js backend:

```javascript
/**
 * Express.js Backend Integration
 */

const express = require('express');
const io = require('socket.io-client');
const axios = require('axios');

const app = express();
app.use(express.json());

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:5001';

// Session management
const sessions = new Map();

// Create session endpoint
app.post('/api/agent/session', async (req, res) => {
    try {
        const response = await axios.post(`${AGENT_URL}/api/session`);
        
        if (response.data.success) {
            const sessionId = response.data.session_id;
            sessions.set(sessionId, {
                created: Date.now(),
                queries: []
            });
            res.json({ success: true, session_id: sessionId });
        } else {
            res.status(500).json({ success: false, error: response.data.error });
        }
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Submit query endpoint
app.post('/api/agent/query', async (req, res) => {
    const { prompt, session_id } = req.body;
    
    if (!prompt || !session_id) {
        return res.status(400).json({
            success: false,
            error: 'Missing prompt or session_id'
        });
    }
    
    const socket = io(AGENT_URL);
    const events = [];
    let result = null;
    
    socket.on('connect', () => {
        socket.emit('query', { prompt, session_id });
    });
    
    socket.on('agent_event', (data) => {
        events.push(data);
    });
    
    socket.on('query_complete', (data) => {
        result = data;
        socket.disconnect();
        
        // Store query in session
        if (sessions.has(session_id)) {
            sessions.get(session_id).queries.push({
                prompt,
                result,
                events,
                timestamp: Date.now()
            });
        }
        
        res.json({
            success: true,
            result,
            events
        });
    });
    
    socket.on('error', (data) => {
        socket.disconnect();
        res.status(500).json({
            success: false,
            error: data.message
        });
    });
    
    // Timeout after 5 minutes
    setTimeout(() => {
        if (!result) {
            socket.disconnect();
            res.status(408).json({
                success: false,
                error: 'Query timeout'
            });
        }
    }, 300000);
});

// Get tools endpoint
app.get('/api/agent/tools', async (req, res) => {
    try {
        const response = await axios.get(`${AGENT_URL}/api/tools`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get session history
app.get('/api/agent/session/:session_id/history', (req, res) => {
    const { session_id } = req.params;
    
    if (sessions.has(session_id)) {
        res.json({
            success: true,
            session: sessions.get(session_id)
        });
    } else {
        res.status(404).json({
            success: false,
            error: 'Session not found'
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Backend server running on port ${PORT}`);
    console.log(`Agent URL: ${AGENT_URL}`);
});
```

---

### Tool Synthesis Request (JavaScript)

```javascript
/**
 * Tool Synthesis Request - Explicitly create a new tool
 */

const io = require('socket.io-client');
const axios = require('axios');

async function synthesizeTool(toolDescription, baseUrl = 'http://localhost:5001') {
    // Create session
    const sessionResponse = await axios.post(`${baseUrl}/api/session`);
    const sessionId = sessionResponse.data.session_id;
    
    return new Promise((resolve, reject) => {
        const socket = io(baseUrl);
        const events = [];
        
        socket.on('connect', () => {
            console.log('Connected to agent');
            const prompt = `Create a function that ${toolDescription}`;
            socket.emit('query', { prompt, session_id: sessionId });
        });
        
        socket.on('agent_event', (data) => {
            events.push(data);
            
            if (data.event_type === 'synthesis_step') {
                const { step, status } = data.data;
                console.log(`  ${step}: ${status}`);
            } else if (data.event_type === 'synthesis_successful') {
                console.log(`\n✓ Tool created: ${data.data.tool_name}`);
            }
        });
        
        socket.on('query_complete', (data) => {
            socket.disconnect();
            resolve({ result: data, events });
        });
        
        socket.on('error', (data) => {
            socket.disconnect();
            reject(new Error(data.message));
        });
    });
}

// Example usage
async function main() {
    try {
        const result = await synthesizeTool(
            'calculates the compound annual growth rate (CAGR) given initial value, final value, and number of years'
        );
        
        if (result.result.success) {
            console.log('\nTool synthesized successfully!');
            console.log(`Tool name: ${result.result.metadata.tool_name}`);
        } else {
            console.error(`\nSynthesis failed: ${result.result.response}`);
        }
    } catch (error) {
        console.error(`Error: ${error.message}`);
    }
}

if (require.main === module) {
    main();
}

module.exports = synthesizeTool;
```

---

### Real-time Dashboard

A complete real-time dashboard example:

```javascript
/**
 * Real-time Agent Dashboard
 */

const express = require('express');
const http = require('http');
const socketIO = require('socket.io');
const agentIO = require('socket.io-client');
const axios = require('axios');

const app = express();
const server = http.createServer(app);
const io = socketIO(server);

const AGENT_URL = process.env.AGENT_URL || 'http://localhost:5001';

app.use(express.static('public'));

io.on('connection', (clientSocket) => {
    console.log('Dashboard client connected');
    
    let agentSocket = null;
    let sessionId = null;
    
    // Create session
    clientSocket.on('create_session', async () => {
        try {
            const response = await axios.post(`${AGENT_URL}/api/session`);
            if (response.data.success) {
                sessionId = response.data.session_id;
                clientSocket.emit('session_created', { session_id: sessionId });
            }
        } catch (error) {
            clientSocket.emit('error', { message: error.message });
        }
    });
    
    // Submit query
    clientSocket.on('submit_query', ({ prompt }) => {
        if (!sessionId) {
            clientSocket.emit('error', { message: 'No active session' });
            return;
        }
        
        agentSocket = agentIO(AGENT_URL);
        
        agentSocket.on('connect', () => {
            clientSocket.emit('agent_connected');
            agentSocket.emit('query', { prompt, session_id: sessionId });
        });
        
        agentSocket.on('agent_event', (data) => {
            clientSocket.emit('agent_event', data);
        });
        
        agentSocket.on('query_complete', (data) => {
            clientSocket.emit('query_complete', data);
            agentSocket.disconnect();
        });
        
        agentSocket.on('error', (data) => {
            clientSocket.emit('error', data);
            agentSocket.disconnect();
        });
    });
    
    // Get tools
    clientSocket.on('get_tools', async () => {
        try {
            const response = await axios.get(`${AGENT_URL}/api/tools`);
            clientSocket.emit('tools_list', response.data);
        } catch (error) {
            clientSocket.emit('error', { message: error.message });
        }
    });
    
    clientSocket.on('disconnect', () => {
        console.log('Dashboard client disconnected');
        if (agentSocket) {
            agentSocket.disconnect();
        }
    });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Dashboard server running on port ${PORT}`);
});
```

**HTML Dashboard (public/index.html):**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Agent Dashboard</title>
    <script src="/socket.io/socket.io.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .status { padding: 10px; background: #f0f0f0; margin-bottom: 20px; }
        .events { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
        .event { padding: 5px; margin: 5px 0; background: #f9f9f9; }
        input { width: 70%; padding: 10px; }
        button { padding: 10px 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Agent Dashboard</h1>
        
        <div class="status" id="status">Status: Disconnected</div>
        
        <div>
            <button onclick="createSession()">Create Session</button>
            <button onclick="getTools()">Refresh Tools</button>
        </div>
        
        <h2>Submit Query</h2>
        <input type="text" id="prompt" placeholder="Enter your query...">
        <button onclick="submitQuery()">Submit</button>
        
        <h2>Activity Log</h2>
        <div class="events" id="events"></div>
        
        <h2>Response</h2>
        <div id="response"></div>
    </div>
    
    <script>
        const socket = io();
        let sessionId = null;
        
        socket.on('session_created', (data) => {
            sessionId = data.session_id;
            document.getElementById('status').textContent = `Status: Session ${sessionId}`;
        });
        
        socket.on('agent_event', (data) => {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event';
            eventDiv.textContent = `[${data.event_type}] ${JSON.stringify(data.data)}`;
            eventsDiv.appendChild(eventDiv);
            eventsDiv.scrollTop = eventsDiv.scrollHeight;
        });
        
        socket.on('query_complete', (data) => {
            document.getElementById('response').innerHTML = `
                <p><strong>Success:</strong> ${data.success}</p>
                <p><strong>Response:</strong> ${data.response}</p>
                <p><strong>Tool:</strong> ${data.metadata.tool_name}</p>
            `;
        });
        
        function createSession() {
            socket.emit('create_session');
        }
        
        function submitQuery() {
            const prompt = document.getElementById('prompt').value;
            if (prompt) {
                document.getElementById('events').innerHTML = '';
                socket.emit('submit_query', { prompt });
            }
        }
        
        function getTools() {
            socket.emit('get_tools');
        }
        
        // Auto-create session on load
        createSession();
    </script>
</body>
</html>
```

---

## Summary

These code examples demonstrate:

1. **Basic Integration**: Simple query submission and response handling
2. **Advanced Integration**: Full event handling with progress tracking
3. **Batch Processing**: Processing multiple queries in sequence
4. **Tool Synthesis**: Explicitly requesting new tool creation
5. **Semantic Search**: Finding tools using natural language
6. **React Integration**: Building interactive UIs with React hooks
7. **Backend Integration**: Integrating into Express.js backends
8. **Real-time Dashboards**: Building monitoring and control interfaces

For more information, see:
- [Integration Guide](./integration-guide.md)
- [WebSocket Events](./websocket-events.md)
- [API Reference](./openapi.yaml)
