"""Local matching-engine throughput benchmark; it is intentionally not a CI gate.

Run with ``python benchmarks/benchmark_order_book.py`` from the repository
after installing the project in editable mode.
"""

from __future__ import annotations

from time import perf_counter

from lobmm.order_book import OrderBook, Side


def run(order_count: int = 100_000) -> None:
    """Print a reproducible, machine-dependent order-submission rate."""

    book = OrderBook()
    started = perf_counter()
    for index in range(order_count):
        side = Side.BUY if index % 2 == 0 else Side.SELL
        price = 9_900 - (index % 20) if side is Side.BUY else 10_100 + (index % 20)
        book.add_limit_order(f"rest-{index}", side, price, 10)
    elapsed = perf_counter() - started
    rate = order_count / elapsed
    print(f"submitted {order_count:,} resting orders in {elapsed:.3f}s ({rate:,.0f}/s)")


if __name__ == "__main__":
    run()
