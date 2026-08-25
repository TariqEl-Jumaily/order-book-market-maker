"""Accounting and analysis primitives for simulated market-making runs.

Prices are expressed in ticks throughout this module.  A market-maker buy has a
positive ``signed_quantity`` and a sell has a negative one; consequently its
cash change is always ``-signed_quantity * price``.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from statistics import fmean, median, stdev
from typing import Literal

import numpy as np

AggressorType = Literal["informed", "uninformed", "unknown"]


@dataclass(frozen=True, slots=True)
class FillRecord:
    """One fill received by the market maker.

    ``pre_event_mid`` is the midpoint observed immediately before the external
    event that generated the fill.  It is deliberately recorded with the fill
    so the spread-capture decomposition is independent of book internals.
    """

    time: float
    signed_quantity: int
    price: float
    pre_event_mid: float
    aggressor_type: AggressorType = "unknown"
    fill_midpoint: float | None = None

    def __post_init__(self) -> None:
        if self.signed_quantity == 0:
            raise ValueError("signed_quantity must be non-zero")
        if self.time < 0:
            raise ValueError("time must be non-negative")


@dataclass(frozen=True, slots=True)
class StateRecord:
    """Post-event state, including the market maker's inventory.

    ``best_bid`` and ``best_ask`` are optional because a midpoint can be
    supplied by an external reference price when one side of a synthetic book
    is temporarily empty.  The level counts are used for calibration
    diagnostics and default to zero when they were not logged.
    """

    time: float
    midpoint: float
    inventory: int
    cash: float = 0.0
    best_bid: float | None = None
    best_ask: float | None = None
    bid_levels: int = 0
    ask_levels: int = 0
    maker_bid: float | None = None
    maker_ask: float | None = None

    def __post_init__(self) -> None:
        if self.time < 0:
            raise ValueError("time must be non-negative")
        if self.bid_levels < 0 or self.ask_levels < 0:
            raise ValueError("level counts must be non-negative")
        if (self.best_bid is None) != (self.best_ask is None):
            raise ValueError("best_bid and best_ask must either both be present or absent")
        if (
            self.best_bid is not None
            and self.best_ask is not None
            and self.best_bid >= self.best_ask
        ):
            raise ValueError("best_bid must be below best_ask")

    @property
    def spread(self) -> float | None:
        """Quoted spread in ticks, if both sides of the book were present."""

        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid


@dataclass(frozen=True, slots=True)
class PnLDecomposition:
    """Marked-to-market PnL and its spread-capture/inventory decomposition."""

    cash: float
    terminal_inventory: int
    terminal_midpoint: float
    total_pnl: float
    spread_capture: float
    inventory_pnl: float
    reconciliation_error: float


@dataclass(frozen=True, slots=True)
class MarkoutRecord:
    """Realised per-unit markout for one fill at one horizon.

    Positive values are favourable to the market maker.  For example, a sell
    fill followed by a price rise has a negative markout.
    """

    fill_time: float
    horizon: float
    aggressor_type: AggressorType
    markout_ticks_per_unit: float


@dataclass(frozen=True, slots=True)
class MarkoutSummary:
    horizon: float
    aggressor_type: AggressorType
    fill_count: int
    mean_ticks_per_unit: float


@dataclass(frozen=True, slots=True)
class MarketDiagnostics:
    event_count: int
    duration: float
    mean_spread: float | None
    median_spread: float | None
    mean_bid_levels: float
    mean_ask_levels: float
    nonempty_fraction: float
    midpoint_volatility: float
    midpoint_range: float


@dataclass(frozen=True, slots=True)
class SweepObservation:
    """A single scalar outcome of one setting and random seed."""

    setting: float
    value: float
    seed: int


@dataclass(frozen=True, slots=True)
class SweepSummary:
    setting: float
    count: int
    mean: float
    standard_deviation: float
    ci_low: float
    ci_high: float


def _ordered_states(states: Sequence[StateRecord]) -> tuple[StateRecord, ...]:
    ordered = tuple(states)
    if not ordered:
        raise ValueError("at least one state record is required")
    if any(
        later.time < earlier.time for earlier, later in zip(ordered, ordered[1:], strict=False)
    ):
        raise ValueError("state records must be ordered by non-decreasing time")
    return ordered


def pnl_decomposition(
    fills: Iterable[FillRecord],
    states: Sequence[StateRecord],
    *,
    initial_midpoint: float | None = None,
    initial_inventory: int = 0,
    initial_cash: float = 0.0,
) -> PnLDecomposition:
    """Return PnL under the project's signed-quantity convention.

    If ``initial_midpoint`` is omitted, the first state is interpreted as the
    initial snapshot and only subsequent state-to-state price changes accrue
    inventory PnL.  Supplying it instead treats every supplied state as a
    post-event state.  With state records captured after every event and fills
    carrying that event's pre-event midpoint, ``reconciliation_error`` is zero
    (up to floating point precision).
    """

    ordered_states = _ordered_states(states)
    fill_records = tuple(fills)
    if any(
        later.time < earlier.time
        for earlier, later in zip(fill_records, fill_records[1:], strict=False)
    ):
        raise ValueError("fill records must be ordered by non-decreasing time")

    cash = initial_cash - sum(fill.signed_quantity * fill.price for fill in fill_records)
    spread_capture = sum(
        fill.signed_quantity * (fill.pre_event_mid - fill.price) for fill in fill_records
    )

    if initial_midpoint is None:
        previous_midpoint = ordered_states[0].midpoint
        price_states = ordered_states[1:]
        initial_value = initial_cash + initial_inventory * previous_midpoint
    else:
        previous_midpoint = initial_midpoint
        price_states = ordered_states
        initial_value = initial_cash + initial_inventory * initial_midpoint

    inventory_pnl = 0.0
    for state in price_states:
        inventory_pnl += state.inventory * (state.midpoint - previous_midpoint)
        previous_midpoint = state.midpoint

    terminal = ordered_states[-1]
    total_pnl = cash + terminal.inventory * terminal.midpoint - initial_value
    return PnLDecomposition(
        cash=cash,
        terminal_inventory=terminal.inventory,
        terminal_midpoint=terminal.midpoint,
        total_pnl=total_pnl,
        spread_capture=spread_capture,
        inventory_pnl=inventory_pnl,
        reconciliation_error=total_pnl - spread_capture - inventory_pnl,
    )


def reconcile_pnl(
    fills: Iterable[FillRecord],
    states: Sequence[StateRecord],
    *,
    initial_midpoint: float | None = None,
    initial_inventory: int = 0,
    initial_cash: float = 0.0,
) -> PnLDecomposition:
    """Alias for :func:`pnl_decomposition` used by reporting code."""

    return pnl_decomposition(
        fills,
        states,
        initial_midpoint=initial_midpoint,
        initial_inventory=initial_inventory,
        initial_cash=initial_cash,
    )


def compute_markouts(
    fills: Iterable[FillRecord],
    states: Sequence[StateRecord],
    horizons: Sequence[float] = (1.0, 5.0, 10.0, 30.0, 60.0),
) -> tuple[MarkoutRecord, ...]:
    """Calculate fill markouts using the first midpoint at or after each target.

    The result has one record for each fill/horizon pair for which the state
    history extends to that horizon.  It therefore avoids looking ahead past a
    simulation's terminal time.
    """

    ordered_states = _ordered_states(states)
    ordered_horizons = tuple(horizons)
    if any(horizon <= 0 for horizon in ordered_horizons):
        raise ValueError("markout horizons must be positive")
    if any(
        later < earlier
        for earlier, later in zip(ordered_horizons, ordered_horizons[1:], strict=False)
    ):
        raise ValueError("markout horizons must be sorted")

    fill_records = tuple(fills)
    if any(
        later.time < earlier.time
        for earlier, later in zip(fill_records, fill_records[1:], strict=False)
    ):
        raise ValueError("fill records must be ordered by non-decreasing time")

    result: list[MarkoutRecord] = []
    state_index = 0
    for fill in fill_records:
        while state_index < len(ordered_states) and ordered_states[state_index].time < fill.time:
            state_index += 1
        for horizon in ordered_horizons:
            target = fill.time + horizon
            index = state_index
            while index < len(ordered_states) and ordered_states[index].time < target:
                index += 1
            if index == len(ordered_states):
                continue
            direction = 1.0 if fill.signed_quantity > 0 else -1.0
            starting_midpoint = (
                fill.fill_midpoint if fill.fill_midpoint is not None else fill.pre_event_mid
            )
            result.append(
                MarkoutRecord(
                    fill_time=fill.time,
                    horizon=horizon,
                    aggressor_type=fill.aggressor_type,
                    markout_ticks_per_unit=direction
                    * (ordered_states[index].midpoint - starting_midpoint),
                )
            )
    return tuple(result)


def summarize_markouts(markouts: Iterable[MarkoutRecord]) -> tuple[MarkoutSummary, ...]:
    """Group markouts by horizon and informed/uninformed aggressor type."""

    grouped: dict[tuple[float, AggressorType], list[float]] = defaultdict(list)
    for markout in markouts:
        grouped[(markout.horizon, markout.aggressor_type)].append(markout.markout_ticks_per_unit)
    return tuple(
        MarkoutSummary(horizon, aggressor_type, len(values), fmean(values))
        for (horizon, aggressor_type), values in sorted(grouped.items())
    )


def market_diagnostics(states: Sequence[StateRecord]) -> MarketDiagnostics:
    """Summarise the calibration diagnostics of a simulated market."""

    ordered_states = _ordered_states(states)
    spreads = [spread for state in ordered_states if (spread := state.spread) is not None]
    midpoints = [state.midpoint for state in ordered_states]
    midpoint_changes = [
        later - earlier for earlier, later in zip(midpoints, midpoints[1:], strict=False)
    ]
    nonempty = [state.bid_levels > 0 and state.ask_levels > 0 for state in ordered_states]
    return MarketDiagnostics(
        event_count=max(0, len(ordered_states) - 1),
        duration=ordered_states[-1].time - ordered_states[0].time,
        mean_spread=fmean(spreads) if spreads else None,
        median_spread=median(spreads) if spreads else None,
        mean_bid_levels=fmean(state.bid_levels for state in ordered_states),
        mean_ask_levels=fmean(state.ask_levels for state in ordered_states),
        nonempty_fraction=fmean(nonempty),
        midpoint_volatility=stdev(midpoint_changes) if len(midpoint_changes) > 1 else 0.0,
        midpoint_range=max(midpoints) - min(midpoints),
    )


def bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    resamples: int = 2_000,
    seed: int = 0,
) -> tuple[float, float]:
    """Return a deterministic percentile-bootstrap confidence interval for a mean."""

    if not values:
        raise ValueError("cannot bootstrap an empty sample")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    if resamples <= 0:
        raise ValueError("resamples must be positive")
    if len(values) == 1:
        return (values[0], values[0])
    samples = np.asarray(values, dtype=float)
    generator = np.random.default_rng(seed)
    indices = generator.integers(0, len(samples), size=(resamples, len(samples)))
    means = samples[indices].mean(axis=1)
    alpha = (1.0 - confidence) / 2.0
    return (float(np.quantile(means, alpha)), float(np.quantile(means, 1.0 - alpha)))


def aggregate_sweep(
    observations: Iterable[SweepObservation],
    *,
    confidence: float = 0.95,
    resamples: int = 2_000,
    seed: int = 0,
) -> tuple[SweepSummary, ...]:
    """Aggregate seeded experiment outcomes by setting in deterministic order."""

    grouped: dict[float, list[float]] = defaultdict(list)
    for observation in observations:
        grouped[observation.setting].append(observation.value)
    if not grouped:
        raise ValueError("at least one sweep observation is required")

    summaries: list[SweepSummary] = []
    for index, setting in enumerate(sorted(grouped)):
        values = grouped[setting]
        ci_low, ci_high = bootstrap_confidence_interval(
            values, confidence=confidence, resamples=resamples, seed=seed + index
        )
        summaries.append(
            SweepSummary(
                setting=setting,
                count=len(values),
                mean=fmean(values),
                standard_deviation=stdev(values) if len(values) > 1 else 0.0,
                ci_low=ci_low,
                ci_high=ci_high,
            )
        )
    return tuple(summaries)
