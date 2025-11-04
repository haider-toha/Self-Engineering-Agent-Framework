# Python API Reference

## Overview

This document provides comprehensive API reference documentation for the 8 core modules of the Self-Engineering Agent Framework. These modules work together to provide autonomous tool synthesis, semantic search, workflow execution, and self-improvement capabilities.

## Core Modules

1. [AgentOrchestrator](#agentorchestrator) - Central coordinator for request processing
2. [CapabilitySynthesisEngine](#capabilitysynthesisengine) - TDD-based tool synthesis
3. [CapabilityRegistry](#capabilityregistry) - Tool storage and semantic search
4. [QueryPlanner](#queryplanner) - Intent analysis and strategy selection
5. [CompositionPlanner](#compositionplanner) - Multi-tool workflow execution
6. [LLMClient](#llmclient) - OpenAI API wrapper
7. [WorkflowTracker](#workflowtracker) - Execution logging and pattern mining
8. [SessionMemoryManager](#sessionmemorymanager) - Conversational context management

---

## AgentOrchestrator

**Module:** `src.orchestrator`  
**Class:** `AgentOrchestrator`

### Description

The central coordinator that manages the entire request lifecycle. It initializes all subsystems, routes requests to appropriate execution strategies, and manages caching, reflection, and error handling.

### Constructor

```python
def __init__(self)
```

Initializes the orchestrator with all required subsystems:
- `CapabilityRegistry` for tool management
- `CapabilitySynthesisEngine` for tool creation
- `ToolExecutor` for tool execution
- `LLMClient` for LLM interactions
- `WorkflowTracker` for execution logging
- `SessionMemoryManager` for conversational memory
- `QueryPlanner` for strategy selection
- `CompositionPlanner` for multi-tool workflows

**Raises:**
- `Exception` if initialization fails (e.g., missing environment variables)

### Methods

#### `process_request(user_prompt: str, session_id: str = None, callback: Callable = None) -> Dict`

Process a user request through the complete agent pipeline.

**Parameters:**
- `user_prompt` (str): Natural language query from the user
- `session_id` (str, optional): UUID of the active session for memory context
- `callback` (Callable, optional): Function to call for progress events. Signature: `callback(event_type: str, event_data: dict)`

**Returns:**
- `dict`: Response dictionary with keys:
  - `success` (bool): Whether the request succeeded
  - `response` (str): Natural language response
  - `tool_name` (str): Name of the tool used
  - `tool_result` (Any): Raw tool execution result
  - `synthesized` (bool): Whether a new tool was created
  - `session_id` (str): Session identifier

**Example:**
```python
orchestrator = AgentOrchestrator()

def progress_callback(event_type, data):
    print(f"[{event_type}] {data}")

result = orchestrator.process_request(
    user_prompt="Calculate profit margins from data.csv",
    session_id="session-123",
    callback=progress_callback
)

if result['success']:
    print(f"Response: {result['response']}")
    print(f"Tool used: {result['tool_name']}")
```

**Execution Flow:**
1. Clean up orphaned tools
2. Plan execution strategy via `QueryPlanner`
3. Execute based on strategy:
   - Single tool execution
   - Composite tool execution
   - Workflow pattern execution
   - Multi-tool workflow
   - Force synthesis
4. Log execution to `WorkflowTracker`
5. Save to `SessionMemoryManager`
6. Return response

---

#### `get_all_tools() -> List[Dict]`

Retrieve all available tools from the registry.

**Returns:**
- `list`: List of tool dictionaries with keys:
  - `name` (str): Tool name
  - `docstring` (str): Tool documentation
  - `file_path` (str): Path to source file
  - `test_path` (str): Path to test file
  - `timestamp` (str): Creation timestamp

**Example:**
```python
tools = orchestrator.get_all_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['docstring']}")
```

---

#### `get_tool_count() -> int`

Get the total number of available tools.

**Returns:**
- `int`: Number of tools in the registry

**Example:**
```python
count = orchestrator.get_tool_count()
print(f"Available tools: {count}")
```

---

## CapabilitySynthesisEngine

**Module:** `src.synthesis_engine`  
**Class:** `CapabilitySynthesisEngine`

### Description

Implements a 5-stage Test-Driven Development (TDD) pipeline for synthesizing new tools from natural language descriptions.

### Constructor

```python
def __init__(self, llm_client: LLMClient, registry: CapabilityRegistry)
```

**Parameters:**
- `llm_client` (LLMClient): Client for LLM interactions
- `registry` (CapabilityRegistry): Registry for storing synthesized tools

### Methods

#### `synthesize_capability(user_prompt: str, callback: Callable = None) -> Dict`

Synthesize a new tool using the TDD pipeline.

**Parameters:**
- `user_prompt` (str): Natural language description of desired capability
- `callback` (Callable, optional): Progress callback function

**Returns:**
- `dict`: Synthesis result with keys:
  - `success` (bool): Whether synthesis succeeded
  - `tool_name` (str): Name of the synthesized tool
  - `tool_code` (str): Generated source code
  - `tests_verified` (bool): Whether tests passed
  - `error` (str, optional): Error message if failed

**Pipeline Stages:**

1. **Specification Generation**
   - Generates function signature and specification
   - Includes parameter types, return type, and description
   - Emits: `synthesis_step(step='specification', status='in_progress')`

2. **Test Generation**
   - Creates pytest test suite with edge cases
   - Validates test syntax and structure
   - Emits: `synthesis_step(step='tests', status='in_progress')`

3. **Implementation Generation**
   - Generates function code to pass tests
   - Follows specification and test requirements
   - Emits: `synthesis_step(step='implementation', status='in_progress')`

4. **Verification**
   - Executes tests in Docker sandbox
   - Validates correctness and safety
   - Emits: `synthesis_step(step='verification', status='in_progress')`

5. **Registration**
   - Stores tool in registry with embeddings
   - Indexes for semantic search
   - Emits: `synthesis_step(step='registration', status='in_progress')`

**Example:**
```python
engine = CapabilitySynthesisEngine(llm_client, registry)

def callback(event_type, data):
    if event_type == 'synthesis_step':
        print(f"Stage: {data['step']} - Status: {data['status']}")

result = engine.synthesize_capability(
    user_prompt="Create a function to calculate moving averages",
    callback=callback
)

if result['success']:
    print(f"Synthesized: {result['tool_name']}")
    print(f"Tests passed: {result['tests_verified']}")
```

**Error Handling:**
- Automatic test validation and fixing
- Aggressive error-based fixes on verification failure
- Fallback to "experimental" registration if tests fail
- Data file detection and loading for file-based tools

---

## CapabilityRegistry

**Module:** `src.capability_registry`  
**Class:** `CapabilityRegistry`

### Description

Manages tool storage, indexing, and semantic search using vector embeddings. Implements dual storage: metadata in Supabase, code on filesystem.

### Constructor

```python
def __init__(self, llm_client: LLMClient)
```

**Parameters:**
- `llm_client` (LLMClient): Client for generating embeddings

### Methods

#### `add_tool(name: str, code: str, tests: str, docstring: str, tests_verified: bool = True) -> bool`

Register a new tool in the registry.

**Parameters:**
- `name` (str): Unique tool name (snake_case)
- `code` (str): Python source code
- `tests` (str): Pytest test suite code
- `docstring` (str): Tool documentation
- `tests_verified` (bool): Whether tests passed verification

**Returns:**
- `bool`: True if registration succeeded

**Example:**
```python
registry = CapabilityRegistry(llm_client)

success = registry.add_tool(
    name="calculate_average",
    code="def calculate_average(numbers):\n    return sum(numbers) / len(numbers)",
    tests="def test_calculate_average():\n    assert calculate_average([1,2,3]) == 2.0",
    docstring="Calculate the arithmetic mean of a list of numbers",
    tests_verified=True
)
```

**Storage:**
- Metadata stored in Supabase `agent_tools` table
- Code written to `{TOOLS_DIR}/{name}.py`
- Tests written to `{TOOLS_DIR}/test_{name}.py`
- 1536-dim embedding generated and indexed

---

#### `search_tool(query: str, threshold: float = 0.4, rerank: bool = False) -> Optional[Dict]`

Search for a tool using semantic similarity.

**Parameters:**
- `query` (str): Natural language search query
- `threshold` (float): Minimum similarity score (0.0-1.0)
- `rerank` (bool): Whether to apply composite scoring

**Returns:**
- `dict` or `None`: Tool information if found, None otherwise
  - `name` (str): Tool name
  - `code` (str): Source code
  - `docstring` (str): Documentation
  - `similarity` (float): Similarity score
  - `file_path` (str): Path to source file
  - `test_path` (str): Path to test file

**Reranking Formula:**
```
composite_score = (0.7 * semantic_similarity) + (0.2 * success_rate) + (0.1 * usage_frequency)
```

**Example:**
```python
# Basic search
tool = registry.search_tool(
    query="calculate profit margins from CSV",
    threshold=0.6
)

if tool:
    print(f"Found: {tool['name']} (similarity: {tool['similarity']:.2f})")
    
# Search with reranking
tool = registry.search_tool(
    query="analyze sales data",
    threshold=0.5,
    rerank=True
)
```

---

#### `get_tool_by_name(name: str) -> Optional[Dict]`

Retrieve a tool by its exact name.

**Parameters:**
- `name` (str): Tool name

**Returns:**
- `dict` or `None`: Tool information if found

**Example:**
```python
tool = registry.get_tool_by_name("calculate_profit_margins")
if tool:
    print(tool['code'])
```

---

#### `cleanup_orphaned_tools() -> int`

Remove database entries for tools without corresponding files.

**Returns:**
- `int`: Number of orphaned tools removed

**Example:**
```python
removed = registry.cleanup_orphaned_tools()
print(f"Cleaned up {removed} orphaned tools")
```

---

## QueryPlanner

**Module:** `src.query_planner`  
**Class:** `QueryPlanner`

### Description

Analyzes user intent and determines the optimal execution strategy. Implements a cascading decision tree for strategy selection.

### Constructor

```python
def __init__(self, registry: CapabilityRegistry, workflow_tracker: WorkflowTracker, llm_client: LLMClient)
```

**Parameters:**
- `registry` (CapabilityRegistry): Tool registry for searching
- `workflow_tracker` (WorkflowTracker): Tracker for pattern lookup
- `llm_client` (LLMClient): Client for query analysis

### Methods

#### `plan_execution(user_prompt: str, callback: Callable = None) -> Dict`

Analyze query and determine execution strategy.

**Parameters:**
- `user_prompt` (str): User's natural language query
- `callback` (Callable, optional): Progress callback

**Returns:**
- `dict`: Execution plan with keys:
  - `strategy` (str): Selected strategy
  - `reasoning` (str): Explanation of choice
  - `sub_tasks` (list, optional): Task breakdown for workflows
  - `tool_name` (str, optional): Tool name for single/composite strategies
  - `pattern` (dict, optional): Pattern info for pattern strategy

**Strategies:**
- `'force_synthesis'`: Explicit synthesis request detected
- `'composite_tool'`: Matching composite tool found (≥0.7 similarity)
- `'workflow_pattern'`: Matching workflow pattern found (≥0.7 similarity)
- `'sequential'`: Multi-step workflow detected
- `'single'`: Single tool found (≥0.6 similarity)
- `'force_synthesis'`: Fallback when no matches found

**Decision Cascade:**
```
1. Check for explicit synthesis keywords
   ↓
2. Search composite tools (threshold=0.7)
   ↓
3. Search workflow patterns (threshold=0.7)
   ↓
4. Analyze query complexity
   ↓
5. Search single tools (threshold=0.6)
   ↓
6. Fallback to synthesis
```

**Example:**
```python
planner = QueryPlanner(registry, workflow_tracker, llm_client)

plan = planner.plan_execution(
    user_prompt="Load data from CSV and calculate profit margins"
)

print(f"Strategy: {plan['strategy']}")
print(f"Reasoning: {plan['reasoning']}")

if plan['strategy'] == 'sequential':
    print(f"Sub-tasks: {plan['sub_tasks']}")
```

---

## CompositionPlanner

**Module:** `src.composition_planner`  
**Class:** `CompositionPlanner`

### Description

Executes multi-tool workflows by orchestrating sequences of tool executions. Handles both dynamic workflows (from analysis) and pre-defined patterns (from learning).

### Constructor

```python
def __init__(self, registry: CapabilityRegistry, executor: ToolExecutor, 
             synthesis_engine: CapabilitySynthesisEngine, llm_client: LLMClient,
             workflow_tracker: WorkflowTracker)
```

### Methods

#### `execute_workflow(sub_tasks: List[str], user_prompt: str, callback: Callable = None) -> Dict`

Execute a dynamic multi-tool workflow.

**Parameters:**
- `sub_tasks` (list): List of task descriptions
- `user_prompt` (str): Original user query
- `callback` (Callable, optional): Progress callback

**Returns:**
- `dict`: Execution result with keys:
  - `success` (bool): Whether workflow succeeded
  - `results` (list): Results from each step
  - `tool_sequence` (list): Tools executed
  - `final_result` (Any): Combined final result

**Example:**
```python
planner = CompositionPlanner(registry, executor, synthesis_engine, llm_client, workflow_tracker)

result = planner.execute_workflow(
    sub_tasks=[
        "Load CSV data from file",
        "Calculate profit margins",
        "Generate summary report"
    ],
    user_prompt="Analyze profit margins from sales data"
)

if result['success']:
    print(f"Tools used: {result['tool_sequence']}")
    print(f"Final result: {result['final_result']}")
```

**Workflow Execution:**
1. Emit `workflow_start` event
2. For each sub-task:
   - Search for matching tool
   - If found: execute tool
   - If not found: synthesize new tool
   - Emit progress events
3. Combine results
4. Log to workflow tracker
5. Check promotion criteria

---

#### `execute_pattern(pattern: Dict, user_prompt: str, callback: Callable = None) -> Dict`

Execute a pre-defined workflow pattern.

**Parameters:**
- `pattern` (dict): Pattern information with `tool_sequence` key
- `user_prompt` (str): Original user query
- `callback` (Callable, optional): Progress callback

**Returns:**
- `dict`: Execution result

**Example:**
```python
pattern = {
    'pattern_name': 'data_analysis_workflow',
    'tool_sequence': ['load_csv_data', 'calculate_profit_margins', 'generate_report']
}

result = planner.execute_pattern(
    pattern=pattern,
    user_prompt="Analyze sales data"
)
```

---

#### `should_create_composite(sequence: List[str], success_rate: float, frequency: int) -> bool`

Determine if a workflow should be promoted to a composite tool.

**Parameters:**
- `sequence` (list): Tool sequence
- `success_rate` (float): Success rate (0.0-1.0)
- `frequency` (int): Number of occurrences

**Returns:**
- `bool`: True if should be promoted

**Promotion Criteria:**
- Sequence length ≥ 2 tools
- Frequency ≥ 3 occurrences
- Success rate ≥ 0.8 (80%)

**Example:**
```python
should_promote = planner.should_create_composite(
    sequence=['load_csv', 'calculate_margins'],
    success_rate=0.95,
    frequency=5
)
# Returns: True
```

---

## LLMClient

**Module:** `src.llm_client`  
**Class:** `LLMClient`

### Description

Wrapper for OpenAI API providing methods for all LLM interactions including code generation, embeddings, and natural language processing.

### Constructor

```python
def __init__(self, api_key: str = None, model: str = None, embedding_model: str = None)
```

**Parameters:**
- `api_key` (str, optional): OpenAI API key (defaults to `OPENAI_API_KEY` env var)
- `model` (str, optional): Model name (defaults to `gpt-4-turbo-preview`)
- `embedding_model` (str, optional): Embedding model (defaults to `text-embedding-3-small`)

### Methods

#### `generate_spec(user_prompt: str) -> Dict`

Generate function specification from natural language.

**Parameters:**
- `user_prompt` (str): Natural language description

**Returns:**
- `dict`: Specification with keys:
  - `function_name` (str): Snake_case function name
  - `parameters` (list): Parameter definitions
  - `return_type` (str): Return type
  - `description` (str): Function description

**Temperature:** 0.2 (deterministic)

**Example:**
```python
client = LLMClient()

spec = client.generate_spec(
    "Create a function to calculate moving averages"
)

print(f"Function: {spec['function_name']}")
print(f"Parameters: {spec['parameters']}")
print(f"Returns: {spec['return_type']}")
```

---

#### `generate_tests(spec: Dict) -> str`

Generate pytest test suite from specification.

**Parameters:**
- `spec` (dict): Function specification

**Returns:**
- `str`: Pytest test code

**Temperature:** 0.3 (slightly creative)

**Example:**
```python
tests = client.generate_tests(spec)
print(tests)
```

---

#### `generate_implementation(spec: Dict, tests: str) -> str`

Generate function implementation to pass tests.

**Parameters:**
- `spec` (dict): Function specification
- `tests` (str): Test suite code

**Returns:**
- `str`: Python implementation code

**Temperature:** 0.2 (deterministic)

**Example:**
```python
code = client.generate_implementation(spec, tests)
print(code)
```

---

#### `extract_arguments(prompt: str, signature: str) -> Dict`

Extract function arguments from natural language.

**Parameters:**
- `prompt` (str): User's natural language query
- `signature` (str): Function signature

**Returns:**
- `dict`: Extracted arguments

**Temperature:** 0.0 (fully deterministic)

**Example:**
```python
args = client.extract_arguments(
    prompt="Calculate profit margins from data/sales.csv",
    signature="calculate_profit_margins(csv_path: str)"
)
# Returns: {'csv_path': 'data/sales.csv'}
```

---

#### `generate_embedding(text: str) -> List[float]`

Generate 1536-dimensional embedding vector.

**Parameters:**
- `text` (str): Text to embed

**Returns:**
- `list`: 1536-dimensional vector

**Example:**
```python
embedding = client.generate_embedding("Calculate profit margins")
print(f"Dimensions: {len(embedding)}")  # 1536
```

---

#### `synthesize_response(prompt: str, result: Any) -> str`

Generate natural language response from tool result.

**Parameters:**
- `prompt` (str): Original user query
- `result` (Any): Tool execution result

**Returns:**
- `str`: Natural language response

**Temperature:** 0.7 (creative)

**Example:**
```python
response = client.synthesize_response(
    prompt="What's the average profit margin?",
    result={"average_margin": 23.5}
)
print(response)
# "The average profit margin is 23.5%."
```

---

## WorkflowTracker

**Module:** `src.workflow_tracker`  
**Class:** `WorkflowTracker`

### Description

Logs tool executions and mines patterns for workflow learning. Tracks session-based workflows and identifies reusable sequences.

### Constructor

```python
def __init__(self)
```

### Methods

#### `log_execution(tool_name: str, inputs: Dict, outputs: Any, success: bool, execution_time_ms: int, session_id: str, execution_order: int) -> None`

Log a tool execution.

**Parameters:**
- `tool_name` (str): Name of executed tool
- `inputs` (dict): Input parameters
- `outputs` (Any): Execution result
- `success` (bool): Whether execution succeeded
- `execution_time_ms` (int): Execution time in milliseconds
- `session_id` (str): Session identifier
- `execution_order` (int): Order within session

**Example:**
```python
tracker = WorkflowTracker()

tracker.log_execution(
    tool_name="calculate_profit_margins",
    inputs={"csv_path": "data/sales.csv"},
    outputs={"average_margin": 23.5},
    success=True,
    execution_time_ms=145,
    session_id="session-123",
    execution_order=1
)
```

---

#### `get_workflow_patterns(min_frequency: int = 2, limit: int = 10) -> List[Dict]`

Retrieve learned workflow patterns.

**Parameters:**
- `min_frequency` (int): Minimum occurrence count
- `limit` (int): Maximum patterns to return

**Returns:**
- `list`: List of pattern dictionaries with keys:
  - `pattern_name` (str): Pattern name
  - `tool_sequence` (list): Tool sequence
  - `frequency` (int): Occurrence count
  - `avg_success_rate` (float): Average success rate
  - `confidence_score` (float): Confidence score

**Example:**
```python
patterns = tracker.get_workflow_patterns(min_frequency=3, limit=5)

for pattern in patterns:
    print(f"{pattern['pattern_name']}: {pattern['tool_sequence']}")
    print(f"  Frequency: {pattern['frequency']}, Success: {pattern['avg_success_rate']:.1%}")
```

---

#### `get_tool_relationships(tool_name: str = None, min_confidence: float = 0.5) -> List[Dict]`

Get tool co-occurrence relationships.

**Parameters:**
- `tool_name` (str, optional): Filter for specific tool
- `min_confidence` (float): Minimum confidence score

**Returns:**
- `list`: List of relationship dictionaries

**Example:**
```python
relationships = tracker.get_tool_relationships(
    tool_name="calculate_profit_margins",
    min_confidence=0.7
)

for rel in relationships:
    print(f"{rel['tool_a']} → {rel['tool_b']}: {rel['confidence_score']:.2f}")
```

---

#### `get_session_history(session_id: str, limit: int = 100) -> List[Dict]`

Get execution history for a session.

**Parameters:**
- `session_id` (str): Session identifier
- `limit` (int): Maximum executions to return

**Returns:**
- `list`: List of execution records

**Example:**
```python
history = tracker.get_session_history("session-123", limit=50)

for execution in history:
    print(f"{execution['tool_name']}: {execution['success']}")
```

---

## SessionMemoryManager

**Module:** `src.session_memory`  
**Class:** `SessionMemoryManager`

### Description

Maintains conversational context across requests. Stores messages in Supabase and provides context enrichment for prompts.

### Constructor

```python
def __init__(self)
```

### Methods

#### `start_session(session_id: str = None) -> str`

Initialize a new session.

**Parameters:**
- `session_id` (str, optional): Custom session ID (generates UUID if not provided)

**Returns:**
- `str`: Session identifier

**Example:**
```python
memory = SessionMemoryManager()

session_id = memory.start_session()
print(f"Session started: {session_id}")
```

---

#### `append_message(session_id: str, role: str, content: str) -> None`

Add a message to session history.

**Parameters:**
- `session_id` (str): Session identifier
- `role` (str): 'user' or 'assistant'
- `content` (str): Message content

**Example:**
```python
memory.append_message(
    session_id="session-123",
    role="user",
    content="Calculate profit margins from data.csv"
)

memory.append_message(
    session_id="session-123",
    role="assistant",
    content="The average profit margin is 23.5%"
)
```

---

#### `get_recent_messages(session_id: str, limit: int = 10) -> List[Dict]`

Retrieve recent messages from session.

**Parameters:**
- `session_id` (str): Session identifier
- `limit` (int): Maximum messages to return

**Returns:**
- `list`: List of message dictionaries with keys:
  - `role` (str): 'user' or 'assistant'
  - `content` (str): Message content
  - `message_index` (int): Sequential index
  - `created_at` (str): ISO 8601 timestamp

**Example:**
```python
messages = memory.get_recent_messages("session-123", limit=5)

for msg in messages:
    print(f"[{msg['role']}] {msg['content']}")
```

---

#### `build_prompt_with_context(session_id: str, user_prompt: str) -> str`

Enrich prompt with conversational context.

**Parameters:**
- `session_id` (str): Session identifier
- `user_prompt` (str): Current user prompt

**Returns:**
- `str`: Enriched prompt with context

**Context Window:** Last 10 messages

**Example:**
```python
enriched_prompt = memory.build_prompt_with_context(
    session_id="session-123",
    user_prompt="What about the cost analysis?"
)

# Returns prompt with previous conversation context prepended
```

---

## Usage Examples

### Complete Workflow Example

```python
from src.orchestrator import AgentOrchestrator

# Initialize orchestrator (initializes all subsystems)
orchestrator = AgentOrchestrator()

# Define progress callback
def progress_handler(event_type, data):
    print(f"[{event_type}] {data}")

# Create session
session_id = orchestrator.memory_manager.start_session()

# Process first request
result1 = orchestrator.process_request(
    user_prompt="Load data from data/sales.csv",
    session_id=session_id,
    callback=progress_handler
)

print(f"Response: {result1['response']}")

# Process follow-up request (uses session context)
result2 = orchestrator.process_request(
    user_prompt="Now calculate the profit margins",
    session_id=session_id,
    callback=progress_handler
)

print(f"Response: {result2['response']}")

# Get session history
messages = orchestrator.memory_manager.get_recent_messages(session_id)
for msg in messages:
    print(f"[{msg['role']}] {msg['content']}")
```

### Direct Tool Synthesis Example

```python
from src.synthesis_engine import CapabilitySynthesisEngine
from src.capability_registry import CapabilityRegistry
from src.llm_client import LLMClient

# Initialize components
llm_client = LLMClient()
registry = CapabilityRegistry(llm_client)
engine = CapabilitySynthesisEngine(llm_client, registry)

# Synthesize tool
result = engine.synthesize_capability(
    user_prompt="Create a function to calculate compound interest"
)

if result['success']:
    print(f"Tool created: {result['tool_name']}")
    print(f"Tests passed: {result['tests_verified']}")
    
    # Retrieve and use the tool
    tool = registry.get_tool_by_name(result['tool_name'])
    print(f"Code:\n{tool['code']}")
```

### Pattern Mining Example

```python
from src.workflow_tracker import WorkflowTracker

tracker = WorkflowTracker()

# Get frequent patterns
patterns = tracker.get_workflow_patterns(min_frequency=3)

for pattern in patterns:
    print(f"\nPattern: {pattern['pattern_name']}")
    print(f"Sequence: {' → '.join(pattern['tool_sequence'])}")
    print(f"Frequency: {pattern['frequency']}")
    print(f"Success Rate: {pattern['avg_success_rate']:.1%}")
    
    # Get relationships for first tool in pattern
    if pattern['tool_sequence']:
        first_tool = pattern['tool_sequence'][0]
        relationships = tracker.get_tool_relationships(
            tool_name=first_tool,
            min_confidence=0.7
        )
        print(f"Related tools: {[r['tool_b'] for r in relationships]}")
```

---

## Configuration

All modules use configuration from `config.py`:

```python
from config import Config

# OpenAI settings
Config.OPENAI_API_KEY        # API key
Config.OPENAI_MODEL          # Model name (default: gpt-4-turbo-preview)
Config.OPENAI_EMBEDDING_MODEL # Embedding model (default: text-embedding-3-small)

# Supabase settings
Config.SUPABASE_URL          # Supabase project URL
Config.SUPABASE_KEY          # Supabase API key
Config.SIMILARITY_THRESHOLD  # Default similarity threshold (0.4)

# Docker settings
Config.DOCKER_IMAGE_NAME     # Sandbox image (agent-sandbox:latest)
Config.DOCKER_TIMEOUT        # Execution timeout (30 seconds)

# Storage settings
Config.TOOLS_DIR             # Tool storage directory (tools/)

# Flask settings
Config.FLASK_HOST            # Server host (0.0.0.0)
Config.FLASK_PORT            # Server port (5001)
Config.FLASK_DEBUG           # Debug mode (True)
```

---

## Error Handling

All modules implement comprehensive error handling:

```python
try:
    result = orchestrator.process_request(
        user_prompt="Invalid query",
        session_id="session-123"
    )
except Exception as e:
    print(f"Error: {e}")
    # Handle error appropriately
```

Common exceptions:
- `ValueError`: Invalid parameters
- `FileNotFoundError`: Missing tool files
- `ConnectionError`: Supabase connection issues
- `TimeoutError`: Docker execution timeout
- `Exception`: General errors with descriptive messages

---

## Best Practices

1. **Always use sessions** for conversational interactions
2. **Implement progress callbacks** for user feedback
3. **Handle errors gracefully** with try-except blocks
4. **Clean up resources** when done (sessions, connections)
5. **Monitor tool count** to track system growth
6. **Review patterns regularly** to understand learned behaviors
7. **Set appropriate thresholds** based on use case requirements
8. **Use reranking** for production deployments to improve accuracy

---

## Generating HTML Documentation

To generate HTML API documentation using pdoc3:

```bash
# Install pdoc3
pip install pdoc3

# Generate documentation for all modules
pdoc3 --html --output-dir docs/api \
  src.orchestrator \
  src.synthesis_engine \
  src.capability_registry \
  src.query_planner \
  src.composition_planner \
  src.llm_client \
  src.workflow_tracker \
  src.session_memory

# View documentation
open docs/api/index.html
```

This will create interactive HTML documentation with:
- Module and class hierarchies
- Method signatures and docstrings
- Source code links
- Cross-references between modules
- Search functionality

---

## Additional Resources

- [OpenAPI REST API Documentation](openapi.yaml)
- [WebSocket Events Reference](websocket-events.md)
- [Integration Guide](integration-guide.md)
- [Database Schema Documentation](database-schema.md)
- [GitHub Repository](https://github.com/haider-toha/Self-Engineering-Agent-Framework)
