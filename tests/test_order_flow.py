"""Tests for continuous-time background order flow."""

import random

import pytest

from lobmm.order_book import Side
from lobmm.order_flow import (
    ActiveOrderPool,
    EventType,
    OrderFlowConfig,
    event_hazards,
    sample_background_limit_order,
    sample_geometric_distance,
    sample_market_order,
    sample_next_event,
    sample_value_shock,
)


def test_active_order_pool_removes_by_swap_and_chooses_active_order() -> None:
    pool = ActiveOrderPool()
    pool.add("a")
    pool.add("b")
    pool.add("c")

    assert pool.discard("b")
    assert pool.order_ids == ("a", "c")
    assert pool.choose(random.Random(3)) in {"a", "c"}
    assert not pool.discard("missing")
    with pytest.raises(ValueError, match="already active"):
        pool.add("a")


def test_cancel_hazard_scales_with_active_background_orders() -> None:
    config = OrderFlowConfig(cancel_rate_per_order=0.3)

    assert event_hazards(config, 4)[EventType.CANCEL] == pytest.approx(1.2)


def test_next_event_is_reproducible_and_advances_time() -> None:
    config = OrderFlowConfig(limit_order_rate=1.0, market_order_rate=0.0, value_shock_rate=0.0)

    first = sample_next_event(2.0, config, 0, random.Random(7))
    second = sample_next_event(2.0, config, 0, random.Random(7))

    assert first == second
    assert first.event_type is EventType.LIMIT_ORDER
    assert first.time > 2.0


def test_informed_market_orders_trade_toward_latent_value() -> None:
    config = OrderFlowConfig(informed_probability=1.0, min_order_size=2, max_order_size=2)

    buy = sample_market_order(
        config, fair_value_ticks=101, midpoint_ticks=100, rng=random.Random(1)
    )
    sell = sample_market_order(
        config, fair_value_ticks=99, midpoint_ticks=100, rng=random.Random(1)
    )

    assert (buy.side, buy.informed, buy.quantity) == (Side.BUY, True, 2)
    assert (sell.side, sell.informed, sell.quantity) == (Side.SELL, True, 2)


def test_background_limits_are_passive_from_the_touch() -> None:
    config = OrderFlowConfig(
        geometric_distance_probability=1.0, min_order_size=3, max_order_size=3
    )
    bid = sample_background_limit_order(
        order_id="b", side=Side.BUY, timestamp=0.0, best_bid_ticks=100,
        best_ask_ticks=102, fair_value_ticks=101, config=config, rng=random.Random(1),
    )
    ask = sample_background_limit_order(
        order_id="a", side=Side.SELL, timestamp=0.0, best_bid_ticks=100,
        best_ask_ticks=102, fair_value_ticks=101, config=config, rng=random.Random(1),
    )

    assert (bid.price, bid.quantity) == (100, 3)
    assert (ask.price, ask.quantity) == (102, 3)
    assert sample_geometric_distance(1.0, random.Random(0)) == 1
    assert abs(sample_value_shock(config, random.Random(0))) == config.value_shock_ticks
