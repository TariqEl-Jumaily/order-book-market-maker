"""Inventory-aware passive market-making strategy."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .order_book import Order, Side, Trade


@dataclass(frozen=True, slots=True)
class MarketMakerConfig:
    """Parameters for linear inventory-skewed two-sided quotes."""

    gamma: float = 0.05
    half_spread_ticks: int = 2
    quote_size: int = 5
    inventory_limit: int = 20
    agent_id: str = "market_maker"

    def __post_init__(self) -> None:
        if self.gamma < 0:
            raise ValueError("gamma must be non-negative")
        if self.half_spread_ticks <= 0:
            raise ValueError("half_spread_ticks must be positive")
        if self.quote_size <= 0:
            raise ValueError("quote_size must be positive")
        if self.inventory_limit <= 0:
            raise ValueError("inventory_limit must be positive")


@dataclass(frozen=True, slots=True)
class FillRecord:
    """A maker fill in signed-quantity accounting convention."""

    order_id: str
    side: Side
    price: int
    quantity: int
    signed_quantity: int


@dataclass(slots=True)
class _LiveQuote:
    side: Side
    price: int
    remaining_qty: int
    quoted_at: float


class MarketMaker:
    """A simple market maker using ``mid - gamma * inventory`` reservation price.

    The class owns strategy state and accounting but does not mutate an order book.
    A simulator should cancel the identifiers from :meth:`withdraw_quotes`, submit
    the orders from :meth:`quote_orders`, and route resulting trades to
    :meth:`on_trade`.
    """

    def __init__(self, config: MarketMakerConfig | None = None) -> None:
        self.config = config or MarketMakerConfig()
        self.inventory = 0
        self.cash = 0.0
        self._next_quote_number = 0
        self._live_quotes: dict[str, _LiveQuote] = {}

    @property
    def agent_id(self) -> str:
        return self.config.agent_id

    @property
    def active_quote_ids(self) -> tuple[str, ...]:
        return tuple(self._live_quotes)

    @property
    def active_quotes(self) -> tuple[tuple[str, Side, int, int], ...]:
        """Return immutable snapshots as ``(id, side, price, remaining)``."""

        return tuple(
            (order_id, quote.side, quote.price, quote.remaining_qty)
            for order_id, quote in self._live_quotes.items()
        )

    def reservation_price(self, midpoint_ticks: int) -> float:
        return midpoint_ticks - self.config.gamma * self.inventory

    def desired_quote_prices(self, midpoint_ticks: int) -> tuple[int | None, int | None]:
        """Return (bid, ask), suppressing any side that would increase a limit hit."""

        reservation = self.reservation_price(midpoint_ticks)
        bid = math.floor(reservation - self.config.half_spread_ticks)
        ask = math.ceil(reservation + self.config.half_spread_ticks)
        bid_price = max(1, bid) if self.inventory < self.config.inventory_limit else None
        ask_price = max(1, ask) if self.inventory > -self.config.inventory_limit else None
        return bid_price, ask_price

    def quote_orders(
        self,
        midpoint_ticks: int,
        timestamp: float,
        *,
        best_bid: int | None = None,
        best_ask: int | None = None,
    ) -> list[Order]:
        """Build and register fresh quotes using currently available inventory room.

        Call :meth:`withdraw_quotes` before replacing live quotes.  Registering the
        orders here ensures partial fills can be accounted for without looking up
        mutable book state.
        """

        if self._live_quotes:
            raise RuntimeError("withdraw existing quotes before issuing replacements")
        bid, ask = self.desired_quote_prices(midpoint_ticks)
        if bid is not None and best_ask is not None:
            bid = min(bid, best_ask - 1)
        if ask is not None and best_bid is not None:
            ask = max(ask, best_bid + 1)
        orders: list[Order] = []
        if bid is not None:
            orders.append(self._new_quote(Side.BUY, bid, timestamp, self._buy_capacity()))
        if ask is not None:
            orders.append(self._new_quote(Side.SELL, ask, timestamp, self._sell_capacity()))
        return orders

    def withdraw_quotes(self) -> tuple[str, ...]:
        """Forget active quote state and return the IDs the caller should cancel."""

        quote_ids = self.active_quote_ids
        self._live_quotes.clear()
        return quote_ids

    def process_fill(self, order_id: str, price: int, quantity: int) -> FillRecord | None:
        """Apply a fill against one of this maker's known resting quotes."""

        quote = self._live_quotes.get(order_id)
        if quote is None:
            return None
        if quantity <= 0:
            raise ValueError("fill quantity must be positive")
        if quantity > quote.remaining_qty:
            raise ValueError("fill quantity exceeds live quote quantity")
        signed_quantity = quantity if quote.side is Side.BUY else -quantity
        new_inventory = self.inventory + signed_quantity
        if abs(new_inventory) > self.config.inventory_limit:
            raise ValueError("fill would breach inventory limit")
        self.inventory = new_inventory
        self.cash -= signed_quantity * price
        quote.remaining_qty -= quantity
        if quote.remaining_qty == 0:
            del self._live_quotes[order_id]
        return FillRecord(
            order_id=order_id,
            side=quote.side,
            price=price,
            quantity=quantity,
            signed_quantity=signed_quantity,
        )

    def on_trade(self, trade: Trade) -> FillRecord | None:
        """Account for a book trade if either referenced order is one of our quotes.

        The matching engine normally reports maker quotes as ``resting_order_id``;
        accepting the incoming identifier as well makes this adapter tolerant of a
        controlled test or a future strategy that crosses the book.
        """

        order_id = self._trade_order_id(trade)
        if order_id is None:
            return None
        return self.process_fill(order_id, int(trade.price), int(trade.quantity))

    def marked_to_market_pnl(self, midpoint_ticks: int) -> float:
        return self.cash + self.inventory * midpoint_ticks

    def _new_quote(self, side: Side, price: int, timestamp: float, capacity: int) -> Order:
        quantity = min(self.config.quote_size, capacity)
        if quantity <= 0:
            raise RuntimeError("attempted to quote with no inventory capacity")
        order_id = f"{self.config.agent_id}-{self._next_quote_number}"
        self._next_quote_number += 1
        self._live_quotes[order_id] = _LiveQuote(
            side=side, price=price, remaining_qty=quantity, quoted_at=timestamp
        )
        return Order(
            order_id=order_id,
            side=side,
            price=price,
            quantity=quantity,
        )

    def _buy_capacity(self) -> int:
        return self.config.inventory_limit - self.inventory

    def _sell_capacity(self) -> int:
        return self.config.inventory_limit + self.inventory

    def _trade_order_id(self, trade: Trade) -> str | None:
        # Keep the strategy adapter compatible with the explicit matching-engine
        # metadata while avoiding an unnecessary dependency on its exact class.
        for attribute in ("resting_order_id", "incoming_order_id"):
            candidate: Any = getattr(trade, attribute, None)
            if isinstance(candidate, str) and candidate in self._live_quotes:
                return candidate
        return None
