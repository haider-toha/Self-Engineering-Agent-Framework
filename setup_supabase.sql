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
