import csv
import json
from pathlib import Path

import pytest

from lobmm.config import SimulationConfig
from lobmm.experiments import (
    generate_report,
    run_parameter_sweep,
    save_simulation,
    save_sweep,
    summarize_metric,
)
from lobmm.simulation import Simulator


def test_sweep_uses_common_seeds_and_aggregates() -> None:
    config = SimulationConfig(session_events=100)
    rows = run_parameter_sweep(
        config, "inventory_aversion", (0.0, 0.1), (2, 1), workers=1
    )
    assert [(row.setting, row.seed) for row in rows] == [
        (0.0, 1),
        (0.0, 2),
        (0.1, 1),
        (0.1, 2),
    ]
    summary = summarize_metric(rows, "total_pnl")
    assert [row.count for row in summary] == [2, 2]


def test_sweep_validation() -> None:
    config = SimulationConfig(session_events=10)
    with pytest.raises(ValueError):
        run_parameter_sweep(config, "inventory_aversion", (), (1,))
    with pytest.raises(ValueError):
        run_parameter_sweep(config, "inventory_aversion", (0.1,), (1,), workers=0)


def test_persistence_and_small_report(tmp_path: Path) -> None:
    config = SimulationConfig(session_events=300)
    result = Simulator(config).run(42)
    saved = save_simulation(result, tmp_path / "single")
    assert json.loads((saved / "summary.json").read_text())["seed"] == 42
    assert list(csv.DictReader((saved / "states.csv").open()))

    rows = run_parameter_sweep(config, "half_spread_ticks", (1,), (0,), workers=1)
    sweep_path = save_sweep(rows, tmp_path / "sweep.csv")
    assert sweep_path.exists()

    report = generate_report(config, runs=2, workers=1, output_dir=tmp_path / "report")
    assert report["runs_per_setting"] == 2
    figures = sorted((tmp_path / "report" / "figures").glob("*.png"))
    assert len(figures) == 7
    assert all(path.stat().st_size > 0 for path in figures)

