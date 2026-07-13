"""Tests for `sea.agent` -- the research loop, end to end.

The LLM is faked at the `LLMClient` seam and *nothing else is*. The sandbox is
real (generated code runs in a real subprocess, under a real pytest), the
mutation engine is real (it really does mutate the implementation and really does
re-run the suite against each mutant), and the registry is a real SQLite database
on disk. Every decision these tests assert on is therefore a decision the loop
actually made, on real executions.

The two tests that matter most:

* `test_the_gate_rejects_a_tool_whose_suite_cannot_kill_its_own_mutants` -- the
  gate is the contribution. If it never rejects anything, the contribution is
  decorative.
* `test_the_same_tool_is_admitted_when_the_gate_is_off` -- the same tool, the same
  suite, the same model output, and the opposite outcome. The difference is
  attributable to the gate and to nothing else.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from sea.agent import handle_task
from sea.llm import FakeLLM
from sea.registry import Registry

# ---------------------------------------------------------------------------
# Two tools. One carries a suite that can see; the other carries a suite that
# cannot. Both pass their own tests -- that is the entire point.
# ---------------------------------------------------------------------------

ADD_DOCSTRING = "Return the sum of two integers."
ADD_SPEC = json.dumps(
    {
        "function_name": "add",
        "signature": "def add(a: int, b: int) -> int:",
        "docstring": ADD_DOCSTRING,
    }
)
ADD_IMPL = "def add(a, b):\n    return a + b"

#: An adequate suite: it pins the actual arithmetic, so every mutant of `add`
#: (a - b, return None, pass) changes an observed value and gets killed.
#: Measured mutation score: 1.00.
ADD_TESTS = """
from tool import add


def test_add_positives():
    assert add(2, 3) == 5


def test_add_negatives():
    assert add(-1, 1) == 0


def test_add_zero_is_the_identity():
    assert add(0, 7) == 7
""".strip()

CLASSIFY_DOCSTRING = "Classify a number as big or small."
CLASSIFY_SPEC = json.dumps(
    {
        "function_name": "classify",
        "signature": "def classify(n: int) -> str:",
        "docstring": CLASSIFY_DOCSTRING,
    }
)
CLASSIFY_IMPL = '''def classify(n):
    """Classify a number."""
    if n > 10:
        return "big"
    return "small"'''

#: An INADEQUATE suite. It passes, so the baseline admits the tool. But it only
#: checks the *type* of the answer, so it cannot tell `n > 10` from `n < 10`, nor
#: "big" from "". Measured mutation score: 0.09 -- 10 of 11 mutants survive.
#: This is a self-generated suite that verifies nothing, which is the failure mode
#: the whole thesis is about.
CLASSIFY_WEAK_TESTS = """
from tool import classify


def test_returns_a_string():
    assert isinstance(classify(50), str)
""".strip()

TAU = 0.8

#: Retrieval geometry, controlled so the cosine similarity is exact rather than
#: incidental. The assertions below are on the loop's *decision*, never on these.
VEC_MATCH = [1.0, 0.0, 0.0, 0.0]
VEC_OTHER = [0.0, 1.0, 0.0, 0.0]

REUSE_PROMPT = "Sum a pair of integers."
UNRELATED_PROMPT = "Classify a number."


def scripted(*responses: str) -> Callable[..., str]:
    """Drive synthesis by call order: spec, tests, impl, then repairs."""
    remaining = list(responses)

    def respond(*, system: str, user: str, temperature: float = 0.0) -> str:
        if not remaining:
            raise AssertionError("the agent made more LLM calls than were scripted")
        return remaining.pop(0)

    return respond


def embeddings(text: str) -> list[float]:
    """`REUSE_PROMPT` lands exactly on `add`'s docstring; everything else does not."""
    return VEC_MATCH if text in (ADD_DOCSTRING, REUSE_PROMPT) else VEC_OTHER


@pytest.fixture
def registry(tmp_path: Path) -> Registry:
    with Registry(tmp_path / "registry.db") as reg:
        yield reg


def adequate_llm() -> FakeLLM:
    return FakeLLM(
        completions=scripted(ADD_SPEC, ADD_TESTS, ADD_IMPL), embeddings=embeddings
    )


def inadequate_llm() -> FakeLLM:
    return FakeLLM(
        completions=scripted(CLASSIFY_SPEC, CLASSIFY_WEAK_TESTS, CLASSIFY_IMPL),
        embeddings=embeddings,
    )


def run(llm: FakeLLM, registry: Registry, **overrides: object) -> object:
    kwargs: dict = {
        "llm": llm,
        "registry": registry,
        "gate": True,
        "tau": TAU,
        "retrieval_threshold": 0.85,
    }
    kwargs.update(overrides)
    task_id = str(kwargs.pop("task_id", "task-1"))
    prompt = str(kwargs.pop("prompt", "Add two numbers."))
    return handle_task(task_id, prompt, **kwargs)


# ---------------------------------------------------------------------------
# The full loop: synthesize -> pass own tests -> clear the gate -> register
# ---------------------------------------------------------------------------


def test_a_tool_with_an_adequate_suite_is_admitted(registry: Registry) -> None:
    outcome = run(adequate_llm(), registry)

    assert outcome.decision == "admitted"
    assert outcome.admitted is True
    assert outcome.tool_name == "add"


def test_an_admitted_tool_is_actually_in_the_registry(registry: Registry) -> None:
    """Query it back. "Admitted" has to mean it is retrievable later, or the
    library does not exist."""
    run(adequate_llm(), registry, task_id="task-42")

    stored = registry.get("add")
    assert stored is not None
    assert stored.task_id == "task-42"
    assert stored.code == ADD_IMPL
    assert stored.tests == ADD_TESTS
    assert [record.name for record in registry.all()] == ["add"]


def test_an_admitted_tool_carries_the_mutation_report_that_admitted_it(
    registry: Registry,
) -> None:
    """The gate's evidence is recorded, not just its verdict."""
    outcome = run(adequate_llm(), registry)

    assert outcome.mutation is not None
    assert outcome.mutation.total > 0, "a gate that scored zero mutants proves nothing"
    assert outcome.mutation.score >= TAU
    assert outcome.mutation.killed + outcome.mutation.survived == outcome.mutation.total

    stored = registry.get("add")
    assert stored is not None
    assert stored.mutation_score == pytest.approx(outcome.mutation.score)


def test_an_admitted_tool_passed_its_own_tests_without_repair(
    registry: Registry,
) -> None:
    outcome = run(adequate_llm(), registry)

    assert outcome.synthesis is not None
    assert outcome.synthesis.passed_own_tests is True
    assert outcome.synthesis.repair_attempts == 0


# ---------------------------------------------------------------------------
# THE GATE. This is the contribution; these two tests are what prove it does
# something.
# ---------------------------------------------------------------------------


def test_the_gate_rejects_a_tool_whose_suite_cannot_kill_its_own_mutants(
    registry: Registry,
) -> None:
    """The tool passes its own tests. The baseline would admit it. The gate does not.

    `classify` is verified by a suite that only checks the return *type*. That
    suite cannot distinguish `n > 10` from `n < 10`, so it would admit a tool
    with an inverted contract. The mutation gate measures exactly that blindness
    and refuses the tool.
    """
    outcome = run(inadequate_llm(), registry)

    assert outcome.synthesis is not None
    assert outcome.synthesis.passed_own_tests is True, (
        "precondition: the baseline oracle is satisfied -- this tool WOULD be "
        "admitted without the gate"
    )
    assert outcome.decision == "rejected_by_gate"
    assert outcome.admitted is False


def test_a_gate_rejected_tool_does_not_enter_the_registry(registry: Registry) -> None:
    """Rejected must mean *absent*. The old system registered these as
    "experimental" and executed them anyway."""
    run(inadequate_llm(), registry)

    assert registry.get("classify") is None
    assert registry.all() == [], "the library must be genuinely empty"
    assert registry.reuse_stats()["tools_registered"] == 0


def test_the_gate_reports_the_score_it_rejected_on(registry: Registry) -> None:
    outcome = run(inadequate_llm(), registry)

    assert outcome.mutation is not None
    assert outcome.mutation.score < TAU
    assert outcome.mutation.survivors, (
        "a rejection must be evidenced by mutants the suite failed to kill"
    )


def test_the_same_tool_is_admitted_when_the_gate_is_off(registry: Registry) -> None:
    """Same task, same model output, same suite. Gate off => admitted.

    Together with the rejection test above, this isolates the gate as the sole
    cause of the difference. Without this pair, a rejection could be an artefact
    of the tool simply being broken.
    """
    outcome = run(inadequate_llm(), registry, gate=False)

    assert outcome.decision == "admitted"
    assert registry.get("classify") is not None
    assert [record.name for record in registry.all()] == ["classify"]


def test_with_the_gate_off_no_mutation_score_is_computed(registry: Registry) -> None:
    """The baseline arm must not silently pay for -- or benefit from -- the gate."""
    outcome = run(inadequate_llm(), registry, gate=False)

    assert outcome.mutation is None
    stored = registry.get("classify")
    assert stored is not None
    assert stored.mutation_score is None


def test_a_low_enough_tau_admits_the_same_weak_tool(registry: Registry) -> None:
    """The gate is a threshold, not a blanket ban on `classify`."""
    outcome = run(inadequate_llm(), registry, tau=0.0)

    assert outcome.decision == "admitted"
    assert outcome.mutation is not None
    assert outcome.mutation.score < TAU


# ---------------------------------------------------------------------------
# Honest failure
# ---------------------------------------------------------------------------


def test_a_tool_that_never_passes_its_own_tests_is_not_registered(
    registry: Registry,
) -> None:
    """The old system rewrote the tests and registered the tool anyway. We report
    the failure and register nothing."""
    broken = "def add(a, b):\n    return a - b"
    llm = FakeLLM(
        completions=scripted(ADD_SPEC, ADD_TESTS, broken, broken, broken),
        embeddings=embeddings,
    )

    outcome = run(llm, registry, max_repairs=2)

    assert outcome.decision == "failed_own_tests"
    assert outcome.admitted is False
    assert registry.all() == []
    assert registry.get("add") is None


def test_a_failed_tool_is_never_gated(registry: Registry) -> None:
    """Mutation score is undefined for an implementation that fails its own suite.
    The loop must not try to compute one."""
    broken = "def add(a, b):\n    return a - b"
    llm = FakeLLM(
        completions=scripted(ADD_SPEC, ADD_TESTS, broken, broken),
        embeddings=embeddings,
    )

    outcome = run(llm, registry, max_repairs=1)

    assert outcome.decision == "failed_own_tests"
    assert outcome.mutation is None


def test_a_malformed_spec_registers_nothing(registry: Registry) -> None:
    llm = FakeLLM(completions=scripted("this is not json"), embeddings=embeddings)

    outcome = run(llm, registry)

    assert outcome.decision == "synthesis_error"
    assert outcome.admitted is False
    assert outcome.error is not None
    assert registry.all() == []


# ---------------------------------------------------------------------------
# Reuse
# ---------------------------------------------------------------------------


def test_a_task_close_to_an_existing_tool_reuses_it(registry: Registry) -> None:
    """Register `add`, then ask a task that sits on top of its embedding."""
    run(adequate_llm(), registry, task_id="task-1", prompt="Add two numbers.")

    reuse_llm = FakeLLM(
        completions=scripted(),  # any synthesis call at all would be a failure
        embeddings=embeddings,
    )
    outcome = run(reuse_llm, registry, task_id="task-2", prompt=REUSE_PROMPT)

    assert outcome.decision == "reused"
    assert outcome.admitted is True
    assert outcome.tool_name == "add"
    assert outcome.retrieval_score is not None
    assert outcome.retrieval_score >= 0.85


def test_reuse_does_not_synthesize_anything(registry: Registry) -> None:
    """The point of a library is that a hit costs no tokens."""
    run(adequate_llm(), registry, task_id="task-1")

    reuse_llm = FakeLLM(completions=scripted(), embeddings=embeddings)
    run(reuse_llm, registry, task_id="task-2", prompt=REUSE_PROMPT)

    assert reuse_llm.completion_calls == 0


def test_reuse_is_recorded_in_the_registry_statistics(registry: Registry) -> None:
    """Reuse is counted, never inferred. Phase 4 reports this number."""
    run(adequate_llm(), registry, task_id="task-1")

    reuse_llm = FakeLLM(completions=scripted(), embeddings=embeddings)
    run(reuse_llm, registry, task_id="task-2", prompt=REUSE_PROMPT)

    stats = registry.reuse_stats()
    assert stats["total_retrievals"] == 1
    assert stats["unique_tools_retrieved"] == 1
    assert stats["unique_tasks_with_retrieval"] == 1
    assert stats["retrievals_per_tool"] == {"add": 1}


def test_a_dissimilar_task_does_not_reuse_and_synthesizes_instead(
    registry: Registry,
) -> None:
    """Retrieval is gated on similarity, not on the library merely being non-empty.

    Without this, "reused" would fire for every task after the first, and the
    reported reuse rate would be an artefact of the loop rather than a
    measurement.
    """
    run(adequate_llm(), registry, task_id="task-1", prompt="Add two numbers.")

    outcome = run(
        inadequate_llm(),
        registry,
        task_id="task-2",
        prompt=UNRELATED_PROMPT,
        gate=False,
    )

    assert outcome.decision == "admitted", "it should have synthesized, not reused"
    assert outcome.tool_name == "classify"
    assert registry.reuse_stats()["total_retrievals"] == 0
    assert {record.name for record in registry.all()} == {"add", "classify"}


def test_an_unreachable_threshold_never_reuses(registry: Registry) -> None:
    """A threshold above the maximum possible cosine must suppress reuse entirely."""
    run(adequate_llm(), registry, task_id="task-1")

    outcome = run(
        adequate_llm(),
        registry,
        task_id="task-2",
        prompt=REUSE_PROMPT,
        retrieval_threshold=1.01,
    )

    assert outcome.decision == "admitted"
    assert registry.reuse_stats()["total_retrievals"] == 0


def test_the_first_task_against_an_empty_library_cannot_reuse(
    registry: Registry,
) -> None:
    """A cold start is normal, not an error."""
    assert registry.all() == []

    outcome = run(adequate_llm(), registry, prompt=REUSE_PROMPT)

    assert outcome.decision == "admitted"
    assert outcome.retrieval_score is None


def test_the_retrieval_query_uses_the_task_prompt(registry: Registry) -> None:
    """The library is searched by the task the agent was actually given."""
    run(adequate_llm(), registry, task_id="task-1")

    reuse_llm = FakeLLM(completions=scripted(), embeddings=embeddings)
    run(reuse_llm, registry, task_id="task-2", prompt=REUSE_PROMPT)

    assert reuse_llm.texts[0] == REUSE_PROMPT


def test_embeddings_are_scored_by_cosine_similarity(registry: Registry) -> None:
    """Sanity-check the retrieval geometry the reuse tests depend on, so that a
    reuse failure elsewhere cannot be silently blamed on the vectors."""
    run(adequate_llm(), registry, task_id="task-1")

    hits = registry.search(np.array(VEC_MATCH, dtype=np.float32), k=1)
    assert hits[0][0].name == "add"
    assert hits[0][1] == pytest.approx(1.0)

    misses = registry.search(np.array(VEC_OTHER, dtype=np.float32), k=1)
    assert misses[0][1] == pytest.approx(0.0)
