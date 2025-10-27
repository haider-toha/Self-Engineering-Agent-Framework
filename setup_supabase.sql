-- Setup SQL for Supabase database
-- Run this in your Supabase SQL editor

-- Enable the pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the agent_tools table
CREATE TABLE IF NOT EXISTS agent_tools (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    test_path TEXT NOT NULL,
    docstring TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    embedding VECTOR(1536)  -- 1536 dimensions for OpenAI text-embedding-3-small model
);

-- Create an index for vector similarity search
CREATE INDEX IF NOT EXISTS agent_tools_embedding_idx 
ON agent_tools USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create a function to search for similar tools
CREATE OR REPLACE FUNCTION search_tools(
    query_embedding VECTOR(1536),
    similarity_threshold FLOAT DEFAULT 0.4,
    match_count INT DEFAULT 1
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    file_path TEXT,
    test_path TEXT,    
    docstring TEXT,
    created_at TIMESTAMP,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        id,
        name,
        file_path,
        test_path,
        docstring,
        created_at,
        1 - (embedding <=> query_embedding) AS similarity
    FROM agent_tools
    WHERE 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

-- Create Row Level Security policies (adjust as needed)
ALTER TABLE agent_tools ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (you can make this more restrictive)
CREATE POLICY "Allow all operations for authenticated users" ON agent_tools
    FOR ALL USING (auth.role() = 'authenticated');

-- Allow read access for anonymous users (optional, remove if you don't want this)
CREATE POLICY "Allow read access for anonymous users" ON agent_tools
    FOR SELECT USING (true);

-- ============================================================================
-- WORKFLOW TRACKING & COMPOSITION TABLES
-- ============================================================================

-- Table to track individual tool executions
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    execution_order INTEGER NOT NULL,
    inputs JSONB,
    outputs JSONB,
    success BOOLEAN NOT NULL,
    error_details TEXT,
    execution_time_ms INTEGER,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    user_prompt TEXT,
    FOREIGN KEY (tool_name) REFERENCES agent_tools(name) ON DELETE CASCADE
);

-- Index for session-based queries
CREATE INDEX IF NOT EXISTS tool_executions_session_idx ON tool_executions(session_id, execution_order);
CREATE INDEX IF NOT EXISTS tool_executions_timestamp_idx ON tool_executions(timestamp DESC);
CREATE INDEX IF NOT EXISTS tool_executions_tool_idx ON tool_executions(tool_name);

-- Table to store learned relationships between tools
CREATE TABLE IF NOT EXISTS tool_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_a TEXT NOT NULL,
    tool_b TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- 'sequence', 'composition', 'alternative'
    frequency_count INTEGER DEFAULT 1,
    success_rate FLOAT DEFAULT 1.0,
    confidence_score FLOAT DEFAULT 0.5,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,
    UNIQUE(tool_a, tool_b, relationship_type)
);

-- Index for relationship queries
CREATE INDEX IF NOT EXISTS tool_relationships_tool_a_idx ON tool_relationships(tool_a);
CREATE INDEX IF NOT EXISTS tool_relationships_tool_b_idx ON tool_relationships(tool_b);
CREATE INDEX IF NOT EXISTS tool_relationships_confidence_idx ON tool_relationships(confidence_score DESC);

-- Table to store detected workflow patterns
CREATE TABLE IF NOT EXISTS workflow_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name TEXT UNIQUE NOT NULL,
    tool_sequence TEXT[] NOT NULL, -- Array of tool names in order
    frequency INTEGER DEFAULT 1,
    avg_success_rate FLOAT DEFAULT 1.0,
    user_sessions TEXT[] DEFAULT '{}', -- Sessions where this pattern occurred
    complexity_score INTEGER, -- Number of steps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    embedding VECTOR(1536), -- For pattern similarity search
    description TEXT
);

-- Index for pattern queries
CREATE INDEX IF NOT EXISTS workflow_patterns_frequency_idx ON workflow_patterns(frequency DESC);
CREATE INDEX IF NOT EXISTS workflow_patterns_embedding_idx 
ON workflow_patterns USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 50);

-- Table to store composite tools
CREATE TABLE IF NOT EXISTS composite_tools (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    component_tools TEXT[] NOT NULL, -- Array of tool names used
    workflow_template JSONB NOT NULL, -- Execution plan with data flow
    success_rate FLOAT DEFAULT 1.0,
    usage_count INTEGER DEFAULT 0,
    auto_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used TIMESTAMP,
    file_path TEXT NOT NULL,
    test_path TEXT NOT NULL,
    docstring TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB
);

-- Index for composite tool queries
CREATE INDEX IF NOT EXISTS composite_tools_embedding_idx 
ON composite_tools USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 50);
CREATE INDEX IF NOT EXISTS composite_tools_usage_idx ON composite_tools(usage_count DESC);

-- Function to search for similar workflow patterns
CREATE OR REPLACE FUNCTION search_workflow_patterns(
    query_embedding VECTOR(1536),
    similarity_threshold FLOAT DEFAULT 0.6,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    pattern_name TEXT,
    tool_sequence TEXT[],
    frequency INTEGER,
    avg_success_rate FLOAT,
    complexity_score INTEGER,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        id,
        pattern_name,
        tool_sequence,
        frequency,
        avg_success_rate,
        complexity_score,
        1 - (embedding <=> query_embedding) AS similarity
    FROM workflow_patterns
    WHERE embedding IS NOT NULL
        AND 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

-- Function to search for composite tools
CREATE OR REPLACE FUNCTION search_composite_tools(
    query_embedding VECTOR(1536),
    similarity_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    component_tools TEXT[],
    success_rate FLOAT,
    usage_count INTEGER,
    similarity FLOAT
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        id,
        name,
        component_tools,
        success_rate,
        usage_count,
        1 - (embedding <=> query_embedding) AS similarity
    FROM composite_tools
    WHERE embedding IS NOT NULL
        AND 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding ASC
    LIMIT match_count;
$$;

-- Function to update tool relationships
CREATE OR REPLACE FUNCTION update_tool_relationship(
    p_tool_a TEXT,
    p_tool_b TEXT,
    p_relationship_type TEXT,
    p_success BOOLEAN
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    current_frequency INTEGER;
    current_success_count FLOAT;
BEGIN
    -- Insert or update the relationship
    INSERT INTO tool_relationships (tool_a, tool_b, relationship_type, frequency_count, success_rate)
    VALUES (p_tool_a, p_tool_b, p_relationship_type, 1, CASE WHEN p_success THEN 1.0 ELSE 0.0 END)
    ON CONFLICT (tool_a, tool_b, relationship_type) 
    DO UPDATE SET
        frequency_count = tool_relationships.frequency_count + 1,
        success_rate = (
            (tool_relationships.success_rate * tool_relationships.frequency_count) + 
            CASE WHEN p_success THEN 1.0 ELSE 0.0 END
        ) / (tool_relationships.frequency_count + 1),
        confidence_score = LEAST(1.0, (tool_relationships.frequency_count + 1) / 10.0),
        last_updated = NOW();
END;
$$;

-- Enable RLS on new tables
ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE composite_tools ENABLE ROW LEVEL SECURITY;

-- Policies for tool_executions
CREATE POLICY "Allow all operations for authenticated users" ON tool_executions
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow read access for anonymous users" ON tool_executions
    FOR SELECT USING (true);

-- Policies for tool_relationships
CREATE POLICY "Allow all operations for authenticated users" ON tool_relationships
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow read access for anonymous users" ON tool_relationships
    FOR SELECT USING (true);

-- Policies for workflow_patterns
CREATE POLICY "Allow all operations for authenticated users" ON workflow_patterns
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow read access for anonymous users" ON workflow_patterns
    FOR SELECT USING (true);

-- Policies for composite_tools
CREATE POLICY "Allow all operations for authenticated users" ON composite_tools
    FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow read access for anonymous users" ON composite_tools
    FOR SELECT USING (true);