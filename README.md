# Limit Order Book & Market-Making Simulator

> Work in progress. Results and performance claims will be published only after the
> simulator, tests, and repeated experiments are complete.

A Python 3.12 project for learning how price-time-priority matching, adverse
selection, and inventory-aware quoting interact in a simulated electronic market.

## Status

The repository is being built in five guided milestones:

1. Matching engine and invariants
2. Continuous-time synthetic order flow
3. Inventory-aware market maker
4. PnL decomposition and markouts
5. Reproducible experiments and report

## Development setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
pytest
```

## Scope

V1 uses synthetic order flow and a linear inventory-skew strategy. It does not
claim live trading performance or results from historical market data.

