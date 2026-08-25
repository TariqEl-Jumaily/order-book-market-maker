from lobmm.config import SimulationConfig
from lobmm.simulation import Simulator


def test_seeded_runs_are_deterministic_and_reconcile() -> None:
    config = SimulationConfig(session_events=500)
    first = Simulator(config).run(7)
    second = Simulator(config).run(7)
    assert first.events == second.events
    assert first.fills == second.fills
    assert first.states == second.states
    assert abs(first.pnl.reconciliation_error) <= 1e-9


def test_calibrated_market_remains_populated_and_inventory_bounded() -> None:
    config = SimulationConfig(session_events=2_000)
    result = Simulator(config).run(11)
    assert result.diagnostics.nonempty_fraction >= 0.99
    assert 1 <= (result.diagnostics.median_spread or 0) <= 3
    assert 5 <= result.diagnostics.mean_bid_levels <= 15
    assert 5 <= result.diagnostics.mean_ask_levels <= 15
    assert result.max_absolute_inventory <= config.inventory_limit
    assert result.fills
    assert result.depth_profile


def test_zero_inventory_aversion_is_valid_baseline() -> None:
    result = Simulator(
        SimulationConfig(session_events=300, inventory_aversion=0.0)
    ).run(3)
    assert result.config.inventory_aversion == 0
    assert result.summary_dict()["seed"] == 3

