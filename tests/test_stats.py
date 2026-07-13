"""Tests for `sea.eval.stats` -- the pure functions behind every reported number.

These are the functions that turn raw pass/fail observations into the figures the
paper stands on. They are pure, so they are tested against *independent* sources
of truth: published reference values, a numerically-solved definition, or a
hand-computed worked example. Nowhere is an expected value recomputed the way
the implementation computes it -- a test that mirrors the code's own arithmetic
cannot disagree with the code, and so tests nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from sea.eval.stats import (
    _rankdata,
    auc,
    auc_with_ci,
    bootstrap_ci,
    far,
    paired_auc_delta_ci,
    wilson_ci,
)

Z = 1.96


# ---------------------------------------------------------------------------
# Independent oracles. Neither reproduces the closed form under test.
# ---------------------------------------------------------------------------


def wilson_by_root_finding(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """Solve the Wilson interval from its *definition*, not its closed form.

    The Wilson score interval is defined as the set of proportions ``p`` that the
    score test does not reject::

        (p_hat - p)^2 <= z^2 * p(1 - p) / n

    ``stats.wilson_ci`` returns the algebraic solution of that inequality. Here
    we find the same set numerically on a dense grid. Agreement between the two
    validates the algebra; a slip in the closed form would show up immediately.
    """
    p_hat = k / n
    grid = np.linspace(0.0, 1.0, 200_001)
    satisfied = (p_hat - grid) ** 2 <= z * z * grid * (1 - grid) / n
    inside = grid[satisfied]
    return float(inside.min()), float(inside.max())


def auc_by_definition(scores: list[float], labels: list[int]) -> float:
    """AUC straight from its probabilistic definition.

    AUC is the probability that a randomly drawn positive outranks a randomly
    drawn negative, ties counting half. This enumerates every positive/negative
    pair. ``stats.auc`` instead uses the Mann-Whitney rank identity -- a
    different computation entirely, which is what makes this a real cross-check.
    """
    pos = [s for s, label in zip(scores, labels) if label == 1]
    neg = [s for s, label in zip(scores, labels) if label == 0]
    wins = sum(
        1.0 if a > b else 0.5 if a == b else 0.0 for a in pos for b in neg
    )
    return wins / (len(pos) * len(neg))


def wald_ci(k: int, n: int, z: float = Z) -> tuple[float, float]:
    """The normal-approximation interval Wilson was chosen over. Not clamped."""
    p = k / n
    margin = z * float(np.sqrt(p * (1 - p) / n))
    return (p - margin, p + margin)


# ---------------------------------------------------------------------------
# wilson_ci
# ---------------------------------------------------------------------------


def test_wilson_ci_matches_the_published_reference_interval() -> None:
    """k=2, n=10 is a standard worked example: the 95% interval is ~[.057, .510]."""
    lo, hi = wilson_ci(2, 10)

    assert lo == pytest.approx(0.0567, abs=5e-4)
    assert hi == pytest.approx(0.5098, abs=5e-4)


@pytest.mark.parametrize(
    ("k", "n"),
    [(0, 10), (1, 5), (2, 10), (5, 100), (9, 10), (10, 10), (50, 100)],
)
def test_wilson_ci_endpoints_solve_the_score_equation(k: int, n: int) -> None:
    """The closed form must agree with the definition it claims to solve."""
    expected_lo, expected_hi = wilson_by_root_finding(k, n)
    lo, hi = wilson_ci(k, n)

    assert lo == pytest.approx(expected_lo, abs=1e-4)
    assert hi == pytest.approx(expected_hi, abs=1e-4)


def test_wilson_ci_with_zero_trials_returns_zeros_without_dividing_by_zero() -> None:
    """n=0 happens whenever a gate admits nothing. It must not explode."""
    assert wilson_ci(0, 0) == (0.0, 0.0)


@pytest.mark.parametrize("k", range(0, 11))
def test_wilson_ci_never_escapes_the_unit_interval(k: int) -> None:
    """A probability outside [0, 1] is not a probability. True even at k=0 and k=n.

    This is the whole reason Wilson was chosen -- see the Wald tests below.
    """
    lo, hi = wilson_ci(k, 10)

    assert 0.0 <= lo <= hi <= 1.0


def test_wilson_ci_brackets_the_observed_proportion() -> None:
    lo, hi = wilson_ci(3, 20)

    assert lo <= 3 / 20 <= hi


# -- why Wilson and not Wald: the two failures Wilson exists to avoid --------


def test_wald_escapes_the_unit_interval_where_wilson_does_not() -> None:
    """The Wald interval for k=1, n=5 runs *below zero*. Wilson stays legal.

    If wilson_ci is ever "simplified" into the normal approximation, this fails.
    """
    wald_lo, _ = wald_ci(1, 5)
    wilson_lo, wilson_hi = wilson_ci(1, 5)

    assert wald_lo < 0.0, "precondition: Wald is supposed to misbehave here"
    assert 0.0 <= wilson_lo <= wilson_hi <= 1.0


@pytest.mark.parametrize("k", [0, 10])
def test_wald_collapses_to_zero_width_at_the_boundaries_where_wilson_does_not(
    k: int,
) -> None:
    """At k=0 (and k=n) Wald claims a *point* estimate with total certainty.

    FAR lands on exactly these boundaries whenever a gate admits nothing wrong,
    which is precisely when an honest interval matters most.
    """
    wald_lo, wald_hi = wald_ci(k, 10)
    wilson_lo, wilson_hi = wilson_ci(k, 10)

    assert wald_hi - wald_lo == pytest.approx(0.0), "precondition: Wald degenerates"
    assert wilson_hi - wilson_lo > 0.15, "Wilson must retain real width"


# ---------------------------------------------------------------------------
# far -- the conditional. This is the number the whole project reports.
# ---------------------------------------------------------------------------


def test_far_conditions_on_admission_and_excludes_everything_else() -> None:
    """FAR is P(fails strong | passed weak). Non-admitted candidates are NOT in it.

    Constructed so the conditioning is load-bearing: the two candidates that
    failed the weak oracle are *also* wrong on the strong oracle. Counting them
    (the naive "how many candidates are wrong" reading) gives 4/5 = 80%. The
    correct conditional is 2/3 = 66.7%. The two answers differ, so this test can
    only pass if the denominator really is restricted to admitted candidates.
    """
    #             admitted?  correct?
    weak_pass = [True, True, True, False, False]
    strong_pass = [True, False, False, False, False]

    result = far(weak_pass, strong_pass)

    assert result.denominator == 3, "denominator must be the ADMITTED candidates"
    assert result.numerator == 2, "numerator must be the admitted-but-wrong ones"
    assert result.value == pytest.approx(2 / 3)
    assert result.value != pytest.approx(4 / 5), "this is the unconditional rate"


def test_far_ignores_a_rejected_candidate_no_matter_how_wrong_it_is() -> None:
    """Adding candidates that never passed the weak oracle cannot move FAR."""
    base = far([True, True], [True, False])
    with_rejects = far(
        [True, True, False, False, False], [True, False, False, False, False]
    )

    assert with_rejects.value == pytest.approx(base.value)
    assert with_rejects.denominator == base.denominator


def test_far_counts_an_admitted_but_wrong_candidate_as_a_false_admission() -> None:
    result = far([True], [False])

    assert result.numerator == 1
    assert result.denominator == 1
    assert result.value == pytest.approx(1.0)


def test_far_with_no_admissions_is_reported_as_not_applicable() -> None:
    """An empty gate output must not fabricate a rate of 0%."""
    result = far([False, False], [False, False])

    assert result.denominator == 0
    assert result.value == 0.0
    assert "n/a" in str(result)


def test_far_carries_a_confidence_interval_that_brackets_the_estimate() -> None:
    result = far([True] * 10, [True] * 8 + [False] * 2)

    assert result.value == pytest.approx(0.2)
    assert result.lo <= result.value <= result.hi
    assert 0.0 <= result.lo <= result.hi <= 1.0


def test_far_raises_on_mismatched_input_lengths() -> None:
    """Misaligned observations would silently mis-pair candidates with verdicts."""
    with pytest.raises(ValueError):
        far([True, False], [True])


# ---------------------------------------------------------------------------
# auc / _rankdata
# ---------------------------------------------------------------------------


def test_auc_of_perfect_separation_is_one() -> None:
    assert auc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([0, 0, 1, 1])) == 1.0


def test_auc_of_perfect_inversion_is_zero() -> None:
    assert auc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([0, 0, 1, 1])) == 0.0


def test_auc_of_a_constant_predictor_is_one_half() -> None:
    """Every score tied => no ranking information => chance."""
    assert auc(np.array([0.5] * 6), np.array([0, 0, 0, 1, 1, 1])) == 0.5


@pytest.mark.parametrize("label", [0, 1])
def test_auc_of_a_single_class_input_is_one_half_not_signal(label: int) -> None:
    """AUC is undefined with one class present. It must return chance, not 1.0.

    A gate that admitted only correct tools has no positives. Reporting a
    perfect AUC there would invent a predictor out of an empty comparison.
    """
    scores = np.array([0.1, 0.5, 0.9])
    labels = np.full(3, label)

    assert auc(scores, labels) == 0.5


def test_rankdata_averages_tied_ranks() -> None:
    """Mann-Whitney requires mid-ranks for ties; ordinal ranks give a wrong AUC."""
    ranks = _rankdata(np.array([2.0, 3.0, 1.0, 2.0]))

    # sorted: 1 -> rank 1; the two 2s share ranks 2 and 3 -> 2.5 each; 3 -> rank 4
    assert list(ranks) == [2.5, 4.0, 1.0, 2.5]


def test_auc_with_ties_matches_the_hand_computed_value() -> None:
    """A worked example where the tie handling changes the answer.

    scores [1, 2, 2, 3], labels [0, 1, 0, 1] => positives {2, 3}, negatives {1, 2}.
    Enumerating the four pairs: (2>1)=1, (2==2)=0.5, (3>1)=1, (3>2)=1 => 3.5/4.

    Averaging ties gives 0.875. Ordinal ranks would give 0.75, so this value can
    only be produced if _rankdata really does average -- it pins the Mann-Whitney
    identity rather than restating it.
    """
    scores = [1.0, 2.0, 2.0, 3.0]
    labels = [0, 1, 0, 1]

    assert auc_by_definition(scores, labels) == 0.875, "independent oracle"
    assert auc(np.array(scores), np.array(labels)) == pytest.approx(0.875)


def test_auc_agrees_with_the_pairwise_definition_on_random_data() -> None:
    """The rank identity and the pairwise definition must never disagree."""
    rng = np.random.default_rng(11)
    scores = rng.integers(0, 5, size=40).astype(float)  # small range => many ties
    labels = (rng.random(40) < 0.5).astype(int)

    expected = auc_by_definition(list(scores), list(labels))

    assert auc(scores, labels) == pytest.approx(expected)


def test_auc_with_ci_reports_the_class_counts_it_scored() -> None:
    labels = np.array([1, 1, 1, 0, 0])
    result = auc_with_ci(np.array([0.9, 0.8, 0.7, 0.2, 0.1]), labels, n_boot=200)

    assert result.n_pos == 3
    assert result.n_neg == 2
    assert result.value == pytest.approx(1.0)
    assert result.lo <= result.value <= result.hi


# ---------------------------------------------------------------------------
# bootstrap_ci / paired_auc_delta_ci
# ---------------------------------------------------------------------------


@pytest.fixture
def observations() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    scores = rng.random(60)
    labels = (rng.random(60) < 0.4).astype(int)
    return scores, labels


def test_bootstrap_ci_is_reproducible_under_a_fixed_seed(
    observations: tuple[np.ndarray, np.ndarray],
) -> None:
    """A published CI that moves between runs is not a result."""
    scores, labels = observations

    first = bootstrap_ci(auc, scores, labels, n_boot=300, seed=0)
    second = bootstrap_ci(auc, scores, labels, n_boot=300, seed=0)

    assert first == second


def test_bootstrap_ci_with_a_different_seed_resamples_differently(
    observations: tuple[np.ndarray, np.ndarray],
) -> None:
    """Guards against the seed being ignored, which would fake reproducibility."""
    scores, labels = observations

    assert bootstrap_ci(auc, scores, labels, n_boot=300, seed=0) != bootstrap_ci(
        auc, scores, labels, n_boot=300, seed=1
    )


def test_bootstrap_ci_brackets_the_point_estimate(
    observations: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, labels = observations

    lo, hi = bootstrap_ci(auc, scores, labels, n_boot=500, seed=0)

    assert lo <= auc(scores, labels) <= hi


def test_bootstrap_ci_of_nothing_is_zero_not_a_crash() -> None:
    empty = np.array([])

    assert bootstrap_ci(auc, empty, empty, n_boot=10) == (0.0, 0.0)


def test_paired_auc_delta_ci_is_reproducible_under_a_fixed_seed(
    observations: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, labels = observations

    first = paired_auc_delta_ci(scores, -scores, labels, n_boot=300, seed=0)
    second = paired_auc_delta_ci(scores, -scores, labels, n_boot=300, seed=0)

    assert first == second


def test_paired_auc_delta_ci_brackets_its_point_estimate(
    observations: tuple[np.ndarray, np.ndarray],
) -> None:
    scores, labels = observations

    delta, lo, hi = paired_auc_delta_ci(scores, -scores, labels, n_boot=500, seed=0)

    assert lo <= delta <= hi


def test_paired_auc_delta_ci_separates_a_real_predictor_from_a_useless_one() -> None:
    """H2 is adjudicated by this: the CI on the AUC gap must exclude zero.

    `informative` ranks the positives correctly; `noise` is unrelated to the
    label. The delta must be clearly positive and its interval must not straddle
    zero -- otherwise the harness could never *support* H2 even if it were true.
    """
    rng = np.random.default_rng(3)
    labels = np.array([0] * 60 + [1] * 60)
    informative = np.concatenate([rng.normal(0.0, 1.0, 60), rng.normal(3.0, 1.0, 60)])
    noise = rng.normal(0.0, 1.0, 120)

    delta, lo, hi = paired_auc_delta_ci(informative, noise, labels, n_boot=500, seed=0)

    assert delta > 0.2
    assert lo > 0.0, "a genuinely better predictor must have a CI excluding zero"
    assert lo <= delta <= hi


def test_paired_auc_delta_ci_does_not_claim_a_difference_between_equal_predictors() -> (
    None
):
    """The same predictor twice has a delta of exactly zero, and a CI containing it."""
    rng = np.random.default_rng(5)
    labels = np.array([0] * 40 + [1] * 40)
    scores = np.concatenate([rng.normal(0.0, 1.0, 40), rng.normal(2.0, 1.0, 40)])

    delta, lo, hi = paired_auc_delta_ci(scores, scores, labels, n_boot=300, seed=0)

    assert delta == pytest.approx(0.0)
    assert lo <= 0.0 <= hi
