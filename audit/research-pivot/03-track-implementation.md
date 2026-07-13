# Phase 3 — Implementation Notes

**Scope:** Execute the Phase 2 delete-list; rebuild the research core end-to-end.
**Branch:** `research-pivot`
**Date:** 2026-07-13

---

## 1. What was deleted

The delete-list from `02-thesis-and-architecture.md` was executed in full: **58 files, 11,923 lines of Python → 0.** The tree was reduced to `README.md`, `LICENSE`, `requirements.txt`, `.gitignore`, and the audit trail, then rebuilt.

Everything went: `src/` (18 modules), `web/`, `evaluation/`, `docs/api/`, `tools/`, `data/`, `docker/`, `scripts/`, `config.py`.

Verification that the cut is real, not cosmetic:

```
$ git ls-files | grep -c '^src/\|^web/\|^evaluation/'
0
$ grep -rn "supabase\|flask\|auto_tuner\|skill_graph\|reflection_engine" sea/ tests/
(no matches — no zombie imports)
```

## 2. What was built

```
sea/
├── config.py        70 LOC   fail-fast; raises ConfigError on missing key
├── llm.py          280 LOC   OpenAI client + content-addressed disk cache + FakeLLM
├── sandbox.py      330 LOC   subprocess + rlimits — the ONLY way code executes
├── mutation.py     600 LOC   AST mutation operators + mutation score
├── registry.py     280 LOC   SQLite + numpy cosine (replaces Supabase)
├── synthesis.py    190 LOC   spec → tests(FROZEN) → impl → bounded repair
├── agent.py        150 LOC   retrieve-or-synthesize → verify → gate → register
├── cli.py          110 LOC   the only interface
└── eval/
    ├── oracle.py   240 LOC   MBPP+ differential testing — the independent oracle
    ├── stats.py    200 LOC   FAR, AUC (Mann-Whitney), Wilson + bootstrap CIs
    ├── experiment_a.py  300 LOC   LLM-free weak-oracle study (suite-level gate)
    ├── per_tool.py      190 LOC   LLM-free study with the PER-TOOL gate
    └── experiment_b.py  230 LOC   the LLM arm (requires an API key)
```

~2,900 LOC replacing ~11,900, and unlike its predecessor it runs.

## 3. Root-cause fixes for the Track 2 findings

| Track 2 finding | Fix |
|---|---|
| **`executor.py` ran untrusted LLM code on the host** via `importlib.exec_module` | All execution routed through `sea/sandbox.py` — subprocess, rlimits, scrubbed env, process-group kill on timeout. There is no other execution path in the codebase. |
| **`_apply_aggressive_test_fixes` rewrote failing tests until they passed** | Deleted, not refactored. Replaced by a structural invariant: `tests` is frozen on a frozen dataclass, the repair loop is handed only the implementation, and `tests_sha256` pins the suite. `synthesis.py` carries an `assert` that fires if the suite ever changes mid-pipeline. (ADR-003) |
| **Tools that failed verification were registered as "experimental" and executed anyway** | `agent.py` returns `decision="failed_own_tests"` and registers **nothing**. Honest failure is a recorded outcome. |
| **`auto_tuner` scored candidates by distance to a hardcoded `0.45` and wrote it back as a learned optimum** | Deleted. Nothing in this codebase claims to learn or tune. The only threshold (`tau`) is *swept and reported*, never "discovered". |
| **`tables.sql` had no pgvector and zero of the six SQL functions Python called** — retrieval provably could not work | Supabase deleted. `registry.py` is SQLite + brute-force numpy cosine, which at a few hundred 1536-d vectors is microseconds and, crucially, *actually executes*. |
| **`config.validate()` raised inside a `try` that swallowed the error** — never failed fast | `Config.from_env()` raises `ConfigError`. Importing `sea.config` has **no** side effects; a regression test asserts that importing with no env set does not raise. |
| **`requirements.txt` omitted 5 imported packages and listed 6 unused ones** | Regenerated from actual imports: `numpy`, `openai`, `evalplus`, `pytest`. (`pytest` is a *runtime* dep — the sandbox shells out to `python -m pytest`.) |
| **`evaluation/tests/*` — 2,823 LOC with zero `assert` statements; 10/10 collection errors** | Deleted. Replaced by a real suite (see Phase 4). |

## 4. Grounding notes (verified, not recalled)

- **`gpt-4` is dead.** OpenAI's deprecation page gives shutdown **2026-10-23**. The old default would have stopped working in three months.
- **GPT-5.x are reasoning models and reject `temperature != default`.** This is a design constraint, not trivia: our `LLMClient.complete()` takes `temperature=0.0` for determinism, and a reasoning-model default would have silently made every run non-reproducible — destroying the replayability the response cache exists to provide. Default set to **`gpt-4.1-mini`** (non-reasoning, honours `temperature=0`, current). `llm.py` still supports reasoning models: on the 400 it drops `temperature`, warns loudly that the run is no longer deterministic, and remembers the capability. Degraded loudly, never silently.
- **`text-embedding-3-small` = 1536 dims** — confirmed against the current docs.
- **MBPP+ is 35× augmented, not 80×** (HumanEval+ is 80×). Track 1 had this wrong; corrected before it reached a results table.

## 5. Judgment calls worth knowing

- **`RLIMIT_AS` is unenforced on macOS.** This was *measured*, not assumed: a child asked for 2 GB under a 512 MB cap allocated it fine. `RLIMIT_DATA` is also unenforced, so it was not shipped as fake protection. On macOS the real backstop is `RLIMIT_CPU` (SIGXCPU verified at 2.01 s) plus the wall clock. The module docstring carries a per-platform table saying so. **We do not claim memory isolation we do not have.**
- **Sandbox output goes to files, not pipes.** A grandchild inheriting a pipe's write end deadlocks `communicate()` forever — a real hazard at 10⁵ executions.
- **Empty test suite → `error`, not `passed`.** pytest exits 5 on "no tests collected". Reporting that as a pass would let a tool be admitted on a *vacuous* oracle and silently corrupt FAR.
- **Docstrings are never mutated**, and `SDL` is confined to function bodies. A mutated docstring is unkillable by construction and would hand every tool a guaranteed survivor, biasing every score by a constant.
- **`preexec_fn` is not thread-safe**, so the eval harness parallelises with **processes**. (Python 3.14 uses `spawn` on macOS, which is why the CLI needs a `__main__` guard.)

## 6. Residual risk

- Per-execution isolation is a **safety** boundary, not a **security** boundary (ADR-002). Stated in the README, the sandbox docstring, and the report. Anyone running this against untrusted prompts should run the whole harness in a container.
- Equivalent mutants are not detected (undecidable in general). They depress mutation scores slightly and roughly uniformly. Not solved; disclosed.
- **Experiment B (the LLM arm) has never been executed** — no API key was available in this environment. The code path is complete and tested with a `FakeLLM` at the LLM seam, but **no LLM-arm numbers are reported, because none were produced.** See Phase 4.
