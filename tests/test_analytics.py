from __future__ import annotations

import pytest

from lobmm.analytics import (
    FillRecord,
    StateRecord,
    SweepObservation,
    aggregate_sweep,
    bootstrap_confidence_interval,
    compute_markouts,
    market_diagnostics,
    pnl_decomposition,
    summarize_markouts,
)


def test_pnl_decomposition_reconciles_exactly() -> None:
    states = (
        StateRecord(time=0, midpoint=100, inventory=0),
        StateRecord(time=1, midpoint=101, inventory=2),
        StateRecord(time=2, midpoint=99, inventory=1),
    )
    fills = (
        FillRecord(time=1, signed_quantity=2, price=100, pre_event_mid=100),
        FillRecord(time=2, signed_quantity=-1, price=102, pre_event_mid=101),
    )

    result = pnl_decomposition(fills, states)

    assert result.cash == -98
    assert result.total_pnl == 1
    assert result.spread_capture == 1
    assert result.inventory_pnl == 0
    assert result.reconciliation_error == 0


def test_markouts_use_first_state_at_or_after_horizon_and_split_aggressors() -> None:
    states = (
        StateRecord(time=0, midpoint=100, inventory=0),
        StateRecord(time=1.1, midpoint=103, inventory=1),
        StateRecord(time=2, midpoint=104, inventory=0),
    )
    fills = (
        FillRecord(0, 1, 100, 100, "uninformed", fill_midpoint=100),
        FillRecord(0, -1, 102, 100, "informed", fill_midpoint=100),
    )

    markouts = compute_markouts(fills, states, horizons=(1, 2))
    summaries = summarize_markouts(markouts)

    assert [(record.horizon, record.markout_ticks_per_unit) for record in markouts] == [
        (1, 3),
        (2, 4),
        (1, -3),
        (2, -4),
    ]
    summary_values = [
        (summary.horizon, summary.aggressor_type, summary.mean_ticks_per_unit)
        for summary in summaries
    ]
    assert summary_values == [
        (1, "informed", -3),
        (1, "uninformed", 3),
        (2, "informed", -4),
        (2, "uninformed", 4),
    ]
    assert summary_values[0][2] < summary_values[1][2]


def test_market_diagnostics_reports_book_health() -> None:
    states = (
        StateRecord(0, 100, 0, best_bid=99, best_ask=101, bid_levels=5, ask_levels=6),
        StateRecord(2, 102, 1, best_bid=101, best_ask=103, bid_levels=7, ask_levels=8),
    )

    result = market_diagnostics(states)

    assert result.event_count == 1
    assert result.duration == 2
    assert result.mean_spread == 2
    assert result.nonempty_fraction == 1
    assert result.midpoint_range == 2


def test_bootstrap_and_sweep_are_deterministic() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    first_interval = bootstrap_confidence_interval(values, seed=7)
    assert first_interval == bootstrap_confidence_interval(values, seed=7)
    summaries = aggregate_sweep(
        [
            SweepObservation(0.1, 2, 2),
            SweepObservation(0.0, 1, 1),
            SweepObservation(0.1, 4, 1),
            SweepObservation(0.0, 3, 2),
        ],
        seed=3,
    )
    assert [summary.setting for summary in summaries] == [0.0, 0.1]
    assert [summary.mean for summary in summaries] == [2.0, 3.0]


def test_invalid_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="non-zero"):
        FillRecord(0, 0, 100, 100)
    with pytest.raises(ValueError, match="ordered"):
        compute_markouts(
            [],
            [StateRecord(1, 101, 0), StateRecord(0, 100, 0)],
        )
    with pytest.raises(ValueError, match="positive"):
        compute_markouts([], [StateRecord(0, 100, 0)], horizons=(0,))
