"""Independent ground-truth oracle for MBPP+ via differential testing.

This module is the measurement apparatus for the whole project. It answers one
question about a candidate implementation:

    Does it agree with the human canonical solution on a given set of inputs?

We never parse assertion strings. We run the candidate and the reference
side by side, in the same subprocess, on the same deep-copied inputs, and
compare their outputs. This mirrors EvalPlus's own semantics and sidesteps a
whole class of string-parsing bugs.

Two oracles per task, and the gap between them is the experiment:

    WEAK   -- ``base_input``: the 3 assertions shipped with the original MBPP.
              This stands in for a self-consistent / under-powered admission
              suite. Note that MBPP's natural-language prompt literally
              *contains* these 3 assertions, so an LLM writing tests from the
              prompt tends to reproduce a suite of about this strength. That is
              what makes the LLM-free Experiment A a faithful proxy for the
              LLM arm.

    STRONG -- ``base_input + plus_input``: ~111 inputs (EvalPlus augments MBPP
              by 35x). Authored independently of any LLM. This is ground truth.

An implementation that passes WEAK but fails STRONG is a **false admission**:
the library accepted a tool whose contract is wrong.

Isolation note: candidate code runs via ``sea.sandbox``, which is a SAFETY
boundary (accidental infinite loops, memory bombs), NOT a security boundary.
See ADR-002.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

from sea.sandbox import run_script

__all__ = [
    "OracleVerdict",
    "Task",
    "load_tasks",
    "check_candidate",
]


# The in-subprocess harness. Reference and candidate are exec'd into separate
# namespaces so they can share a function name without colliding. Each call is
# guarded by SIGALRM so that one hanging input cannot consume the entire
# wall-clock budget and destroy the verdict for every other input.
_HARNESS = '''\
import copy, json, math, signal, sys

REF_SRC   = {ref_src!r}
CAND_SRC  = {cand_src!r}
ENTRY     = {entry!r}
BASE      = {base!r}
PLUS      = {plus!r}
ATOL      = {atol!r}
CALL_T    = {call_timeout!r}


class _Timeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _on_alarm)


def _call(fn, args):
    signal.setitimer(signal.ITIMER_REAL, CALL_T)
    try:
        return ("ok", fn(*copy.deepcopy(args)))
    except _Timeout:
        return ("timeout", None)
    except BaseException as exc:
        return ("exc", type(exc).__name__)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _eq(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        try:
            if math.isnan(a) and math.isnan(b):
                return True
            return math.isclose(a, b, rel_tol=1e-6, abs_tol=max(ATOL, 1e-6))
        except TypeError:
            return False
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if type(a) is not type(b) or len(a) != len(b):
            return False
        return all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(_eq(a[k], b[k]) for k in a)
    try:
        return bool(a == b)
    except Exception:
        return False


ns_ref, ns_cand = {{}}, {{}}
try:
    exec(REF_SRC, ns_ref)
    exec(CAND_SRC, ns_cand)
    ref, cand = ns_ref[ENTRY], ns_cand[ENTRY]
except BaseException as exc:
    # Candidate does not even import/define. That is a hard failure on both
    # oracles -- it cannot be admitted and it is certainly not correct.
    print(json.dumps({{"weak": False, "strong": False, "n_weak": 0, "n_strong": 0,
                      "load_error": type(exc).__name__}}))
    sys.exit(0)


def agree(inputs):
    """Return (all_agree, n_inputs_where_reference_was_well_defined)."""
    ok, n_valid = True, 0
    for args in inputs:
        rs, rv = _call(ref, args)
        if rs != "ok":
            # The reference itself is undefined on this input. Skip it -- we
            # cannot hold a candidate to a contract the ground truth does not
            # have. Skipped inputs are reported, never silently dropped.
            continue
        n_valid += 1
        cs, cv = _call(cand, args)
        if cs != "ok" or not _eq(rv, cv):
            ok = False
            break
    return ok, n_valid


weak_ok, n_weak = agree(BASE)
strong_ok, n_strong = (agree(PLUS) if weak_ok else (False, 0))

print(json.dumps({{
    "weak": weak_ok,
    "strong": bool(weak_ok and strong_ok),
    "n_weak": n_weak,
    "n_strong": n_strong,
}}))
'''


@dataclass(frozen=True)
class Task:
    """One MBPP+ problem."""

    task_id: str
    prompt: str
    entry_point: str
    canonical_solution: str
    base_input: list[Any]
    plus_input: list[Any]
    atol: float

    @property
    def n_weak(self) -> int:
        return len(self.base_input)

    @property
    def n_strong(self) -> int:
        return len(self.base_input) + len(self.plus_input)


@dataclass(frozen=True)
class OracleVerdict:
    """How a candidate fared against the two oracles.

    ``weak_pass``   -- agrees with canonical on all base inputs (=> ADMITTED).
    ``strong_pass`` -- agrees with canonical on base + plus inputs (=> CORRECT).

    ``weak_pass and not strong_pass`` is a FALSE ADMISSION: the defining event
    this project measures.
    """

    weak_pass: bool
    strong_pass: bool
    n_weak_evaluated: int
    n_strong_evaluated: int
    error: str | None = None

    @property
    def false_admission(self) -> bool:
        return self.weak_pass and not self.strong_pass


def load_tasks(limit: int | None = None) -> list[Task]:
    """Load MBPP+ from EvalPlus. Requires the `evalplus` package."""
    from evalplus.data import get_mbpp_plus

    raw = get_mbpp_plus()
    tasks: list[Task] = []
    for task_id in sorted(raw, key=lambda k: int(str(k).split("/")[-1])):
        p = raw[task_id]
        tasks.append(
            Task(
                task_id=str(task_id),
                prompt=p["prompt"],
                entry_point=p["entry_point"],
                canonical_solution=p["canonical_solution"],
                base_input=list(p.get("base_input", [])),
                plus_input=list(p.get("plus_input", [])),
                atol=float(p.get("atol", 0.0) or 0.0),
            )
        )
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def check_candidate(
    task: Task,
    candidate_src: str,
    *,
    timeout_s: float = 30.0,
    call_timeout_s: float = 1.0,
    max_plus: int | None = None,
) -> OracleVerdict:
    """Run `candidate_src` against the weak and strong oracles for `task`.

    The candidate is compared *differentially* against the task's canonical
    solution -- we never trust the candidate to self-report.
    """
    plus = task.plus_input if max_plus is None else task.plus_input[:max_plus]

    script = _HARNESS.format(
        ref_src=task.canonical_solution,
        cand_src=candidate_src,
        entry=task.entry_point,
        base=task.base_input,
        plus=plus,
        atol=task.atol,
        call_timeout=call_timeout_s,
    )

    res = run_script(script, timeout_s=timeout_s)

    if res.status == "timeout":
        # Wall clock blew past even the per-call alarms. Treat as failure on
        # both oracles: a tool that hangs is neither admissible nor correct.
        return OracleVerdict(False, False, 0, 0, error="timeout")

    line = ""
    for candidate_line in reversed(res.stdout.strip().splitlines()):
        if candidate_line.strip().startswith("{"):
            line = candidate_line.strip()
            break
    if not line:
        return OracleVerdict(
            False, False, 0, 0, error=f"no verdict (status={res.status})"
        )

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return OracleVerdict(False, False, 0, 0, error="unparseable verdict")

    return OracleVerdict(
        weak_pass=bool(data["weak"]),
        strong_pass=bool(data["strong"]),
        n_weak_evaluated=int(data["n_weak"]),
        n_strong_evaluated=int(data["n_strong"]),
        error=data.get("load_error"),
    )


def validate_task(task: Task, **kw: Any) -> bool:
    """Sanity check: the canonical solution must pass its own oracles.

    Any task failing this is a data-quality problem and is EXCLUDED from the
    experiment and reported -- never silently kept.
    """
    v = check_candidate(task, task.canonical_solution, **kw)
    return v.weak_pass and v.strong_pass
