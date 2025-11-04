# Database Schema Documentation

## Overview

The Self-Engineering Agent Framework uses Supabase (PostgreSQL) as its primary database for storing tool metadata, execution logs, workflow patterns, and conversational memory. This document provides comprehensive documentation of all database tables, their fields, relationships, and usage patterns.

## Database Technology

- **Database**: PostgreSQL (via Supabase)
- **Vector Extension**: pgvector for semantic search
- **Indexing**: IVFFlat indexes for approximate nearest neighbor search
- **Embedding Dimensions**: 1536 (OpenAI text-embedding-3-small)

## Table of Contents

1. [agent_tools](#agent_tools)
2. [tool_executions](#tool_executions)
3. [workflow_patterns](#workflow_patterns)
4. [composite_tools](#composite_tools)
5. [tool_relationships](#tool_relationships)
6. [session_messages](#session_messages)
7. [agent_sessions](#agent_sessions)
8. [Relationships and Indexes](#relationships-and-indexes)
9. [Query Examples](#query-examples)

---

## agent_tools

**Purpose**: Stores metadata for all synthesized tools including embeddings for semantic search.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | text | NO | - | Primary key, unique tool identifier (UUID) |
| `name` | text | NO | - | Unique tool name in snake_case format |
| `embedding` | vector(1536) | YES | NULL | 1536-dimensional embedding vector for semantic search |
| `file_path` | text | NO | - | Absolute or relative path to tool source code file |
| `test_path` | text | NO | - | Absolute or relative path to tool test file |
| `docstring` | text | YES | NULL | Tool documentation and description |
| `created_at` | timestamp with time zone | YES | now() | Timestamp when tool was created |

### Constraints

- **Primary Key**: `id`
- **Unique**: `name` (enforces unique tool names)
- **Not Null**: `id`, `name`, `file_path`, `test_path`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX agent_tools_pkey ON agent_tools(id);

-- Unique name index
CREATE UNIQUE INDEX agent_tools_name_key ON agent_tools(name);

-- Vector similarity search index (IVFFlat)
CREATE INDEX agent_tools_embedding_idx ON agent_tools 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Usage

The `agent_tools` table is the central registry for all synthesized tools. Each tool has:
- A unique identifier and name
- An embedding vector for semantic similarity search
- File paths to source code and tests
- Documentation in the docstring field

**Semantic Search Query**:
```sql
SELECT name, docstring, file_path, test_path,
       1 - (embedding <=> query_embedding) AS similarity
FROM agent_tools
WHERE 1 - (embedding <=> query_embedding) > 0.4
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### Example Record

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "calculate_profit_margins",
  "embedding": [0.023, -0.015, 0.042, ...],  // 1536 dimensions
  "file_path": "tools/calculate_profit_margins.py",
  "test_path": "tools/test_calculate_profit_margins.py",
  "docstring": "Calculate profit margins from a CSV file containing product data with price and cost columns",
  "created_at": "2025-11-04T10:30:00.000Z"
}
```

---

## tool_executions

**Purpose**: Logs all tool executions for analytics, pattern mining, and debugging.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NO | auto-increment | Primary key, unique execution identifier |
| `session_id` | text | NO | - | Session identifier (UUID) |
| `tool_name` | text | NO | - | Name of the executed tool |
| `execution_order` | integer | NO | - | Order of execution within the session (1-indexed) |
| `inputs` | jsonb | YES | NULL | Input parameters passed to the tool |
| `outputs` | jsonb | YES | NULL | Output returned by the tool |
| `success` | boolean | NO | - | Whether the execution was successful |
| `execution_time_ms` | integer | YES | NULL | Execution time in milliseconds |
| `timestamp` | timestamp with time zone | YES | now() | When the execution occurred |

### Constraints

- **Primary Key**: `id`
- **Not Null**: `id`, `session_id`, `tool_name`, `execution_order`, `success`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX tool_executions_pkey ON tool_executions(id);

-- Session lookup index
CREATE INDEX tool_executions_session_idx ON tool_executions(session_id);

-- Tool name lookup index
CREATE INDEX tool_executions_tool_name_idx ON tool_executions(tool_name);

-- Timestamp index for time-based queries
CREATE INDEX tool_executions_timestamp_idx ON tool_executions(timestamp DESC);

-- Composite index for session-based queries
CREATE INDEX tool_executions_session_order_idx ON tool_executions(session_id, execution_order);
```

### Usage

The `tool_executions` table logs every tool execution for:
- Workflow pattern mining
- Performance analytics
- Debugging failed executions
- Success rate tracking
- Tool usage statistics

**Pattern Mining Query**:
```sql
SELECT session_id, 
       array_agg(tool_name ORDER BY execution_order) AS tool_sequence,
       COUNT(*) AS frequency
FROM tool_executions
WHERE success = true
  AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY session_id
HAVING COUNT(*) >= 2
ORDER BY frequency DESC;
```

### Example Record

```json
{
  "id": 12345,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "calculate_profit_margins",
  "execution_order": 1,
  "inputs": {
    "csv_path": "data/ecommerce_products.csv"
  },
  "outputs": {
    "average_margin": 23.5,
    "min_margin": 5.2,
    "max_margin": 45.8
  },
  "success": true,
  "execution_time_ms": 145,
  "timestamp": "2025-11-04T10:30:15.000Z"
}
```

---

## workflow_patterns

**Purpose**: Stores learned workflow patterns - sequences of tools that are frequently executed together.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NO | auto-increment | Primary key, unique pattern identifier |
| `pattern_name` | text | NO | - | Descriptive name for the pattern |
| `tool_sequence` | text[] | NO | - | Ordered array of tool names in the pattern |
| `frequency` | integer | NO | - | Number of times this pattern has been observed |
| `avg_success_rate` | double precision | YES | NULL | Average success rate (0.0-1.0) |
| `confidence_score` | double precision | YES | NULL | Confidence score for the pattern (0.0-1.0) |
| `embedding` | vector(1536) | YES | NULL | Embedding vector for semantic pattern matching |
| `created_at` | timestamp with time zone | YES | now() | When the pattern was first detected |
| `updated_at` | timestamp with time zone | YES | now() | When the pattern was last updated |

### Constraints

- **Primary Key**: `id`
- **Unique**: `pattern_name`
- **Not Null**: `id`, `pattern_name`, `tool_sequence`, `frequency`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX workflow_patterns_pkey ON workflow_patterns(id);

-- Unique pattern name index
CREATE UNIQUE INDEX workflow_patterns_name_key ON workflow_patterns(pattern_name);

-- Frequency index for ranking
CREATE INDEX workflow_patterns_frequency_idx ON workflow_patterns(frequency DESC);

-- Vector similarity index
CREATE INDEX workflow_patterns_embedding_idx ON workflow_patterns 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
```

### Usage

The `workflow_patterns` table stores learned multi-tool sequences that can be:
- Reused for similar queries
- Promoted to composite tools
- Analyzed for common workflows

**Pattern Lookup Query**:
```sql
SELECT pattern_name, tool_sequence, frequency, avg_success_rate
FROM workflow_patterns
WHERE frequency >= 3
  AND avg_success_rate >= 0.8
ORDER BY frequency DESC, avg_success_rate DESC
LIMIT 10;
```

### Example Record

```json
{
  "id": 1,
  "pattern_name": "data_analysis_workflow",
  "tool_sequence": ["load_csv_data", "calculate_profit_margins", "generate_report"],
  "frequency": 8,
  "avg_success_rate": 0.95,
  "confidence_score": 0.88,
  "embedding": [0.015, -0.023, 0.038, ...],
  "created_at": "2025-11-01T10:00:00.000Z",
  "updated_at": "2025-11-04T10:30:00.000Z"
}
```

---

## composite_tools

**Purpose**: Stores composite tools - promoted workflow patterns that have become first-class tools.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NO | auto-increment | Primary key, unique composite tool identifier |
| `tool_name` | text | NO | - | Unique name for the composite tool |
| `component_tools` | text[] | NO | - | Ordered array of component tool names |
| `embedding` | vector(1536) | YES | NULL | Embedding vector for semantic search |
| `docstring` | text | YES | NULL | Documentation for the composite tool |
| `created_at` | timestamp with time zone | YES | now() | When the composite tool was created |

### Constraints

- **Primary Key**: `id`
- **Unique**: `tool_name`
- **Not Null**: `id`, `tool_name`, `component_tools`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX composite_tools_pkey ON composite_tools(id);

-- Unique tool name index
CREATE UNIQUE INDEX composite_tools_name_key ON composite_tools(tool_name);

-- Vector similarity index
CREATE INDEX composite_tools_embedding_idx ON composite_tools 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
```

### Usage

Composite tools are created when workflow patterns meet promotion criteria:
- Sequence length ≥ 2 tools
- Frequency ≥ 3 occurrences
- Success rate ≥ 80%

**Composite Tool Search**:
```sql
SELECT tool_name, component_tools, docstring,
       1 - (embedding <=> query_embedding) AS similarity
FROM composite_tools
WHERE 1 - (embedding <=> query_embedding) > 0.7
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### Example Record

```json
{
  "id": 1,
  "tool_name": "analyze_ecommerce_data",
  "component_tools": ["load_csv_data", "calculate_profit_margins", "generate_report"],
  "embedding": [0.018, -0.027, 0.041, ...],
  "docstring": "Complete ecommerce data analysis pipeline: loads CSV data, calculates profit margins, and generates a summary report",
  "created_at": "2025-11-04T10:30:00.000Z"
}
```

---

## tool_relationships

**Purpose**: Stores pairwise tool co-occurrence relationships for predicting likely tool sequences.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NO | auto-increment | Primary key, unique relationship identifier |
| `tool_a` | text | NO | - | First tool in the relationship |
| `tool_b` | text | NO | - | Second tool in the relationship |
| `confidence_score` | double precision | NO | - | Confidence score (0.0-1.0) |
| `frequency` | integer | NO | - | Number of times these tools were used together |
| `created_at` | timestamp with time zone | YES | now() | When the relationship was first detected |
| `updated_at` | timestamp with time zone | YES | now() | When the relationship was last updated |

### Constraints

- **Primary Key**: `id`
- **Unique**: (`tool_a`, `tool_b`) - prevents duplicate relationships
- **Not Null**: `id`, `tool_a`, `tool_b`, `confidence_score`, `frequency`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX tool_relationships_pkey ON tool_relationships(id);

-- Unique pair index
CREATE UNIQUE INDEX tool_relationships_pair_key ON tool_relationships(tool_a, tool_b);

-- Tool A lookup index
CREATE INDEX tool_relationships_tool_a_idx ON tool_relationships(tool_a);

-- Tool B lookup index
CREATE INDEX tool_relationships_tool_b_idx ON tool_relationships(tool_b);

-- Confidence score index
CREATE INDEX tool_relationships_confidence_idx ON tool_relationships(confidence_score DESC);
```

### Usage

Tool relationships help predict likely next tools in a workflow based on historical co-occurrence patterns.

**Relationship Query**:
```sql
SELECT tool_b, confidence_score, frequency
FROM tool_relationships
WHERE tool_a = 'calculate_profit_margins'
  AND confidence_score >= 0.7
ORDER BY confidence_score DESC, frequency DESC
LIMIT 5;
```

### Example Record

```json
{
  "id": 1,
  "tool_a": "calculate_profit_margins",
  "tool_b": "generate_report",
  "confidence_score": 0.85,
  "frequency": 12,
  "created_at": "2025-11-01T10:00:00.000Z",
  "updated_at": "2025-11-04T10:30:00.000Z"
}
```

---

## session_messages

**Purpose**: Stores conversational messages for session-based memory and context.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | bigint | NO | auto-increment | Primary key, unique message identifier |
| `session_id` | text | NO | - | Session identifier (UUID) |
| `message_index` | integer | NO | - | Sequential index of message in session (0-indexed) |
| `role` | text | NO | - | Message role: 'user' or 'assistant' |
| `content` | text | NO | - | Message content |
| `created_at` | timestamp with time zone | YES | now() | When the message was created |

### Constraints

- **Primary Key**: `id`
- **Unique**: (`session_id`, `message_index`) - ensures unique message ordering
- **Not Null**: `id`, `session_id`, `message_index`, `role`, `content`
- **Check**: `role IN ('user', 'assistant')`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX session_messages_pkey ON session_messages(id);

-- Unique session-message index
CREATE UNIQUE INDEX session_messages_session_idx_key ON session_messages(session_id, message_index);

-- Session lookup index
CREATE INDEX session_messages_session_id_idx ON session_messages(session_id);

-- Timestamp index
CREATE INDEX session_messages_timestamp_idx ON session_messages(created_at DESC);
```

### Usage

Session messages maintain conversational context across multiple requests, enabling the agent to:
- Remember previous interactions
- Provide contextual responses
- Build upon previous results

**Recent Messages Query**:
```sql
SELECT role, content, message_index, created_at
FROM session_messages
WHERE session_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY message_index DESC
LIMIT 10;
```

### Example Records

```json
[
  {
    "id": 1,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_index": 0,
    "role": "user",
    "content": "Calculate profit margins from data/ecommerce_products.csv",
    "created_at": "2025-11-04T10:30:00.000Z"
  },
  {
    "id": 2,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_index": 1,
    "role": "assistant",
    "content": "I've calculated the profit margins. The average margin is 23.5%, with a minimum of 5.2% and maximum of 45.8%.",
    "created_at": "2025-11-04T10:30:15.000Z"
  }
]
```

---

## agent_sessions

**Purpose**: Tracks active and historical sessions for session management.

### Schema

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `session_id` | text | NO | - | Primary key, unique session identifier (UUID) |
| `created_at` | timestamp with time zone | YES | now() | When the session was created |
| `last_interaction_at` | timestamp with time zone | YES | now() | When the last interaction occurred |

### Constraints

- **Primary Key**: `session_id`
- **Not Null**: `session_id`

### Indexes

```sql
-- Primary key index
CREATE UNIQUE INDEX agent_sessions_pkey ON agent_sessions(session_id);

-- Last interaction index for cleanup
CREATE INDEX agent_sessions_last_interaction_idx ON agent_sessions(last_interaction_at DESC);
```

### Usage

The `agent_sessions` table tracks all sessions for:
- Session lifecycle management
- Cleanup of stale sessions
- Session analytics

**Active Sessions Query**:
```sql
SELECT session_id, created_at, last_interaction_at
FROM agent_sessions
WHERE last_interaction_at > NOW() - INTERVAL '1 hour'
ORDER BY last_interaction_at DESC;
```

### Example Record

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-04T10:00:00.000Z",
  "last_interaction_at": "2025-11-04T10:30:15.000Z"
}
```

---

## Relationships and Indexes

### Entity Relationship Diagram

```
agent_sessions (1) ──< (N) session_messages
                │
                └──< (N) tool_executions

agent_tools (1) ──< (N) tool_executions
                │
                └──< (N) tool_relationships (via tool_a, tool_b)

workflow_patterns (1) ──< (1) composite_tools (promotion)
```

### Key Relationships

1. **Sessions to Messages**: One session has many messages (1:N)
2. **Sessions to Executions**: One session has many tool executions (1:N)
3. **Tools to Executions**: One tool can be executed many times (1:N)
4. **Tools to Relationships**: Tools participate in many relationships (N:N)
5. **Patterns to Composites**: Patterns can be promoted to composite tools (1:1)

### Vector Indexes

All vector indexes use the IVFFlat algorithm with cosine distance for approximate nearest neighbor search:

```sql
-- IVFFlat parameters
-- lists: Number of clusters (typically sqrt(rows))
-- probe: Number of clusters to search (set at query time)

-- Query example with probe setting
SET ivfflat.probes = 10;
SELECT name FROM agent_tools
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

---

## Query Examples

### 1. Find Similar Tools

```sql
-- Find tools similar to a query embedding
SELECT 
  name,
  docstring,
  1 - (embedding <=> $1::vector) AS similarity
FROM agent_tools
WHERE 1 - (embedding <=> $1::vector) > 0.4
ORDER BY embedding <=> $1::vector
LIMIT 5;
```

### 2. Get Tool Usage Statistics

```sql
-- Get usage statistics for each tool
SELECT 
  tool_name,
  COUNT(*) AS total_executions,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) AS successful_executions,
  ROUND(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END), 2) AS success_rate,
  ROUND(AVG(execution_time_ms), 0) AS avg_execution_time_ms
FROM tool_executions
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY tool_name
ORDER BY total_executions DESC;
```

### 3. Mine Workflow Patterns

```sql
-- Mine workflow patterns from recent executions
SELECT 
  array_agg(tool_name ORDER BY execution_order) AS tool_sequence,
  COUNT(DISTINCT session_id) AS frequency,
  ROUND(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END), 2) AS avg_success_rate
FROM tool_executions
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY session_id
HAVING COUNT(*) >= 2
  AND AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) >= 0.8
ORDER BY frequency DESC
LIMIT 20;
```

### 4. Get Session Conversation History

```sql
-- Get full conversation history for a session
SELECT 
  m.role,
  m.content,
  m.message_index,
  m.created_at,
  s.created_at AS session_started
FROM session_messages m
JOIN agent_sessions s ON m.session_id = s.session_id
WHERE m.session_id = $1
ORDER BY m.message_index ASC;
```

### 5. Find Tool Co-occurrence Patterns

```sql
-- Find tools frequently used together
SELECT 
  tool_a,
  tool_b,
  confidence_score,
  frequency
FROM tool_relationships
WHERE confidence_score >= 0.7
ORDER BY confidence_score DESC, frequency DESC
LIMIT 20;
```

### 6. Identify Composite Tool Candidates

```sql
-- Find workflow patterns eligible for promotion
SELECT 
  pattern_name,
  tool_sequence,
  frequency,
  avg_success_rate,
  confidence_score
FROM workflow_patterns
WHERE array_length(tool_sequence, 1) >= 2
  AND frequency >= 3
  AND avg_success_rate >= 0.8
  AND pattern_name NOT IN (SELECT tool_name FROM composite_tools)
ORDER BY frequency DESC, avg_success_rate DESC;
```

### 7. Session Activity Report

```sql
-- Generate session activity report
SELECT 
  s.session_id,
  s.created_at,
  s.last_interaction_at,
  COUNT(DISTINCT m.id) AS message_count,
  COUNT(DISTINCT e.id) AS execution_count,
  ROUND(AVG(CASE WHEN e.success THEN 1.0 ELSE 0.0 END), 2) AS success_rate
FROM agent_sessions s
LEFT JOIN session_messages m ON s.session_id = m.session_id
LEFT JOIN tool_executions e ON s.session_id = e.session_id
WHERE s.last_interaction_at > NOW() - INTERVAL '24 hours'
GROUP BY s.session_id, s.created_at, s.last_interaction_at
ORDER BY s.last_interaction_at DESC;
```

---

## Database Maintenance

### Cleanup Queries

```sql
-- Remove stale sessions (inactive for 7+ days)
DELETE FROM agent_sessions
WHERE last_interaction_at < NOW() - INTERVAL '7 days';

-- Remove orphaned messages (sessions no longer exist)
DELETE FROM session_messages
WHERE session_id NOT IN (SELECT session_id FROM agent_sessions);

-- Remove old execution logs (older than 90 days)
DELETE FROM tool_executions
WHERE timestamp < NOW() - INTERVAL '90 days';
```

### Performance Optimization

```sql
-- Vacuum and analyze tables
VACUUM ANALYZE agent_tools;
VACUUM ANALYZE tool_executions;
VACUUM ANALYZE workflow_patterns;

-- Reindex vector indexes
REINDEX INDEX agent_tools_embedding_idx;
REINDEX INDEX workflow_patterns_embedding_idx;
REINDEX INDEX composite_tools_embedding_idx;
```

---

## Migration Scripts

### Initial Schema Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create agent_tools table
CREATE TABLE agent_tools (
  id TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  embedding vector(1536),
  file_path TEXT NOT NULL,
  test_path TEXT NOT NULL,
  docstring TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector index
CREATE INDEX agent_tools_embedding_idx ON agent_tools 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create other tables...
-- (See individual table schemas above)
```

---

## Best Practices

1. **Vector Search**: Always set `ivfflat.probes` appropriately for your use case (higher = more accurate but slower)
2. **Indexing**: Ensure all foreign key columns are indexed for join performance
3. **Cleanup**: Regularly clean up old sessions and execution logs to maintain performance
4. **Monitoring**: Monitor vector index performance and rebuild if query times degrade
5. **Backups**: Regular backups of tool metadata and workflow patterns are critical
6. **Embeddings**: Always generate embeddings for new tools, patterns, and composite tools

---

## Additional Resources

- [REST API Documentation](openapi.yaml)
- [WebSocket Events Reference](websocket-events.md)
- [Python API Reference](python-api-reference.md)
- [Integration Guide](integration-guide.md)
- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
