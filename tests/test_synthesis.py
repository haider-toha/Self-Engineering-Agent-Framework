"""Tests for `sea.synthesis` -- and above all for ADR-003: TESTS ARE IMMUTABLE.

The system this replaced had a method called `_apply_aggressive_test_fixes` which,
when the generated tests failed, rewrote the failing assertions until they passed,
and registered the tool anyway if they still did not. Every "verified" tool it
produced was verified against an oracle it had been allowed to edit.

So the load-bearing tests in this file are the ones that drive a repair cycle and
then check that the suite came out the other side untouched -- byte for byte, and
by hash. Asserting `result.tests == what the model emitted` is not a tautology
here: it is the invariant. A pipeline that "helpfully" patched a failing
assertion, or regenerated the suite on retry, would produce a different string
and fail these tests. That is exactly what they are for.

The LLM is faked at the `LLMClient` seam. Everything below it -- the sandbox, the
subprocess, the real pytest run that decides pass/fail -- is real.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import pytest

from sea.llm import FakeLLM
from sea.synthesis import SynthesisError, _strip_fences, synthesize

# ---------------------------------------------------------------------------
# Fixtures: a real spec, a real suite, and implementations that really do pass
# or fail it when pytest is actually run.
# ---------------------------------------------------------------------------

SPEC = json.dumps(
    {
        "function_name": "add",
        "signature": "def add(a: int, b: int) -> int:",
        "docstring": "Return the sum of two integers.",
    }
)

#: Pre-stripped, so `_strip_fences` is the identity on it and "what the model
#: emitted" and "what the pipeline stored" can be compared byte for byte.
TESTS = """
from tool import add


def test_add_positives():
    assert add(2, 3) == 5


def test_add_negatives():
    assert add(-1, 1) == 0


def test_add_zero_is_the_identity():
    assert add(0, 7) == 7
""".strip()

PASSING_IMPL = "def add(a, b):\n    return a + b"
FAILING_IMPL = "def add(a, b):\n    return a - b"


def scripted(*responses: str) -> Callable[..., str]:
    """Drive `synthesize` by call order: spec, tests, impl, then each repair.

    An unscripted call is an error rather than a default, so a pipeline that
    started making extra LLM calls would be caught instead of silently absorbed.
    """
    remaining = list(responses)

    def respond(*, system: str, user: str, temperature: float = 0.0) -> str:
        if not remaining:
            raise AssertionError("synthesize made more LLM calls than were scripted")
        return remaining.pop(0)

    return respond


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_an_implementation_that_passes_needs_no_repair() -> None:
    llm = FakeLLM(completions=scripted(SPEC, TESTS, PASSING_IMPL))

    result = synthesize(llm, "Add two numbers.")

    assert result.passed_own_tests is True
    assert result.repair_attempts == 0
    assert result.spec.function_name == "add"


def test_synthesis_stops_calling_the_model_once_the_tests_pass() -> None:
    """Exactly three calls: spec, tests, implementation. No speculative repair."""
    llm = FakeLLM(completions=scripted(SPEC, TESTS, PASSING_IMPL))

    synthesize(llm, "Add two numbers.")

    assert llm.completion_calls == 3


def test_the_generated_suite_is_pinned_by_its_hash() -> None:
    llm = FakeLLM(completions=scripted(SPEC, TESTS, PASSING_IMPL))

    result = synthesize(llm, "Add two numbers.")

    assert result.tests_sha256 == sha(result.tests)
    assert result.verify_tests_unmodified(TESTS) is True


def test_verify_tests_unmodified_rejects_a_tampered_suite() -> None:
    """The hash must actually be able to say no, or it pins nothing."""
    llm = FakeLLM(completions=scripted(SPEC, TESTS, PASSING_IMPL))

    result = synthesize(llm, "Add two numbers.")

    tampered = TESTS.replace("== 5", "== 6")
    assert result.verify_tests_unmodified(tampered) is False


# ---------------------------------------------------------------------------
# ADR-003 -- the repair loop may only ever touch the implementation
# ---------------------------------------------------------------------------


def test_repair_fixes_the_implementation_and_leaves_the_suite_untouched() -> None:
    """The invariant, under the one condition that could break it: a failing suite.

    The first implementation genuinely fails a real pytest run. The pipeline must
    respond by regenerating the *implementation* -- never by touching the tests
    that caught it.
    """
    llm = FakeLLM(completions=scripted(SPEC, TESTS, FAILING_IMPL, PASSING_IMPL))

    result = synthesize(llm, "Add two numbers.", max_repairs=3)

    assert result.repair_attempts == 1, "exactly one repair should have been needed"
    assert result.passed_own_tests is True

    # THE INVARIANT: the suite that failed the first implementation is the same
    # suite, byte for byte, that passed the second one.
    assert result.tests == TESTS
    assert result.tests_sha256 == sha(TESTS)
    assert result.verify_tests_unmodified(TESTS) is True

    # ...and the thing that actually changed was the implementation.
    assert result.code != FAILING_IMPL


def test_the_repair_prompt_carries_the_suite_as_read_only_context() -> None:
    """The model is shown the tests, and told it may not change them.

    The repair response is bound to `code` and nowhere else, so even a model that
    tried to return a new suite could not install one.
    """
    llm = FakeLLM(completions=scripted(SPEC, TESTS, FAILING_IMPL, PASSING_IMPL))

    synthesize(llm, "Add two numbers.", max_repairs=3)

    repair_system, repair_user, _ = llm.prompts[3]
    assert TESTS in repair_user, "the repair prompt must show the immutable suite"
    assert "not change the tests" in repair_system.lower()


def test_a_repair_that_returns_a_new_test_suite_cannot_install_it() -> None:
    """A model ignoring the instructions must not be able to replace the oracle.

    Here the "repair" response is itself a test file. The pipeline binds it to the
    implementation slot, where it fails the real suite -- it does *not* become the
    new suite. The tool is reported as failing, which is the honest outcome.
    """
    hostile_repair = "from tool import add\n\n\ndef test_trivial():\n    assert True"
    llm = FakeLLM(completions=scripted(SPEC, TESTS, FAILING_IMPL, hostile_repair))

    result = synthesize(llm, "Add two numbers.", max_repairs=1)

    assert result.tests == TESTS, "the suite must survive a model that returns tests"
    assert result.tests_sha256 == sha(TESTS)
    assert result.passed_own_tests is False


# ---------------------------------------------------------------------------
# Repair exhaustion -- an honest failure, not a laundered pass
# ---------------------------------------------------------------------------


def test_an_implementation_that_never_passes_is_reported_as_failing() -> None:
    """The old system rewrote the tests here, or registered the tool anyway.

    The correct behaviour is to come back and say: this did not work.
    """
    llm = FakeLLM(
        completions=scripted(SPEC, TESTS, FAILING_IMPL, FAILING_IMPL, FAILING_IMPL)
    )

    result = synthesize(llm, "Add two numbers.", max_repairs=2)

    assert result.passed_own_tests is False
    assert result.repair_attempts == 2, "it must exhaust its budget, not give up early"


def test_the_suite_survives_repair_exhaustion_unmodified() -> None:
    """Even after every repair has failed, nothing may have edited the oracle."""
    llm = FakeLLM(
        completions=scripted(SPEC, TESTS, FAILING_IMPL, FAILING_IMPL, FAILING_IMPL)
    )

    result = synthesize(llm, "Add two numbers.", max_repairs=2)

    assert result.tests == TESTS
    assert result.tests_sha256 == sha(TESTS)
    assert result.verify_tests_unmodified(TESTS) is True


def test_repair_exhaustion_returns_a_result_rather_than_raising() -> None:
    """A synthesis failure is a *result* -- the agent must be able to record it."""
    llm = FakeLLM(completions=scripted(SPEC, TESTS, FAILING_IMPL, FAILING_IMPL))

    result = synthesize(llm, "Add two numbers.", max_repairs=1)

    assert result.passed_own_tests is False
    assert result.code, "the failing implementation is still returned, for the record"
    assert result.history, "and the attempt is recorded in the history"


def test_no_repairs_are_attempted_when_the_budget_is_zero() -> None:
    llm = FakeLLM(completions=scripted(SPEC, TESTS, FAILING_IMPL))

    result = synthesize(llm, "Add two numbers.", max_repairs=0)

    assert result.repair_attempts == 0
    assert result.passed_own_tests is False
    assert llm.completion_calls == 3


# ---------------------------------------------------------------------------
# An empty suite is not a passing suite
# ---------------------------------------------------------------------------


def test_a_suite_with_no_tests_does_not_count_as_passing() -> None:
    """A vacuous oracle trivially "passes". Admitting on it would corrupt every
    downstream number, so the sandbox reports zero collected tests as an error."""
    empty_suite = "# the model wrote no tests at all"
    llm = FakeLLM(completions=scripted(SPEC, empty_suite, PASSING_IMPL, PASSING_IMPL))

    result = synthesize(llm, "Add two numbers.", max_repairs=1)

    assert result.passed_own_tests is False


# ---------------------------------------------------------------------------
# Malformed specs
# ---------------------------------------------------------------------------


def test_a_spec_that_is_not_json_raises_synthesis_error() -> None:
    llm = FakeLLM(completions=scripted("Sure! Here is the spec you asked for."))

    with pytest.raises(SynthesisError, match="not valid JSON"):
        synthesize(llm, "Add two numbers.")


def test_a_spec_missing_required_keys_raises_synthesis_error() -> None:
    llm = FakeLLM(completions=scripted(json.dumps({"function_name": "add"})))

    with pytest.raises(SynthesisError, match="missing keys"):
        synthesize(llm, "Add two numbers.")


def test_a_malformed_spec_stops_the_pipeline_before_it_generates_tests() -> None:
    """No point writing tests for a specification that does not exist."""
    llm = FakeLLM(completions=scripted("not json"))

    with pytest.raises(SynthesisError):
        synthesize(llm, "Add two numbers.")

    assert llm.completion_calls == 1


def test_a_fenced_json_spec_is_still_parsed() -> None:
    """Models fence their output despite being told not to."""
    llm = FakeLLM(
        completions=scripted(f"```json\n{SPEC}\n```", TESTS, PASSING_IMPL)
    )

    result = synthesize(llm, "Add two numbers.")

    assert result.spec.function_name == "add"
    assert result.passed_own_tests is True


def test_fenced_code_is_unwrapped_before_it_reaches_the_sandbox() -> None:
    """If the fences survived into `tool.py`, the module would not even parse."""
    llm = FakeLLM(
        completions=scripted(
            SPEC, f"```python\n{TESTS}\n```", f"```python\n{PASSING_IMPL}\n```"
        )
    )

    result = synthesize(llm, "Add two numbers.")

    assert result.passed_own_tests is True
    assert "```" not in result.code
    assert "```" not in result.tests


# ---------------------------------------------------------------------------
# _strip_fences
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("```python\nx = 1\n```", "x = 1"),
        ("```json\n{\"a\": 1}\n```", '{"a": 1}'),
        ("```\nx = 1\n```", "x = 1"),
        ("x = 1", "x = 1"),
        ("  \n```python\nx = 1\n```\n  ", "x = 1"),
        ("def f():\n    return 1", "def f():\n    return 1"),
    ],
)
def test_strip_fences(raw: str, expected: str) -> None:
    assert _strip_fences(raw) == expected


def test_strip_fences_keeps_fences_that_are_inside_the_code() -> None:
    """Only a wrapping fence is a fence. A triple-quote in a docstring is content."""
    code = 'def f():\n    """Example: ```x```"""\n    return 1'

    assert _strip_fences(code) == code
