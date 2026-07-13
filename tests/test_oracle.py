"""Tests for `sea.eval.oracle` -- the measurement apparatus itself.

These run against **real MBPP+ data** loaded through EvalPlus. Nothing here is
mocked, because there is nothing here worth mocking: the oracle *is* the
instrument, and an instrument validated against a fake is not validated at all.

Two tests carry the project:

* `test_canonical_solution_passes_both_oracles` -- apparatus validation. If the
  human reference solution does not satisfy the oracle that judges every
  candidate against it, then every number the project reports is garbage.
* `test_false_admission_is_detectable` -- phenomenon validation. The whole thesis
  is about candidates that pass a weak suite and fail an independent one. If the
  instrument cannot observe that event, there is no experiment.
"""

from __future__ import annotations

import time

import pytest

from sea.eval.oracle import OracleVerdict, Task, check_candidate, load_tasks, validate_task
from sea.mutation import generate_mutants


@pytest.fixture(scope="module")
def tasks() -> list[Task]:
    """The first few real MBPP+ tasks. Module-scoped: loading parses a dataset."""
    return load_tasks(limit=8)


@pytest.fixture(scope="module")
def is_not_prime(tasks: list[Task]) -> Task:
    """Mbpp/3 -- `is_not_prime(n)`.

    Chosen because its contract is easy to get subtly wrong and its base inputs
    (1, 2, 10, 35, 37) are all small, while MBPP+ probes it with values like
    7919 and 7921 = 89*89. That gap is exactly the phenomenon under study.
    """
    return next(task for task in tasks if task.task_id == "Mbpp/3")


# ---------------------------------------------------------------------------
# load_tasks
# ---------------------------------------------------------------------------


def test_load_tasks_returns_the_requested_number_of_tasks() -> None:
    assert len(load_tasks(limit=5)) == 5


def test_load_tasks_returns_well_formed_tasks(tasks: list[Task]) -> None:
    """Every field the oracle depends on must actually be populated."""
    for task in tasks:
        assert task.task_id.startswith("Mbpp/")
        assert task.prompt.strip(), f"{task.task_id} has an empty prompt"
        assert task.entry_point.strip(), f"{task.task_id} has no entry point"
        assert task.canonical_solution.strip(), f"{task.task_id} has no reference"
        assert task.base_input, f"{task.task_id} has no weak (base) inputs"
        assert task.plus_input, f"{task.task_id} has no strong (plus) inputs"


def test_the_canonical_solution_defines_the_entry_point(tasks: list[Task]) -> None:
    """The reference must define the function the oracle is going to call."""
    for task in tasks:
        assert f"def {task.entry_point}" in task.canonical_solution


def test_the_strong_oracle_is_substantially_larger_than_the_weak_one(
    tasks: list[Task],
) -> None:
    """EvalPlus augments MBPP ~35x. If the two oracles were the same size there
    would be no gap to measure, and FAR would be structurally zero."""
    for task in tasks:
        assert task.n_strong > task.n_weak * 5, (
            f"{task.task_id}: strong oracle ({task.n_strong}) is not meaningfully "
            f"bigger than the weak one ({task.n_weak})"
        )


def test_load_tasks_is_ordered_and_deterministic() -> None:
    """A shifting task order would silently change every seeded split downstream."""
    assert [t.task_id for t in load_tasks(limit=6)] == [
        t.task_id for t in load_tasks(limit=6)
    ]


# ---------------------------------------------------------------------------
# APPARATUS VALIDATION -- if this fails, nothing else in the project means anything
# ---------------------------------------------------------------------------


def test_canonical_solution_passes_both_oracles(tasks: list[Task]) -> None:
    """The human reference solution must satisfy the oracle built from it.

    This is the calibration test for the entire instrument. Every candidate is
    judged by differential comparison against this reference; if the reference
    itself does not agree with itself on the recorded inputs, the harness is
    measuring noise and every FAR, AUC and gate number in the project is void.
    """
    failures = []
    for task in tasks:
        verdict = check_candidate(task, task.canonical_solution)
        if not (verdict.weak_pass and verdict.strong_pass):
            failures.append((task.task_id, verdict))

    assert not failures, f"canonical solutions failed their own oracles: {failures}"


def test_canonical_solution_is_evaluated_on_every_recorded_input(
    is_not_prime: Task,
) -> None:
    """The reference is scored on all of the inputs, not a silently-skipped subset."""
    verdict = check_candidate(is_not_prime, is_not_prime.canonical_solution)

    assert verdict.n_weak_evaluated == len(is_not_prime.base_input)
    assert verdict.n_strong_evaluated == len(is_not_prime.plus_input)


def test_validate_task_accepts_a_real_task(is_not_prime: Task) -> None:
    assert validate_task(is_not_prime) is True


# ---------------------------------------------------------------------------
# The oracle actually rejects wrong code
# ---------------------------------------------------------------------------


def test_a_constant_implementation_fails_the_strong_oracle(is_not_prime: Task) -> None:
    """The crudest possible wrong tool: ignore the input, return a constant."""
    verdict = check_candidate(is_not_prime, "def is_not_prime(n):\n    return True\n")

    assert verdict.strong_pass is False


def test_a_constant_implementation_is_not_even_admitted(is_not_prime: Task) -> None:
    """It is so wrong that even the weak oracle catches it -- so it is no false
    admission, merely a rejection. The distinction matters: FAR counts only the
    ones that get *through*."""
    verdict = check_candidate(is_not_prime, "def is_not_prime(n):\n    return True\n")

    assert verdict.weak_pass is False
    assert verdict.false_admission is False


def test_a_plausible_but_wrong_implementation_fails_the_strong_oracle(
    is_not_prime: Task,
) -> None:
    """Checking only divisibility by 2 and 3 -- wrong for 25, 35, 49, ..."""
    naive = (
        "def is_not_prime(n):\n"
        "    if n == 1:\n"
        "        return True\n"
        "    return n % 2 == 0 or n % 3 == 0\n"
    )
    verdict = check_candidate(is_not_prime, naive)

    assert verdict.strong_pass is False


# ---------------------------------------------------------------------------
# THE PHENOMENON. The single most important test in the repository.
# ---------------------------------------------------------------------------


def test_false_admission_is_detectable(is_not_prime: Task) -> None:
    """A candidate that PASSES the weak oracle and FAILS the independent one.

    This implementation does trial division, but only up to a hardcoded bound of
    7. That is enough to be correct on every one of MBPP's base inputs
    (1, 2, 10, 35, 37) -- so a suite built from them admits it -- while being
    wrong on 7921 = 89 * 89, which MBPP+ probes and MBPP does not. It reports
    7921 as prime.

    This is a tool with a wrong contract entering the library through a green
    test suite: precisely the event the thesis is about. If this assertion ever
    fails, the phenomenon under study is not observable by the instrument and
    there is no experiment to run.
    """
    overfitted = (
        "def is_not_prime(n):\n"
        "    if n == 1:\n"
        "        return True\n"
        "    for i in range(2, 7):\n"
        "        if n != i and n % i == 0:\n"
        "            return True\n"
        "    return False\n"
    )

    verdict = check_candidate(is_not_prime, overfitted)

    assert verdict.weak_pass is True, "the weak oracle must ADMIT this tool"
    assert verdict.strong_pass is False, "the strong oracle must REJECT it"
    assert verdict.false_admission is True


def test_false_admissions_arise_naturally_from_mutants_of_real_solutions(
    tasks: list[Task],
) -> None:
    """The event is not an artefact of one hand-crafted example.

    Mutating the human canonical solutions -- the same engine the experiments use
    to manufacture candidate tools -- produces genuine false admissions on real
    MBPP+ tasks. This is the LLM-free arm's core premise, checked directly.
    """
    false_admissions = [
        (task.task_id, mutant.operator, mutant.before, mutant.after)
        for task in tasks
        for mutant in generate_mutants(task.canonical_solution, max_mutants=20, seed=0)
        if check_candidate(task, mutant.code).false_admission
    ]

    assert false_admissions, (
        "no mutant of any canonical solution passed the weak oracle while failing "
        "the strong one -- the phenomenon under study would be unobservable"
    )


def test_false_admission_requires_both_conditions() -> None:
    """The defining event is weak_pass AND NOT strong_pass -- nothing else."""
    assert OracleVerdict(True, False, 3, 0).false_admission is True
    assert OracleVerdict(True, True, 3, 100).false_admission is False
    assert OracleVerdict(False, False, 1, 0).false_admission is False


# ---------------------------------------------------------------------------
# Malformed candidates degrade to a verdict, never to a crash
# ---------------------------------------------------------------------------


def test_an_implementation_missing_the_entry_point_yields_a_failed_verdict(
    is_not_prime: Task,
) -> None:
    """A tool that does not define the function under test fails both oracles and
    reports an error -- it does not take the sweep down with it."""
    verdict = check_candidate(
        is_not_prime, "def some_other_function(n):\n    return True\n"
    )

    assert verdict.weak_pass is False
    assert verdict.strong_pass is False
    assert verdict.error is not None
    assert verdict.false_admission is False


def test_an_unparseable_implementation_yields_a_failed_verdict(
    is_not_prime: Task,
) -> None:
    verdict = check_candidate(is_not_prime, "def is_not_prime(n)\n    ???\n")

    assert verdict.weak_pass is False
    assert verdict.strong_pass is False
    assert verdict.error is not None


def test_an_implementation_that_raises_is_not_admitted(is_not_prime: Task) -> None:
    verdict = check_candidate(
        is_not_prime, "def is_not_prime(n):\n    raise RuntimeError('boom')\n"
    )

    assert verdict.weak_pass is False


# ---------------------------------------------------------------------------
# Non-termination is bounded. A hanging tool must not hang the experiment.
# ---------------------------------------------------------------------------


def test_an_infinite_loop_inside_the_function_does_not_hang_the_suite(
    is_not_prime: Task,
) -> None:
    """Each call is guarded, so one non-terminating input cannot eat the budget."""
    started = time.monotonic()
    verdict = check_candidate(
        is_not_prime,
        "def is_not_prime(n):\n    while True:\n        pass\n",
        timeout_s=20.0,
        call_timeout_s=0.5,
    )
    elapsed = time.monotonic() - started

    assert verdict.weak_pass is False
    assert elapsed < 15.0, f"per-call guard did not bound the run ({elapsed:.1f}s)"


def test_an_infinite_loop_at_import_time_is_caught_by_the_wall_clock(
    is_not_prime: Task,
) -> None:
    """A module that hangs before any call still terminates, via the wall clock."""
    started = time.monotonic()
    verdict = check_candidate(
        is_not_prime,
        "while True:\n    pass\n\ndef is_not_prime(n):\n    return True\n",
        timeout_s=3.0,
    )
    elapsed = time.monotonic() - started

    assert verdict.weak_pass is False
    assert verdict.strong_pass is False
    assert verdict.error == "timeout"
    assert elapsed < 15.0


# ---------------------------------------------------------------------------
# max_plus
# ---------------------------------------------------------------------------


def test_max_plus_bounds_the_strong_oracle(is_not_prime: Task) -> None:
    """Truncating the strong oracle must reduce what it evaluates, not what it
    concludes about a correct implementation."""
    verdict = check_candidate(
        is_not_prime, is_not_prime.canonical_solution, max_plus=5
    )

    assert verdict.n_strong_evaluated == 5
    assert verdict.strong_pass is True
