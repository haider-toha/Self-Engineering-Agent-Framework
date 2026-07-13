"""The research loop: retrieve-or-synthesize -> verify -> gate -> register.

This is the whole agent. It is ~150 lines because that is all the thesis needs;
the system it replaced spent 8,000 lines to do less, and most of that was
theatre (a "tuner" that scored candidates by distance to a hardcoded constant, a
skill graph with zero callers, a reflection engine never invoked at runtime).

The admission gate is the contribution:

    baseline  : admit iff the tool passes its own self-generated tests.
    gated     : admit iff it passes its own tests AND those tests kill >= tau of
                the mutants of the tool's own implementation.

The gate costs ZERO extra LLM tokens -- mutation testing is pure execution. Its
price is CPU, paid once at admission, against a false-admission cost that is
paid on every future retrieval of a bad tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from sea.llm import LLMClient
from sea.mutation import MutationReport, mutation_score
from sea.registry import Registry, ToolRecord
from sea.synthesis import SynthesisError, SynthesisResult, synthesize

__all__ = ["Outcome", "handle_task"]

Decision = Literal[
    "reused",             # retrieved an existing tool above the similarity threshold
    "admitted",           # synthesized, passed its tests, cleared the gate
    "rejected_by_gate",   # synthesized, passed its tests, FAILED the gate
    "failed_own_tests",   # synthesized, could not pass its own tests even after repair
    "synthesis_error",    # never produced a well-formed artefact
]


@dataclass(frozen=True)
class Outcome:
    task_id: str
    decision: Decision
    tool_name: str | None = None
    retrieval_score: float | None = None
    mutation: MutationReport | None = None
    synthesis: SynthesisResult | None = None
    error: str | None = None

    @property
    def admitted(self) -> bool:
        return self.decision in ("admitted", "reused")


def handle_task(
    task_id: str,
    task_prompt: str,
    *,
    llm: LLMClient,
    registry: Registry,
    gate: bool,
    tau: float,
    retrieval_threshold: float,
    mutation_max: int = 30,
    max_repairs: int = 3,
    seed: int = 0,
) -> Outcome:
    """Handle one task. Retrieve if we can, synthesize if we must."""
    # ---- 1. Retrieve --------------------------------------------------------
    query = registry.search(llm.embed(task_prompt), k=1)
    if query:
        rec, score = query[0]
        if score >= retrieval_threshold:
            registry.record_retrieval(rec.name, task_id, score)
            return Outcome(
                task_id=task_id,
                decision="reused",
                tool_name=rec.name,
                retrieval_score=score,
            )

    # ---- 2. Synthesize (tests are frozen the moment they are generated) ------
    try:
        res = synthesize(llm, task_prompt, max_repairs=max_repairs)
    except SynthesisError as exc:
        return Outcome(task_id, "synthesis_error", error=str(exc))

    if not res.passed_own_tests:
        # Honest failure. The old system would have rewritten the tests here and
        # registered the tool anyway. We do not.
        return Outcome(task_id, "failed_own_tests", synthesis=res)

    # ---- 3. Gate ------------------------------------------------------------
    # How adequate is the suite that just admitted this tool? Mutate the tool's
    # own implementation and ask whether its own tests notice.
    report: MutationReport | None = None
    if gate:
        try:
            report = mutation_score(
                res.code, res.tests, max_mutants=mutation_max, seed=seed
            )
        except ValueError as exc:
            # mutation_score's precondition is that the impl passes its tests.
            # We only get here if it does, so this is a genuine anomaly (e.g. a
            # flaky/nondeterministic test). Do not admit on an unknown oracle.
            return Outcome(
                task_id, "rejected_by_gate", synthesis=res,
                error=f"mutation precondition failed: {exc}",
            )
        if report.score < tau:
            return Outcome(
                task_id, "rejected_by_gate", synthesis=res, mutation=report
            )

    # ---- 4. Register --------------------------------------------------------
    registry.add(
        ToolRecord(
            name=res.spec.function_name,
            task_id=task_id,
            code=res.code,
            tests=res.tests,
            docstring=res.spec.docstring,
            mutation_score=(report.score if report else None),
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        embedding=llm.embed(res.spec.docstring),
    )
    return Outcome(
        task_id=task_id,
        decision="admitted",
        tool_name=res.spec.function_name,
        mutation=report,
        synthesis=res,
    )
