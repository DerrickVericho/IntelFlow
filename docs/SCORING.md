# Scoring Specification

| Field | Value |
|---|---|
| Status | Implemented draft hypothesis; calibration pending |
| Version | draft-v0.7 |
| Last updated | 2026-09-27 |

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

- **Liquidity (30%)**: estimated daily transaction value in IDR against a
  Rp5 billion per day benchmark for entry and exit capacity.
- **Foreign accumulation / distribution (30%)**: top-five foreign-investor
  broker net balance, weighted by observed foreign participation. Positive-day
  counts and gross pressure remain context only.
- **Broker accumulation / distribution (40%)**: top 3/5 ranked net balance,
  daily accumulation over the 20 trading observations, and accumulated net
  value relative to all-broker buy value. Top 10 remains context only.

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

## Implemented normalization — draft-v0.7

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
not the component formulas or weights. Published scores are bounded to 0–100
and rounded to two decimals; calculations use dated evidence rather than an
LLM. The foreign and broker direction functions reach their bounds through
explicit thresholds, without clipping negative score results after calculation.

### Flow

The IntelScore score uses the last 20 observed trading dates. Tabs change the
evidence window only. The 20-day volume baseline remains chart context and is
not a scoring prerequisite.

- Liquidity: for each date, estimate IDR transaction value as closing price
  multiplied by traded shares. Score `clip(100 * estimated_IDR / 5,000,000,000)`
  and average the available dated scores. A zero-share day scores zero; an
  invalid closing price is unavailable. This is a proxy, not exact trade-by-
  trade turnover, and the Rp5 billion threshold is a user-defined hypothesis.
- Foreign: request the 20-day top-broker ranking with `foreign=true`,
  `cohort=all`, and `origin=all`. This ranking is ordered by investor-origin
  `foreign_net_idr`; calculate the top-five buyer/seller ratio from that field,
  **not** the overall `net_idr`. Let `balance = (buyer_net + seller_net) /
  (abs(buyer_net) + abs(seller_net))`. `direction(balance)` is 0 at or below
  −0.25, 100 at or above +0.25, and `50 + 200 × balance` between those
  thresholds. Missing or zero total ranked net is unavailable. Participation
  is the mean of available dated provider `foreign_share` fractions, scaled
  as `min(max(mean_share / 0.40, 0), 1)`. Final score is
  `(1 − participation) × 50 + participation × direction`. Thus low foreign
  turnover dampens directional evidence toward 50; 40% participation allows
  the full 0–100 range. Gross buy/sell pressure and positive-day consistency
  are not scored. The provider's `foreign_share` is foreign investor share of
  two-sided stock turnover, not a retail or broker-origin designation.
- Broker: calculate independent 5-day and 20-day windows. Each window obtains
  its own overall top-broker ranking so a recently active broker is not hidden
  by the longer ranking. For N=3 and N=5, take its ranked net buyers and
  sellers and calculate `balance` as above. Broker `direction` is 0 at or below
  −0.20, 100 at or above +0.20, and `50 + 250 × balance` between those
  thresholds. For every available daily broker row in that window, add net
  values of **both** selected buyer and selected seller broker groups. Let
  `consistency = 100 × positive_days / (positive_days + negative_days)`;
  zero-net dates are excluded, and all-zero dates give 50. Let
  `period_balance = sum(daily_group_net)`, `total_transaction =
  sum(daily_all_broker_buy_IDR)`, and `strength = min(abs(period_balance) /
  total_transaction / target, 1)`, with targets 5% for top 3 and 8% for top
  5. `concentration = 50 + 50 × strength` when period balance is positive,
  otherwise `50 − 50 × strength` when negative (50 if zero). Each slice is
  `0.50 × direction + 0.30 × consistency + 0.20 × concentration`; the broker
  window score averages both slices. Final Broker Flow is `65% × 5-day score +
  35% × 20-day score`. A nonpositive transaction denominator is unavailable.
  Missing daily dates are excluded, not assigned zero. Require at least four
  recent observations for the 5-day calculation. This remains broker activity
  across all investors, not investor-origin attribution.

All three components, 20 price/trading dates, and at least 16 dated observations
each for foreign flow, valid IDR liquidity proxy, and 20-day broker activity,
plus at least four of five recent broker observations, are required for an
aggregate Flow Score. A 16–19-date long component or four-date recent broker
component remains numeric with a partial-coverage explanation. Lower coverage,
missing components, or invalid/mismatched broker rankings leave Flow and
Combined Scores null.
Available components remain visible. The weights remain 30/30/40. These
formula changes advance the version to `draft-v0.7`.

### Fundamentals

- Growth: average `clip(50 + annual_YoY_percentage_points)` for revenue and
  earnings. Require consecutive years and a positive prior denominator.
  Undated quarterly YoY snapshots are displayed only, not scored.
- Earnings: for earnings, net/operating margin, ROA and ROE, level scores are
  100/50/0 for positive/zero/negative. Where consecutive years and a nonzero
  prior value exist, average the level score with
  `clip(50 + 50 * (latest - prior) / abs(prior))`. Then average available metrics.
- Cash flow: take the three latest reported financial years. Score each available
  annual OCF and FCF observation as 100/50/0 for positive/zero/negative, plus
  `clip(50 * OCF / earnings)` when earnings are positive. Average the scored
  observations, dividing by their actual count. An unavailable metric or year
  contributes neither a zero nor a denominator. Capex is context only.
- Valuation: take the three latest valuation years. For every positive
  PE/PB/PS/PCF observation, compare it against the median of at least two
  earlier positive annual observations of the same ratio:
  `clip(100 * median / (median + observation))`. Require a positive annual
  earnings/equity/revenue/OCF denominator respectively for that observation's
  year or the preceding year. Exclude ratios with nonpositive or missing
  denominators. Average all eligible dated observations, dividing by their
  actual count; peer averages remain context only. Positive but unusually high
  ratios retain a small score instead of being flattened to zero.

Require at least two fundamental components. Available component weights are
renormalized; original weights and unavailable components remain visible.
The component `reason` describes missing evidence; missing values never become
zero. Combined Score requires both aggregates, using the unchanged 60/40 weights.
The cash-flow and valuation observation rules and valuation normalization change
the formula, so the calculation version advances from `draft-v0.3` to
`draft-v0.4`. The four Fundamental Score weights are unchanged. A displayed
zero remains a valid score when all available observations score zero; it is not
an unavailable state.

### Limits to validate before demo

These normalizations are transparent first-pass hypotheses, not calibrated
predictors. More trading activity can accompany distribution, and positive
cash flow has different significance across sectors. A positive annual
denominator is a conservative check, not verification of the exact provider
valuation denominator (which may use a trailing period). Compare representative
tickers before declaring the scoring version final. No confidence score is added.


## Display interpretation and data confidence (2026-09-27)

This is a frontend presentation policy. Numeric formulas, eligibility rules,
weights and the research-state matrix are unchanged by these
display rules. The backend
research-state string remains available; the UI uses the explicit summary below.

| Existing score | Display band |
|---|---|
| Null | Unavailable |
| 0 to below 50 | Weak |
| 50 to below 60 | Neutral |
| 60 to below 70 | Positive |
| 70 to 100 | Strong |

These bands are explanatory labels, not calibrated predictions or recommendations.
They apply consistently to Overall, Flow, Fundamental and component values.
Neutral uses the additional research-context label Watch. A component's position
on a progress indicator represents its existing score; it is not recomputed.

Key driver identifies the two highest available component scores, with their
values. Strong support is used only when both are at least 70. This is a summary
of component support, not a claim about exact weighted contribution or causality.
Main risk prioritizes unavailable Flow/Fundamental coverage, then flagged stale
sources, then the lowest available component. Positive/strong weakest components
are described as relative limitations, not invented negative evidence.

Data confidence is a categorical coverage/freshness label, not a numerical score
or probability. It cannot change any score:

- Low: an aggregate is null, any source is flagged stale, status is stale,
  trading history is incomplete or has fewer than 20 distinct price dates,
  foreign flow is missing any corresponding date, or a scored component is null.
- Medium: no Low condition, but partial status, missing inputs, missing expected
  components, or missing dates/periods for price, broker, foreign, financial or
  valuation sources.
- High: all above coverage checks pass. This means no source is flagged stale;
  it does not assert real-time data or investment certainty.

The current contract has no dated score-history snapshots. The Overall Score
card omits prior-week and prior-month comparison rows; the separate Overall
Score trend remains explicitly unavailable.
Never infer historical scores from historical prices, current components,
annual financial values, browser visit history, or the evidence-period controls.
