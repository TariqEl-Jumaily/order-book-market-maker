"""Command-line interface for simulations and experiments."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from .config import SimulationConfig
from .experiments import generate_report, run_parameter_sweep, save_simulation, save_sweep
from .simulation import Simulator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lobmm", description="Limit-order-book market-making simulator"
    )
    parser.add_argument("--config", default="configs/baseline.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser("simulate", help="run one seeded session")
    simulate.add_argument("--seed", type=int, default=42)
    simulate.add_argument("--events", type=int)
    simulate.add_argument("--output", default="results/raw/baseline-seed-42")

    for name in ("spread-sweep", "gamma-sweep", "report"):
        command = subparsers.add_parser(name)
        command.add_argument("--runs", type=int, default=200)
        command.add_argument("--events", type=int)
        command.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
        command.add_argument("--output", default="results")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = SimulationConfig.from_toml(args.config)
    if getattr(args, "events", None) is not None:
        config = config.with_updates(session_events=args.events)

    if args.command == "simulate":
        result = Simulator(config).run(args.seed)
        save_simulation(result, args.output)
        print(json.dumps(result.summary_dict(), indent=2, sort_keys=True))
        return 0

    seeds = tuple(range(args.runs))
    output = Path(args.output)
    if args.command == "spread-sweep":
        rows = run_parameter_sweep(
            config,
            "half_spread_ticks",
            (1, 2, 3, 4, 5),
            seeds,
            workers=args.workers,
        )
        path = save_sweep(rows, output / "raw" / "spread-sweep.csv")
        print(path)
        return 0
    if args.command == "gamma-sweep":
        rows = run_parameter_sweep(
            config,
            "inventory_aversion",
            (0.0, 0.025, 0.05, 0.1, 0.2, 0.4),
            seeds,
            workers=args.workers,
        )
        path = save_sweep(rows, output / "raw" / "gamma-sweep.csv")
        print(path)
        return 0
    report = generate_report(config, runs=args.runs, workers=args.workers, output_dir=output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
