# The beginner's study book for the order book and market maker project

This book explains the project from the beginning. You do not need prior knowledge of trading, market making, statistics, or large Python programs.

The aim is not to help you memorize impressive words. The aim is to help you understand the system well enough to explain it in your own language, change it safely, and answer follow-up questions without guessing.

The project is a simulation. It does not trade real money, connect to an exchange, or prove that a strategy would make money in a real market.

## Contents

1. [The project in plain English](#1-the-project-in-plain-english)
2. [How a financial market works](#2-how-a-financial-market-works)
3. [What an order book is](#3-what-an-order-book-is)
4. [How orders match](#4-how-orders-match)
5. [What a market maker does](#5-what-a-market-maker-does)
6. [Inventory risk and quote skew](#6-inventory-risk-and-quote-skew)
7. [Adverse selection and markouts](#7-adverse-selection-and-markouts)
8. [How the simulated market creates activity](#8-how-the-simulated-market-creates-activity)
9. [How one simulation runs](#9-how-one-simulation-runs)
10. [Cash, inventory, and PnL](#10-cash-inventory-and-pnl)
11. [What each code file does](#11-what-each-code-file-does)
12. [The Python ideas used in the project](#12-the-python-ideas-used-in-the-project)
13. [The configuration file](#13-the-configuration-file)
14. [How to run the program](#14-how-to-run-the-program)
15. [What the output files contain](#15-what-the-output-files-contain)
16. [How the experiments work](#16-how-the-experiments-work)
17. [What the results mean](#17-what-the-results-mean)
18. [How to read the seven figures](#18-how-to-read-the-seven-figures)
19. [Testing, coverage, CI, and GitHub](#19-testing-coverage-ci-and-github)
20. [What the project does today](#20-what-the-project-does-today)
21. [What the project does not do](#21-what-the-project-does-not-do)
22. [What we want to add next](#22-what-we-want-to-add-next)
23. [How the project can read on your CV](#23-how-the-project-can-read-on-your-cv)
24. [Interview questions and simple answers](#24-interview-questions-and-simple-answers)
25. [A five-session study plan](#25-a-five-session-study-plan)
26. [Practice exercises](#26-practice-exercises)
27. [Glossary](#27-glossary)
28. [One-page revision sheet](#28-one-page-revision-sheet)

## 1. The project in plain English

Imagine a small fictional stock exchange inside your computer.

People send instructions saying things like:

- "I will buy 5 units if the price is 99 or lower."
- "I will sell 3 units if the price is 101 or higher."
- "Buy 4 units immediately at the best available price."
- "Cancel the order I sent earlier."

The program stores those instructions in an order book. When a buyer and seller are willing to trade at compatible prices, the program matches them and records a trade.

The program also controls a fictional market maker. The market maker continuously offers to buy and sell. It tries to earn the gap between its buying and selling prices, but it also tries to avoid building a dangerously large position.

The project studies one question:

> Can moving quotes in response to inventory reduce risk without giving up too much trading revenue?

The experiment says yes within this simulated model. Compared with no inventory adjustment, the chosen inventory adjustment reduced terminal-PnL standard deviation by 82.5% and mean maximum absolute inventory by 74.3%. Mean gross spread capture fell by 10.4%.

Those numbers come from 200 simulated sessions at each parameter setting. They are not real trading returns.

## 2. How a financial market works

A financial market brings buyers and sellers together. The item being traded is called an asset or instrument. A share in a company is one example. A currency, bond, future, or option is another.

This simulator does not try to model a particular real stock. It models one generic instrument with prices measured in ticks.

### Buyers and sellers

A buyer wants to acquire the asset. A seller wants to give up the asset in return for cash.

They often disagree about price:

- A buyer may be willing to pay 99.
- A seller may refuse to accept less than 101.

No trade happens yet because the buyer's maximum price is below the seller's minimum price.

### Bid and ask

A bid is an offer to buy.

An ask is an offer to sell. You may also hear the word offer used in place of ask.

The highest current bid is the best bid. It is the most any visible buyer is offering.

The lowest current ask is the best ask. It is the least any visible seller is asking for.

For example:

```text
Best bid: 99
Best ask: 101
```

### Spread

The spread is the distance between the best ask and best bid:

```text
spread = best ask - best bid
spread = 101 - 99 = 2 ticks
```

A narrow spread means the best buyer and seller are close to agreeing. A wide spread means they are further apart.

### Midpoint

The midpoint is halfway between the best bid and best ask:

```text
midpoint = (best bid + best ask) / 2
midpoint = (99 + 101) / 2 = 100
```

The midpoint is not necessarily a price at which someone traded. It is a reference value based on the best visible quotes.

### Tick

A tick is the smallest price step allowed by the model or market.

If one tick represents one penny, these stored prices mean:

```text
10000 ticks = GBP 100.00
10001 ticks = GBP 100.01
```

The program stores prices as whole-number ticks. It avoids floating-point prices because values such as `0.1` cannot always be represented exactly inside a computer. Exact tick values make price comparisons safer.

### Quantity

Quantity is the number of units in an order or trade.

An instruction to buy 5 units at 99 has:

```text
side     = buy
price    = 99
quantity = 5
```

### Liquidity

Liquidity describes how easy it is to trade without moving the price too much.

A book with many orders at several nearby prices has more displayed liquidity than an almost empty book. A large market order can still use up that liquidity and move through several price levels.

## 3. What an order book is

An order book is a live list of unfilled buy and sell orders.

A simplified book might look like this:

| Sell side | Quantity |
|---:|---:|
| 103 | 8 |
| 102 | 4 |
| 101 | 6 |
| **Spread** | **2 ticks** |
| 99 | 5 |
| 98 | 7 |
| 97 | 10 |
| Buy side | Quantity |

The best ask is 101 because it is the cheapest sell order. The best bid is 99 because it is the most expensive buy order.

### Price levels

A price level groups all orders at the same price.

Suppose three buyers submit:

```text
Order A: buy 2 at 99
Order B: buy 5 at 99
Order C: buy 3 at 98
```

The book has two buy price levels:

```text
99: total quantity 7
98: total quantity 3
```

The program still remembers A and B separately because their arrival order matters.

### Depth

Depth is the amount of resting quantity available at different prices.

The touch means the best bid and best ask. Moving away from the touch takes you to less competitive price levels.

A depth profile asks questions such as:

- How much quantity usually rests one tick from the midpoint?
- How much rests five ticks away?
- Does liquidity thin out as prices move further away?

### Resting order

A resting order is an unfilled order waiting in the book.

If you offer to buy at 99 while the cheapest seller wants 101, your order cannot trade immediately. It rests on the buy side.

## 4. How orders match

The matching engine is the exchange rulebook. It decides which orders trade, at what price, and in what sequence.

### Limit order

A limit order controls the worst price you will accept.

Examples:

- A buy limit at 100 means: buy at 100 or lower, but never above 100.
- A sell limit at 100 means: sell at 100 or higher, but never below 100.

A limit order may rest, trade immediately, or do both.

### Market order

A market order asks to trade immediately at the best available prices. It controls quantity but not price.

This makes market orders aggressive. They take liquidity that is already resting in the book.

If the book does not contain enough quantity, the simulator fills what it can and discards the unfilled market-order remainder.

### Price priority

Better prices execute first.

For an incoming buyer, the cheapest seller executes first. For an incoming seller, the most expensive buyer executes first.

Suppose the sell side contains:

```text
Sell 4 at 101
Sell 8 at 102
```

An incoming market buy for 5 units will:

1. Buy 4 at 101.
2. Buy 1 at 102.

It cannot buy at 102 before using the cheaper 101 order.

### Time priority and FIFO

When several orders have the same price, the earliest one trades first. This is time priority.

FIFO means "first in, first out." It is the queue rule used at each price level.

Suppose these orders arrive in order:

```text
10:00:00  Order A sells 3 at 101
10:00:01  Order B sells 4 at 101
```

An incoming buy for 5 at 101 fills:

1. All 3 units from A.
2. Then 2 units from B.

Order B keeps 2 units resting.

### Partial fill

A partial fill happens when only part of an order trades.

If an order sells 10 units but an incoming buyer wants only 4, the seller has:

```text
4 units filled
6 units still resting
```

### Walking the book

A large market order walks the book when it consumes several price levels.

Suppose asks are:

```text
3 units at 101
4 units at 102
5 units at 103
```

A market buy for 10 units executes:

```text
3 at 101
4 at 102
3 at 103
```

The buyer receives all 10 units, but the average price is worse than the original best ask. This is one reason large trades can move markets.

### Crossing limit order

A buy limit crosses the book if its limit price reaches or exceeds the best ask. A sell limit crosses if its price reaches or falls below the best bid.

Suppose the best ask is 101. A buy limit for 8 at 102 is willing to pay up to 102, so it trades with available sellers at 101 and then 102. Any remainder rests only if it no longer crosses the opposite side.

The simulator never leaves a crossed book resting. After matching, the best bid must remain below the best ask whenever both sides exist.

### Cancellation

A cancellation removes an active resting order before it trades.

Exchanges process huge numbers of cancellations because traders frequently replace stale quotes. The program keeps a direct order lookup so it does not have to scan every order to find the one being cancelled.

## 5. What a market maker does

A market maker continuously offers both a bid and an ask.

Example:

```text
Market maker bid: buy at 99
Market maker ask: sell at 101
Midpoint: 100
```

The market maker provides liquidity because other traders can immediately sell to its bid or buy from its ask.

### The basic source of revenue

If the maker buys one unit at 99 and later sells it at 101, it earns 2 ticks before fees and other risks.

This is the intuitive idea behind spread capture. Real accounting is more careful because the market price may move while the maker holds inventory.

### Quote

A quote is a displayed price and quantity at which the maker is willing to trade.

The project uses a fixed quote size of 5 units in its baseline configuration.

### Fill

A fill is the part of an order that successfully trades.

If the maker offers to sell 5 and someone buys 2, the maker receives a 2-unit fill and still has 3 units available unless it cancels and replaces the quote.

### Why market making is not free money

The maker may buy just before the price falls or sell just before the price rises. It can also accumulate a large position on one side.

The spread is compensation for taking these risks. It is not a guaranteed profit.

## 6. Inventory risk and quote skew

Inventory is the maker's current position.

The project uses this sign convention:

```text
Positive inventory = long = owns units
Negative inventory = short = owes or has sold units
```

### Long and short

If the maker buys 10 and sells 4, its inventory is:

```text
inventory = 10 - 4 = +6
```

It is long 6 units.

If it sells 10 and buys 4, its inventory is `-6`. It is short 6 units.

### Why inventory creates risk

A long position loses value when the midpoint falls. A short position loses value when the midpoint rises.

Even if average inventory is near zero across many sessions, individual sessions can reach large positive or negative positions. Average inventory therefore does not measure the full risk.

### Symmetric quoting

A simple maker quotes the same distance on both sides of the midpoint:

```text
midpoint = 100
half-spread = 1
bid = 99
ask = 101
```

This ignores inventory. If buyers repeatedly hit the ask, the maker becomes increasingly short. If sellers repeatedly hit the bid, the maker becomes increasingly long.

### Reservation price

The reservation price is the center around which the market maker wants to quote after considering inventory.

The project uses:

```text
reservation price = midpoint - gamma * inventory
```

Gamma, written as the Greek letter gamma in finance texts, controls how strongly inventory moves the quotes.

### Worked skew example

Suppose:

```text
midpoint = 100
inventory = +10
gamma = 0.1
half-spread = 1
```

Then:

```text
reservation price = 100 - 0.1 * 10 = 99
bid = 99 - 1 = 98
ask = 99 + 1 = 100
```

Before the skew, the maker might quote 99 and 101. After becoming long, it moves both quotes down to 98 and 100.

That does two useful things:

- The lower bid makes another purchase less likely.
- The lower ask makes a sale more likely.

Both effects push inventory back toward zero.

### What happens when gamma changes

`gamma = 0` means no inventory skew. Inventory does not affect quotes.

A small positive gamma gently moves quotes. A larger gamma reacts more strongly.

Too little skew can leave the maker with large inventory. Too much skew can move quotes so far that the maker loses spread-capture opportunities or trades at unattractive prices.

The experiment searches for this trade-off.

### Inventory limit

The baseline inventory limit is 100 units.

At the positive limit, the maker stops placing a bid that could increase its long position. At the negative limit, it stops placing an ask that could increase its short position.

The limit is a safety rule. It does not remove inventory risk before the limit is reached.

## 7. Adverse selection and markouts

Adverse selection happens when the person trading against you has better information or better timing, so the price tends to move against you after the trade.

### A simple example

Your market maker sells at 101. Immediately afterwards, the midpoint rises from 100 to 105.

Selling at 101 now looks poor because the asset became more valuable. The buyer may have known or correctly anticipated that prices were about to rise.

The reverse can happen when the maker buys just before a fall.

### Informed and uninformed flow

The model labels 20% of market orders as informed.

The simulator has a hidden latent fair value. When that value sits above the visible midpoint, an informed trader buys. When it sits below, an informed trader sells. The order size can grow with the size of the gap.

Uninformed orders choose direction randomly.

This is a simplified mechanism. It is designed to produce a controlled difference between informed and uninformed fills. It does not claim to reproduce how real traders obtain information.

### Latent fair value

Latent means hidden or not directly observed.

Fair value is the model's hidden reference for where price pressure should point. Independent shocks move it up or down during a session.

The public order book does not instantly jump to fair value. Informed orders trade in the direction of the gap and can move the visible book toward it.

### Markout

A markout measures where the midpoint moves after a fill.

The program checks the midpoint after 1, 5, 10, 30, and 60 units of simulation time.

For a maker buy:

```text
markout = future midpoint - fill-time midpoint
```

For a maker sell:

```text
markout = fill-time midpoint - future midpoint
```

This sign convention makes interpretation consistent:

```text
Positive markout = price moved in the maker's favor
Negative markout = price moved against the maker
```

### Worked markout example

The maker buys while the fill-time midpoint is 100.

At the 10-unit horizon, the midpoint is 97:

```text
buy markout = 97 - 100 = -3 ticks
```

The maker suffered adverse selection.

If the maker had sold at the same starting midpoint and price later reached 97:

```text
sell markout = 100 - 97 = +3 ticks
```

The move favored the seller.

### What the project found

In the documented seed-42 session, the 30-unit mean markout was:

```text
Informed fills:   -7.09 ticks per unit
Uninformed fills: +2.04 ticks per unit
```

That is evidence that the model's informed-flow mechanism behaves as intended. It is evidence about the simulator, not a measurement from a real exchange.

## 8. How the simulated market creates activity

The program needs orders from other participants so the market maker has something to trade against. These participants are generated by a stochastic order-flow model.

Stochastic means partly governed by randomness.

### Four event types

The simulator produces:

1. Limit-order arrivals
2. Market-order arrivals
3. Cancellations
4. Latent-value shocks

Each event changes the book or the hidden fair value.

### Poisson process

A Poisson process is a common model for random event arrivals through time.

It assumes events arrive independently at an average rate. For example, a market-order rate of 10 means an average intensity of 10 arrivals per unit of simulation time. It does not mean exactly 10 arrive in every unit.

Some intervals will be quiet. Others will be busy.

### Rate and hazard

In this project, rate and hazard describe how quickly an event is expected to occur.

A larger hazard makes that event more likely to be the next event and shortens its typical waiting time.

The baseline hazards include:

```text
Limit orders:  12.0
Market orders: 10.0
Value shocks:   0.8
Cancellation:   0.05 * active background orders
```

Cancellation is different because its total hazard grows with the number of active background orders. If the book fills with many orders, more of them are exposed to cancellation.

### Exponential waiting time

The time to the next event is sampled from an exponential distribution.

The simulator adds the current hazards to get one total hazard. It then:

1. Samples how long until something happens.
2. Chooses which event happened, weighted by the individual hazards.

This creates continuous event time. Events do not need to happen at fixed whole-number steps.

### Geometric distribution

Background limit orders need a distance from the current best prices. Order quantities also need a size.

The project uses bounded geometric distributions. They make small distances and small orders more common while still allowing occasional larger values.

### Random seed

A random seed is the starting value for a pseudo-random number generator.

Computers generate sequences that look random but are reproducible from the same seed. If the code, configuration, and seed stay the same, the simulation produces the same events and results.

This helps with:

- Debugging
- Fair strategy comparisons
- Reproducing figures
- Proving that a reported result can be rerun

## 9. How one simulation runs

The baseline session contains 5,000 external events.

### Starting the book

The simulator starts around 10,000 ticks. With the configured tick value of `0.01`, that can be displayed as 100.00 currency units.

It creates 10 seeded levels on each side. Each level starts with 2 orders of 3 units.

This prevents the first market order from seeing an empty book.

### Event loop

For each event, the program follows this sequence:

1. Calculate the current event hazards.
2. Sample the next event time and type.
3. Record the midpoint before the event.
4. Process the limit order, market order, cancellation, or fair-value shock.
5. Record any trades.
6. Send market-maker fills to its accounting system.
7. Update cash and inventory.
8. Cancel and replace maker quotes when the midpoint changes or a quote disappears.
9. Record the new book and strategy state.
10. Continue until 5,000 events have occurred.

### Important safety checks

The simulator checks that:

- Order IDs are not reused.
- Prices and quantities are valid.
- A crossed book does not remain after matching.
- Inventory does not breach the configured limit.
- Time moves forward.
- The same seed reproduces the same result.
- PnL components reconcile exactly within the chosen tolerance.

## 10. Cash, inventory, and PnL

PnL means profit and loss.

The project measures values in ticks times quantity. It does not add a currency symbol because this is a generic simulated instrument.

### Signed quantity

The accounting convention is:

```text
Buy  quantity = positive
Sell quantity = negative
```

If the maker buys 5, signed quantity is `+5`. If it sells 5, signed quantity is `-5`.

### Cash accounting

A purchase uses cash:

```text
cash change = -signed quantity * fill price
```

Buy 5 at 99:

```text
cash change = -(+5) * 99 = -495
inventory change = +5
```

Sell 5 at 101:

```text
cash change = -(-5) * 101 = +505
inventory change = -5
```

### Marked-to-market PnL

An unsold position still has value. Marking to market values current inventory at the latest midpoint:

```text
total PnL = cash + inventory * current midpoint
```

Suppose the maker buys 5 at 99 and the midpoint is 100:

```text
cash = -495
inventory = +5
inventory value = 5 * 100 = 500
total PnL = -495 + 500 = +5
```

### Spread capture

Spread capture measures execution edge against the pre-event midpoint:

```text
spread capture = signed quantity * (pre-event midpoint - fill price)
```

For a buy of 5 at 99 with midpoint 100:

```text
spread capture = +5 * (100 - 99) = +5
```

For a sell of 5 at 101 with midpoint 100:

```text
spread capture = -5 * (100 - 101) = +5
```

Both fills earn positive execution edge.

### Inventory PnL

Inventory PnL measures the effect of midpoint changes while the maker holds a position:

```text
inventory PnL = post-event inventory * midpoint change
```

If the maker owns 5 units and the midpoint falls from 100 to 98:

```text
inventory PnL = 5 * (98 - 100) = -10
```

### Full worked example

Start with no cash and no inventory.

The maker buys 5 at 99 while the midpoint is 100:

```text
cash = -495
inventory = +5
spread capture = +5
```

The midpoint then falls to 98:

```text
inventory PnL = 5 * (98 - 100) = -10
total PnL = -495 + 5 * 98 = -5
```

The maker later sells all 5 at 99 while the midpoint is 98:

```text
cash received = +495
final cash = 0
final inventory = 0
second spread capture = -5 * (98 - 99) = +5
```

Final decomposition:

```text
total spread capture = +10
inventory PnL = -10
total PnL = 0
```

The example shows why spread capture alone can be misleading. The maker earned good prices at each fill but lost the same amount while holding inventory.

### Reconciliation

The simulator checks:

```text
total PnL = spread capture + inventory PnL
```

The allowed numerical difference is `1e-9`, which is 0.000000001. If the identity fails by more than this tolerance, the simulation raises an error.

## 11. What each code file does

The main code lives in `src/lobmm/`.

### `order_book.py`

This is the matching engine.

It defines:

- `Side`: buy or sell
- `Order`: order ID, side, price, and remaining quantity
- `Trade`: the record of a match
- `PriceLevel`: the FIFO queue at one price
- `OrderBook`: the complete buy and sell book

It handles limit orders, market orders, cancellations, partial fills, depth, and best prices.

### `order_flow.py`

This generates the fictional outside market.

It defines event types, event hazards, informed and uninformed market-order intentions, fair-value shocks, geometric order placement, and the active background-order pool used for cancellation.

### `market_maker.py`

This stores the maker's strategy and accounting state.

It calculates reservation prices and desired quotes, creates quote orders, processes fills, updates cash, updates inventory, and enforces the inventory limit.

### `simulation.py`

This connects the matching engine, order flow, and market maker.

It creates the starting book, runs the event loop, records events and states, calculates diagnostics, checks PnL reconciliation, and returns one `SimulationResult`.

### `analytics.py`

This turns raw simulation records into financial and statistical measures.

It calculates PnL decomposition, markouts, market-health diagnostics, bootstrap confidence intervals, and aggregated sweep summaries.

### `experiments.py`

This runs many simulations and creates reports.

It performs parameter sweeps, uses multiple processor cores, writes CSV and JSON files, and produces the seven headline figures.

### `config.py`

This defines every configurable simulation parameter. It validates values and reads the TOML configuration file.

### `cli.py`

CLI means command-line interface. This file turns terminal commands such as `simulate` and `report` into Python function calls.

## 12. The Python ideas used in the project

You do not need to master every Python feature before reading the code. Learn these ideas first.

### Variable

A variable gives a name to a value:

```python
inventory = 5
```

### Function

A function is a reusable operation. It receives inputs and may return an output.

```python
def spread(best_bid, best_ask):
    return best_ask - best_bid
```

### Class and object

A class describes a type of thing. An object is one instance of that type.

`OrderBook` is a class. The simulator creates one particular order-book object for a session.

### Method

A method is a function attached to a class. `book.cancel(order_id)` calls the `cancel` method on one book object.

### Dataclass

A dataclass is a convenient Python class for storing related fields. `Order` and `Trade` are examples.

### Enum

An enum provides a limited set of named values. `Side.BUY` and `Side.SELL` prevent arbitrary side strings from entering the matching engine.

### List

A list is an ordered collection that can change.

### Tuple

A tuple is an ordered collection that is usually treated as fixed.

### Dictionary

A dictionary maps keys to values:

```python
order_id -> order
price -> price level
```

Dictionaries usually provide average constant-time lookup by key.

### Type hint

A type hint records the expected kind of value:

```python
price: int
```

The program uses mypy to check these hints.

### Module and package

A module is one Python file. A package is a directory of related modules. `lobmm` is the package.

### Exception

An exception stops normal execution when something invalid happens. A duplicate order ID or negative quantity raises an exception instead of silently corrupting the book.

### Assertion

An assertion states something that must be true. The simulation asserts that PnL reconciles.

## 13. The configuration file

The baseline configuration is in `configs/baseline.toml`.

TOML is a human-readable configuration format containing names and values.

| Parameter | Current value | Plain-English meaning |
|---|---:|---|
| `initial_mid_ticks` | 10000 | Starting price reference |
| `tick_value` | 0.01 | Display value of one tick |
| `seed_levels` | 10 | Starting price levels per side |
| `seed_orders_per_level` | 2 | Starting orders at each level |
| `seed_order_qty` | 3 | Quantity in each starting order |
| `limit_order_rate` | 12.0 | Passive-order arrival intensity |
| `market_order_rate` | 10.0 | Aggressive-order arrival intensity |
| `cancel_rate_per_order` | 0.05 | Cancellation hazard for each background order |
| `value_shock_rate` | 0.8 | Latent-value shock intensity |
| `informed_fraction` | 0.2 | Fraction of market orders labelled informed |
| `placement_geometric_p` | 0.45 | Shape of limit-order distance distribution |
| `size_geometric_p` | 0.2 | Shape of order-size distribution |
| `max_order_qty` | 15 | Largest generated background order |
| `fundamental_shock_ticks` | 4 | Size of each fair-value shock |
| `session_events` | 5000 | External events in one session |
| `half_spread_ticks` | 1 | Distance from quote center to each maker quote |
| `inventory_aversion` | 0.1 | Gamma used by the baseline maker |
| `quote_size` | 5 | Quantity in each maker quote |
| `inventory_limit` | 100 | Maximum absolute maker inventory |
| `markout_horizons` | 1, 5, 10, 30, 60 | Future times checked after fills |

Change one parameter at a time while learning. If you change several at once, you may not know which change caused the result.

## 14. How to run the program

Open Terminal and move into the repository:

```bash
cd /Users/Tariq/order-book-market-maker
```

Activate the existing virtual environment:

```bash
source .venv/bin/activate
```

Your prompt should now show `(.venv)`.

### Run the tests

```bash
pytest
```

The expected result is 47 passing tests and about 94% statement coverage.

### Run one session

```bash
python -m lobmm simulate --seed 42
```

### Run a shorter practice session

```bash
python -m lobmm simulate \
  --seed 7 \
  --events 500 \
  --output results/raw/practice-seed-7
```

### Run only the inventory-aversion experiment

```bash
python -m lobmm gamma-sweep --runs 200 --workers 8
```

### Run only the spread experiment

```bash
python -m lobmm spread-sweep --runs 200 --workers 8
```

### Rebuild the full report

```bash
python -m lobmm report --runs 200 --workers 8
```

The full command runs 2,200 sweep sessions, plus two representative sessions used for detailed plots: 5 spread settings and 6 gamma settings, each with 200 seeds. It can take several minutes.

### Virtual environment

A virtual environment is an isolated Python installation for one project. It stops this project's packages from interfering with other Python projects.

If `.venv` is missing, rebuild it:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## 15. What the output files contain

A single saved run creates:

```text
results/raw/baseline-seed-42/
  config.json
  events.csv
  fills.csv
  markouts.csv
  states.csv
  summary.json
```

### `config.json`

The exact parameters used for the run. This makes the result reproducible.

### `events.csv`

One row for each external event. It includes event number, time, type, latent fair value, trade count, and aggressor classification.

### `fills.csv`

One row for each market-maker fill. It includes time, signed quantity, price, reference midpoint, aggressor type, and fill-time midpoint.

### `states.csv`

One row for the market state after each event. It includes midpoint, maker inventory, cash, best prices, number of levels, and maker quotes.

### `markouts.csv`

Post-fill midpoint movement at each available horizon.

### `summary.json`

A short run-level summary containing total PnL, spread capture, inventory PnL, fill count, inventory measures, spread statistics, duration, and midpoint behavior.

### CSV and JSON

CSV means comma-separated values. It is a simple table format that Excel can open.

JSON stores named fields and nested data. It is useful for programs and still readable by people.

## 16. How the experiments work

A single session can be lucky or unlucky. A strategy should not be judged from one path.

### Parameter sweep

A parameter sweep runs the simulator repeatedly while changing one parameter.

The gamma sweep uses:

```text
0, 0.025, 0.05, 0.1, 0.2, 0.4
```

The spread sweep uses:

```text
1, 2, 3, 4, 5 ticks
```

### Common random seeds

Every setting uses the same 200 seed numbers.

Seed 17 under `gamma = 0` faces the same pseudo-random stream as seed 17 under `gamma = 0.1`. The strategy changes, but the source of randomness begins from the same point.

This reduces unnecessary comparison noise.

### Parallel processing

`--workers 8` allows up to eight simulation jobs to run at the same time on separate processor workers. It changes speed, not the mathematical result.

### Mean

The mean is the arithmetic average:

```text
mean = sum of observations / number of observations
```

### Variance and standard deviation

Variance measures how widely observations spread around their mean. Standard deviation is the square root of variance and uses the same units as the original measurement.

A strategy with a lower PnL standard deviation has more consistent terminal outcomes in this model.

Lower standard deviation is not automatically better. A strategy could have very consistent losses. Mean and risk must be considered together.

### Mean divided by standard deviation

The report includes mean PnL divided by PnL standard deviation as a simple risk-adjusted comparison.

It is not an annualized Sharpe ratio. The sessions are synthetic and do not represent calendar return periods.

### Bootstrap confidence interval

Bootstrapping repeatedly resamples the observed session results with replacement. It builds a distribution of possible sample means without assuming a particular bell-curve formula.

The report calculates a 95% percentile-bootstrap confidence interval for each mean.

This interval describes uncertainty in the estimated mean within the simulation experiment. It does not cover errors caused by unrealistic model assumptions.

## 17. What the results mean

### Inventory-aversion result

The main comparison is `gamma = 0` versus `gamma = 0.1` across 200 sessions each.

| Metric | Gamma 0 | Gamma 0.1 | Change |
|---|---:|---:|---:|
| Terminal-PnL standard deviation | 2,897 ticks | 506 ticks | 82.5% lower |
| Mean gross spread capture | 3,861 ticks | 3,460 ticks | 10.4% lower |
| Mean maximum absolute inventory | 100 units | 25.7 units | 74.3% lower |
| Mean terminal PnL | -5,310 ticks | 389 ticks | 5,699 ticks higher |
| Mean divided by standard deviation | -1.83 | 0.77 | Improved |

The no-skew strategy reached the 100-unit inventory limit in every tested session. Its inventory exposure created large PnL losses and high outcome variability.

At `gamma = 0.1`, the maker gave up some gross execution edge, but inventory stayed much closer to zero. The reduction in inventory risk was much larger than the reduction in spread capture.

This is the project's strongest result.

### Why gamma 0.4 is not automatically best

Higher gamma keeps reducing mean maximum absolute inventory, but it also moves quotes more aggressively.

At `gamma = 0.4`, mean PnL falls to about `-580` ticks even though PnL standard deviation is lower than at `gamma = 0.1`. Strong risk aversion can damage average performance.

The goal is not to minimize inventory at any cost. It is to balance inventory risk against trading revenue.

### Spread-width result

As half-spread increases from 1 to 5 ticks:

- Mean fill count falls from about 837 to 280.
- Mean terminal PnL rises from about 389 to 1,736 ticks.

The expected teaching story was a hump: very tight quotes trade too often at poor prices, while very wide quotes barely trade. The tested range did not produce that hump. PnL kept rising through 5 ticks.

This may mean the range is too narrow or the simulated flow fills wide quotes too easily. The result is kept and documented. The model was not retuned to force the expected shape.

### Why honest negative results matter

An experiment tests a claim. It does not guarantee the answer you hoped for.

In an interview, you can say:

> I expected an interior optimum, but within one to five ticks PnL continued to rise while fills fell. That suggests my order-flow model does not penalize wide quotes enough, or the sweep needs a wider range. I reported the result instead of tuning the model until it matched my expectation.

That answer shows judgment and honesty.

## 18. How to read the seven figures

### 1. Depth profile

File: `results/figures/01-depth-profile.png`

The horizontal axis is distance from the midpoint. The vertical axis is average resting quantity.

You should look for liquidity concentrated near the midpoint and thinning further away. The current seed also shows side-to-side asymmetry and a long bid-side tail. That is a property of the simulated path, not a universal market fact.

### 2. Midpoint and market-maker quotes

File: `results/figures/02-mid-and-quotes.png`

The midpoint line shows the visible price reference through time. The maker bid and ask sit around a center adjusted for inventory.

When the quote pair shifts relative to the midpoint, inventory skew is acting.

### 3. Spread sweep

File: `results/figures/03-spread-sweep.png`

The blue line is mean terminal PnL. The red line is mean fill count.

Fill count falls as quotes widen. PnL rises throughout the tested range, which is the unresolved result described above.

### 4. Inventory-aversion sweep

File: `results/figures/04-inventory-aversion.png`

The purple line is terminal-PnL standard deviation. It falls sharply as gamma first moves above zero.

The green line is mean gross spread capture. It falls more gradually.

This visual contains the project's main conclusion: a modest inventory response removes a large amount of PnL variability for a smaller reduction in spread capture.

### 5. Inventory distribution

File: `results/figures/05-inventory-distribution.png`

The unskewed distribution spreads widely and reaches the limits. The `gamma = 0.1` distribution is tightly concentrated around zero.

This is an intuitive picture of inventory control.

### 6. Markout curves

File: `results/figures/06-markout-curves.png`

The informed curve is negative. The uninformed curve is near zero or positive in the representative session.

The gap shows that fills against informed flow are more toxic to the maker.

### 7. PnL decomposition

File: `results/figures/07-pnl-decomposition.png`

Spread capture trends upward as the maker earns execution edge. Inventory PnL is negative in the representative path. Total PnL is the sum of those two lines.

The graph shows that good spread capture can be partly or mostly offset by holding inventory while prices move.

## 19. Testing, coverage, CI, and GitHub

### Test

A test runs a small scenario and checks the result.

One test places orders at different prices and confirms the better price fills first. Another places two orders at the same price and confirms FIFO order.

Tests do not prove that every possible bug is absent. They provide repeatable evidence for the behaviors they cover.

### Unit test

A unit test checks one small component, such as cancellation or partial-fill accounting.

### Integration test

An integration test checks several components working together, such as order flow, matching, market-maker fills, accounting, and saved reports.

### Coverage

Statement coverage is the percentage of executable code lines reached by the test suite.

The project currently reports about 94% statement coverage. High coverage is useful, but it does not guarantee that the assertions are intelligent. The content of the tests still matters.

### Ruff

Ruff checks Python style and common mistakes.

### Mypy

Mypy checks type hints. It can catch cases where a function expects one kind of value but receives another.

### Continuous integration

Continuous integration, usually shortened to CI, runs automated checks on GitHub whenever code is pushed.

This repository's CI installs Python 3.12 and runs:

```text
Ruff
Mypy
Pytest with a 90% coverage requirement
```

The green badge in the README means the latest workflow passed.

### Git and GitHub

Git records versions of the project as commits. It lets you see what changed and return to earlier work.

GitHub hosts the repository online. Recruiters can inspect the code, tests, figures, commit history, and CI results.

The public repository is:

`https://github.com/TariqEl-Jumaily/order-book-market-maker`

## 20. What the project does today

The current version can:

- Store buy and sell limit orders at integer prices.
- Match trades using price priority and FIFO time priority.
- Process market orders across several levels.
- Handle partial fills and cancellations.
- Reject invalid prices, quantities, sides, and reused order IDs.
- Generate continuous-time limit orders, market orders, cancellations, and value shocks.
- Separate informed and uninformed market-order flow.
- Maintain an efficient pool of cancellable background orders.
- Run a linear inventory-skew market maker.
- Enforce a hard inventory limit.
- Track maker cash, inventory, fills, quotes, and marked-to-market PnL.
- Reconcile spread capture and inventory PnL with total PnL.
- Calculate multi-horizon markouts.
- Calculate market diagnostics such as spread, depth, midpoint range, and non-empty-book fraction.
- Reproduce a session from its seed and configuration.
- Run spread and gamma sweeps using common seeds.
- Run experiments in parallel.
- Calculate bootstrap confidence intervals.
- Save CSV and JSON evidence.
- Generate seven report figures.
- Run 47 tests with about 94% coverage.
- Run automatic CI checks on GitHub.

## 21. What the project does not do

The current version does not:

- Connect to a live exchange.
- Place real orders.
- Use real money.
- Replay historical market data.
- Estimate real trading profitability.
- Model exchange fees or maker rebates.
- Model network or processing latency.
- Model a precise queue position for the maker within real exchange messages.
- Model traders learning or changing strategy.
- Reproduce order-flow autocorrelation found in real markets.
- Model fat-tailed price changes in a validated empirical way.
- Implement Avellaneda-Stoikov quoting.
- Use C++ for the matching engine.
- Include a browser dashboard.

Do not claim any of these features in a CV or interview.

## 22. What we want to add next

The order matters. Validation is more useful than adding advanced names without evidence.

### Step 1: interactive learning notebook

A Jupyter notebook would let you create orders one cell at a time, display the book, run a short session, and inspect fills without using the terminal for every step.

This is the best next feature for learning.

### Step 2: aggregate markouts across many sessions

The current headline markout graph uses the representative seed-42 run. The next report should pool or summarize markouts across 200 sessions and add uncertainty intervals.

This would make the adverse-selection result comparable in strength to the gamma sweep.

### Step 3: widen the spread sweep

Testing half-spreads beyond 5 ticks would show whether the PnL curve eventually turns down. If it does not, the fill mechanism needs investigation.

### Step 4: fees and rebates

Exchanges may charge a trader for taking liquidity and pay a rebate for providing it. These amounts can change whether a small spread is profitable.

### Step 5: latency

Latency is the delay between deciding to change a quote and the exchange processing that change.

With latency, a stale quote can remain exposed while better-informed traders hit it. This usually worsens adverse selection.

### Step 6: queue position

Real orders at one price may sit behind many earlier orders. A maker is not filled merely because a trade occurs at its price. Enough quantity must trade ahead of it first.

The current engine has FIFO queues, but the synthetic strategy does not calibrate queue position against real exchange data.

### Step 7: historical order-book replay

LOBSTER is a source of historical Nasdaq limit-order-book message data. A future version could replay a sample day and compare simulated depth, spread, trade sizes, and markouts with empirical data.

This would test whether the synthetic model resembles a real market.

### Step 8: Avellaneda-Stoikov strategy

Avellaneda-Stoikov is a mathematical market-making model that connects inventory, risk aversion, volatility, time remaining, and order-arrival intensity.

It should be added as a second strategy after the simpler linear model is understood. The linear strategy is easier to debug and explain.

### Step 9: C++ matching engine

C++ can provide tighter control over memory and performance. A C++ hot path could be connected to Python and benchmarked against the current engine.

This is useful for a quant-development angle, but it does not improve the model's economic realism by itself.

## 23. How the project can read on your CV

### The current draft idea

Your earlier draft described a price-time-priority engine, an inventory-aware maker, Poisson order flow, PnL decomposition, and adverse-selection measurement.

Those claims are now supported by code and tests. The bullet should use the actual experiment numbers rather than placeholders or vague wording.

### Recommended one-bullet version

> Built a Python price-time-priority limit-order-book and continuous-time market-making simulator; across 200 seeded sessions, inventory-skewed quoting cut terminal-PnL standard deviation by 82.5% and mean maximum absolute inventory by 74.3% for a 10.4% reduction in gross spread capture.

### Optional second bullet if space allows

> Modelled informed and uninformed order flow and quantified adverse selection using multi-horizon markouts; validated matching, accounting, and experiment reproducibility with 47 tests, 94% coverage, and GitHub CI.

### What every phrase means

`Python`: the implementation language.

`Price-time priority`: better prices fill first; equal prices fill in arrival order.

`Limit-order-book`: the stored collection of unfilled bids and asks.

`Continuous-time`: event times are sampled from exponential waiting times rather than fixed clock steps.

`Market-making simulator`: a model that posts both buy and sell quotes and records fills, cash, and inventory.

`200 seeded sessions`: 200 reproducible runs for each parameter setting.

`Inventory-skewed quoting`: moving both quotes against the current position to encourage inventory to return toward zero.

`Terminal-PnL standard deviation`: variability in final session PnL across runs.

`Maximum inventory`: the largest absolute long or short position reached in a session.

`Gross spread capture`: execution edge before subtracting inventory PnL, fees, and other omitted costs.

### Claims to avoid

Do not say:

- The strategy made real money.
- The model was profitable in live markets.
- The simulator used historical Nasdaq data.
- The strategy achieved a real Sharpe ratio.
- The engine has strictly O(1) cancellation in every case.
- The project implements Avellaneda-Stoikov.

### A 30-second spoken explanation

> I built a small exchange simulator with a price-time-priority order book. It generates passive orders, aggressive orders, cancellations, and a simplified informed-flow channel. A market maker posts both sides and moves its quote center against inventory. I compared several inventory-aversion settings over the same 200 random seeds. A moderate setting reduced terminal-PnL variability by 82.5% and mean maximum absolute inventory by 74.3%, while gross spread capture fell by 10.4%. I also decomposed PnL and used post-fill markouts to check that informed flow was more adverse.

Do not memorize this word for word. Rewrite it in language that sounds natural when you speak.

## 24. Interview questions and simple answers

### What is a limit order book?

It is a list of unfilled buy and sell limit orders, grouped by price. The highest bid and lowest ask are the best visible prices.

### What is price-time priority?

The best price executes first. If two orders have the same price, the one that arrived first executes first.

### What is the difference between a market order and a limit order?

A market order prioritizes immediate execution but does not control price. A limit order controls the worst acceptable price but may not execute.

### Why use integer ticks?

Whole-number ticks make price equality and ordering exact. Floating-point currency values can create comparison errors.

### Why use a sorted price structure?

The engine needs to find the best price and insert new price levels efficiently. A `SortedDict` keeps prices ordered while allowing logarithmic insertion and removal by level.

### Is cancellation O(1)?

The direct order lookup and removal from a populated FIFO level are average O(1). If cancellation removes the last order at a price, deleting that price level from the sorted structure costs O(log P), where P is the number of populated price levels.

### What is a market maker?

A market maker posts both a bid and ask so other traders can trade immediately. It tries to earn execution edge while controlling inventory and adverse selection.

### Why is inventory dangerous?

A long position loses when price falls. A short position loses when price rises. Repeated one-sided fills can build a large position even when expected inventory is zero across many sessions.

### What does gamma do?

Gamma controls how strongly inventory shifts the quote center. Zero ignores inventory. Larger values react more aggressively.

### What is adverse selection?

It is the tendency to trade against counterparties whose information or timing causes price to move against you after the fill.

### How did you measure adverse selection?

I calculated signed midpoint markouts after each maker fill at several future horizons and compared informed with uninformed aggressors.

### Why create informed traders in a simulation?

A purely random order-flow model has little reason for post-fill prices to move systematically against the maker. The latent-value channel creates a controlled source of toxic flow that markouts can detect.

### How do you calculate PnL?

I track cash and inventory, mark inventory at the current midpoint, and reconcile total PnL with spread capture plus inventory PnL after every session.

### Why run 200 sessions?

PnL variability is noisy. Hundreds of seeds provide a more stable estimate than a handful of paths.

### Why use the same seeds for every setting?

It gives each parameter setting comparable pseudo-random conditions and reduces noise in the differences.

### What did the experiment find?

Gamma 0.1 reduced terminal-PnL standard deviation by 82.5% and mean maximum absolute inventory by 74.3%, while mean gross spread capture fell by 10.4% compared with gamma zero.

### What result surprised you?

PnL kept rising as half-spread increased from one to five ticks, even though fills fell. I expected a hump. The result suggests the range is too narrow or the model fills wide quotes too easily.

### What is the biggest limitation?

The flow is synthetic and not calibrated against real message data. It omits latency, fees, realistic queue-position effects, and strategic behavior.

### What would you build next?

I would aggregate markouts across many runs, widen the spread sweep, then validate the model by replaying real order-book messages before adding a more advanced quoting formula.

## 25. A five-session study plan

### Session 1: orders and matching

Read sections 2 to 4.

Then open `tests/test_order_book.py`. For each test, draw the book on paper before reading the expected trades.

You should be able to explain limit orders, market orders, price priority, FIFO, partial fills, crossing orders, and cancellation.

### Session 2: random market activity

Read sections 7 to 9.

Run two 500-event sessions with different seeds. Compare event counts, duration, spread, and midpoint range.

You should be able to explain Poisson arrivals, exponential waiting time, hazards, latent value, informed flow, and reproducibility.

### Session 3: market making and inventory

Read sections 5 and 6.

Calculate quotes by hand for inventories of `-20`, `0`, and `+20` using midpoint 100, gamma 0.1, and half-spread 1.

You should be able to explain why both quotes move down when long and up when short.

### Session 4: PnL and markouts

Read sections 7 and 10.

Recreate the full PnL example on paper. Then open one `fills.csv` and `states.csv` file and identify a maker buy and sell.

You should be able to explain cash, inventory, marked-to-market PnL, spread capture, inventory PnL, reconciliation, and markouts.

### Session 5: experiments and communication

Read sections 16 to 24.

Explain each figure aloud. Record yourself giving the 30-second project explanation, then answer the interview questions without reading.

You should be able to separate verified findings from limitations and future plans.

## 26. Practice exercises

Try each question before reading the answer.

### Exercise 1: spread and midpoint

Best bid is 204 and best ask is 208. Find the spread and midpoint.

Answer:

```text
spread = 208 - 204 = 4 ticks
midpoint = (204 + 208) / 2 = 206 ticks
```

### Exercise 2: price priority

The sell book contains 2 units at 101 and 5 units at 102. A market buy for 4 arrives. What trades?

Answer:

```text
2 units at 101
2 units at 102
```

### Exercise 3: time priority

A sells 3 at 101, then B sells 4 at 101. A buyer takes 5. What remains?

Answer:

```text
A fills all 3.
B fills 2 and keeps 2 resting.
```

### Exercise 4: quote skew

Midpoint is 100, inventory is `+20`, gamma is 0.1, and half-spread is 1. Find the reservation price, bid, and ask.

Answer:

```text
reservation price = 100 - 0.1 * 20 = 98
bid = 97
ask = 99
```

### Exercise 5: cash and inventory

The maker buys 4 at 50. What changes?

Answer:

```text
cash change = -200
inventory change = +4
```

### Exercise 6: marked-to-market PnL

After that purchase, the midpoint is 52. Find PnL.

Answer:

```text
cash = -200
inventory value = 4 * 52 = 208
PnL = +8
```

### Exercise 7: buy markout

The maker buys when the fill-time midpoint is 100. Ten time units later the midpoint is 96. Find the markout.

Answer:

```text
markout = 96 - 100 = -4 ticks per unit
```

The price moved against the maker.

### Exercise 8: interpreting risk

Strategy A has mean PnL 500 and standard deviation 2,000. Strategy B has mean PnL 300 and standard deviation 400. Which is automatically better?

Answer:

Neither is automatically better. A has higher average PnL, while B is more consistent and has a higher mean divided by standard deviation. The correct choice depends on risk preferences and whether the model is realistic.

## 27. Glossary

### Active order

A resting order that has not been completely filled or cancelled.

### Adverse selection

Trading against someone whose information or timing causes price to move against you afterwards.

### Aggressive order

An order that immediately takes available liquidity. Market orders are aggressive.

### Ask

An offer to sell.

### Asset

The financial item being traded.

### Average or mean

The sum of observations divided by their count.

### Backtest

A test of a strategy on historical data. This project is a simulation, not a historical backtest.

### Best ask

The lowest visible sell price.

### Best bid

The highest visible buy price.

### Bid

An offer to buy.

### Bootstrap

A method that resamples observed results to estimate uncertainty in a statistic.

### Cancellation

Removal of an active resting order.

### Cash

Money received from sales minus money spent on purchases.

### CI

Continuous integration in the software section. Confidence interval in a statistical context. The surrounding sentence tells you which meaning applies.

### CLI

Command-line interface, meaning commands typed into a terminal.

### Common random numbers

Using the same seeds across strategy settings so comparisons face similar pseudo-random inputs.

### Confidence interval

A range that describes uncertainty in an estimated statistic under the experiment's assumptions.

### Continuous time

Event times can occur at any positive time rather than only fixed integer steps.

### Coverage

The percentage of executable statements reached by tests.

### Crossing order

A limit order whose price is compatible with immediate execution against the opposite side.

### CSV

Comma-separated values, a table-like text file.

### Depth

Resting quantity available across price levels.

### Deterministic

Guaranteed to produce the same result from the same inputs.

### Event

One simulated occurrence, such as an order arrival, cancellation, or value shock.

### Exchange

A venue or system that matches buyers and sellers.

### Exponential distribution

A probability distribution used here for waiting time until the next event.

### Fair value

A model reference for an asset's value. In this project it is latent and simplified.

### FIFO

First in, first out. Earlier orders at the same price fill first.

### Fill

The executed part of an order.

### Gamma

The parameter controlling how strongly inventory shifts maker quotes.

### Geometric distribution

A discrete distribution used here to make smaller distances and sizes more common.

### Gross spread capture

Execution edge against the midpoint before inventory PnL and omitted real-world costs.

### Hazard

The current event-arrival intensity.

### Informed flow

Orders whose direction uses the simulator's latent-value signal.

### Instrument

The asset or contract being traded.

### Inventory

The maker's signed position. Positive is long and negative is short.

### Inventory limit

The largest absolute position the strategy permits.

### Inventory PnL

Profit or loss caused by midpoint movement while inventory is held.

### JSON

A text format for named and nested data.

### Latency

Delay between making a trading decision and the exchange processing it.

### Latent

Hidden rather than directly observed.

### Limit order

An order that controls the worst acceptable price.

### Liquidity

The ability to trade without causing a large price movement.

### Long

Holding positive inventory.

### Maker

A participant that provides resting liquidity.

### Market maker

A participant or strategy that continuously quotes buy and sell prices.

### Market order

An order seeking immediate execution at available prices.

### Marked to market

Valuing current inventory at the latest market reference price.

### Markout

Signed midpoint movement after a fill.

### Mean divided by standard deviation

A simple risk-adjusted statistic used here. It is not presented as an annualized Sharpe ratio.

### Midpoint

The average of best bid and best ask.

### Order book

The collection of active bids and asks.

### Order flow

The stream of new orders, trades, and cancellations.

### Parameter

A configurable value controlling model behavior.

### Parameter sweep

Repeated runs across several values of one parameter.

### Partial fill

Execution of only part of an order's quantity.

### Passive order

An order that rests and provides liquidity instead of trading immediately.

### PnL

Profit and loss.

### Poisson process

A model for independent random arrivals at an average rate.

### Price level

All resting orders at one price.

### Price priority

Better prices execute before worse prices.

### Queue position

An order's place behind earlier orders at the same price.

### Quote

A displayed price and quantity available to trade.

### Random seed

The starting value that makes a pseudo-random sequence reproducible.

### Rebate

A payment an exchange may give for providing liquidity. The current model omits rebates.

### Reconciliation

Checking that separate accounting calculations agree.

### Reservation price

The inventory-adjusted center of the maker's desired quotes.

### Resting order

An unfilled limit order waiting in the book.

### Risk aversion

Preference for reducing uncertain outcomes, even if doing so sacrifices some expected reward.

### Short

Holding negative inventory.

### Simulation

A generated model of a system rather than a replay of actual history.

### Spread

Best ask minus best bid.

### Spread capture

Execution edge earned relative to the reference midpoint.

### Standard deviation

A measure of how widely observations vary around their mean.

### Stochastic

Involving randomness.

### Strategy

A set of rules for making trading decisions.

### Sweep

An experiment that changes a parameter across several values.

### Taker

A participant whose aggressive order removes resting liquidity.

### Tick

The smallest allowed price step.

### Time priority

Earlier orders at the same price execute first.

### TOML

A human-readable configuration-file format.

### Toxic flow

Flow that tends to be followed by adverse price movement for the maker.

### Trade

A completed match between a buyer and seller.

### Variance

A measure of dispersion equal to the average squared distance from the mean, with the precise sample formula depending on context.

### Virtual environment

An isolated Python installation for one project.

### Walking the book

An aggressive order consuming liquidity across several price levels.

## 28. One-page revision sheet

### Market structure

```text
Bid = offer to buy
Ask = offer to sell
Best bid = highest bid
Best ask = lowest ask
Spread = best ask - best bid
Midpoint = (best bid + best ask) / 2
```

### Matching

```text
Better price first
Same price: earliest order first
Limit order: price control, execution not guaranteed
Market order: immediate execution attempt, price not controlled
```

### Market maker

```text
Posts a bid and ask
Earns execution edge
Faces inventory risk and adverse selection
```

### Inventory skew

```text
reservation price = midpoint - gamma * inventory

Long inventory  -> move quotes down
Short inventory -> move quotes up
Gamma 0         -> ignore inventory
```

### Accounting

```text
Buy signed quantity  = positive
Sell signed quantity = negative
Cash change = -signed quantity * fill price
Total PnL = cash + inventory * midpoint
Total PnL = spread capture + inventory PnL
```

### Adverse selection

```text
Negative markout = price moved against the maker
Informed flow should have worse markouts than uninformed flow
```

### Main experiment

```text
Comparison: gamma 0 versus gamma 0.1
Sessions: 200 per setting with common seeds
PnL standard deviation: 82.5% lower
Mean maximum absolute inventory: 74.3% lower
Mean gross spread capture: 10.4% lower
```

### Honest limitations

```text
Synthetic flow
No real trading
No historical replay
No latency, fees, or rebates
No empirical queue calibration
No real Sharpe ratio
Spread sweep did not produce the expected hump within 1 to 5 ticks
```

### Short explanation

```text
I built a price-time-priority exchange simulator and an inventory-aware market maker.
I generated continuous-time synthetic order flow with an informed component.
I measured PnL, inventory, spread capture, and post-fill markouts.
Across 200 common seeds, moderate inventory skew reduced PnL variability and
mean maximum absolute inventory much more than it reduced gross spread capture.
```
