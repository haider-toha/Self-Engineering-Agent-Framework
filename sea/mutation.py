"""AST mutation operators and the mutation score — the research contribution.

The mutation score of a test suite is the fraction of small, semantics-changing
edits to the implementation ("mutants") that the suite detects. It is the
standard measure of *test adequacy*, and in this project it is the candidate
predictor of whether a self-verified tool is safe to admit to the library (H2),
and the quantity an admission gate thresholds on (H3).

Semantics
---------
* A mutant is **KILLED** if the suite does not pass on it — the suite detected
  the injected fault. Anything other than a clean pass counts: a failed
  assertion, an error, a crash, a timeout.
* A mutant **SURVIVED** if the suite still passes. Survivors are the interesting
  ones: they are faults the suite is blind to, and they are reported in full.
* A **timeout counts as KILLED** — an induced infinite loop is a demonstrable
  behaviour change — but is also reported separately in ``timed_out`` so that a
  reader can see how much of the score rests on that weaker signal.
* ``score = killed / total``, and ``0.0`` when there are no mutants.

Operator set (mirrors mutmut / cosmic-ray)
------------------------------------------
=====  ==========================  =================================================
Code   Operator                    Replacements
=====  ==========================  =================================================
AOR    Arithmetic replacement      ``+``↔``-``, ``*``↔``/``, ``//``↔``/``, ``%``↔``*``
ROR    Relational replacement      ``<``↔``<=``, ``>``↔``>=``, ``==``↔``!=``, ``<``↔``>``
COR    Boolean replacement         ``and``↔``or``
CRP    Constant replacement        int ``n``→``n+1``, ``True``↔``False``, string perturbation
RVR    Return value replacement    ``return X`` → ``return None``
SDL    Statement deletion          statement → ``pass``
UOI    Unary operator insertion    ``not X`` ↔ ``X``
=====  ==========================  =================================================

Equivalent mutants
------------------
An *equivalent mutant* changes the source without changing behaviour, so no test
can ever kill it. Detecting them in general is undecidable, and we do **not**
claim to solve it. We apply the standard mitigations, and state them so the
denominator is interpretable:

* mutants whose regenerated source is byte-identical to the original are dropped;
* duplicate mutants (distinct sites, identical resulting program) are dropped;
* **docstrings are never mutated** — a mutated docstring is an equivalent mutant
  by construction, and leaving them in would hand every tool a guaranteed
  survivor and depress every score by a biased constant;
* SDL is confined to statements inside function bodies, so we do not manufacture
  trivially-killed mutants (deleting an ``import`` or a whole ``def`` breaks the
  module for *any* suite, including an empty one, and would inflate the score);
* timeouts count as killed.

Residual equivalent mutants remain — e.g. ``x * 1`` → ``x / 1`` on integers.
They depress the score slightly and uniformly, and we report the operator set
explicitly so the number can be reproduced.

Determinism
-----------
Mutation sites are enumerated in a stable pre-order walk of the AST. When more
sites exist than ``max_mutants``, the sample is drawn round-robin across
operators (so a rare operator is never starved by a common one) and uniformly at
random *within* each operator (so the sample is not biased toward the top of the
file, which is what taking the first N would do). The same ``seed`` always
yields exactly the same mutants.
"""

from __future__ import annotations

import ast
import copy
import random
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from sea.sandbox import run_pytest

__all__ = [
    "OPERATORS",
    "Mutant",
    "MutationReport",
    "Operator",
    "generate_mutants",
    "mutation_score",
]

Operator = Literal["AOR", "ROR", "COR", "CRP", "RVR", "SDL", "UOI"]

#: Every operator this engine implements, in a stable order.
OPERATORS: tuple[Operator, ...] = ("AOR", "ROR", "COR", "CRP", "RVR", "SDL", "UOI")

# ``+``↔``-``, ``*``↔``/``, ``//``↔``/``, ``%``↔``*``, read bidirectionally.
_AOR_REPLACEMENTS: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
    ast.Add: (ast.Sub,),
    ast.Sub: (ast.Add,),
    ast.Mult: (ast.Div, ast.Mod),
    ast.Div: (ast.Mult, ast.FloorDiv),
    ast.FloorDiv: (ast.Div,),
    ast.Mod: (ast.Mult,),
}

# ``<``↔``<=``, ``>``↔``>=``, ``==``↔``!=``, ``<``↔``>``, read bidirectionally.
# Identity comparisons (``is``, ``in``) are deliberately out of scope.
_ROR_REPLACEMENTS: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
    ast.Lt: (ast.LtE, ast.Gt),
    ast.LtE: (ast.Lt,),
    ast.Gt: (ast.GtE, ast.Lt),
    ast.GtE: (ast.Gt,),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}

#: Statements SDL must not touch. Deleting an import or a definition breaks the
#: module for every conceivable suite, which is a trivially-killed mutant, not a
#: measurement. ``Pass`` is excluded because replacing it with ``pass`` is a
#: no-op.
_SDL_EXEMPT: tuple[type[ast.stmt], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.Pass,
)


@dataclass(frozen=True)
class Mutant:
    """One mutated program.

    Attributes:
        index: Position in the returned list, ``0``-based.
        operator: The operator that produced it, one of :data:`OPERATORS`.
        lineno: Line of the mutated construct **in the original source**.
        before: Unparsed source of the construct before mutation, e.g. ``a + b``.
        after: Unparsed source of the construct after mutation, e.g. ``a - b``.
        code: The full mutated module source, ready to execute.
    """

    index: int
    operator: str
    lineno: int
    before: str
    after: str
    code: str


@dataclass(frozen=True)
class MutationReport:
    """Result of scoring a test suite against the mutants of its implementation.

    Attributes:
        total: Number of mutants executed.
        killed: Mutants the suite detected. Includes ``timed_out``.
        survived: Mutants the suite passed on — faults it is blind to.
        timed_out: Subset of ``killed`` that were killed by exhausting the time
            budget rather than by an assertion.
        score: ``killed / total``; ``0.0`` when ``total == 0``.
        survivors: The surviving mutants, in full, for inspection.
    """

    total: int
    killed: int
    survived: int
    timed_out: int
    score: float
    survivors: list[Mutant]


@dataclass(frozen=True)
class _Candidate:
    """A mutant before it is sampled and given its final index."""

    operator: Operator
    lineno: int
    col_offset: int
    before: str
    after: str
    code: str


def generate_mutants(
    source: str,
    *,
    max_mutants: int = 30,
    seed: int = 0,
) -> list[Mutant]:
    """Generate mutants of ``source``.

    Every mutant is a complete, syntactically valid module, regenerated with
    ``ast.unparse``. Mutants identical to the original (no-ops) and mutants
    identical to each other (distinct sites, same resulting program) are
    dropped, so ``total`` is a count of *distinct programs*.

    Args:
        source: The implementation module source.
        max_mutants: Upper bound on how many mutants to return. When more sites
            exist, they are sampled round-robin across operators and uniformly
            within each operator — never simply the first ``max_mutants``, which
            would bias the sample toward the top of the file.
        seed: Seed for the sampler. The same seed always yields the same mutants.

    Returns:
        The mutants, ordered by source position, indexed contiguously from 0.

    Raises:
        SyntaxError: If ``source`` does not parse.
    """
    tree = ast.parse(source)
    original = ast.unparse(tree)

    candidates = _collect_candidates(tree, original)
    selected = _sample(candidates, max_mutants=max_mutants, seed=seed)

    # Canonical order: by position in the file, then by operator, so that the
    # returned indices are stable and readable.
    selected.sort(key=lambda c: (c.lineno, c.col_offset, c.operator, c.after))

    return [
        Mutant(
            index=index,
            operator=candidate.operator,
            lineno=candidate.lineno,
            before=candidate.before,
            after=candidate.after,
            code=candidate.code,
        )
        for index, candidate in enumerate(selected)
    ]


def mutation_score(
    impl_code: str,
    test_code: str,
    *,
    max_mutants: int = 30,
    seed: int = 0,
    timeout_s: float = 5.0,
) -> MutationReport:
    """Score how many of ``impl_code``'s mutants ``test_code`` kills.

    The unmutated implementation **must** pass its own suite. If it does not,
    the mutation score is not merely low, it is *undefined*: every mutant would
    be recorded as killed by a suite that was already failing, and the number
    would be meaningless. We refuse rather than return a plausible-looking 0.

    Args:
        impl_code: The implementation under test.
        test_code: The suite that admitted it. Never modified (ADR-003).
        max_mutants: Cap on mutants generated.
        seed: Seed for mutant sampling.
        timeout_s: Per-mutant wall-clock budget. A mutant that exceeds it is
            counted as killed, and separately in ``timed_out``.

    Returns:
        The :class:`MutationReport`.

    Raises:
        ValueError: If ``impl_code`` does not pass ``test_code``.
        SyntaxError: If ``impl_code`` does not parse.
    """
    baseline = run_pytest(impl_code, test_code, timeout_s=timeout_s)
    if baseline.status != "passed":
        raise ValueError(
            "mutation score is undefined: the unmutated implementation does not "
            f"pass its own test suite (sandbox status={baseline.status!r}). "
            "Fix or reject the tool before scoring it.\n"
            f"--- captured stderr ---\n{baseline.stderr[-2000:]}\n"
            f"--- captured stdout ---\n{baseline.stdout[-2000:]}"
        )

    mutants = generate_mutants(impl_code, max_mutants=max_mutants, seed=seed)

    killed = 0
    timed_out = 0
    survivors: list[Mutant] = []

    for mutant in mutants:
        result = run_pytest(mutant.code, test_code, timeout_s=timeout_s)
        if result.status == "passed":
            survivors.append(mutant)
        else:
            # "failed", "error" and "timeout" all mean the suite noticed.
            killed += 1
            if result.status == "timeout":
                timed_out += 1

    total = len(mutants)
    return MutationReport(
        total=total,
        killed=killed,
        survived=len(survivors),
        timed_out=timed_out,
        score=killed / total if total else 0.0,
        survivors=survivors,
    )


# --------------------------------------------------------------------------
# Site enumeration
# --------------------------------------------------------------------------


def _collect_candidates(tree: ast.Module, original: str) -> list[_Candidate]:
    """Enumerate every mutant of ``tree``, in a stable source order."""
    nodes = _preorder(tree)
    context = _Context(tree)

    candidates: list[_Candidate] = []
    seen: set[str] = {original}

    for index, node in enumerate(nodes):
        for operator, mutate in _mutations_for(node, context):
            code, before, after = _apply(tree, index, node, mutate)
            # Drop no-ops (identical to the original) and duplicates (a
            # different site that happens to yield the same program, e.g. either
            # ``not`` removed from ``not not x``).
            if code in seen:
                continue
            seen.add(code)
            candidates.append(
                _Candidate(
                    operator=operator,
                    lineno=getattr(node, "lineno", 1),
                    col_offset=getattr(node, "col_offset", 0),
                    before=before,
                    after=after,
                    code=code,
                )
            )

    return candidates


class _Context:
    """Whole-tree facts a single node cannot know about itself."""

    def __init__(self, tree: ast.Module) -> None:
        self.docstring_exprs: set[int] = set()
        self.docstring_constants: set[int] = set()
        self.function_statements: set[int] = set()
        self.boolean_contexts: set[int] = set()

        for node in ast.walk(tree):
            self._note_docstring(node)
            self._note_function_body(node)
            self._note_boolean_context(node)

    def _note_docstring(self, node: ast.AST) -> None:
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            return
        if not node.body:
            return
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            self.docstring_exprs.add(id(first))
            self.docstring_constants.add(id(first.value))

    def _note_function_body(self, node: ast.AST) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        for statement in node.body:
            for descendant in ast.walk(statement):
                if isinstance(descendant, ast.stmt):
                    self.function_statements.add(id(descendant))

    def _note_boolean_context(self, node: ast.AST) -> None:
        """Record expressions Python will coerce to a truth value.

        UOI only inserts ``not`` here. Inserting it on an arbitrary expression
        would be legal Python but would mostly produce nonsense that any test
        kills, inflating the score with trivial mutants.
        """
        if isinstance(node, (ast.If, ast.While, ast.IfExp, ast.Assert)):
            self.boolean_contexts.add(id(node.test))
        elif isinstance(node, ast.BoolOp):
            for value in node.values:
                self.boolean_contexts.add(id(value))
        elif isinstance(node, ast.comprehension):
            for guard in node.ifs:
                self.boolean_contexts.add(id(guard))


_Mutate = Callable[[ast.AST], ast.AST]


def _mutations_for(
    node: ast.AST, context: _Context
) -> list[tuple[Operator, _Mutate]]:
    """Every (operator, edit) pair applicable at ``node``."""
    mutations: list[tuple[Operator, _Mutate]] = []
    mutations.extend(_aor(node))
    mutations.extend(_ror(node))
    mutations.extend(_cor(node))
    mutations.extend(_crp(node, context))
    mutations.extend(_rvr(node))
    mutations.extend(_sdl(node, context))
    mutations.extend(_uoi(node, context))
    return mutations


def _aor(node: ast.AST) -> list[tuple[Operator, _Mutate]]:
    """Arithmetic operator replacement, on binary and augmented assignment."""
    if not isinstance(node, (ast.BinOp, ast.AugAssign)):
        return []

    mutations: list[tuple[Operator, _Mutate]] = []
    for replacement in _AOR_REPLACEMENTS.get(type(node.op), ()):

        def mutate(
            target: ast.AST,
            replacement: type[ast.operator] = replacement,
        ) -> ast.AST:
            target.op = replacement()  # type: ignore[attr-defined]
            return target

        mutations.append(("AOR", mutate))
    return mutations


def _ror(node: ast.AST) -> list[tuple[Operator, _Mutate]]:
    """Relational operator replacement, per position in a comparison chain."""
    if not isinstance(node, ast.Compare):
        return []

    mutations: list[tuple[Operator, _Mutate]] = []
    for position, op in enumerate(node.ops):
        for replacement in _ROR_REPLACEMENTS.get(type(op), ()):

            def mutate(
                target: ast.AST,
                position: int = position,
                replacement: type[ast.cmpop] = replacement,
            ) -> ast.AST:
                target.ops[position] = replacement()  # type: ignore[attr-defined]
                return target

            mutations.append(("ROR", mutate))
    return mutations


def _cor(node: ast.AST) -> list[tuple[Operator, _Mutate]]:
    """Boolean connector replacement: ``and`` ↔ ``or``."""
    if not isinstance(node, ast.BoolOp):
        return []

    replacement = ast.Or if isinstance(node.op, ast.And) else ast.And

    def mutate(target: ast.AST) -> ast.AST:
        target.op = replacement()  # type: ignore[attr-defined]
        return target

    return [("COR", mutate)]


def _crp(node: ast.AST, context: _Context) -> list[tuple[Operator, _Mutate]]:
    """Constant replacement.

    Booleans are checked before integers: ``isinstance(True, int)`` is true in
    Python, and mutating ``True`` to ``2`` would be both wrong and unkillable in
    a boolean context.
    """
    if not isinstance(node, ast.Constant) or id(node) in context.docstring_constants:
        return []

    value = node.value
    if isinstance(value, bool):
        new_value: object = not value
    elif isinstance(value, int):
        new_value = value + 1
    elif isinstance(value, str):
        # "" → "x" and, symmetrically, any non-empty string → "". Every string
        # constant gets a mutant, and none of them is ever a no-op.
        new_value = "x" if value == "" else ""
    else:
        # Floats, bytes, None and complex are out of the declared operator set.
        return []

    def mutate(target: ast.AST) -> ast.AST:
        return ast.copy_location(ast.Constant(value=new_value), target)

    return [("CRP", mutate)]


def _rvr(node: ast.AST) -> list[tuple[Operator, _Mutate]]:
    """Return value replacement: ``return X`` → ``return None``."""
    if not isinstance(node, ast.Return) or node.value is None:
        return []
    if isinstance(node.value, ast.Constant) and node.value.value is None:
        return []  # already `return None`; the mutant would be a no-op

    def mutate(target: ast.AST) -> ast.AST:
        return ast.copy_location(
            ast.Return(value=ast.copy_location(ast.Constant(value=None), target)),
            target,
        )

    return [("RVR", mutate)]


def _sdl(node: ast.AST, context: _Context) -> list[tuple[Operator, _Mutate]]:
    """Statement deletion: replace a statement with ``pass``.

    Replacing rather than removing keeps every block non-empty, so the mutant is
    always syntactically valid.
    """
    if not isinstance(node, ast.stmt):
        return []
    if id(node) not in context.function_statements:
        return []
    if isinstance(node, _SDL_EXEMPT) or id(node) in context.docstring_exprs:
        return []

    def mutate(target: ast.AST) -> ast.AST:
        return ast.copy_location(ast.Pass(), target)

    return [("SDL", mutate)]


def _uoi(node: ast.AST, context: _Context) -> list[tuple[Operator, _Mutate]]:
    """Unary operator insertion/removal: ``not X`` ↔ ``X``."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):

        def remove(target: ast.AST) -> ast.AST:
            return target.operand  # type: ignore[attr-defined]

        return [("UOI", remove)]

    if id(node) in context.boolean_contexts:
        # `not not X` is pointless: removal on the inner node already covers it.
        def insert(target: ast.AST) -> ast.AST:
            return ast.copy_location(
                ast.UnaryOp(op=ast.Not(), operand=target), target
            )

        return [("UOI", insert)]

    return []


# --------------------------------------------------------------------------
# Mutant construction
# --------------------------------------------------------------------------


def _preorder(tree: ast.AST) -> list[ast.AST]:
    """Nodes in pre-order.

    This is exactly the order :class:`ast.NodeTransformer` visits them, which is
    what lets ``_Applier`` find node ``i`` of a *copy* of the tree by counting.
    """
    nodes: list[ast.AST] = []

    def walk(node: ast.AST) -> None:
        nodes.append(node)
        for child in ast.iter_child_nodes(node):
            walk(child)

    walk(tree)
    return nodes


class _Applier(ast.NodeTransformer):
    """Apply one edit to the node at a given pre-order index."""

    def __init__(self, target_index: int, mutate: _Mutate) -> None:
        self._target_index = target_index
        self._mutate = mutate
        self._counter = 0

    def visit(self, node: ast.AST) -> ast.AST:
        index = self._counter
        self._counter += 1
        if index == self._target_index:
            return self._mutate(node)
        return self.generic_visit(node)


def _apply(
    tree: ast.Module,
    target_index: int,
    original_node: ast.AST,
    mutate: _Mutate,
) -> tuple[str, str, str]:
    """Return ``(mutated_module_source, before_snippet, after_snippet)``.

    ``original_node`` must be the node at ``target_index`` in ``_preorder(tree)``;
    the caller already has it, so we do not re-walk the tree for every candidate.
    """
    before = ast.unparse(original_node)

    # Preview the edit on an isolated copy of the node, so `after` describes the
    # construct rather than the whole module.
    after = ast.unparse(mutate(copy.deepcopy(original_node)))

    mutated = _Applier(target_index, mutate).visit(copy.deepcopy(tree))
    ast.fix_missing_locations(mutated)
    return ast.unparse(mutated), before, after


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------


def _sample(
    candidates: list[_Candidate], *, max_mutants: int, seed: int
) -> list[_Candidate]:
    """Draw at most ``max_mutants`` candidates, unbiased and deterministically.

    Round-robin across operators, so a common operator cannot crowd out a rare
    one; uniformly at random within each operator, so the draw is not biased
    toward the top of the file.
    """
    if max_mutants <= 0:
        return []
    if len(candidates) <= max_mutants:
        return list(candidates)

    rng = random.Random(seed)

    pools: dict[Operator, list[_Candidate]] = defaultdict(list)
    for candidate in candidates:
        pools[candidate.operator].append(candidate)

    # Sorted keys, so the rng is consumed in an order that does not depend on
    # dict insertion order.
    for operator in sorted(pools):
        rng.shuffle(pools[operator])

    selected: list[_Candidate] = []
    while len(selected) < max_mutants:
        available = [operator for operator in sorted(pools) if pools[operator]]
        if not available:
            break
        # Shuffle the round order too: otherwise a cap that cuts mid-round would
        # systematically favour whichever operator sorts first.
        rng.shuffle(available)
        for operator in available:
            if len(selected) >= max_mutants:
                break
            selected.append(pools[operator].pop())

    return selected
