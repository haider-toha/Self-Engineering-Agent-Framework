# Quickstart Tutorial

This tutorial provides a complete end-to-end example of building a simple client application that interacts with the Self-Engineering Agent Framework API. By the end of this tutorial, you'll have a working application that can submit queries, handle real-time events, and display results.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Building a Simple Python Client](#building-a-simple-python-client)
4. [Building a Simple JavaScript Client](#building-a-simple-javascript-client)
5. [Building a Web Dashboard](#building-a-web-dashboard)
6. [Testing Your Integration](#testing-your-integration)
7. [Next Steps](#next-steps)

---

## Prerequisites

Before starting, ensure you have:

- **Agent Server Running**: The Self-Engineering Agent Framework server running on `http://localhost:5001`
- **Python 3.8+** or **Node.js 14+** installed
- **Basic knowledge** of REST APIs and WebSockets
- **Network access** to the agent server

### Verify Agent Server

Check that the agent server is running:

```bash
curl http://localhost:5001/api/tools
```

You should receive a JSON response with a list of available tools.

---

## Setup

### Python Setup

Install required dependencies:

```bash
pip install requests python-socketio
```

### JavaScript Setup

Install required dependencies:

```bash
npm install socket.io-client axios
```

---

## Building a Simple Python Client

Let's build a complete Python client that can interact with the agent.

### Step 1: Create the Client Class

Create a file named `agent_client.py`:

```python
#!/usr/bin/env python3
"""
Simple Agent Client - Complete example
"""

import requests
import socketio
import time
from typing import Optional, Callable, Dict, Any

class AgentClient:
    def __init__(self, base_url='http://localhost:5001'):
        self.base_url = base_url
        self.session_id = None
        self.sio = socketio.Client()
        self.result = None
        
    def create_session(self) -> bool:
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
    
    def submit_query(self, prompt: str, verbose: bool = True) -> Optional[Dict[str, Any]]:
        """Submit a query and wait for response"""
        if not self.session_id:
            print("✗ No active session. Create a session first.")
            return None
        
        self.result = None
        
        @self.sio.on('connect')
        def on_connect():
            if verbose:
                print("✓ Connected to agent\n")
            self.sio.emit('query', {
                'prompt': prompt,
                'session_id': self.session_id
            })
        
        @self.sio.on('agent_event')
        def on_agent_event(data):
            if verbose:
                event_type = data['event_type']
                event_data = data.get('data', {})
                
                if event_type == 'tool_found':
                    print(f"✓ Found tool: {event_data.get('tool_name')}")
                elif event_type == 'synthesis_step':
                    step = event_data.get('step')
                    status = event_data.get('status')
                    if status == 'in_progress':
                        print(f"  ⏳ {step}...")
                    elif status == 'complete':
                        print(f"  ✓ {step} complete")
                elif event_type == 'executing':
                    print(f"▶ Executing: {event_data.get('tool_name')}")
        
        @self.sio.on('query_complete')
        def on_query_complete(data):
            self.result = data
            if verbose:
                print(f"\n{'='*60}")
                print(f"Response: {data['response']}")
                print(f"{'='*60}\n")
            self.sio.disconnect()
        
        @self.sio.on('error')
        def on_error(data):
            print(f"✗ Error: {data['message']}")
            self.sio.disconnect()
        
        try:
            self.sio.connect(self.base_url)
            while self.result is None:
                self.sio.sleep(0.1)
            return self.result
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return None
    
    def get_tools(self):
        """Get list of all available tools"""
        try:
            response = requests.get(f'{self.base_url}/api/tools')
            data = response.json()
            return data.get('tools', []) if data['success'] else []
        except Exception as e:
            print(f"✗ Error fetching tools: {e}")
            return []

def main():
    # Create client
    client = AgentClient()
    
    # Create session
    if not client.create_session():
        return
    
    # Submit a query
    print("Submitting query...\n")
    result = client.submit_query(
        "Calculate profit margins from data/ecommerce_products.csv"
    )
    
    if result and result['success']:
        print(f"Tool used: {result['metadata']['tool_name']}")
        print(f"New tool: {result['metadata']['synthesized']}")
    
    # Get available tools
    print("\nFetching available tools...")
    tools = client.get_tools()
    print(f"Total tools: {len(tools)}")
    for tool in tools[:5]:  # Show first 5
        print(f"  - {tool['name']}")

if __name__ == '__main__':
    main()
```

### Step 2: Run the Client

```bash
python agent_client.py
```

**Expected Output**:

```
✓ Session created: 550e8400-e29b-41d4-a716-446655440000
Submitting query...

✓ Connected to agent

✓ Found tool: calculate_profit_margins
▶ Executing: calculate_profit_margins

============================================================
Response: I've calculated the profit margins for all products...
============================================================

Tool used: calculate_profit_margins
New tool: False

Fetching available tools...
Total tools: 15
  - calculate_profit_margins
  - load_csv_data
  - calculate_statistics
  - generate_report
  - analyze_trends
```

---

## Building a Simple JavaScript Client

Let's build a Node.js client that can interact with the agent.

### Step 1: Create the Client

Create a file named `agent_client.js`:

```javascript
#!/usr/bin/env node
/**
 * Simple Agent Client - Complete example
 */

const io = require('socket.io-client');
const axios = require('axios');

class AgentClient {
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
    
    submitQuery(prompt, verbose = true) {
        return new Promise((resolve, reject) => {
            if (!this.sessionId) {
                reject(new Error('No active session'));
                return;
            }
            
            this.socket = io(this.baseUrl);
            
            this.socket.on('connect', () => {
                if (verbose) {
                    console.log('✓ Connected to agent\n');
                }
                this.socket.emit('query', {
                    prompt: prompt,
                    session_id: this.sessionId
                });
            });
            
            this.socket.on('agent_event', (data) => {
                if (verbose) {
                    const { event_type, data: eventData } = data;
                    
                    if (event_type === 'tool_found') {
                        console.log(`✓ Found tool: ${eventData.tool_name}`);
                    } else if (event_type === 'synthesis_step') {
                        const { step, status } = eventData;
                        if (status === 'in_progress') {
                            console.log(`  ⏳ ${step}...`);
                        } else if (status === 'complete') {
                            console.log(`  ✓ ${step} complete`);
                        }
                    } else if (event_type === 'executing') {
                        console.log(`▶ Executing: ${eventData.tool_name}`);
                    }
                }
            });
            
            this.socket.on('query_complete', (data) => {
                if (verbose) {
                    console.log('\n' + '='.repeat(60));
                    console.log(`Response: ${data.response}`);
                    console.log('='.repeat(60) + '\n');
                }
                this.socket.disconnect();
                resolve(data);
            });
            
            this.socket.on('error', (data) => {
                console.error(`✗ Error: ${data.message}`);
                this.socket.disconnect();
                reject(new Error(data.message));
            });
        });
    }
    
    async getTools() {
        try {
            const response = await axios.get(`${this.baseUrl}/api/tools`);
            return response.data.success ? response.data.tools : [];
        } catch (error) {
            console.error(`✗ Error fetching tools: ${error.message}`);
            return [];
        }
    }
}

async function main() {
    // Create client
    const client = new AgentClient();
    
    // Create session
    if (!await client.createSession()) {
        return;
    }
    
    // Submit a query
    console.log('Submitting query...\n');
    try {
        const result = await client.submitQuery(
            'Calculate profit margins from data/ecommerce_products.csv'
        );
        
        if (result.success) {
            console.log(`Tool used: ${result.metadata.tool_name}`);
            console.log(`New tool: ${result.metadata.synthesized}`);
        }
    } catch (error) {
        console.error(`Query failed: ${error.message}`);
    }
    
    // Get available tools
    console.log('\nFetching available tools...');
    const tools = await client.getTools();
    console.log(`Total tools: ${tools.length}`);
    tools.slice(0, 5).forEach(tool => {
        console.log(`  - ${tool.name}`);
    });
}

if (require.main === module) {
    main();
}

module.exports = AgentClient;
```

### Step 2: Run the Client

```bash
node agent_client.js
```

---

## Building a Web Dashboard

Let's build a simple web dashboard with real-time updates.

### Step 1: Create HTML File

Create `dashboard.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: #4CAF50;
            margin-bottom: 20px;
        }
        
        .status {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #4CAF50;
        }
        
        .input-section {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        input[type="text"] {
            width: 70%;
            padding: 12px;
            background: #1a1a1a;
            border: 1px solid #444;
            color: #e0e0e0;
            border-radius: 4px;
            font-size: 14px;
        }
        
        button {
            padding: 12px 24px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-left: 10px;
        }
        
        button:hover {
            background: #45a049;
        }
        
        button:disabled {
            background: #666;
            cursor: not-allowed;
        }
        
        .events {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            height: 300px;
            overflow-y: auto;
        }
        
        .event {
            padding: 8px;
            margin: 5px 0;
            background: #1a1a1a;
            border-radius: 4px;
            font-size: 13px;
            font-family: 'Courier New', monospace;
        }
        
        .event.info { border-left: 3px solid #2196F3; }
        .event.success { border-left: 3px solid #4CAF50; }
        .event.warning { border-left: 3px solid #FF9800; }
        .event.error { border-left: 3px solid #f44336; }
        
        .response {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .response-content {
            background: #1a1a1a;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
        }
        
        .tools-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .tool-card {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #444;
        }
        
        .tool-name {
            color: #4CAF50;
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .tool-description {
            font-size: 13px;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Agent Dashboard</h1>
        
        <div class="status" id="status">
            Status: <span id="status-text">Disconnected</span> | 
            Session: <span id="session-id">None</span>
        </div>
        
        <div class="input-section">
            <h2>Submit Query</h2>
            <input type="text" id="prompt" placeholder="Enter your query..." />
            <button onclick="submitQuery()" id="submit-btn">Submit</button>
            <button onclick="createSession()">New Session</button>
        </div>
        
        <div>
            <h2>Activity Log</h2>
            <div class="events" id="events"></div>
        </div>
        
        <div class="response" id="response-section" style="display: none;">
            <h2>Response</h2>
            <div class="response-content" id="response"></div>
        </div>
        
        <div>
            <h2>Available Tools (<span id="tool-count">0</span>)</h2>
            <div class="tools-grid" id="tools"></div>
        </div>
    </div>
    
    <script>
        const socket = io('http://localhost:5001');
        let sessionId = null;
        let isProcessing = false;
        
        // Connection handlers
        socket.on('connect', () => {
            updateStatus('Connected', 'success');
            loadTools();
        });
        
        socket.on('disconnect', () => {
            updateStatus('Disconnected', 'error');
        });
        
        // Agent event handler
        socket.on('agent_event', (data) => {
            const { event_type, data: eventData } = data;
            
            if (event_type === 'tool_found') {
                addEvent('success', `Found tool: ${eventData.tool_name}`);
            } else if (event_type === 'synthesis_step') {
                addEvent('info', `Synthesis: ${eventData.step} - ${eventData.status}`);
            } else if (event_type === 'executing') {
                addEvent('info', `Executing: ${eventData.tool_name}`);
            } else if (event_type === 'execution_complete') {
                addEvent('success', `Complete: ${eventData.result}`);
            }
        });
        
        // Query complete handler
        socket.on('query_complete', (data) => {
            isProcessing = false;
            document.getElementById('submit-btn').disabled = false;
            
            if (data.success) {
                document.getElementById('response-section').style.display = 'block';
                document.getElementById('response').textContent = data.response;
                addEvent('success', 'Query completed successfully');
            } else {
                addEvent('error', `Query failed: ${data.response}`);
            }
            
            loadTools();
        });
        
        // Create session
        async function createSession() {
            try {
                const response = await fetch('http://localhost:5001/api/session', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    sessionId = data.session_id;
                    document.getElementById('session-id').textContent = 
                        sessionId.substring(0, 8) + '...';
                    addEvent('success', `Session created: ${sessionId}`);
                }
            } catch (error) {
                addEvent('error', `Failed to create session: ${error.message}`);
            }
        }
        
        // Submit query
        function submitQuery() {
            const prompt = document.getElementById('prompt').value.trim();
            
            if (!prompt) {
                addEvent('warning', 'Please enter a query');
                return;
            }
            
            if (!sessionId) {
                addEvent('warning', 'Please create a session first');
                return;
            }
            
            isProcessing = true;
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('events').innerHTML = '';
            
            socket.emit('query', {
                prompt: prompt,
                session_id: sessionId
            });
            
            addEvent('info', `Query: ${prompt}`);
        }
        
        // Load tools
        async function loadTools() {
            try {
                const response = await fetch('http://localhost:5001/api/tools');
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('tool-count').textContent = data.count;
                    
                    const toolsDiv = document.getElementById('tools');
                    toolsDiv.innerHTML = data.tools.map(tool => `
                        <div class="tool-card">
                            <div class="tool-name">${tool.name}</div>
                            <div class="tool-description">${tool.docstring}</div>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('Failed to load tools:', error);
            }
        }
        
        // Helper functions
        function updateStatus(text, type) {
            const statusText = document.getElementById('status-text');
            statusText.textContent = text;
            statusText.style.color = type === 'success' ? '#4CAF50' : '#f44336';
        }
        
        function addEvent(type, message) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${type}`;
            eventDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            eventsDiv.appendChild(eventDiv);
            eventsDiv.scrollTop = eventsDiv.scrollHeight;
        }
        
        // Initialize
        createSession();
        
        // Enter key handler
        document.getElementById('prompt').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                submitQuery();
            }
        });
    </script>
</body>
</html>
```

### Step 2: Open in Browser

Simply open `dashboard.html` in your web browser. The dashboard will:

1. Automatically create a session
2. Load available tools
3. Allow you to submit queries
4. Display real-time events
5. Show responses

---

## Testing Your Integration

### Test 1: Simple Query

```python
client = AgentClient()
client.create_session()
result = client.submit_query("What is 2 + 2?")
```

### Test 2: Tool Synthesis

```python
result = client.submit_query(
    "Create a function that calculates the factorial of a number"
)
```

### Test 3: Multi-Tool Workflow

```python
result = client.submit_query(
    "Load data from products.csv, calculate statistics, and generate a report"
)
```

### Test 4: Error Handling

```python
# Test with invalid session
client.session_id = "invalid-session-id"
result = client.submit_query("Test query")
# Should handle error gracefully
```

---

## Next Steps

Now that you have a working integration, explore these advanced topics:

### 1. Explore the Full API

- Read the [Integration Guide](./integration-guide.md) for detailed workflows
- Check the [API Reference](./openapi.yaml) for all available endpoints
- Review [WebSocket Events](./websocket-events.md) for complete event documentation

### 2. View Interactive API Documentation

Visit the Swagger UI at:
```
http://localhost:5001/api/docs
```

### 3. Build Advanced Features

- Implement batch processing for multiple queries
- Add caching for frequently used tools
- Build a monitoring dashboard with analytics
- Integrate with your existing applications

### 4. Extend the Framework

- Read the [SDK Documentation](./sdk-documentation.md) to extend the framework
- Create custom planners for domain-specific workflows
- Implement custom tool templates
- Add custom event handlers

### 5. Review Code Examples

Check out comprehensive code examples in:
- [Code Examples](./code-examples.md) - Python and JavaScript examples
- Advanced patterns and best practices
- React integration examples
- Backend integration examples

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to agent server

**Solution**:
```bash
# Check if server is running
curl http://localhost:5001/api/tools

# Check server logs
# Restart server if needed
```

### Session Issues

**Problem**: "No active session" error

**Solution**:
```python
# Always create session before submitting queries
client.create_session()
result = client.submit_query("Your query")
```

### Timeout Issues

**Problem**: Query times out

**Solution**:
```python
# Increase timeout in socket connection
# Or check server logs for errors
```

---

## Summary

You've successfully built a complete integration with the Self-Engineering Agent Framework! You now know how to:

✓ Create sessions for conversational context  
✓ Submit queries via WebSocket  
✓ Handle real-time events  
✓ Display responses  
✓ Retrieve tool information  
✓ Build interactive dashboards  

Continue exploring the documentation to build more advanced integrations!

---

## Additional Resources

- **API Documentation**: http://localhost:5001/api/docs
- **GitHub Repository**: https://github.com/haider-toha/Self-Engineering-Agent-Framework
- **Integration Guide**: [integration-guide.md](./integration-guide.md)
- **Code Examples**: [code-examples.md](./code-examples.md)
- **SDK Documentation**: [sdk-documentation.md](./sdk-documentation.md)
