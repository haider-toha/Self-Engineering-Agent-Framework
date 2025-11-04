# API Documentation

Welcome to the Self-Engineering Agent Framework API documentation. This directory contains comprehensive documentation for developers integrating with or extending the framework.

## Documentation Overview

This documentation suite provides everything you need to understand, integrate with, and extend the Self-Engineering Agent Framework.

### Quick Links

- **[OpenAPI Specification](openapi.yaml)** - Complete REST API reference in OpenAPI 3.0 format
- **[WebSocket Events Reference](websocket-events.md)** - Real-time bidirectional communication events
- **[Python API Reference](python-api-reference.md)** - Core module documentation
- **[Integration Guide](integration-guide.md)** - Complete integration examples and workflows
- **[SDK Examples](sdk-examples.md)** - Client libraries in Python, JavaScript, and cURL
- **[Database Schema](database-schema.md)** - Supabase table structures and relationships
- **[Authentication & Security](authentication-and-security.md)** - Security best practices and authentication

### Interactive Documentation

The framework includes an interactive API documentation UI powered by Swagger UI:

**Access at**: [http://localhost:5001/api/docs](http://localhost:5001/api/docs)

The interactive UI allows you to:
- Explore all REST API endpoints
- View request/response schemas
- Try out API calls directly from your browser
- See example payloads and responses
- Download the OpenAPI specification

## Getting Started

### For End Users

If you're using the web interface:

1. Start the Flask server: `python web/app.py`
2. Open your browser to [http://localhost:5001](http://localhost:5001)
3. Start a session and submit queries
4. The agent will synthesize tools or reuse existing ones automatically

### For Developers

If you're building a custom client or integration:

1. **Read the [Integration Guide](integration-guide.md)** - Start here for complete examples
2. **Review the [OpenAPI Specification](openapi-yaml)** - Understand the REST API
3. **Study the [WebSocket Events](websocket-events.md)** - Learn real-time communication
4. **Explore [SDK Examples](sdk-examples.md)** - See client implementations
5. **Check [Authentication & Security](authentication-and-security.md)** - Secure your deployment

### Quick Start Example

```python
import requests
import socketio

# Create a session
response = requests.post('http://localhost:5001/api/session')
session_id = response.json()['session_id']

# Connect to WebSocket
sio = socketio.Client()
sio.connect('http://localhost:5001')

# Handle events
@sio.on('agent_event')
def on_event(data):
    print(f"[{data['type']}] {data['message']}")

@sio.on('query_complete')
def on_complete(data):
    print(f"Result: {data['result']}")
    sio.disconnect()

# Submit a query
sio.emit('query', {
    'session_id': session_id,
    'prompt': 'Calculate profit margins from data/ecommerce_products.csv'
})

sio.wait()
```

## Documentation Structure

### 1. OpenAPI Specification (`openapi.yaml`)

**Format**: OpenAPI 3.0 (YAML)  
**Purpose**: Machine-readable REST API specification

**Contents**:
- 6 REST endpoints with complete schemas
- Request/response examples
- Authentication requirements
- Error response formats
- Component schemas for reuse

**Use Cases**:
- Generate client SDKs with tools like OpenAPI Generator
- Import into API testing tools (Postman, Insomnia)
- Validate API requests/responses
- Auto-generate documentation

### 2. WebSocket Events Reference (`websocket-events.md`)

**Format**: Markdown  
**Purpose**: Complete Socket.IO event catalog

**Contents**:
- Connection lifecycle events
- Client-to-server events (query submission)
- Server-to-client events (30+ agent lifecycle events)
- Event payload schemas
- Client handling examples

**Use Cases**:
- Build real-time clients
- Understand agent execution flow
- Implement progress tracking
- Debug WebSocket communication

### 3. Python API Reference (`python-api-reference.md`)

**Format**: Markdown  
**Purpose**: Core module documentation

**Contents**:
- 8 core modules fully documented
- Method signatures with type hints
- Parameter descriptions
- Return value documentation
- Usage examples for each module

**Modules Covered**:
- `AgentOrchestrator` - Central coordinator
- `CapabilitySynthesisEngine` - Tool synthesis
- `CapabilityRegistry` - Tool storage and search
- `QueryPlanner` - Strategy selection
- `CompositionPlanner` - Multi-tool workflows
- `LLMClient` - OpenAI API wrapper
- `WorkflowTracker` - Execution logging
- `SessionMemoryManager` - Conversational memory

**Use Cases**:
- Extend the framework
- Understand internal architecture
- Debug issues
- Contribute to the project

### 4. Integration Guide (`integration-guide.md`)

**Format**: Markdown  
**Purpose**: Complete integration examples

**Contents**:
- Quick start guide
- Session management
- REST API usage examples
- WebSocket integration patterns
- Tool retrieval workflows
- Custom client development
- Common workflow examples
- Error handling strategies
- Best practices

**Use Cases**:
- Build custom clients
- Integrate with existing systems
- Implement specific workflows
- Learn by example

### 5. SDK Examples (`sdk-examples.md`)

**Format**: Markdown  
**Purpose**: Client library implementations

**Contents**:
- Complete Python SDK with `AgentClient` class
- Complete JavaScript SDK with `AgentClient` class
- cURL examples for all endpoints
- Workflow automation scripts
- Common usage patterns

**Use Cases**:
- Copy-paste working code
- Understand client patterns
- Build SDKs in other languages
- Automate workflows

### 6. Database Schema (`database-schema.md`)

**Format**: Markdown  
**Purpose**: Supabase database documentation

**Contents**:
- 7 table schemas with field descriptions
- Indexes and constraints
- Relationships and foreign keys
- Query examples
- Maintenance procedures
- Migration scripts

**Tables Documented**:
- `agent_tools` - Tool metadata and embeddings
- `tool_executions` - Execution logs
- `workflow_patterns` - Learned sequences
- `composite_tools` - Promoted patterns
- `tool_relationships` - Co-occurrence patterns
- `session_messages` - Conversation history
- `agent_sessions` - Session tracking

**Use Cases**:
- Understand data model
- Write custom queries
- Build analytics dashboards
- Perform database maintenance

### 7. Authentication & Security (`authentication-and-security.md`)

**Format**: Markdown  
**Purpose**: Security best practices

**Contents**:
- Current authentication model (development mode)
- Environment variables and credentials
- Production authentication recommendations (API keys, JWT, OAuth)
- Rate limiting implementation
- Security best practices (HTTPS, CORS, input validation)
- Docker sandbox security layers
- API security headers
- Security checklist

**Use Cases**:
- Secure production deployments
- Implement authentication
- Configure rate limiting
- Follow security best practices

## API Overview

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session` | POST | Create a new session |
| `/api/session/<session_id>/messages` | GET | Get conversation history |
| `/api/tools` | GET | List all available tools |
| `/api/tools/<tool_name>` | GET | Get tool details |
| `/api/analytics/patterns` | GET | Get workflow patterns |
| `/api/analytics/relationships` | GET | Get tool relationships |

**Base URL**: `http://localhost:5001`

### WebSocket Events

**Connection**: `ws://localhost:5001`

**Client → Server**:
- `query` - Submit a query for processing

**Server → Client**:
- `agent_event` - General agent lifecycle events
- `query_complete` - Query processing finished
- `tool_count` - Available tool count
- `session_memory` - Session context update
- `error` - Error occurred

### Authentication

**Current**: No authentication required (development mode)

**Production**: See [Authentication & Security](authentication-and-security.md) for:
- API key authentication
- JWT tokens
- OAuth 2.0 integration
- Rate limiting

## Common Use Cases

### 1. Building a Custom Web Client

**Steps**:
1. Create a session via REST API
2. Connect to WebSocket with session ID
3. Listen for `agent_event` and `query_complete` events
4. Submit queries via `query` event
5. Display results and maintain conversation history

**Example**: See [Integration Guide - Custom Client](integration-guide.md#building-custom-clients)

### 2. Automating Workflows

**Steps**:
1. Create a session
2. Submit multiple queries in sequence
3. Parse results and use in subsequent queries
4. Retrieve analytics data

**Example**: See [SDK Examples - Workflow Automation](sdk-examples.md#complete-workflow-example)

### 3. Building an Analytics Dashboard

**Steps**:
1. Query `/api/analytics/patterns` for workflow patterns
2. Query `/api/analytics/relationships` for tool relationships
3. Query tool execution logs from database
4. Visualize patterns and usage statistics

**Example**: See [Integration Guide - Analytics Dashboard](integration-guide.md#analytics-dashboard-example)

### 4. Extending the Framework

**Steps**:
1. Study [Python API Reference](python-api-reference.md)
2. Understand module responsibilities
3. Implement custom components
4. Register with orchestrator

**Example**: See [Python API Reference - Extension Points](python-api-reference.md)

## Development Workflow

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start the server
python web/app.py

# Access the UI
open http://localhost:5001

# Access API docs
open http://localhost:5001/api/docs
```

### Testing API Endpoints

**Using cURL**:
```bash
# Create session
curl -X POST http://localhost:5001/api/session

# Get tools
curl http://localhost:5001/api/tools

# Get tool details
curl http://localhost:5001/api/tools/calculate_profit_margins
```

**Using Python**:
```python
import requests

# Create session
response = requests.post('http://localhost:5001/api/session')
session_id = response.json()['session_id']

# Get tools
tools = requests.get('http://localhost:5001/api/tools').json()
print(f"Available tools: {len(tools['tools'])}")
```

**Using JavaScript**:
```javascript
// Create session
const response = await fetch('http://localhost:5001/api/session', {
  method: 'POST'
});
const { session_id } = await response.json();

// Get tools
const toolsResponse = await fetch('http://localhost:5001/api/tools');
const { tools } = await toolsResponse.json();
console.log(`Available tools: ${tools.length}`);
```

### Testing WebSocket Events

**Using Python**:
```python
import socketio

sio = socketio.Client()
sio.connect('http://localhost:5001')

@sio.on('agent_event')
def on_event(data):
    print(f"Event: {data}")

sio.emit('query', {
    'session_id': 'your-session-id',
    'prompt': 'Your query here'
})

sio.wait()
```

**Using JavaScript**:
```javascript
const socket = io('http://localhost:5001');

socket.on('agent_event', (data) => {
  console.log('Event:', data);
});

socket.emit('query', {
  session_id: 'your-session-id',
  prompt: 'Your query here'
});
```

## Architecture Overview

### Request Flow

```
User Request
    ↓
REST API / WebSocket
    ↓
AgentOrchestrator
    ↓
QueryPlanner (strategy selection)
    ↓
┌─────────────────────────────────┐
│  Semantic Search                │
│  ↓                              │
│  Tool Found? → Execute          │
│  ↓                              │
│  Not Found → Synthesize         │
│      ↓                          │
│      Specification              │
│      ↓                          │
│      Tests                      │
│      ↓                          │
│      Implementation             │
│      ↓                          │
│      Verification (Docker)      │
│      ↓                          │
│      Registration               │
│      ↓                          │
│      Execute                    │
└─────────────────────────────────┘
    ↓
Result Processing
    ↓
Response to User
    ↓
Update Memory & Logs
```

### Key Components

- **AgentOrchestrator**: Central coordinator
- **QueryPlanner**: Strategy selection
- **CapabilityRegistry**: Tool storage and search
- **CapabilitySynthesisEngine**: Tool creation
- **CompositionPlanner**: Multi-tool workflows
- **SessionMemoryManager**: Conversational context
- **WorkflowTracker**: Learning and analytics

## Troubleshooting

### Common Issues

**Issue**: "Connection refused" when connecting to WebSocket  
**Solution**: Ensure Flask server is running on port 5001

**Issue**: "No tools found" in semantic search  
**Solution**: Check Supabase connection and ensure tools are registered

**Issue**: "Docker timeout" during tool synthesis  
**Solution**: Increase `DOCKER_TIMEOUT` in config.py or optimize generated code

**Issue**: "OpenAI API error"  
**Solution**: Verify `OPENAI_API_KEY` is set correctly in .env file

**Issue**: "Session not found"  
**Solution**: Create a new session via `/api/session` endpoint

### Debug Mode

Enable debug logging:
```python
# In config.py
FLASK_DEBUG = True

# In web/app.py
app.logger.setLevel(logging.DEBUG)
```

### Database Queries

Check tool count:
```sql
SELECT COUNT(*) FROM agent_tools;
```

Check recent executions:
```sql
SELECT * FROM tool_executions 
ORDER BY timestamp DESC 
LIMIT 10;
```

Check active sessions:
```sql
SELECT * FROM agent_sessions 
WHERE last_interaction_at > NOW() - INTERVAL '1 hour';
```

## Contributing

### Documentation Updates

To update documentation:

1. Edit the relevant Markdown file
2. Ensure examples are tested and working
3. Update this README if adding new documentation
4. Submit a pull request

### API Changes

When making API changes:

1. Update `openapi.yaml` with new endpoints/schemas
2. Update relevant documentation files
3. Add examples to integration guide
4. Update SDK examples if needed
5. Test with interactive Swagger UI

## Additional Resources

### External Documentation

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Socket.IO Documentation](https://socket.io/docs/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Supabase Documentation](https://supabase.com/docs)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Docker Documentation](https://docs.docker.com/)

### Related Projects

- [LangChain](https://github.com/langchain-ai/langchain) - Traditional agent framework
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - Autonomous GPT-4
- [BabyAGI](https://github.com/yoheinakajima/babyagi) - Task-driven autonomous agent

## Support

For questions, issues, or contributions:

- **GitHub Issues**: [haider-toha/Self-Engineering-Agent-Framework/issues](https://github.com/haider-toha/Self-Engineering-Agent-Framework/issues)
- **Main README**: [../README.md](../README.md)
- **Project Repository**: [https://github.com/haider-toha/Self-Engineering-Agent-Framework](https://github.com/haider-toha/Self-Engineering-Agent-Framework)

---

**Last Updated**: November 2025  
**Version**: 1.0.0  
**Maintained By**: Self-Engineering Agent Framework Team
