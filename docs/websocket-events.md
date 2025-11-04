# WebSocket API Documentation

## Overview

The Self-Engineering Agent Framework uses Socket.IO for real-time bidirectional communication between the client and server. This enables live progress updates, event streaming, and interactive agent responses.

## Connection

### Server URL
```
ws://localhost:5001
```

### Client Library
```javascript
// Include Socket.IO client library
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

// Initialize connection
const socket = io();
```

## Connection Events

### `connect`
**Direction:** Server → Client  
**Description:** Emitted when the client successfully connects to the server.

**Payload:**
```javascript
{
  data: "Connected to agent"
}
```

**Client Handler Example:**
```javascript
socket.on('connect', () => {
  console.log('Connected to agent');
  updateStatus('Connected', 'success');
});
```

---

### `disconnect`
**Direction:** Server → Client  
**Description:** Emitted when the client disconnects from the server.

**Client Handler Example:**
```javascript
socket.on('disconnect', () => {
  console.log('Disconnected from agent');
  updateStatus('Disconnected', 'error');
});
```

---

## Client-to-Server Events

### `query`
**Direction:** Client → Server  
**Description:** Submit a user query/prompt to the agent for processing.

**Payload:**
```javascript
{
  prompt: string,      // User's natural language query
  session_id: string   // UUID of the active session
}
```

**Example:**
```javascript
socket.emit('query', {
  prompt: 'Calculate profit margins from data/ecommerce_products.csv',
  session_id: '550e8400-e29b-41d4-a716-446655440000'
});
```

**Response Events:**
- `agent_event` (multiple, for progress updates)
- `query_complete` (final result)
- `session_memory` (updated conversation history)
- `tool_count` (updated tool count)

---

## Server-to-Client Events

### `tool_count`
**Direction:** Server → Client  
**Description:** Provides the current count of available tools in the registry.

**Payload:**
```javascript
{
  count: number  // Total number of synthesized tools
}
```

**Example:**
```javascript
socket.on('tool_count', (data) => {
  console.log(`Available tools: ${data.count}`);
});
```

---

### `agent_event`
**Direction:** Server → Client  
**Description:** Real-time progress updates during query processing. This is the primary event for tracking agent activity.

**Payload:**
```javascript
{
  event_type: string,  // Type of event (see Event Types below)
  data: object         // Event-specific data
}
```

**Example:**
```javascript
socket.on('agent_event', (data) => {
  handleAgentEvent(data.event_type, data.data);
});
```

---

### `query_complete`
**Direction:** Server → Client  
**Description:** Emitted when query processing is complete with final results.

**Payload:**
```javascript
{
  success: boolean,           // Whether the query was successful
  response: string,           // Natural language response
  metadata: {
    tool_name: string,        // Name of the tool used
    synthesized: boolean,     // Whether a new tool was created
    tool_result: string       // Raw tool execution result
  },
  session_id: string          // Session identifier
}
```

**Example:**
```javascript
socket.on('query_complete', (data) => {
  if (data.success) {
    displayResponse(data.response, data.metadata);
  } else {
    displayError(data.response);
  }
});
```

---

### `session_memory`
**Direction:** Server → Client  
**Description:** Provides updated conversation history for the session.

**Payload:**
```javascript
{
  session_id: string,
  messages: [
    {
      role: "user" | "assistant",
      content: string,
      message_index: number,
      created_at: string  // ISO 8601 timestamp
    }
  ]
}
```

**Example:**
```javascript
socket.on('session_memory', (data) => {
  if (data.session_id === currentSessionId) {
    renderConversationHistory(data.messages);
  }
});
```

---

### `error`
**Direction:** Server → Client  
**Description:** Emitted when an error occurs during query processing.

**Payload:**
```javascript
{
  message: string  // Error description
}
```

**Example:**
```javascript
socket.on('error', (data) => {
  console.error(`Error: ${data.message}`);
  updateStatus('Error', 'error');
});
```

---

## Agent Event Types

The `agent_event` socket event includes various `event_type` values that indicate different stages of query processing. Below is a comprehensive list of all event types.

### Tool Discovery Events

#### `orphans_cleaned`
**Description:** Orphaned tools (database entries without corresponding files) were cleaned up.

**Data:**
```javascript
{
  count: number  // Number of orphaned tools removed
}
```

**Example:**
```javascript
{
  event_type: 'orphans_cleaned',
  data: { count: 3 }
}
```

---

#### `searching`
**Description:** Agent is searching for an existing tool that matches the query.

**Data:**
```javascript
{}
```

---

#### `tool_found`
**Description:** A matching tool was found in the registry.

**Data:**
```javascript
{
  tool_name: string,    // Name of the found tool
  similarity: number    // Similarity score (0.0-1.0)
}
```

**Example:**
```javascript
{
  event_type: 'tool_found',
  data: {
    tool_name: 'calculate_profit_margins',
    similarity: 0.87
  }
}
```

---

#### `tool_mismatch`
**Description:** A tool was found but its signature doesn't match the query requirements.

**Data:**
```javascript
{
  tool_name: string,  // Name of the mismatched tool
  error: string       // Reason for mismatch
}
```

---

#### `no_tool_found`
**Description:** No matching tool was found in the registry.

**Data:**
```javascript
{}
```

---

### Tool Synthesis Events

#### `entering_synthesis_mode`
**Description:** Agent is entering synthesis mode to create a new tool.

**Data:**
```javascript
{}
```

---

#### `synthesis_step`
**Description:** Progress update for a specific synthesis pipeline stage.

**Data:**
```javascript
{
  step: "specification" | "tests" | "implementation" | "verification" | "registration",
  status: "in_progress" | "complete" | "failed",
  error?: string  // Present if status is "failed"
}
```

**Example:**
```javascript
{
  event_type: 'synthesis_step',
  data: {
    step: 'implementation',
    status: 'in_progress'
  }
}
```

**Synthesis Steps:**
1. **specification** - Generating function specification from natural language
2. **tests** - Creating pytest test suite with edge cases
3. **implementation** - Implementing the function code
4. **verification** - Executing in Docker sandbox to verify correctness
5. **registration** - Registering the tool in the registry with embeddings

---

#### `synthesis_successful`
**Description:** Tool synthesis completed successfully.

**Data:**
```javascript
{
  tool_name: string  // Name of the newly synthesized tool
}
```

---

#### `tool_experimental_warning`
**Description:** Tool was registered but marked as experimental (tests failed).

**Data:**
```javascript
{
  tool_name: string
}
```

---

#### `synthesis_failed`
**Description:** Tool synthesis failed at a specific step.

**Data:**
```javascript
{
  step: string,  // Step where synthesis failed
  error: string  // Error description
}
```

---

### Tool Execution Events

#### `executing`
**Description:** Agent is executing a tool.

**Data:**
```javascript
{
  tool_name: string  // Name of the tool being executed
}
```

---

#### `execution_complete`
**Description:** Tool execution completed successfully.

**Data:**
```javascript
{
  result: string  // Execution result (may be truncated for display)
}
```

---

#### `execution_failed`
**Description:** Tool execution failed.

**Data:**
```javascript
{
  error: string  // Error description
}
```

---

#### `execution_skipped`
**Description:** Tool execution was skipped.

**Data:**
```javascript
{
  reason: string  // Reason for skipping
}
```

---

### Response Generation Events

#### `synthesizing_response`
**Description:** Agent is generating a natural language response.

**Data:**
```javascript
{}
```

---

#### `complete`
**Description:** Request processing is complete.

**Data:**
```javascript
{}
```

---

### Planning and Strategy Events

#### `planning_query`
**Description:** Agent is analyzing query complexity and planning execution strategy.

**Data:**
```javascript
{}
```

---

#### `plan_complete`
**Description:** Execution strategy has been selected.

**Data:**
```javascript
{
  strategy: "single" | "sequential" | "composition" | "workflow_pattern" | "composite_tool" | "force_synthesis",
  reasoning: string  // Explanation of strategy choice
}
```

**Example:**
```javascript
{
  event_type: 'plan_complete',
  data: {
    strategy: 'workflow_pattern',
    reasoning: 'Found matching workflow pattern with 0.85 confidence'
  }
}
```

---

### Composite Tool Events

#### `using_composite_tool`
**Description:** Agent is using a composite tool (promoted workflow pattern).

**Data:**
```javascript
{
  tool_name: string,           // Name of the composite tool
  component_tools: string[]    // Array of component tool names
}
```

**Example:**
```javascript
{
  event_type: 'using_composite_tool',
  data: {
    tool_name: 'data_analysis_pipeline',
    component_tools: ['load_csv_data', 'calculate_profit_margins', 'generate_report']
  }
}
```

---

### Workflow Pattern Events

#### `using_workflow_pattern`
**Description:** Agent is using a learned workflow pattern.

**Data:**
```javascript
{
  pattern_name: string,      // Name of the pattern
  tool_sequence: string[]    // Ordered sequence of tools
}
```

---

#### `multi_tool_workflow`
**Description:** Multi-tool workflow detected from query analysis.

**Data:**
```javascript
{
  num_tasks: number  // Number of steps in the workflow
}
```

---

#### `workflow_start`
**Description:** Starting execution of a multi-tool workflow.

**Data:**
```javascript
{
  total_steps: number,  // Total number of steps
  tasks: string[]       // Array of task descriptions
}
```

**Example:**
```javascript
{
  event_type: 'workflow_start',
  data: {
    total_steps: 3,
    tasks: [
      'Load CSV data from file',
      'Calculate profit margins',
      'Generate summary report'
    ]
  }
}
```

---

#### `workflow_step`
**Description:** Starting a specific workflow step.

**Data:**
```javascript
{
  step: number,       // Current step number (1-indexed)
  total: number,      // Total number of steps
  task: string        // Task description
}
```

---

#### `workflow_step_tool_found`
**Description:** Found a tool for the current workflow step.

**Data:**
```javascript
{
  tool_name: string,
  similarity: number  // Similarity score (0.0-1.0)
}
```

---

#### `workflow_step_executing`
**Description:** Executing tool for the current workflow step.

**Data:**
```javascript
{
  tool_name: string
}
```

---

#### `workflow_step_complete`
**Description:** Workflow step completed successfully.

**Data:**
```javascript
{
  result: string  // Step result (may be truncated)
}
```

---

#### `workflow_step_failed`
**Description:** Workflow step failed.

**Data:**
```javascript
{
  error: string  // Error description
}
```

---

#### `workflow_step_needs_synthesis`
**Description:** Current workflow step requires synthesizing a new tool.

**Data:**
```javascript
{
  step: number  // Step number that needs synthesis
}
```

---

#### `workflow_step_synthesizing`
**Description:** Creating a new tool for the current workflow step.

**Data:**
```javascript
{
  step: number,  // Step number
  task: string   // Task description
}
```

---

#### `workflow_complete`
**Description:** Entire workflow completed successfully.

**Data:**
```javascript
{
  total_steps: number,      // Total steps executed
  tool_sequence: string[]   // Sequence of tools used
}
```

**Example:**
```javascript
{
  event_type: 'workflow_complete',
  data: {
    total_steps: 3,
    tool_sequence: ['load_csv_data', 'calculate_profit_margins', 'generate_report']
  }
}
```

---

#### `workflow_needs_synthesis`
**Description:** Workflow requires synthesizing a new tool at a specific step.

**Data:**
```javascript
{
  step_failed: number  // Step number where synthesis is needed
}
```

---

#### `workflow_retry`
**Description:** Retrying workflow execution.

**Data:**
```javascript
{
  reason: string  // Reason for retry
}
```

---

### Pattern Execution Events

#### `pattern_execution_start`
**Description:** Starting execution of a workflow pattern.

**Data:**
```javascript
{
  pattern_name: string
}
```

---

#### `pattern_step`
**Description:** Executing a specific step in the pattern.

**Data:**
```javascript
{
  step: number,       // Current step (1-indexed)
  total: number,      // Total steps
  tool_name: string   // Tool being executed
}
```

---

#### `pattern_step_complete`
**Description:** Pattern step completed successfully.

**Data:**
```javascript
{
  tool_name: string,
  result: string
}
```

---

#### `pattern_execution_complete`
**Description:** Pattern execution completed successfully.

**Data:**
```javascript
{
  pattern_name: string
}
```

---

## Complete Event Flow Example

Here's a typical event flow for a query that requires tool synthesis:

```javascript
// 1. Client submits query
socket.emit('query', {
  prompt: 'Calculate average sales from sales_data.csv',
  session_id: 'session-123'
});

// 2. Server emits progress events
socket.on('agent_event', (data) => {
  // Event: searching
  // Event: no_tool_found
  // Event: entering_synthesis_mode
  // Event: synthesis_step (specification, in_progress)
  // Event: synthesis_step (specification, complete)
  // Event: synthesis_step (tests, in_progress)
  // Event: synthesis_step (tests, complete)
  // Event: synthesis_step (implementation, in_progress)
  // Event: synthesis_step (implementation, complete)
  // Event: synthesis_step (verification, in_progress)
  // Event: synthesis_step (verification, complete)
  // Event: synthesis_step (registration, in_progress)
  // Event: synthesis_step (registration, complete)
  // Event: synthesis_successful
  // Event: executing
  // Event: execution_complete
  // Event: synthesizing_response
  // Event: complete
});

// 3. Server emits final result
socket.on('query_complete', (data) => {
  console.log('Success:', data.success);
  console.log('Response:', data.response);
  console.log('Tool used:', data.metadata.tool_name);
  console.log('Was synthesized:', data.metadata.synthesized);
});

// 4. Server emits updated session memory
socket.on('session_memory', (data) => {
  console.log('Messages:', data.messages);
});

// 5. Server emits updated tool count
socket.on('tool_count', (data) => {
  console.log('Total tools:', data.count);
});
```

## Error Handling

Always implement error handlers for robust client applications:

```javascript
socket.on('error', (data) => {
  console.error('Socket error:', data.message);
  // Handle error appropriately
});

socket.on('connect_error', (error) => {
  console.error('Connection error:', error);
  // Attempt reconnection or notify user
});

socket.on('disconnect', (reason) => {
  console.log('Disconnected:', reason);
  if (reason === 'io server disconnect') {
    // Server disconnected, manual reconnection needed
    socket.connect();
  }
  // Otherwise, Socket.IO will automatically attempt to reconnect
});
```

## Best Practices

1. **Session Management**: Always create a session before submitting queries
2. **Event Buffering**: Buffer agent_event updates to avoid UI flooding
3. **Reconnection**: Implement automatic reconnection logic with exponential backoff
4. **State Synchronization**: Re-fetch session state after reconnection
5. **Progress Indication**: Use agent_event updates to show detailed progress to users
6. **Error Recovery**: Implement graceful error handling and user feedback
7. **Memory Management**: Clean up event listeners when components unmount

## Client Implementation Example

```javascript
class AgentClient {
  constructor(serverUrl = 'http://localhost:5001') {
    this.socket = io(serverUrl);
    this.sessionId = null;
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    this.socket.on('connect', () => {
      console.log('Connected to agent');
      this.createSession();
    });

    this.socket.on('agent_event', (data) => {
      this.handleAgentEvent(data.event_type, data.data);
    });

    this.socket.on('query_complete', (data) => {
      this.handleQueryComplete(data);
    });

    this.socket.on('error', (data) => {
      console.error('Error:', data.message);
    });
  }

  async createSession() {
    const response = await fetch('http://localhost:5001/api/session', {
      method: 'POST'
    });
    const data = await response.json();
    this.sessionId = data.session_id;
    console.log('Session created:', this.sessionId);
  }

  submitQuery(prompt) {
    if (!this.sessionId) {
      throw new Error('No active session');
    }
    this.socket.emit('query', {
      prompt: prompt,
      session_id: this.sessionId
    });
  }

  handleAgentEvent(eventType, data) {
    console.log(`[${eventType}]`, data);
    // Implement custom handling based on event type
  }

  handleQueryComplete(data) {
    console.log('Query complete:', data);
    // Process final result
  }
}

// Usage
const client = new AgentClient();
client.submitQuery('Calculate profit margins from data.csv');
```

## Summary

The WebSocket API provides 30+ distinct event types organized into categories:

- **Connection Events** (2): connect, disconnect
- **Client-to-Server Events** (1): query
- **Server-to-Client Events** (5): tool_count, agent_event, query_complete, session_memory, error
- **Agent Event Types** (30+):
  - Tool Discovery (5): orphans_cleaned, searching, tool_found, tool_mismatch, no_tool_found
  - Tool Synthesis (5): entering_synthesis_mode, synthesis_step, synthesis_successful, tool_experimental_warning, synthesis_failed
  - Tool Execution (4): executing, execution_complete, execution_failed, execution_skipped
  - Response Generation (2): synthesizing_response, complete
  - Planning (2): planning_query, plan_complete
  - Composite Tools (1): using_composite_tool
  - Workflow Patterns (13): using_workflow_pattern, multi_tool_workflow, workflow_start, workflow_step, workflow_step_tool_found, workflow_step_executing, workflow_step_complete, workflow_step_failed, workflow_step_needs_synthesis, workflow_step_synthesizing, workflow_complete, workflow_needs_synthesis, workflow_retry
  - Pattern Execution (4): pattern_execution_start, pattern_step, pattern_step_complete, pattern_execution_complete

This comprehensive event system enables rich, real-time user experiences with detailed progress tracking and feedback.
