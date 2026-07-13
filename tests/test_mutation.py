"""Behavioural tests for sea.mutation — the mutation engine.

This module is the paper's contribution, so these tests assert on real mutated
programs really executed against real test suites. The key test is
``test_strong_suite_scores_far_higher_than_weak_suite_on_same_impl``: if the
mutation score does not discriminate a thorough suite from a vacuous one, the
whole thesis (H2) is unsupportable.
"""

from __future__ import annotations

import ast

import pytest

from sea.mutation import Mutant, generate_mutants, mutation_score
from sea.sandbox import run_pytest

# --------------------------------------------------------------------------
# Sources that contain exactly the construct each operator targets
# --------------------------------------------------------------------------

AOR_SRC = "def f(a, b):\n    return a + b\n"
ROR_SRC = "def f(a, b):\n    return a < b\n"
COR_SRC = "def f(a, b):\n    return a and b\n"
CRP_SRC = "def f():\n    return 41\n"
RVR_SRC = "def f(a):\n    return a\n"
SDL_SRC = "def f(a):\n    x = a\n    return x\n"
UOI_REMOVE_SRC = "def f(a):\n    if not a:\n        return 1\n    return 2\n"
UOI_INSERT_SRC = "def f(a):\n    if a:\n        return 1\n    return 2\n"


def _normalized(source: str) -> str:
    """The source as the mutation engine would regenerate it, unmutated."""
    return ast.unparse(ast.parse(source))


# --------------------------------------------------------------------------
# Operator coverage: every operator fires on its target construct
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("operator", "source"),
    [
        ("AOR", AOR_SRC),
        ("ROR", ROR_SRC),
        ("COR", COR_SRC),
        ("CRP", CRP_SRC),
        ("RVR", RVR_SRC),
        ("SDL", SDL_SRC),
        ("UOI", UOI_REMOVE_SRC),
        ("UOI", UOI_INSERT_SRC),
    ],
)
def test_operator_fires_on_its_target_construct(operator: str, source: str) -> None:
    mutants = generate_mutants(source)

    assert operator in {m.operator for m in mutants}


def test_aor_replaces_addition_with_subtraction() -> None:
    mutants = [m for m in generate_mutants(AOR_SRC) if m.operator == "AOR"]

    assert len(mutants) == 1
    mutant = mutants[0]
    assert mutant.before == "a + b"
    assert mutant.after == "a - b"
    assert "return a - b" in mutant.code
    assert mutant.lineno == 2


def test_ror_produces_both_boundary_and_inversion_variants() -> None:
    """``<`` mutates to both ``<=`` (boundary) and ``>`` (inversion)."""
    afters = {m.after for m in generate_mutants(ROR_SRC) if m.operator == "ROR"}

    assert afters == {"a <= b", "a > b"}


def test_cor_swaps_and_for_or() -> None:
    mutants = [m for m in generate_mutants(COR_SRC) if m.operator == "COR"]

    assert [m.after for m in mutants] == ["a or b"]


def test_crp_increments_integer_constant() -> None:
    mutants = [m for m in generate_mutants(CRP_SRC) if m.operator == "CRP"]

    assert [m.after for m in mutants] == ["42"]


def test_rvr_replaces_returned_value_with_none() -> None:
    mutants = [m for m in generate_mutants(RVR_SRC) if m.operator == "RVR"]

    assert [m.after for m in mutants] == ["return None"]


def test_sdl_replaces_statement_with_pass() -> None:
    mutants = [m for m in generate_mutants(SDL_SRC) if m.operator == "SDL"]

    assert {m.after for m in mutants} == {"pass"}
    assert {m.before for m in mutants} == {"x = a", "return x"}


def test_uoi_removes_existing_not() -> None:
    mutants = [m for m in generate_mutants(UOI_REMOVE_SRC) if m.operator == "UOI"]

    assert [m.after for m in mutants] == ["a"]


def test_uoi_inserts_not_in_boolean_context() -> None:
    mutants = [m for m in generate_mutants(UOI_INSERT_SRC) if m.operator == "UOI"]

    assert [m.after for m in mutants] == ["not a"]


def test_crp_flips_booleans_and_perturbs_strings() -> None:
    source = "def f():\n    flag = True\n    name = 'hello'\n    return flag, name\n"

    afters = {m.after for m in generate_mutants(source) if m.operator == "CRP"}

    assert "False" in afters
    assert "''" in afters


# --------------------------------------------------------------------------
# Structural invariants of every generated mutant
# --------------------------------------------------------------------------


def test_every_mutant_is_syntactically_valid_python() -> None:
    source = (
        "def grade(score):\n"
        "    if score >= 90 and score <= 100:\n"
        "        return 'A'\n"
        "    total = 0\n"
        "    for i in range(score):\n"
        "        total += i * 2\n"
        "    return not total\n"
    )

    mutants = generate_mutants(source, max_mutants=100)

    assert len(mutants) > 10
    for mutant in mutants:
        ast.parse(mutant.code)  # raises SyntaxError if the engine emitted junk


def test_no_mutant_is_identical_to_the_original() -> None:
    source = "def f(a):\n    if not a:\n        return None\n    return a + 1\n"
    original = _normalized(source)

    mutants = generate_mutants(source, max_mutants=100)

    assert mutants
    for mutant in mutants:
        assert mutant.code != original


def test_noop_mutants_are_excluded() -> None:
    """``return None`` has no RVR mutant: rewriting it to None changes nothing."""
    mutants = generate_mutants("def f(a):\n    return None\n", max_mutants=100)

    assert not [m for m in mutants if m.operator == "RVR"]


def test_duplicate_mutants_are_excluded() -> None:
    """``not not a`` yields the same program whichever ``not`` is removed."""
    source = "def f(a):\n    if not not a:\n        return 1\n    return 2\n"

    mutants = generate_mutants(source, max_mutants=100)

    codes = [m.code for m in mutants]
    assert len(codes) == len(set(codes))


def test_docstrings_are_never_mutated() -> None:
    """Docstring mutants are equivalent mutants: no test can ever kill them.

    Leaving them in would guarantee a survivor on every tool and depress every
    mutation score by a constant, biased amount.
    """
    source = (
        '"""Module docstring."""\n\n\n'
        "def f(a):\n"
        '    """Function docstring."""\n'
        "    return a + 1\n"
    )

    mutants = generate_mutants(source, max_mutants=100)

    assert mutants
    for mutant in mutants:
        assert "Module docstring." in mutant.code
        assert "Function docstring." in mutant.code


def test_mutants_are_indexed_contiguously_from_zero() -> None:
    mutants = generate_mutants(
        "def f(a, b):\n    return a + b * 2\n", max_mutants=100
    )

    assert [m.index for m in mutants] == list(range(len(mutants)))


def test_mutant_lineno_points_at_the_original_line() -> None:
    source = "def f(a):\n    x = a + 1\n    y = x * 2\n    return y\n"

    by_line = {m.lineno for m in generate_mutants(source, max_mutants=100)}

    assert by_line <= {2, 3, 4}
    assert {2, 3, 4} <= by_line


# --------------------------------------------------------------------------
# Determinism and unbiased sampling under the cap
# --------------------------------------------------------------------------

MANY_SITES_SRC = (
    "def f(a, b, c, d):\n"
    "    p = a + b\n"
    "    q = c + d\n"
    "    r = p + q\n"
    "    s = r + a\n"
    "    t = s + b\n"
    "    u = t + c\n"
    "    return u\n"
)


def test_generate_mutants_is_deterministic_under_a_fixed_seed() -> None:
    first = generate_mutants(MANY_SITES_SRC, max_mutants=5, seed=7)
    second = generate_mutants(MANY_SITES_SRC, max_mutants=5, seed=7)

    assert first == second


def test_capping_samples_across_operators_not_just_the_commonest() -> None:
    """The cap must not starve rare operators.

    This source has 6 AOR sites and 7 SDL sites but only 1 RVR site. Taking the
    first N, or sampling uniformly over sites, would usually miss RVR entirely.
    Round-robin across operators guarantees it appears.
    """
    for seed in range(8):
        mutants = generate_mutants(MANY_SITES_SRC, max_mutants=3, seed=seed)

        assert len(mutants) == 3
        assert {m.operator for m in mutants} == {"AOR", "RVR", "SDL"}


def test_capping_samples_across_the_file_not_just_the_top() -> None:
    """The cap must not bias toward the top of the file.

    The six AOR sites sit on lines 2..7. Sites are enumerated in source order,
    so an implementation that just took the first N could *never* draw the AOR
    site on line 7, under any seed. Uniform sampling within the operator reaches
    every line. Fixed seeds, so this is a deterministic check, not a flaky one.
    """
    first_aor_line, last_aor_line = 2, 7
    reached = set()
    for seed in range(20):
        mutants = generate_mutants(MANY_SITES_SRC, max_mutants=6, seed=seed)
        reached.update(m.lineno for m in mutants if m.operator == "AOR")

    assert last_aor_line in reached, "sampling never reaches the bottom of the file"
    assert first_aor_line in reached
    assert reached == {2, 3, 4, 5, 6, 7}


def test_max_mutants_is_respected() -> None:
    mutants = generate_mutants(MANY_SITES_SRC, max_mutants=4, seed=0)

    assert len(mutants) == 4


def test_source_with_no_mutable_construct_yields_no_mutants() -> None:
    assert generate_mutants("import os\n") == []


def test_mutants_are_frozen_dataclasses() -> None:
    mutant = generate_mutants(AOR_SRC)[0]

    assert isinstance(mutant, Mutant)
    with pytest.raises(AttributeError):
        mutant.index = 99  # type: ignore[misc]


def test_syntax_error_in_source_propagates() -> None:
    with pytest.raises(SyntaxError):
        generate_mutants("def f(:\n    pass\n")


# --------------------------------------------------------------------------
# mutation_score — the semantics the whole result rests on
# --------------------------------------------------------------------------

GRADE_IMPL = (
    "def grade(score):\n"
    "    if score >= 90:\n"
    "        return 'A'\n"
    "    if score >= 80:\n"
    "        return 'B'\n"
    "    return 'F'\n"
)

#: Pins every branch and every boundary. Should kill essentially everything.
STRONG_SUITE = (
    "from tool import grade\n\n\n"
    "def test_boundaries():\n"
    "    assert grade(100) == 'A'\n"
    "    assert grade(90) == 'A'\n"
    "    assert grade(89) == 'B'\n"
    "    assert grade(80) == 'B'\n"
    "    assert grade(79) == 'F'\n"
    "    assert grade(0) == 'F'\n"
)

#: Exercises one value on one branch. Passes, and verifies almost nothing —
#: exactly the kind of self-generated suite the thesis is about.
WEAK_SUITE = (
    "from tool import grade\n\n\n"
    "def test_typical():\n"
    "    assert grade(95) == 'A'\n"
)


def test_strong_suite_scores_far_higher_than_weak_suite_on_same_impl() -> None:
    """The discriminative test. If this fails, H2 is unsupportable.

    Same implementation, same seed, therefore the same mutants — the only
    variable is the quality of the suite. A suite that pins the boundaries kills
    nearly every mutant; one that checks a single interior value is blind to most
    of them, including both off-by-one boundary faults (``>=`` → ``>``, ``90`` →
    ``91``) and the whole of the second branch.
    """
    strong = mutation_score(GRADE_IMPL, STRONG_SUITE, timeout_s=5.0)
    weak = mutation_score(GRADE_IMPL, WEAK_SUITE, timeout_s=5.0)

    # Apples to apples: identical mutant sets.
    assert strong.total == weak.total
    assert strong.total > 10

    assert strong.score >= 0.9, f"strong suite scored only {strong.score}"
    assert weak.score <= 0.5, f"weak suite scored {weak.score}, too high to discriminate"
    assert strong.score > weak.score
    assert len(weak.survivors) > len(strong.survivors)


def test_survivors_really_do_pass_the_suite() -> None:
    """Verify the KILLED/SURVIVED semantics against the sandbox itself.

    A survivor is *defined* as a mutant the suite still passes on. Re-executing
    each reported survivor must therefore reproduce a pass. This is what makes
    the survivor list trustworthy as the object of study.
    """
    report = mutation_score(GRADE_IMPL, WEAK_SUITE, timeout_s=5.0)

    assert report.survivors
    for survivor in report.survivors:
        result = run_pytest(survivor.code, WEAK_SUITE, timeout_s=5.0)
        assert result.status == "passed", (
            f"mutant {survivor.index} ({survivor.operator}: "
            f"{survivor.before!r} -> {survivor.after!r}) was reported as a "
            f"survivor but the suite does not pass on it ({result.status})"
        )


def test_report_arithmetic_is_consistent() -> None:
    report = mutation_score(GRADE_IMPL, WEAK_SUITE, timeout_s=5.0)

    assert report.killed + report.survived == report.total
    assert report.survived == len(report.survivors)
    assert report.timed_out <= report.killed
    assert report.score == pytest.approx(report.killed / report.total)


def test_timeouts_are_counted_as_killed() -> None:
    """An induced infinite loop is a detected behaviour change, not a survivor.

    ``n = n - 1`` mutates to ``n = n + 1``, which never terminates. The suite
    cannot assert on it, but the behaviour demonstrably changed, so it counts as
    killed — and is reported separately so the reader can see how much of the
    score rests on that weaker signal.
    """
    impl = (
        "def countdown(n):\n"
        "    total = 0\n"
        "    while n > 0:\n"
        "        total = total + n\n"
        "        n = n - 1\n"
        "    return total\n"
    )
    suite = (
        "from tool import countdown\n\n\n"
        "def test_countdown():\n"
        "    assert countdown(4) == 10\n"
    )

    report = mutation_score(impl, suite, timeout_s=2.0)

    assert report.timed_out >= 1, "expected the n+1 mutant to hang"
    # Timeouts are inside `killed`, not a third bucket.
    assert report.killed + report.survived == report.total
    assert report.killed >= report.timed_out


def test_raises_when_impl_does_not_pass_its_own_tests() -> None:
    """Mutation score is undefined on a failing implementation, not zero."""
    broken_impl = "def add(a, b):\n    return a - b\n"
    suite = "from tool import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"

    with pytest.raises(ValueError, match="undefined"):
        mutation_score(broken_impl, suite)


def test_raises_when_suite_is_vacuous() -> None:
    """An empty suite collects no tests; that is an error, not a pass."""
    with pytest.raises(ValueError, match="undefined"):
        mutation_score(GRADE_IMPL, "# I assert nothing\n")


def test_score_is_zero_when_there_are_no_mutants() -> None:
    impl = "def noop():\n    pass\n"
    suite = "from tool import noop\n\n\ndef test_noop():\n    assert noop() is None\n"

    report = mutation_score(impl, suite)

    assert report.total == 0
    assert report.score == 0.0
    assert report.killed == 0
    assert report.survivors == []
