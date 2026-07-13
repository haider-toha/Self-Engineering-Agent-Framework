# Phase 4 — Evaluation and Iteration

**Scope:** Build a research-honest eval; run it; report what happened, including what failed.
**Date:** 2026-07-13
**Reproduce:** `PYTHONPATH=. .venv/bin/python -m sea exp-a` and `... exp-a2` (~20 min, CPU only, **no API key needed**).

---

## 0. Headline

| Hypothesis (pre-registered in Phase 2) | Verdict |
|---|---|
| **H1** — FAR ≥ 15% | ✅ **SUPPORTED, strongly.** FAR = **54.5%** [47.9%, 60.9%] |
| **H2** — mutation adequacy predicts false admission, beating naive baselines | ❌ **NOT SUPPORTED.** AUC 0.578 vs. 0.519 baseline; Δ = +0.060 **[−0.042, +0.160]** — CI includes 0 |
| **H3** — gating on adequacy halves FAR at ≥50% coverage | ❌ **NOT SUPPORTED.** Best: τ=0.7 → FAR 48.9% at 60% coverage (a 10% reduction, not 50%) |

**Two of my three hypotheses are dead.** Phase 2 wrote the kill conditions in advance precisely so this could not be renegotiated after the fact, and they fired. The intervention I proposed does not work. Section 4 explains *why*, mechanistically — and that mechanism is the most useful thing this project produced.

---

## 1. The measurement instrument

The apparatus never trusts a candidate to self-report. For every task it runs the candidate **and** the human canonical solution side by side, in one sandboxed subprocess, on the same deep-copied inputs, and compares outputs (with `atol` for floats). Two oracles:

- **WEAK** — `base_input`: the 3 assertions shipped with the original MBPP. Stands in for a self-consistent admission suite. *MBPP's natural-language prompt literally embeds these 3 assertions*, so an LLM writing tests from the prompt tends to reproduce a suite of about this strength.
- **STRONG** — `base_input + plus_input`: ~111 inputs (EvalPlus's 35× augmentation), authored independently of any LLM. **Ground truth.**

> **FALSE ADMISSION := passes WEAK, fails STRONG.** The library accepted a tool whose contract is wrong.

**Apparatus validation (the test that gates everything else):** the canonical solution must pass both oracles on every task used. Any task where it does not is a data-quality defect and is **excluded and reported**, never silently kept. This is asserted in `tests/test_oracle.py` — if it ever fails, every number below is garbage and we would know.

### Avoiding circularity

Both the adequacy signal and the candidate implementations are drawn from the same mutant population. Scoring a suite's adequacy on the very mutants it is then asked to admit would make the correlation mechanical and meaningless. So, per task, mutants are split **disjointly and deterministically**:

- **ADEQUACY SET** — used *only* to measure the suite's mutation score.
- **CANDIDATE SET** — used *only* as the tools seeking admission. Held out.

The prediction tested in H2 is therefore genuinely out-of-sample. A train/test split.

---

## 2. Baseline: H1 — the gap is real, and it is large

**Experiment A** (`sea/eval/experiment_a.py`), all 378 MBPP+ tasks, seed 0:

```
tasks used: 174/378 (204 skipped)
candidates: 1431   admitted: 224   false admissions: 122

FAR = 54.5%   95% CI [47.9%, 60.9%]   (122/224)
```

Only **15.7%** of mutants survive the 3-assertion oracle at all — those assertions are not useless. But **of the tools they do admit, 54.5% are wrong.** The remaining 45.5% are equivalent or otherwise-undetectable mutants (semantically identical to canonical, or differing only outside all 111 inputs).

Which faults slip through is itself informative:

| operator | admitted | false | FAR |
|---|---|---|---|
| **CRP** (constant replacement — off-by-one) | 94 | **57** | **61%** |
| SDL (statement deletion) | 52 | 25 | 48% |
| ROR (relational operator) | 34 | 15 | 44% |
| AOR (arithmetic operator) | 24 | 10 | 42% |
| RVR (`return None`) | 15 | 12 | 80% |
| COR / UOI | 5 | 3 | — |

**CRP alone accounts for 57 of the 122 false admissions.** Off-by-one constants are exactly the subtle faults that three hand-picked assertions do not probe. This is the shape of the problem.

**H1 is supported with a wide margin** (54.5% vs. a 15% bar; the CI's lower bound of 47.9% is >3× the bar). It is also the first *admission-conditioned* FAR reported: EvolveTool-Bench measured unconditional per-tool correctness; this is `P(wrong | admitted)`, which is what a library owner actually experiences.

---

## 3. The intervention fails: H2 and H3

### 3.1 First attempt, and a flaw in my own test

Experiment A gates at the **suite** level: adequacy is a property of the (task, suite) pair, so every candidate for a task shares one score. That gate can only discriminate *between* tasks — it is structurally blind to the fact that within one task some admitted tools are equivalent mutants and others are genuinely wrong.

That is a handicapped version of the hypothesis. The thesis gates **per tool**. Testing the weaker form and reporting failure would have been a straw man of my own argument, so I built the faithful test.

### 3.2 The faithful test: the per-tool gate

**Experiment A2** (`sea/eval/per_tool.py`) reproduces exactly what `sea/agent.py` does in the LLM arm: take the admitted tool's *own* implementation, mutate **it**, and ask whether the tool's *own* admitting suite notices.

```
admitted tools: 224   false admissions: 122     FAR = 54.5% [47.9%, 60.9%]

H2  per-tool adequacy : AUC = 0.578 [0.503, 0.650]
    code-size baseline: AUC = 0.519 [0.454, 0.580]
    delta             : +0.060 [-0.042, +0.160]   -> NOT SUPPORTED

H3   tau   admitted     FAR   coverage   FAR reduction
     0.0        224   54.5%     100.0%           0.0%
     0.5        203   54.2%      90.6%           0.5%
     0.7        135   48.9%      60.3%          10.2%
     0.8         85   45.9%      37.9%          15.8%
     0.9         33   36.4%      14.7%          33.2%
     1.0          8   37.5%       3.6%          31.1%
```

**H2 fails.** Per-tool mutation adequacy reaches AUC 0.578 — above chance, but it does **not** significantly beat a naive code-size baseline (Δ = +0.060, CI **[−0.042, +0.160]**, straddling zero). A predictor that cannot beat "how big is the function" is not a predictor.

**H3 fails.** The gate never halves FAR at usable coverage. To get even a 33% FAR reduction you must throw away **85% of your library**.

---

## 4. Why it fails — the mechanism (the actual finding)

This is not an inexplicable null. But the obvious explanation is **wrong**, and it is worth recording that I nearly shipped it.

### 4.1 The explanation I first reached for — and why it does not hold

The *suite-level* score is saturated: median **1.00**, p25 = 0.80 across 174 tasks. Half the tasks kill every mutant and still admit wrong tools, and a metric at its ceiling for half the population cannot rank that population. Tidy.

**But it does not explain the per-tool result, which is the one that matters.** Per-tool adequacy has genuine dynamic range:

```
per-tool adequacy (224 admitted tools):
  min 0.30   p10 0.50   p25 0.60   MEDIAN 0.75   p75 0.81   p90 0.93   max 1.00
  fraction at ceiling (>= 0.999): 3.6%
```

Only **3.6%** sit at the ceiling. The predictor has room to discriminate — and it still doesn't. So saturation is a real property of the suite-level score and a **false explanation of the per-tool failure.** The tidy story was wrong.

### 4.2 The actual mechanism

Look at what the score does and does not separate:

```
mean adequacy │ tool is CORRECT : 0.736   (n = 102)
mean adequacy │ tool is WRONG   : 0.696   (n = 122)
separation                      : +0.040
```

```
FAR by per-tool adequacy:
  [0.2,0.4)    n=  7    71%
  [0.4,0.6)    n= 36    56%
  [0.6,0.8)    n= 96    60%
  [0.8,1.0)    n= 85    46%
```

Shallow and barely monotone. And the decisive observation:

> **Of the 8 tools whose own suite kills 100% of the mutants of their own implementation, 3 (38%) are still WRONG.**

A suite can pin its implementation down *perfectly* and the tool is still broken. That is not noise — it is the mechanism:

> ### Mutation adequacy measures suite↔**implementation** coupling. False admission is a failure of suite↔**specification** coupling.

Mutation score asks: *"if I perturb this implementation, does the suite notice?"* It is computed **against the implementation**. But a falsely-admitted tool is not wrong because its implementation drifted from its tests — it is wrong because **the implementation and the tests were co-generated from the same misunderstanding of the task.** They agree with each other perfectly. They are both wrong together.

Tightly pinning down a wrong behaviour earns a *high* mutation score. The metric rewards exactly the pathology it was recruited to detect. This is Konstantinou et al. ([2410.21136](https://arxiv.org/pdf/2410.21136)) — *tests capture what the code does, not what it should do* — made quantitative: the tighter that capture, the better the mutation score, and the more confidently wrong the library becomes.

### 4.3 What this rules out — and it is more than mutation score

Mutation adequacy is *the* obvious test-quality metric; it is what the literature reaches for (VALTEST, mutation-guided test generation) and it is what I reached for. It does not transfer to the admission decision.

But the mechanism generalises further than my own hypothesis did. **Any adequacy metric computed against the implementation is structurally incapable of detecting false admission** — mutation score, branch coverage, line coverage, path coverage. They all measure the suite against the code, and *the code is the thing that is wrong*. You cannot audit a witness using only the witness's own testimony.

The corollary is a positive direction, and it is the reason this null is worth publishing: **a working gate must import information from outside the co-generated pair.** Property-based invariants, metamorphic relations, independently-authored adversarial suites, differential testing against a second model — all of these are untested here, and all of them are *not* confined to the implementation-derived space that structurally defeats coverage-style metrics. That is future work. It is **not claimed here.**

---

## 5. Test suite

```
$ PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
272 passed in 87s
```

Coverage of the real seams — sandbox (isolation, timeout, orphan-kill, env scrubbing), mutation (all 7 operators, determinism, the strong-vs-weak discrimination), registry (cosine ranking, empty DB, dim mismatch), config (fail-fast), llm (cache actually avoids the network), synthesis (**the immutability invariant**), agent (**the gate actually rejects, and nothing is registered when it does**), oracle (**a false admission is detectable by the instrument** — the test that proves the phenomenon is observable at all), stats (Wilson/AUC/bootstrap against hand-computed values), per_tool (the disjoint split reproduces Experiment A's exactly).

**No test asserts a mock's return value back at itself.** The suite this replaced had 2,823 LOC and *zero* `assert` statements, and its "learning" test used `>=` so it passed when nothing was learned.

### Reproducibility

Verified, not assumed: two independent runs at `--seed 0` produce **byte-identical** result JSON.

```
$ python -m sea exp-a --limit 60 --seed 0 --out /tmp/r1
$ python -m sea exp-a --limit 60 --seed 0 --out /tmp/r2
$ diff /tmp/r1/experiment_a.json /tmp/r2/experiment_a.json   # silent
```

This required a fix: `as_completed` yields futures in completion order, so while the *statistics* were always order-invariant and identical, the serialized artefact was not. Results are now sorted by task id before writing. A reviewer is entitled to diff two runs and get silence.

### End-to-end check of the mechanism

The gate is not merely present, it *acts* — same implementation, opposite outcomes, attributable to the gate alone:

```
strong suite, gate ON  (tau=.8)   decision=admitted           mutation=1.00   in_registry=1
weak suite,   gate ON  (tau=.8)   decision=rejected_by_gate   mutation=0.50   in_registry=0
weak suite,   gate OFF            decision=admitted           mutation=n/a    in_registry=1
```

This matters for the integrity of the negative result: **H2/H3 failed because the metric is the wrong signal, not because the gate is broken.** A broken gate would be a bug; a working gate that does not help is a finding.

---

## 6. Threats to validity — stated plainly

1. **Mutants are not LLM-written code.** This is the biggest one. Their error distribution is operator-shaped (off-by-one, flipped comparison, deleted branch), not model-shaped. Experiment A establishes the *mechanism* and validates the *instrument*; it is **not** a substitute for the LLM arm.
   *Convergent evidence that H1 generalises:* EvalPlus's own published result is that top models lose **19–29 points** of apparent pass rate under the augmented tests — which is `P(fail strong | pass weak)` for real LLM code, i.e. an LLM-arm FAR comfortably above the 15% bar. Consistent with H1. **We cite this; we do not claim it as our result.**
2. **204 of 378 tasks (54%) were excluded.** Cause: MBPP canonical solutions are short, so many yield fewer than the 6 mutants needed for a meaningful disjoint split. This biases the sample toward *longer* functions. Longer functions plausibly have *more* room for undetected faults, so **FAR on the excluded short tasks is likely lower** and the 54.5% figure should be read as applying to the retained (longer-function) subpopulation, not to all of MBPP+.
3. **Experiment B was never run.** No API key was available. The code path is complete and tested at the `FakeLLM` seam, but **zero LLM-arm numbers are reported, because none were produced.** No estimates, no extrapolations, no "expected" figures.
4. **Single benchmark, single language.** MBPP+, Python. HumanEval+ is wired but unrun.
5. **Equivalent mutants are undetected** (undecidable in general). They inflate the "true admission" bucket and thus, if anything, make FAR a *conservative* estimate.
6. **Benchmark contamination.** Models may have memorised MBPP. This inflates base pass rate, which biases the LLM-arm FAR *downward* — again conservative for H1.

---

## 7. Iteration log

| # | Problem | Root cause | Fix |
|---|---|---|---|
| 1 | Smoke test: **zero** mutants admitted; FAR undefined | Small-sample artefact. 3 tiny tasks, ≤8 mutants each, and the operators that fired were coarse (`SDL`, `RVR`) — obliterating faults that even 3 assertions catch. | Measured at scale instead of guessing. At 80 tasks / 816 mutants, 14.6% survive and FAR = 42.9%. The phenomenon was always there; the sample wasn't. |
| 2 | `ProcessPoolExecutor` → `BrokenProcessPool` | Python 3.14 uses `spawn` on macOS and re-imports `__main__`; a heredoc script has no importable `__main__`. | Real modules + `__main__` guard in the CLI. |
| 3 | H3 tested at the **suite** level — a straw man of my own thesis | Adequacy was a per-*task* property, so the gate could not discriminate *within* a task. | Built `per_tool.py` (Experiment A2), the faithful per-tool gate. It is the test that ultimately killed H2 and H3 — the *stronger* test, not the weaker one. |
| 4 | H2/H3 null — is it a bug or a finding? | Investigated rather than accepted. Adequacy distribution: **median 1.00**. The metric is saturated. | Reported as a mechanistic negative result (§4), not an unexplained null. |

---

## 8. Residual risk

- The negative result for H2/H3 is established **only in the LLM-free proxy**. It is possible that in the LLM arm, where suite *size and quality genuinely vary* (a model may write 3 tests or 12), adequacy has more dynamic range and more signal. The saturation argument predicts it will not help much — but **this is a prediction, not a result**, and the honest status of H2/H3 in the LLM arm is **UNTESTED**, not "refuted".
- FAR is measured on a fault population we generated. A different operator set would give a different FAR. The *direction and magnitude* are robust (15.7% survival, 54.5% conditional failure); the exact figure is operator-dependent, and we do not claim otherwise.
