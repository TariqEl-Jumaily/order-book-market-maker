"""Stochastic background order flow for the simulated limit order book.

The model intentionally separates *sampling* from book mutation.  A simulator can
therefore log the sampled event before applying it, which makes seeded runs easy to
reproduce and audit.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum

from .order_book import Order, Side


class EventType(StrEnum):
    """Exogenous event categories in the continuous-time simulation."""

    LIMIT_ORDER = "limit_order"
    MARKET_ORDER = "market_order"
    CANCEL = "cancel"
    VALUE_SHOCK = "value_shock"


@dataclass(frozen=True, slots=True)
class OrderFlowConfig:
    """Rates and distributional assumptions for the synthetic market.

    Rates are intensities per unit of simulation time.  ``cancel_rate_per_order``
    is multiplied by the active background-order count, so cancellation pressure
    naturally grows with displayed background liquidity.
    """

    limit_order_rate: float = 8.0
    market_order_rate: float = 2.0
    cancel_rate_per_order: float = 0.08
    value_shock_rate: float = 0.20
    informed_probability: float = 0.20
    geometric_distance_probability: float = 0.55
    geometric_size_probability: float = 0.50
    min_order_size: int = 1
    max_order_size: int = 10
    value_shock_ticks: int = 2

    def __post_init__(self) -> None:
        nonnegative = (
            self.limit_order_rate,
            self.market_order_rate,
            self.cancel_rate_per_order,
            self.value_shock_rate,
        )
        if any(rate < 0 for rate in nonnegative):
            raise ValueError("event rates must be non-negative")
        if not 0 <= self.informed_probability <= 1:
            raise ValueError("informed_probability must lie in [0, 1]")
        if not 0 < self.geometric_distance_probability <= 1:
            raise ValueError("geometric_distance_probability must lie in (0, 1]")
        if not 0 < self.geometric_size_probability <= 1:
            raise ValueError("geometric_size_probability must lie in (0, 1]")
        if self.min_order_size <= 0 or self.max_order_size < self.min_order_size:
            raise ValueError("order-size bounds must be positive and ordered")
        if self.value_shock_ticks <= 0:
            raise ValueError("value_shock_ticks must be positive")


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    """An event sampled from the total hazard at an absolute time."""

    event_type: EventType
    time: float


@dataclass(frozen=True, slots=True)
class MarketOrderIntent:
    """A market order direction, size, and whether it is value informed."""

    side: Side
    quantity: int
    informed: bool


class ActiveOrderPool:
    """An indexed set of cancellable background order identifiers.

    Adding, removing, testing membership, and sampling a uniformly random active
    order are all average O(1).  The final list position is swapped into a removed
    element's slot, so callers must not rely on iteration order.
    """

    def __init__(self) -> None:
        self._order_ids: list[str] = []
        self._positions: dict[str, int] = {}

    def __len__(self) -> int:
        return len(self._order_ids)

    def __contains__(self, order_id: object) -> bool:
        return order_id in self._positions

    def __iter__(self) -> Iterator[str]:
        return iter(self._order_ids)

    @property
    def order_ids(self) -> tuple[str, ...]:
        """Return a stable snapshot of currently active identifiers."""

        return tuple(self._order_ids)

    def add(self, order_id: str) -> None:
        if order_id in self._positions:
            raise ValueError(f"order already active: {order_id}")
        self._positions[order_id] = len(self._order_ids)
        self._order_ids.append(order_id)

    def discard(self, order_id: str) -> bool:
        """Remove ``order_id`` and return whether it had been present."""

        position = self._positions.pop(order_id, None)
        if position is None:
            return False
        last_order_id = self._order_ids.pop()
        if position != len(self._order_ids):
            self._order_ids[position] = last_order_id
            self._positions[last_order_id] = position
        return True

    def choose(self, rng: random.Random) -> str:
        if not self._order_ids:
            raise IndexError("cannot choose from an empty ActiveOrderPool")
        return self._order_ids[rng.randrange(len(self._order_ids))]


def event_hazards(config: OrderFlowConfig, active_background_orders: int) -> dict[EventType, float]:
    """Return event hazards for the current background-book state."""

    if active_background_orders < 0:
        raise ValueError("active_background_orders cannot be negative")
    return {
        EventType.LIMIT_ORDER: config.limit_order_rate,
        EventType.MARKET_ORDER: config.market_order_rate,
        EventType.CANCEL: config.cancel_rate_per_order * active_background_orders,
        EventType.VALUE_SHOCK: config.value_shock_rate,
    }


def sample_next_event(
    now: float,
    config: OrderFlowConfig,
    active_background_orders: int,
    rng: random.Random,
) -> ScheduledEvent:
    """Sample a waiting time and event category from a competing-hazards model."""

    if now < 0:
        raise ValueError("now cannot be negative")
    hazards = event_hazards(config, active_background_orders)
    total_hazard = sum(hazards.values())
    if total_hazard <= 0:
        raise ValueError("at least one event hazard must be positive")
    event_time = now + rng.expovariate(total_hazard)
    draw = rng.random() * total_hazard
    running_total = 0.0
    for event_type in EventType:
        running_total += hazards[event_type]
        if draw < running_total:
            return ScheduledEvent(event_type=event_type, time=event_time)
    # Floating-point round-off can put draw on the upper edge of the interval.
    return ScheduledEvent(event_type=EventType.VALUE_SHOCK, time=event_time)


def sample_geometric_distance(probability: float, rng: random.Random) -> int:
    """Sample a positive geometric distance in ticks without a NumPy dependency."""

    if not 0 < probability <= 1:
        raise ValueError("probability must lie in (0, 1]")
    if probability == 1:
        return 1
    return int(math.floor(math.log1p(-rng.random()) / math.log1p(-probability))) + 1


def sample_order_size(config: OrderFlowConfig, rng: random.Random) -> int:
    """Sample a bounded positive geometric order size."""

    if config.min_order_size == config.max_order_size:
        return config.min_order_size
    draw = sample_geometric_distance(config.geometric_size_probability, rng)
    return min(config.max_order_size, config.min_order_size + draw - 1)


def sample_market_order(
    config: OrderFlowConfig,
    fair_value_ticks: int,
    midpoint_ticks: int,
    rng: random.Random,
) -> MarketOrderIntent:
    """Sample an 80/20-style uninformed/informed aggressive order.

    Informed flow buys when the latent fair value exceeds the midpoint and sells
    when it is below.  At equality it is deliberately direction-neutral.
    """

    informed = rng.random() < config.informed_probability
    if informed and fair_value_ticks != midpoint_ticks:
        side = Side.BUY if fair_value_ticks > midpoint_ticks else Side.SELL
    else:
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
    quantity = sample_order_size(config, rng)
    if informed and fair_value_ticks != midpoint_ticks:
        signal_size = 2 * abs(fair_value_ticks - midpoint_ticks)
        quantity = min(config.max_order_size, max(quantity, signal_size))
    return MarketOrderIntent(side=side, quantity=quantity, informed=informed)


def sample_value_shock(config: OrderFlowConfig, rng: random.Random) -> int:
    """Draw an independent signed latent-value shock measured in ticks."""

    sign = 1 if rng.random() < 0.5 else -1
    return sign * config.value_shock_ticks


def sample_background_limit_order(
    *,
    order_id: str,
    side: Side,
    timestamp: float,
    best_bid_ticks: int | None,
    best_ask_ticks: int | None,
    fair_value_ticks: int,
    config: OrderFlowConfig,
    rng: random.Random,
) -> Order:
    """Create a passive background order at a geometric distance from the touch."""

    # Add one tick so background flow may join the touch but never creates a
    # locked one-tick book. This keeps the baseline spread near two ticks.
    distance = sample_geometric_distance(config.geometric_distance_probability, rng) + 1
    if side is Side.BUY:
        reference = best_ask_ticks if best_ask_ticks is not None else fair_value_ticks
        price = max(1, reference - distance)
    else:
        reference = best_bid_ticks if best_bid_ticks is not None else fair_value_ticks
        price = max(1, reference + distance)
    quantity = sample_order_size(config, rng)
    return Order(
        order_id=order_id,
        side=side,
        price=price,
        quantity=quantity,
    )
