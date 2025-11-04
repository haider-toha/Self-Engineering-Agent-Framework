# Backend Module API Documentation

This document provides comprehensive API documentation for all core backend modules in the Self-Engineering Agent Framework.

## Table of Contents

1. [AgentOrchestrator](#agentorchestrator)
2. [CapabilitySynthesisEngine](#capabilitysynthesisengine)
3. [CapabilityRegistry](#capabilityregistry)
4. [QueryPlanner](#queryplanner)
5. [CompositionPlanner](#compositionplanner)
6. [LLMClient](#llmclient)
7. [ToolExecutor](#toolexecutor)
8. [WorkflowTracker](#workflowtracker)
9. [SessionMemoryManager](#sessionmemorymanager)
10. [SecureSandbox](#securesandbox)

---

## AgentOrchestrator

**Module:** `src/orchestrator.py`

Central coordinator that manages the entire request lifecycle from user input to response generation.

### Class: `AgentOrchestrator`

#### Constructor

```python
def __init__(
    self,
    registry: CapabilityRegistry = None,
    synthesis_engine: CapabilitySynthesisEngine = None,
    executor: ToolExecutor = None,
    synthesizer: ResponseSynthesizer = None,
    workflow_tracker: WorkflowTracker = None,
    query_planner: QueryPlanner = None,
    composition_planner: CompositionPlanner = None,
    memory_manager: SessionMemoryManager = None
)
```

**Parameters:**
- `registry` (CapabilityRegistry, optional): Tool storage and retrieval system
- `synthesis_engine` (CapabilitySynthesisEngine, optional): Tool synthesis system
- `executor` (ToolExecutor, optional): Tool execution engine
- `synthesizer` (ResponseSynthesizer, optional): Natural language response generator
- `workflow_tracker` (WorkflowTracker, optional): Execution logging and pattern mining
- `query_planner` (QueryPlanner, optional): Query analysis and strategy selection
- `composition_planner` (CompositionPlanner, optional): Multi-tool workflow execution
- `memory_manager` (SessionMemoryManager, optional): Conversational context management

**Example:**
```python
from src.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()
```

#### Methods

##### `process_request()`

Process a user request from start to finish with enhanced workflow capabilities.

```python
def process_request(
    self,
    user_prompt: str,
    session_id: Optional[str] = None,
    callback: Optional[Callable[[str, Any], None]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `user_prompt` (str): User's natural language request
- `session_id` (str, optional): Session identifier for conversational context
- `callback` (Callable, optional): Callback function(event_type, data) for progress updates

**Returns:**
- `Dict[str, Any]`: Result dictionary with keys:
  - `success` (bool): Whether the request was processed successfully
  - `response` (str): Natural language response or error message
  - `tool_name` (str, optional): Name of the tool that was executed
  - `tool_result` (Any, optional): Raw tool execution result
  - `synthesized` (bool, optional): Whether a new tool was created
  - `session_id` (str, optional): Session identifier if provided
  - `error` (str, optional): Error message if failed

**Example:**
```python
def progress_callback(event_type, data):
    print(f"[{event_type}] {data}")

result = orchestrator.process_request(
    user_prompt="Calculate profit margins from data/sales.csv",
    session_id="my-session-123",
    callback=progress_callback
)

if result['success']:
    print(f"Response: {result['response']}")
    print(f"Tool used: {result['tool_name']}")
else:
    print(f"Error: {result['error']}")
```

##### `get_all_tools()`

Get list of all registered tools.

```python
def get_all_tools(self) -> List[Dict[str, Any]]
```

**Returns:**
- `List[Dict[str, Any]]`: List of tool metadata dictionaries

**Example:**
```python
tools = orchestrator.get_all_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['docstring']}")
```

##### `get_tool_count()`

Get the total number of registered tools.

```python
def get_tool_count(self) -> int
```

**Returns:**
- `int`: Number of registered tools

**Example:**
```python
count = orchestrator.get_tool_count()
print(f"Available tools: {count}")
```

---

## CapabilitySynthesisEngine

**Module:** `src/synthesis_engine.py`

Synthesizes new agent capabilities using a Test-Driven Development workflow.

### Class: `CapabilitySynthesisEngine`

#### Constructor

```python
def __init__(
    self,
    llm_client: LLMClient = None,
    sandbox: SecureSandbox = None,
    registry: CapabilityRegistry = None
)
```

**Parameters:**
- `llm_client` (LLMClient, optional): LLM client for code generation
- `sandbox` (SecureSandbox, optional): Secure sandbox for verification
- `registry` (CapabilityRegistry, optional): Capability registry for storage

#### Methods

##### `synthesize_capability()`

Synthesize a new capability from a user prompt using 5-stage TDD pipeline.

```python
def synthesize_capability(
    self,
    user_prompt: str,
    callback: Optional[Callable[[str, Any], None]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `user_prompt` (str): Natural language description of desired functionality
- `callback` (Callable, optional): Callback function for progress updates

**Returns:**
- `Dict[str, Any]`: Synthesis result with keys:
  - `success` (bool): Whether synthesis succeeded
  - `tool_name` (str): Name of the synthesized tool
  - `spec` (dict): Function specification
  - `code` (str): Implementation code
  - `tests` (str): Test suite code
  - `metadata` (dict): Tool metadata
  - `tests_verified` (bool): Whether tests passed
  - `error` (str, optional): Error message if failed
  - `step` (str, optional): Failed step if unsuccessful

**Pipeline Stages:**
1. **Specification**: Generate function spec from natural language
2. **Tests**: Create pytest test suite with edge cases
3. **Implementation**: Generate code to pass tests
4. **Verification**: Execute in Docker sandbox
5. **Registration**: Store in registry with embedding

**Example:**
```python
from src.synthesis_engine import CapabilitySynthesisEngine

engine = CapabilitySynthesisEngine()

result = engine.synthesize_capability(
    user_prompt="Create a function to calculate factorial of a number",
    callback=lambda event, data: print(f"[{event}] {data}")
)

if result['success']:
    print(f"Created tool: {result['tool_name']}")
    print(f"Tests verified: {result['tests_verified']}")
else:
    print(f"Failed at {result['step']}: {result['error']}")
```

---

## CapabilityRegistry

**Module:** `src/capability_registry.py`

Manages storage, indexing, and retrieval of agent capabilities using Supabase with vector search.

### Class: `CapabilityRegistry`

#### Constructor

```python
def __init__(self, llm_client=None)
```

**Parameters:**
- `llm_client` (LLMClient, optional): LLM client for generating embeddings

#### Methods

##### `add_tool()`

Add a new tool to the registry.

```python
def add_tool(
    self,
    name: str,
    code: str,
    tests: str,
    docstring: str
) -> Dict[str, Any]
```

**Parameters:**
- `name` (str): Function name (snake_case)
- `code` (str): Python function implementation
- `tests` (str): Pytest test code
- `docstring` (str): Descriptive documentation

**Returns:**
- `Dict[str, Any]`: Tool metadata

**Example:**
```python
from src.capability_registry import CapabilityRegistry

registry = CapabilityRegistry()

metadata = registry.add_tool(
    name="calculate_factorial",
    code="def calculate_factorial(n: int) -> int:\n    ...",
    tests="def test_calculate_factorial():\n    ...",
    docstring="Calculate the factorial of a positive integer"
)
```

##### `search_tool()`

Search for a tool using semantic similarity with optional re-ranking.

```python
def search_tool(
    self,
    query: str,
    threshold: float = None,
    rerank: bool = True
) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `query` (str): Natural language query
- `threshold` (float, optional): Minimum similarity score (0-1), defaults to Config.SIMILARITY_THRESHOLD
- `rerank` (bool): Whether to re-rank results by usage statistics (default True)

**Returns:**
- `Optional[Dict[str, Any]]`: Tool information dictionary if found, None otherwise
  - `name` (str): Tool function name
  - `code` (str): Implementation code
  - `file_path` (str): Path to tool file
  - `test_path` (str): Path to test file
  - `docstring` (str): Tool documentation
  - `timestamp` (str): Creation timestamp
  - `similarity_score` (float): Semantic similarity score

**Example:**
```python
tool = registry.search_tool(
    query="Calculate factorial of a number",
    threshold=0.7,
    rerank=True
)

if tool:
    print(f"Found: {tool['name']} (similarity: {tool['similarity_score']})")
else:
    print("No matching tool found")
```

##### `get_tool_by_name()`

Retrieve a specific tool by name.

```python
def get_tool_by_name(self, name: str) -> Optional[Dict[str, Any]]
```

**Parameters:**
- `name` (str): Tool function name

**Returns:**
- `Optional[Dict[str, Any]]`: Tool information dictionary if found, None otherwise

**Example:**
```python
tool = registry.get_tool_by_name("calculate_factorial")
if tool:
    print(tool['code'])
```

##### `get_all_tools()`

Get list of all registered tools.

```python
def get_all_tools(self) -> List[Dict[str, Any]]
```

**Returns:**
- `List[Dict[str, Any]]`: List of tool metadata dictionaries

##### `delete_tool()`

Delete a tool from the registry.

```python
def delete_tool(self, name: str) -> bool
```

**Parameters:**
- `name` (str): Tool function name

**Returns:**
- `bool`: True if deleted, False if not found

##### `cleanup_orphaned_tools()`

Remove tools from database that no longer have corresponding files.

```python
def cleanup_orphaned_tools(self) -> int
```

**Returns:**
- `int`: Number of orphaned tools removed

##### `count_tools()`

Get the total number of registered tools.

```python
def count_tools(self) -> int
```

**Returns:**
- `int`: Number of tools

---

## QueryPlanner

**Module:** `src/query_planner.py`

Analyzes user intent and determines execution strategy.

### Class: `QueryPlanner`

#### Constructor

```python
def __init__(
    self,
    llm_client: LLMClient,
    registry: CapabilityRegistry
)
```

**Parameters:**
- `llm_client` (LLMClient): LLM client for query analysis
- `registry` (CapabilityRegistry): Tool registry for searching

#### Methods

##### `plan_execution()`

Analyze user prompt and determine execution strategy.

```python
def plan_execution(self, user_prompt: str) -> Dict[str, Any]
```

**Parameters:**
- `user_prompt` (str): User's natural language request

**Returns:**
- `Dict[str, Any]`: Execution plan with keys:
  - `strategy` (str): Execution strategy
  - `reasoning` (str): Explanation of strategy choice
  - `sub_tasks` (List[str], optional): Decomposed tasks for multi-tool workflows
  - `composite_tool` (dict, optional): Composite tool information
  - `pattern` (dict, optional): Workflow pattern information

**Strategies:**
- `force_synthesis`: User explicitly requested tool creation
- `composite_tool`: Existing composite tool matches query
- `workflow_pattern`: Known workflow pattern matches query
- `multi_tool_composition`: Complex query requiring multiple tools
- `multi_tool_sequential`: Sequential multi-tool execution
- `single`: Single tool execution (default)

**Example:**
```python
from src.query_planner import QueryPlanner

planner = QueryPlanner(llm_client, registry)

plan = planner.plan_execution(
    "Load sales data, calculate metrics, and generate a report"
)

print(f"Strategy: {plan['strategy']}")
print(f"Reasoning: {plan['reasoning']}")
if 'sub_tasks' in plan:
    print(f"Sub-tasks: {plan['sub_tasks']}")
```

---

## CompositionPlanner

**Module:** `src/composition_planner.py`

Executes multi-tool workflows.

### Class: `CompositionPlanner`

#### Constructor

```python
def __init__(
    self,
    registry: CapabilityRegistry,
    executor: ToolExecutor,
    llm_client: LLMClient
)
```

**Parameters:**
- `registry` (CapabilityRegistry): Tool registry
- `executor` (ToolExecutor): Tool execution engine
- `llm_client` (LLMClient): LLM client for workflow coordination

#### Methods

##### `execute_workflow()`

Execute a dynamic multi-tool workflow.

```python
def execute_workflow(
    self,
    sub_tasks: List[str],
    user_prompt: str,
    callback: Optional[Callable] = None
) -> Dict[str, Any]
```

**Parameters:**
- `sub_tasks` (List[str]): List of task descriptions
- `user_prompt` (str): Original user prompt
- `callback` (Callable, optional): Progress callback

**Returns:**
- `Dict[str, Any]`: Workflow execution result

##### `execute_pattern()`

Execute a pre-defined workflow pattern.

```python
def execute_pattern(
    self,
    pattern: Dict[str, Any],
    user_prompt: str,
    callback: Optional[Callable] = None
) -> Dict[str, Any]
```

**Parameters:**
- `pattern` (dict): Workflow pattern with tool_sequence
- `user_prompt` (str): Original user prompt
- `callback` (Callable, optional): Progress callback

**Returns:**
- `Dict[str, Any]`: Pattern execution result

---

## LLMClient

**Module:** `src/llm_client.py`

Wrapper for OpenAI API providing all LLM interactions.

### Class: `LLMClient`

#### Constructor

```python
def __init__(self)
```

Initializes OpenAI client with API key from Config.

#### Methods

##### `generate_spec()`

Generate function specification from user prompt.

```python
def generate_spec(self, user_prompt: str) -> Dict[str, Any]
```

**Parameters:**
- `user_prompt` (str): Natural language description

**Returns:**
- `Dict[str, Any]`: Function specification with keys:
  - `function_name` (str): Snake_case function name
  - `parameters` (List[dict]): Parameter specifications
  - `return_type` (str): Return type description
  - `docstring` (str): Function documentation

**Example:**
```python
from src.llm_client import LLMClient

client = LLMClient()

spec = client.generate_spec("Calculate factorial of a number")
print(f"Function: {spec['function_name']}")
print(f"Parameters: {spec['parameters']}")
```

##### `generate_tests()`

Generate pytest test suite from specification.

```python
def generate_tests(self, spec: Dict[str, Any]) -> str
```

**Parameters:**
- `spec` (dict): Function specification

**Returns:**
- `str`: Pytest test code

##### `generate_implementation()`

Generate function implementation from spec and tests.

```python
def generate_implementation(
    self,
    spec: Dict[str, Any],
    tests: str
) -> str
```

**Parameters:**
- `spec` (dict): Function specification
- `tests` (str): Test suite code

**Returns:**
- `str`: Python implementation code

##### `extract_arguments()`

Extract function arguments from natural language prompt.

```python
def extract_arguments(
    self,
    prompt: str,
    signature: str
) -> Dict[str, Any]
```

**Parameters:**
- `prompt` (str): User's natural language prompt
- `signature` (str): Function signature

**Returns:**
- `Dict[str, Any]`: Extracted arguments

**Example:**
```python
args = client.extract_arguments(
    prompt="Calculate factorial of 5",
    signature="calculate_factorial(n: int) -> int"
)
print(args)  # {'n': 5}
```

##### `generate_embedding()`

Generate 1536-dimensional embedding vector.

```python
def generate_embedding(self, text: str) -> List[float]
```

**Parameters:**
- `text` (str): Text to embed

**Returns:**
- `List[float]`: 1536-dimensional embedding vector

##### `synthesize_response()`

Generate natural language response from tool result.

```python
def synthesize_response(
    self,
    prompt: str,
    result: Any
) -> str
```

**Parameters:**
- `prompt` (str): Original user prompt
- `result` (Any): Tool execution result

**Returns:**
- `str`: Natural language response

---

## ToolExecutor

**Module:** `src/executor.py`

Executes tools with argument extraction and retry logic.

### Class: `ToolExecutor`

#### Constructor

```python
def __init__(self, llm_client: LLMClient)
```

**Parameters:**
- `llm_client` (LLMClient): LLM client for argument extraction

#### Methods

##### `execute_with_retry()`

Execute a tool with automatic retry on failure.

```python
def execute_with_retry(
    self,
    tool_info: Dict[str, Any],
    user_prompt: str,
    max_retries: int = 2
) -> Dict[str, Any]
```

**Parameters:**
- `tool_info` (dict): Tool information from registry
- `user_prompt` (str): User's natural language prompt
- `max_retries` (int): Maximum retry attempts (default 2)

**Returns:**
- `Dict[str, Any]`: Execution result with keys:
  - `success` (bool): Whether execution succeeded
  - `result` (Any): Tool execution result
  - `error` (str, optional): Error message if failed
  - `error_type` (str, optional): Error classification

**Example:**
```python
from src.executor import ToolExecutor

executor = ToolExecutor(llm_client)

result = executor.execute_with_retry(
    tool_info=tool,
    user_prompt="Calculate factorial of 5"
)

if result['success']:
    print(f"Result: {result['result']}")
else:
    print(f"Error: {result['error']}")
```

---

## WorkflowTracker

**Module:** `src/workflow_tracker.py`

Logs tool executions and mines workflow patterns.

### Class: `WorkflowTracker`

#### Constructor

```python
def __init__(self)
```

Initializes Supabase client for execution logging.

#### Methods

##### `start_session()`

Start a new workflow tracking session.

```python
def start_session(self, session_id: Optional[str] = None) -> None
```

**Parameters:**
- `session_id` (str, optional): Session identifier

##### `log_execution()`

Log a tool execution.

```python
def log_execution(
    self,
    tool_name: str,
    inputs: Dict[str, Any],
    outputs: Any,
    success: bool,
    execution_time_ms: int,
    user_prompt: str
) -> None
```

**Parameters:**
- `tool_name` (str): Name of executed tool
- `inputs` (dict): Tool input parameters
- `outputs` (Any): Tool execution results
- `success` (bool): Whether execution succeeded
- `execution_time_ms` (int): Execution time in milliseconds
- `user_prompt` (str): Original user prompt

##### `get_workflow_patterns()`

Retrieve learned workflow patterns.

```python
def get_workflow_patterns(
    self,
    min_frequency: int = 2,
    limit: int = 10
) -> List[Dict[str, Any]]
```

**Parameters:**
- `min_frequency` (int): Minimum pattern frequency (default 2)
- `limit` (int): Maximum number of patterns (default 10)

**Returns:**
- `List[Dict[str, Any]]`: List of workflow patterns

##### `get_tool_relationships()`

Get tool co-occurrence relationships.

```python
def get_tool_relationships(
    self,
    tool_name: Optional[str] = None,
    min_confidence: float = 0.5
) -> List[Dict[str, Any]]
```

**Parameters:**
- `tool_name` (str, optional): Filter by specific tool
- `min_confidence` (float): Minimum confidence score (default 0.5)

**Returns:**
- `List[Dict[str, Any]]`: List of tool relationships

---

## SessionMemoryManager

**Module:** `src/session_memory.py`

Maintains conversational context across requests.

### Class: `SessionMemoryManager`

#### Constructor

```python
def __init__(self)
```

Initializes Supabase client for session storage.

#### Methods

##### `start_session()`

Initialize or retrieve a session.

```python
def start_session(self, session_id: Optional[str] = None) -> str
```

**Parameters:**
- `session_id` (str, optional): Existing session ID or None for new session

**Returns:**
- `str`: Session identifier

**Example:**
```python
from src.session_memory import SessionMemoryManager

memory = SessionMemoryManager()

session_id = memory.start_session()
print(f"Session ID: {session_id}")
```

##### `append_message()`

Add a message to session history.

```python
def append_message(
    self,
    session_id: str,
    role: str,
    content: str
) -> None
```

**Parameters:**
- `session_id` (str): Session identifier
- `role` (str): Message role ('user' or 'assistant')
- `content` (str): Message content

##### `get_recent_messages()`

Retrieve recent messages from session.

```python
def get_recent_messages(
    self,
    session_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]
```

**Parameters:**
- `session_id` (str): Session identifier
- `limit` (int): Maximum number of messages (default 10)

**Returns:**
- `List[Dict[str, Any]]`: List of messages with role, content, created_at

##### `build_prompt_with_context()`

Enrich user prompt with conversation history.

```python
def build_prompt_with_context(
    self,
    session_id: str,
    user_prompt: str
) -> str
```

**Parameters:**
- `session_id` (str): Session identifier
- `user_prompt` (str): Current user prompt

**Returns:**
- `str`: Enriched prompt with context

---

## SecureSandbox

**Module:** `src/sandbox.py`

Executes generated code safely in Docker containers.

### Class: `SecureSandbox`

#### Constructor

```python
def __init__(self)
```

Initializes Docker client.

#### Methods

##### `verify_tool()`

Verify a tool by running its tests in a secure container.

```python
def verify_tool(
    self,
    function_name: str,
    function_code: str,
    test_code: str,
    data_files: Dict[str, str] = None
) -> Dict[str, Any]
```

**Parameters:**
- `function_name` (str): Name of the function
- `function_code` (str): Implementation code
- `test_code` (str): Pytest test code
- `data_files` (dict, optional): Dictionary of filename -> content for data files

**Returns:**
- `Dict[str, Any]`: Verification result with keys:
  - `success` (bool): Whether tests passed
  - `output` (str): Test execution output
  - `error` (str, optional): Error message if failed

**Security Features:**
1. Container isolation (kernel-level separation)
2. Network isolation (network_mode='none')
3. Resource limits (512MB RAM, 50% CPU, 30s timeout)
4. Read-only filesystem (limited /tmp access)
5. Non-root user execution

**Example:**
```python
from src.sandbox import SecureSandbox

sandbox = SecureSandbox()

result = sandbox.verify_tool(
    function_name="calculate_factorial",
    function_code="def calculate_factorial(n):\n    ...",
    test_code="def test_calculate_factorial():\n    ..."
)

if result['success']:
    print("Tests passed!")
else:
    print(f"Tests failed: {result['output']}")
```

---

## Usage Examples

### Complete Workflow Example

```python
from src.orchestrator import AgentOrchestrator
from src.session_memory import SessionMemoryManager

# Initialize orchestrator
orchestrator = AgentOrchestrator()

# Create a session
memory = SessionMemoryManager()
session_id = memory.start_session()

# Define progress callback
def progress_callback(event_type, data):
    print(f"[{event_type}] {data}")

# Process a request
result = orchestrator.process_request(
    user_prompt="Calculate profit margins from data/sales.csv",
    session_id=session_id,
    callback=progress_callback
)

# Handle result
if result['success']:
    print(f"\nSuccess!")
    print(f"Response: {result['response']}")
    print(f"Tool: {result['tool_name']}")
    print(f"Synthesized: {result.get('synthesized', False)}")
else:
    print(f"\nError: {result['error']}")

# Get conversation history
messages = memory.get_recent_messages(session_id)
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

### Direct Tool Synthesis Example

```python
from src.synthesis_engine import CapabilitySynthesisEngine
from src.capability_registry import CapabilityRegistry

# Initialize components
engine = CapabilitySynthesisEngine()
registry = CapabilityRegistry()

# Synthesize a new tool
result = engine.synthesize_capability(
    user_prompt="Create a function to calculate the Fibonacci sequence up to n terms"
)

if result['success']:
    print(f"Created: {result['tool_name']}")
    print(f"Code:\n{result['code']}")
    
    # Tool is automatically registered and ready to use
    tool = registry.get_tool_by_name(result['tool_name'])
    print(f"Tool registered: {tool is not None}")
```

### Tool Search and Execution Example

```python
from src.capability_registry import CapabilityRegistry
from src.executor import ToolExecutor
from src.llm_client import LLMClient

# Initialize components
registry = CapabilityRegistry()
executor = ToolExecutor(LLMClient())

# Search for a tool
tool = registry.search_tool(
    query="Calculate factorial",
    threshold=0.7
)

if tool:
    print(f"Found: {tool['name']}")
    
    # Execute the tool
    result = executor.execute_with_retry(
        tool_info=tool,
        user_prompt="Calculate factorial of 10"
    )
    
    if result['success']:
        print(f"Result: {result['result']}")
    else:
        print(f"Error: {result['error']}")
else:
    print("No matching tool found")
```
