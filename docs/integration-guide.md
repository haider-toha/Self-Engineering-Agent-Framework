# Integration Guide

This guide covers key workflows for integrating with the Self-Engineering Agent Framework API. It provides detailed examples of common integration patterns and best practices.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Session Management](#session-management)
3. [Submitting Queries](#submitting-queries)
4. [Handling Real-time Events](#handling-real-time-events)
5. [Retrieving Tool Information](#retrieving-tool-information)
6. [Managing Conversational Context](#managing-conversational-context)
7. [Analytics and Insights](#analytics-and-insights)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## Getting Started

### Prerequisites

- Python 3.8+ or Node.js 14+ (depending on your integration language)
- Network access to the agent server (default: `http://localhost:5001`)
- Basic understanding of REST APIs and WebSocket/Socket.IO

### Installation

**Python:**
```bash
pip install requests python-socketio
```

**JavaScript/Node.js:**
```bash
npm install socket.io-client axios
```

---

## Session Management

Sessions enable the agent to maintain conversational context across multiple requests. Always create a session before submitting queries.

### Creating a New Session

**REST API:**
```http
POST /api/session
Content-Type: application/json
```

**Python Example:**
```python
import requests

response = requests.post('http://localhost:5001/api/session')
data = response.json()

if data['success']:
    session_id = data['session_id']
    print(f"Session created: {session_id}")
else:
    print(f"Error: {data['error']}")
```

**JavaScript Example:**
```javascript
const axios = require('axios');

async function createSession() {
    const response = await axios.post('http://localhost:5001/api/session');
    
    if (response.data.success) {
        const sessionId = response.data.session_id;
        console.log(`Session created: ${sessionId}`);
        return sessionId;
    } else {
        console.error(`Error: ${response.data.error}`);
        return null;
    }
}
```

**Response:**
```json
{
    "success": true,
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Retrieving Session Messages

**REST API:**
```http
GET /api/session/{session_id}/messages?limit=20
```

**Python Example:**
```python
def get_session_messages(session_id, limit=20):
    response = requests.get(
        f'http://localhost:5001/api/session/{session_id}/messages',
        params={'limit': limit}
    )
    data = response.json()
    
    if data['success']:
        return data['messages']
    else:
        print(f"Error: {data['error']}")
        return []
```

**JavaScript Example:**
```javascript
async function getSessionMessages(sessionId, limit = 20) {
    const response = await axios.get(
        `http://localhost:5001/api/session/${sessionId}/messages`,
        { params: { limit } }
    );
    
    if (response.data.success) {
        return response.data.messages;
    } else {
        console.error(`Error: ${response.data.error}`);
        return [];
    }
}
```

---

## Submitting Queries

Queries are submitted via WebSocket using Socket.IO for real-time bidirectional communication.

### Basic Query Submission

**Python Example:**
```python
import socketio

# Create Socket.IO client
sio = socketio.Client()

# Connect to server
sio.connect('http://localhost:5001')

# Submit query
sio.emit('query', {
    'prompt': 'Calculate profit margins from data/ecommerce_products.csv',
    'session_id': session_id
})

# Wait for response
@sio.on('query_complete')
def on_query_complete(data):
    if data['success']:
        print(f"Response: {data['response']}")
        print(f"Tool used: {data['metadata']['tool_name']}")
    else:
        print(f"Query failed: {data['response']}")
    
    sio.disconnect()

sio.wait()
```

**JavaScript Example:**
```javascript
const io = require('socket.io-client');

const socket = io('http://localhost:5001');

socket.on('connect', () => {
    console.log('Connected to agent');
    
    // Submit query
    socket.emit('query', {
        prompt: 'Calculate profit margins from data/ecommerce_products.csv',
        session_id: sessionId
    });
});

socket.on('query_complete', (data) => {
    if (data.success) {
        console.log(`Response: ${data.response}`);
        console.log(`Tool used: ${data.metadata.tool_name}`);
    } else {
        console.error(`Query failed: ${data.response}`);
    }
    
    socket.disconnect();
});
```

---

## Handling Real-time Events

The agent emits various events during query processing to provide real-time progress updates.

### Event Handling Pattern

**Python Example:**
```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to agent')

@sio.on('agent_event')
def on_agent_event(data):
    event_type = data['event_type']
    event_data = data['data']
    
    if event_type == 'searching':
        print('Searching for existing tool...')
    
    elif event_type == 'tool_found':
        print(f"Found tool: {event_data['tool_name']}")
        print(f"Similarity: {event_data['similarity']:.2%}")
    
    elif event_type == 'no_tool_found':
        print('No matching tool found')
    
    elif event_type == 'entering_synthesis_mode':
        print('Creating new tool...')
    
    elif event_type == 'synthesis_step':
        step = event_data['step']
        status = event_data['status']
        print(f"Synthesis: {step} - {status}")
    
    elif event_type == 'synthesis_successful':
        print(f"Tool synthesized: {event_data['tool_name']}")
    
    elif event_type == 'executing':
        print(f"Executing: {event_data['tool_name']}")
    
    elif event_type == 'execution_complete':
        print(f"Result: {event_data['result']}")

@sio.on('query_complete')
def on_query_complete(data):
    print(f"\nFinal response: {data['response']}")
    sio.disconnect()

sio.connect('http://localhost:5001')
sio.emit('query', {
    'prompt': 'Your query here',
    'session_id': session_id
})
sio.wait()
```

**JavaScript Example:**
```javascript
const socket = io('http://localhost:5001');

socket.on('agent_event', (data) => {
    const { event_type, data: eventData } = data;
    
    switch (event_type) {
        case 'searching':
            console.log('Searching for existing tool...');
            break;
        
        case 'tool_found':
            console.log(`Found tool: ${eventData.tool_name}`);
            console.log(`Similarity: ${(eventData.similarity * 100).toFixed(1)}%`);
            break;
        
        case 'no_tool_found':
            console.log('No matching tool found');
            break;
        
        case 'entering_synthesis_mode':
            console.log('Creating new tool...');
            break;
        
        case 'synthesis_step':
            console.log(`Synthesis: ${eventData.step} - ${eventData.status}`);
            break;
        
        case 'synthesis_successful':
            console.log(`Tool synthesized: ${eventData.tool_name}`);
            break;
        
        case 'executing':
            console.log(`Executing: ${eventData.tool_name}`);
            break;
        
        case 'execution_complete':
            console.log(`Result: ${eventData.result}`);
            break;
    }
});

socket.on('query_complete', (data) => {
    console.log(`\nFinal response: ${data.response}`);
    socket.disconnect();
});
```

### Workflow Event Handling

For multi-tool workflows, additional events are emitted:

```python
@sio.on('agent_event')
def on_agent_event(data):
    event_type = data['event_type']
    event_data = data['data']
    
    if event_type == 'workflow_start':
        print(f"Starting workflow with {event_data['total_steps']} steps")
        for i, task in enumerate(event_data['tasks'], 1):
            print(f"  {i}. {task}")
    
    elif event_type == 'workflow_step':
        print(f"\nStep {event_data['step']}/{event_data['total']}: {event_data['task']}")
    
    elif event_type == 'workflow_step_complete':
        print(f"  ✓ Complete: {event_data['result']}")
    
    elif event_type == 'workflow_complete':
        print(f"\nWorkflow complete!")
        print(f"Tool sequence: {' → '.join(event_data['tool_sequence'])}")
```

---

## Retrieving Tool Information

### List All Available Tools

**REST API:**
```http
GET /api/tools
```

**Python Example:**
```python
def get_all_tools():
    response = requests.get('http://localhost:5001/api/tools')
    data = response.json()
    
    if data['success']:
        tools = data['tools']
        print(f"Found {data['count']} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['docstring']}")
        return tools
    else:
        print(f"Error: {data['error']}")
        return []
```

**JavaScript Example:**
```javascript
async function getAllTools() {
    const response = await axios.get('http://localhost:5001/api/tools');
    
    if (response.data.success) {
        const tools = response.data.tools;
        console.log(`Found ${response.data.count} tools:`);
        tools.forEach(tool => {
            console.log(`  - ${tool.name}: ${tool.docstring}`);
        });
        return tools;
    } else {
        console.error(`Error: ${response.data.error}`);
        return [];
    }
}
```

### Get Tool Details

**REST API:**
```http
GET /api/tools/{tool_name}
```

**Python Example:**
```python
def get_tool_details(tool_name):
    response = requests.get(f'http://localhost:5001/api/tools/{tool_name}')
    data = response.json()
    
    if data['success']:
        tool = data['tool']
        print(f"Tool: {tool['name']}")
        print(f"Description: {tool['docstring']}")
        print(f"File: {tool['file_path']}")
        print(f"\nImplementation:\n{tool['code']}")
        print(f"\nTests:\n{tool['test_code']}")
        return tool
    else:
        print(f"Error: {data['error']}")
        return None
```

---

## Managing Conversational Context

The agent maintains conversational context within sessions, enabling multi-turn interactions.

### Context-Aware Queries

```python
import socketio
import requests

# Create session
response = requests.post('http://localhost:5001/api/session')
session_id = response.json()['session_id']

sio = socketio.Client()
sio.connect('http://localhost:5001')

# First query
sio.emit('query', {
    'prompt': 'Load data from data/ecommerce_products.csv',
    'session_id': session_id
})

# Wait for completion
@sio.on('query_complete')
def on_first_complete(data):
    print(f"First query: {data['response']}")
    
    # Second query - uses context from first
    sio.emit('query', {
        'prompt': 'Now calculate the average profit margin',
        'session_id': session_id
    })

@sio.on('query_complete')
def on_second_complete(data):
    print(f"Second query: {data['response']}")
    sio.disconnect()

sio.wait()
```

### Retrieving Conversation History

```python
def print_conversation_history(session_id):
    response = requests.get(
        f'http://localhost:5001/api/session/{session_id}/messages',
        params={'limit': 10}
    )
    data = response.json()
    
    if data['success']:
        print(f"\nConversation History ({data['count']} messages):")
        for msg in data['messages']:
            role = "User" if msg['role'] == 'user' else "Agent"
            print(f"\n{role}: {msg['content']}")
    else:
        print(f"Error: {data['error']}")
```

---

## Analytics and Insights

### Tool Relationships

Discover which tools are frequently used together:

```python
def get_tool_relationships(tool_name=None, min_confidence=0.5):
    params = {'min_confidence': min_confidence}
    if tool_name:
        params['tool_name'] = tool_name
    
    response = requests.get(
        'http://localhost:5001/api/analytics/relationships',
        params=params
    )
    data = response.json()
    
    if data['success']:
        print(f"Found {data['count']} relationships:")
        for rel in data['relationships']:
            print(f"  {rel['tool_a']} → {rel['tool_b']}")
            print(f"    Confidence: {rel['confidence_score']:.2%}")
            print(f"    Frequency: {rel['frequency']}")
        return data['relationships']
    else:
        print(f"Error: {data['error']}")
        return []
```

### Workflow Patterns

Discover learned multi-tool workflows:

```python
def get_workflow_patterns(min_frequency=2, limit=10):
    response = requests.get(
        'http://localhost:5001/api/analytics/patterns',
        params={'min_frequency': min_frequency, 'limit': limit}
    )
    data = response.json()
    
    if data['success']:
        print(f"Found {data['count']} patterns:")
        for pattern in data['patterns']:
            print(f"\n{pattern['pattern_name']}:")
            print(f"  Sequence: {' → '.join(pattern['tool_sequence'])}")
            print(f"  Frequency: {pattern['frequency']}")
            print(f"  Success Rate: {pattern['avg_success_rate']:.2%}")
        return data['patterns']
    else:
        print(f"Error: {data['error']}")
        return []
```

### Session History

Retrieve execution history for a session:

```python
def get_session_history(session_id, limit=100):
    response = requests.get(
        f'http://localhost:5001/api/analytics/sessions/{session_id}',
        params={'limit': limit}
    )
    data = response.json()
    
    if data['success']:
        print(f"Session {session_id} - {data['count']} executions:")
        for exec in data['executions']:
            print(f"\n{exec['tool_name']}:")
            print(f"  Success: {exec['success']}")
            print(f"  Time: {exec['execution_time_ms']}ms")
            print(f"  Inputs: {exec['inputs']}")
        return data['executions']
    else:
        print(f"Error: {data['error']}")
        return []
```

### Overall Statistics

```python
def get_workflow_stats():
    response = requests.get('http://localhost:5001/api/analytics/stats')
    data = response.json()
    
    if data['success']:
        stats = data['stats']
        print("Workflow Statistics:")
        print(f"  Total Patterns: {stats['total_patterns']}")
        print(f"  Total Relationships: {stats['total_relationships']}")
        
        if stats['most_frequent_pattern']:
            pattern = stats['most_frequent_pattern']
            print(f"\nMost Frequent Pattern: {pattern['name']}")
            print(f"  Frequency: {pattern['frequency']}")
            print(f"  Tools: {' → '.join(pattern['tools'])}")
        
        print("\nMost Connected Tools:")
        for tool in stats['most_connected_tools']:
            print(f"  {tool['tool']}: {tool['connections']} connections")
        
        return stats
    else:
        print(f"Error: {data['error']}")
        return None
```

---

## Error Handling

### REST API Errors

```python
def safe_api_call(url, method='GET', **kwargs):
    try:
        if method == 'GET':
            response = requests.get(url, **kwargs)
        elif method == 'POST':
            response = requests.post(url, **kwargs)
        
        response.raise_for_status()
        data = response.json()
        
        if not data.get('success', False):
            print(f"API Error: {data.get('error', 'Unknown error')}")
            return None
        
        return data
    
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to agent server")
        return None
    
    except requests.exceptions.Timeout:
        print("Error: Request timed out")
        return None
    
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        return None
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### WebSocket Error Handling

```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to agent')

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from agent')

@sio.on('error')
def on_error(data):
    print(f"Agent error: {data['message']}")

@sio.on('connect_error')
def on_connect_error(data):
    print(f"Connection error: {data}")

try:
    sio.connect('http://localhost:5001', wait_timeout=10)
    sio.emit('query', {
        'prompt': 'Your query',
        'session_id': session_id
    })
    sio.wait()
except socketio.exceptions.ConnectionError:
    print("Failed to connect to agent server")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    if sio.connected:
        sio.disconnect()
```

---

## Best Practices

### 1. Always Use Sessions

Create a session before submitting queries to enable conversational context:

```python
# Good
session_id = create_session()
submit_query(prompt, session_id)

# Bad
submit_query(prompt, None)  # Will fail
```

### 2. Handle All Event Types

Implement handlers for all relevant event types to provide comprehensive feedback:

```python
@sio.on('agent_event')
def on_agent_event(data):
    event_type = data['event_type']
    # Handle all event types your application cares about
    if event_type in ['tool_found', 'synthesis_successful', 'execution_complete']:
        # Update UI or log progress
        pass
```

### 3. Implement Timeout Handling

Set appropriate timeouts for long-running operations:

```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Query processing timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300)  # 5 minute timeout

try:
    sio.wait()
except TimeoutError:
    print("Query took too long")
finally:
    signal.alarm(0)
```

### 4. Cache Tool Information

Cache tool lists to reduce API calls:

```python
class AgentClient:
    def __init__(self):
        self.tools_cache = None
        self.cache_timestamp = None
    
    def get_tools(self, force_refresh=False):
        now = time.time()
        if force_refresh or not self.tools_cache or (now - self.cache_timestamp) > 300:
            response = requests.get('http://localhost:5001/api/tools')
            if response.json()['success']:
                self.tools_cache = response.json()['tools']
                self.cache_timestamp = now
        return self.tools_cache
```

### 5. Use Semantic Tool Search

When you know a tool exists, use semantic search to find it:

```python
def find_similar_tool(query, threshold=0.7):
    tools = get_all_tools()
    # The agent uses vector similarity internally
    # You can also implement client-side filtering
    matching_tools = [
        tool for tool in tools
        if query.lower() in tool['name'].lower() or 
           query.lower() in tool['docstring'].lower()
    ]
    return matching_tools
```

### 6. Monitor Workflow Patterns

Regularly check for learned patterns to optimize your workflows:

```python
def optimize_workflow():
    patterns = get_workflow_patterns(min_frequency=5)
    
    for pattern in patterns:
        if pattern['avg_success_rate'] > 0.9:
            print(f"Consider using pattern: {pattern['pattern_name']}")
            print(f"  Sequence: {' → '.join(pattern['tool_sequence'])}")
```

### 7. Graceful Degradation

Handle cases where the agent is unavailable:

```python
def submit_query_with_fallback(prompt, session_id):
    try:
        return submit_query(prompt, session_id)
    except ConnectionError:
        print("Agent unavailable, using fallback logic")
        return fallback_handler(prompt)
```

### 8. Log All Interactions

Maintain logs for debugging and analysis:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@sio.on('agent_event')
def on_agent_event(data):
    logger.info(f"Agent event: {data['event_type']}", extra=data)
```

---

## Complete Integration Example

Here's a complete example that demonstrates all key workflows:

```python
import requests
import socketio
import time

class AgentClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.session_id = None
        self.sio = socketio.Client()
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.sio.on('connect')
        def on_connect():
            print('Connected to agent')
        
        @self.sio.on('agent_event')
        def on_agent_event(data):
            print(f"[{data['event_type']}] {data.get('data', {})}")
        
        @self.sio.on('query_complete')
        def on_query_complete(data):
            if data['success']:
                print(f"\n✓ Response: {data['response']}")
            else:
                print(f"\n✗ Error: {data['response']}")
            self.sio.disconnect()
    
    def create_session(self):
        response = requests.post(f'{self.base_url}/api/session')
        data = response.json()
        if data['success']:
            self.session_id = data['session_id']
            print(f"Session created: {self.session_id}")
            return self.session_id
        return None
    
    def submit_query(self, prompt):
        if not self.session_id:
            print("Error: No active session")
            return
        
        self.sio.connect(self.base_url)
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': self.session_id
        })
        self.sio.wait()
    
    def get_tools(self):
        response = requests.get(f'{self.base_url}/api/tools')
        return response.json()

# Usage
if __name__ == '__main__':
    client = AgentClient()
    client.create_session()
    client.submit_query('Calculate profit margins from data/ecommerce_products.csv')
    
    # Get available tools
    tools = client.get_tools()
    print(f"\nAvailable tools: {tools['count']}")
```

---

## Next Steps

- Review the [Code Examples](./code-examples.md) for more detailed implementation patterns
- Explore the [WebSocket Events](./websocket-events.md) documentation for complete event reference
- Check the [API Reference](./openapi.yaml) for detailed endpoint specifications
- Read the [SDK Documentation](./sdk-documentation.md) for extending the framework
