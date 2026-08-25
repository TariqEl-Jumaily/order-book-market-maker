"""Validated configuration for simulations and experiments."""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Self


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """All parameters needed to reproduce one simulated market session."""

    initial_mid_ticks: int = 10_000
    tick_value: float = 0.01
    seed_levels: int = 10
    seed_orders_per_level: int = 2
    seed_order_qty: int = 3
    limit_order_rate: float = 12.0
    market_order_rate: float = 10.0
    cancel_rate_per_order: float = 0.05
    value_shock_rate: float = 0.8
    informed_fraction: float = 0.2
    placement_geometric_p: float = 0.45
    size_geometric_p: float = 0.2
    max_order_qty: int = 15
    fundamental_shock_ticks: int = 4
    session_events: int = 5_000
    half_spread_ticks: int = 1
    inventory_aversion: float = 0.1
    quote_size: int = 5
    inventory_limit: int = 100
    markout_horizons: tuple[float, ...] = (1.0, 5.0, 10.0, 30.0, 60.0)

    def __post_init__(self) -> None:
        positive_ints = {
            "initial_mid_ticks": self.initial_mid_ticks,
            "seed_levels": self.seed_levels,
            "seed_orders_per_level": self.seed_orders_per_level,
            "seed_order_qty": self.seed_order_qty,
            "max_order_qty": self.max_order_qty,
            "fundamental_shock_ticks": self.fundamental_shock_ticks,
            "session_events": self.session_events,
            "half_spread_ticks": self.half_spread_ticks,
            "quote_size": self.quote_size,
            "inventory_limit": self.inventory_limit,
        }
        for name, value in positive_ints.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        positive_rates: dict[str, float] = {
            "tick_value": self.tick_value,
            "limit_order_rate": self.limit_order_rate,
            "market_order_rate": self.market_order_rate,
            "placement_geometric_p": self.placement_geometric_p,
            "size_geometric_p": self.size_geometric_p,
        }
        for name, rate in positive_rates.items():
            if rate <= 0:
                raise ValueError(f"{name} must be positive")
        if self.cancel_rate_per_order < 0 or self.value_shock_rate < 0:
            raise ValueError("cancellation and value-shock rates cannot be negative")
        if not 0.0 <= self.informed_fraction <= 1.0:
            raise ValueError("informed_fraction must lie in [0, 1]")
        if not 0.0 < self.placement_geometric_p <= 1.0:
            raise ValueError("placement_geometric_p must lie in (0, 1]")
        if not 0.0 < self.size_geometric_p <= 1.0:
            raise ValueError("size_geometric_p must lie in (0, 1]")
        if self.inventory_aversion < 0:
            raise ValueError("inventory_aversion cannot be negative")
        if not self.markout_horizons or any(h <= 0 for h in self.markout_horizons):
            raise ValueError("markout_horizons must contain positive values")

    @classmethod
    def from_toml(cls, path: str | Path) -> Self:
        with Path(path).open("rb") as handle:
            raw: dict[str, Any] = tomllib.load(handle)
        if "markout_horizons" in raw:
            raw["markout_horizons"] = tuple(float(x) for x in raw["markout_horizons"])
        return cls(**raw)

    def with_updates(self, **updates: Any) -> Self:
        return replace(self, **updates)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["markout_horizons"] = list(self.markout_horizons)
        return result
