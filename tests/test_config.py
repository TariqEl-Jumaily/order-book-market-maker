from pathlib import Path

import pytest

from lobmm.config import SimulationConfig


def test_loads_committed_baseline() -> None:
    config = SimulationConfig.from_toml(Path("configs/baseline.toml"))
    assert config.initial_mid_ticks == 10_000
    assert config.markout_horizons == (1.0, 5.0, 10.0, 30.0, 60.0)


def test_updates_are_immutable() -> None:
    original = SimulationConfig()
    changed = original.with_updates(inventory_aversion=0.4)
    assert original.inventory_aversion == 0.1
    assert changed.inventory_aversion == 0.4


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_events", 0),
        ("market_order_rate", 0.0),
        ("informed_fraction", 1.1),
        ("inventory_aversion", -0.1),
        ("markout_horizons", ()),
    ],
)
def test_rejects_invalid_values(field: str, value: object) -> None:
    with pytest.raises(ValueError):
        SimulationConfig(**{field: value})  # type: ignore[arg-type]
