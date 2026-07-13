"""TDD synthesis: spec -> tests -> implementation -> bounded repair.

THE ONE RULE
------------
**Generated tests are immutable.** Once the model emits a test suite, nothing in
this codebase may alter it -- not a regex, not a retry, not a "fix". Repair may
only rewrite the *implementation*.

This is not stylistic. The system this replaced had a method called
``_apply_aggressive_test_fixes`` that, when the generated tests failed, rewrote
the failing assertions until they passed, and if they still failed, registered
the tool anyway as "experimental". A pass rate produced that way is not a
measurement of anything. A synthesis failure rate is a *result*; a zero failure
rate obtained by editing the oracle is a *fabrication*.

The immutability is enforced structurally, not by convention: ``tests`` lives on
a frozen dataclass, the repair loop is handed only the implementation, and
``SynthesisResult.tests_sha256`` pins the suite that was generated so any later
mutation is detectable. See ADR-003.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from sea.llm import LLMClient
from sea.sandbox import ExecResult, run_pytest

__all__ = [
    "Spec",
    "SynthesisResult",
    "SynthesisError",
    "synthesize",
]


class SynthesisError(RuntimeError):
    """Synthesis could not produce a well-formed artefact."""


_SPEC_SYSTEM = """\
You are a software architect. Given a task description, produce a JSON \
specification for a single Python function that solves it.

Return ONLY a JSON object with these keys:
  "function_name": snake_case identifier
  "signature":     the full def line, e.g. "def foo(a: int, b: int) -> int:"
  "docstring":     a precise description of the contract, including edge cases

No prose, no markdown fences."""

_TESTS_SYSTEM = """\
You are a test engineer practising TDD. Given a function specification, write a \
pytest suite that pins the function's contract BEFORE any implementation exists.

Rules:
- Import the function with: from tool import <function_name>
- Cover the happy path, boundary values, and error conditions.
- Assert on behaviour, never on implementation details.
- Return ONLY Python code. No prose, no markdown fences."""

_IMPL_SYSTEM = """\
You are a Python engineer. Write an implementation that satisfies the given \
specification and passes the given test suite.

Rules:
- Define exactly the specified function (helpers are fine).
- You may NOT modify the tests; they are the contract.
- Return ONLY Python code. No prose, no markdown fences."""

_REPAIR_SYSTEM = """\
Your implementation failed its test suite. Rewrite the IMPLEMENTATION so the \
tests pass.

You may NOT change the tests. The tests are the specification. If a test looks \
wrong to you, it is still the contract -- satisfy it.

Return ONLY the corrected Python implementation. No prose, no markdown fences."""


@dataclass(frozen=True)
class Spec:
    function_name: str
    signature: str
    docstring: str


@dataclass(frozen=True)
class SynthesisResult:
    """Outcome of one synthesis attempt.

    `tests` is frozen at generation time. `tests_sha256` pins it so that any
    downstream mutation of the suite is detectable rather than silent.
    """

    spec: Spec
    tests: str
    code: str
    passed_own_tests: bool
    repair_attempts: int
    tests_sha256: str
    history: list[str] = field(default_factory=list)

    def verify_tests_unmodified(self, tests: str) -> bool:
        return hashlib.sha256(tests.encode()).hexdigest() == self.tests_sha256


def _strip_fences(text: str) -> str:
    """Models emit markdown fences despite instructions. Strip them."""
    text = text.strip()
    m = re.match(r"^```(?:python|json)?\s*\n(.*?)\n?```$", text, re.DOTALL)
    return m.group(1).strip() if m else text


def _parse_spec(raw: str) -> Spec:
    body = _strip_fences(raw)
    try:
        data: dict[str, Any] = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SynthesisError(f"spec was not valid JSON: {exc}") from exc
    missing = {"function_name", "signature", "docstring"} - data.keys()
    if missing:
        raise SynthesisError(f"spec missing keys: {sorted(missing)}")
    return Spec(
        function_name=str(data["function_name"]),
        signature=str(data["signature"]),
        docstring=str(data["docstring"]),
    )


def synthesize(
    llm: LLMClient,
    task_prompt: str,
    *,
    max_repairs: int = 3,
    timeout_s: float = 10.0,
) -> SynthesisResult:
    """Run the TDD pipeline. Tests are generated once and never touched again."""
    history: list[str] = []

    spec = _parse_spec(llm.complete(_SPEC_SYSTEM, task_prompt))
    history.append(f"spec: {spec.function_name}")

    # ---- The suite is born here and is immutable from this line onward. ----
    tests = _strip_fences(
        llm.complete(
            _TESTS_SYSTEM,
            f"Specification:\n{json.dumps(spec.__dict__, indent=2)}",
        )
    )
    tests_sha = hashlib.sha256(tests.encode()).hexdigest()
    history.append(f"tests: {tests.count('def test_')} test functions")

    code = _strip_fences(
        llm.complete(
            _IMPL_SYSTEM,
            f"Specification:\n{json.dumps(spec.__dict__, indent=2)}\n\n"
            f"Test suite:\n{tests}",
        )
    )

    result: ExecResult = run_pytest(code, tests, timeout_s=timeout_s)
    history.append(f"verify: {result.status}")

    repairs = 0
    while result.status != "passed" and repairs < max_repairs:
        repairs += 1
        # Only `code` is regenerated. `tests` is passed as read-only context and
        # the model's output is only ever bound back to `code`. There is no code
        # path in this function that can reassign `tests`.
        code = _strip_fences(
            llm.complete(
                _REPAIR_SYSTEM,
                f"Test suite (IMMUTABLE -- do not change):\n{tests}\n\n"
                f"Current implementation:\n{code}\n\n"
                f"pytest output:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}",
            )
        )
        result = run_pytest(code, tests, timeout_s=timeout_s)
        history.append(f"repair {repairs}: {result.status}")

    assert hashlib.sha256(tests.encode()).hexdigest() == tests_sha, (
        "INVARIANT VIOLATED: the test suite was modified during synthesis. "
        "This invalidates every downstream measurement. See ADR-003."
    )

    return SynthesisResult(
        spec=spec,
        tests=tests,
        code=code,
        passed_own_tests=(result.status == "passed"),
        repair_attempts=repairs,
        tests_sha256=tests_sha,
        history=history,
    )
