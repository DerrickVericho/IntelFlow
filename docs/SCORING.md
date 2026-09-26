# Scoring Specification

| Field | Value |
|---|---|
| Status | Implemented draft hypothesis; calibration pending |
| Version | draft-v0.2 |
| Last updated | 2026-09-25 |

This document defines the scoring model separately from the product PRD. The
weights and thresholds are provisional and must be validated against sample
ticker data before being frozen for the demo.

## Principles

- Scores range from 0 to 100.
- Flow and fundamentals are calculated independently.
- A combined score never hides the two underlying scores.
- A score of 50 means neutral/mixed evidence; it does not mean missing data.
- Every output includes a calculation version, input dates, and key drivers.

## Scores

### Broker Flow Score

```text
Broker Flow Score =
    30% Liquidity
  + 30% Foreign accumulation / distribution
  + 40% Broker accumulation / distribution
```

Candidate evidence:

- **Liquidity (30%)**: daily volume, trading activity consistency, and a
  turnover proxy where available. Normalize against the stock's own recent
  history rather than all IDX tickers directly.
- **Foreign accumulation / distribution (30%)**: cumulative daily net foreign
  inflow, percentage of positive-flow days, and foreign share of turnover.
- **Broker accumulation / distribution (40%)**: net buy/sell value from the
  ranked top 3, top 5, and top 10 brokers. Score both direction and agreement
  across these ranked slices; stronger buyer-side concentration scores higher than a
  conflicting or distribution-dominated result.

Interpretation rule: broker origin is not investor origin. A foreign broker does
not prove the underlying investor is foreign.

### Fundamental Support Score

```text
Fundamental Support Score =
    30% Growth
  + 25% Earnings quality
  + 25% Cash-flow quality
  + 20% Valuation
```

Candidate evidence:

- **Growth (30%)**: year-over-year quarterly revenue and earnings growth,
  plus annual revenue, earnings, and EPS direction across available periods.
- **Earnings quality (25%)**: positive earnings, revenue-versus-earnings
  divergence, and company-level net/operating margin, ROA, and ROE trends.
- **Cash-flow quality (25%)**: positive operating cash flow and free cash flow,
  plus operating-cash-flow-to-earnings conversion. Capital expenditure is
  retained as context, not rewarded or penalized on its own.
- **Valuation (20%)**: positive and meaningful PE, PB, PS, and PCF compared with
  the company's own history and available provider peer averages. Forward PE
  is optional context. A negative or zero denominator is unavailable evidence,
  never an automatic "cheap" signal.

The initial model deliberately uses a shallow cross-sector subset. Missing or
economically meaningless metrics are omitted from the applicable calculation,
never converted to zero. Sector-specific accounting models and business-segment
profitability are deferred beyond the MVP.

### Combined Conviction Score

```text
Combined Conviction Score =
    60% Broker Flow Score
  + 40% Fundamental Support Score
```

The default is flow-first. If user-adjustable weights ship, they must total 100%,
remain visible, and label the resulting combined score as customized.

## Research-state matrix

Use 60 as the initial high/low boundary. This threshold is provisional.

| | Fundamental >= 60 | Fundamental < 60 |
|---|---|---|
| Flow >= 60 | Accumulation with fundamental support | Speculative or event-driven flow |
| Flow < 60 | Fundamentally supported, flow unconfirmed | Weak or inconclusive setup |

The state is explanatory. It never replaces numeric scores.

## Validation plan

1. Select several liquid and less-liquid stocks with different flow profiles.
2. Calculate raw features before finalizing normalization.
3. Check whether the scores match inspectable underlying evidence.
4. Test stale data, missing segments, and bank/non-bank behavior.
5. Version formula changes and lock a version before final demo recording.

## Implemented normalization — draft-v0.2

The original weights remain unchanged. The implementation has three public
calculation steps:

1. `calculate_flow_score()` builds the Flow Score.
2. `calculate_fundamental_score()` builds the Fundamental Score.
3. `calculate()` combines both scores and adds the research state and metadata.

These functions live in `src/backend/scoring/flow.py`,
`src/backend/scoring/fundamentals.py`, and
`src/backend/scoring/research.py`. Individual component formulas live in
`src/backend/scoring/components.py`; shared score aggregation lives in
`src/backend/scoring/utils.py`. This separation changes code ownership only,
not the formula, weights, thresholds, or `draft-v0.2` version. All scores are
clipped to [0, 100], rounded to two decimals; calculations use dated evidence
rather than an LLM.

### Flow

The IntelScore score always uses the last 20 observed trading dates. Tabs only
change the evidence window. Daily data supplies up to 90 calendar days, with
20 preceding observations needed for each volume baseline.

- Liquidity: mean of `clip(50 * volume / preceding_20_observation_mean)` over
  the selected observations. The plotted day is excluded from its baseline.
  A zero baseline or fewer than 20 preceding observations is unavailable.
- Foreign: 70% of `clip(50 + 50 * net / (buy + sell))` plus 30% of
  `100 * positive_flow_days / observed_days`. Require positive foreign turnover.
  Foreign share is displayed as context; it is not a separate score factor.
- Broker: for each N in 3, 5, 10, sum signed net values of the top N net buyers
  and top N net sellers separately. Compute
  `balance = (buyer_net + seller_net) / (abs(buyer_net) + abs(seller_net))`.
  Average `clip(50 + 50 * balance)` across slices with N buyers and N sellers.
  Zero denominators are unavailable. This measures concentration asymmetry;
  it is not the net flow of the whole market, which balances across all brokers.

All three flow components and complete selected-date coverage are required for
the aggregate Flow Score. Any incomplete baseline, missing foreign dates, or
shorter-than-20 research window leaves the aggregate null; charts and component
evidence remain inspectable.

### Fundamentals

- Growth: average `clip(50 + annual_YoY_percentage_points)` for revenue and
  earnings. Require consecutive years and a positive prior denominator.
  Undated quarterly YoY snapshots are displayed only, not scored.
- Earnings: for earnings, net/operating margin, ROA and ROE, level scores are
  100/50/0 for positive/zero/negative. Where consecutive years and a nonzero
  prior value exist, average the level score with
  `clip(50 + 50 * (latest - prior) / abs(prior))`. Then average available metrics.
- Cash flow: average 100/50/0 for positive/zero/negative OCF and FCF, plus
  `clip(50 * OCF / earnings)` when earnings are positive. Capex is context only.
- Valuation: for each positive PE/PB/PS/PCF, compare latest against the median
  of at least two earlier positive annual ratios:
  `clip(50 + 50 * (median - latest) / median)`. Require positive latest annual
  earnings/equity/revenue/OCF respectively; that statement must be no more than
  one year behind the valuation year and must not be from a later year.
  Provider peer averages are context only. Average eligible ratios.

Require at least two fundamental components. Available component weights are
renormalized; original weights and unavailable components remain visible.
The component `reason` describes missing evidence; missing values never become
zero. Combined Score requires both aggregates, using the unchanged 60/40 weights.

### Limits to validate before demo

These normalizations are transparent first-pass hypotheses, not calibrated
predictors. More trading activity can accompany distribution, and positive
cash flow has different significance across sectors. A positive annual
denominator is a conservative check, not verification of the exact provider
valuation denominator (which may use a trailing period). Compare representative
tickers before declaring the scoring version final. No confidence score is added.
