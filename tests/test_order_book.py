from __future__ import annotations

import pytest

from lobmm.order_book import OrderBook, Side


def test_resting_orders_follow_price_then_time_priority() -> None:
    book = OrderBook()
    book.add_limit_order("ask-old", Side.SELL, 101, 3)
    book.add_limit_order("ask-new", Side.SELL, 101, 4)
    book.add_limit_order("ask-worse", Side.SELL, 102, 5)

    trades = book.add_market_order("buyer", Side.BUY, 8)

    assert [(t.resting_order_id, t.price, t.quantity) for t in trades] == [
        ("ask-old", 101, 3),
        ("ask-new", 101, 4),
        ("ask-worse", 102, 1),
    ]
    assert book.depth(Side.SELL) == [(102, 4)]


def test_partial_fill_leaves_remainder_at_resting_price() -> None:
    book = OrderBook()
    book.add_limit_order("ask", Side.SELL, 101, 10)

    trades = book.add_market_order("buyer", Side.BUY, 3)

    assert trades[0].quantity == 3
    assert book.depth(Side.SELL) == [(101, 7)]
    assert book.order_count == 1


def test_market_order_walks_multiple_levels_and_can_be_partially_filled() -> None:
    book = OrderBook()
    book.add_limit_order("a1", Side.SELL, 101, 2)
    book.add_limit_order("a2", Side.SELL, 102, 2)

    trades = book.add_market_order("buyer", Side.BUY, 9)

    assert [(trade.price, trade.quantity) for trade in trades] == [(101, 2), (102, 2)]
    assert book.best_ask is None
    assert book.order_count == 0


def test_crossing_limit_matches_and_does_not_rest_crossed_book() -> None:
    book = OrderBook()
    book.add_limit_order("ask", Side.SELL, 101, 2)

    trades = book.add_limit_order("bid", Side.BUY, 102, 5)

    assert [(trade.price, trade.quantity) for trade in trades] == [(101, 2)]
    assert book.depth(Side.BUY) == [(102, 3)]
    assert book.best_ask is None
    assert book.spread is None


def test_cancel_removes_order_and_empty_level() -> None:
    book = OrderBook()
    book.add_limit_order("bid", Side.BUY, 99, 5)

    cancelled = book.cancel("bid")

    assert cancelled is not None
    assert cancelled.quantity == 5
    assert book.best_bid is None
    assert book.cancel("bid") is None


def test_cancel_from_a_populated_level_preserves_remaining_fifo_queue() -> None:
    book = OrderBook()
    book.add_limit_order("first", Side.SELL, 101, 1)
    book.add_limit_order("cancelled", Side.SELL, 101, 1)
    book.add_limit_order("last", Side.SELL, 101, 1)

    book.cancel("cancelled")
    trades = book.add_market_order("buyer", Side.BUY, 2)

    assert [trade.resting_order_id for trade in trades] == ["first", "last"]


def test_duplicate_identifiers_are_rejected_even_after_fill_or_cancel() -> None:
    book = OrderBook()
    book.add_limit_order("id", Side.BUY, 99, 1)
    book.cancel("id")

    with pytest.raises(ValueError, match="duplicate"):
        book.add_limit_order("id", Side.SELL, 101, 1)


@pytest.mark.parametrize(
    "price,quantity", [(0, 1), (-1, 1), (1, 0), (1, -1), (1.5, 1)]
)
def test_invalid_prices_and_quantities_are_rejected(price: int | float, quantity: int) -> None:
    with pytest.raises(ValueError):
        OrderBook().add_limit_order("order", Side.BUY, price, quantity)  # type: ignore[arg-type]


def test_invalid_side_and_depth_limit_are_rejected() -> None:
    book = OrderBook()
    with pytest.raises(TypeError, match="side"):
        book.add_limit_order("order", "buy", 100, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="levels"):
        book.depth(Side.BUY, levels=-1)


def test_book_is_never_left_crossed_by_sequential_orders() -> None:
    book = OrderBook()
    book.add_limit_order("bid-1", Side.BUY, 99, 2)
    book.add_limit_order("ask-1", Side.SELL, 103, 2)
    book.add_limit_order("bid-2", Side.BUY, 104, 4)
    book.add_limit_order("ask-2", Side.SELL, 98, 3)

    assert book.best_bid == 99
    assert book.best_ask is None
    assert book.spread is None


def test_depth_is_touch_first_and_can_be_limited() -> None:
    book = OrderBook()
    book.add_limit_order("b1", Side.BUY, 98, 1)
    book.add_limit_order("b2", Side.BUY, 100, 2)
    book.add_limit_order("a1", Side.SELL, 103, 3)
    book.add_limit_order("a2", Side.SELL, 101, 4)

    assert book.depth(Side.BUY, levels=1) == [(100, 2)]
    assert book.depth(Side.SELL) == [(101, 4), (103, 3)]
    assert book.mid == 100.5
    assert book.spread == 1


def test_market_order_id_cannot_be_reused() -> None:
    book = OrderBook()
    book.add_market_order("market", Side.BUY, 1)

    with pytest.raises(ValueError, match="duplicate"):
        book.add_market_order("market", Side.SELL, 1)
