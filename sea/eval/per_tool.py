"""Experiment A2 -- the PER-TOOL gate. The faithful analogue of the thesis.

Experiment A gates at the *suite* level: the adequacy score is a property of the
(task, admitting-suite) pair, so every candidate for a task shares one score.
That gate can only discriminate *between* tasks -- it is structurally blind to
the fact that, within a single task, some admitted tools are equivalent mutants
(harmless) and others are genuinely wrong. Testing H3 that way handicaps the
hypothesis before it starts.

The thesis gates PER TOOL:

    Take the tool's own implementation. Mutate IT. Ask whether the tool's own
    admitting suite notices. That score -- specific to this one artefact -- is
    the gate.

That is exactly what `sea.agent` does in the LLM arm. Here we reproduce it in
the LLM-free setting: for each ADMITTED candidate (an admitted mutant), we
generate second-order mutants of *that candidate's* code and ask how many the
weak suite kills. The result is a per-tool adequacy score with real
within-task variance, and H2/H3 can be tested as actually stated.

Fully deterministic: same seed => same first-order mutants => same admitted set.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sea.eval.oracle import Task, check_candidate, load_tasks
from sea.eval.stats import auc_with_ci, far, paired_auc_delta_ci, wilson_ci
from sea.mutation import generate_mutants

__all__ = ["run_per_tool_gate"]


@dataclass(frozen=True)
class ToolRow:
    task_id: str
    mutant_index: int
    operator: str
    per_tool_adequacy: float   # weak suite's mutation score ON THIS TOOL
    n_second_order: int
    strong_pass: bool          # against the independent oracle


def _weak_kills(task: Task, impl: str, call_timeout_s: float) -> bool:
    """Does the weak suite (base_input) reject this implementation?"""
    return not check_candidate(task, impl, call_timeout_s=call_timeout_s).weak_pass


def _score_task(
    task: Task,
    max_mutants: int,
    second_order: int,
    seed: int,
    min_mutants: int,
    call_timeout_s: float,
) -> list[ToolRow]:
    """Rebuild this task's admitted set, then score each admitted tool per-tool."""
    ref = check_candidate(task, task.canonical_solution, call_timeout_s=call_timeout_s)
    if not (ref.weak_pass and ref.strong_pass):
        return []

    mutants = generate_mutants(task.canonical_solution, max_mutants=max_mutants, seed=seed)
    if len(mutants) < min_mutants:
        return []

    # Identical split to Experiment A -- same seed, same shuffle, same held-out set.
    rng = random.Random(f"{task.task_id}:{seed}")
    shuffled = list(mutants)
    rng.shuffle(shuffled)
    candidate_set = shuffled[len(shuffled) // 2 :]

    rows: list[ToolRow] = []
    for m in candidate_set:
        v = check_candidate(task, m.code, call_timeout_s=call_timeout_s)
        if not v.weak_pass:
            continue  # never admitted; FAR is conditional on admission

        # --- the per-tool gate: mutate THIS tool, ask if the suite notices ---
        second = generate_mutants(m.code, max_mutants=second_order, seed=seed)
        if not second:
            continue
        killed = sum(1 for s in second if _weak_kills(task, s.code, call_timeout_s))
        rows.append(
            ToolRow(
                task_id=task.task_id,
                mutant_index=m.index,
                operator=m.operator,
                per_tool_adequacy=killed / len(second),
                n_second_order=len(second),
                strong_pass=v.strong_pass,
            )
        )
    return rows


def run_per_tool_gate(
    *,
    limit: int | None = None,
    max_mutants: int = 40,
    min_mutants: int = 6,
    second_order: int = 20,
    seed: int = 0,
    workers: int = 10,
    call_timeout_s: float = 1.0,
    out_dir: Path = Path("results"),
) -> dict[str, Any]:
    tasks = load_tasks(limit=limit)
    print(f"[exp-a2] per-tool gate over {len(tasks)} tasks "
          f"(second-order mutants/tool <= {second_order})")

    rows: list[ToolRow] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = [
            pool.submit(_score_task, t, max_mutants, second_order, seed,
                        min_mutants, call_timeout_s)
            for t in tasks
        ]
        for i, fut in enumerate(as_completed(futs), 1):
            rows.extend(fut.result())
            if i % 50 == 0 or i == len(tasks):
                print(f"[exp-a2] {i}/{len(tasks)} tasks | {len(rows)} admitted tools",
                      flush=True)

    if not rows:
        raise RuntimeError("no admitted tools -- nothing to gate")

    labels = np.array([0 if r.strong_pass else 1 for r in rows])
    # Predict false admission from LOW per-tool adequacy -> negate.
    pred = np.array([-r.per_tool_adequacy for r in rows])
    # Naive baseline: how many second-order mutants existed at all (a proxy for
    # code size). If adequacy is just measuring "bigger code", this catches it.
    size_pred = np.array([-float(r.n_second_order) for r in rows])

    base = far([True] * len(rows), [r.strong_pass for r in rows])
    auc_ad = auc_with_ci(pred, labels, seed=seed)
    auc_sz = auc_with_ci(size_pred, labels, seed=seed)
    d, d_lo, d_hi = paired_auc_delta_ci(pred, size_pred, labels, seed=seed)

    gate = []
    for tau in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        keep = [r for r in rows if r.per_tool_adequacy >= tau]
        n, k = len(keep), sum(1 for r in keep if not r.strong_pass)
        rate = k / n if n else 0.0
        lo, hi = wilson_ci(k, n)
        gate.append({
            "tau": tau, "n_admitted": n, "n_false_admissions": k,
            "far": rate, "far_lo": lo, "far_hi": hi,
            "coverage": n / len(rows),
            "far_reduction_vs_baseline": (
                1.0 - rate / base.value if base.value > 0 else 0.0),
        })

    summary = {
        "experiment": "A2 (LLM-free; PER-TOOL mutation gate)",
        "config": {"n_tasks": len(tasks), "second_order": second_order, "seed": seed},
        "H1_far": {"far": base.value, "ci95": [base.lo, base.hi],
                   "n_false_admissions": base.numerator,
                   "n_admitted": base.denominator},
        "H2_predictor": {
            "auc_per_tool_adequacy": {"value": auc_ad.value,
                                      "ci95": [auc_ad.lo, auc_ad.hi]},
            "auc_code_size_baseline": {"value": auc_sz.value,
                                       "ci95": [auc_sz.lo, auc_sz.hi]},
            "auc_delta": {"value": d, "ci95": [d_lo, d_hi]},
        },
        "H3_gate": gate,
        "per_tool": [r.__dict__ for r in rows],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "experiment_a2_per_tool.json").write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 68)
    print("EXPERIMENT A2 -- PER-TOOL mutation gate (the thesis as stated)")
    print("=" * 68)
    print(f"admitted tools: {base.denominator}   false admissions: {base.numerator}")
    print(f"\n-- H1 --  FAR = {base.value:.1%} [{base.lo:.1%}, {base.hi:.1%}]")
    print(f"\n-- H2 --  per-tool adequacy : AUC={auc_ad.value:.3f} "
          f"[{auc_ad.lo:.3f}, {auc_ad.hi:.3f}]")
    print(f"          code-size baseline: AUC={auc_sz.value:.3f} "
          f"[{auc_sz.lo:.3f}, {auc_sz.hi:.3f}]")
    print(f"          delta             : {d:+.3f} [{d_lo:+.3f}, {d_hi:+.3f}]"
          f"   -> {'SUPPORTED' if d_lo > 0 else 'NOT SUPPORTED'}")
    print(f"\n-- H3 --  {'tau':>5} {'admitted':>9} {'FAR':>8} {'coverage':>9} {'reduction':>10}")
    for r in gate:
        print(f"          {r['tau']:>5.1f} {r['n_admitted']:>9d} {r['far']:>7.1%} "
              f"{r['coverage']:>8.1%} {r['far_reduction_vs_baseline']:>9.1%}")
    ok = [r for r in gate
          if r["far_reduction_vs_baseline"] >= 0.5 and r["coverage"] >= 0.5]
    if ok:
        b = ok[0]
        print(f"\n   H3: SUPPORTED at tau={b['tau']:.1f} "
              f"(FAR {base.value:.1%} -> {b['far']:.1%}, coverage {b['coverage']:.0%})")
    else:
        print("\n   H3: NOT SUPPORTED -- no tau halves FAR at >=50% coverage")
    print("=" * 68 + "\n")
    return summary
