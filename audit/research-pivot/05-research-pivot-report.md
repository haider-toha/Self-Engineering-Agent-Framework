# Research Pivot — Consolidated Report

**From:** a half-finished e-commerce demo making 17 false claims
**To:** a small, honest research instrument that produced one strong positive result and one clean negative one
**Branch:** `research-pivot` · **Date:** 2026-07-13

*Written for a skeptical researcher. Five questions, answered in order: what is novel, what was cut, how to run it, how to evaluate it, what could still be wrong.*

---

## 1. What is novel

**The measured claim:**

```
FAR = P( tool is wrong │ it passed its own tests and was admitted to the library )
    = 54.5%   95% CI [47.9%, 60.9%]   (122 / 224)
```

Agents that synthesize their own tools — Voyager, CREATOR, LATM, TroVE, CRAFT — all admit on a **self-consistent oracle**: the same LLM writes the code and the tests, and the tool joins the library if its own tests pass. Konstantinou et al. ([2410.21136](https://arxiv.org/pdf/2410.21136)) established the mechanism: such tests encode *what the code does*, not *what the task requires*.

**What is genuinely ours — stated narrowly:**

1. **The admission-conditioned rate.** [EvolveTool-Bench](https://arxiv.org/abs/2604.00392) (April 2026) already reported the *observation* — 96.8% of 222 synthesized tools fail held-out conformance. That kills any claim to discovering the gap, and **we cite it in the first paragraph of the README.** What nobody reported is the **conditional**: `P(wrong | admitted)`. That is the number a library owner actually experiences, and it is 54.5%.

2. **A mechanistic negative result that rules out the obvious fix.** Mutation adequacy is *the* test-quality metric the field reaches for (VALTEST, mutation-guided test generation). We tried it as an admission gate. **It does not work, and we can say exactly why** (§4). Knowing the cheap fix fails — and the reason — is worth more than not knowing.

3. **A reproducible, CPU-only, zero-API-key harness.** ~20 minutes on a laptop. A reviewer can rerun every number in this report without spending a cent.

**The delta in one sentence:** *prior work observes that self-verified tool libraries are unreliable; we quantify the unreliability conditional on admission, and we show that the natural test-adequacy fix does not close it.*

---

## 2. What was cut

**11,923 lines of Python → 0, then rebuilt to ~2,900.**

The autopsy ([`01-track-2`](01-track-2-codebase-autopsy.md)) graded the old README's claims **3 TRUE / 4 PARTIAL / 17 FALSE**. The three findings that forced a total rewrite rather than a refactor:

| Finding | Evidence |
|---|---|
| **The sandbox was a decoy.** Untrusted LLM code executed **on the host** every time a tool ran. | `executor.py:70-82` — `spec.loader.exec_module(module)`. Docker was touched only during synthesis-time verification. |
| **The TDD claim was falsified by its own source.** On test failure the engine **rewrote the failing tests** until they passed; if they still failed it registered the tool anyway as "experimental" — and then executed it on the host. | `synthesis_engine.py:332` (`_apply_aggressive_test_fixes`), `:342-352`, `orchestrator.py:326-338` |
| **The "learning" was theatre.** The auto-tuner scored candidates by distance to a hardcoded `optimal = 0.45`, then wrote 0.45 back to the policy store as a discovered optimum. | `auto_tuner.py:150-174`; same pattern with a hardcoded ideal `[0.65, 0.25, 0.1]` for re-ranking weights |

Also deleted: Supabase (its migration had **no pgvector and zero of the six SQL functions Python called** — retrieval provably could not execute), the Flask/SocketIO UI (`cors_allowed_origins="*"` + hardcoded secret, on a service that ran generated code on the host), the skill graph (**zero callers**), the reflection engine (`apply_fix()` never invoked at runtime), the composite synthesizer, the query planner, the pattern miner, the e-commerce CSV demo, 5,700 lines of docs for a deleted API, and an "evaluation" suite of 2,823 lines containing **zero `assert` statements** — whose learning test used `>=` so it passed when nothing was learned.

Every deletion is justified with a 3-option decision in [`02-thesis-and-architecture.md`](02-thesis-and-architecture.md) §5.

**The cut is real:** `git ls-files` shows no `src/`, `web/`, or `evaluation/`; `grep` finds no zombie imports; `requirements.txt` went from 9 entries (5 of them missing packages the code imported, 6 of them unused) to 4 that match actual imports.

---

## 3. How to run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt

PYTHONPATH=. .venv/bin/python -m sea exp-a      # FAR + suite-level gate   (~20 min)
PYTHONPATH=. .venv/bin/python -m sea exp-a2     # per-tool gate            (~25 min)
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q          # 272 passed
```

**No API key required.** Installs clean in a fresh venv (4 dependencies). Results → `results/*.json`, committed as evidence.

**Byte-reproducible**, verified not assumed: two independent runs at `--seed 0` produce identical JSON (`diff` is silent). You are entitled to check my numbers without re-deriving them.

The LLM arm (`exp-b`) is implemented and tested but **was never executed** — no key was available in this environment. **No LLM-arm number appears anywhere in this repository, because none was produced.**

---

## 4. How to evaluate it

### The instrument

The whole design rests on one requirement: **an oracle independent of the LLM**, so that "verified" can be checked against something that cannot be gamed. MBPP+ supplies it:

- **WEAK oracle** = `base_input`, the **3** assertions from original MBPP. Stands in for a self-generated suite. *MBPP's prompt literally embeds these 3 assertions*, so an LLM writing tests from the prompt reproduces a suite of about this strength — which is what makes the LLM-free proxy faithful.
- **STRONG oracle** = `base_input + plus_input`, **~111** inputs (EvalPlus's 35× augmentation), authored independently of any LLM. **Ground truth.**

> **FALSE ADMISSION := passes the 3, fails the 111.**

Candidates are mutants of the human canonical solution. Nothing self-reports: every candidate runs **side-by-side with the canonical solution** on the same deep-copied inputs.

**Non-circularity.** Each task's mutants are split **disjointly and deterministically** into an *adequacy set* (which scores the suite) and a held-out *candidate set* (the tools seeking admission). H2's prediction is therefore out-of-sample. Without this split the correlation would be mechanical and meaningless.

**Apparatus validation.** The canonical solution must pass **both** oracles on every task used; any task where it doesn't is excluded and reported. Asserted in `tests/test_oracle.py`. If that test ever fails, every number here is garbage — and we would know.

### Results

| Hypothesis (pre-registered, [§3.3](02-thesis-and-architecture.md)) | Verdict |
|---|---|
| **H1** — FAR ≥ 15% | ✅ **SUPPORTED.** 54.5% [47.9%, 60.9%] |
| **H2** — mutation adequacy predicts false admission | ❌ **REFUTED.** AUC 0.578 vs. 0.519 baseline; Δ = +0.060 **[−0.042, +0.160]** |
| **H3** — gating on it halves FAR at ≥50% coverage | ❌ **REFUTED.** Best τ=0.7 → FAR 48.9% at 60% coverage |

Only **15.7%** of mutants survive the 3-assertion oracle — those assertions are not useless. But **54.5% of what they admit is wrong.**

I first tested H3 with a *suite-level* gate, which is a straw man of my own thesis (it can only discriminate between tasks, never between tools within one). So I built the **per-tool** gate — the faithful analogue of what `sea/agent.py` does in the LLM arm. **It is the stronger test, and it is the one that killed H2 and H3.**

### Why the intervention fails — and why that is the most useful thing here

> ### Mutation adequacy measures suite↔**implementation** coupling. False admission is a failure of suite↔**specification** coupling.

Mutation score asks: *"if I perturb this implementation, does the suite notice?"* It is computed **against the implementation**. But a falsely-admitted tool is not wrong because its code drifted from its tests — it is wrong because **the code and the tests were co-generated from the same misunderstanding of the task.** They agree with each other perfectly. They are wrong *together*.

Tightly pinning down a wrong behaviour therefore earns a **high** mutation score. The metric rewards precisely the pathology it was recruited to detect.

The decisive numbers:

```
mean adequacy │ tool is CORRECT : 0.736  (n=102)
mean adequacy │ tool is WRONG   : 0.696  (n=122)     separation: +0.040

Tools whose OWN suite kills 100% of mutants of their OWN impl:   8
...and are STILL WRONG:                                        3/8 = 38%
```

This is Konstantinou et al. ([2410.21136](https://arxiv.org/pdf/2410.21136)) — *tests capture what the code does, not what it should do* — made quantitative: **the tighter that capture, the better the mutation score, and the more confidently wrong the library becomes.**

*(Honesty note: my first explanation was that the metric "saturates." That holds for the suite-level score — median 1.00 — and is **false** for the per-tool score, where only 3.6% are at the ceiling and the median is 0.75. The tidy story did not survive contact with the per-tool distribution, and was replaced rather than kept.)*

**The generalisation, which is larger than my own hypothesis:** *any* adequacy metric computed against the implementation is structurally incapable of detecting false admission — mutation score, branch coverage, line coverage, path coverage. They all audit the suite against the code, and **the code is the thing that is wrong.** You cannot audit a witness using only the witness's own testimony.

The corollary is a positive direction, and it is why this null is worth reporting: **a working gate must import information from outside the co-generated pair** — property-based invariants, metamorphic relations, independently-authored adversarial suites, or differential testing against a second model. All untested here. **Not claimed here.**

---

## 5. Residual risks

Ordered by how much they should worry you.

1. **Mutants are not LLM-written code.** *The* threat. Their fault distribution is operator-shaped, not model-shaped. Experiment A establishes the **mechanism** and validates the **instrument**; it does not substitute for the LLM arm.
   *Convergent evidence for H1:* EvalPlus reports top models losing **19–29 points** of pass rate under the augmented tests — that is `P(fail strong | pass weak)` for real LLM code, comfortably above the 15% bar. **We cite this. We do not claim it as our result.**
2. **Experiment B was never run.** No key. In the LLM arm, **H2/H3 are UNTESTED, not refuted.** The saturation argument predicts adequacy will not help much there either — but that is a *prediction*, not a result.
3. **204 of 378 tasks (54%) excluded** — MBPP canonical solutions are often too short to yield the ≥6 mutants a disjoint split needs. This skews the sample toward longer functions, which plausibly have more room for undetected faults; FAR on the excluded short tasks is likely **lower**. Read 54.5% as applying to the retained subpopulation.
4. **Isolation is a safety boundary, not a security boundary** (ADR-002). Generated code runs in a subprocess with rlimits. On macOS `RLIMIT_AS` is **not enforced** — measured, not assumed. Run the harness in a container if you don't trust the prompts. **We claim no security property.**
5. **Single benchmark, single language, single fault generator.** MBPP+, Python, our 7 operators. A different operator set gives a different FAR; the direction and magnitude are robust, the exact figure is not.
6. **Equivalent mutants undetected** (undecidable in general) — they inflate the "true admission" bucket, making FAR if anything a *conservative* estimate. Same for MBPP contamination, which biases the LLM-arm FAR downward.

---

## 6. Audit trail

| File | Contents |
|---|---|
| [`01-track-1-landscape-and-gap.md`](01-track-1-landscape-and-gap.md) | Literature map; overlap with Voyager/CREATOR/LATM/TroVE; ranked theses and domains; what we will not claim |
| [`01-track-2-codebase-autopsy.md`](01-track-2-codebase-autopsy.md) | File-level keep/cut/rewrite table; fake-learning inventory; README claim audit (3 TRUE / 4 PARTIAL / **17 FALSE**); security reality |
| [`02-thesis-and-architecture.md`](02-thesis-and-architecture.md) | Locked thesis, pre-registered kill conditions, 3-option decisions (D1–D5), delete-list, **ADR-004 recording the thesis's own refutation** |
| [`03-track-implementation.md`](03-track-implementation.md) | What was deleted and built; root-cause fixes; grounding notes (`gpt-4` shutdown, reasoning-model temperature constraint) |
| [`04-eval-and-iteration.md`](04-eval-and-iteration.md) | Baseline → failures → fixes → final numbers; threats to validity; iteration log |

The sections of `02` above the amendment are left **exactly as written before the experiments ran**. Pre-registration is only worth something if the kill conditions are not quietly edited once they fire.

---

## 7. The one rule

> ### 🔒 Generated tests are immutable.
> Repair may rewrite the **implementation**. Never the tests. `synthesis.py` pins the suite with a SHA-256 and asserts it never changes; the invariant is enforced structurally, not by convention.
>
> The system this replaced had a method that rewrote failing tests until they passed, then registered the tool anyway if they didn't.
>
> **A synthesis failure rate is a result. A zero failure rate obtained by editing the oracle is a fabrication.**

That rule is why the 54.5% is worth reading — and it is why H2 and H3 were allowed to die.
