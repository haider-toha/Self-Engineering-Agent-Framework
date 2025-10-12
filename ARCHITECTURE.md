# 🏗️ Architecture Deep Dive

## System Overview

The Self-Engineering Agent Framework is built on a **modular, event-driven architecture** where each component has a single, well-defined responsibility.

## Component Interaction Flow

### Scenario 1: Using an Existing Tool

```
┌─────────────┐
│  User Input │ "What is 15% of 300?"
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Web Interface (Flask + Socket.IO)                       │
│  • Receives query via WebSocket                          │
│  • Emits real-time events to frontend                    │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Orchestrator (Brain)                                    │
│  • Receives: user_prompt, callback                       │
│  • Emit: "searching"                                     │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Capability Registry (ChromaDB)                          │
│  • Convert prompt to embedding                           │
│  • Search vector database                                │
│  • Find: calculate_percentage (similarity: 0.89)         │
│  • Return: tool_info (code, metadata)                    │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ Tool Found!
┌─────────────────────────────────────────────────────────┐
│  Orchestrator                                            │
│  • Emit: "tool_found"                                    │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Tool Executor                                           │
│  • Parse prompt with LLM                                 │
│  • Extract: {base: 300, percentage: 15}                 │
│  • Load calculate_percentage dynamically                 │
│  • Execute: calculate_percentage(300, 15)                │
│  • Return: 45.0                                          │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Response Synthesizer                                    │
│  • Input: prompt + result (45.0)                         │
│  • LLM generates natural response                        │
│  • Output: "15 percent of 300 is 45."                    │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Web Interface                                           │
│  • Emit: "complete"                                      │
│  • Display response to user                              │
└─────────────────────────────────────────────────────────┘
```

### Scenario 2: Synthesizing a New Tool

```
┌─────────────┐
│  User Input │ "Reverse the string 'hello'"
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Web Interface → Orchestrator                            │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Capability Registry                                     │
│  • Search for "reverse string"                           │
│  • No matches above threshold (0.75)                     │
│  • Return: None                                          │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ No Tool Found!
┌─────────────────────────────────────────────────────────┐
│  Orchestrator                                            │
│  • Emit: "no_tool_found"                                 │
│  • Emit: "entering_synthesis_mode"                       │
│  • Call: synthesis_engine.synthesize_capability()        │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
╔═════════════════════════════════════════════════════════╗
║  SYNTHESIS ENGINE - TDD Workflow                         ║
╚═════════════════════════════════════════════════════════╝
       │
       ▼ STEP 1: Specification
┌─────────────────────────────────────────────────────────┐
│  LLM Client                                              │
│  • Prompt: "Generate function spec for: reverse string"  │
│  • LLM responds with JSON:                               │
│    {                                                     │
│      "function_name": "reverse_string",                  │
│      "parameters": [{"name": "s", "type": "str"}],       │
│      "return_type": "str",                               │
│      "docstring": "Reverse a string..."                  │
│    }                                                     │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ STEP 2: Test Generation
┌─────────────────────────────────────────────────────────┐
│  LLM Client                                              │
│  • Prompt: "Generate pytest tests for reverse_string"    │
│  • LLM generates:                                        │
│    def test_reverse_basic():                             │
│        assert reverse_string("hello") == "olleh"         │
│    def test_reverse_empty():                             │
│        assert reverse_string("") == ""                   │
│    def test_reverse_single():                            │
│        assert reverse_string("a") == "a"                 │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ STEP 3: Implementation
┌─────────────────────────────────────────────────────────┐
│  LLM Client                                              │
│  • Prompt: "Implement reverse_string to pass tests"      │
│  • LLM generates:                                        │
│    def reverse_string(s: str) -> str:                    │
│        return s[::-1]                                    │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ STEP 4: Verification
┌─────────────────────────────────────────────────────────┐
│  Secure Sandbox (Docker)                                 │
│  1. Create temporary directory                           │
│  2. Write function code and tests                        │
│  3. Spin up Docker container:                            │
│     - Image: python:3.10-slim + pytest                   │
│     - Network: disabled                                  │
│     - CPU/Memory: limited                                │
│     - Mount: /code (read-only)                           │
│  4. Execute: pytest -v test_tool.py                      │
│  5. Capture output and exit code                         │
│  6. Destroy container                                    │
│  7. Return: {success: true, output: "..."}               │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ Tests Pass! ✓
       │
       ▼ STEP 5: Registration
┌─────────────────────────────────────────────────────────┐
│  Capability Registry                                     │
│  • Save code: tools/reverse_string.py                    │
│  • Save tests: tools/test_reverse_string.py              │
│  • Generate embedding from docstring                     │
│  • Store in ChromaDB with metadata                       │
│  • Return: tool metadata                                 │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼ Tool Registered!
┌─────────────────────────────────────────────────────────┐
│  Orchestrator                                            │
│  • Emit: "synthesis_successful"                          │
│  • Get newly registered tool                             │
│  • Call: executor.execute_tool()                         │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  Tool Executor → Response Synthesizer → User             │
│  • Execute: reverse_string("hello")                      │
│  • Result: "olleh"                                       │
│  • Response: "The reversed string is 'olleh'"            │
└─────────────────────────────────────────────────────────┘
```

## Component Details

### 1. LLM Client (`src/llm_client.py`)

**Purpose**: Unified interface to OpenAI API

**Key Methods**:
- `generate_spec(prompt)` → Structured function specification
- `generate_tests(spec)` → pytest test suite
- `generate_implementation(spec, tests)` → Function code
- `extract_arguments(prompt, signature)` → Parsed parameters
- `synthesize_response(prompt, result)` → Natural language

**Design Patterns**:
- **Wrapper Pattern**: Encapsulates OpenAI API complexity
- **Template Method**: Consistent prompt engineering

### 2. Capability Registry (`src/capability_registry.py`)

**Purpose**: Persistent storage and semantic search for tools

**Key Methods**:
- `add_tool(name, code, tests, docstring)` → Store new tool
- `search_tool(query, threshold)` → Find similar tool
- `get_tool_by_name(name)` → Direct retrieval
- `get_all_tools()` → List all capabilities

**Technology**: 
- ChromaDB for vector storage
- Cosine similarity for matching
- File system for code persistence

**Data Flow**:
```
User Query → Embedding (384-dim vector) → 
ChromaDB Similarity Search → 
Top Match + Similarity Score → 
Load Code from File → 
Return Tool Info
```

### 3. Secure Sandbox (`src/sandbox.py`)

**Purpose**: Isolated execution environment for untrusted code

**Key Methods**:
- `build_image()` → Create Docker image
- `verify_tool(code, tests)` → Run tests safely
- `ensure_image_exists()` → Lazy image building

**Security Features**:
```
Docker Container:
├── Base: python:3.10-slim
├── Network: DISABLED
├── CPU: Limited to 50%
├── Memory: Limited to 256MB
├── Filesystem: Read-only mount
├── Timeout: 30 seconds
└── Lifecycle: Created → Used → Destroyed
```

**Why Docker?**:
- **Isolation**: Complete separation from host
- **Reproducibility**: Consistent environment
- **Security**: No network, limited resources
- **Cleanup**: Automatic container destruction

### 4. Synthesis Engine (`src/synthesis_engine.py`)

**Purpose**: Orchestrate TDD workflow for tool creation

**5-Step Process**:
```
1. Specification  ─┐
2. Tests          ─┤ LLM Client
3. Implementation ─┘
4. Verification   ──→ Sandbox
5. Registration   ──→ Registry
```

**Event Emission**:
Each step emits progress events:
- `synthesis_step` with status: in_progress/complete/failed
- `synthesis_complete` with tool metadata
- `synthesis_error` on failure

**Error Handling**:
- Try-catch at each step
- Detailed error messages
- Step identification for debugging

### 5. Tool Executor (`src/executor.py`)

**Purpose**: Dynamic loading and execution of tools

**Workflow**:
```
Tool Info + User Prompt
    ↓
Extract Function Signature
    ↓
LLM: Parse Prompt → Arguments
    ↓
Dynamic Import (importlib)
    ↓
Call Function(**args)
    ↓
Return Result
```

**Key Features**:
- **Dynamic Loading**: Uses `importlib.util`
- **Retry Logic**: Multiple argument extraction attempts
- **Error Handling**: Catches and reports execution errors

### 6. Response Synthesizer (`src/response_synthesizer.py`)

**Purpose**: Convert tool outputs to natural language

**Methods**:
- `synthesize(prompt, result)` → Normal response
- `synthesize_error(prompt, error)` → Error message
- `synthesize_synthesis_result(...)` → New tool announcement

**Example**:
```
Input:  prompt="What is 15% of 300?", result=45.0
Output: "15 percent of 300 is 45."
```

### 7. Orchestrator (`src/orchestrator.py`)

**Purpose**: Central coordinator and decision maker

**Decision Logic**:
```python
tool = registry.search_tool(prompt)

if tool:
    # Path A: Use existing
    result = executor.execute(tool, prompt)
else:
    # Path B: Synthesize new
    synthesis = synthesis_engine.synthesize(prompt)
    if synthesis.success:
        tool = registry.get_tool(synthesis.name)
        result = executor.execute(tool, prompt)

response = synthesizer.synthesize(prompt, result)
return response
```

**Event Flow**:
All events are emitted via callback for real-time UI updates

## Data Models

### Tool Metadata
```python
{
    "name": "function_name",
    "code": "def function_name(...):\n    ...",
    "file_path": "./tools/function_name.py",
    "test_path": "./tools/test_function_name.py",
    "docstring": "Description...",
    "timestamp": "2025-10-12T15:30:00",
    "similarity_score": 0.89  # Only in search results
}
```

### Function Specification
```python
{
    "function_name": "calculate_percentage",
    "parameters": [
        {"name": "base", "type": "float", "description": "..."},
        {"name": "percentage", "type": "float", "description": "..."}
    ],
    "return_type": "float",
    "docstring": "Detailed documentation..."
}
```

## Configuration Management

**Centralized in `config.py`**:
```python
class Config:
    OPENAI_API_KEY = env("OPENAI_API_KEY")
    OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4")
    SIMILARITY_THRESHOLD = 0.75
    DOCKER_IMAGE_NAME = "self-eng-sandbox"
    DOCKER_TIMEOUT = 30
    CHROMA_PERSIST_DIR = "./chroma_db"
    TOOLS_DIR = "./tools"
```

**Benefits**:
- Single source of truth
- Environment-based configuration
- Type safety and validation
- Easy testing with overrides

## Web Architecture

### Backend (Flask + Socket.IO)

**Endpoints**:
- `GET /` → Serve web interface
- `GET /api/tools` → List all tools (REST)
- WebSocket events:
  - `query` (client → server)
  - `agent_event` (server → client)
  - `query_complete` (server → client)
  - `tool_count` (server → client)

### Frontend (Vanilla JavaScript)

**Real-Time Updates**:
```javascript
socket.on('agent_event', (data) => {
    switch(data.event_type) {
        case 'searching': addLog('info', 'Searching...');
        case 'tool_found': addLog('success', 'Found!');
        case 'synthesis_step': handleSynthesis(data);
        // ... etc
    }
});
```

**UI Components**:
- Query input + examples
- Real-time activity log
- Response display
- Tool library grid
- Status indicators

## Security Architecture

### Threat Model

**Protected Against**:
- ✅ Arbitrary code execution on host
- ✅ Network access from generated code
- ✅ Resource exhaustion (CPU, memory)
- ✅ Persistent filesystem changes
- ✅ Container escape

**How?**:
1. **Docker Isolation**: Separate kernel namespace
2. **Network Disabled**: `network_disabled=True`
3. **Read-Only Mount**: Cannot modify host files
4. **Resource Limits**: CPU quota + memory limit
5. **Immediate Cleanup**: Container destroyed after use
6. **TDD Verification**: All code tested before use

### Trust Boundaries

```
TRUSTED                 BOUNDARY              UNTRUSTED
─────────────────────────────────────────────────────────
User Input     →     Orchestrator     ←    LLM Generated
Registry       →     Sandbox          ←    Tool Code
Executor       →     Docker           ←    Test Code
```

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**: Docker image built only when needed
2. **Caching**: ChromaDB caches embeddings
3. **Async I/O**: Socket.IO for non-blocking updates
4. **Resource Pooling**: Docker client reused
5. **Minimal Images**: Slim Python base (150MB vs 1GB)

### Scalability Points

**Current Limitations**:
- Single-threaded request processing
- Local ChromaDB only
- Synchronous LLM calls

**Future Enhancements**:
- Task queue for parallel synthesis
- Distributed vector DB
- Async LLM client
- Result caching

## Error Handling Strategy

**Layered Approach**:
```
Level 1: Component Try-Catch
    ↓
Level 2: Orchestrator Catch-All
    ↓
Level 3: Flask Error Handlers
    ↓
Level 4: User-Friendly Messages
```

**Error Propagation**:
- Technical errors logged
- User errors synthesized to natural language
- Partial failures handled gracefully

## Testing Strategy

**Unit Tests**: Each component independently
**Integration Tests**: Component interactions
**Verification Tests**: All synthesized tools

**Test Files**:
- `test_installation.py` - Setup verification
- `test_*.py` in tools/ - Tool validation
- Sandbox self-test - Docker functionality

## Conclusion

This architecture demonstrates:
- **Modularity**: Clear separation of concerns
- **Security**: Multiple layers of isolation
- **Extensibility**: Easy to add new components
- **Transparency**: Real-time visibility
- **Robustness**: Comprehensive error handling

The system successfully achieves autonomous capability synthesis while maintaining safety and reliability.

