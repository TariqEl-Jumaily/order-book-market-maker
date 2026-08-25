"""A small, price-time-priority limit order book.

Prices are deliberately represented as integer ticks.  The book keeps one
``SortedDict`` per side and an ``OrderedDict`` for each price level, which
makes the first order at a price the FIFO execution priority.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from enum import StrEnum

from sortedcontainers import SortedDict


class Side(StrEnum):
    """The side of an order from the submitting participant's perspective."""

    BUY = "buy"
    SELL = "sell"

    @property
    def opposite(self) -> Side:
        return Side.SELL if self is Side.BUY else Side.BUY


@dataclass
class Order:
    """A resting or incoming order, with ``quantity`` equal to its remainder."""

    order_id: str
    side: Side
    price: int
    quantity: int


@dataclass(frozen=True)
class Trade:
    """A fill at the resting order's price."""

    resting_order_id: str
    incoming_order_id: str
    aggressor_side: Side
    price: int
    quantity: int


@dataclass
class PriceLevel:
    """FIFO queue of orders at one price."""

    price: int
    orders: OrderedDict[str, Order] = field(default_factory=OrderedDict)

    @property
    def total_quantity(self) -> int:
        return sum(order.quantity for order in self.orders.values())

    def add(self, order: Order) -> None:
        self.orders[order.order_id] = order

    def remove(self, order_id: str) -> Order:
        return self.orders.pop(order_id)


class OrderBook:
    """Price-time-priority book for a single instrument.

    ``cancel`` has average O(1) order lookup and removal while its price level
    remains populated.  If it removes the final order at a level, deleting the
    level from ``SortedDict`` takes O(log P), where P is populated price levels.
    Matching an order is O(number of fills plus crossed levels * log P).
    """

    def __init__(self) -> None:
        self._bids: SortedDict[int, PriceLevel] = SortedDict()
        self._asks: SortedDict[int, PriceLevel] = SortedDict()
        self._active_orders: dict[str, Order] = {}
        self._used_order_ids: set[str] = set()

    @property
    def best_bid(self) -> int | None:
        """The highest bid tick, or ``None`` when there are no bids."""

        return self._bids.peekitem(-1)[0] if self._bids else None

    @property
    def best_ask(self) -> int | None:
        """The lowest ask tick, or ``None`` when there are no asks."""

        return self._asks.peekitem(0)[0] if self._asks else None

    @property
    def mid(self) -> float | None:
        """The arithmetic midpoint in ticks when both sides are populated."""

        if self.best_bid is None or self.best_ask is None:
            return None
        return (self.best_bid + self.best_ask) / 2

    @property
    def spread(self) -> int | None:
        """The quoted spread in ticks when both sides are populated."""

        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    @property
    def order_count(self) -> int:
        return len(self._active_orders)

    def add_limit_order(
        self, order_id: str, side: Side, price: int, quantity: int
    ) -> list[Trade]:
        """Submit a limit order and return all immediate executions.

        Any remainder rests only if it is no longer marketable; consequently a
        book can never retain crossed bid and ask levels.
        """

        self._validate_new_order(order_id, side, price, quantity)
        self._used_order_ids.add(order_id)
        incoming = Order(order_id=order_id, side=side, price=price, quantity=quantity)
        trades = self._match(incoming, limit_price=price)
        if incoming.quantity:
            self._rest(incoming)
        return trades

    def add_market_order(self, order_id: str, side: Side, quantity: int) -> list[Trade]:
        """Submit a market order, returning fills and discarding any remainder."""

        self._validate_new_order(order_id, side, price=1, quantity=quantity)
        self._used_order_ids.add(order_id)
        incoming = Order(order_id=order_id, side=side, price=0, quantity=quantity)
        return self._match(incoming, limit_price=None)

    def cancel(self, order_id: str) -> Order | None:
        """Cancel a resting order, or return ``None`` if it is not active."""

        order = self._active_orders.pop(order_id, None)
        if order is None:
            return None
        levels = self._levels_for(order.side)
        level = levels[order.price]
        cancelled: Order = level.remove(order_id)
        if not level.orders:
            del levels[order.price]
        return cancelled

    def depth(self, side: Side, levels: int | None = None) -> list[tuple[int, int]]:
        """Return ``(price, aggregate quantity)`` from the touch outward."""

        if levels is not None and levels < 0:
            raise ValueError("levels must be non-negative or None")
        book = self._levels_for(side)
        prices = reversed(book.keys()) if side is Side.BUY else iter(book.keys())
        output: list[tuple[int, int]] = []
        for price in prices:
            output.append((price, book[price].total_quantity))
            if levels is not None and len(output) >= levels:
                break
        return output

    def _match(self, incoming: Order, limit_price: int | None) -> list[Trade]:
        trades: list[Trade] = []
        opposite = self._levels_for(incoming.side.opposite)
        while incoming.quantity and opposite:
            best_price = (
                opposite.peekitem(0)[0]
                if incoming.side is Side.BUY
                else opposite.peekitem(-1)[0]
            )
            if limit_price is not None and not self._crosses(
                incoming.side, limit_price, best_price
            ):
                break
            level = opposite[best_price]
            while incoming.quantity and level.orders:
                resting_id, resting = next(iter(level.orders.items()))
                fill_quantity = min(incoming.quantity, resting.quantity)
                incoming.quantity -= fill_quantity
                resting.quantity -= fill_quantity
                trades.append(
                    Trade(
                        resting_order_id=resting_id,
                        incoming_order_id=incoming.order_id,
                        aggressor_side=incoming.side,
                        price=best_price,
                        quantity=fill_quantity,
                    )
                )
                if resting.quantity == 0:
                    level.remove(resting_id)
                    del self._active_orders[resting_id]
            if not level.orders:
                del opposite[best_price]
        return trades

    def _rest(self, order: Order) -> None:
        levels = self._levels_for(order.side)
        level = levels.get(order.price)
        if level is None:
            level = PriceLevel(price=order.price)
            levels[order.price] = level
        level.add(order)
        self._active_orders[order.order_id] = order

    def _levels_for(self, side: Side) -> SortedDict[int, PriceLevel]:
        return self._bids if side is Side.BUY else self._asks

    @staticmethod
    def _crosses(side: Side, limit_price: int, best_opposite_price: int) -> bool:
        if side is Side.BUY:
            return limit_price >= best_opposite_price
        return limit_price <= best_opposite_price

    def _validate_new_order(
        self, order_id: str, side: Side, price: int, quantity: int
    ) -> None:
        if not isinstance(order_id, str) or not order_id:
            raise ValueError("order_id must be a non-empty string")
        if order_id in self._used_order_ids:
            raise ValueError(f"duplicate order_id: {order_id}")
        if not isinstance(side, Side):
            raise TypeError("side must be a Side")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0:
            raise ValueError("price must be a positive integer tick")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
