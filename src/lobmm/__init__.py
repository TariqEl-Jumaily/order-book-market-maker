"""Limit order book and market-making simulator."""

from .config import SimulationConfig
from .market_maker import MarketMaker, MarketMakerConfig
from .order_book import Order, OrderBook, Side, Trade
from .simulation import SimulationResult, Simulator

__version__ = "0.1.0"

__all__ = [
    "MarketMaker",
    "MarketMakerConfig",
    "Order",
    "OrderBook",
    "Side",
    "SimulationConfig",
    "SimulationResult",
    "Simulator",
    "Trade",
]
