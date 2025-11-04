# Database Schema Documentation

This document describes the complete Supabase database schema for the Self-Engineering Agent Framework, including all tables, fields, relationships, and indexes.

## Overview

The database consists of seven main tables that support tool management, execution tracking, workflow learning, and conversational memory:

1. **agent_tools** - Tool metadata and embeddings
2. **tool_executions** - Execution logs and analytics
3. **workflow_patterns** - Learned multi-tool sequences
4. **composite_tools** - Promoted workflow patterns
5. **tool_relationships** - Tool co-occurrence patterns
6. **session_messages** - Conversational history
7. **agent_sessions** - Session metadata

---

## Table Schemas

### 1. agent_tools

Stores metadata and embeddings for all synthesized tools.

**Purpose:** Primary tool registry with vector search capabilities

**Schema:**
```sql
CREATE TABLE agent_tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    test_path TEXT NOT NULL,
    docstring TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    embedding VECTOR(1536) NOT NULL
);

-- Vector similarity search index
CREATE INDEX agent_tools_embedding_idx 
ON agent_tools 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Name lookup index
CREATE INDEX agent_tools_name_idx 
ON agent_tools (name);

-- Timestamp index for sorting
CREATE INDEX agent_tools_created_at_idx 
ON agent_tools (created_at DESC);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | TEXT | PRIMARY KEY | Unique identifier (same as name) |
| name | TEXT | NOT NULL, UNIQUE | Function name in snake_case |
| file_path | TEXT | NOT NULL | Absolute path to tool implementation file |
| test_path | TEXT | NOT NULL | Absolute path to test file |
| docstring | TEXT | NOT NULL | Tool description and documentation |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Tool creation timestamp |
| embedding | VECTOR(1536) | NOT NULL | OpenAI text-embedding-3-small vector |

**Indexes:**
- `agent_tools_embedding_idx` - IVFFlat index for fast vector similarity search
- `agent_tools_name_idx` - B-tree index for name lookups
- `agent_tools_created_at_idx` - B-tree index for chronological sorting

**Example Row:**
```json
{
  "id": "calculate_profit_margins",
  "name": "calculate_profit_margins",
  "file_path": "/path/to/tools/calculate_profit_margins.py",
  "test_path": "/path/to/tools/test_calculate_profit_margins.py",
  "docstring": "Calculate profit margins from product cost and price data",
  "created_at": "2025-11-04T19:30:00Z",
  "embedding": [0.023, -0.015, 0.041, ...]
}
```

**Relationships:**
- Referenced by `tool_executions.tool_name`
- Referenced by `composite_tools.component_tools`
- Referenced by `tool_relationships.tool_a` and `tool_relationships.tool_b`

---

### 2. tool_executions

Logs all tool execution attempts with inputs, outputs, and performance metrics.

**Purpose:** Execution tracking, analytics, and pattern mining

**Schema:**
```sql
CREATE TABLE tool_executions (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    tool_name TEXT NOT NULL,
    execution_order INTEGER NOT NULL,
    inputs JSONB,
    outputs JSONB,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    user_prompt TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Session-based queries
CREATE INDEX tool_executions_session_idx 
ON tool_executions (session_id, timestamp DESC);

-- Tool-based analytics
CREATE INDEX tool_executions_tool_idx 
ON tool_executions (tool_name, timestamp DESC);

-- Success rate queries
CREATE INDEX tool_executions_success_idx 
ON tool_executions (tool_name, success);

-- Timestamp for time-series analysis
CREATE INDEX tool_executions_timestamp_idx 
ON tool_executions (timestamp DESC);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing execution ID |
| session_id | TEXT | NULL | Session identifier (NULL for non-session executions) |
| tool_name | TEXT | NOT NULL | Name of executed tool |
| execution_order | INTEGER | NOT NULL | Order in workflow sequence (1-indexed) |
| inputs | JSONB | NULL | Tool input parameters as JSON |
| outputs | JSONB | NULL | Tool execution results as JSON |
| success | BOOLEAN | NOT NULL | Whether execution succeeded |
| execution_time_ms | INTEGER | NOT NULL | Execution duration in milliseconds |
| user_prompt | TEXT | NULL | Original user prompt that triggered execution |
| timestamp | TIMESTAMP | NOT NULL, DEFAULT NOW() | Execution timestamp |

**Indexes:**
- `tool_executions_session_idx` - Composite index for session-based queries
- `tool_executions_tool_idx` - Composite index for tool analytics
- `tool_executions_success_idx` - Composite index for success rate calculations
- `tool_executions_timestamp_idx` - B-tree index for time-series analysis

**Example Row:**
```json
{
  "id": 12345,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "tool_name": "calculate_profit_margins",
  "execution_order": 1,
  "inputs": {"file_path": "data/products.csv"},
  "outputs": {"avg_margin": 42.5, "total_products": 150},
  "success": true,
  "execution_time_ms": 1250,
  "user_prompt": "Calculate profit margins from data/products.csv",
  "timestamp": "2025-11-04T19:30:05Z"
}
```

**Relationships:**
- References `agent_tools.name` via `tool_name` (soft reference)
- References `agent_sessions.session_id` via `session_id` (soft reference)

---

### 3. workflow_patterns

Stores learned multi-tool workflow patterns discovered through pattern mining.

**Purpose:** Workflow pattern recognition and reuse

**Schema:**
```sql
CREATE TABLE workflow_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name TEXT NOT NULL UNIQUE,
    tool_sequence TEXT[] NOT NULL,
    frequency INTEGER NOT NULL DEFAULT 1,
    avg_success_rate FLOAT NOT NULL DEFAULT 0.0,
    confidence_score FLOAT NOT NULL DEFAULT 0.0,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Pattern name lookup
CREATE INDEX workflow_patterns_name_idx 
ON workflow_patterns (pattern_name);

-- Frequency-based queries
CREATE INDEX workflow_patterns_frequency_idx 
ON workflow_patterns (frequency DESC);

-- Vector similarity search
CREATE INDEX workflow_patterns_embedding_idx 
ON workflow_patterns 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing pattern ID |
| pattern_name | TEXT | NOT NULL, UNIQUE | Descriptive pattern name |
| tool_sequence | TEXT[] | NOT NULL | Ordered array of tool names |
| frequency | INTEGER | NOT NULL, DEFAULT 1 | Number of times pattern observed |
| avg_success_rate | FLOAT | NOT NULL, DEFAULT 0.0 | Average success rate (0.0-1.0) |
| confidence_score | FLOAT | NOT NULL, DEFAULT 0.0 | Pattern confidence (0.0-1.0) |
| embedding | VECTOR(1536) | NOT NULL | Pattern description embedding |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Pattern discovery timestamp |
| last_used_at | TIMESTAMP | NULL | Last execution timestamp |

**Indexes:**
- `workflow_patterns_name_idx` - B-tree index for name lookups
- `workflow_patterns_frequency_idx` - B-tree index for popularity sorting
- `workflow_patterns_embedding_idx` - IVFFlat index for semantic search

**Example Row:**
```json
{
  "id": 42,
  "pattern_name": "sales_analysis_workflow",
  "tool_sequence": ["load_csv_data", "calculate_profit_margins", "generate_report"],
  "frequency": 15,
  "avg_success_rate": 0.933,
  "confidence_score": 0.85,
  "embedding": [0.012, -0.034, 0.056, ...],
  "created_at": "2025-11-01T10:00:00Z",
  "last_used_at": "2025-11-04T19:30:00Z"
}
```

**Relationships:**
- Tool names in `tool_sequence` reference `agent_tools.name` (soft reference)
- Can be promoted to `composite_tools`

---

### 4. composite_tools

Stores composite tools created by promoting frequently-used workflow patterns.

**Purpose:** First-class tools composed of multiple sub-tools

**Schema:**
```sql
CREATE TABLE composite_tools (
    id SERIAL PRIMARY KEY,
    tool_name TEXT NOT NULL UNIQUE,
    component_tools TEXT[] NOT NULL,
    docstring TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    usage_count INTEGER NOT NULL DEFAULT 0
);

-- Tool name lookup
CREATE INDEX composite_tools_name_idx 
ON composite_tools (tool_name);

-- Vector similarity search
CREATE INDEX composite_tools_embedding_idx 
ON composite_tools 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- Usage-based sorting
CREATE INDEX composite_tools_usage_idx 
ON composite_tools (usage_count DESC);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing composite tool ID |
| tool_name | TEXT | NOT NULL, UNIQUE | Composite tool name |
| component_tools | TEXT[] | NOT NULL | Ordered array of component tool names |
| docstring | TEXT | NOT NULL | Composite tool description |
| embedding | VECTOR(1536) | NOT NULL | Description embedding for search |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Creation timestamp |
| usage_count | INTEGER | NOT NULL, DEFAULT 0 | Number of times used |

**Indexes:**
- `composite_tools_name_idx` - B-tree index for name lookups
- `composite_tools_embedding_idx` - IVFFlat index for semantic search
- `composite_tools_usage_idx` - B-tree index for popularity sorting

**Example Row:**
```json
{
  "id": 7,
  "tool_name": "analyze_sales_and_report",
  "component_tools": ["load_csv_data", "calculate_profit_margins", "filter_top_products", "generate_summary_report"],
  "docstring": "Complete sales analysis workflow: load data, calculate margins, identify top products, and generate report",
  "embedding": [0.045, -0.023, 0.067, ...],
  "created_at": "2025-11-03T14:20:00Z",
  "usage_count": 8
}
```

**Relationships:**
- Tool names in `component_tools` reference `agent_tools.name` (soft reference)
- Often created from `workflow_patterns`

**Promotion Criteria:**
- Pattern length ≥ 2 tools
- Frequency ≥ 3 occurrences
- Success rate ≥ 80%

---

### 5. tool_relationships

Stores pairwise tool co-occurrence relationships for prediction and recommendation.

**Purpose:** Tool relationship analytics and next-tool prediction

**Schema:**
```sql
CREATE TABLE tool_relationships (
    id SERIAL PRIMARY KEY,
    tool_a TEXT NOT NULL,
    tool_b TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    frequency INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(tool_a, tool_b)
);

-- Tool-based queries
CREATE INDEX tool_relationships_tool_a_idx 
ON tool_relationships (tool_a, confidence_score DESC);

CREATE INDEX tool_relationships_tool_b_idx 
ON tool_relationships (tool_b, confidence_score DESC);

-- Confidence-based filtering
CREATE INDEX tool_relationships_confidence_idx 
ON tool_relationships (confidence_score DESC);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing relationship ID |
| tool_a | TEXT | NOT NULL | First tool in relationship |
| tool_b | TEXT | NOT NULL | Second tool in relationship |
| confidence_score | FLOAT | NOT NULL | Relationship confidence (0.0-1.0) |
| frequency | INTEGER | NOT NULL | Number of co-occurrences |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Relationship discovery timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Constraints:**
- UNIQUE(tool_a, tool_b) - Prevents duplicate relationships

**Indexes:**
- `tool_relationships_tool_a_idx` - Composite index for tool_a queries
- `tool_relationships_tool_b_idx` - Composite index for tool_b queries
- `tool_relationships_confidence_idx` - B-tree index for confidence filtering

**Example Row:**
```json
{
  "id": 123,
  "tool_a": "load_csv_data",
  "tool_b": "calculate_profit_margins",
  "confidence_score": 0.89,
  "frequency": 28,
  "created_at": "2025-10-15T08:00:00Z",
  "updated_at": "2025-11-04T19:30:00Z"
}
```

**Relationships:**
- `tool_a` and `tool_b` reference `agent_tools.name` (soft reference)

**Confidence Score Calculation:**
```python
confidence_score = min(0.95, success_rate * min(1.0, frequency / 10.0))
```

---

### 6. session_messages

Stores conversational message history for each session.

**Purpose:** Conversational context and memory

**Schema:**
```sql
CREATE TABLE session_messages (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, message_index)
);

-- Session-based queries
CREATE INDEX session_messages_session_idx 
ON session_messages (session_id, message_index DESC);

-- Timestamp for cleanup
CREATE INDEX session_messages_created_at_idx 
ON session_messages (created_at);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Auto-incrementing message ID |
| session_id | TEXT | NOT NULL | Session identifier |
| message_index | INTEGER | NOT NULL | Message order in session (0-indexed) |
| role | TEXT | NOT NULL, CHECK | Message role: 'user' or 'assistant' |
| content | TEXT | NOT NULL | Message content |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Message timestamp |

**Constraints:**
- UNIQUE(session_id, message_index) - Ensures message order integrity
- CHECK (role IN ('user', 'assistant')) - Validates role values

**Indexes:**
- `session_messages_session_idx` - Composite index for session queries
- `session_messages_created_at_idx` - B-tree index for cleanup operations

**Example Rows:**
```json
[
  {
    "id": 1001,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_index": 0,
    "role": "user",
    "content": "Calculate profit margins from data/products.csv",
    "created_at": "2025-11-04T19:30:00Z"
  },
  {
    "id": 1002,
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "message_index": 1,
    "role": "assistant",
    "content": "Average margin: 42.5%",
    "created_at": "2025-11-04T19:30:05Z"
  }
]
```

**Relationships:**
- References `agent_sessions.session_id` via `session_id`

---

### 7. agent_sessions

Stores session metadata for tracking active and historical sessions.

**Purpose:** Session lifecycle management

**Schema:**
```sql
CREATE TABLE agent_sessions (
    session_id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_interaction_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Last interaction for cleanup
CREATE INDEX agent_sessions_last_interaction_idx 
ON agent_sessions (last_interaction_at DESC);
```

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| session_id | TEXT | PRIMARY KEY | Unique session identifier (UUID) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Session creation timestamp |
| last_interaction_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last activity timestamp |

**Indexes:**
- `agent_sessions_last_interaction_idx` - B-tree index for cleanup and sorting

**Example Row:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-11-04T19:25:00Z",
  "last_interaction_at": "2025-11-04T19:30:05Z"
}
```

**Relationships:**
- Referenced by `session_messages.session_id`
- Referenced by `tool_executions.session_id`

---

## Entity Relationship Diagram

```
┌─────────────────┐
│  agent_tools    │
│  (Primary)      │
│─────────────────│
│ • id (PK)       │
│ • name (UK)     │
│ • file_path     │
│ • test_path     │
│ • docstring     │
│ • embedding     │
│ • created_at    │
└────────┬────────┘
         │
         │ Referenced by (soft)
         │
    ┌────┴────┬────────────┬──────────────┐
    │         │            │              │
    ▼         ▼            ▼              ▼
┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│tool_executions│  │composite_tools│  │tool_relations│
│───────────────│  │──────────────│  │──────────────│
│• tool_name    │  │• component_  │  │• tool_a      │
│• session_id   │  │  tools[]     │  │• tool_b      │
│• inputs       │  │• tool_name   │  │• confidence  │
│• outputs      │  │• embedding   │  │• frequency   │
│• success      │  └──────────────┘  └──────────────┘
└───────┬───────┘
        │
        │ References
        │
        ▼
┌─────────────────┐
│ agent_sessions  │
│─────────────────│
│• session_id (PK)│
│• created_at     │
│• last_interact  │
└────────┬────────┘
         │
         │ Referenced by
         │
         ▼
┌─────────────────┐
│session_messages │
│─────────────────│
│• session_id     │
│• message_index  │
│• role           │
│• content        │
└─────────────────┘

┌──────────────────┐
│workflow_patterns │
│──────────────────│
│• pattern_name    │
│• tool_sequence[] │
│• frequency       │
│• avg_success_rate│
│• embedding       │
└──────────────────┘
         │
         │ Can be promoted to
         │
         ▼
┌──────────────────┐
│ composite_tools  │
└──────────────────┘
```

---

## Database Functions

### search_tools

RPC function for vector similarity search on agent_tools.

```sql
CREATE OR REPLACE FUNCTION search_tools(
    query_embedding VECTOR(1536),
    similarity_threshold FLOAT DEFAULT 0.4,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    file_path TEXT,
    test_path TEXT,
    docstring TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.name,
        t.file_path,
        t.test_path,
        t.docstring,
        t.created_at,
        1 - (t.embedding <=> query_embedding) AS similarity
    FROM agent_tools t
    WHERE 1 - (t.embedding <=> query_embedding) > similarity_threshold
    ORDER BY t.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

**Usage:**
```sql
SELECT * FROM search_tools(
    query_embedding := '[0.023, -0.015, ...]'::vector,
    similarity_threshold := 0.7,
    match_count := 5
);
```

---

## Maintenance Queries

### Cleanup Old Sessions

Remove sessions inactive for more than 30 days:

```sql
DELETE FROM agent_sessions
WHERE last_interaction_at < NOW() - INTERVAL '30 days';

-- Also cleanup associated messages
DELETE FROM session_messages
WHERE session_id NOT IN (SELECT session_id FROM agent_sessions);
```

### Recalculate Tool Statistics

Update tool success rates and usage counts:

```sql
-- Update composite tool usage counts
UPDATE composite_tools ct
SET usage_count = (
    SELECT COUNT(*)
    FROM tool_executions te
    WHERE te.tool_name = ct.tool_name
);

-- Recalculate workflow pattern success rates
UPDATE workflow_patterns wp
SET avg_success_rate = (
    SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END)
    FROM tool_executions te
    WHERE te.tool_name = ANY(wp.tool_sequence)
);
```

### Rebuild Vector Indexes

Rebuild IVFFlat indexes for optimal performance:

```sql
REINDEX INDEX agent_tools_embedding_idx;
REINDEX INDEX workflow_patterns_embedding_idx;
REINDEX INDEX composite_tools_embedding_idx;
```

---

## Performance Considerations

### Vector Search Optimization

- **IVFFlat Index**: Uses inverted file with flat compression
- **Lists Parameter**: Set to ~sqrt(total_rows) for optimal performance
- **Query Time**: <45ms for 10,000 tools with proper indexing

### Query Patterns

**Fast Queries:**
- Tool lookup by name: O(log n) with B-tree index
- Session messages retrieval: O(log n) with composite index
- Recent executions: O(log n) with timestamp index

**Slower Queries:**
- Vector similarity search: O(n/lists) with IVFFlat index
- Full table scans: O(n) - avoid when possible

### Scaling Recommendations

- **< 1,000 tools**: Default indexes sufficient
- **1,000 - 10,000 tools**: Tune IVFFlat lists parameter
- **> 10,000 tools**: Consider partitioning by created_at
- **High write volume**: Use connection pooling (pgBouncer)

---

## Backup and Recovery

### Backup Strategy

```bash
# Full database backup
pg_dump -h supabase-host -U postgres -d agent_db > backup.sql

# Table-specific backup
pg_dump -h supabase-host -U postgres -d agent_db -t agent_tools > tools_backup.sql

# Vector data backup (binary format for efficiency)
pg_dump -h supabase-host -U postgres -d agent_db -t agent_tools -Fc > tools_backup.dump
```

### Restore

```bash
# Full restore
psql -h supabase-host -U postgres -d agent_db < backup.sql

# Table-specific restore
psql -h supabase-host -U postgres -d agent_db < tools_backup.sql

# Binary restore
pg_restore -h supabase-host -U postgres -d agent_db tools_backup.dump
```

---

## Security Considerations

### Row Level Security (RLS)

Enable RLS for multi-tenant deployments:

```sql
-- Enable RLS on tables
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own sessions
CREATE POLICY session_isolation ON agent_sessions
    FOR ALL
    USING (session_id = current_setting('app.current_session_id'));

CREATE POLICY message_isolation ON session_messages
    FOR ALL
    USING (session_id = current_setting('app.current_session_id'));
```

### Access Control

- **Public Access**: agent_tools (read-only)
- **Authenticated Access**: All other tables
- **Admin Access**: Schema modifications, index management

---

## Migration Scripts

### Initial Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create all tables (see schemas above)
-- Create all indexes (see schemas above)
-- Create RPC functions (see Database Functions section)
```

### Version Upgrades

```sql
-- Example: Add new field to agent_tools
ALTER TABLE agent_tools 
ADD COLUMN tags TEXT[] DEFAULT '{}';

CREATE INDEX agent_tools_tags_idx 
ON agent_tools USING GIN (tags);
```
