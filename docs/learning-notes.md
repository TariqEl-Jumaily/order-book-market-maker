# Guided learning notes

## 1. Matching engine

An order book answers two questions: which price executes first, and which order
at that price executes first? Better prices have priority; equal prices use FIFO
time priority. Prices are integers because floats make equality and tick alignment
unreliable.

Key interview distinction: insertion depends on the number of price levels `P`,
not the number of orders `N`. Cancellation is not unconditionally O(1): removing
an order from its FIFO queue is average O(1), but deleting an empty level from the
sorted map costs O(log P).

## 2. Continuous-time flow

For independent Poisson processes, the waiting time to the next event is
exponential with rate equal to the sum of all hazards. After sampling the wait,
choose the event category with probability proportional to its hazard.

Cancellation uses `delta * active_orders`, so the total cancellation pressure
grows with displayed liquidity. This prevents the book from accumulating orders
without bound.

## 3. Market making and inventory

Symmetric quoting earns spread but lets inventory behave like a random walk.
Linear skew moves both quotes against the current position. When long, both quotes
move down: the maker becomes less eager to buy and more eager to sell.

Risk matters even if expected inventory is zero because the distribution can be
wide. In this experiment the unskewed strategy touched its inventory limit in all
200 sessions, while `gamma = 0.1` reduced mean maximum absolute inventory to 25.7.

## 4. Accounting and markouts

Spread capture measures the edge at execution relative to the pre-event midpoint.
Inventory PnL measures what happens as the midpoint moves while inventory is held.
Their exact reconciliation is a model invariant, not a charting convenience.

A markout asks whether price subsequently moves for or against the maker's fill.
Negative signed markouts indicate adverse selection. Splitting by informed versus
uninformed aggressors is a controlled test that the synthetic information channel
actually works.

## 5. Reading the experiments

Common random seeds make parameter comparisons less noisy because each setting
faces the same sequence of pseudo-random draws. Two hundred sessions are used
because PnL variance is too noisy to infer from a handful of paths.

The gamma sweep supports the intended conclusion. The spread sweep does not show
an interior optimum from one to five ticks. A credible analysis states that result
and proposes validation; it does not retune the simulator until the expected shape
appears.

## Questions to practise aloud

1. Why use integer ticks and FIFO queues?
2. Why is cancellation not always strictly O(1) in this implementation?
3. What economic behavior does inventory skew create?
4. Why can mean inventory be zero while inventory risk is still dangerous?
5. What does a negative markout mean?
6. Why use common seeds and hundreds of sessions?
7. Which model assumptions most threaten external validity?
