-- Create extension for UUIDs and random UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================================
-- 1. agent_tools
-- =====================================================================
CREATE TABLE public.agent_tools (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  file_path TEXT NOT NULL,
  test_path TEXT NOT NULL,
  docstring TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  embedding BYTEA, -- replaced USER-DEFINED with BYTEA (for embeddings)
  metadata JSONB
);

-- =====================================================================
-- 2. tool_executions
-- =====================================================================
CREATE TABLE public.tool_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  execution_order INTEGER NOT NULL,
  inputs JSONB,
  outputs JSONB,
  success BOOLEAN NOT NULL,
  error_details TEXT,
  execution_time_ms INTEGER,
  timestamp TIMESTAMP NOT NULL DEFAULT now(),
  user_prompt TEXT,
  CONSTRAINT tool_executions_tool_name_fkey FOREIGN KEY (tool_name)
    REFERENCES public.agent_tools(name)
);

-- =====================================================================
-- 3. workflow_patterns
-- =====================================================================
CREATE TABLE public.workflow_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name TEXT NOT NULL UNIQUE,
  tool_sequence TEXT[] NOT NULL, -- replaced ARRAY with TEXT[]
  frequency INTEGER DEFAULT 1,
  avg_success_rate DOUBLE PRECISION DEFAULT 1.0,
  user_sessions TEXT[] DEFAULT '{}',
  complexity_score INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_seen TIMESTAMP NOT NULL DEFAULT now(),
  embedding BYTEA, -- replaced USER-DEFINED
  description TEXT
);

-- =====================================================================
-- 4. composite_candidates
-- =====================================================================
CREATE TABLE public.composite_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_id UUID NOT NULL,
  tool_sequence TEXT[] NOT NULL,
  frequency INTEGER NOT NULL,
  success_rate DOUBLE PRECISION NOT NULL,
  confidence_score DOUBLE PRECISION NOT NULL,
  evaluation_status TEXT DEFAULT 'pending',
  tests_generated BOOLEAN DEFAULT false,
  tests_passing BOOLEAN DEFAULT false,
  promoted_to_composite TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  evaluated_at TIMESTAMP,
  rejection_reason TEXT,
  metadata JSONB,
  CONSTRAINT composite_candidates_pattern_id_fkey FOREIGN KEY (pattern_id)
    REFERENCES public.workflow_patterns(id)
);

-- =====================================================================
-- 5. composite_tools
-- =====================================================================
CREATE TABLE public.composite_tools (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  component_tools TEXT[] NOT NULL,
  workflow_template JSONB NOT NULL,
  success_rate DOUBLE PRECISION DEFAULT 1.0,
  usage_count INTEGER DEFAULT 0,
  auto_generated BOOLEAN DEFAULT false,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_used TIMESTAMP,
  file_path TEXT NOT NULL,
  test_path TEXT NOT NULL,
  docstring TEXT NOT NULL,
  embedding BYTEA,
  metadata JSONB
);

-- =====================================================================
-- 6. agent_policies
-- =====================================================================
CREATE TABLE public.agent_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_name TEXT NOT NULL UNIQUE,
  policy_type TEXT NOT NULL,
  value JSONB NOT NULL,
  version INTEGER DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now(),
  created_by TEXT DEFAULT 'system',
  metadata JSONB,
  is_active BOOLEAN DEFAULT true
);

-- =====================================================================
-- 7. ab_experiments
-- =====================================================================
CREATE TABLE public.ab_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_name TEXT NOT NULL UNIQUE,
  variant_a_policy JSONB NOT NULL,
  variant_b_policy JSONB NOT NULL,
  start_date TIMESTAMP NOT NULL DEFAULT now(),
  end_date TIMESTAMP,
  traffic_split DOUBLE PRECISION DEFAULT 0.5,
  metric_name TEXT NOT NULL,
  variant_a_metric DOUBLE PRECISION,
  variant_b_metric DOUBLE PRECISION,
  winner TEXT,
  is_active BOOLEAN DEFAULT true,
  metadata JSONB
);

-- =====================================================================
-- 8. execution_cache
-- =====================================================================
CREATE TABLE public.execution_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  inputs JSONB NOT NULL,
  outputs JSONB NOT NULL,
  execution_time_ms INTEGER NOT NULL,
  cache_hits INTEGER DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_accessed TIMESTAMP NOT NULL DEFAULT now(),
  expires_at TIMESTAMP,
  CONSTRAINT execution_cache_tool_name_fkey FOREIGN KEY (tool_name)
    REFERENCES public.agent_tools(name)
);

-- =====================================================================
-- 9. reflection_log
-- =====================================================================
CREATE TABLE public.reflection_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  execution_id UUID,
  tool_name TEXT NOT NULL,
  failure_type TEXT NOT NULL,
  error_message TEXT,
  root_cause_analysis TEXT,
  proposed_fix TEXT,
  fix_applied BOOLEAN DEFAULT false,
  fix_successful BOOLEAN,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  resolved_at TIMESTAMP,
  metadata JSONB,
  CONSTRAINT reflection_log_tool_name_fkey FOREIGN KEY (tool_name)
    REFERENCES public.agent_tools(name),
  CONSTRAINT reflection_log_execution_id_fkey FOREIGN KEY (execution_id)
    REFERENCES public.tool_executions(id)
);

-- =====================================================================
-- 10. request_traces
-- =====================================================================
CREATE TABLE public.request_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  user_prompt TEXT NOT NULL,
  execution_plan JSONB NOT NULL,
  steps JSONB NOT NULL,
  final_result JSONB,
  success BOOLEAN NOT NULL,
  total_duration_ms INTEGER NOT NULL,
  total_cost_tokens INTEGER,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  metadata JSONB
);

-- =====================================================================
-- 11. skill_graph_nodes
-- =====================================================================
CREATE TABLE public.skill_graph_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  node_name TEXT NOT NULL UNIQUE,
  node_type TEXT NOT NULL,
  tool_name TEXT,
  input_schema JSONB,
  output_schema JSONB,
  cost_estimate INTEGER DEFAULT 0,
  avg_latency_ms INTEGER DEFAULT 0,
  success_rate DOUBLE PRECISION DEFAULT 1.0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  metadata JSONB,
  CONSTRAINT skill_graph_nodes_tool_name_fkey FOREIGN KEY (tool_name)
    REFERENCES public.agent_tools(name)
);

-- =====================================================================
-- 12. skill_graph_edges
-- =====================================================================
CREATE TABLE public.skill_graph_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_node_id UUID NOT NULL,
  to_node_id UUID NOT NULL,
  edge_type TEXT DEFAULT 'sequence',
  data_flow_mapping JSONB,
  weight DOUBLE PRECISION DEFAULT 1.0,
  frequency INTEGER DEFAULT 0,
  success_rate DOUBLE PRECISION DEFAULT 1.0,
  avg_data_quality DOUBLE PRECISION DEFAULT 1.0,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  last_used TIMESTAMP,
  CONSTRAINT skill_graph_edges_from_node_id_fkey FOREIGN KEY (from_node_id)
    REFERENCES public.skill_graph_nodes(id),
  CONSTRAINT skill_graph_edges_to_node_id_fkey FOREIGN KEY (to_node_id)
    REFERENCES public.skill_graph_nodes(id)
);

-- =====================================================================
-- 13. tool_relationships
-- =====================================================================
CREATE TABLE public.tool_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_a TEXT NOT NULL,
  tool_b TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  frequency_count INTEGER DEFAULT 1,
  success_rate DOUBLE PRECISION DEFAULT 1.0,
  confidence_score DOUBLE PRECISION DEFAULT 0.5,
  last_updated TIMESTAMP NOT NULL DEFAULT now(),
  metadata JSONB
);

-- =====================================================================
-- 14. tool_versions
-- =====================================================================
CREATE TABLE public.tool_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tool_name TEXT NOT NULL,
  version INTEGER NOT NULL,
  code TEXT NOT NULL,
  tests TEXT NOT NULL,
  docstring TEXT NOT NULL,
  file_path TEXT NOT NULL,
  test_path TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  created_by TEXT DEFAULT 'synthesis',
  change_reason TEXT,
  performance_metrics JSONB,
  is_current BOOLEAN DEFAULT false,
  signature_hash TEXT,
  CONSTRAINT tool_versions_tool_name_fkey FOREIGN KEY (tool_name)
    REFERENCES public.agent_tools(name)
);
