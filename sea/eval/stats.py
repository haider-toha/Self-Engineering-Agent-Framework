"""Statistics for the false-admission experiments.

Everything here is a pure function over observed outcomes. No LLM, no I/O.
Hand-rolled rather than pulling in scikit-learn: AUC is a rank statistic and
the bootstrap is a resample, both a few lines, and the dependency is not worth
it for a package a reviewer has to install.

Definitions (these are the paper's definitions -- keep them honest):

    ADMITTED       a candidate that passed its admitting suite.
    FALSE ADMISSION  an admitted candidate that fails the independent oracle.
    FAR            P(fails independent oracle | admitted)
                   = n_false_admissions / n_admitted

FAR is *conditional on admission*. It is not the error rate over all
candidates. That conditioning is the entire point: it is the quantity a
library owner actually experiences, and the quantity nobody reports.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = [
    "AUCResult",
    "ProportionResult",
    "auc",
    "auc_with_ci",
    "bootstrap_ci",
    "far",
    "wilson_ci",
]


@dataclass(frozen=True)
class ProportionResult:
    """A proportion with a confidence interval."""

    value: float
    lo: float
    hi: float
    numerator: int
    denominator: int

    def __str__(self) -> str:
        if self.denominator == 0:
            return "n/a (no admissions)"
        return (
            f"{self.value:.1%} [{self.lo:.1%}, {self.hi:.1%}] "
            f"({self.numerator}/{self.denominator})"
        )


@dataclass(frozen=True)
class AUCResult:
    """AUC with a bootstrap CI."""

    value: float
    lo: float
    hi: float
    n_pos: int
    n_neg: int

    def __str__(self) -> str:
        return (
            f"AUC={self.value:.3f} [{self.lo:.3f}, {self.hi:.3f}] "
            f"(pos={self.n_pos}, neg={self.n_neg})"
        )


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Chosen over the normal approximation because FAR can land near 0 or 1 with
    modest n, where the Wald interval famously misbehaves (and can escape
    [0, 1]).
    """
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def far(weak_pass: list[bool], strong_pass: list[bool]) -> ProportionResult:
    """False Admission Rate: P(fails strong oracle | passed weak oracle).

    Candidates that never passed the weak oracle were never admitted and are
    excluded from the denominator -- that is what makes this a *conditional*.
    """
    if len(weak_pass) != len(strong_pass):
        raise ValueError("weak_pass and strong_pass must be the same length")

    admitted = [s for w, s in zip(weak_pass, strong_pass) if w]
    n = len(admitted)
    k = sum(1 for s in admitted if not s)  # admitted but wrong
    lo, hi = wilson_ci(k, n)
    return ProportionResult(
        value=(k / n if n else 0.0), lo=lo, hi=hi, numerator=k, denominator=n
    )


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Area under the ROC curve, via the Mann-Whitney U identity.

    `labels` is 1 for the positive class. AUC is the probability that a
    randomly chosen positive is ranked above a randomly chosen negative, with
    ties counted as half. Returns 0.5 (chance) when either class is empty --
    an undefined AUC must not masquerade as a signal.
    """
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels).astype(int)
    pos, neg = scores[labels == 1], scores[labels == 0]
    if pos.size == 0 or neg.size == 0:
        return 0.5

    ranks = _rankdata(np.concatenate([pos, neg]))
    r_pos = ranks[: pos.size].sum()
    u = r_pos - pos.size * (pos.size + 1) / 2.0
    return float(u / (pos.size * neg.size))


def _rankdata(a: np.ndarray) -> np.ndarray:
    """Average ranks, 1-based, ties averaged (as Mann-Whitney requires)."""
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(1, len(a) + 1, dtype=float)

    sorted_a = a[order]
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and sorted_a[j + 1] == sorted_a[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = ranks[order[i : j + 1]].mean()
        i = j + 1
    return ranks


def bootstrap_ci(
    fn,
    *arrays: np.ndarray,
    n_boot: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Percentile bootstrap CI for a statistic over paired arrays."""
    rng = np.random.default_rng(seed)
    n = len(arrays[0])
    if n == 0:
        return (0.0, 0.0)
    vals = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        vals[b] = fn(*[np.asarray(a)[idx] for a in arrays])
    return (
        float(np.quantile(vals, alpha / 2)),
        float(np.quantile(vals, 1 - alpha / 2)),
    )


def auc_with_ci(
    scores: np.ndarray, labels: np.ndarray, *, n_boot: int = 2000, seed: int = 0
) -> AUCResult:
    lo, hi = bootstrap_ci(auc, scores, labels, n_boot=n_boot, seed=seed)
    labels_arr = np.asarray(labels).astype(int)
    return AUCResult(
        value=auc(scores, labels),
        lo=lo,
        hi=hi,
        n_pos=int((labels_arr == 1).sum()),
        n_neg=int((labels_arr == 0).sum()),
    )


def paired_auc_delta_ci(
    score_a: np.ndarray,
    score_b: np.ndarray,
    labels: np.ndarray,
    *,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """CI on AUC(a) - AUC(b), resampling *cases* (so the two are paired).

    This is how H2 is adjudicated: mutation score must beat the naive
    predictor by a margin whose CI excludes zero. Testing each AUC against
    0.5 separately would not establish that one is better than the other.
    """

    def delta(sa: np.ndarray, sb: np.ndarray, lb: np.ndarray) -> float:
        return auc(sa, lb) - auc(sb, lb)

    lo, hi = bootstrap_ci(
        delta, score_a, score_b, labels, n_boot=n_boot, seed=seed
    )
    return (delta(np.asarray(score_a), np.asarray(score_b), np.asarray(labels)), lo, hi)
