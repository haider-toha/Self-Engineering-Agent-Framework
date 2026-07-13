"""Experiment B -- the LLM arm. The thesis proper.

For each MBPP+ task the agent synthesizes a tool via TDD, writing its OWN test
suite from the natural-language prompt alone. It never sees MBPP+'s inputs. The
tool is admitted on its own tests (baseline) or on its own tests plus the
mutation-adequacy gate (treatment). Only AFTER admission do we score the tool
against MBPP+'s independent oracle.

    FAR = P(fails MBPP+ | passed its own tests and was admitted)

ONE SYNTHESIS PASS, BOTH ARMS
-----------------------------
We synthesize once, record the mutation score once, and score against MBPP+
once. Both arms are then recovered by post-hoc filtering on the recorded
mutation score. This is statistically valid -- the gate is a deterministic
function of data already collected -- and it means the entire tau sweep costs
zero additional API calls. It also guarantees the two arms see *identical*
tools, so any FAR difference is attributable to the gate and nothing else.

REQUIRES AN API KEY. There is no offline fallback and there must not be one:
a fabricated LLM would produce fabricated numbers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sea.config import Config
from sea.eval.oracle import check_candidate, load_tasks
from sea.eval.stats import auc_with_ci, far, paired_auc_delta_ci, wilson_ci
from sea.llm import OpenAIClient
from sea.mutation import mutation_score
from sea.registry import Registry, ToolRecord
from sea.synthesis import SynthesisError, synthesize

__all__ = ["run_experiment_b"]


@dataclass
class ToolOutcome:
    task_id: str
    function_name: str | None
    passed_own_tests: bool
    repair_attempts: int
    n_tests: int
    mutation_score: float | None
    mutants_total: int
    strong_pass: bool | None      # against MBPP+ -- the independent oracle
    reused_from: str | None
    error: str | None


def run_experiment_b(
    *,
    limit: int | None = None,
    seed: int = 0,
    max_repairs: int = 3,
    mutation_max: int = 30,
    out_dir: Path = Path("results"),
) -> dict[str, Any]:
    cfg = Config.from_env()  # raises ConfigError without a key -- fail fast
    llm = OpenAIClient(cfg)
    tasks = load_tasks(limit=limit)

    db = out_dir / "experiment_b.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    registry = Registry(db)

    print(f"[exp-b] {len(tasks)} tasks | model={cfg.model} | cache={cfg.cache_dir}")

    outcomes: list[ToolOutcome] = []
    for i, task in enumerate(tasks, 1):
        # Retrieval is measured, never assumed. If the library has a
        # near-paraphrase we reuse it and record that; MBPP+ tasks are largely
        # independent so we expect this to be rare, and we report whatever it is.
        reused = None
        hits = registry.search(llm.embed(task.prompt), k=1)
        if hits and hits[0][1] >= cfg.retrieval_threshold:
            rec, score = hits[0]
            registry.record_retrieval(rec.name, task.task_id, score)
            reused = rec.name

        try:
            res = synthesize(llm, task.prompt, max_repairs=max_repairs)
        except SynthesisError as exc:
            outcomes.append(ToolOutcome(
                task.task_id, None, False, 0, 0, None, 0, None, reused, str(exc)))
            continue

        # Mutation adequacy of the suite that would admit this tool. Recorded for
        # EVERY tool that passes its own tests, so both arms can be recovered
        # post hoc from one pass.
        ms: float | None = None
        n_mut = 0
        if res.passed_own_tests:
            try:
                rep = mutation_score(
                    res.code, res.tests, max_mutants=mutation_max, seed=seed
                )
                ms, n_mut = rep.score, rep.total
            except ValueError as exc:
                outcomes.append(ToolOutcome(
                    task.task_id, res.spec.function_name, True,
                    res.repair_attempts, res.tests.count("def test_"),
                    None, 0, None, reused, f"mutation: {exc}"))
                continue

        # The independent oracle. Scored only now, and never fed back.
        strong: bool | None = None
        if res.passed_own_tests:
            v = check_candidate(task, res.code)
            strong = v.strong_pass
            registry.add(
                ToolRecord(
                    name=res.spec.function_name, task_id=task.task_id,
                    code=res.code, tests=res.tests,
                    docstring=res.spec.docstring, mutation_score=ms,
                    created_at="",
                ),
                embedding=llm.embed(res.spec.docstring),
            )

        outcomes.append(ToolOutcome(
            task_id=task.task_id,
            function_name=res.spec.function_name,
            passed_own_tests=res.passed_own_tests,
            repair_attempts=res.repair_attempts,
            n_tests=res.tests.count("def test_"),
            mutation_score=ms,
            mutants_total=n_mut,
            strong_pass=strong,
            reused_from=reused,
            error=None,
        ))

        if i % 10 == 0 or i == len(tasks):
            adm = sum(1 for o in outcomes if o.passed_own_tests)
            bad = sum(1 for o in outcomes if o.passed_own_tests and o.strong_pass is False)
            print(f"[exp-b] {i}/{len(tasks)} | admitted={adm} | false={bad} "
                  f"| cache={llm.cache_stats()}", flush=True)

    # ---- Analysis ------------------------------------------------------------
    admitted = [o for o in outcomes
                if o.passed_own_tests and o.strong_pass is not None
                and o.mutation_score is not None]

    weak = [True] * len(admitted)  # every one of these passed its own suite
    strong = [bool(o.strong_pass) for o in admitted]
    far_base = far(weak, strong)

    labels = np.array([0 if o.strong_pass else 1 for o in admitted])
    mut_pred = np.array([-(o.mutation_score or 0.0) for o in admitted])
    # In the LLM arm the naive baselines are NOT degenerate: the model chooses
    # how many tests to write, and how many repairs it needed.
    size_pred = np.array([-float(o.n_tests) for o in admitted])

    auc_mut = auc_with_ci(mut_pred, labels, seed=seed)
    auc_size = auc_with_ci(size_pred, labels, seed=seed)
    d, d_lo, d_hi = paired_auc_delta_ci(mut_pred, size_pred, labels, seed=seed)

    gate_rows = []
    for tau in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        keep = [o for o in admitted if (o.mutation_score or 0.0) >= tau]
        n_adm = len(keep)
        n_fa = sum(1 for o in keep if not o.strong_pass)
        rate = n_fa / n_adm if n_adm else 0.0
        lo, hi = wilson_ci(n_fa, n_adm)
        gate_rows.append({
            "tau": tau, "n_admitted": n_adm, "n_false_admissions": n_fa,
            "far": rate, "far_lo": lo, "far_hi": hi,
            "coverage": n_adm / far_base.denominator if far_base.denominator else 0.0,
            "far_reduction_vs_baseline": (
                1.0 - rate / far_base.value if far_base.value > 0 else 0.0),
        })

    summary = {
        "experiment": "B (LLM arm)",
        "config": {
            "model": cfg.model, "embedding_model": cfg.embedding_model,
            "n_tasks": len(tasks), "seed": seed, "max_repairs": max_repairs,
            "mutation_max": mutation_max,
        },
        "pipeline": {
            "n_tasks": len(outcomes),
            "n_synthesis_errors": sum(1 for o in outcomes if o.error),
            "n_failed_own_tests": sum(1 for o in outcomes if not o.passed_own_tests),
            "n_admitted_baseline": far_base.denominator,
            "n_reused": sum(1 for o in outcomes if o.reused_from),
        },
        "H1_far": {
            "far": far_base.value, "ci95": [far_base.lo, far_base.hi],
            "n_false_admissions": far_base.numerator,
            "n_admitted": far_base.denominator,
        },
        "H2_predictor": {
            "auc_mutation_score": {"value": auc_mut.value,
                                   "ci95": [auc_mut.lo, auc_mut.hi]},
            "auc_test_count_baseline": {"value": auc_size.value,
                                        "ci95": [auc_size.lo, auc_size.hi]},
            "auc_delta": {"value": d, "ci95": [d_lo, d_hi]},
        },
        "H3_gate": gate_rows,
        "reuse": registry.reuse_stats(),
        "llm_cache": llm.cache_stats(),
        "per_task": [o.__dict__ for o in outcomes],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "experiment_b.json").write_text(json.dumps(summary, indent=2))
    registry.close()

    h1 = summary["H1_far"]
    print("\n" + "=" * 68)
    print("EXPERIMENT B -- LLM arm")
    print("=" * 68)
    print(f"FAR = {h1['far']:.1%} [{h1['ci95'][0]:.1%}, {h1['ci95'][1]:.1%}] "
          f"({h1['n_false_admissions']}/{h1['n_admitted']})")
    print(f"AUC(mutation) = {auc_mut.value:.3f}   AUC(test count) = {auc_size.value:.3f}")
    print(f"delta = {d:+.3f} [{d_lo:+.3f}, {d_hi:+.3f}]")
    print("=" * 68)
    return summary
