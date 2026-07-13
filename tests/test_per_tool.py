"""Tests for `sea.eval.per_tool` -- Experiment A2, the per-tool mutation gate.

Two things are checked here, both on real MBPP+ data.

**The split.** A2 re-derives its candidate set from the same seed as Experiment A
so that the two experiments score the *same* admitted tools and their numbers can
be compared. That is not a stylistic preference -- if the two split differently,
A and A2 would be measuring different populations and every "the per-tool gate
does better than the suite-level gate" claim would be comparing apples to
oranges. So the split is checked against Experiment A's own output, rather than
by restating the shuffling logic (which would pass no matter what either module
did).

**The sweep.** `run_per_tool_gate` is executed end to end and its summary is
checked for well-formedness and internal consistency -- in particular that
coverage falls monotonically as the gate tightens.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sea.eval.experiment_a import _evaluate_task
from sea.eval.oracle import Task, load_tasks
from sea.eval.per_tool import _score_task, run_per_tool_gate

#: The defaults both experiments run with. The split reproduces only if the
#: mutant pool is identical, which means `max_mutants` and `seed` must agree --
#: the tests below would catch the two drifting apart.
MAX_MUTANTS = 40
MIN_MUTANTS = 6
SECOND_ORDER = 20
SEED = 0
CALL_TIMEOUT_S = 1.0


@pytest.fixture(scope="module")
def tasks() -> dict[str, Task]:
    return {task.task_id: task for task in load_tasks(limit=10)}


@pytest.fixture(scope="module")
def admitting_task(tasks: dict[str, Task]) -> Task:
    """Mbpp/9 -- the first task with enough mutants AND a non-empty admitted set.

    (Mbpp/2, /4, /7, /8 yield fewer than six mutants and are skipped; Mbpp/3, /6
    and /11 have their entire candidate set killed by the weak suite.)
    """
    return tasks["Mbpp/9"]


@pytest.fixture(scope="module")
def rejecting_task(tasks: dict[str, Task]) -> Task:
    """Mbpp/3 -- enough mutants, but the weak suite kills every candidate."""
    return tasks["Mbpp/3"]


def experiment_a_split(task: Task) -> tuple[set[int], set[int], set[int]]:
    """Experiment A's own (adequacy, candidate, admitted) mutant indices."""
    result = _evaluate_task(task, MAX_MUTANTS, SEED, CALL_TIMEOUT_S, MIN_MUTANTS)
    assert result is not None, f"{task.task_id} is unusable in Experiment A"

    adequacy = {o.mutant_index for o in result.outcomes if o.role == "adequacy"}
    candidate = {o.mutant_index for o in result.outcomes if o.role == "candidate"}
    admitted = {
        o.mutant_index
        for o in result.outcomes
        if o.role == "candidate" and o.weak_pass
    }
    return adequacy, candidate, admitted


def per_tool_rows(task: Task) -> list[Any]:
    return _score_task(
        task, MAX_MUTANTS, SECOND_ORDER, SEED, MIN_MUTANTS, CALL_TIMEOUT_S
    )


# ---------------------------------------------------------------------------
# The split must reproduce Experiment A's, or the two experiments are not
# comparable.
# ---------------------------------------------------------------------------


def test_per_tool_scores_exactly_the_tools_experiment_a_admitted(
    admitting_task: Task,
) -> None:
    """A2's scored set is A's admitted set. Same seed, same tools."""
    _, _, admitted = experiment_a_split(admitting_task)
    scored = {row.mutant_index for row in per_tool_rows(admitting_task)}

    assert scored, "precondition: this task must admit something to compare"
    assert scored == admitted


def test_per_tool_never_scores_a_tool_from_the_adequacy_half(
    admitting_task: Task,
) -> None:
    """The held-out split is what keeps H2 out-of-sample.

    If A2 drew from A's adequacy half, the adequacy signal and the candidates
    would come from the same mutants and the correlation would be mechanical.
    A different shuffle would show up here as an overlap.
    """
    adequacy, candidate, _ = experiment_a_split(admitting_task)
    scored = {row.mutant_index for row in per_tool_rows(admitting_task)}

    assert scored <= candidate, "A2 scored a tool outside A's candidate set"
    assert not (scored & adequacy), "A2 leaked into A's adequacy half"


def test_experiment_a_splits_the_mutants_into_two_disjoint_halves(
    admitting_task: Task,
) -> None:
    """Sanity-check the baseline the comparison above rests on."""
    adequacy, candidate, _ = experiment_a_split(admitting_task)

    assert not (adequacy & candidate)
    assert adequacy and candidate


def test_the_two_experiments_agree_on_the_independent_oracle(
    admitting_task: Task,
) -> None:
    """A and A2 must reach the same strong-oracle verdict for the same tool.

    They call the oracle through separate code paths; a disagreement would mean
    one of them is mis-scoring the tools it admits.
    """
    result = _evaluate_task(
        admitting_task, MAX_MUTANTS, SEED, CALL_TIMEOUT_S, MIN_MUTANTS
    )
    assert result is not None
    verdict_from_a = {
        o.mutant_index: o.strong_pass
        for o in result.outcomes
        if o.role == "candidate"
    }

    rows = per_tool_rows(admitting_task)
    assert rows

    for row in rows:
        assert row.strong_pass == verdict_from_a[row.mutant_index], (
            f"mutant {row.mutant_index} of {admitting_task.task_id}: A2 and A "
            "disagree about the independent oracle"
        )


def test_a_task_whose_candidates_are_all_rejected_yields_no_tools(
    rejecting_task: Task,
) -> None:
    """FAR is conditional on admission: a tool the weak suite killed was never
    admitted and must not appear in the per-tool population."""
    _, _, admitted = experiment_a_split(rejecting_task)

    assert admitted == set(), "precondition: Mbpp/3 admits nothing"
    assert per_tool_rows(rejecting_task) == []


def test_scoring_a_task_is_deterministic(admitting_task: Task) -> None:
    """Same seed => same mutants => same admitted set => same scores.

    The module claims full determinism; an experiment that cannot be re-run to
    the same numbers is not reproducible.
    """
    first = per_tool_rows(admitting_task)
    second = per_tool_rows(admitting_task)

    assert [row.__dict__ for row in first] == [row.__dict__ for row in second]


def test_per_tool_adequacy_is_a_real_fraction(admitting_task: Task) -> None:
    rows = per_tool_rows(admitting_task)
    assert rows

    for row in rows:
        assert row.n_second_order > 0, "a score over zero mutants is not a score"
        assert 0.0 <= row.per_tool_adequacy <= 1.0
        assert row.task_id == admitting_task.task_id


# ---------------------------------------------------------------------------
# The sweep, end to end, on real data.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def summary(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One real run of the experiment. Module-scoped: it executes ~10^3 subprocesses.

    `limit=20` rather than a smaller slice because the first 20 MBPP+ tasks are
    what it takes to reach a non-degenerate population (13 admitted tools, of
    which 5 are false admissions). See
    `test_the_gate_refuses_to_report_on_an_empty_population` for what happens
    below that.
    """
    out_dir = tmp_path_factory.mktemp("results")
    return run_per_tool_gate(limit=20, out_dir=out_dir, workers=8)


def test_the_sweep_produces_a_well_formed_summary(summary: dict[str, Any]) -> None:
    assert set(summary) >= {
        "experiment",
        "config",
        "H1_far",
        "H2_predictor",
        "H3_gate",
        "per_tool",
    }
    assert summary["config"]["seed"] == 0
    assert summary["per_tool"], "the sweep admitted no tools at all"


def test_the_sweep_scores_real_tools(summary: dict[str, Any]) -> None:
    for row in summary["per_tool"]:
        assert row["task_id"].startswith("Mbpp/")
        assert 0.0 <= row["per_tool_adequacy"] <= 1.0
        assert row["n_second_order"] > 0
        assert isinstance(row["strong_pass"], bool)


def test_the_reported_far_is_the_conditional_it_claims_to_be(
    summary: dict[str, Any],
) -> None:
    """H1's FAR must be the false admissions over the *admitted* tools -- which,
    in A2, is every row (a tool only gets a row if it was admitted)."""
    h1 = summary["H1_far"]
    rows = summary["per_tool"]

    assert h1["n_admitted"] == len(rows)
    assert h1["n_false_admissions"] == sum(1 for r in rows if not r["strong_pass"])
    assert h1["far"] == pytest.approx(h1["n_false_admissions"] / h1["n_admitted"])
    assert h1["ci95"][0] <= h1["far"] <= h1["ci95"][1]


def test_coverage_is_non_increasing_as_the_gate_tightens(
    summary: dict[str, Any],
) -> None:
    """Raising tau can only ever admit fewer tools. If coverage rose with tau the
    gate would be filtering in the wrong direction, and the H3 trade-off curve --
    FAR reduction bought with coverage -- would be meaningless."""
    gate = summary["H3_gate"]
    taus = [row["tau"] for row in gate]
    assert taus == sorted(taus), "precondition: the sweep is ordered by tau"

    coverage = [row["coverage"] for row in gate]
    admitted = [row["n_admitted"] for row in gate]

    for previous, current in zip(coverage, coverage[1:]):
        assert current <= previous + 1e-12, f"coverage rose with tau: {coverage}"
    for previous, current in zip(admitted, admitted[1:]):
        assert current <= previous, f"admissions rose with tau: {admitted}"


def test_the_sweep_spans_a_real_range_of_thresholds(summary: dict[str, Any]) -> None:
    """A sweep that never changes anything would satisfy monotonicity vacuously."""
    gate = summary["H3_gate"]
    coverage = [row["coverage"] for row in gate]

    assert coverage[0] == pytest.approx(1.0), "tau=0 must admit everything"
    assert min(coverage) < max(coverage), "the gate never rejected anything"


def test_every_gate_row_is_internally_consistent(summary: dict[str, Any]) -> None:
    baseline = summary["H1_far"]["far"]

    for row in summary["H3_gate"]:
        assert 0 <= row["n_false_admissions"] <= row["n_admitted"]
        assert 0.0 <= row["far"] <= 1.0
        assert 0.0 <= row["coverage"] <= 1.0
        assert row["far_lo"] <= row["far"] <= row["far_hi"]
        assert 0.0 <= row["far_lo"] <= row["far_hi"] <= 1.0
        if row["n_admitted"]:
            assert row["far"] == pytest.approx(
                row["n_false_admissions"] / row["n_admitted"]
            )
        if baseline > 0:
            assert row["far_reduction_vs_baseline"] == pytest.approx(
                1.0 - row["far"] / baseline
            )


def test_the_gate_admits_only_tools_at_or_above_tau(summary: dict[str, Any]) -> None:
    """Recount the sweep from the raw rows -- the headline table must match them."""
    rows = summary["per_tool"]

    for gate_row in summary["H3_gate"]:
        expected = [
            r for r in rows if r["per_tool_adequacy"] >= gate_row["tau"]
        ]
        assert gate_row["n_admitted"] == len(expected)
        assert gate_row["n_false_admissions"] == sum(
            1 for r in expected if not r["strong_pass"]
        )


def test_the_predictor_is_scored_against_a_baseline(summary: dict[str, Any]) -> None:
    """H2 needs both AUCs and a paired delta, or it cannot be adjudicated."""
    h2 = summary["H2_predictor"]

    for key in ("auc_per_tool_adequacy", "auc_code_size_baseline", "auc_delta"):
        assert key in h2
        assert h2[key]["ci95"][0] <= h2[key]["value"] <= h2[key]["ci95"][1]

    for key in ("auc_per_tool_adequacy", "auc_code_size_baseline"):
        assert 0.0 <= h2[key]["value"] <= 1.0


def test_the_sweep_writes_its_results_to_disk(
    tmp_path_factory: pytest.TempPathFactory, summary: dict[str, Any]
) -> None:
    """A reviewer must be able to read the numbers back without re-running it."""
    out_dir = tmp_path_factory.mktemp("written")
    run_per_tool_gate(limit=10, out_dir=out_dir, workers=8)

    written = out_dir / "experiment_a2_per_tool.json"
    assert written.is_file()

    reloaded = json.loads(written.read_text())
    assert reloaded["H1_far"]["n_admitted"] == len(reloaded["per_tool"])


# ---------------------------------------------------------------------------
# The empty-population guard
# ---------------------------------------------------------------------------


def test_the_gate_refuses_to_report_on_an_empty_population(tmp_path: Path) -> None:
    """With only the first three MBPP+ tasks, nothing is admitted at all.

    Mbpp/2 and Mbpp/4 produce fewer than `min_mutants` mutants and are skipped;
    Mbpp/3's entire candidate set is killed by the weak suite. There is no
    admitted population, so there is no FAR to report -- and the module raises
    instead of emitting a 0.0 that would look like a finding.
    """
    with pytest.raises(RuntimeError, match="no admitted tools"):
        run_per_tool_gate(limit=3, out_dir=tmp_path, workers=3)
