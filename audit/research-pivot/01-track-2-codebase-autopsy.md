# Track 2 — Codebase Autopsy

**Repo:** `Self-Engineering-Agent-Framework` @ `70c3af4`
**Date:** 2026-07-13
**Purpose:** Decide what lives and what dies before the research-core rewrite.

**Target research loop (the bar every module is judged against):**
> accept a task → retrieve an existing capability or synthesize a new one → **verify it** → register it → reuse it — evaluated honestly.

Anything not serving that loop is ballast.

---

## 1. Scope

Read in full:

- **`src/` — all 18 modules** (`__init__`, `auto_tuner`, `capability_registry`, `composite_synthesizer`, `composition_planner`, `executor`, `llm_client`, `orchestrator`, `policy_store`, `query_planner`, `reflection_engine`, `response_synthesizer`, `sandbox`, `session_memory`, `skill_graph`, `synthesis_engine`, `utils`, `workflow_tracker`)
- `src/migrations/tables.sql` (263 lines)
- `web/app.py` (523), `tools/` (6 files), `scripts/batch_pattern_miner.py` (168)
- `evaluation/` (all: `eval_framework`, `run_evaluation`, `visualization`, `test_dataset_generator`, `questions.json`, `tests/*` ×7, both `.md`)
- `config.py`, `requirements.txt`, `docker/sandbox.dockerfile`, `data/*.csv`, `README.md`, `docs/api/*` (6 files, 5,700 lines)

**Executed** to verify claims (not just read):

- `python3 -m pytest --collect-only -q` → **10 collection errors, 0 tests collected**
- `PYTHONPATH=./tools python3 -m pytest tools/ -q` → **3 failed, 21 passed** (the committed, supposedly TDD-verified tool library fails its own tests)
- Import-graph trace of every `src` module; caller trace for every policy, every `SkillGraph`/`ReflectionEngine` method, every RPC name, every table name.

**Size:** 11,923 Python LOC; 5,700 lines of `docs/api/`; 263 lines SQL.

---

## 2. File-Level Verdict Table

Severity: **S1** critical (blocks/falsifies the research claim) · **S2** major · **S3** minor · **S4** cosmetic.

### Core spine

| Path | LOC | Verdict | Sev | Justification |
|---|---|---|---|---|
| `src/executor.py` | 181 | **REPLACE** | **S1** | `exec_module` runs LLM code **in the host process** (`:70-82`); the sandbox is never consulted at execution time. |
| `src/synthesis_engine.py` | 448 | **REPLACE** | **S1** | Regex-rewrites failing tests until green (`:148-214`), then registers unverified tools anyway (`:342-352`). Falsifies TDD. |
| `src/sandbox.py` | 244 | **REPLACE** | **S1** | Delivers 2 of the 5 claimed defense layers. No user, no cap-drop, no pids-limit, no read-only rootfs. |
| `docker/sandbox.dockerfile` | 11 | **REPLACE** | **S1** | **No `USER` directive → container runs as root.** Directly falsifies "Layer 5: Privilege Restriction". |
| `src/migrations/tables.sql` | 263 | **REPLACE** | **S1** | No pgvector, no index, `embedding BYTEA` (`:14`), **zero RPC functions**, 2 tables + 2 columns missing. Repo cannot run from its own migration. |
| `requirements.txt` | 10 | **REPLACE** | **S1** | 5 imported packages absent; pins `gpt-4` era assumptions. |
| `README.md` | 1280 | **REPLACE** | **S1** | Majority of load-bearing claims are FALSE (§4). |
| `src/orchestrator.py` | 837 | **REPLACE** | **S1** | 6 strategies, 4 of which are unreachable or dead-ended. Rewrite as a ~150-line loop. |
| `src/capability_registry.py` | 404 | **CORE MECHANISM** | S2 | Retrieval spine — keep. But re-rank weights hardcoded (`:219-221`) and ignore the policy the tuner writes; depends on a missing RPC. |
| `src/llm_client.py` | 482 | **CORE MECHANISM** | S2 | Spec/test/impl generation is the spine. But prompts hardcode pandas/CSV/`data/ecommerce_products.csv` (`:166`, `:182`, `:200-202`). De-slop. |
| `src/utils.py` | 96 | **SUPPORTING** | S3 | Brittle (`response.find('{')`, `split("```python")`) but small and genuinely needed. Harden. |
| `config.py` | 57 | **REPLACE** | S2 | `validate()` raises, module-level caller swallows it (`:52-56`). Does not fail fast. |
| `src/__init__.py` | 25 | **SUPPORTING** | S4 | Trim exports after the cut. |

### Ballast — delete

| Path | LOC | Verdict | Sev | Justification |
|---|---|---|---|---|
| `src/auto_tuner.py` | 427 | **DELETE** | **S1** | Fake learning. Objective functions score distance to hardcoded constants (§3). |
| `src/skill_graph.py` | 537 | **DELETE** | **S1** | `create_node`/`create_edge`/`load_graph`/`get_execution_path`/`update_*_metrics` have **zero callers**. The graph is always empty. Only `check_cache`/`cache_result` (~90 lines) run — and caching *harms* honest eval. |
| `src/reflection_engine.py` | 483 | **DELETE** | S2 | `apply_fix()` is never called at runtime (`orchestrator.py:509` calls only `analyze_failure`). "Self-healing" writes a fix proposal to a DB table and never applies it. |
| `src/composite_synthesizer.py` | 500 | **DELETE** | S2 | Only importer is `scripts/batch_pattern_miner.py` — an offline script with no scheduler, no CI, no caller. Composite promotion never runs. |
| `src/policy_store.py` | 382 | **DELETE** | S2 | 4 of 6 policies are never read. A/B API (`:258-368`) has zero callers. Replace with a dataclass of constants. |
| `src/query_planner.py` | 421 | **DELETE** | S2 | Adds 2 embeddings + 1 chat call per request before any work; its composite/pattern lookups hit RPCs that don't exist. Intent detection is a keyword list (`:256-274`). |
| `src/composition_planner.py` | 395 | **DELETE** | S2 | Multi-tool data-flow chaining is out of scope for the loop. |
| `src/session_memory.py` | 171 | **DELETE** | S3 | Writes to `agent_sessions`/`session_messages` — **neither table exists** in the migration. Fails silently. Not in the loop. |
| `src/response_synthesizer.py` | 84 | **DELETE** | S3 | `synthesize()` and `synthesize_synthesis_result()` have zero callers; orchestrator returns `str(tool_result)` raw ("Return raw data instead of synthesized response" ×5). Inline the 6-line error path. |
| `src/workflow_tracker.py` | 445 | **REPLACE** | S2 | Execution logging *is* needed for honest eval — keep ~60 lines. All pattern mining is dead (writes non-existent columns, §5/§8). |
| `web/app.py` | 523 | **DELETE** | S2 | Demo UI + Flask-RESTX Swagger. Zero research value. Hardcoded `SECRET_KEY` (`:23`), `cors_allowed_origins="*"` (`:36`). |
| `scripts/batch_pattern_miner.py` | 168 | **DELETE** | S2 | The only caller of auto_tuner/composite_synthesizer/apply_fix. `mine_patterns()` (`:17-44`) is a **no-op that prints "Analyzed pattern mining for period"** and does nothing. |
| `docs/api/*` (6 files) | 5,700 | **DELETE** | S2 | Documents a system that does not exist (§4). `DATABASE_SCHEMA.md:36,42` shows `VECTOR(1536)` + ivfflat index that the shipped migration does not contain. |
| `tools/*.py` (6 files) | 268 | **DELETE** | S3 | 3 demo tools (2 e-commerce), whose tests **fail 3/24**. Keep `tools/` as an empty output dir. |
| `data/*.csv` | 36 | **DELETE** | S3 | E-commerce demo fixtures leaked into core prompts. |

### Evaluation — delete and rebuild

| Path | LOC | Verdict | Sev | Justification |
|---|---|---|---|---|
| `evaluation/tests/*` (7 files) | 2,823 | **DELETE** | **S1** | **Zero `assert` statements across all 7 files.** Not pytest tests; self-scoring harnesses with rigged metrics (§6). |
| `evaluation/test_dataset_generator.py` | 494 | **DELETE** | S3 | Zero callers outside its own `__main__`. |
| `evaluation/questions.json` | 283 | **DELETE** | S3 | Zero callers. General-knowledge QA (quadratic roots, matrix determinants) — the wrong benchmark for a tool-synthesis agent. |
| `evaluation/visualization.py` | 405 | **DELETE** | S4 | Charts for an eval that doesn't measure anything. Needs matplotlib+seaborn, both unlisted. |
| `evaluation/eval_framework.py` | 445 | **REPLACE** | S2 | The metric primitives (P/R/F1/MRR/NDCG, `:81-185`) are salvageable. The harness around them is not. |
| `evaluation/run_evaluation.py` | 154 | **REPLACE** | S3 | Rewrite against a real harness. |
| `evaluation/EVALUATION_METHODOLOGY.md` | — | **REPLACE** | S2 | Codifies the theater: "Code Quality Score: docstring 30%, type hints 30%, structure 20%, no syntax errors 20%" (`:131-135`) — **zero correctness signal**. |

---

## 3. Fake-Learning Inventory

Every stub that pretends to learn, with the line that proves it.

### 3.1 `auto_tuner._evaluate_threshold` — the search is a constant

`src/auto_tuner.py:164-170`
```python
optimal = 0.45
distance = abs(threshold - optimal)
score = 1.0 - (distance * 2)   # Penalty for distance from optimal
return max(0, score)
```
The objective function **takes no data**. `tune_retrieval_threshold` (`:111`) sweeps `np.linspace(0.3, 0.7, 7)` = `[0.30, 0.367, 0.433, 0.50, 0.567, 0.633, 0.70]` and picks the argmax of "closeness to 0.45". The winner is **deterministically `0.4333`**, forever, on every machine, regardless of a single byte of execution history. It is then written to the policy store as a *learned optimum* (`:132-142`) with a `"trials"` array to make it look like a search happened.

Comments admitting it: `:154` `"For simplicity, we estimate based on historical data."` · `:155` `"In production, this would run live experiments."` · `:169` `"# In real implementation, would query actual metrics"`.

### 3.2 `auto_tuner._evaluate_reranking_weights` — random search toward a hardcoded answer

`src/auto_tuner.py:347-354`
```python
# Ideal is similarity: 0.6-0.7, success: 0.2-0.3, frequency: 0.1
ideal = np.array([0.65, 0.25, 0.1])
actual = np.array([similarity_w, success_w, frequency_w])
distance = np.linalg.norm(ideal - actual)
score = max(0, 1.0 - distance)
```
`tune_reranking_weights` (`:290-294`) draws 10 Dirichlet samples under `np.random.seed(42)` and returns whichever random sample landed closest to the hardcoded ideal. Seeded → identical output every run. This is not optimisation; it is a lottery whose prize is a constant.

### 3.3 The metrics are decorative

`run_full_tuning` (`:370`) calls `compute_current_metrics()` — which *does* query `tool_executions` — prints the numbers (`:371-373`), stores them in `results["baseline_metrics"]`, and then **never passes them to any `_evaluate_*` function**. Two of the three objectives take no data argument at all. The real metrics exist only to be printed.

### 3.4 The auto-tuner crashes on a fresh install

`compute_current_metrics` returns **without** a `pattern_reuse_rate` key on the no-data path (`:53-58`) and on the exception path (`:87-91`). `run_full_tuning` then does:
```python
print(f"   Pattern Reuse: {baseline_metrics['pattern_reuse_rate']:.2%}")   # :373
```
→ **`KeyError` on any database with zero executions in the last 7 days.** The auto-tuner has never been successfully run against an empty DB. Combined with §3.1–3.3: it cannot learn, and it cannot even start.

### 3.5 Three of the tuner's outputs are write-only

| Policy | Written by | Read by |
|---|---|---|
| `retrieval_similarity_threshold` | `auto_tuner:133` | `orchestrator:399` ✅ (the *only* live one) |
| `reranking_weights` | `auto_tuner:319` | **nobody** — `capability_registry:219-221` hardcodes `0.7/0.2/0.1` |
| `composite_promotion_criteria` | `auto_tuner:215` | `composite_synthesizer:54` — which is only reachable from a script nobody runs |
| `workflow_complexity_thresholds` | (default only) | **nobody** |
| `cost_limits` | (default only) | **nobody** |
| `cache_ttl` | (default only) | **nobody** — `skill_graph.cache_result` is called without `ttl_hours` (`orchestrator:457`), so `expires_at=None` and **the cache never expires** |

So the single behavioural effect the entire 427-line "learning" subsystem can have on the running agent is: set the retrieval threshold to `0.4333`.

### 3.6 `workflow_tracker` pattern mining — writes to columns that don't exist

`src/workflow_tracker.py:225-226` and `:240-241` write `avg_execution_time_ms` and `confidence_score` into `workflow_patterns`. Neither column exists in `src/migrations/tables.sql:40-52`. Every insert/update raises, and every one is swallowed:
```python
except Exception as e:
    print(f"Warning: Failed to mine full sequence pattern: {str(e)}")   # :249-250
```
**Pattern mining fails 100% of the time, silently, by construction.** Everything downstream (confidence scoring, composite promotion, `_evaluate_composite_criteria`) is therefore reading from a table that is permanently empty.

### 3.7 `skill_graph` — "learned edges" on a graph with no nodes

`create_node`, `create_edge`, `load_graph`, `get_execution_path`, `update_node_metrics`, `update_edge_metrics` — **zero callers anywhere in the repo** (verified by grep). The orchestrator constructs `SkillGraph()` (`:90`) and calls only `check_cache` (`:425`) and `cache_result` (`:457`). The "typed workflow graph with learned edges" is 450 lines of code operating on a structure that is never populated. `get_execution_path` on an empty graph returns `[]`.

### 3.8 `reflection_engine` — "self-healing" that never heals

`orchestrator.py:509` calls `analyze_failure()`, which generates a root cause and a `proposed_fix` and **INSERTs it into `reflection_log`** (`reflection_engine.py:421`). That's it. `apply_fix()` — the method that actually verifies the fix in the sandbox and rewrites the tool (`:117-234`) — is called from exactly one place: `scripts/batch_pattern_miner.py:102`, an offline script with no scheduler and no invocation anywhere. **In the running agent, the reflection loop terminates at "write a suggestion to a table nobody reads."** The README's reflection diagram (FAIL→ANALYZE→ROOT→FIX→**VERIFY→UPDATE**) is truncated after ROOT→FIX in reality.

### 3.9 Bonus: the synthesis engine "learns" to pass by editing the exam

Not learning theater but the same species. `src/synthesis_engine.py:148-214`, `_apply_aggressive_test_fixes`, mutates the *test* file with regex after the tests fail:

- `:182-186` — `if 'negative price' in line.lower() and ... '== -1.5' in line:` → `line.replace('== -1.5', '== 1.5')`. **It flips the sign of an expected value to match whatever the implementation produced.**
- `:174-179` — rewrites `assert result['success'] == False` into `assert result['success'] == True`.
- `:189-194` — deletes `with pytest.raises(ValueError...)` blocks entirely.
- `:165-171`, `:203-204` — deletes whole test functions whose names contain `malformed` or `parser_error`.

And `_validate_and_fix_tests` (`:100-146`) does this *before the first run*, unconditionally, on every synthesis.

Then, if the tests *still* fail after being rewritten, `:342-352` registers the tool anyway with `tests_verified = False`. **Verification is advisory. It gates nothing.**

---

## 4. README / docs Claim Audit

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | "Verifies the implementation in a secure sandbox environment" / "Generated code must prove itself before joining the tool library" (README:124, 722) | **FALSE** | `synthesis_engine.py:342-352` — on failure it sets `tests_verified = False` and **proceeds to registration**. `orchestrator.py:326-338` then *executes it anyway*. Nothing is gated on verification. |
| 2 | "Each tool execution runs in a separate Docker container" (README:254); "**All** synthesized code runs in isolated Docker containers" (`docs/api/AUTHENTICATION.md:37`) | **FALSE** | `executor.py:70-82` — `spec.loader.exec_module(module)` + `function(**arguments)` (`:116`). **Tool execution happens in the host Python process.** Docker is used only during synthesis-time verification. |
| 3 | Security Layer 5: "Container processes run as **non-root** users" (README:856) | **FALSE** | `docker/sandbox.dockerfile` — 11 lines, **no `USER` directive**. Container runs as root. |
| 4 | Security Layer 5: "No capability to modify system files / **Minimal Capabilities**" (README:800-860) | **FALSE** | `sandbox.py:145-155` — no `cap_drop`, no `security_opt=["no-new-privileges"]`. |
| 5 | Security Layer 3: "**Process limits** prevent fork bombs" (README:846) | **FALSE** | `sandbox.py:145-155` — no `pids_limit` parameter. |
| 6 | Security Layer 4: "The container's filesystem is largely **read-only**" (README:517) | **PARTIAL** | The `/code` **bind mount** is `mode: 'ro'` (`sandbox.py:148`) ✅, but the container **rootfs is writable** — no `read_only=True`. |
| 7 | Security Layer 2: "Containers have **no network access**" (README:515) | **TRUE** | `sandbox.py:151` — `network_disabled=True`. |
| 8 | Security Layer 3: "CPU 50%, Memory 256MB, 30s timeout" (README:842-847) | **PARTIAL** | mem/CPU real (`sandbox.py:152-154`) ✅. Timeout is **not enforced on the container**: `container.wait(timeout=…)` (`:158`) times out the *client*, not the process. The handler then force-removes **every container from that image** (`:189-191`) — nuking any concurrent verification. |
| 9 | "Vector Database: PostgreSQL with **pgvector**"; "1536-dim vectors"; "**HNSW Index**"; "Cosine Similarity" (README:246, 885-895) | **FALSE** | `src/migrations/tables.sql` — only `CREATE EXTENSION pgcrypto` (`:2`). `embedding **BYTEA**` (`:14`). **No vector type, no HNSW, no IVFFlat, no index of any kind.** (`docs/api/DATABASE_SCHEMA.md:36,42` shows `VECTOR(1536)` + ivfflat — the docs describe a schema the repo does not ship.) |
| 10 | Semantic search works at all | **FALSE (as shipped)** | `capability_registry.py:142` calls RPC `search_tools`. **Zero SQL functions are defined anywhere in the repo.** Same for `search_workflow_patterns`, `search_composite_tools`, `update_tool_relationship`, `get_policy`, `update_policy`, `get_unique_sessions_since`. |
| 11 | Re-ranking "Semantic 70% / Success 20% / Frequency 10%" (README:936-940) | **TRUE (but hardcoded)** | `capability_registry.py:219-221` implements exactly `0.7·sim + 0.2·success + 0.1·freq`. It is **not** read from the `reranking_weights` policy the auto-tuner writes — that policy is dead. |
| 12 | Thresholds: ">80% execute, 65–80% verify, <65% synthesize" (README:927-930, 336-338) | **FALSE** | There is one threshold, `0.4` (`config.py:24`, `policy_store.py:23`). No 3-tier logic exists. The only other constant is a `0.65` in the force-synthesis path (`orchestrator.py:166`). |
| 13 | "**Composite Promotion**: frequently-used patterns promoted to first-class tools" (README:1085-1091) | **FALSE** | `CompositeSynthesizer` is imported only by `scripts/batch_pattern_miner.py` — never invoked by the agent or any scheduler. Its input table (`workflow_patterns`) can never be populated (§3.6). |
| 14 | "**Pattern Mining**: detects recurring tool sequences" (README:539) | **FALSE** | Writes `confidence_score`/`avg_execution_time_ms` to `workflow_patterns` — columns that don't exist (`tables.sql:40-52`) → every write raises → swallowed at `workflow_tracker.py:249`. Also, `start_session`/`end_session` are called **per request** (`orchestrator.py:143`), so sequences are never linked across a conversation. |
| 15 | "**Self-healing**: failed executions trigger automatic analysis and fixes" (README:161, 560-568) | **FALSE** | `apply_fix()` never called at runtime (§3.8). The loop stops at "log a suggestion". |
| 16 | "**Version Management**: maintains version history so fixes can be rolled back" (README:568) | **FALSE** | `_save_tool_version` is only reachable from `apply_fix` (dead). `registry.add_tool` (`:106-114`) writes **no version field**. The `tool_versions` table is never written at runtime. |
| 17 | "**Auto-Tuning**: the tuner explores parameter combinations to find optimal configurations" (README:1131) | **FALSE** | §3.1–3.4. Returns a hardcoded constant; crashes on empty DB. |
| 18 | "**A/B Testing**" in the auto-tuner diagram (README:1109) | **FALSE** | `create_ab_experiment` / `get_experiment_variant` / `record_experiment_result` — **zero callers** outside `policy_store.py` itself. |
| 19 | "**Response Assembly**: combining tool results with context to generate coherent responses" (README:399) | **FALSE** | Every success path returns `str(tool_result)` raw. `orchestrator.py:480, 605, 660, 716, 788` each carry the comment `# Return raw data instead of synthesized response`. `ResponseSynthesizer.synthesize()` has zero callers. |
| 20 | "**Orphan Cleanup**: automatically removes DB entries for tools whose files are deleted" (README:454) | **TRUE** | `capability_registry.py:360-387`, called at `orchestrator.py:147`. (One of the few claims that holds.) |
| 21 | "Test Generation … 7–10 test functions covering edge cases" | **TRUE-ish** | `llm_client.py:155` asks for it. But the tests are then **rewritten to pass** (§3.9). |
| 22 | Intent detection via keywords "(create, build, make, write, **generate**, develop)" (README:431) | **PARTIAL** | `query_planner.py:256-271` — the keyword list contains create/build/make/write/implement/develop. **"generate" is absent.** "Generate a function that…" does not trigger synthesis. |
| 23 | SocketIO event `composite_created` (`docs/api/SOCKETIO_EVENTS.md:332`) | **FALSE** | Never emitted anywhere in the codebase. |
| 24 | `docs/api/AUTHENTICATION.md` (910 lines: RBAC roles, RLS policies, rate limiting) | **FALSE / aspirational** | `web/app.py` has **zero** auth code. Hardcoded `SECRET_KEY` (`:23`), `cors_allowed_origins="*"` (`:36`). The doc is at least explicit that dev mode has "No authentication required" (`:23`) — but then documents an authorization system that does not exist. |

**Tally: 3 TRUE, 4 PARTIAL, 17 FALSE.**

---

## 5. Security Reality

### Does untrusted LLM-generated code ever execute on the host?

**Yes. Every single time a tool runs.** This is the headline finding.

`src/executor.py:69-82`:
```python
spec = importlib.util.spec_from_file_location(function_name, file_path)
module = importlib.util.module_from_spec(spec)
sys.modules[function_name] = module
spec.loader.exec_module(module)          # ← module-level LLM code executes HERE, in-process
```
`src/executor.py:116`:
```python
result = function(**arguments)           # ← LLM function body executes HERE, in-process
```

There is **no sandbox anywhere on this path.** `ToolExecutor` does not import `SecureSandbox`; `Docker` is only touched by `synthesis_engine.py:314` (verification) and `reflection_engine.py:173`. Once a tool is on disk, it is imported straight into the Flask/eventlet process with the full privileges of the user running the server — filesystem, network, environment (including `OPENAI_API_KEY` and `SUPABASE_KEY`), and everything else.

**It gets worse.** The code that reaches `exec_module` is not even code that passed its tests:

1. `synthesis_engine.py:332` — tests fail → rewrite the tests with regex.
2. `synthesis_engine.py:342-352` — still fail → `tests_verified = False`, **register anyway** as "experimental".
3. `orchestrator.py:326-329` — emits a cosmetic `tool_experimental_warning`.
4. `orchestrator.py:331-338` — **immediately loads and executes it on the host.** No gate. No branch. The warning is decorative.

So the actual pipeline is: *LLM writes code → code fails its own tests → tests get rewritten → code still fails → code is imported into the host process and run.* The word "verified" in this repo means nothing.

### What isolation actually exists (verification-time only)

`sandbox.py:145-155` — the complete list of what is passed to `containers.run`:

| Control | Present? | Line |
|---|---|---|
| Fresh container per run + removed after | ✅ | `:145`, `:165` |
| `network_disabled=True` | ✅ | `:151` |
| `mem_limit="256m"` | ✅ | `:152` |
| `cpu_quota=50000` (50% of a core) | ✅ | `:153-154` |
| Code mounted read-only (`mode: 'ro'`) | ✅ | `:148` |
| **`user=` / non-root** | ❌ | absent — and `sandbox.dockerfile` has no `USER` → **root** |
| **`cap_drop=["ALL"]`** | ❌ | absent |
| **`pids_limit=`** | ❌ | absent → fork bombs unmitigated |
| **`read_only=True`** (rootfs) | ❌ | absent → rootfs writable |
| **`security_opt=["no-new-privileges"]`** | ❌ | absent |
| **Enforced wall-clock timeout** | ❌ | `container.wait(timeout=…)` (`:158`) times out the *docker client*, not the container. The container keeps running. |

**Score: 5 controls present, 6 absent. The README claims 5 layers; 2 are fully real (network, resources), 1 is half-real (RO mount but writable rootfs), and 2 are entirely fictional (privilege restriction, process limits).**

### Additional security defects

- **`sandbox.py:189-191`** — the timeout/exception handler does `containers.list(all=True, filters={"ancestor": self.image_name})` and force-removes **every container built from the sandbox image**. Under any concurrency, one slow verification destroys all the others. It is also the only thing that kills a runaway container, and it kills its neighbours to do it.
- **`web/app.py:23`** — `SECRET_KEY = 'self-engineering-agent-secret-key'`, committed.
- **`web/app.py:36`** — `cors_allowed_origins="*"` on a WebSocket that executes arbitrary generated code on the host. Any web page in the world can drive this agent.
- **`config.py:52-56`** — misconfiguration is logged, not raised. The app boots with no API key and fails later, deep in a call stack.

---

## 6. Test Theater

### The suite does not run — and would collect zero tests even if it did

```
$ python3 -m pytest --collect-only -q
!!! Interrupted: 10 errors during collection !!!
no tests collected, 10 errors in 0.33s
```

**Why (two distinct root causes):**

1. **The 7 `evaluation/tests/*` files** all fail with the *same* error: `evaluation/tests/__init__.py:5-11` eagerly imports all seven modules, and `test_performance.py:12` does `import psutil` — which is **not in `requirements.txt`**. One missing dep takes down all seven.
2. **The 3 `tools/test_*` files** fail with `ModuleNotFoundError: No module named 'reverse_string'`. They use flat imports (`from reverse_string import reverse_string`) that only resolve inside the Docker sandbox, where `sandbox.py:110-120` rewrites them and flattens the layout. **On the host they are permanently unimportable.**

There is **no `conftest.py`, no `pytest.ini`, no `pyproject.toml`, no `setup.cfg`** — nothing puts the repo root on `sys.path`.

**And here is the kicker:** even with every dependency installed, `pytest` would collect **zero** tests from `evaluation/tests/`. Those files contain:
- **zero module-level `def test_*` functions** (verified by grep), and
- classes named `LearningTests`, `RetrievalTests`, … which pytest **refuses to collect** because they have `__init__` constructors (`PytestCollectionWarning: cannot collect test class ... because it has a __init__ constructor`).

**Zero `assert` statements exist in any of the 7 files.** They are not tests. They are a self-scoring harness driven by `eval_framework._run_test_category()` that grades itself with arithmetic.

### The metrics are rigged

**A. The pattern-learning test passes when nothing is learned.** `test_learning.py:228`:
```python
patterns_learned = final_pattern_count >= initial_pattern_count   # >= , not >
...
passed = patterns_learned                                          # :243
```
`>=`, not `>`. Pattern mining is **provably broken** (§3.6 — it writes to non-existent columns), so `final == initial == 0` on every run → `patterns_learned = True` → **PASS**. The test that is supposed to prove the system learns is guaranteed to pass on a system that provably learns nothing.

**B. The retention test asserts the shape of its own SELECT.** `test_learning.py:288`:
```python
if all(key in tool for key in ['name', 'docstring', 'file_path']):
```
`registry.get_all_tools()` SELECTs literally `"name, docstring, created_at, file_path"` (`capability_registry.py:325-327`). `retention_rate` is **1.0 by construction**, always. It is tautological.

**C. Crashes are scored as successes.** `test_retrieval.py:~318`:
```python
except Exception:
    true_negatives += 1          # a crash counts as a correct rejection
...
score = 1.0 - fpr                # → a retriever that throws on every query scores 1.0
```

**D. The retrieval ground truth is a substring match on word fragments.** `test_retrieval.py:~190`:
```python
if expected_tool.lower() in found_name or any(
        word in found_name for word in expected_tool.lower().split('_')):
    true_positives += 1
```
`expected_tool = "calculate_percentage"` → splits to `["calculate", "percentage"]` → **any tool whose name contains "calculate" is a true positive.** `calculate_profit_margins` scores as a correct retrieval for the query "calculate 50% of 200". Precision/recall/F1 built on this are meaningless.

**E. "Code quality" measures prompt compliance, not correctness.** `test_synthesis.py:~157` and `EVALUATION_METHODOLOGY.md:131-135`:
```
score = has_docstring*0.3 + has_type_hints*0.3 + proper_structure*0.2 + no_syntax_errors*0.2
```
The system prompt (`llm_client.py:308-311`) *explicitly demands* docstrings and type hints. The metric measures whether the LLM followed instructions. **Nothing anywhere checks that a synthesized `lcm` function actually computes an LCM.**

**F. The "learning curve" measures OpenAI latency jitter.** `test_learning.py:157-159` computes `improvement_rate` from wall-clock times of 5 *different* queries and clamps it at 0 (`:165`), so network noise can only ever help the score.

**G. Stateful, non-reproducible.** `test_retrieval.test_exact_match` queries `"calculate percentage"` and expects a tool named `*percentage*`. **No such tool exists in the repo** (the library is `reverse_string`, `calculate_profit_margins`, `identify_low_margin_products`). It can only pass if an *earlier* eval run happened to synthesize one into the shared Supabase DB. The eval has a hidden ordering dependency on live external state.

### The registered "TDD-verified" tool library fails its own tests

Run the way the sandbox runs them:
```
$ PYTHONPATH=./tools python3 -m pytest tools/ -q
3 failed, 21 passed
```
The failures are semantic garbage produced by the regex test-fixer:
```python
# tools/test_calculate_profit_margins.py:48
assert pd.isna(result['output_file']), "Profit margin for NaN price should be None"
E  AssertionError: assert False
E   + where False = pd.isna('data/profit_margins.csv')
```
`output_file` is a **file path string**, asserted to be `NaN`. This is what `_validate_and_fix_tests` (`synthesis_engine.py:116-121`) does when it splices a "graceful handling" assertion into a test it doesn't understand. **These three tools are committed to the repo as the proof of the TDD claim, and they fail.**

---

## 7. Load-Bearing Analysis

Against the loop: *accept → retrieve|synthesize → **verify** → register → reuse → evaluate honestly.*

| Subsystem | LOC | Load-bearing? | Recommendation |
|---|---|---|---|
| **Docker sandbox** | 244 + 11 | **LOAD-BEARING — the single most load-bearing thing here** | **KEEP and FIX.** "Verify" is the only word in the thesis that distinguishes this from a code-gen demo, and verification is the one thing that must be real. Add `USER nobody` to the dockerfile; add `cap_drop=["ALL"]`, `pids_limit=64`, `read_only=True`, `security_opt=["no-new-privileges"]`, and a real container-side timeout. **Then make the executor use it too** — verification-only sandboxing is worse than useless, because it launders untrusted code as "verified" before running it on the host. |
| **Supabase / pgvector** | 404 + 263 | **Concept load-bearing; implementation is ballast** | **REPLACE.** Retrieval *is* the loop. But the shipped schema has **no pgvector, no index, and zero RPC functions** — the retrieval path literally cannot execute. For a research core with O(10²–10³) tools, a network round-trip to a hosted Postgres for every embedding lookup buys nothing. **Recommendation: SQLite + a numpy cosine scan** (or `sqlite-vec`). ~80 lines, zero infra, fully reproducible, offline, and it makes the eval hermetic instead of dependent on shared mutable cloud state. Supabase's only real contribution is making every eval run non-reproducible. |
| **Flask + SocketIO UI** | 523 | **BALLAST** | **DELETE.** Zero research value. It exists to make a demo GIF. It also contributes the two worst security defects (`cors_allowed_origins="*"` + hardcoded secret) on a service that executes generated code on the host. A CLI entrypoint is all the research core needs. |
| **Composite synthesizer** | 500 | **BALLAST** | **DELETE.** Reachable only from an offline script with no caller. Its input table can never be populated (§3.6). It's an unfinished feature for a problem the core doesn't have yet: you cannot promote composites before you can reliably synthesize *singletons*, and the repo cannot yet do that honestly. Revisit only if the core loop is proven first. |
| **Auto-tuner** | 427 | **BALLAST — actively harmful** | **DELETE.** §3. It is not a weak learner; it is a constant with a `for` loop around it, writing fabricated "learned optima" into a policy store. It is the single clearest instance of research fraud in the codebase, and it must not survive in any form. If policy tuning matters later, do it as an honest offline sweep with a held-out set. |
| **Skill graph** | 537 | **BALLAST** | **DELETE.** Node/edge API has **zero callers**; the graph is always empty. The only live part is `check_cache`/`cache_result` (~90 lines) — and that cache is *harmful* to the research goal: it has no TTL (`cache_ttl` policy unread, `ttl_hours` never passed), so a repeated eval query returns a memoized answer and **inflates apparent success and latency improvements**. Deleting the cache makes the eval honest. |
| **Reflection engine** | 483 | **Concept is interesting; implementation is ballast** | **DELETE now; re-earn later.** `apply_fix()` is never called at runtime — "self-healing" writes a suggestion to a table and stops (§3.8). *However*: a repair loop is arguably the most defensible research contribution available here (synthesize → verify → **repair on failure** → re-verify), and it's the one thing that would make the TDD claim mean something. **Recommendation: delete these 483 lines, then rebuild a ~120-line repair loop as a first-class, gated, honestly-measured part of the core** — with the fixed test suite held *immutable* (see below). Do not carry this code forward. |
| **Query planner** | 421 | **BALLAST** | **DELETE.** Adds 2 embedding calls + 1 chat call to *every* request before any work happens. Its two headline features (composite lookup, pattern lookup) call RPCs that don't exist. Its intent detection is a 14-item keyword list that doesn't even contain "generate". The research loop needs exactly one decision — *retrieve or synthesize?* — and that's a threshold on a similarity score, not a 421-line planner. |
| **Session memory** | 171 | **BALLAST** | **DELETE.** Writes to `agent_sessions` and `session_messages` — **neither table exists in the migration**. It fails silently on every call. Multi-turn conversation is not in the loop. |
| **Workflow tracker** | 445 | **~15% load-bearing** | **REPLACE with ~60 lines.** Honest evaluation *requires* an execution log (tool, inputs, success, latency). Keep that. **Delete all pattern mining** (`_analyze_session_patterns`, `_mine_full_sequence_pattern`, `_mine_pairwise_relationships`, `_mine_subsequence_patterns`, `_update_subsequence_pattern` — ~250 lines) — it is 100% broken (§3.6) and feeds only the composite synthesizer, which is also being deleted. |

### The shape of the surviving core

| Keep (rewrite/fix) | ~LOC |
|---|---|
| `llm_client` (de-slopped prompts, no pandas/CSV/e-commerce) | ~250 |
| `capability_registry` → local vector store (SQLite + numpy) | ~150 |
| `synthesis_engine` → **verification gates registration, tests immutable** | ~150 |
| `sandbox` + hardened dockerfile → **used for execution too** | ~180 |
| `executor` → **runs in the sandbox, not the host** | ~120 |
| `orchestrator` → the actual loop | ~150 |
| execution logger (from `workflow_tracker`) | ~60 |
| honest eval harness + real pytest tests | ~300 |
| **Total** | **~1,360** |

**Deleted: ~8,000 Python LOC + 5,700 lines of docs.** From 11,923 → ~1,400. A small complete system instead of a large incomplete one.

### The one non-negotiable design rule for the rewrite

**The generated test suite must be immutable once written.** The entire scientific claim of this project rests on tests-as-specification. `_validate_and_fix_tests` and `_apply_aggressive_test_fixes` must not be reimplemented in any form. If the implementation fails the tests: retry the *implementation* (bounded), then **fail loudly and record it as a failure**. A synthesis failure rate is a *result*. A synthesis failure rate of zero, achieved by editing the tests, is a fabrication.

---

## 8. Dependency Reality

### `requirements.txt` (9 lines) vs. what the code imports

| Package | In requirements? | Imported by | Status |
|---|---|---|---|
| `openai` | ✅ | `llm_client.py:7` | OK |
| `supabase` | ✅ | 8 modules | OK |
| `flask`, `flask-socketio`, `flask-restx` | ✅ | `web/app.py:11-13` | OK (but the whole UI is being deleted) |
| `docker` | ✅ | `sandbox.py:9` | OK |
| `pytest` | ✅ | generated tests | OK |
| `python-dotenv` | ✅ | `config.py:3` | OK |
| `eventlet` | ✅ | `web/app.py:16` | OK |
| **`numpy`** | ❌ **MISSING** | `auto_tuner.py:6`, `eval_framework.py:16` — **both core-path** | **BROKEN** |
| **`pandas`** | ❌ **MISSING** | `tools/*.py`; hardcoded into `llm_client.py:153`, `synthesis_engine.py:136-140` prompts; installed in `sandbox.dockerfile:4` | **BROKEN** |
| **`psutil`** | ❌ **MISSING** | `evaluation/tests/test_performance.py:12` | **BROKEN — this single omission causes 7 of the 10 pytest collection errors** |
| **`matplotlib`** | ❌ **MISSING** | `evaluation/visualization.py` | **BROKEN** |
| **`seaborn`** | ❌ **MISSING** | `evaluation/visualization.py` | **BROKEN** |

**Exact diff — add to `requirements.txt`:**
```
numpy
pandas
psutil        # test_performance.py — cause of 7/10 collection errors
matplotlib    # visualization.py
seaborn       # visualization.py
```
`evaluation/README.md:9-11` even *tells the user* to `pip install matplotlib seaborn psutil` manually — an acknowledgement that the requirements file is knowingly incomplete.

### Other dependency defects

- **`config.py:18`** — `OPENAI_MODEL` defaults to **`"gpt-4"`**, a deprecated model. Every README/architecture diagram hardcodes GPT-4 (README:474, 1158). This needs to be a current model, and it should be explicit, not a silent default.
- **No `conftest.py` / `pyproject.toml` / `pytest.ini` / `setup.cfg`.** The package is not installable and the tests cannot resolve `src.*` or `evaluation.*`.
- **`docker/sandbox.dockerfile:4`** pins nothing: `pip install --no-cache-dir pytest pandas numpy openpyxl xlrd`. Unpinned, unreproducible, and hardcodes the e-commerce/Excel demo stack into the "general" sandbox.
- **`xlrd`** is installed in the sandbox and imported by nothing.

### Schema reality (the deepest breakage)

`src/migrations/tables.sql` is not a working migration. Running it produces a database the code cannot use:

| Required by code | Present in `tables.sql`? |
|---|---|
| `CREATE EXTENSION vector` | ❌ — only `pgcrypto` (`:2`) |
| `embedding vector(1536)` | ❌ — **`embedding BYTEA`** (`:14`, `:50`, `:92`) |
| Any index on any embedding | ❌ — **zero `CREATE INDEX` statements in the file** |
| RPC `search_tools` (`capability_registry.py:142`) | ❌ |
| RPC `search_workflow_patterns` (`query_planner.py:173`) | ❌ |
| RPC `search_composite_tools` (`query_planner.py:220`) | ❌ |
| RPC `update_tool_relationship` (`workflow_tracker.py:151`) | ❌ |
| RPC `get_policy` / `update_policy` (`policy_store.py:106,153`) | ❌ |
| RPC `get_unique_sessions_since` (`batch_pattern_miner.py:36`) | ❌ |
| Table `agent_sessions` (`session_memory.py:43`) | ❌ **missing entirely** |
| Table `session_messages` (`session_memory.py:77`) | ❌ **missing entirely** |
| Column `workflow_patterns.confidence_score` (`workflow_tracker.py:226`) | ❌ **missing** |
| Column `workflow_patterns.avg_execution_time_ms` (`workflow_tracker.py:225`) | ❌ **missing** |

**Zero SQL functions are defined anywhere in the repository.** The `-- replaced USER-DEFINED with BYTEA` comment at `:14` is the tell: this file is a *schema dump* from a live Supabase instance where pgvector's type came back as `USER-DEFINED`, and someone hand-substituted `BYTEA` to make the DDL parse. **The repo, as committed, cannot perform semantic retrieval.** The only correct pgvector DDL in the project lives in a *markdown file* (`docs/api/DATABASE_SCHEMA.md:36,42`).

This also means: whatever numbers this project has ever reported, they were produced against a database that is not in the repo and cannot be reconstructed from it. **Nothing here is reproducible.**

---

## 9. Residual Risk — what I could not determine statically

1. **The live Supabase instance.** The real schema (with pgvector + the 6 RPCs) exists somewhere; only a dump-with-substitutions is committed. I cannot verify what `search_tools` actually computes — whether it's cosine, L2, or inner-product, and whether it returns a `similarity` in `[0,1]` (the whole threshold logic in `orchestrator.py:399-411` assumes it does). **Get the real SQL before designing the replacement.**
2. **Whether the system has ever run end-to-end.** Given the missing RPCs, missing tables, missing columns, missing deps, and the `KeyError` in `run_full_tuning`, I believe it has run *only* against a hand-maintained cloud DB that diverged from the repo. Not statically provable.
3. **Real LLM behaviour.** Whether `gpt-4` reliably emits parseable JSON for `utils.extract_json_from_response` (`response.find('{') … rfind('}')` — which will mangle any response containing prose braces or two JSON objects) is an empirical question. Prompt-parse failure rates are unknown and unmeasured.
4. **Actual Docker behaviour under `eventlet.monkey_patch()`** (`web/app.py:19`). Monkey-patching sockets before the `docker` SDK opens its Unix socket is a classic source of hangs. Unverified — but the UI is being deleted anyway.
5. **`sandbox.py` on a read-only `/code` mount.** pytest normally tolerates an unwritable `__pycache__`/`.pytest_cache`, but I did not build the image and run it. Low risk; verify during the rewrite.
6. **Concurrency.** The `containers.list(ancestor=…)` + `remove(force=True)` handler (`sandbox.py:189-191`) is a race by inspection, but I could not exercise it. Assume it is real.
7. **Whether any evaluation results were ever published.** `evaluation/results/` is not committed. If numbers exist anywhere (paper, slides, README history), they were produced by the harness in §6 and should be treated as **void**.
