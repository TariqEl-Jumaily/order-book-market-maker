# Development roadmap

This roadmap starts from the working version of the project. It separates the next work into small milestones so that every addition teaches one idea, has a clear test, and improves what you can defend in an interview.

The current repository already has a matching engine, synthetic continuous-time order flow, an inventory-aware market maker, PnL and markout analytics, parameter sweeps, figures, tests, and continuous integration. The next stage is about learning the existing system, making the evidence stronger, and then adding realism.

## Recommended order

| Stage | Main outcome | Why it comes here |
|---|---|---|
| 1 | Interactive learning notebook | Makes the existing model easier to understand and demonstrate |
| 2 | Multi-session markout analysis | Strengthens the adverse-selection evidence |
| 3 | Wider spread experiment | Investigates the current result instead of hiding it |
| 4 | Fees and rebates | Adds a major real-world cost with limited code complexity |
| 5 | Quote latency | Introduces stale-quote risk and a more realistic event sequence |
| 6 | Queue-position model | Makes passive fills harder and more realistic |
| 7 | Historical-data replay | Tests whether the synthetic market resembles actual data |
| 8 | Avellaneda-Stoikov strategy | Adds a research-backed strategy for comparison |
| 9 | Optional C++ matching path | Adds a quant-development performance angle |

Stages 1 to 3 should be completed before changing the CV bullet. Stages 4 onward can produce new bullets, but only after their results have been measured.

## Stage 1: interactive learning notebook

### What we will build

Add `notebooks/01_order_book_walkthrough.ipynb`. It will let you:

- create a book manually;
- submit limit and market orders one at a time;
- observe price-time priority and partial fills;
- calculate midpoint and spread;
- run a short seeded simulation;
- inspect the maker's inventory, cash, fills, and markouts;
- change gamma and compare two paths using the same seed.

The notebook should call the package code. It must not contain a second matching engine or a simplified copy of the strategy.

### What you should learn

You should be able to draw a small book on paper and predict the next trade before running the cell. You should also be able to explain why a long maker moves both quotes down and why a short maker moves both quotes up.

### Files likely to change

- `notebooks/01_order_book_walkthrough.ipynb`
- `pyproject.toml`, to add notebook dependencies if needed
- `README.md`, to add launch instructions
- `docs/study-book.md`, to link each exercise to notebook cells

### Acceptance checks

- A new user can launch the notebook from documented commands.
- Every cell runs from top to bottom in a clean environment.
- All examples use deterministic seeds.
- The notebook explains each output in plain language.
- Existing tests, coverage, Ruff, and mypy still pass.

### Interview value

The notebook will make demonstrations easier, but it should not create a new quantitative CV claim by itself.

## Stage 2: aggregate markouts across many sessions

### Why this is the most important analytical improvement

The committed markout figure uses the representative seed 42 session. That result shows the sign convention and confirms that the informed-flow mechanism works in one controlled path. It is weaker evidence than the gamma experiment, which uses 200 seeds per setting.

The next report should summarize markouts across the same 200 seeds. This will answer whether informed flow is consistently worse for the maker, how large the difference is, and how uncertain the estimate is.

### What we will build

- Save fill-level markouts from every report run or aggregate them safely during the experiment.
- Produce separate informed and uninformed estimates at horizons 1, 5, 10, 30, and 60.
- Report fill counts, mean ticks per unit, and 95% bootstrap confidence intervals.
- Add the informed-minus-uninformed difference at each horizon.
- Use resampling at the session level, not the individual-fill level, for the headline interval. Fills inside one session share the same market path and are not independent observations.
- Add a new aggregate markout figure and a machine-readable summary.

### Why session-level resampling matters

Treating every fill as independent would make the sample appear larger than it really is. A price path can affect many fills in the same session. Resampling whole sessions preserves that dependence within each path.

### Files likely to change

- `src/lobmm/experiments.py`
- `src/lobmm/analytics.py`
- `src/lobmm/cli.py`
- `tests/test_analytics.py`
- `tests/test_experiments.py`
- `results/report-summary.json`
- `results/figures/markouts.png`
- `README.md`

### Acceptance checks

- The same configuration and seeds produce identical summaries.
- Every horizon reports informed and uninformed sample sizes.
- Bootstrap intervals use a documented deterministic bootstrap seed.
- A controlled unit test still produces worse informed markouts.
- The 200-session aggregate result is reported even if it is weak or changes sign.
- PnL reconciliation remains within `1e-9`.

### Possible CV improvement

If the aggregate evidence supports it, the second bullet can state that informed-flow markouts were worse across 200 simulated sessions. It should include the measured horizon and difference. We will not write that claim until the report exists.

## Stage 3: investigate the spread sweep

### The current puzzle

From half-spread 1 to 5 ticks, fills fall from about 837 to 280 per session, but mean PnL rises from about 389 to 1,736 ticks. A simple intuition says wider quotes should earn more per fill but trade less often, possibly producing a hump-shaped PnL curve. The tested range did not show that hump.

This is not a failed project result. It is a model-diagnosis question.

### What we will test

- Extend half-spreads beyond 5 ticks, for example through 10 or 15 ticks.
- Plot fill count, gross spread capture, inventory PnL, total PnL, and PnL standard deviation.
- Measure the maker's participation rate in aggressive flow.
- Check how often the maker is at the best bid or ask.
- Check whether quotes remain fillable at unrealistic distances because background market orders ignore price impact or urgency.
- Compare results under different market-order rates and order sizes.

The final parameter grid should be predeclared before the full run so that we do not choose a range after seeing the answer.

### Acceptance checks

- The extended experiment uses common seeds across every spread.
- Report generation still has deterministic row ordering under parallel execution.
- The README explains whether a turnover point appeared.
- If no turnover appears, the limitation is stated and the fill mechanism becomes the next research target.

### Interview value

This stage gives you a strong answer to: "Tell me about a result that did not match your expectation." It shows that you investigated the model rather than selecting only attractive charts.

## Stage 4: add fees and maker rebates

### The concept

Many exchanges charge liquidity takers and may pay a rebate to liquidity providers. A maker can show positive gross spread capture but weak net economics after costs.

### What we will build

- Add maker rebate and taker fee parameters in ticks or currency per unit.
- Record exchange economics separately from spread capture.
- Define net PnL as spread capture plus inventory PnL plus rebates minus fees.
- Keep gross and net figures side by side.
- Sweep the rebate or fee assumption over a small, declared range.

The current market maker is normally passive, so maker rebates are the main direct effect. The design should still support future aggressive hedging orders that pay taker fees.

### Acceptance checks

- Zero fees and zero rebates reproduce the old PnL exactly.
- Fee signs are tested for buys and sells.
- The PnL decomposition gains a cost component and still reconciles.
- Every result states whether it is gross or net.

## Stage 5: model quote latency

### The concept

The current simulator cancels and replaces quotes immediately after a relevant event. A real system has delays. During that delay, an old quote can remain in the book even though the midpoint or latent fair value has changed.

### What we will build

- Add quote-request and quote-arrival events.
- Give cancel and new-order messages configurable delays.
- Allow an old quote to be filled while its cancellation is in flight.
- Track quote age when a fill occurs.
- Compare markouts for fresh and stale quotes.

### Design question

The event queue will need stable ordering when two events have the same timestamp. We should define a sequence number so results do not depend on incidental Python object ordering.

### Acceptance checks

- Zero latency reproduces the current simulator.
- Positive latency cannot process a quote before its submission time.
- Pending cancellations can still receive fills.
- Seeded runs remain deterministic.
- Markouts can be grouped by quote age.

## Stage 6: improve queue-position realism

### The concept

The matching engine already applies FIFO within a price level. The missing part is empirical queue placement. When the maker joins a price, it should sit behind displayed quantity that arrived earlier. Some historical feeds also make cancellations and hidden liquidity difficult to infer.

### What we will build

- Record quantity ahead of each maker quote when it joins a level.
- Track how trades and cancellations reduce quantity ahead.
- Report fill probability by initial queue position.
- Compare joining the touch with improving the price by one tick.

### Acceptance checks

- A maker order cannot fill before earlier visible orders at the same price.
- Partial depletion ahead of the maker updates queue position correctly.
- Cancel and replace loses time priority.
- Queue metrics appear in the fill log.

## Stage 7: replay historical order-book data

### Why this changes the status of the project

The current results describe a synthetic market. Historical replay would let us compare the simulator with real message sequences and measure whether its spread, depth, trade-size, cancellation, and markout distributions are plausible.

### What we will build

- A separate data adapter that converts historical messages into the package's order events.
- A replay mode that does not use the synthetic event generator.
- Data validation for timestamps, unique order identifiers, prices, quantities, and message ordering.
- Empirical calibration reports for spread, depth, event rates, trade sizes, and markouts.
- Clear separation between simulation results and replay results.

LOBSTER is one possible data source. We must check licensing and redistribution rules before committing any raw data. The repository should contain download or preparation instructions rather than restricted data.

### Acceptance checks

- A tiny legally shareable fixture reproduces a known final book exactly.
- Replay is deterministic.
- Bad messages fail with useful errors.
- Synthetic and historical modes use the same accounting and analytics where possible.
- The README states the instrument, date, trading hours, and filters used for any empirical claim.

## Stage 8: implement Avellaneda-Stoikov as a comparison strategy

### The concept

The current rule is intentionally simple:

```text
reservation price = midpoint - gamma * inventory
quotes = reservation price plus or minus a fixed half-spread
```

Avellaneda-Stoikov links reservation price and optimal spread to risk aversion, volatility, time remaining, and fill intensity. It is useful because it provides a more formal benchmark, not because an advanced formula is automatically better.

### What we will build

- A strategy interface shared by the current linear strategy and the new strategy.
- Volatility and arrival-intensity estimators with explicit assumptions.
- Time-horizon handling.
- Side-by-side experiments under common paths.
- Sensitivity analysis for estimated parameters.

### Acceptance checks

- The current linear strategy produces unchanged baseline results.
- Dimensional units are documented for every formula.
- Extreme parameters are validated and tested.
- Comparisons use the same market paths.
- Results distinguish model-estimated inputs from fixed assumptions.

## Stage 9: optional C++ matching path

### Why this is optional

The local Python benchmark is useful for profiling, but faster matching does not make the market model more realistic. Historical validation should come first unless you are targeting a quant-developer role that places more weight on systems performance.

### What we will build

- A small C++ matching core with the same observable behavior as `OrderBook`.
- Python bindings using an appropriate binding library.
- Differential tests that feed identical order streams to both engines.
- Benchmarks for throughput, cancellation, matching, and memory use.

### Acceptance checks

- Python and C++ produce identical trades and final depth for generated order streams.
- Benchmarks state the machine, compiler, flags, Python version, workload, and number of repetitions.
- The Python reference implementation remains available for clarity.
- No performance number appears on the CV until it has been measured reproducibly.

## What we should build in the next guided session

The next session should combine the learning notebook with the design of aggregate markouts:

1. Recreate three matching examples by hand.
2. Build the first notebook cells around those examples.
3. Run seed 42 and inspect one informed and one uninformed fill.
4. Sketch the table needed for session-level markout aggregation.
5. Write the aggregation tests before running the full 200-session report.

The first code change should be small. We should not start a costly sweep until the output schema, sign convention, grouping unit, and tests are agreed.

## How each stage affects the CV

| Stage | CV effect |
|---|---|
| Notebook | Better demonstration, usually no new bullet |
| Aggregate markouts | Stronger adverse-selection claim if supported |
| Wider spread sweep | Better research discussion, even with a negative result |
| Fees and rebates | Supports gross-versus-net economics discussion |
| Latency | Supports stale-quote and event-system claims |
| Queue position | Supports more realistic execution modelling claims |
| Historical replay | Supports empirical validation claims |
| Avellaneda-Stoikov | Supports strategy-comparison claims |
| C++ engine | Supports measured systems-performance claims |

The rule is simple: code creates a feature, tests create confidence, and experiments create evidence. The CV can claim only the last of those that actually exists.
