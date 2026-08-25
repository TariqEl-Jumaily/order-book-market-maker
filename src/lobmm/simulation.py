"""Continuous-time integration of the book, order flow, and market maker."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .analytics import (
    AggressorType,
    FillRecord,
    MarketDiagnostics,
    MarkoutRecord,
    MarkoutSummary,
    PnLDecomposition,
    StateRecord,
    compute_markouts,
    market_diagnostics,
    pnl_decomposition,
    summarize_markouts,
)
from .config import SimulationConfig
from .market_maker import MarketMaker, MarketMakerConfig
from .order_book import OrderBook, Side, Trade
from .order_flow import (
    ActiveOrderPool,
    EventType,
    OrderFlowConfig,
    sample_background_limit_order,
    sample_market_order,
    sample_next_event,
    sample_value_shock,
)


@dataclass(frozen=True, slots=True)
class EventRecord:
    index: int
    time: float
    event_type: str
    fair_value: int
    trade_count: int
    aggressor_type: str = "unknown"


@dataclass(frozen=True, slots=True)
class SimulationResult:
    seed: int
    config: SimulationConfig
    events: tuple[EventRecord, ...]
    fills: tuple[FillRecord, ...]
    states: tuple[StateRecord, ...]
    pnl: PnLDecomposition
    diagnostics: MarketDiagnostics
    markouts: tuple[MarkoutRecord, ...]
    markout_summary: tuple[MarkoutSummary, ...]
    max_absolute_inventory: int
    depth_profile: tuple[tuple[float, float, float], ...]

    def summary_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "total_pnl_ticks": self.pnl.total_pnl,
            "spread_capture_ticks": self.pnl.spread_capture,
            "inventory_pnl_ticks": self.pnl.inventory_pnl,
            "reconciliation_error": self.pnl.reconciliation_error,
            "terminal_inventory": self.pnl.terminal_inventory,
            "max_absolute_inventory": self.max_absolute_inventory,
            "fill_count": len(self.fills),
            "duration": self.diagnostics.duration,
            "mean_spread_ticks": self.diagnostics.mean_spread,
            "median_spread_ticks": self.diagnostics.median_spread,
            "mean_bid_levels": self.diagnostics.mean_bid_levels,
            "mean_ask_levels": self.diagnostics.mean_ask_levels,
            "nonempty_fraction": self.diagnostics.nonempty_fraction,
            "midpoint_volatility": self.diagnostics.midpoint_volatility,
            "midpoint_range": self.diagnostics.midpoint_range,
        }

    def config_dict(self) -> dict[str, Any]:
        return self.config.as_dict()


class Simulator:
    """Run a deterministic seeded synthetic market session."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()

    def run(self, seed: int) -> SimulationResult:
        rng = random.Random(seed)
        book = OrderBook()
        background_pool = ActiveOrderPool()
        background_remaining: dict[str, int] = {}
        fair_value = self.config.initial_mid_ticks
        maker = MarketMaker(self._maker_config())
        flow_config = self._flow_config()
        next_order_number = 0

        def new_id(prefix: str) -> str:
            nonlocal next_order_number
            identifier = f"{prefix}-{next_order_number}"
            next_order_number += 1
            return identifier

        self._seed_book(book, background_pool, background_remaining, new_id)
        last_quote_mid = self._refresh_quotes(book, maker, time=0.0)
        initial_mid = self._reference_mid(book, float(fair_value))
        states: list[StateRecord] = [self._state(0.0, book, maker, initial_mid)]
        fills: list[FillRecord] = []
        events: list[EventRecord] = []
        bid_depth_totals: dict[float, float] = {}
        ask_depth_totals: dict[float, float] = {}
        depth_snapshots = 0
        now = 0.0

        for index in range(self.config.session_events):
            scheduled = sample_next_event(now, flow_config, len(background_pool), rng)
            now = scheduled.time
            pre_mid = self._reference_mid(book, states[-1].midpoint)
            trades: list[Trade] = []
            aggressor_type: AggressorType = "unknown"

            if scheduled.event_type is EventType.LIMIT_ORDER:
                side = Side.BUY if rng.random() < 0.5 else Side.SELL
                incoming = sample_background_limit_order(
                    order_id=new_id("background-limit"),
                    side=side,
                    timestamp=now,
                    best_bid_ticks=book.best_bid,
                    best_ask_ticks=book.best_ask,
                    fair_value_ticks=fair_value,
                    config=flow_config,
                    rng=rng,
                )
                trades = book.add_limit_order(
                    incoming.order_id, incoming.side, incoming.price, incoming.quantity
                )
                remainder = incoming.quantity - sum(trade.quantity for trade in trades)
                if remainder > 0:
                    background_pool.add(incoming.order_id)
                    background_remaining[incoming.order_id] = remainder
            elif scheduled.event_type is EventType.MARKET_ORDER:
                intent = sample_market_order(flow_config, fair_value, round(pre_mid), rng)
                incoming_id = new_id("background-market")
                trades = book.add_market_order(incoming_id, intent.side, intent.quantity)
                aggressor_type = "informed" if intent.informed else "uninformed"
            elif scheduled.event_type is EventType.CANCEL:
                if background_pool:
                    cancelled_id = background_pool.choose(rng)
                    book.cancel(cancelled_id)
                    background_pool.discard(cancelled_id)
                    background_remaining.pop(cancelled_id, None)
            else:
                fair_value = max(2, fair_value + sample_value_shock(flow_config, rng))

            maker_fills = self._process_trades(
                trades,
                maker,
                background_pool,
                background_remaining,
                now,
                pre_mid,
                aggressor_type,
            )
            unquoted_mid = self._reference_mid(book, pre_mid)
            missing_quote = (
                len(maker.active_quote_ids) < 2
                and abs(maker.inventory) < self.config.inventory_limit
            )
            if unquoted_mid != last_quote_mid or missing_quote:
                last_quote_mid = self._refresh_quotes(book, maker, time=now)
            post_mid = self._reference_mid(book, pre_mid)
            fills.extend(
                FillRecord(
                    time=fill.time,
                    signed_quantity=fill.signed_quantity,
                    price=fill.price,
                    pre_event_mid=fill.pre_event_mid,
                    aggressor_type=fill.aggressor_type,
                    fill_midpoint=post_mid,
                )
                for fill in maker_fills
            )
            states.append(self._state(now, book, maker, post_mid))
            if index % 10 == 0:
                self._accumulate_depth(
                    book, post_mid, bid_depth_totals, ask_depth_totals
                )
                depth_snapshots += 1
            events.append(
                EventRecord(
                    index=index,
                    time=now,
                    event_type=scheduled.event_type.value,
                    fair_value=fair_value,
                    trade_count=len(trades),
                    aggressor_type=aggressor_type,
                )
            )

        pnl = pnl_decomposition(fills, states)
        if abs(pnl.reconciliation_error) > 1e-9:
            raise AssertionError(f"PnL failed to reconcile: {pnl.reconciliation_error}")
        markouts = compute_markouts(fills, states, self.config.markout_horizons)
        return SimulationResult(
            seed=seed,
            config=self.config,
            events=tuple(events),
            fills=tuple(fills),
            states=tuple(states),
            pnl=pnl,
            diagnostics=market_diagnostics(states),
            markouts=markouts,
            markout_summary=summarize_markouts(markouts),
            max_absolute_inventory=max(abs(state.inventory) for state in states),
            depth_profile=self._depth_profile(
                bid_depth_totals, ask_depth_totals, depth_snapshots
            ),
        )

    def _flow_config(self) -> OrderFlowConfig:
        return OrderFlowConfig(
            limit_order_rate=self.config.limit_order_rate,
            market_order_rate=self.config.market_order_rate,
            cancel_rate_per_order=self.config.cancel_rate_per_order,
            value_shock_rate=self.config.value_shock_rate,
            informed_probability=self.config.informed_fraction,
            geometric_distance_probability=self.config.placement_geometric_p,
            geometric_size_probability=self.config.size_geometric_p,
            min_order_size=1,
            max_order_size=self.config.max_order_qty,
            value_shock_ticks=self.config.fundamental_shock_ticks,
        )

    def _maker_config(self) -> MarketMakerConfig:
        return MarketMakerConfig(
            gamma=self.config.inventory_aversion,
            half_spread_ticks=self.config.half_spread_ticks,
            quote_size=self.config.quote_size,
            inventory_limit=self.config.inventory_limit,
        )

    def _seed_book(
        self,
        book: OrderBook,
        pool: ActiveOrderPool,
        remaining: dict[str, int],
        new_id: Callable[[str], str],
    ) -> None:
        for level in range(self.config.seed_levels):
            for side in (Side.BUY, Side.SELL):
                price = (
                    self.config.initial_mid_ticks - level - 1
                    if side is Side.BUY
                    else self.config.initial_mid_ticks + level + 1
                )
                for _ in range(self.config.seed_orders_per_level):
                    order_id = new_id("seed")
                    book.add_limit_order(order_id, side, price, self.config.seed_order_qty)
                    pool.add(order_id)
                    remaining[order_id] = self.config.seed_order_qty

    @staticmethod
    def _process_trades(
        trades: list[Trade],
        maker: MarketMaker,
        pool: ActiveOrderPool,
        remaining: dict[str, int],
        time: float,
        pre_mid: float,
        aggressor_type: AggressorType,
    ) -> list[FillRecord]:
        maker_fills: list[FillRecord] = []
        for trade in trades:
            if trade.resting_order_id in remaining:
                left = remaining[trade.resting_order_id] - trade.quantity
                if left <= 0:
                    remaining.pop(trade.resting_order_id, None)
                    pool.discard(trade.resting_order_id)
                else:
                    remaining[trade.resting_order_id] = left
            maker_fill = maker.on_trade(trade)
            if maker_fill is not None:
                maker_fills.append(
                    FillRecord(
                        time=time,
                        signed_quantity=maker_fill.signed_quantity,
                        price=maker_fill.price,
                        pre_event_mid=pre_mid,
                        aggressor_type=aggressor_type,
                    )
                )
        return maker_fills

    @staticmethod
    def _refresh_quotes(
        book: OrderBook, maker: MarketMaker, *, time: float
    ) -> float | None:
        for order_id in maker.withdraw_quotes():
            book.cancel(order_id)
        midpoint = book.mid
        if midpoint is None:
            return None
        for order in maker.quote_orders(
            round(midpoint), time, best_bid=book.best_bid, best_ask=book.best_ask
        ):
            trades = book.add_limit_order(order.order_id, order.side, order.price, order.quantity)
            if trades:
                raise AssertionError("market-maker quote unexpectedly crossed the book")
        return midpoint

    @staticmethod
    def _reference_mid(book: OrderBook, fallback: float) -> float:
        return book.mid if book.mid is not None else fallback

    @staticmethod
    def _state(time: float, book: OrderBook, maker: MarketMaker, midpoint: float) -> StateRecord:
        bid_depth = book.depth(Side.BUY)
        ask_depth = book.depth(Side.SELL)
        best_bid = book.best_bid
        best_ask = book.best_ask
        both_sides = best_bid is not None and best_ask is not None
        maker_bid = next(
            (float(price) for _, side, price, _ in maker.active_quotes if side is Side.BUY),
            None,
        )
        maker_ask = next(
            (float(price) for _, side, price, _ in maker.active_quotes if side is Side.SELL),
            None,
        )
        return StateRecord(
            time=time,
            midpoint=midpoint,
            inventory=maker.inventory,
            cash=maker.cash,
            best_bid=float(best_bid) if both_sides and best_bid is not None else None,
            best_ask=float(best_ask) if both_sides and best_ask is not None else None,
            bid_levels=len(bid_depth),
            ask_levels=len(ask_depth),
            maker_bid=maker_bid,
            maker_ask=maker_ask,
        )

    @staticmethod
    def _accumulate_depth(
        book: OrderBook,
        midpoint: float,
        bid_totals: dict[float, float],
        ask_totals: dict[float, float],
    ) -> None:
        for price, quantity in book.depth(Side.BUY):
            distance = float(max(1, round(midpoint - price)))
            bid_totals[distance] = bid_totals.get(distance, 0.0) + quantity
        for price, quantity in book.depth(Side.SELL):
            distance = float(max(1, round(price - midpoint)))
            ask_totals[distance] = ask_totals.get(distance, 0.0) + quantity

    @staticmethod
    def _depth_profile(
        bid_totals: dict[float, float],
        ask_totals: dict[float, float],
        snapshots: int,
    ) -> tuple[tuple[float, float, float], ...]:
        if snapshots == 0:
            return ()
        distances = sorted(set(bid_totals) | set(ask_totals))
        return tuple(
            (
                distance,
                bid_totals.get(distance, 0.0) / snapshots,
                ask_totals.get(distance, 0.0) / snapshots,
            )
            for distance in distances
        )
