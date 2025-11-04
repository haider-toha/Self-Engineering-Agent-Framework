# Socket.IO Events Documentation

This document describes all Socket.IO events used for real-time communication between the client and the Self-Engineering Agent Framework server.

## Connection Events

### `connect`
**Direction:** Client → Server

Emitted automatically when a client establishes a WebSocket connection.

**Server Response:**
- Emits `connected` event with connection confirmation
- Emits `tool_count` event with current number of available tools

---

### `connected`
**Direction:** Server → Client

Sent immediately after a client connects successfully.

**Payload:**
```json
{
  "data": "Connected to agent"
}
```

---

### `disconnect`
**Direction:** Client → Server

Emitted automatically when a client disconnects from the WebSocket.

**Server Action:** Logs disconnection event

---

## Query Processing Events

### `query`
**Direction:** Client → Server

Submit a user query for processing by the agent.

**Payload:**
```json
{
  "prompt": "Calculate profit margins from data/ecommerce_products.csv",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Required Fields:**
- `prompt` (string): The user's natural language request
- `session_id` (string): Valid session identifier from `/api/session` endpoint

**Server Response:** Triggers a series of `agent_event` emissions followed by `query_complete`

---

### `query_complete`
**Direction:** Server → Client

Emitted when query processing is complete.

**Payload:**
```json
{
  "success": true,
  "response": "Profit margins calculated successfully. Average margin: 42.5%",
  "metadata": {
    "tool_name": "calculate_profit_margins",
    "synthesized": false,
    "tool_result": "{'avg_margin': 42.5, 'total_products': 150}"
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Fields:**
- `success` (boolean): Whether the query was processed successfully
- `response` (string): Natural language response or error message
- `metadata` (object): Additional execution metadata
  - `tool_name` (string): Name of the tool that was executed
  - `synthesized` (boolean): Whether a new tool was created
  - `tool_result` (string): Raw tool execution result
- `session_id` (string): Session identifier

---

## Agent Lifecycle Events

### `agent_event`
**Direction:** Server → Client

Real-time progress updates during query processing. Emitted multiple times throughout the execution lifecycle.

**Payload:**
```json
{
  "event_type": "searching",
  "data": {
    "query": "Calculate profit margins"
  }
}
```

**Event Types and Payloads:**

#### Planning Phase

**`planning_query`**
```json
{
  "event_type": "planning_query",
  "data": {
    "query": "Calculate profit margins from CSV"
  }
}
```

**`plan_complete`**
```json
{
  "event_type": "plan_complete",
  "data": {
    "strategy": "single",
    "reasoning": "Query matches existing tool capability"
  }
}
```

Possible strategies: `single`, `multi_tool_composition`, `multi_tool_sequential`, `composite_tool`, `workflow_pattern`, `force_synthesis`

#### Tool Search Phase

**`searching`**
```json
{
  "event_type": "searching",
  "data": {
    "query": "Calculate profit margins"
  }
}
```

**`tool_found`**
```json
{
  "event_type": "tool_found",
  "data": {
    "tool_name": "calculate_profit_margins",
    "similarity": 0.92
  }
}
```

**`no_tool_found`**
```json
{
  "event_type": "no_tool_found",
  "data": {
    "query": "Calculate profit margins"
  }
}
```

**`cache_hit`**
```json
{
  "event_type": "cache_hit",
  "data": {
    "tool": "calculate_profit_margins"
  }
}
```

#### Synthesis Phase

**`entering_synthesis_mode`**
```json
{
  "event_type": "entering_synthesis_mode",
  "data": {}
}
```

**`synthesis_step`**
```json
{
  "event_type": "synthesis_step",
  "data": {
    "step": "specification",
    "status": "in_progress"
  }
}
```

Synthesis steps: `specification`, `tests`, `implementation`, `verification`, `registration`

Status values: `in_progress`, `complete`, `failed`, `warning`

**`synthesis_successful`**
```json
{
  "event_type": "synthesis_successful",
  "data": {
    "tool_name": "calculate_profit_margins",
    "experimental": false
  }
}
```

**`synthesis_failed`**
```json
{
  "event_type": "synthesis_failed",
  "data": {
    "error": "Failed to generate implementation",
    "step": "implementation"
  }
}
```

**`tool_experimental_warning`**
```json
{
  "event_type": "tool_experimental_warning",
  "data": {
    "message": "Note: 'calculate_profit_margins' was registered as experimental (tests failed during verification)"
  }
}
```

#### Execution Phase

**`executing`**
```json
{
  "event_type": "executing",
  "data": {
    "tool_name": "calculate_profit_margins"
  }
}
```

**`execution_complete`**
```json
{
  "event_type": "execution_complete",
  "data": {
    "tool_name": "calculate_profit_margins",
    "result": "Average margin: 42.5%"
  }
}
```

**`execution_failed`**
```json
{
  "event_type": "execution_failed",
  "data": {
    "error": "FileNotFoundError: data/ecommerce_products.csv not found",
    "tool": "calculate_profit_margins"
  }
}
```

**`execution_skipped`**
```json
{
  "event_type": "execution_skipped",
  "data": {
    "reason": "Tool created successfully but requires explicit arguments for execution"
  }
}
```

#### Workflow Phase

**`workflow_start`**
```json
{
  "event_type": "workflow_start",
  "data": {
    "sub_tasks": ["load_data", "calculate_metrics", "generate_report"],
    "total_steps": 3
  }
}
```

**`workflow_step`**
```json
{
  "event_type": "workflow_step",
  "data": {
    "step": 1,
    "total": 3,
    "task": "load_data",
    "status": "executing"
  }
}
```

**`workflow_complete`**
```json
{
  "event_type": "workflow_complete",
  "data": {
    "total_steps": 3,
    "successful_steps": 3
  }
}
```

#### Reflection and Learning Phase

**`reflection_created`**
```json
{
  "event_type": "reflection_created",
  "data": {
    "reflection_id": "refl_123456",
    "root_cause": "Missing required dependency: pandas"
  }
}
```

**`composite_created`**
```json
{
  "event_type": "composite_created",
  "data": {
    "composite_name": "analyze_sales_data",
    "component_tools": ["load_csv", "calculate_metrics", "generate_chart"]
  }
}
```

#### Response Synthesis Phase

**`synthesizing_response`**
```json
{
  "event_type": "synthesizing_response",
  "data": {}
}
```

**`complete`**
```json
{
  "event_type": "complete",
  "data": {
    "response": "Analysis complete. Found 150 products with average margin of 42.5%"
  }
}
```

#### Error Events

**`error`**
```json
{
  "event_type": "error",
  "data": {
    "error": "An unexpected error occurred: Connection timeout"
  }
}
```

**`tool_mismatch`**
```json
{
  "event_type": "tool_mismatch",
  "data": {
    "tool_name": "calculate_profit_margins",
    "error": "Tool found, but arguments in your prompt do not match its requirements. Attempting to synthesize a new tool."
  }
}
```

#### Maintenance Events

**`orphans_cleaned`**
```json
{
  "event_type": "orphans_cleaned",
  "data": {
    "count": 3
  }
}
```

---

## Status Events

### `tool_count`
**Direction:** Server → Client

Emitted when the number of available tools changes.

**Payload:**
```json
{
  "count": 42
}
```

**Triggered by:**
- Client connection
- Successful tool synthesis
- Tool deletion

---

### `session_memory`
**Direction:** Server → Client

Emitted after query completion with updated conversation history.

**Payload:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "Calculate profit margins",
      "created_at": "2025-11-04T19:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Average margin: 42.5%",
      "created_at": "2025-11-04T19:30:05Z"
    }
  ]
}
```

---

## Error Handling

### `error`
**Direction:** Server → Client

Emitted when an error occurs during query processing.

**Payload:**
```json
{
  "message": "No prompt provided"
}
```

**Common Error Messages:**
- `"No prompt provided"` - Query submitted without prompt field
- `"Please start a new session before sending prompts."` - Query submitted without valid session_id
- `"Orchestrator not initialized"` - Server initialization failure

---

## Example Client Implementation

### JavaScript (Socket.IO Client)

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:5001');

// Connection handlers
socket.on('connect', () => {
  console.log('Connected to agent');
});

socket.on('connected', (data) => {
  console.log('Server confirmed:', data.data);
});

socket.on('tool_count', (data) => {
  console.log(`Available tools: ${data.count}`);
});

// Submit a query
function submitQuery(prompt, sessionId) {
  socket.emit('query', {
    prompt: prompt,
    session_id: sessionId
  });
}

// Handle agent events
socket.on('agent_event', (event) => {
  console.log(`[${event.event_type}]`, event.data);
  
  switch(event.event_type) {
    case 'searching':
      console.log('Searching for existing tool...');
      break;
    case 'tool_found':
      console.log(`Found tool: ${event.data.tool_name}`);
      break;
    case 'synthesis_step':
      console.log(`Synthesis: ${event.data.step} - ${event.data.status}`);
      break;
    case 'executing':
      console.log(`Executing: ${event.data.tool_name}`);
      break;
  }
});

// Handle query completion
socket.on('query_complete', (result) => {
  if (result.success) {
    console.log('Success:', result.response);
    console.log('Tool used:', result.metadata.tool_name);
  } else {
    console.error('Error:', result.response);
  }
});

// Handle errors
socket.on('error', (error) => {
  console.error('Error:', error.message);
});

// Example usage
submitQuery('Calculate profit margins from data/ecommerce_products.csv', 'my-session-id');
```

### Python (python-socketio)

```python
import socketio

sio = socketio.Client()

@sio.on('connect')
def on_connect():
    print('Connected to agent')

@sio.on('connected')
def on_connected(data):
    print(f"Server confirmed: {data['data']}")

@sio.on('tool_count')
def on_tool_count(data):
    print(f"Available tools: {data['count']}")

@sio.on('agent_event')
def on_agent_event(event):
    event_type = event['event_type']
    data = event['data']
    print(f"[{event_type}]", data)

@sio.on('query_complete')
def on_query_complete(result):
    if result['success']:
        print(f"Success: {result['response']}")
        print(f"Tool used: {result['metadata']['tool_name']}")
    else:
        print(f"Error: {result['response']}")

@sio.on('error')
def on_error(error):
    print(f"Error: {error['message']}")

# Connect and submit query
sio.connect('http://localhost:5001')
sio.emit('query', {
    'prompt': 'Calculate profit margins from data/ecommerce_products.csv',
    'session_id': 'my-session-id'
})
sio.wait()
```

---

## Event Flow Diagrams

### Successful Tool Execution (Existing Tool)
```
Client                          Server
  |                               |
  |------- query ---------------->|
  |                               |
  |<----- agent_event ------------|  (planning_query)
  |<----- agent_event ------------|  (plan_complete)
  |<----- agent_event ------------|  (searching)
  |<----- agent_event ------------|  (tool_found)
  |<----- agent_event ------------|  (executing)
  |<----- agent_event ------------|  (execution_complete)
  |<----- agent_event ------------|  (complete)
  |                               |
  |<----- query_complete ---------|
  |<----- session_memory ---------|
  |<----- tool_count -------------|
  |                               |
```

### Tool Synthesis Flow
```
Client                          Server
  |                               |
  |------- query ---------------->|
  |                               |
  |<----- agent_event ------------|  (planning_query)
  |<----- agent_event ------------|  (plan_complete)
  |<----- agent_event ------------|  (searching)
  |<----- agent_event ------------|  (no_tool_found)
  |<----- agent_event ------------|  (entering_synthesis_mode)
  |<----- agent_event ------------|  (synthesis_step: specification)
  |<----- agent_event ------------|  (synthesis_step: tests)
  |<----- agent_event ------------|  (synthesis_step: implementation)
  |<----- agent_event ------------|  (synthesis_step: verification)
  |<----- agent_event ------------|  (synthesis_step: registration)
  |<----- agent_event ------------|  (synthesis_successful)
  |<----- agent_event ------------|  (executing)
  |<----- agent_event ------------|  (execution_complete)
  |<----- agent_event ------------|  (complete)
  |                               |
  |<----- query_complete ---------|
  |<----- session_memory ---------|
  |<----- tool_count -------------|
  |                               |
```

### Multi-Tool Workflow
```
Client                          Server
  |                               |
  |------- query ---------------->|
  |                               |
  |<----- agent_event ------------|  (planning_query)
  |<----- agent_event ------------|  (plan_complete: multi_tool_sequential)
  |<----- agent_event ------------|  (workflow_start)
  |<----- agent_event ------------|  (workflow_step: 1/3)
  |<----- agent_event ------------|  (executing: tool_1)
  |<----- agent_event ------------|  (execution_complete)
  |<----- agent_event ------------|  (workflow_step: 2/3)
  |<----- agent_event ------------|  (executing: tool_2)
  |<----- agent_event ------------|  (execution_complete)
  |<----- agent_event ------------|  (workflow_step: 3/3)
  |<----- agent_event ------------|  (executing: tool_3)
  |<----- agent_event ------------|  (execution_complete)
  |<----- agent_event ------------|  (workflow_complete)
  |<----- agent_event ------------|  (complete)
  |                               |
  |<----- query_complete ---------|
  |<----- session_memory ---------|
  |<----- tool_count -------------|
  |                               |
```
