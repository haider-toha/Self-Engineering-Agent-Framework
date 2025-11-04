# WebSocket/Socket.IO Event Schema

This document describes all WebSocket events emitted by the Self-Engineering Agent Framework via Socket.IO. The framework uses bidirectional real-time communication to provide progress updates, execution status, and workflow information.

## Connection Events

### `connect`
**Direction:** Server → Client  
**Description:** Emitted when a client successfully connects to the Socket.IO server.

**Payload:**
```json
{
  "data": "Connected to agent"
}
```

**Client Handler:**
```javascript
socket.on('connect', () => {
  console.log('Connected to agent');
});
```

---

### `connected`
**Direction:** Server → Client  
**Description:** Confirmation event sent immediately after connection is established.

**Payload:**
```json
{
  "data": "Connected to agent"
}
```

---

### `disconnect`
**Direction:** Server → Client  
**Description:** Emitted when the client disconnects from the server.

**Payload:** None

---

## Session & Tool Management Events

### `tool_count`
**Direction:** Server → Client  
**Description:** Emitted to update the client with the current number of available tools in the registry.

**Payload:**
```json
{
  "count": 42
}
```

**When Emitted:**
- On initial connection
- After query completion
- After tool synthesis

---

### `session_memory`
**Direction:** Server → Client  
**Description:** Sends the recent conversation history for a session to update the UI.

**Payload:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "messages": [
    {
      "role": "user",
      "content": "Calculate profit margins",
      "message_index": 0,
      "created_at": "2025-11-04T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "I've calculated the profit margins...",
      "message_index": 1,
      "created_at": "2025-11-04T10:30:15Z"
    }
  ]
}
```

---

## Query Lifecycle Events

### `query` (Client → Server)
**Direction:** Client → Server  
**Description:** Client sends a user query to be processed by the agent.

**Payload:**
```json
{
  "prompt": "Calculate profit margins from data/ecommerce_products.csv",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Client Usage:**
```javascript
socket.emit('query', {
  prompt: userInput,
  session_id: currentSessionId
});
```

---

### `query_complete`
**Direction:** Server → Client  
**Description:** Emitted when query processing is complete with final results.

**Payload:**
```json
{
  "success": true,
  "response": "The profit margins have been calculated...",
  "metadata": {
    "tool_name": "calculate_profit_margins",
    "synthesized": false,
    "tool_result": "{\"products\": [...]}"
  },
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Fields:**
- `success` (boolean): Whether the query was processed successfully
- `response` (string): Natural language response to the user
- `metadata` (object): Additional information about execution
  - `tool_name` (string): Name of the tool that was executed
  - `synthesized` (boolean): Whether a new tool was created
  - `tool_result` (string): Raw output from tool execution
- `session_id` (string): Session identifier

---

### `error`
**Direction:** Server → Client  
**Description:** Emitted when an error occurs during query processing.

**Payload:**
```json
{
  "message": "No prompt provided"
}
```

---

## Agent Event Stream

All agent lifecycle events are emitted via the `agent_event` event with different `event_type` values.

### `agent_event`
**Direction:** Server → Client  
**Description:** Generic event wrapper for all agent lifecycle events.

**Payload Structure:**
```json
{
  "event_type": "tool_found",
  "data": {
    // Event-specific data
  }
}
```

---

## Tool Discovery Events

### `orphans_cleaned`
**Event Type:** `agent_event`  
**Description:** Emitted when orphaned tools are removed from the database on startup.

**Data:**
```json
{
  "count": 3
}
```

---

### `searching`
**Event Type:** `agent_event`  
**Description:** Emitted when the agent begins searching for an existing tool.

**Data:**
```json
{
  "query": "Calculate profit margins"
}
```

---

### `tool_found`
**Event Type:** `agent_event`  
**Description:** Emitted when a matching tool is found in the registry.

**Data:**
```json
{
  "tool_name": "calculate_profit_margins",
  "similarity": 0.92
}
```

**Fields:**
- `tool_name` (string): Name of the found tool
- `similarity` (float): Cosine similarity score (0.0 to 1.0)

---

### `tool_mismatch`
**Event Type:** `agent_event`  
**Description:** Emitted when a found tool doesn't match the expected signature.

**Data:**
```json
{
  "tool_name": "calculate_margins",
  "error": "Argument mismatch: expected 'file_path', got 'csv_path'"
}
```

---

### `no_tool_found`
**Event Type:** `agent_event`  
**Description:** Emitted when no matching tool is found in the registry.

**Data:**
```json
{
  "query": "Calculate profit margins"
}
```

---

## Tool Synthesis Events

### `entering_synthesis_mode`
**Event Type:** `agent_event`  
**Description:** Emitted when the agent begins synthesizing a new tool.

**Data:**
```json
{
  "reason": "No matching tool found"
}
```

---

### `synthesis_step`
**Event Type:** `agent_event`  
**Description:** Emitted for each step in the 5-stage TDD synthesis pipeline.

**Data:**
```json
{
  "step": "specification",
  "status": "in_progress"
}
```

**Synthesis Steps:**
1. `specification` - Generating function specification
2. `tests` - Generating test suite
3. `implementation` - Implementing function
4. `verification` - Verifying in Docker sandbox
5. `registration` - Registering new tool

**Status Values:**
- `in_progress` - Step is currently executing
- `complete` - Step completed successfully
- `failed` - Step failed with error

---

### `synthesis_successful`
**Event Type:** `agent_event`  
**Description:** Emitted when tool synthesis completes successfully.

**Data:**
```json
{
  "tool_name": "calculate_profit_margins",
  "tests_verified": true
}
```

---

### `tool_experimental_warning`
**Event Type:** `agent_event`  
**Description:** Emitted when a synthesized tool failed verification but was registered anyway.

**Data:**
```json
{
  "tool_name": "calculate_profit_margins",
  "reason": "Tests failed but tool was registered as experimental"
}
```

---

### `synthesis_failed`
**Event Type:** `agent_event`  
**Description:** Emitted when tool synthesis fails completely.

**Data:**
```json
{
  "step": "verification",
  "error": "Docker container timeout"
}
```

---

## Tool Execution Events

### `executing`
**Event Type:** `agent_event`  
**Description:** Emitted when a tool begins execution.

**Data:**
```json
{
  "tool_name": "calculate_profit_margins"
}
```

---

### `execution_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when tool execution completes successfully.

**Data:**
```json
{
  "result": "Calculated margins for 150 products"
}
```

---

### `execution_failed`
**Event Type:** `agent_event`  
**Description:** Emitted when tool execution fails.

**Data:**
```json
{
  "error": "FileNotFoundError: data/products.csv not found"
}
```

---

### `execution_skipped`
**Event Type:** `agent_event`  
**Description:** Emitted when tool execution is skipped.

**Data:**
```json
{
  "reason": "Tool is informational only"
}
```

---

## Planning & Strategy Events

### `planning_query`
**Event Type:** `agent_event`  
**Description:** Emitted when the query planner begins analyzing the user's request.

**Data:**
```json
{
  "query": "Load CSV and calculate statistics"
}
```

---

### `plan_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when the execution strategy has been determined.

**Data:**
```json
{
  "strategy": "sequential",
  "reasoning": "Query requires multiple tools in sequence"
}
```

**Strategy Values:**
- `single` - Single tool execution
- `sequential` - Multiple tools in sequence
- `composition` - Use composite tool
- `workflow_pattern` - Use learned workflow pattern
- `force_synthesis` - Force new tool creation

---

## Workflow & Composition Events

### `using_composite_tool`
**Event Type:** `agent_event`  
**Description:** Emitted when a composite tool is selected for execution.

**Data:**
```json
{
  "tool_name": "data_analysis_pipeline",
  "component_tools": ["load_csv_data", "calculate_statistics", "generate_report"]
}
```

---

### `using_workflow_pattern`
**Event Type:** `agent_event`  
**Description:** Emitted when a learned workflow pattern is selected.

**Data:**
```json
{
  "pattern_name": "csv_analysis_workflow",
  "tool_sequence": ["load_csv_data", "calculate_statistics"]
}
```

---

### `multi_tool_workflow`
**Event Type:** `agent_event`  
**Description:** Emitted when a multi-tool workflow is detected.

**Data:**
```json
{
  "num_tasks": 3
}
```

---

### `workflow_start`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow begins execution.

**Data:**
```json
{
  "total_steps": 3,
  "tasks": [
    "Load CSV data",
    "Calculate statistics",
    "Generate report"
  ]
}
```

---

### `workflow_step`
**Event Type:** `agent_event`  
**Description:** Emitted at the start of each workflow step.

**Data:**
```json
{
  "step": 1,
  "total": 3,
  "task": "Load CSV data"
}
```

---

### `workflow_step_tool_found`
**Event Type:** `agent_event`  
**Description:** Emitted when a tool is found for a workflow step.

**Data:**
```json
{
  "tool_name": "load_csv_data",
  "similarity": 0.89
}
```

---

### `workflow_step_executing`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow step begins execution.

**Data:**
```json
{
  "tool_name": "load_csv_data"
}
```

---

### `workflow_step_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow step completes successfully.

**Data:**
```json
{
  "result": "Loaded 150 rows from CSV"
}
```

---

### `workflow_step_failed`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow step fails.

**Data:**
```json
{
  "error": "File not found"
}
```

---

### `workflow_step_needs_synthesis`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow step requires a new tool to be created.

**Data:**
```json
{
  "step": 2
}
```

---

### `workflow_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when the entire workflow completes.

**Data:**
```json
{
  "total_steps": 3,
  "tool_sequence": ["load_csv_data", "calculate_statistics", "generate_report"]
}
```

---

### `workflow_needs_synthesis`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow requires tool synthesis.

**Data:**
```json
{
  "step_failed": 2
}
```

---

### `workflow_step_synthesizing`
**Event Type:** `agent_event`  
**Description:** Emitted when synthesizing a new tool for a workflow step.

**Data:**
```json
{
  "step": 2,
  "task": "Calculate statistics"
}
```

---

### `workflow_retry`
**Event Type:** `agent_event`  
**Description:** Emitted when retrying a workflow after synthesis.

**Data:**
```json
{
  "reason": "New tool synthesized successfully"
}
```

---

## Pattern Execution Events

### `pattern_execution_start`
**Event Type:** `agent_event`  
**Description:** Emitted when a workflow pattern begins execution.

**Data:**
```json
{
  "pattern_name": "csv_analysis_workflow"
}
```

---

### `pattern_step`
**Event Type:** `agent_event`  
**Description:** Emitted for each step in a pattern execution.

**Data:**
```json
{
  "step": 1,
  "total": 3,
  "tool_name": "load_csv_data"
}
```

---

### `pattern_step_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when a pattern step completes.

**Data:**
```json
{
  "tool_name": "load_csv_data",
  "result": "Loaded 150 rows"
}
```

---

### `pattern_execution_complete`
**Event Type:** `agent_event`  
**Description:** Emitted when pattern execution completes.

**Data:**
```json
{
  "pattern_name": "csv_analysis_workflow"
}
```

---

## Response Generation Events

### `synthesizing_response`
**Event Type:** `agent_event`  
**Description:** Emitted when generating a natural language response.

**Data:**
```json
{
  "tool_result": "{'products': [...]}"
}
```

---

### `complete`
**Event Type:** `agent_event`  
**Description:** Emitted when the entire request processing is complete.

**Data:**
```json
{
  "response": "I've calculated the profit margins for all products..."
}
```

---

## Event Flow Examples

### Simple Tool Execution Flow
```
1. query (client → server)
2. agent_event: searching
3. agent_event: tool_found
4. agent_event: executing
5. agent_event: execution_complete
6. agent_event: synthesizing_response
7. agent_event: complete
8. query_complete
9. session_memory
10. tool_count
```

### Tool Synthesis Flow
```
1. query (client → server)
2. agent_event: searching
3. agent_event: no_tool_found
4. agent_event: entering_synthesis_mode
5. agent_event: synthesis_step (specification, in_progress)
6. agent_event: synthesis_step (specification, complete)
7. agent_event: synthesis_step (tests, in_progress)
8. agent_event: synthesis_step (tests, complete)
9. agent_event: synthesis_step (implementation, in_progress)
10. agent_event: synthesis_step (implementation, complete)
11. agent_event: synthesis_step (verification, in_progress)
12. agent_event: synthesis_step (verification, complete)
13. agent_event: synthesis_step (registration, in_progress)
14. agent_event: synthesis_step (registration, complete)
15. agent_event: synthesis_successful
16. agent_event: executing
17. agent_event: execution_complete
18. agent_event: synthesizing_response
19. agent_event: complete
20. query_complete
21. session_memory
22. tool_count
```

### Multi-Tool Workflow Flow
```
1. query (client → server)
2. agent_event: planning_query
3. agent_event: plan_complete
4. agent_event: multi_tool_workflow
5. agent_event: workflow_start
6. agent_event: workflow_step (1/3)
7. agent_event: workflow_step_tool_found
8. agent_event: workflow_step_executing
9. agent_event: workflow_step_complete
10. agent_event: workflow_step (2/3)
11. agent_event: workflow_step_tool_found
12. agent_event: workflow_step_executing
13. agent_event: workflow_step_complete
14. agent_event: workflow_step (3/3)
15. agent_event: workflow_step_tool_found
16. agent_event: workflow_step_executing
17. agent_event: workflow_step_complete
18. agent_event: workflow_complete
19. agent_event: synthesizing_response
20. agent_event: complete
21. query_complete
22. session_memory
23. tool_count
```

---

## Client Implementation Example

```javascript
// Initialize Socket.IO connection
const socket = io('http://localhost:5001');

// Handle connection
socket.on('connect', () => {
  console.log('Connected to agent');
});

// Handle agent events
socket.on('agent_event', (data) => {
  const { event_type, data: eventData } = data;
  
  switch (event_type) {
    case 'tool_found':
      console.log(`Found tool: ${eventData.tool_name}`);
      break;
    case 'synthesis_step':
      console.log(`Synthesis: ${eventData.step} - ${eventData.status}`);
      break;
    case 'execution_complete':
      console.log(`Result: ${eventData.result}`);
      break;
    // ... handle other events
  }
});

// Handle query completion
socket.on('query_complete', (data) => {
  if (data.success) {
    console.log('Response:', data.response);
  } else {
    console.error('Query failed');
  }
});

// Send a query
socket.emit('query', {
  prompt: 'Calculate profit margins from data/products.csv',
  session_id: 'your-session-id'
});
```

---

## Event Summary Table

| Event Type | Direction | Category | Description |
|------------|-----------|----------|-------------|
| `connect` | S→C | Connection | Client connected |
| `connected` | S→C | Connection | Connection confirmed |
| `disconnect` | S→C | Connection | Client disconnected |
| `query` | C→S | Query | Submit user query |
| `query_complete` | S→C | Query | Query processing complete |
| `error` | S→C | Error | Error occurred |
| `tool_count` | S→C | Tool | Tool count update |
| `session_memory` | S→C | Session | Session history update |
| `orphans_cleaned` | S→C | Tool | Orphaned tools removed |
| `searching` | S→C | Discovery | Searching for tool |
| `tool_found` | S→C | Discovery | Tool found |
| `tool_mismatch` | S→C | Discovery | Tool signature mismatch |
| `no_tool_found` | S→C | Discovery | No tool found |
| `entering_synthesis_mode` | S→C | Synthesis | Starting synthesis |
| `synthesis_step` | S→C | Synthesis | Synthesis pipeline step |
| `synthesis_successful` | S→C | Synthesis | Synthesis succeeded |
| `tool_experimental_warning` | S→C | Synthesis | Tool is experimental |
| `synthesis_failed` | S→C | Synthesis | Synthesis failed |
| `executing` | S→C | Execution | Tool executing |
| `execution_complete` | S→C | Execution | Execution succeeded |
| `execution_failed` | S→C | Execution | Execution failed |
| `execution_skipped` | S→C | Execution | Execution skipped |
| `planning_query` | S→C | Planning | Analyzing query |
| `plan_complete` | S→C | Planning | Strategy determined |
| `using_composite_tool` | S→C | Workflow | Using composite tool |
| `using_workflow_pattern` | S→C | Workflow | Using workflow pattern |
| `multi_tool_workflow` | S→C | Workflow | Multi-tool workflow |
| `workflow_start` | S→C | Workflow | Workflow started |
| `workflow_step` | S→C | Workflow | Workflow step |
| `workflow_step_tool_found` | S→C | Workflow | Tool found for step |
| `workflow_step_executing` | S→C | Workflow | Step executing |
| `workflow_step_complete` | S→C | Workflow | Step complete |
| `workflow_step_failed` | S→C | Workflow | Step failed |
| `workflow_step_needs_synthesis` | S→C | Workflow | Step needs synthesis |
| `workflow_complete` | S→C | Workflow | Workflow complete |
| `workflow_needs_synthesis` | S→C | Workflow | Workflow needs synthesis |
| `workflow_step_synthesizing` | S→C | Workflow | Synthesizing for step |
| `workflow_retry` | S→C | Workflow | Retrying workflow |
| `pattern_execution_start` | S→C | Pattern | Pattern execution start |
| `pattern_step` | S→C | Pattern | Pattern step |
| `pattern_step_complete` | S→C | Pattern | Pattern step complete |
| `pattern_execution_complete` | S→C | Pattern | Pattern complete |
| `synthesizing_response` | S→C | Response | Generating response |
| `complete` | S→C | Response | Request complete |

**Legend:** S→C = Server to Client, C→S = Client to Server
