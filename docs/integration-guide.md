# Integration Guide

## Overview

This guide provides complete examples for integrating with the Self-Engineering Agent Framework. Whether you're building a custom client, integrating into an existing application, or creating automation workflows, this guide will help you get started.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Starting a Session](#starting-a-session)
3. [Submitting Queries via REST](#submitting-queries-via-rest)
4. [Handling WebSocket Events](#handling-websocket-events)
5. [Retrieving Tool Information](#retrieving-tool-information)
6. [Building Custom Clients](#building-custom-clients)
7. [Common Workflows](#common-workflows)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)

---

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+ (for JavaScript examples)
- Access to a running Self-Engineering Agent Framework instance
- OpenAI API key
- Supabase credentials

### Installation

```bash
# Clone the repository
git clone https://github.com/haider-toha/Self-Engineering-Agent-Framework.git
cd Self-Engineering-Agent-Framework

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials:
# OPENAI_API_KEY=your_key_here
# SUPABASE_URL=your_url_here
# SUPABASE_KEY=your_key_here

# Start the server
python web/app.py
```

The server will start on `http://localhost:5001`.

---

## Starting a Session

Sessions maintain conversational context across multiple requests. Always create a session before submitting queries.

### REST API

```bash
# Create a new session
curl -X POST http://localhost:5001/api/session \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Python

```python
import requests

# Create session
response = requests.post('http://localhost:5001/api/session')
data = response.json()

if data['success']:
    session_id = data['session_id']
    print(f"Session created: {session_id}")
else:
    print(f"Error: {data['error']}")
```

### JavaScript

```javascript
async function createSession() {
  const response = await fetch('http://localhost:5001/api/session', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  const data = await response.json();
  
  if (data.success) {
    console.log(`Session created: ${data.session_id}`);
    return data.session_id;
  } else {
    throw new Error(data.error);
  }
}

// Usage
const sessionId = await createSession();
```

---

## Submitting Queries via REST

While the primary interface uses WebSocket for real-time updates, you can also interact via REST endpoints.

### Get Session Messages

```bash
# Retrieve conversation history
curl http://localhost:5001/api/session/{session_id}/messages?limit=10
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "messages": [
    {
      "role": "user",
      "content": "Calculate profit margins from data.csv",
      "message_index": 0,
      "created_at": "2025-11-04T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "The average profit margin is 23.5%.",
      "message_index": 1,
      "created_at": "2025-11-04T10:30:15Z"
    }
  ]
}
```

### Python Example

```python
import requests

def get_session_messages(session_id, limit=10):
    url = f'http://localhost:5001/api/session/{session_id}/messages'
    params = {'limit': limit}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['success']:
        for msg in data['messages']:
            role = msg['role'].upper()
            content = msg['content']
            print(f"[{role}] {content}")
    else:
        print(f"Error: {data['error']}")

# Usage
get_session_messages('550e8400-e29b-41d4-a716-446655440000')
```

---

## Handling WebSocket Events

WebSocket provides real-time bidirectional communication for live progress updates.

### JavaScript Client

```javascript
// Include Socket.IO client
// <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

const socket = io('http://localhost:5001');

// Connection events
socket.on('connect', () => {
  console.log('Connected to agent');
});

socket.on('disconnect', () => {
  console.log('Disconnected from agent');
});

// Create session first
async function initialize() {
  const sessionId = await createSession();
  
  // Set up event handlers
  socket.on('agent_event', (data) => {
    handleAgentEvent(data.event_type, data.data);
  });
  
  socket.on('query_complete', (data) => {
    if (data.success) {
      console.log('Response:', data.response);
      console.log('Tool used:', data.metadata.tool_name);
      console.log('Synthesized:', data.metadata.synthesized);
    } else {
      console.error('Error:', data.response);
    }
  });
  
  socket.on('tool_count', (data) => {
    console.log(`Available tools: ${data.count}`);
  });
  
  socket.on('error', (data) => {
    console.error('Error:', data.message);
  });
  
  // Submit query
  socket.emit('query', {
    prompt: 'Calculate profit margins from data/ecommerce_products.csv',
    session_id: sessionId
  });
}

function handleAgentEvent(eventType, data) {
  switch (eventType) {
    case 'searching':
      console.log('Searching for existing tool...');
      break;
    case 'tool_found':
      console.log(`Found tool: ${data.tool_name} (${(data.similarity * 100).toFixed(1)}% match)`);
      break;
    case 'entering_synthesis_mode':
      console.log('Creating new tool...');
      break;
    case 'synthesis_step':
      console.log(`Synthesis: ${data.step} - ${data.status}`);
      break;
    case 'synthesis_successful':
      console.log(`Tool created: ${data.tool_name}`);
      break;
    case 'executing':
      console.log(`Executing: ${data.tool_name}`);
      break;
    case 'execution_complete':
      console.log(`Result: ${data.result}`);
      break;
    default:
      console.log(`[${eventType}]`, data);
  }
}

initialize();
```

### Python Client with Socket.IO

```python
import socketio
import requests

# Create Socket.IO client
sio = socketio.Client()

# Connection events
@sio.on('connect')
def on_connect():
    print('Connected to agent')

@sio.on('disconnect')
def on_disconnect():
    print('Disconnected from agent')

# Agent events
@sio.on('agent_event')
def on_agent_event(data):
    event_type = data['event_type']
    event_data = data['data']
    
    if event_type == 'searching':
        print('Searching for existing tool...')
    elif event_type == 'tool_found':
        print(f"Found tool: {event_data['tool_name']}")
    elif event_type == 'synthesis_step':
        print(f"Synthesis: {event_data['step']} - {event_data['status']}")
    elif event_type == 'executing':
        print(f"Executing: {event_data['tool_name']}")
    else:
        print(f"[{event_type}] {event_data}")

@sio.on('query_complete')
def on_query_complete(data):
    if data['success']:
        print(f"Response: {data['response']}")
        print(f"Tool: {data['metadata']['tool_name']}")
    else:
        print(f"Error: {data['response']}")

@sio.on('error')
def on_error(data):
    print(f"Error: {data['message']}")

# Main function
def main():
    # Connect to server
    sio.connect('http://localhost:5001')
    
    # Create session
    response = requests.post('http://localhost:5001/api/session')
    session_id = response.json()['session_id']
    print(f"Session: {session_id}")
    
    # Submit query
    sio.emit('query', {
        'prompt': 'Calculate profit margins from data/ecommerce_products.csv',
        'session_id': session_id
    })
    
    # Wait for completion
    sio.wait()

if __name__ == '__main__':
    main()
```

---

## Retrieving Tool Information

### Get All Tools

```bash
# List all available tools
curl http://localhost:5001/api/tools
```

**Response:**
```json
{
  "success": true,
  "count": 15,
  "tools": [
    {
      "name": "calculate_profit_margins",
      "docstring": "Calculate profit margins from a CSV file",
      "file_path": "tools/calculate_profit_margins.py",
      "test_path": "tools/test_calculate_profit_margins.py",
      "timestamp": "2025-11-04T10:30:00Z"
    }
  ]
}
```

### Get Tool Details

```bash
# Get detailed information about a specific tool
curl http://localhost:5001/api/tools/calculate_profit_margins
```

**Response:**
```json
{
  "success": true,
  "tool": {
    "name": "calculate_profit_margins",
    "code": "import pandas as pd\n\ndef calculate_profit_margins(csv_path):\n    ...",
    "test_code": "import pytest\nfrom calculate_profit_margins import calculate_profit_margins\n...",
    "docstring": "Calculate profit margins from a CSV file",
    "timestamp": "2025-11-04T10:30:00Z",
    "file_path": "tools/calculate_profit_margins.py",
    "test_path": "tools/test_calculate_profit_margins.py"
  }
}
```

### Python Example

```python
import requests

def get_all_tools():
    response = requests.get('http://localhost:5001/api/tools')
    data = response.json()
    
    if data['success']:
        print(f"Available tools: {data['count']}")
        for tool in data['tools']:
            print(f"  - {tool['name']}: {tool['docstring']}")
    else:
        print(f"Error: {data['error']}")

def get_tool_details(tool_name):
    response = requests.get(f'http://localhost:5001/api/tools/{tool_name}')
    data = response.json()
    
    if data['success']:
        tool = data['tool']
        print(f"Tool: {tool['name']}")
        print(f"Description: {tool['docstring']}")
        print(f"\nCode:\n{tool['code']}")
        print(f"\nTests:\n{tool['test_code']}")
    else:
        print(f"Error: {data['error']}")

# Usage
get_all_tools()
get_tool_details('calculate_profit_margins')
```

---

## Building Custom Clients

### Complete Python Client Class

```python
import socketio
import requests
from typing import Callable, Optional, Dict, List

class AgentClient:
    """
    Complete client for the Self-Engineering Agent Framework.
    
    Features:
    - Session management
    - Query submission
    - Real-time event handling
    - Tool retrieval
    - Analytics access
    """
    
    def __init__(self, base_url: str = 'http://localhost:5001'):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.sio = socketio.Client()
        self._setup_socket_handlers()
        
    def _setup_socket_handlers(self):
        """Set up Socket.IO event handlers."""
        
        @self.sio.on('connect')
        def on_connect():
            print('Connected to agent')
            
        @self.sio.on('disconnect')
        def on_disconnect():
            print('Disconnected from agent')
            
        @self.sio.on('agent_event')
        def on_agent_event(data):
            if hasattr(self, '_event_callback') and self._event_callback:
                self._event_callback(data['event_type'], data['data'])
                
        @self.sio.on('query_complete')
        def on_query_complete(data):
            if hasattr(self, '_complete_callback') and self._complete_callback:
                self._complete_callback(data)
                
        @self.sio.on('error')
        def on_error(data):
            print(f"Error: {data['message']}")
    
    def connect(self):
        """Connect to the agent server."""
        self.sio.connect(self.base_url)
        
    def disconnect(self):
        """Disconnect from the agent server."""
        self.sio.disconnect()
        
    def create_session(self) -> str:
        """Create a new session."""
        response = requests.post(f'{self.base_url}/api/session')
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def submit_query(self, prompt: str, 
                    event_callback: Optional[Callable] = None,
                    complete_callback: Optional[Callable] = None):
        """
        Submit a query to the agent.
        
        Args:
            prompt: Natural language query
            event_callback: Function called for each agent event
            complete_callback: Function called when query completes
        """
        if not self.session_id:
            raise Exception("No active session. Call create_session() first.")
        
        self._event_callback = event_callback
        self._complete_callback = complete_callback
        
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': self.session_id
        })
    
    def get_tools(self) -> List[Dict]:
        """Get all available tools."""
        response = requests.get(f'{self.base_url}/api/tools')
        data = response.json()
        
        if data['success']:
            return data['tools']
        else:
            raise Exception(f"Failed to get tools: {data['error']}")
    
    def get_tool_details(self, tool_name: str) -> Dict:
        """Get detailed information about a tool."""
        response = requests.get(f'{self.base_url}/api/tools/{tool_name}')
        data = response.json()
        
        if data['success']:
            return data['tool']
        else:
            raise Exception(f"Failed to get tool: {data['error']}")
    
    def get_session_messages(self, limit: int = 10) -> List[Dict]:
        """Get recent messages from the current session."""
        if not self.session_id:
            raise Exception("No active session")
        
        response = requests.get(
            f'{self.base_url}/api/session/{self.session_id}/messages',
            params={'limit': limit}
        )
        data = response.json()
        
        if data['success']:
            return data['messages']
        else:
            raise Exception(f"Failed to get messages: {data['error']}")
    
    def get_workflow_patterns(self, min_frequency: int = 2, 
                             limit: int = 10) -> List[Dict]:
        """Get detected workflow patterns."""
        response = requests.get(
            f'{self.base_url}/api/analytics/patterns',
            params={'min_frequency': min_frequency, 'limit': limit}
        )
        data = response.json()
        
        if data['success']:
            return data['patterns']
        else:
            raise Exception(f"Failed to get patterns: {data['error']}")
    
    def get_tool_relationships(self, tool_name: Optional[str] = None,
                              min_confidence: float = 0.5) -> List[Dict]:
        """Get tool relationship analytics."""
        params = {'min_confidence': min_confidence}
        if tool_name:
            params['tool_name'] = tool_name
            
        response = requests.get(
            f'{self.base_url}/api/analytics/relationships',
            params=params
        )
        data = response.json()
        
        if data['success']:
            return data['relationships']
        else:
            raise Exception(f"Failed to get relationships: {data['error']}")
    
    def wait(self):
        """Wait for all events to complete."""
        self.sio.wait()


# Usage Example
def main():
    # Initialize client
    client = AgentClient('http://localhost:5001')
    
    # Connect
    client.connect()
    
    # Create session
    session_id = client.create_session()
    print(f"Session: {session_id}")
    
    # Define callbacks
    def on_event(event_type, data):
        print(f"[{event_type}] {data}")
    
    def on_complete(data):
        if data['success']:
            print(f"\nResponse: {data['response']}")
            print(f"Tool: {data['metadata']['tool_name']}")
            print(f"Synthesized: {data['metadata']['synthesized']}")
        else:
            print(f"Error: {data['response']}")
        
        # Get conversation history
        messages = client.get_session_messages()
        print(f"\nConversation history ({len(messages)} messages):")
        for msg in messages:
            print(f"  [{msg['role']}] {msg['content']}")
    
    # Submit query
    client.submit_query(
        prompt='Calculate profit margins from data/ecommerce_products.csv',
        event_callback=on_event,
        complete_callback=on_complete
    )
    
    # Wait for completion
    client.wait()
    
    # Get available tools
    tools = client.get_tools()
    print(f"\nAvailable tools: {len(tools)}")
    
    # Disconnect
    client.disconnect()

if __name__ == '__main__':
    main()
```

---

## Common Workflows

### Workflow 1: Tool Synthesis

Request a new capability and have the agent synthesize it.

```python
client = AgentClient()
client.connect()
client.create_session()

# Request synthesis
client.submit_query(
    prompt='Create a function to calculate compound interest with principal, rate, and time parameters',
    event_callback=lambda t, d: print(f"[{t}] {d}"),
    complete_callback=lambda d: print(f"Result: {d['response']}")
)

client.wait()
```

### Workflow 2: Tool Search and Execution

Search for an existing tool and execute it.

```python
client = AgentClient()
client.connect()
client.create_session()

# Search and execute
client.submit_query(
    prompt='Calculate profit margins from data/sales.csv',
    event_callback=lambda t, d: print(f"[{t}] {d}"),
    complete_callback=lambda d: print(f"Result: {d['response']}")
)

client.wait()
```

### Workflow 3: Multi-Tool Workflow

Execute a complex workflow requiring multiple tools.

```python
client = AgentClient()
client.connect()
client.create_session()

# Multi-step workflow
client.submit_query(
    prompt='Load data from sales.csv, calculate profit margins, and generate a summary report',
    event_callback=lambda t, d: print(f"[{t}] {d}"),
    complete_callback=lambda d: print(f"Result: {d['response']}")
)

client.wait()
```

### Workflow 4: Conversational Interaction

Have a multi-turn conversation with context.

```python
client = AgentClient()
client.connect()
session_id = client.create_session()

# First query
client.submit_query(
    prompt='Load data from sales.csv',
    complete_callback=lambda d: print(f"Response 1: {d['response']}")
)
client.wait()

# Follow-up query (uses context)
client.submit_query(
    prompt='Now calculate the average profit margin',
    complete_callback=lambda d: print(f"Response 2: {d['response']}")
)
client.wait()

# Another follow-up
client.submit_query(
    prompt='What was the highest margin?',
    complete_callback=lambda d: print(f"Response 3: {d['response']}")
)
client.wait()

# View conversation history
messages = client.get_session_messages()
for msg in messages:
    print(f"[{msg['role']}] {msg['content']}")
```

### Workflow 5: Analytics and Pattern Discovery

Analyze learned patterns and tool relationships.

```python
client = AgentClient()
client.connect()

# Get workflow patterns
patterns = client.get_workflow_patterns(min_frequency=3)
print("Detected patterns:")
for pattern in patterns:
    print(f"  {pattern['pattern_name']}: {pattern['tool_sequence']}")
    print(f"    Frequency: {pattern['frequency']}, Success: {pattern['avg_success_rate']:.1%}")

# Get tool relationships
relationships = client.get_tool_relationships(min_confidence=0.7)
print("\nTool relationships:")
for rel in relationships:
    print(f"  {rel['tool_a']} → {rel['tool_b']} (confidence: {rel['confidence_score']:.2f})")

client.disconnect()
```

---

## Error Handling

### Handling Connection Errors

```python
import socketio
import time

def connect_with_retry(client, max_retries=3, delay=2):
    """Connect with exponential backoff."""
    for attempt in range(max_retries):
        try:
            client.connect()
            return True
        except socketio.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                print(f"Connection failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Failed to connect after {max_retries} attempts")
                raise

# Usage
client = AgentClient()
connect_with_retry(client)
```

### Handling Query Errors

```python
def safe_query(client, prompt):
    """Submit query with error handling."""
    try:
        result = {'success': False, 'error': None}
        
        def on_complete(data):
            result['success'] = data['success']
            result['response'] = data['response']
            if not data['success']:
                result['error'] = data['response']
        
        client.submit_query(
            prompt=prompt,
            complete_callback=on_complete
        )
        
        client.wait()
        
        if result['success']:
            return result['response']
        else:
            raise Exception(f"Query failed: {result['error']}")
            
    except Exception as e:
        print(f"Error executing query: {e}")
        return None

# Usage
response = safe_query(client, 'Calculate profit margins')
if response:
    print(f"Success: {response}")
```

### Timeout Handling

```python
import threading

def query_with_timeout(client, prompt, timeout=60):
    """Submit query with timeout."""
    result = {'completed': False, 'data': None}
    
    def on_complete(data):
        result['completed'] = True
        result['data'] = data
    
    client.submit_query(prompt=prompt, complete_callback=on_complete)
    
    # Wait with timeout
    start_time = time.time()
    while not result['completed']:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Query timed out after {timeout}s")
        time.sleep(0.1)
    
    return result['data']

# Usage
try:
    response = query_with_timeout(client, 'Complex query', timeout=30)
    print(f"Response: {response['response']}")
except TimeoutError as e:
    print(f"Error: {e}")
```

---

## Best Practices

### 1. Session Management

Always create and maintain sessions for conversational interactions:

```python
# Good
session_id = client.create_session()
client.submit_query('First query', session_id=session_id)
client.submit_query('Follow-up query', session_id=session_id)

# Bad - no session context
client.submit_query('First query')
client.submit_query('Follow-up query')  # No context from first query
```

### 2. Event Handling

Implement comprehensive event handlers for better user experience:

```python
def detailed_event_handler(event_type, data):
    """Detailed event handler with user feedback."""
    
    event_messages = {
        'searching': 'Searching for existing tools...',
        'tool_found': f"Found tool: {data.get('tool_name', 'unknown')}",
        'entering_synthesis_mode': 'Creating new tool...',
        'synthesis_step': f"Synthesis: {data.get('step', 'unknown')}",
        'executing': f"Executing: {data.get('tool_name', 'unknown')}",
        'execution_complete': 'Execution complete',
    }
    
    message = event_messages.get(event_type, f"[{event_type}]")
    print(message)
    
    # Log to file or database for debugging
    log_event(event_type, data)
```

### 3. Resource Cleanup

Always clean up resources when done:

```python
try:
    client = AgentClient()
    client.connect()
    client.create_session()
    
    # Do work...
    
finally:
    client.disconnect()
```

### 4. Batch Operations

For multiple queries, reuse the same session:

```python
client = AgentClient()
client.connect()
session_id = client.create_session()

queries = [
    'Load data from sales.csv',
    'Calculate profit margins',
    'Generate summary report'
]

for query in queries:
    client.submit_query(query)
    client.wait()

client.disconnect()
```

### 5. Error Recovery

Implement graceful error recovery:

```python
def robust_query(client, prompt, max_retries=3):
    """Query with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            result = execute_query(client, prompt)
            if result['success']:
                return result
            else:
                print(f"Attempt {attempt + 1} failed: {result['error']}")
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    raise Exception(f"Failed after {max_retries} attempts")
```

### 6. Monitoring and Logging

Implement comprehensive logging:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_client.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('AgentClient')

def logged_query(client, prompt):
    """Query with comprehensive logging."""
    logger.info(f"Submitting query: {prompt}")
    
    def on_event(event_type, data):
        logger.debug(f"Event: {event_type} - {data}")
    
    def on_complete(data):
        if data['success']:
            logger.info(f"Query completed: {data['metadata']['tool_name']}")
        else:
            logger.error(f"Query failed: {data['response']}")
    
    client.submit_query(
        prompt=prompt,
        event_callback=on_event,
        complete_callback=on_complete
    )
```

---

## Advanced Integration Examples

### Integration with Flask Application

```python
from flask import Flask, request, jsonify
from agent_client import AgentClient

app = Flask(__name__)
agent_client = AgentClient()
agent_client.connect()

@app.route('/api/query', methods=['POST'])
def handle_query():
    data = request.json
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    # Create session if not exists
    session_id = data.get('session_id')
    if not session_id:
        session_id = agent_client.create_session()
    
    # Execute query
    result = {'completed': False}
    
    def on_complete(response_data):
        result['completed'] = True
        result['data'] = response_data
    
    agent_client.submit_query(
        prompt=prompt,
        complete_callback=on_complete
    )
    
    # Wait for completion
    while not result['completed']:
        time.sleep(0.1)
    
    return jsonify({
        'success': result['data']['success'],
        'response': result['data']['response'],
        'session_id': session_id
    })

if __name__ == '__main__':
    app.run(port=5002)
```

### Integration with CLI Tool

```python
import click
from agent_client import AgentClient

@click.group()
def cli():
    """Self-Engineering Agent CLI"""
    pass

@cli.command()
@click.argument('prompt')
@click.option('--session', '-s', help='Session ID')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def query(prompt, session, verbose):
    """Submit a query to the agent."""
    client = AgentClient()
    client.connect()
    
    if not session:
        session = client.create_session()
        click.echo(f"Created session: {session}")
    
    if verbose:
        def on_event(event_type, data):
            click.echo(f"[{event_type}] {data}")
        event_callback = on_event
    else:
        event_callback = None
    
    def on_complete(data):
        if data['success']:
            click.echo(f"\n{data['response']}")
        else:
            click.echo(f"Error: {data['response']}", err=True)
    
    client.submit_query(
        prompt=prompt,
        event_callback=event_callback,
        complete_callback=on_complete
    )
    
    client.wait()
    client.disconnect()

@cli.command()
def tools():
    """List all available tools."""
    client = AgentClient()
    client.connect()
    
    tools = client.get_tools()
    click.echo(f"Available tools: {len(tools)}")
    for tool in tools:
        click.echo(f"  - {tool['name']}: {tool['docstring']}")
    
    client.disconnect()

if __name__ == '__main__':
    cli()
```

Usage:
```bash
# Submit query
python cli.py query "Calculate profit margins from data.csv" --verbose

# List tools
python cli.py tools
```

---

## Troubleshooting

### Common Issues

**Issue: Connection refused**
```
Solution: Ensure the server is running on the correct port (5001)
```

**Issue: Session not found**
```
Solution: Create a new session before submitting queries
```

**Issue: Tool synthesis fails**
```
Solution: Check OpenAI API key and ensure sufficient credits
```

**Issue: Database connection error**
```
Solution: Verify Supabase credentials in .env file
```

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = AgentClient()
# All operations will now log debug information
```

---

## Additional Resources

- [REST API Documentation](openapi.yaml)
- [WebSocket Events Reference](websocket-events.md)
- [Python API Reference](python-api-reference.md)
- [Database Schema Documentation](database-schema.md)
- [GitHub Repository](https://github.com/haider-toha/Self-Engineering-Agent-Framework)

---

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/haider-toha/Self-Engineering-Agent-Framework/issues
- Documentation: https://github.com/haider-toha/Self-Engineering-Agent-Framework/tree/main/docs
