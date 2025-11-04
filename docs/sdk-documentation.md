# SDK Documentation

This document provides comprehensive documentation for developers who want to extend the Self-Engineering Agent Framework. It covers the internal SDK patterns, architecture, and best practices for building custom components.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [LLMClient Usage](#llmclient-usage)
4. [CapabilityRegistry Interactions](#capabilityregistry-interactions)
5. [AgentOrchestrator Lifecycle](#agentorchestrator-lifecycle)
6. [SecureSandbox Execution](#securesandbox-execution)
7. [Custom Tool Development](#custom-tool-development)
8. [Custom Planners](#custom-planners)
9. [Event System](#event-system)
10. [Database Schema](#database-schema)
11. [Best Practices](#best-practices)

---

## Architecture Overview

The Self-Engineering Agent Framework follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Interface Layer                       │
│              (Flask + Socket.IO + React UI)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│         (AgentOrchestrator + QueryPlanner)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Intelligence Layer                          │
│    (LLMClient + CapabilitySynthesisEngine)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Execution Layer                            │
│      (ToolExecutor + SecureSandbox + Docker)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│    (CapabilityRegistry + Supabase + File System)             │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Event-Driven**: Components communicate via callbacks and events
3. **Extensibility**: New components can be added without modifying core logic
4. **Safety**: All user-generated code runs in isolated Docker containers
5. **Observability**: Comprehensive event emission for monitoring

---

## Core Components

### AgentOrchestrator

The central coordinator that manages the entire request lifecycle.

**Location**: `src/orchestrator.py`

**Key Methods**:

```python
class AgentOrchestrator:
    def __init__(self):
        """Initialize all subsystems"""
        self.llm_client = LLMClient()
        self.registry = CapabilityRegistry(self.llm_client)
        self.synthesis_engine = CapabilitySynthesisEngine(
            self.llm_client, 
            self.registry
        )
        self.memory_manager = SessionMemoryManager()
        self.workflow_tracker = WorkflowTracker()
        self.query_planner = QueryPlanner(
            self.llm_client,
            self.registry,
            self.workflow_tracker
        )
        self.composition_planner = CompositionPlanner(
            self.registry,
            self.workflow_tracker,
            self.llm_client
        )
    
    def process_request(
        self,
        user_prompt: str,
        session_id: str,
        callback: Callable = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the complete pipeline
        
        Args:
            user_prompt: Natural language request from user
            session_id: Session identifier for context
            callback: Function to emit progress events
        
        Returns:
            Dict containing success status, response, and metadata
        """
        pass
```

**Usage Example**:

```python
from src.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

def event_callback(event_type, data):
    print(f"[{event_type}] {data}")

result = orchestrator.process_request(
    user_prompt="Calculate profit margins from data/products.csv",
    session_id="550e8400-e29b-41d4-a716-446655440000",
    callback=event_callback
)

if result['success']:
    print(f"Response: {result['response']}")
    print(f"Tool: {result['tool_name']}")
```

---

### QueryPlanner

Analyzes user intent and determines execution strategy.

**Location**: `src/query_planner.py`

**Key Methods**:

```python
class QueryPlanner:
    def plan_execution(self, user_prompt: str) -> Dict[str, Any]:
        """
        Analyze query and determine execution strategy
        
        Returns:
            {
                'strategy': str,  # 'single', 'sequential', 'composition', etc.
                'reasoning': str,
                'sub_tasks': List[str]  # For multi-step workflows
            }
        """
        pass
```

**Extending QueryPlanner**:

```python
from src.query_planner import QueryPlanner

class CustomQueryPlanner(QueryPlanner):
    def plan_execution(self, user_prompt: str) -> Dict[str, Any]:
        # Add custom planning logic
        if "urgent" in user_prompt.lower():
            return {
                'strategy': 'force_synthesis',
                'reasoning': 'Urgent request requires immediate tool creation',
                'sub_tasks': []
            }
        
        # Fall back to default planning
        return super().plan_execution(user_prompt)
```

---

### CompositionPlanner

Executes multi-tool workflows and manages composite tools.

**Location**: `src/composition_planner.py`

**Key Methods**:

```python
class CompositionPlanner:
    def execute_workflow(
        self,
        sub_tasks: List[str],
        user_prompt: str,
        callback: Callable
    ) -> Dict[str, Any]:
        """Execute a multi-step workflow"""
        pass
    
    def execute_pattern(
        self,
        pattern: Dict[str, Any],
        user_prompt: str,
        callback: Callable
    ) -> Dict[str, Any]:
        """Execute a learned workflow pattern"""
        pass
```

---

## LLMClient Usage

The LLMClient wraps OpenAI API calls with specialized prompts for different tasks.

**Location**: `src/llm_client.py`

### Basic Usage

```python
from src.llm_client import LLMClient

llm_client = LLMClient()

# Generate function specification
spec = llm_client.generate_spec(
    "Calculate profit margins from a CSV file"
)

# Generate test suite
tests = llm_client.generate_tests(spec)

# Generate implementation
implementation = llm_client.generate_implementation(spec, tests)

# Generate embedding
embedding = llm_client.generate_embedding(
    "Calculate profit margins"
)

# Extract arguments from natural language
args = llm_client.extract_arguments(
    prompt="Calculate margins for products.csv",
    signature="calculate_profit_margins(csv_path: str) -> dict"
)
```

### Custom LLM Integration

To use a different LLM provider:

```python
from src.llm_client import LLMClient
from typing import Dict, Any

class CustomLLMClient(LLMClient):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    def generate_spec(self, user_prompt: str) -> Dict[str, Any]:
        # Implement custom LLM call
        response = your_llm_api.complete(
            prompt=self._build_spec_prompt(user_prompt),
            model=self.model
        )
        return self._parse_spec_response(response)
    
    def generate_embedding(self, text: str) -> List[float]:
        # Implement custom embedding generation
        return your_embedding_api.embed(text)
```

### Temperature Settings

Different tasks use different temperature settings:

```python
TEMPERATURE_SETTINGS = {
    'specification': 0.2,      # Low for consistency
    'tests': 0.3,              # Slightly higher for variety
    'implementation': 0.2,     # Low for correctness
    'argument_extraction': 0.0, # Zero for determinism
    'response_synthesis': 0.7   # High for natural language
}
```

---

## CapabilityRegistry Interactions

The CapabilityRegistry manages tool storage, indexing, and search.

**Location**: `src/capability_registry.py`

### Adding Tools

```python
from src.capability_registry import CapabilityRegistry
from src.llm_client import LLMClient

llm_client = LLMClient()
registry = CapabilityRegistry(llm_client)

# Add a new tool
tool_id = registry.add_tool(
    name="calculate_profit_margins",
    code="""
def calculate_profit_margins(csv_path: str) -> dict:
    import pandas as pd
    df = pd.read_csv(csv_path)
    df['profit_margin'] = (df['price'] - df['cost']) / df['price']
    return df.to_dict('records')
""",
    tests="""
def test_calculate_profit_margins():
    result = calculate_profit_margins('data/test.csv')
    assert isinstance(result, dict)
""",
    docstring="Calculate profit margins for products in a CSV file"
)
```

### Searching Tools

```python
# Semantic search
results = registry.search_tool(
    query="Calculate profit margins",
    threshold=0.6,
    rerank=True
)

if results:
    best_match = results[0]
    print(f"Found: {best_match['name']}")
    print(f"Similarity: {best_match['similarity']:.2%}")

# Direct lookup
tool = registry.get_tool_by_name("calculate_profit_margins")
if tool:
    print(f"Code: {tool['code']}")
```

### Custom Ranking

```python
from src.capability_registry import CapabilityRegistry

class CustomRegistry(CapabilityRegistry):
    def search_tool(
        self,
        query: str,
        threshold: float = 0.4,
        rerank: bool = True
    ):
        # Get base results
        results = super().search_tool(query, threshold, rerank=False)
        
        # Apply custom ranking
        for result in results:
            # Boost recently used tools
            if self._is_recently_used(result['name']):
                result['similarity'] *= 1.2
            
            # Boost tools with high success rate
            success_rate = self._get_success_rate(result['name'])
            result['similarity'] *= (0.8 + 0.2 * success_rate)
        
        # Re-sort and return
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results
```

---

## AgentOrchestrator Lifecycle

Understanding the request lifecycle is crucial for extending the framework.

### Request Flow

```python
def process_request(self, user_prompt, session_id, callback):
    # 1. Cleanup orphaned tools
    removed = self.registry.cleanup_orphaned_tools()
    
    # 2. Plan execution strategy
    plan = self.query_planner.plan_execution(user_prompt)
    
    # 3. Execute based on strategy
    if plan['strategy'] == 'single':
        result = self._execute_single_tool(user_prompt, callback)
    elif plan['strategy'] == 'sequential':
        result = self.composition_planner.execute_workflow(
            plan['sub_tasks'], user_prompt, callback
        )
    elif plan['strategy'] == 'composite_tool':
        result = self._execute_composite_tool(plan, user_prompt, callback)
    
    # 4. Log execution
    self.workflow_tracker.log_execution(...)
    
    # 5. Save to session memory
    self.memory_manager.append_message(session_id, 'user', user_prompt)
    self.memory_manager.append_message(session_id, 'assistant', result['response'])
    
    # 6. Return result
    return result
```

### Custom Execution Strategies

```python
from src.orchestrator import AgentOrchestrator

class CustomOrchestrator(AgentOrchestrator):
    def process_request(self, user_prompt, session_id, callback):
        # Add pre-processing
        user_prompt = self._preprocess_prompt(user_prompt)
        
        # Add custom strategy
        if self._is_cached_query(user_prompt):
            return self._get_cached_result(user_prompt)
        
        # Fall back to default processing
        return super().process_request(user_prompt, session_id, callback)
    
    def _preprocess_prompt(self, prompt: str) -> str:
        # Add custom preprocessing logic
        return prompt.strip().lower()
    
    def _is_cached_query(self, prompt: str) -> bool:
        # Check if query result is cached
        return prompt in self.cache
    
    def _get_cached_result(self, prompt: str):
        # Return cached result
        return self.cache[prompt]
```

---

## SecureSandbox Execution

All user-generated code runs in isolated Docker containers.

**Location**: `src/sandbox.py`

### Security Layers

1. **Container Isolation**: Kernel-level process isolation
2. **Network Isolation**: No network access (`network_mode='none'`)
3. **Resource Limits**: 512MB RAM, 50% CPU, 30s timeout
4. **Filesystem Restrictions**: Read-only with limited /tmp access
5. **Privilege Dropping**: Non-root user execution

### Using SecureSandbox

```python
from src.sandbox import SecureSandbox

sandbox = SecureSandbox()

# Verify a tool
result = sandbox.verify_tool(
    tool_name="calculate_profit_margins",
    tool_code="""
def calculate_profit_margins(csv_path: str) -> dict:
    import pandas as pd
    df = pd.read_csv(csv_path)
    df['profit_margin'] = (df['price'] - df['cost']) / df['price']
    return df.to_dict('records')
""",
    test_code="""
def test_calculate_profit_margins():
    result = calculate_profit_margins('data/test.csv')
    assert isinstance(result, dict)
"""
)

if result['success']:
    print("Tool verified successfully")
else:
    print(f"Verification failed: {result['error']}")
```

### Custom Sandbox Configuration

```python
from src.sandbox import SecureSandbox

class CustomSandbox(SecureSandbox):
    def __init__(self):
        super().__init__()
        self.timeout = 60  # Increase timeout to 60s
        self.memory_limit = '1g'  # Increase memory to 1GB
    
    def verify_tool(self, tool_name, tool_code, test_code):
        # Add custom verification logic
        if self._is_trusted_tool(tool_name):
            # Skip sandbox for trusted tools
            return self._direct_verification(tool_code, test_code)
        
        # Use sandbox for untrusted tools
        return super().verify_tool(tool_name, tool_code, test_code)
```

---

## Custom Tool Development

### Manual Tool Registration

You can manually register tools without synthesis:

```python
from src.capability_registry import CapabilityRegistry
from src.llm_client import LLMClient

llm_client = LLMClient()
registry = CapabilityRegistry(llm_client)

# Define tool code
tool_code = """
def custom_analysis(data: list) -> dict:
    '''Perform custom analysis on data'''
    total = sum(data)
    average = total / len(data)
    return {'total': total, 'average': average}
"""

# Define tests
test_code = """
def test_custom_analysis():
    result = custom_analysis([1, 2, 3, 4, 5])
    assert result['total'] == 15
    assert result['average'] == 3.0
"""

# Register tool
registry.add_tool(
    name="custom_analysis",
    code=tool_code,
    tests=test_code,
    docstring="Perform custom analysis on data"
)
```

### Tool Templates

Create reusable tool templates:

```python
class ToolTemplate:
    @staticmethod
    def csv_processor(operation: str) -> str:
        return f"""
def process_csv_{operation}(csv_path: str) -> dict:
    '''Process CSV file with {operation} operation'''
    import pandas as pd
    df = pd.read_csv(csv_path)
    # Perform {operation}
    result = df.{operation}()
    return result.to_dict()
"""
    
    @staticmethod
    def api_caller(endpoint: str) -> str:
        return f"""
def call_api_{endpoint}(params: dict) -> dict:
    '''Call API endpoint {endpoint}'''
    import requests
    response = requests.get('{endpoint}', params=params)
    return response.json()
"""

# Usage
tool_code = ToolTemplate.csv_processor("describe")
registry.add_tool("csv_describe", tool_code, tests, docstring)
```

---

## Custom Planners

### Creating a Custom Planner

```python
from src.query_planner import QueryPlanner
from typing import Dict, Any

class DomainSpecificPlanner(QueryPlanner):
    """Planner optimized for specific domain"""
    
    def __init__(self, llm_client, registry, workflow_tracker):
        super().__init__(llm_client, registry, workflow_tracker)
        self.domain_keywords = {
            'finance': ['profit', 'revenue', 'cost', 'margin'],
            'analytics': ['analyze', 'statistics', 'trend', 'correlation'],
            'reporting': ['report', 'summary', 'dashboard', 'visualization']
        }
    
    def plan_execution(self, user_prompt: str) -> Dict[str, Any]:
        # Detect domain
        domain = self._detect_domain(user_prompt)
        
        if domain == 'finance':
            return self._plan_finance_workflow(user_prompt)
        elif domain == 'analytics':
            return self._plan_analytics_workflow(user_prompt)
        elif domain == 'reporting':
            return self._plan_reporting_workflow(user_prompt)
        
        # Fall back to default planning
        return super().plan_execution(user_prompt)
    
    def _detect_domain(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        for domain, keywords in self.domain_keywords.items():
            if any(kw in prompt_lower for kw in keywords):
                return domain
        return 'general'
    
    def _plan_finance_workflow(self, prompt: str) -> Dict[str, Any]:
        return {
            'strategy': 'sequential',
            'reasoning': 'Finance workflow detected',
            'sub_tasks': [
                'Load financial data',
                'Calculate financial metrics',
                'Generate financial report'
            ]
        }
```

---

## Event System

The framework uses a callback-based event system for real-time updates.

### Event Emission Pattern

```python
def emit(event_type: str, data: Any = None):
    """Helper to emit events via callback"""
    if callback:
        callback(event_type, data or {})

# Emit events at key points
emit("searching", {"query": user_prompt})
emit("tool_found", {"tool_name": tool['name'], "similarity": 0.92})
emit("executing", {"tool_name": tool['name']})
emit("execution_complete", {"result": result})
```

### Custom Event Handlers

```python
class EventLogger:
    def __init__(self):
        self.events = []
    
    def __call__(self, event_type: str, data: dict):
        self.events.append({
            'timestamp': time.time(),
            'type': event_type,
            'data': data
        })
        
        # Custom handling
        if event_type == 'synthesis_failed':
            self._handle_synthesis_failure(data)
        elif event_type == 'execution_failed':
            self._handle_execution_failure(data)
    
    def _handle_synthesis_failure(self, data):
        # Log to external monitoring system
        print(f"ALERT: Synthesis failed - {data['error']}")
    
    def _handle_execution_failure(self, data):
        # Retry logic
        print(f"Retrying execution after failure: {data['error']}")

# Usage
logger = EventLogger()
orchestrator.process_request(prompt, session_id, callback=logger)
```

---

## Database Schema

### Supabase Tables

**agent_tools**:
```sql
CREATE TABLE agent_tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    embedding VECTOR(1536),
    file_path TEXT,
    test_path TEXT,
    docstring TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON agent_tools USING ivfflat (embedding vector_cosine_ops);
```

**tool_executions**:
```sql
CREATE TABLE tool_executions (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    tool_name TEXT,
    execution_order INTEGER,
    inputs JSONB,
    outputs JSONB,
    success BOOLEAN,
    execution_time_ms INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

**workflow_patterns**:
```sql
CREATE TABLE workflow_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name TEXT,
    tool_sequence TEXT[],
    frequency INTEGER,
    avg_success_rate FLOAT,
    confidence_score FLOAT,
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Custom Database Operations

```python
from src.capability_registry import CapabilityRegistry

class ExtendedRegistry(CapabilityRegistry):
    def get_tools_by_category(self, category: str):
        """Get tools filtered by category"""
        response = self.supabase.table('agent_tools') \
            .select('*') \
            .eq('category', category) \
            .execute()
        return response.data
    
    def get_tool_usage_stats(self, tool_name: str):
        """Get usage statistics for a tool"""
        response = self.supabase.table('tool_executions') \
            .select('*') \
            .eq('tool_name', tool_name) \
            .execute()
        
        executions = response.data
        total = len(executions)
        successful = sum(1 for e in executions if e['success'])
        
        return {
            'total_executions': total,
            'success_rate': successful / total if total > 0 else 0,
            'avg_execution_time': sum(e['execution_time_ms'] for e in executions) / total
        }
```

---

## Best Practices

### 1. Error Handling

Always implement comprehensive error handling:

```python
try:
    result = orchestrator.process_request(prompt, session_id, callback)
except ConnectionError as e:
    logger.error(f"Database connection failed: {e}")
    # Implement fallback logic
except TimeoutError as e:
    logger.error(f"Request timeout: {e}")
    # Implement retry logic
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Implement graceful degradation
```

### 2. Resource Management

Clean up resources properly:

```python
class ManagedOrchestrator:
    def __enter__(self):
        self.orchestrator = AgentOrchestrator()
        return self.orchestrator
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup resources
        self.orchestrator.cleanup()

# Usage
with ManagedOrchestrator() as orchestrator:
    result = orchestrator.process_request(prompt, session_id)
```

### 3. Logging

Implement structured logging:

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_request(prompt, session_id, result):
    logger.info(json.dumps({
        'event': 'request_processed',
        'prompt': prompt,
        'session_id': session_id,
        'success': result['success'],
        'tool_name': result.get('tool_name'),
        'synthesized': result.get('synthesized', False)
    }))
```

### 4. Testing

Write comprehensive tests for custom components:

```python
import pytest
from src.orchestrator import AgentOrchestrator

def test_custom_planner():
    orchestrator = AgentOrchestrator()
    
    result = orchestrator.process_request(
        user_prompt="Calculate profit margins",
        session_id="test-session",
        callback=None
    )
    
    assert result['success']
    assert result['tool_name'] is not None

def test_error_handling():
    orchestrator = AgentOrchestrator()
    
    result = orchestrator.process_request(
        user_prompt="",  # Invalid prompt
        session_id="test-session",
        callback=None
    )
    
    assert not result['success']
```

### 5. Performance Optimization

Cache frequently accessed data:

```python
from functools import lru_cache

class OptimizedRegistry(CapabilityRegistry):
    @lru_cache(maxsize=100)
    def get_tool_by_name(self, name: str):
        return super().get_tool_by_name(name)
    
    def add_tool(self, name, code, tests, docstring):
        # Clear cache when adding new tool
        self.get_tool_by_name.cache_clear()
        return super().add_tool(name, code, tests, docstring)
```

### 6. Monitoring

Implement metrics collection:

```python
from prometheus_client import Counter, Histogram

request_counter = Counter('agent_requests_total', 'Total requests')
request_duration = Histogram('agent_request_duration_seconds', 'Request duration')

class MonitoredOrchestrator(AgentOrchestrator):
    def process_request(self, user_prompt, session_id, callback):
        request_counter.inc()
        
        with request_duration.time():
            result = super().process_request(user_prompt, session_id, callback)
        
        return result
```

---

## Summary

This SDK documentation covers:

1. **Architecture**: Layered design with clear separation of concerns
2. **Core Components**: AgentOrchestrator, QueryPlanner, CompositionPlanner
3. **LLMClient**: Wrapper for LLM interactions with custom provider support
4. **CapabilityRegistry**: Tool storage, indexing, and semantic search
5. **SecureSandbox**: Isolated execution environment with multiple security layers
6. **Custom Development**: Extending planners, tools, and execution strategies
7. **Event System**: Callback-based real-time updates
8. **Database**: Supabase schema and custom operations
9. **Best Practices**: Error handling, resource management, testing, monitoring

For more information, see:
- [Integration Guide](./integration-guide.md)
- [Code Examples](./code-examples.md)
- [API Reference](./openapi.yaml)
