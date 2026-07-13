"""Experiment A -- Does a weak admission oracle admit wrong code?

This is the LLM-free arm. It requires no API key, runs on CPU, and produces
real numbers from real executions. It exists because the phenomenon under
study -- a weak, self-consistent suite admitting an incorrect tool -- does not
actually require an LLM to *exhibit*. It requires only (a) plausible wrong
implementations, (b) a weak admitting suite, and (c) an independent oracle.
MBPP+ supplies all three.

    (a) wrong implementations  <- mutants of the human canonical solution
    (b) weak admitting suite   <- MBPP's original 3 assertions (`base_input`)
    (c) independent oracle     <- MBPP+'s ~111 inputs (35x augmentation)

WHY THIS IS A FAITHFUL PROXY, AND WHERE IT IS NOT
-------------------------------------------------
Faithful: MBPP's natural-language prompt literally *embeds* those same 3
assertions, so an LLM asked to write tests from the prompt tends to reproduce a
suite of roughly this strength. The admitting oracle in the LLM arm is
therefore about as weak as the one here.

Not faithful: mutants are not LLM-written code. Their error distribution is
operator-shaped (off-by-one, flipped comparison, dropped branch), not
model-shaped. Experiment A therefore establishes the *mechanism* and validates
the *apparatus*; it does not substitute for the LLM arm (Experiment B), and we
never report its numbers as if it did.

AVOIDING CIRCULARITY (this is the crux)
---------------------------------------
Both the adequacy signal and the candidate implementations are drawn from the
same mutant population. Scoring a suite's adequacy on the very mutants we then
ask it to admit would make the correlation mechanical and meaningless.

So we split, per task, deterministically and disjointly:

    ADEQUACY SET  -- used ONLY to measure the weak suite's mutation score.
    CANDIDATE SET -- used ONLY as the tools seeking admission. Held out.

The suite's mutation score is computed on mutants it never has to admit; the
false-admission rate is computed on mutants that never informed the score. A
train/test split. The prediction in H2 is genuinely out-of-sample.
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sea.eval.oracle import Task, check_candidate, load_tasks
from sea.eval.stats import auc_with_ci, far, paired_auc_delta_ci, wilson_ci
from sea.mutation import generate_mutants

__all__ = ["CandidateOutcome", "TaskResult", "run_experiment_a"]


@dataclass(frozen=True)
class CandidateOutcome:
    task_id: str
    mutant_index: int
    operator: str
    role: str  # "adequacy" | "candidate"
    weak_pass: bool
    strong_pass: bool
    error: str | None


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    entry_point: str
    n_weak_inputs: int
    n_strong_inputs: int
    n_mutants: int
    adequacy_mutation_score: float  # weak suite's score, on the ADEQUACY set
    n_candidates: int
    n_admitted: int
    n_false_admissions: int
    outcomes: list[CandidateOutcome]


def _evaluate_task(
    task: Task,
    max_mutants: int,
    seed: int,
    call_timeout_s: float,
    min_mutants: int = 6,
) -> TaskResult | None:
    """Run one task end to end. Returns None if the task is unusable."""
    # Gate 1: the canonical solution must pass its own oracles. If it does not,
    # the task's data is broken and every downstream number would be garbage.
    ref = check_candidate(task, task.canonical_solution, call_timeout_s=call_timeout_s)
    if not (ref.weak_pass and ref.strong_pass):
        return None

    mutants = generate_mutants(
        task.canonical_solution, max_mutants=max_mutants, seed=seed
    )
    # Below this, the disjoint split leaves too few mutants on each side for the
    # adequacy estimate to mean anything. MBPP canonical solutions are short, so
    # this excludes a real slice of the benchmark -- reported, never hidden.
    if len(mutants) < min_mutants:
        return None

    # Deterministic, task-scoped disjoint split.
    rng = random.Random(f"{task.task_id}:{seed}")
    shuffled = list(mutants)
    rng.shuffle(shuffled)
    half = len(shuffled) // 2
    adequacy_set, candidate_set = shuffled[:half], shuffled[half:]

    outcomes: list[CandidateOutcome] = []

    def _run(ms: list[Any], role: str) -> list[CandidateOutcome]:
        out = []
        for m in ms:
            v = check_candidate(task, m.code, call_timeout_s=call_timeout_s)
            out.append(
                CandidateOutcome(
                    task_id=task.task_id,
                    mutant_index=m.index,
                    operator=m.operator,
                    role=role,
                    weak_pass=v.weak_pass,
                    strong_pass=v.strong_pass,
                    error=v.error,
                )
            )
        return out

    adequacy_outcomes = _run(adequacy_set, "adequacy")
    candidate_outcomes = _run(candidate_set, "candidate")
    outcomes = adequacy_outcomes + candidate_outcomes

    # The weak suite's mutation score: fraction of ADEQUACY mutants it kills.
    # "Killed" == the suite noticed the fault == the mutant fails the weak oracle.
    killed = sum(1 for o in adequacy_outcomes if not o.weak_pass)
    adequacy_score = killed / len(adequacy_outcomes) if adequacy_outcomes else 0.0

    admitted = [o for o in candidate_outcomes if o.weak_pass]
    false_admissions = [o for o in admitted if not o.strong_pass]

    return TaskResult(
        task_id=task.task_id,
        entry_point=task.entry_point,
        n_weak_inputs=task.n_weak,
        n_strong_inputs=task.n_strong,
        n_mutants=len(mutants),
        adequacy_mutation_score=adequacy_score,
        n_candidates=len(candidate_outcomes),
        n_admitted=len(admitted),
        n_false_admissions=len(false_admissions),
        outcomes=outcomes,
    )


def run_experiment_a(
    *,
    limit: int | None = None,
    max_mutants: int = 40,
    min_mutants: int = 6,
    seed: int = 0,
    workers: int = 8,
    call_timeout_s: float = 1.0,
    out_dir: Path = Path("results"),
) -> dict[str, Any]:
    """Run Experiment A and write results to `out_dir`."""
    tasks = load_tasks(limit=limit)
    print(f"[exp-a] loaded {len(tasks)} MBPP+ tasks")
    print(f"[exp-a] mutants/task<={max_mutants} (min {min_mutants}), "
          f"workers={workers}, seed={seed}")

    results: list[TaskResult] = []
    skipped: list[str] = []

    # Processes, not threads: sandbox.run_script uses preexec_fn, which is not
    # thread-safe (it runs Python between fork and exec).
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                _evaluate_task, t, max_mutants, seed, call_timeout_s, min_mutants
            ): t
            for t in tasks
        }
        done = 0
        for fut in as_completed(futs):
            task = futs[fut]
            done += 1
            try:
                r = fut.result()
            except Exception as exc:  # noqa: BLE001 - report, never silently drop
                skipped.append(f"{task.task_id}: {type(exc).__name__}: {exc}")
                continue
            if r is None:
                skipped.append(f"{task.task_id}: unusable (bad canonical or too few mutants)")
            else:
                results.append(r)
            if done % 25 == 0 or done == len(tasks):
                print(f"[exp-a] {done}/{len(tasks)} tasks", flush=True)

    if not results:
        raise RuntimeError("no usable tasks -- cannot compute FAR")

    # `as_completed` yields in completion order, which varies with process
    # scheduling. The statistics are unaffected (they are order-invariant), but
    # the serialized artefact would not be byte-reproducible -- and a reviewer
    # is entitled to diff two runs and get silence. Sort by task id.
    results.sort(key=lambda r: int(r.task_id.split("/")[-1]))
    skipped.sort()

    # ---------------- H1: magnitude of FAR ----------------
    cand = [o for r in results for o in r.outcomes if o.role == "candidate"]
    weak = [o.weak_pass for o in cand]
    strong = [o.strong_pass for o in cand]
    far_overall = far(weak, strong)

    # ---------------- H2: does adequacy predict false admission? ----------------
    # Population: ADMITTED candidates only (FAR is conditional on admission).
    # Predictor: the adequacy score of that candidate's task -- computed on the
    # DISJOINT adequacy set, so this is a held-out prediction.
    # Label: 1 == false admission (admitted but wrong).
    score_by_task = {r.task_id: r.adequacy_mutation_score for r in results}
    admitted = [o for o in cand if o.weak_pass]

    labels = np.array([0 if o.strong_pass else 1 for o in admitted])
    # We predict *false admission* from a LOW adequacy score, so the score
    # enters negated.
    mut_pred = np.array([-score_by_task[o.task_id] for o in admitted])

    # Naive baseline: suite size. In Experiment A this is ~constant (MBPP ships
    # 3 assertions for nearly every task), so it is a degenerate predictor by
    # construction. We report it anyway, and say so, rather than quietly
    # choosing a baseline that flatters us.
    size_by_task = {r.task_id: r.n_weak_inputs for r in results}
    size_pred = np.array([-float(size_by_task[o.task_id]) for o in admitted])

    auc_mut = auc_with_ci(mut_pred, labels, seed=seed)
    auc_size = auc_with_ci(size_pred, labels, seed=seed)
    d, d_lo, d_hi = paired_auc_delta_ci(mut_pred, size_pred, labels, seed=seed)

    # Sensitivity: MBPP canonical solutions are short, so on many tasks the
    # adequacy score is estimated from only ~3 mutants and is very noisy. Repeat
    # H2 on tasks where the estimate is well-powered (>=10 mutants => >=5 in the
    # adequacy half). If the effect is an artefact of noisy estimates, it should
    # weaken here. If it is real, it should hold or strengthen.
    nmut_by_task = {r.task_id: r.n_mutants for r in results}
    well = [o for o in admitted if nmut_by_task[o.task_id] >= 10]
    if well:
        w_labels = np.array([0 if o.strong_pass else 1 for o in well])
        w_pred = np.array([-score_by_task[o.task_id] for o in well])
        auc_well = auc_with_ci(w_pred, w_labels, seed=seed)
        sensitivity = {
            "n_tasks": len({o.task_id for o in well}),
            "n_admitted": len(well),
            "auc_mutation_score": {
                "value": auc_well.value,
                "ci95": [auc_well.lo, auc_well.hi],
                "n_pos": auc_well.n_pos,
                "n_neg": auc_well.n_neg,
            },
        }
    else:
        sensitivity = {"n_admitted": 0, "note": "no well-powered tasks"}

    # ---------------- H3: the admission gate ----------------
    # Gate: admit a tool only if its admitting suite's adequacy >= tau.
    # In Experiment A the gate is necessarily suite-level (every candidate for a
    # task shares one admitting suite). In the LLM arm it is per-tool, as the
    # thesis specifies, because each synthesized tool carries its own suite.
    baseline_admitted = far_overall.denominator
    gate_rows = []
    for tau in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        keep = [o for o in admitted if score_by_task[o.task_id] >= tau]
        n_adm = len(keep)
        n_fa = sum(1 for o in keep if not o.strong_pass)
        rate = n_fa / n_adm if n_adm else 0.0
        lo, hi = wilson_ci(n_fa, n_adm)
        gate_rows.append(
            {
                "tau": tau,
                "n_admitted": n_adm,
                "n_false_admissions": n_fa,
                "far": rate,
                "far_lo": lo,
                "far_hi": hi,
                "coverage": (n_adm / baseline_admitted) if baseline_admitted else 0.0,
                "far_reduction_vs_baseline": (
                    1.0 - (rate / far_overall.value) if far_overall.value > 0 else 0.0
                ),
            }
        )

    summary: dict[str, Any] = {
        "experiment": "A (LLM-free; mutants of canonical solutions)",
        "config": {
            "n_tasks_loaded": len(tasks),
            "n_tasks_used": len(results),
            "n_tasks_skipped": len(skipped),
            "max_mutants": max_mutants,
            "seed": seed,
        },
        "totals": {
            "n_candidates": len(cand),
            "n_admitted": far_overall.denominator,
            "n_false_admissions": far_overall.numerator,
        },
        "H1_far": {
            "far": far_overall.value,
            "ci95": [far_overall.lo, far_overall.hi],
            "n_false_admissions": far_overall.numerator,
            "n_admitted": far_overall.denominator,
        },
        "H2_predictor": {
            "auc_mutation_score": {
                "value": auc_mut.value,
                "ci95": [auc_mut.lo, auc_mut.hi],
                "n_pos": auc_mut.n_pos,
                "n_neg": auc_mut.n_neg,
            },
            "auc_suite_size_baseline": {
                "value": auc_size.value,
                "ci95": [auc_size.lo, auc_size.hi],
                "note": "degenerate in Experiment A: MBPP ships ~3 assertions for every task",
            },
            "auc_delta_mutation_minus_size": {
                "value": d,
                "ci95": [d_lo, d_hi],
            },
            "sensitivity_well_powered_tasks": sensitivity,
        },
        "H3_gate": gate_rows,
        "skipped_tasks": skipped[:50],
        "per_task": [
            {k: v for k, v in asdict(r).items() if k != "outcomes"} for r in results
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "experiment_a.json").write_text(json.dumps(summary, indent=2))
    raw = [asdict(o) for r in results for o in r.outcomes]
    (out_dir / "experiment_a_raw.json").write_text(json.dumps(raw, indent=2))

    _print_report(summary)
    return summary


def _print_report(s: dict[str, Any]) -> None:
    h1, h2 = s["H1_far"], s["H2_predictor"]
    print("\n" + "=" * 68)
    print("EXPERIMENT A -- weak admission oracle vs. independent oracle")
    print("=" * 68)
    c = s["config"]
    print(f"tasks used: {c['n_tasks_used']}/{c['n_tasks_loaded']} "
          f"(skipped {c['n_tasks_skipped']})")
    t = s["totals"]
    print(f"candidates: {t['n_candidates']}  admitted: {t['n_admitted']}  "
          f"false admissions: {t['n_false_admissions']}")

    print("\n-- H1: FAR = P(fails independent oracle | admitted) --")
    print(f"   FAR = {h1['far']:.1%}  95% CI [{h1['ci95'][0]:.1%}, {h1['ci95'][1]:.1%}]"
          f"   ({h1['n_false_admissions']}/{h1['n_admitted']})")
    verdict = "SUPPORTED" if h1["far"] >= 0.15 else (
        "KILLED (FAR < 5%)" if h1["far"] < 0.05 else "WEAK (5% <= FAR < 15%)")
    print(f"   H1 (FAR >= 15%): {verdict}")

    print("\n-- H2: does admitting-suite adequacy predict false admission? --")
    am = h2["auc_mutation_score"]
    print(f"   mutation score : AUC={am['value']:.3f} "
          f"[{am['ci95'][0]:.3f}, {am['ci95'][1]:.3f}]")
    asz = h2["auc_suite_size_baseline"]
    print(f"   suite size     : AUC={asz['value']:.3f}  (degenerate -- see note)")
    dd = h2["auc_delta_mutation_minus_size"]
    print(f"   delta          : {dd['value']:+.3f} "
          f"[{dd['ci95'][0]:+.3f}, {dd['ci95'][1]:+.3f}]")
    sig = dd["ci95"][0] > 0
    print(f"   H2 (mutation beats baseline, CI excludes 0): "
          f"{'SUPPORTED' if sig else 'NOT SUPPORTED'}")
    sens = h2.get("sensitivity_well_powered_tasks", {})
    if sens.get("n_admitted"):
        sa = sens["auc_mutation_score"]
        print(f"   sensitivity (tasks with >=10 mutants, n={sens['n_admitted']} admitted): "
              f"AUC={sa['value']:.3f} [{sa['ci95'][0]:.3f}, {sa['ci95'][1]:.3f}]")

    print("\n-- H3: admission gate (tau on suite adequacy) --")
    print(f"   {'tau':>5} {'admitted':>9} {'FAR':>8} {'coverage':>9} {'FAR reduction':>14}")
    for r in s["H3_gate"]:
        print(f"   {r['tau']:>5.1f} {r['n_admitted']:>9d} {r['far']:>7.1%} "
              f"{r['coverage']:>8.1%} {r['far_reduction_vs_baseline']:>13.1%}")
    ok = [r for r in s["H3_gate"]
          if r["far_reduction_vs_baseline"] >= 0.5 and r["coverage"] >= 0.5]
    if ok:
        b = ok[0]
        print(f"   H3 (>=50% FAR reduction at >=50% coverage): SUPPORTED at tau={b['tau']:.1f} "
              f"(FAR {h1['far']:.1%} -> {b['far']:.1%}, coverage {b['coverage']:.0%})")
    else:
        print("   H3: NOT SUPPORTED -- no tau halves FAR while retaining >=50% coverage")
    print("=" * 68 + "\n")
