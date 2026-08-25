"""Reproducible parameter sweeps, persistence, and report figures."""

from __future__ import annotations

import csv
import json
import os
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .analytics import bootstrap_confidence_interval
from .config import SimulationConfig
from .simulation import SimulationResult, Simulator

SweepParameter = Literal["half_spread_ticks", "inventory_aversion"]


@dataclass(frozen=True, slots=True)
class ExperimentObservation:
    parameter: str
    setting: float
    seed: int
    total_pnl: float
    spread_capture: float
    inventory_pnl: float
    fill_count: int
    max_absolute_inventory: int


@dataclass(frozen=True, slots=True)
class MetricSummary:
    setting: float
    count: int
    mean: float
    standard_deviation: float
    ci_low: float
    ci_high: float


def _config_from_dict(values: dict[str, Any]) -> SimulationConfig:
    values = dict(values)
    values["markout_horizons"] = tuple(values["markout_horizons"])
    return SimulationConfig(**values)


def _run_task(task: tuple[dict[str, Any], int, str, float]) -> ExperimentObservation:
    config_values, seed, parameter, setting = task
    result = Simulator(_config_from_dict(config_values)).run(seed)
    return ExperimentObservation(
        parameter=parameter,
        setting=setting,
        seed=seed,
        total_pnl=result.pnl.total_pnl,
        spread_capture=result.pnl.spread_capture,
        inventory_pnl=result.pnl.inventory_pnl,
        fill_count=len(result.fills),
        max_absolute_inventory=result.max_absolute_inventory,
    )


def run_parameter_sweep(
    config: SimulationConfig,
    parameter: SweepParameter,
    settings: Sequence[float],
    seeds: Sequence[int],
    *,
    workers: int = 1,
) -> tuple[ExperimentObservation, ...]:
    """Run settings with common random seeds and return deterministically ordered rows."""

    if parameter not in {"half_spread_ticks", "inventory_aversion"}:
        raise ValueError(f"unsupported sweep parameter: {parameter}")
    if not settings or not seeds:
        raise ValueError("settings and seeds cannot be empty")
    if workers <= 0:
        raise ValueError("workers must be positive")
    tasks: list[tuple[dict[str, Any], int, str, float]] = []
    for setting in settings:
        update: int | float = int(setting) if parameter == "half_spread_ticks" else setting
        configured = config.with_updates(**{parameter: update})
        tasks.extend(
            (configured.as_dict(), seed, parameter, float(setting)) for seed in seeds
        )
    if workers == 1:
        observations = [_run_task(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            observations = list(executor.map(_run_task, tasks, chunksize=max(1, len(tasks) // 100)))
    return tuple(sorted(observations, key=lambda row: (row.setting, row.seed)))


def summarize_metric(
    observations: Sequence[ExperimentObservation],
    metric: Literal[
        "total_pnl", "spread_capture", "inventory_pnl", "fill_count", "max_absolute_inventory"
    ],
    *,
    bootstrap_seed: int = 0,
) -> tuple[MetricSummary, ...]:
    grouped: dict[float, list[float]] = {}
    for row in observations:
        grouped.setdefault(row.setting, []).append(float(getattr(row, metric)))
    summaries: list[MetricSummary] = []
    for index, setting in enumerate(sorted(grouped)):
        values = grouped[setting]
        low, high = bootstrap_confidence_interval(values, seed=bootstrap_seed + index)
        summaries.append(
            MetricSummary(
                setting=setting,
                count=len(values),
                mean=fmean(values),
                standard_deviation=stdev(values) if len(values) > 1 else 0.0,
                ci_low=low,
                ci_high=high,
            )
        )
    return tuple(summaries)


def save_simulation(result: SimulationResult, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write_json(output / "summary.json", result.summary_dict())
    _write_json(output / "config.json", result.config_dict())
    _write_csv(output / "events.csv", [asdict(row) for row in result.events])
    _write_csv(output / "fills.csv", [asdict(row) for row in result.fills])
    _write_csv(output / "states.csv", [asdict(row) for row in result.states])
    _write_csv(
        output / "markouts.csv", [asdict(row) for row in result.markouts]
    )
    return output


def save_sweep(
    observations: Sequence[ExperimentObservation], output_path: str | Path
) -> Path:
    path = Path(output_path)
    _write_csv(path, [asdict(row) for row in observations])
    return path


def generate_report(
    config: SimulationConfig,
    *,
    runs: int = 200,
    workers: int | None = None,
    output_dir: str | Path = "results",
) -> dict[str, Any]:
    """Run the planned experiments and produce all seven headline figures."""

    if runs <= 0:
        raise ValueError("runs must be positive")
    worker_count = workers or max(1, (os.cpu_count() or 2) - 1)
    output = Path(output_dir)
    figures = output / "figures"
    raw = output / "raw"
    figures.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)

    baseline = Simulator(config).run(42)
    no_skew = Simulator(config.with_updates(inventory_aversion=0.0)).run(42)
    save_simulation(baseline, raw / "baseline-seed-42")
    seeds = tuple(range(runs))
    spread_rows = run_parameter_sweep(
        config, "half_spread_ticks", (1, 2, 3, 4, 5), seeds, workers=worker_count
    )
    gamma_rows = run_parameter_sweep(
        config,
        "inventory_aversion",
        (0.0, 0.025, 0.05, 0.1, 0.2, 0.4),
        seeds,
        workers=worker_count,
    )
    save_sweep(spread_rows, raw / "spread-sweep.csv")
    save_sweep(gamma_rows, raw / "gamma-sweep.csv")

    _plot_depth(baseline, figures / "01-depth-profile.png")
    _plot_mid_and_quotes(baseline, figures / "02-mid-and-quotes.png")
    _plot_spread_sweep(spread_rows, figures / "03-spread-sweep.png")
    _plot_gamma_sweep(gamma_rows, figures / "04-inventory-aversion.png")
    _plot_inventory(no_skew, baseline, figures / "05-inventory-distribution.png")
    _plot_markouts(baseline, figures / "06-markout-curves.png")
    _plot_pnl_decomposition(baseline, figures / "07-pnl-decomposition.png")

    report = {
        "runs_per_setting": runs,
        "baseline": baseline.summary_dict(),
        "spread_pnl": [asdict(row) for row in summarize_metric(spread_rows, "total_pnl")],
        "spread_fills": [asdict(row) for row in summarize_metric(spread_rows, "fill_count")],
        "gamma_pnl": [asdict(row) for row in summarize_metric(gamma_rows, "total_pnl")],
        "gamma_spread_capture": [
            asdict(row) for row in summarize_metric(gamma_rows, "spread_capture")
        ],
        "gamma_max_inventory": [
            asdict(row) for row in summarize_metric(gamma_rows, "max_absolute_inventory")
        ],
    }
    _write_json(output / "report-summary.json", report)
    return report


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _finish_figure(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def _plot_depth(result: SimulationResult, path: Path) -> None:
    distances = [row[0] for row in result.depth_profile]
    plt.figure(figsize=(8, 4.5))
    plt.plot(distances, [row[1] for row in result.depth_profile], label="Bid depth")
    plt.plot(distances, [row[2] for row in result.depth_profile], label="Ask depth")
    plt.xlabel("Distance from midpoint (ticks)")
    plt.ylabel("Average resting quantity")
    plt.title("Average order-book depth profile")
    plt.legend()
    _finish_figure(path)


def _plot_mid_and_quotes(result: SimulationResult, path: Path) -> None:
    sample = result.states[:: max(1, len(result.states) // 1_000)]
    times = [state.time for state in sample]
    plt.figure(figsize=(9, 4.5))
    plt.plot(times, [state.midpoint for state in sample], label="Midpoint", linewidth=1.5)
    plt.plot(
        times,
        [float("nan") if state.maker_bid is None else state.maker_bid for state in sample],
        label="MM bid",
        alpha=0.75,
    )
    plt.plot(
        times,
        [float("nan") if state.maker_ask is None else state.maker_ask for state in sample],
        label="MM ask",
        alpha=0.75,
    )
    plt.xlabel("Simulation time")
    plt.ylabel("Price (ticks)")
    plt.title("Midpoint and market-maker quotes")
    plt.legend()
    _finish_figure(path)


def _plot_spread_sweep(rows: Sequence[ExperimentObservation], path: Path) -> None:
    pnl = summarize_metric(rows, "total_pnl")
    fills = summarize_metric(rows, "fill_count")
    figure, left = plt.subplots(figsize=(8, 4.5))
    right = left.twinx()
    left.plot([x.setting for x in pnl], [x.mean for x in pnl], marker="o", color="#2563eb")
    right.plot(
        [x.setting for x in fills], [x.mean for x in fills], marker="s", color="#dc2626"
    )
    left.set_xlabel("Half-spread (ticks)")
    left.set_ylabel("Mean terminal PnL (ticks)", color="#2563eb")
    right.set_ylabel("Mean fill count", color="#dc2626")
    left.set_title("Spread width: edge per fill versus fill rate")
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _plot_gamma_sweep(rows: Sequence[ExperimentObservation], path: Path) -> None:
    pnl = summarize_metric(rows, "total_pnl")
    spread = summarize_metric(rows, "spread_capture")
    figure, left = plt.subplots(figsize=(8, 4.5))
    right = left.twinx()
    left.plot(
        [x.setting for x in pnl],
        [x.standard_deviation for x in pnl],
        marker="o",
        color="#7c3aed",
    )
    right.plot(
        [x.setting for x in spread], [x.mean for x in spread], marker="s", color="#059669"
    )
    left.set_xlabel("Inventory aversion gamma")
    left.set_ylabel("PnL standard deviation (ticks)", color="#7c3aed")
    right.set_ylabel("Mean gross spread capture (ticks)", color="#059669")
    left.set_title("Inventory-risk versus spread-capture trade-off")
    figure.tight_layout()
    figure.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def _plot_inventory(no_skew: SimulationResult, skew: SimulationResult, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    plt.hist(
        [state.inventory for state in no_skew.states], bins=25, alpha=0.6, label="gamma = 0"
    )
    plt.hist(
        [state.inventory for state in skew.states],
        bins=25,
        alpha=0.6,
        label=f"gamma = {skew.config.inventory_aversion:g}",
    )
    plt.xlabel("Inventory")
    plt.ylabel("Event observations")
    plt.title("Inventory distribution with and without skew")
    plt.legend()
    _finish_figure(path)


def _plot_markouts(result: SimulationResult, path: Path) -> None:
    plt.figure(figsize=(8, 4.5))
    for aggressor in ("informed", "uninformed"):
        rows = [row for row in result.markout_summary if row.aggressor_type == aggressor]
        plt.plot(
            [row.horizon for row in rows],
            [row.mean_ticks_per_unit for row in rows],
            marker="o",
            label=aggressor.title(),
        )
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xlabel("Post-fill horizon (simulation time)")
    plt.ylabel("Mean markout (ticks per unit)")
    plt.title("Adverse selection by aggressor type")
    plt.legend()
    _finish_figure(path)


def _plot_pnl_decomposition(result: SimulationResult, path: Path) -> None:
    fills_by_time: dict[float, list[Any]] = {}
    for fill in result.fills:
        fills_by_time.setdefault(fill.time, []).append(fill)
    times: list[float] = []
    spread_values: list[float] = []
    inventory_values: list[float] = []
    spread_pnl = 0.0
    inventory_pnl = 0.0
    previous_mid = result.states[0].midpoint
    for state in result.states[1:]:
        for fill in fills_by_time.get(state.time, []):
            spread_pnl += fill.signed_quantity * (fill.pre_event_mid - fill.price)
        inventory_pnl += state.inventory * (state.midpoint - previous_mid)
        previous_mid = state.midpoint
        times.append(state.time)
        spread_values.append(spread_pnl)
        inventory_values.append(inventory_pnl)
    plt.figure(figsize=(9, 4.5))
    plt.plot(times, spread_values, label="Spread capture", color="#2563eb")
    plt.plot(times, inventory_values, label="Inventory PnL", color="#f97316")
    plt.plot(
        times,
        [
            spread + inventory
            for spread, inventory in zip(spread_values, inventory_values, strict=True)
        ],
        color="black",
        linewidth=1,
        label="Total PnL",
    )
    plt.xlabel("Simulation time")
    plt.ylabel("Cumulative PnL (ticks)")
    plt.title("Cumulative PnL decomposition")
    plt.legend(loc="upper left")
    _finish_figure(path)
