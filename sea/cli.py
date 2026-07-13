"""Command-line interface. The only interface -- there is no web UI (ADR: D3).

    python -m sea exp-a              # LLM-free. No API key. Real numbers.
    python -m sea exp-b              # The LLM arm. Requires OPENAI_API_KEY.
    python -m sea run "<task>"       # One task through the full agent loop.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sea", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("exp-a", help="Experiment A (LLM-free weak-oracle study)")
    a.add_argument("--limit", type=int, default=None, help="first N tasks only")
    a.add_argument("--max-mutants", type=int, default=40)
    a.add_argument("--min-mutants", type=int, default=6)
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("--out", type=Path, default=Path("results"))

    a2 = sub.add_parser("exp-a2", help="Experiment A2 (LLM-free PER-TOOL gate)")
    a2.add_argument("--limit", type=int, default=None)
    a2.add_argument("--max-mutants", type=int, default=40)
    a2.add_argument("--min-mutants", type=int, default=6)
    a2.add_argument("--second-order", type=int, default=20)
    a2.add_argument("--workers", type=int, default=10)
    a2.add_argument("--seed", type=int, default=0)
    a2.add_argument("--out", type=Path, default=Path("results"))

    b = sub.add_parser("exp-b", help="Experiment B (LLM arm; needs OPENAI_API_KEY)")
    b.add_argument("--limit", type=int, default=None)
    b.add_argument("--max-repairs", type=int, default=3)
    b.add_argument("--max-mutants", type=int, default=30)
    b.add_argument("--seed", type=int, default=0)
    b.add_argument("--out", type=Path, default=Path("results"))

    r = sub.add_parser("run", help="Run one task through the agent loop")
    r.add_argument("task", help="natural-language task description")
    r.add_argument("--no-gate", action="store_true", help="disable the mutation gate")
    r.add_argument("--db", type=Path, default=Path("results/tools.sqlite"))

    args = p.parse_args(argv)

    if args.cmd == "exp-a":
        from sea.eval.experiment_a import run_experiment_a

        run_experiment_a(
            limit=args.limit,
            max_mutants=args.max_mutants,
            min_mutants=args.min_mutants,
            workers=args.workers,
            seed=args.seed,
            out_dir=args.out,
        )
        return 0

    if args.cmd == "exp-a2":
        from sea.eval.per_tool import run_per_tool_gate

        run_per_tool_gate(
            limit=args.limit, max_mutants=args.max_mutants,
            min_mutants=args.min_mutants, second_order=args.second_order,
            workers=args.workers, seed=args.seed, out_dir=args.out,
        )
        return 0

    if args.cmd == "exp-b":
        from sea.eval.experiment_b import run_experiment_b

        run_experiment_b(
            limit=args.limit,
            max_repairs=args.max_repairs,
            mutation_max=args.max_mutants,
            seed=args.seed,
            out_dir=args.out,
        )
        return 0

    if args.cmd == "run":
        from sea.agent import handle_task
        from sea.config import Config
        from sea.llm import OpenAIClient
        from sea.registry import Registry

        cfg = Config.from_env()
        args.db.parent.mkdir(parents=True, exist_ok=True)
        registry = Registry(args.db)
        out = handle_task(
            task_id="cli",
            task_prompt=args.task,
            llm=OpenAIClient(cfg),
            registry=registry,
            gate=not args.no_gate,
            tau=cfg.mutation_tau,
            retrieval_threshold=cfg.retrieval_threshold,
            mutation_max=cfg.mutation_max,
        )
        print(f"decision : {out.decision}")
        print(f"tool     : {out.tool_name}")
        if out.mutation:
            print(f"mutation : {out.mutation.score:.2f} "
                  f"({out.mutation.killed}/{out.mutation.total} killed)")
        if out.retrieval_score is not None:
            print(f"retrieval: {out.retrieval_score:.3f}")
        if out.error:
            print(f"error    : {out.error}")
        registry.close()
        return 0 if out.admitted else 1

    return 1


if __name__ == "__main__":
    # Guard required: ProcessPoolExecutor uses spawn on macOS/py3.14 and
    # re-imports __main__ in each child.
    sys.exit(main())
