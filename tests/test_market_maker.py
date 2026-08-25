"""Tests for linear inventory-skew market-maker accounting."""

import pytest

from lobmm.market_maker import MarketMaker, MarketMakerConfig
from lobmm.order_book import Side, Trade


def test_inventory_skews_both_quotes_downward() -> None:
    maker = MarketMaker(MarketMakerConfig(gamma=1.0, half_spread_ticks=2))
    maker.inventory = 3

    assert maker.reservation_price(100) == 97.0
    assert maker.desired_quote_prices(100) == (95, 99)


def test_quotes_have_unique_ids_and_respect_remaining_capacity() -> None:
    maker = MarketMaker(MarketMakerConfig(quote_size=5, inventory_limit=3))
    orders = maker.quote_orders(100, timestamp=0.0)

    assert [order.side for order in orders] == [Side.BUY, Side.SELL]
    assert all(order.quantity == 3 for order in orders)
    assert len(set(order.order_id for order in orders)) == 2
    assert maker.withdraw_quotes() == tuple(order.order_id for order in orders)


def test_partial_fill_updates_signed_cash_inventory_and_quote_remainder() -> None:
    maker = MarketMaker(MarketMakerConfig(quote_size=4, inventory_limit=5))
    bid = maker.quote_orders(100, timestamp=0.0)[0]

    fill = maker.process_fill(bid.order_id, price=98, quantity=2)

    assert fill is not None
    assert fill.signed_quantity == 2
    assert maker.inventory == 2
    assert maker.cash == -196
    assert maker.active_quote_ids == (bid.order_id, maker.active_quote_ids[1])
    with pytest.raises(ValueError, match="exceeds"):
        maker.process_fill(bid.order_id, price=98, quantity=3)
    assert maker.process_fill(bid.order_id, price=98, quantity=2) is not None
    assert bid.order_id not in maker.active_quote_ids


def test_inventory_limit_suppresses_exposure_increasing_quote() -> None:
    maker = MarketMaker(MarketMakerConfig(inventory_limit=2))
    maker.inventory = 2

    bid, ask = maker.desired_quote_prices(100)

    assert bid is None
    assert ask is not None


def test_trade_adapter_identifies_resting_maker_quote() -> None:
    maker = MarketMaker(MarketMakerConfig(quote_size=2))
    quote = maker.quote_orders(100, timestamp=0.0)[0]
    trade = Trade(
        resting_order_id=quote.order_id,
        incoming_order_id="external-1",
        aggressor_side=Side.SELL,
        price=quote.price,
        quantity=2,
    )

    fill = maker.on_trade(trade)

    assert fill is not None
    assert maker.inventory == 2
    assert maker.cash == -2 * quote.price
    assert maker.on_trade(trade) is None
