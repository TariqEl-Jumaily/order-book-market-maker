# Interview question bank

This bank contains 120 questions about the project. The answers are written as spoken model answers, not scripts that you should memorize word for word. Learn the logic, then answer in your own voice.

The safest structure for most technical answers is:

1. Define the idea plainly.
2. Explain how this project handles it.
3. State one trade-off, test, result, or limitation.

If you do not know an answer, do not bluff. Say what you do know, identify the uncertain part, and explain how you would verify it.

## Project overview and communication

### 1. Tell me about this project

I built a Python limit-order-book and market-making simulator. The matching engine applies price-time priority, while a synthetic event generator creates limit orders, market orders, cancellations, and latent-value shocks in continuous time. A market maker posts two-sided quotes and shifts them according to inventory. I then measure fills, PnL, inventory risk, and post-fill markouts. Across 200 common seeds, gamma 0.1 reduced terminal-PnL standard deviation by 82.5% and mean maximum absolute inventory by 74.3% relative to gamma zero, while mean gross spread capture fell by 10.4%.

### 2. Explain the project to somebody with no trading background

Imagine a marketplace with a queue of people willing to buy at different prices and another queue willing to sell. I built the rules that decide who trades first. I then added an automated dealer that continuously offers to buy and sell. The dealer may earn the gap between those prices, but it can accumulate too much stock or trade with people who know more. The project tests how changing the dealer's prices can reduce that risk.

### 3. What question were you trying to answer?

The main question was whether a simple inventory-aware quoting rule could reduce a market maker's risk without giving up too much execution revenue. I compared no inventory adjustment with several gamma settings under the same random seeds. The moderate setting reduced inventory and PnL variability substantially, but it also reduced gross spread capture. That is the risk-reward trade-off the project was designed to expose.

### 4. What did you personally build?

I built the project as one integrated Python package: the order-book data structures and matching rules, the stochastic order-flow model, the inventory-aware market maker, the event loop, PnL and markout analytics, parameter sweeps, command-line interface, report figures, tests, and CI setup. I can explain how each component interacts and reproduce every committed result from the configuration and seeds.

### 5. Why did you choose this project?

It connects finance, probability, data structures, testing, and experimental analysis in one system. A market maker is easy to describe at a high level, but implementing one forces you to be precise about execution priority, inventory, cash signs, event timing, and adverse selection. Those details made it a good project for learning both market microstructure and reliable software engineering.

### 6. What is the most important result?

For the current synthetic model, gamma 0.1 reduced terminal-PnL standard deviation from about 2,897 ticks to 506 ticks, an 82.5% reduction. Mean maximum absolute inventory fell from 100 units to 25.7 units, a 74.3% reduction. Mean gross spread capture fell from about 3,861 ticks to 3,460 ticks, a 10.4% cost. I describe these as simulated results, not evidence of live profitability.

### 7. What are you most proud of technically?

The accounting reconciliation is the part I trust most. Total marked-to-market PnL equals spread capture plus inventory PnL to within `1e-9`. That identity is tested, and the simulator checks it after every completed run. It catches subtle mistakes in cash signs, fill timing, and which inventory should receive a midpoint change.

### 8. What was the hardest conceptual part?

The hardest part was getting event timing and PnL attribution consistent. A fill occurs because of an external event, so I record the midpoint before that event for spread capture, process the fill, record the new inventory, then apply the post-event midpoint for inventory PnL. If those observations are taken in the wrong order, the decomposition can look plausible but fail to reconcile.

### 9. What would you show in a five-minute demonstration?

I would first submit a few hand-built orders to show price priority, FIFO, and a partial fill. Then I would run one seeded simulation and inspect its summary, fills, and inventory path. Finally, I would show the gamma sweep and explain the measured trade-off between risk reduction and spread capture. I would finish with the limitations so the audience knows the results come from a synthetic market.

### 10. What does this project prove about you?

It shows that I can turn an economic question into explicit rules, implement those rules, test edge cases, run reproducible experiments, and communicate results without overstating them. It does not prove that I can run a profitable live strategy. I see that distinction as important.

## Market microstructure foundations

### 11. What is a limit order book?

A limit order book is the set of unfilled buy and sell limit orders for one instrument. Buy orders are bids and sell orders are asks. The highest bid and lowest ask are the best visible prices. The book groups orders by price and keeps their priority within each price.

### 12. What is a bid?

A bid is an offer to buy. The best bid is the highest current buying price because it is most attractive to a seller. In the engine, bids are stored by integer tick price, and the highest populated bid level is the first buy price shown by `best_bid`.

### 13. What is an ask?

An ask is an offer to sell. The best ask is the lowest current selling price because it is most attractive to a buyer. In the engine, the lowest populated ask level is returned by `best_ask`.

### 14. What is the spread?

The quoted spread is the best ask minus the best bid. If the best bid is 100 ticks and the best ask is 102 ticks, the spread is 2 ticks. It is one rough measure of the cost of immediate execution and the compensation available to a passive market maker, although actual economics also depend on fills, price movement, fees, and queue position.

### 15. What is the midpoint?

The midpoint is the average of the best bid and best ask. It is used here as a simple reference price for quoting, marking inventory, and calculating markouts. It is not guaranteed to equal fundamental value, and it can be noisy when depth is thin or the spread is wide.

### 16. What is a tick?

A tick is the minimum price increment represented by the model. The engine stores price as whole-number ticks, so 10,000 ticks with a tick value of 0.01 would display as 100.00 currency units. Integer ticks avoid floating-point equality problems inside the matching engine.

### 17. What is market depth?

Depth is the quantity resting at each price level. More depth near the touch means a larger aggressive order can trade without walking as far through the book. The simulator records average bid and ask depth by distance from the midpoint for its depth-profile figure.

### 18. What is liquidity?

Liquidity is the ability to trade without a large delay or price movement. A narrow spread and substantial depth often indicate more visible liquidity, but liquidity also depends on how stable those orders are and how quickly they disappear under pressure. This project models displayed liquidity but not hidden orders.

### 19. What is a limit order?

A limit order sets a worst acceptable price. A buy limit executes only at its limit or lower, while a sell limit executes only at its limit or higher. If it cannot trade immediately, its remainder may rest in the book. That price control comes with execution risk because the order may never fill.

### 20. What is a market order?

A market order prioritizes immediate execution against the best available resting prices. It does not set a limit price. In this engine, any unfilled remainder is discarded if the opposite book runs out, which models a market order without an unlimited promise of liquidity.

### 21. What makes an order passive or aggressive?

A passive order rests and supplies liquidity. An aggressive order crosses the spread and consumes resting liquidity. A limit order can be aggressive if its price crosses the opposite touch, so passive versus aggressive is about behavior, not simply the order type.

### 22. What is a fill?

A fill is an execution of some quantity at a price. One order can receive several fills, and a fill can be partial. The simulator records maker fills with time, signed quantity, execution price, pre-event midpoint, and aggressor type.

### 23. What is a partial fill?

A partial fill occurs when only part of an order trades. If a resting sell has 10 units and an incoming buyer takes 4, the sell keeps 6 units in its original queue position. The matching engine and market-maker accounting both test this behavior.

### 24. What does it mean to walk the book?

An aggressive order walks the book when it consumes all available quantity at the best price and continues to worse price levels. For example, a market buy may take asks at 101, then 102, then 103. The engine returns a separate trade record for each resting order it reaches.

### 25. What is a crossed or locked book?

A crossed book has a best bid above the best ask. A locked book has equal best bid and ask. In a continuous matching engine, a marketable incoming order should execute instead of leaving a crossed book resting. This project tests that sequential order submissions never leave a crossed state.

## Matching engine and data structures

### 26. What is price-time priority?

Better prices execute before worse prices. At the same price, earlier orders execute before later ones. That combination is price-time priority. The engine implements price priority with sorted price levels and time priority with a FIFO queue at each level.

### 27. What does FIFO mean?

FIFO means first in, first out. Within one price level, the first order inserted is the first eligible to trade. The project uses an `OrderedDict` keyed by order identifier, so the earliest remaining item at a price is selected first.

### 28. Why use a `SortedDict` for price levels?

The engine repeatedly needs the highest bid, lowest ask, and ordered traversal through prices. `SortedDict` keeps prices ordered and supports level insertion and deletion in logarithmic time. A normal dictionary would provide fast lookup but would not maintain price order, while sorting its keys for every match would add unnecessary repeated work.

### 29. Why use an `OrderedDict` within each level?

It gives deterministic FIFO iteration and direct removal by order identifier. The first item is the oldest active order at that price. Removing a known order from a populated level is average constant time, which matters for cancellations.

### 30. Why keep a separate active-order index?

Without an index, cancellation would require scanning price levels and queues to find an order. The `_active_orders` dictionary maps each active identifier directly to its order and therefore its side and price. That makes lookup average O(1).

### 31. Is cancellation O(1)?

Not in every case. Finding the order and removing it from a populated FIFO level are average O(1). If it was the final order at that price, deleting the empty price level from `SortedDict` costs O(log P), where P is the number of populated price levels. I state that qualification explicitly rather than claiming unconditional O(1).

### 32. What is the complexity of adding a resting limit order?

If it does not match, finding or creating its price level is generally O(log P), then appending it within the level is average O(1). If it crosses, cost also depends on the number of orders filled and price levels removed. The practical complexity is therefore driven by both book structure and how far the order walks.

### 33. What is the complexity of matching an aggressive order?

It is roughly proportional to the number of fills plus the cost of removing exhausted price levels. The implementation documents it as O(number of fills plus crossed levels times log P). Any matching engine must at least process the fills it creates.

### 34. Why not use heaps for bids and asks?

Heaps make access to one extreme efficient, but arbitrary cancellation and traversing multiple live levels are awkward. Lazy deletion can work, but it adds stale entries and bookkeeping. `SortedDict` gives clear ordered levels, direct level deletion, and readable behavior for this educational engine.

### 35. Why not store all orders in one sorted list?

Insertion and removal from the middle of a Python list are linear because elements shift. Grouping orders into sorted price levels plus FIFO queues separates price priority from time priority and makes cancellation much more efficient.

### 36. Why reject duplicate order identifiers even after an order has filled or been cancelled?

Order identifiers are audit keys. Reusing one can make logs ambiguous and can cause a late cancel or fill message to refer to the wrong order. The engine keeps a set of all identifiers seen during its lifetime and rejects reuse.

### 37. At what price does a trade execute?

It executes at the resting order's price. The incoming order chose to cross that liquidity, so the resting order's displayed price determines the execution. The `Trade` record stores the resting and incoming identifiers, aggressor side, price, and quantity.

### 38. What happens to an unfilled market-order remainder?

It is discarded. A market order should not rest because it has no limit price. The engine returns the fills that occurred and leaves no remainder in the book.

### 39. What happens to an unfilled crossing-limit remainder?

It first executes at every acceptable opposite price. If quantity remains after no more acceptable prices exist, the remainder rests at its own limit. That preserves its price constraint and prevents a crossed book.

### 40. How did you test matching correctness?

The tests cover price priority, FIFO, partial fills, walking multiple levels, crossing limits, cancellation, duplicate identifiers, invalid prices and quantities, touch-first depth, market-order identifier reuse, and the never-resting-crossed invariant. I prefer small scenarios where the exact sequence of fills can be checked by hand.

## Stochastic order flow and simulation

### 41. Why is the simulation event driven?

Markets change when orders, cancellations, trades, or information events occur. An event-driven design jumps directly from one event to the next instead of checking every fixed clock interval. That gives a natural sequence for book mutation and avoids empty time steps.

### 42. What does continuous time mean here?

Event timestamps are real-valued and separated by exponentially distributed waiting times. The model is not updated once per second or once per millisecond. Continuous time here describes the mathematical clock, not a claim about nanosecond exchange realism.

### 43. What is a Poisson process?

A Poisson process is a standard model for random event arrivals with a constant rate over an interval. Its waiting times are exponential. This project uses competing hazards for several event categories. It is a useful baseline, although real order flow often has clustering and time-varying intensity.

### 44. What is a hazard or intensity?

A hazard is the instantaneous event rate. Higher intensity means a shorter expected waiting time. The baseline has separate rates for limit orders, market orders, value shocks, and cancellations, with cancellation intensity multiplied by the number of active background orders.

### 45. How do you select the next event?

I sum the current hazards to get a total hazard. I sample the next waiting time from an exponential distribution with that total rate. I then select an event category with probability equal to its hazard divided by the total. This is the standard competing-hazards construction.

### 46. Why does cancellation intensity depend on active orders?

If there are more cancellable orders, there should be more opportunities for a cancellation. The model uses `cancel_rate_per_order * active_background_order_count`. That also provides negative feedback: as the book grows, cancellation pressure rises.

### 47. How do you choose a random order to cancel efficiently?

The active pool combines a list of identifiers with a dictionary of their positions. Selection is random indexing into the list. Removal swaps the last identifier into the removed slot and updates its index. Adding, selecting, membership checks, and removal are average O(1), but iteration order is not preserved.

### 48. Why use a geometric distribution for price distance?

It gives positive integer distances and places more probability near the touch than far away. That is convenient for tick-based prices. It is a modelling choice, not an empirical claim about a particular exchange, and its parameter should eventually be calibrated against data.

### 49. How are order sizes generated?

Sizes come from a positive geometric draw, bounded by a maximum quantity. The baseline uses a geometric probability of 0.2 and caps size at 15. Bounded sizes prevent rare draws from creating unreasonably large events in this simple model.

### 50. How are background limit-order sides chosen?

Buy and sell sides are sampled symmetrically with equal probability. Their prices are placed passively relative to the opposite touch, so they do not intentionally cross the book. Symmetry helps avoid building an unexplained directional bias into the baseline.

### 51. What is latent fair value?

It is an unobserved reference value used by the informed-flow mechanism. Independent signed shocks move it by a fixed number of ticks. The market maker quotes from the visible midpoint, while informed market orders trade toward the latent value when it differs from that midpoint.

### 52. How do informed market orders work?

With baseline probability 0.2, a market order is labelled informed. If latent fair value is above the midpoint, it buys; if value is below, it sells. Its size can also increase with the value gap, subject to the maximum. At equality, its direction is random.

### 53. What does uninformed flow mean in this model?

Uninformed market orders choose direction randomly rather than using the latent-value signal. The label means uninformed with respect to this model's signal. It does not claim that real traders can be cleanly divided into two observable groups.

### 54. What is a random seed and why use one?

A seed initializes the pseudo-random number generator. The same code, configuration, and seed reproduce the same event path and output records. Seeds make debugging and comparisons possible because a surprising path can be replayed exactly.

### 55. What is the exact event sequence?

The simulator samples an event and records the midpoint immediately before it. It applies the external order, cancellation, or value shock, processes any maker fills and updates cash and inventory, refreshes quotes when needed, then records the post-event state. That ordering supports the PnL decomposition and prevents the maker from reacting before the event occurs.

## Market-making strategy and inventory

### 56. What is a market maker?

A market maker posts a bid and an ask so others can trade immediately. It may earn execution edge by buying below and selling above a reference price. It also faces inventory risk, adverse selection, missed fills, fees, and operational risk. This project focuses on inventory and adverse selection in a simplified setting.

### 57. Where does market-making revenue come from in the model?

The maker tries to buy below the pre-event midpoint and sell above it. That execution edge is recorded as gross spread capture. Revenue is not guaranteed because the midpoint can move while the maker holds inventory, creating inventory PnL that can offset or exceed spread capture.

### 58. What is inventory?

Inventory is the maker's net position. Buys add positive units and sells add negative units. Positive inventory is long, while negative inventory is short. Even if buy and sell orders are symmetric in expectation, one path can produce a large one-sided position.

### 59. Why is inventory risky?

A long maker loses marked-to-market value if the midpoint falls, and a short maker loses if it rises. The maker does not control the sequence of incoming orders, so repeated fills on one side can build exposure before offsetting trades arrive.

### 60. What is the reservation price?

It is the center around which the maker places quotes. The model uses `reservation_price = midpoint - gamma * inventory`. At zero inventory, it equals the midpoint. When inventory is positive, it moves down; when inventory is negative, it moves up.

### 61. What does gamma mean?

Gamma controls the strength of inventory skew in ticks per unit of inventory. Zero means quotes ignore inventory. A larger gamma moves the quote center more for the same position. In this project it is a strategy parameter, not a full utility-theory risk-aversion estimate.

### 62. Why do both quotes move down when the maker is long?

Moving the bid down makes another buy less likely or less expensive. Moving the ask down makes a sale more attractive to incoming buyers. Both changes encourage inventory to fall. Widening only one side would change other properties of the quote, while this strategy keeps a fixed half-spread around a shifted center.

### 63. Why do both quotes move up when the maker is short?

A higher bid encourages the maker to buy back inventory. A higher ask makes another sale less attractive or earns a higher price if it occurs. Together they push the position back toward zero.

### 64. How are quote prices converted to integer ticks?

The reservation price can be fractional because gamma times inventory need not be an integer. The implementation rounds the bid downward with `floor` and the ask upward with `ceil`. It then keeps quotes passive relative to the current best prices so they do not unexpectedly cross.

### 65. What does half-spread mean?

Half-spread is the distance from the reservation price to each quote before tick rounding and passive-price constraints. With a reservation price of 100 and half-spread 1, the intended bid is 99 and ask is 101. The full quoted width is therefore roughly two ticks.

### 66. How does the hard inventory limit work?

The maker calculates remaining buy and sell capacity. At the positive limit, it suppresses the bid because another buy would increase exposure, but it can still offer to sell. At the negative limit, it suppresses the ask. Quote size is also capped by the remaining capacity so a fill cannot cross the limit.

### 67. When does the maker requote?

The simulator cancels and replaces quotes after the midpoint changes or when a quote is missing because of a fill, provided inventory capacity allows it. The refresh uses the unquoted book midpoint so the maker's own quotes do not mechanically determine the center used to replace themselves.

### 68. What are the weaknesses of the linear strategy?

The spread is fixed rather than derived from volatility, arrival intensity, time remaining, or fees. Gamma has an informal unit and must be tuned. The strategy also reacts instantly and does not estimate queue value. Its advantage is that the mechanism is transparent, easy to test, and suitable as a baseline for a later Avellaneda-Stoikov comparison.

## Cash, PnL, and markouts

### 69. What signed-quantity convention do you use?

A maker buy has positive signed quantity, and a maker sell has negative signed quantity. Cash changes by `-signed_quantity * fill_price`. This single rule handles both sides consistently.

### 70. Show the cash calculation for a buy

If the maker buys 5 units at 99 ticks, signed quantity is `+5`. Cash change is `-(+5) * 99 = -495` ticks of value. Inventory rises by 5. The cash outflow and asset received are separate parts of the balance sheet.

### 71. Show the cash calculation for a sell

If the maker sells 5 units at 101 ticks, signed quantity is `-5`. Cash change is `-(-5) * 101 = +505`. Inventory falls by 5. If that sale closes the earlier buy, the round-trip cash profit is 10 ticks before other effects.

### 72. What is marked-to-market PnL?

It is cash plus inventory valued at the terminal midpoint, adjusted for any initial value. The baseline begins with zero cash and zero inventory, so terminal PnL is `cash + inventory * terminal_midpoint`. Marking inventory avoids pretending that an open position is worthless.

### 73. Why not force liquidation at the end?

Forced liquidation would add an extra execution rule and potentially a large artificial terminal trade. Marking at the midpoint keeps the experiment focused on quoting behavior. The limitation is that midpoint valuation ignores the cost of actually liquidating a position through finite depth.

### 74. What is gross spread capture?

For each fill it is `signed_quantity * (pre_event_mid - fill_price)`. A buy below the pre-event midpoint contributes positively, and a sell above it also contributes positively because sell quantity is negative. It is called gross because fees, rebates, latency costs, and liquidation costs are omitted.

### 75. What is inventory PnL?

Inventory PnL is the gain or loss from holding a position while the midpoint changes. For each event interval, the project uses post-event inventory times the midpoint change. Summing those terms attributes price movement to the inventory that was actually held after that event's fills.

### 76. State the PnL reconciliation identity

Total marked-to-market PnL equals gross spread capture plus inventory PnL. In the code, the residual is `total_pnl - spread_capture - inventory_pnl`, and the simulator raises an error if its absolute value exceeds `1e-9`.

### 77. Why use the pre-event midpoint for spread capture?

The fill is caused by the current external event. Using the midpoint before that event measures execution relative to the price visible just before the aggressor arrived. The later midpoint movement is then assigned to inventory PnL rather than counted inside spread capture.

### 78. What is a markout?

A markout measures how the midpoint moves after a fill, signed from the maker's perspective. Positive means the later move favored the maker, while negative means it moved against the maker. It is measured in ticks per unit so fills of different sizes are comparable.

### 79. Give a buy-markout example

Suppose the maker buys at a fill-time midpoint of 100 and the midpoint at the chosen horizon is 103. The maker owns the asset, so the movement is favorable and the markout is `+3` ticks per unit. If the midpoint falls to 97, the markout is `-3`.

### 80. Give a sell-markout example

Suppose the maker sells when the midpoint is 100 and the future midpoint is 103. The maker is short relative to that fill, so the move is unfavorable and the signed markout is `-3` ticks per unit. A fall to 97 would produce `+3`.

### 81. How do you find the future midpoint for a markout?

For each horizon, the analytics use the first recorded state at or after `fill_time + horizon`. That works with irregular event times. If the simulation ends before the target, no markout is created for that fill-horizon pair.

### 82. What did the representative markout result show?

In seed 42 at horizon 30, informed fills averaged about `-7.09` ticks per unit while uninformed fills averaged about `+2.04`. That is consistent with the mechanism generating adverse selection. It is a representative-path result, so the next analytical step is a session-level aggregate over 200 seeds with uncertainty intervals.

## Experiments and statistics

### 83. What is a parameter sweep?

A parameter sweep runs the same experiment over a declared set of parameter values. The project sweeps half-spread values 1 through 5 and gamma values `0`, `0.025`, `0.05`, `0.1`, `0.2`, and `0.4`. Each setting uses 200 seeds.

### 84. Why run 200 seeds?

One simulated path can be unusually favorable or unfavorable. Repeating the experiment estimates the distribution of outcomes rather than presenting one story. Two hundred is a practical balance for this version, but it is not a universal sample-size rule.

### 85. What are common random numbers?

Common random numbers means every parameter setting uses the same seed list. Seed 17 under gamma zero and gamma 0.1 begins from comparable pseudo-random draws. This often reduces noise in setting-to-setting comparisons because some path-specific luck is shared.

### 86. Does the same seed create exactly the same realized market under different strategies?

It creates the same pseudo-random draw stream, but strategy changes can alter book state, cancellation counts, hazards, and therefore later interpretation of draws. So I call them common random numbers, not perfectly identical counterfactual market paths. A stronger design could separate exogenous random streams or pre-generate external events.

### 87. What is the mean?

The mean is the sum of observations divided by their count. It describes the average outcome across seeds. It can be affected by extreme paths, so I report it with variability and intervals rather than alone.

### 88. What is standard deviation?

Standard deviation measures how dispersed outcomes are around the mean. In this project, terminal-PnL standard deviation is a risk measure across simulated sessions. It is not the same as downside risk, tail loss, or maximum drawdown.

### 89. What is a confidence interval?

A confidence interval is a range produced by a statistical procedure to express uncertainty around an estimate. The project uses percentile bootstrap intervals for sweep means. It does not mean there is a 95% probability that a fixed true value lies inside this particular completed interval.

### 90. How does the bootstrap work here?

The bootstrap repeatedly samples the observed session outcomes with replacement, recalculates the mean, and takes percentiles of those resampled means. A fixed bootstrap seed makes the interval reproducible. For future aggregate markouts, I would resample sessions rather than individual fills.

### 91. Why not report a Sharpe ratio?

The simulations are not calibrated to a real time horizon, and the observations are terminal outcomes from synthetic sessions. The report includes mean divided by standard deviation as a descriptive ratio, but it explicitly does not annualize or label it Sharpe. Calling it Sharpe would imply assumptions the model has not justified.

### 92. How are sweeps parallelized without losing reproducibility?

Each task contains a complete configuration, seed, parameter name, and setting. Worker processes run tasks independently. After collection, rows are sorted by setting and seed, so output order is deterministic even if worker completion order changes.

### 93. How did you choose gamma 0.1 as the comparison?

It was one of the predeclared sweep values and provides a clear moderate-risk comparison. Gamma 0.05 had slightly higher mean PnL in the committed results, while gamma 0.1 had lower PnL variability and inventory. I do not claim gamma 0.1 is universally optimal; the choice depends on the objective and model assumptions.

### 94. Did you tune the simulation to produce a good CV result?

The baseline was calibrated against book-health diagnostics such as populated levels, typical spread, non-empty fraction, and a stable midpoint. The plan explicitly ruled out tuning to manufacture the inventory-aversion result. I report the spread sweep's unexpected monotonic PnL result because selecting only favorable outcomes would undermine the project.

## Python and software engineering

### 95. Why Python 3.12?

Python makes the model, tests, analytics, and figures readable in one language. Version 3.12 supports the typing and standard-library features used by the package. It is suitable for this research-scale workload, while a C++ path remains a possible later performance comparison.

### 96. Why use dataclasses?

Orders, trades, fills, states, configurations, and summaries are structured records. Dataclasses remove repetitive constructor and representation code while keeping fields explicit. Many result records are frozen so experiment outputs cannot be changed accidentally after creation.

### 97. Why use enums for side and event type?

Enums restrict values to known categories such as buy, sell, limit order, and cancellation. That avoids scattered magic strings and catches invalid values earlier. `StrEnum` also makes values straightforward to serialize.

### 98. Why make `SimulationConfig` immutable?

An experiment should have a stable set of assumptions. A frozen configuration prevents accidental mutation halfway through a run. Parameter sweeps create updated copies with `with_updates`, which makes each task's inputs explicit.

### 99. Why use TOML for configuration?

TOML is readable, supports numeric and list values cleanly, and Python 3.12 can parse it with `tomllib`. Committing the baseline file makes results easier to reproduce and review without searching source code for constants.

### 100. What does deterministic mean in this project?

Given the same code, configuration, Python environment, and seed, the simulator produces identical records and summaries. Tests compare repeated seeded runs directly. Parallel sweeps also sort outputs deterministically.

### 101. What does mypy add?

Mypy checks whether values flow through the program with compatible types. Strict typing catches mistakes such as confusing an optional price with a guaranteed integer or passing an unsupported parameter name. It does not prove runtime correctness, so tests are still necessary.

### 102. What does Ruff add?

Ruff checks style and common error patterns, including unused imports, suspicious constructs, and import ordering. It keeps the codebase consistent and catches some defects cheaply before tests run.

### 103. What does 94% coverage mean?

About 94% of measured executable statements ran during the test suite. It is evidence that tests exercise most of the package, not proof that every behavior is correct. The quality of assertions and edge cases matters more than the percentage alone.

### 104. What does GitHub Actions do?

On every push and pull request, CI installs Python 3.12 and the development dependencies, runs Ruff, runs mypy, and runs pytest with a 90% coverage threshold. This checks the repository in a clean environment rather than relying only on my laptop.

### 105. How would you profile performance?

I would define representative workloads, separate order insertion, cancellation, non-crossing orders, and multi-level matching, then measure repeated runs with warm-up and stable inputs. I would use a profiler to identify actual hotspots before rewriting code. Any reported throughput would include machine, Python version, workload, repetitions, and uncertainty.

## Results, challenges, limitations, and future work

### 106. Interpret the gamma sweep

As gamma rises from zero, the maker reacts more strongly to inventory. Mean maximum absolute inventory falls steadily. PnL standard deviation also falls sharply at first, but gross spread capture declines. Mean PnL improves from a very negative zero-gamma baseline, peaks around the moderate settings in this grid, then becomes negative again at gamma 0.4. Too little control leaves large directional exposure, while too much skew damages execution economics.

### 107. Why did gamma zero hit mean maximum absolute inventory of exactly 100?

One hundred is the configured hard inventory limit. The result means zero-gamma paths commonly reached that cap, so the reported maximum metric is censored by the risk control. It does not tell us how far inventory would have grown without the cap. That makes the contrast useful operationally, but it should be interpreted with the binding limit in mind.

### 108. Why can gamma 0.4 have lower risk but worse mean PnL?

Strong skew can move quotes far enough from the balanced market that the maker loses attractive fills or trades at less favorable opportunities for spread capture. Risk reduction has a cost. The best setting depends on the objective, such as maximizing mean PnL, limiting inventory, controlling downside, or optimizing a utility function.

### 109. What happened in the spread sweep?

From half-spread 1 to 5, mean fills fell from about 837 to 280, but mean PnL rose from about 389 to 1,736 ticks. I expected wider spreads eventually to reduce PnL through lost fills, but no turnover appeared in that range. I would widen the grid and inspect whether aggressive flow fills distant quotes too readily.

### 110. Is the strategy profitable?

It has positive mean PnL for some settings in this synthetic model. That is not enough to call it a profitable trading strategy. The model omits real data calibration, fees, latency, market impact, hidden liquidity, precise queue effects, and operational costs. I describe simulated PnL in ticks, not expected live returns.

### 111. What is the biggest modelling limitation?

The order flow is synthetic and mostly memoryless. Real markets show intraday seasonality, clustered activity, correlated order signs, changing volatility, strategic reactions, and instrument-specific behavior. Until the model is compared with historical message data, its numeric results apply only to its own assumptions.

### 112. What is the biggest execution limitation?

The maker can cancel and replace immediately. Real systems have network, processing, and exchange latency, so stale quotes can remain exposed. Queue position is respected mechanically by FIFO, but the distribution of quantity ahead is not calibrated to a real venue.

### 113. What would you build next and why?

I would first aggregate informed and uninformed markouts across 200 sessions with session-level bootstrap intervals. That strengthens the adverse-selection evidence. I would then widen the spread sweep and diagnose fill behavior. After those validation steps, I would add fees and latency before moving to historical replay and a more advanced strategy.

### 114. How would fees and rebates change the accounting?

I would add a separate exchange-cost component for every fill, with maker rebates positive and fees negative under a documented convention. Net PnL would equal spread capture plus inventory PnL plus rebates minus fees. Zero-cost settings must reproduce the current results exactly.

### 115. How would you model latency?

Quote decisions would create future message-arrival events rather than mutating the book immediately. Cancel requests and replacement orders would have configurable delays. An old quote could fill while cancellation is pending, and I would record quote age so stale-quote markouts can be measured.

### 116. How would you use historical data?

I would create an adapter from message records to add, cancel, execute, and replace events, then replay a small validated period through the same accounting and analytics. I would verify the final book against known snapshots and compare spread, depth, event rates, sizes, and markouts. Any claim would state the instrument, date, hours, filters, and data licence constraints.

### 117. What is Avellaneda-Stoikov?

It is a market-making framework that derives a reservation price and quote spread using inventory, risk aversion, volatility, time remaining, and order-arrival intensity under specific assumptions. I have not implemented it in the current version. I would add it as a second strategy and compare it with the transparent linear baseline under common simulated paths.

### 118. Why not start with Avellaneda-Stoikov?

The linear rule made inventory mechanics, accounting, and event sequencing easier to understand and test. Starting with a complex formula can hide bugs behind impressive notation. A simple baseline also gives the advanced model something meaningful to beat.

### 119. Tell me about a mistake or issue you would watch for

A dangerous mistake is using the wrong midpoint or inventory in PnL attribution. The totals may still look reasonable while spread capture and inventory PnL are misclassified. I guard against that with an explicit event sequence, immutable fill and state records, hand-worked tests, and exact reconciliation.

### 120. If you had another month, what would the finished version look like?

I would aim for a notebook that demonstrates the mechanics, aggregate markout evidence over 200 sessions, a diagnosed wider spread sweep, and fee and latency extensions with zero-value backward-compatibility tests. If suitable historical data were available under workable terms, I would also build a small replay adapter and calibration report. I would choose those improvements over adding a dashboard because they strengthen the financial evidence.

## Fast follow-up questions

Interviewers often shorten a question or challenge one word in your answer. Practise these short replies.

### Why "gross" spread capture?

Because it excludes fees, rebates, latency costs, hedging costs, and liquidation costs.

### Why "synthetic" sessions?

Because the events are generated from assumed probability distributions rather than replayed from historical exchange messages.

### Why "common" seeds?

Every setting uses the same seed list, which makes comparisons less noisy, although strategy changes can still alter later state-dependent events.

### Why "terminal" PnL?

It is measured at the end of each simulated session after valuing remaining inventory at the terminal midpoint.

### Why "absolute" inventory?

Long `+30` and short `-30` have different signs but the same position magnitude and comparable directional exposure.

### Why not use floats for prices?

Integer ticks give exact price equality and ordering inside the engine.

### Why does a market order have an identifier?

It gives every submitted order an auditable identity even though the order never rests.

### Why can midpoint be fractional?

If bid and ask ticks differ by an odd number, their arithmetic average lies on a half tick.

### Why is an informed fill expected to have a bad markout?

The aggressor trades in the direction of latent value, so the visible midpoint is more likely to move against the passive maker afterward.

### Why are no-skew results so poor?

The maker does not react to accumulated inventory, frequently reaches the hard limit, and is exposed to large adverse midpoint movements in this model.

## Questions you should ask the interviewer

At the end of an interview, questions about their system can connect naturally to this project:

- How does the team evaluate execution quality and adverse selection?
- Which parts of the research stack are event driven?
- How are simulation assumptions validated against production or historical data?
- How does the team separate strategy PnL from inventory or market-movement PnL?
- What matters most for this role: research quality, production engineering, or low-latency performance?
- How are queue position, latency, fees, and venue differences represented in backtests?
- What testing or reconciliation checks have caught the most serious trading-system errors?

Ask only questions that fit the role and the conversation. The goal is to understand their work, not to recite a prepared list.

## Final interview rules

- Say "in this synthetic model" when discussing results.
- Say "mean maximum absolute inventory" for the 74.3% figure.
- Say "gross spread capture" for the 10.4% cost.
- Do not call mean divided by standard deviation a Sharpe ratio.
- Do not claim historical data, live trading, fees, latency, Avellaneda-Stoikov, or C++.
- If asked for a number, give its comparison and unit, not the percentage alone.
- If challenged, explain the limitation before defending the result.
- Draw the book, cash flow, or event sequence on paper when words become confusing.
