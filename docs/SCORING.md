# Scoring Specification

| Field | Value |
|---|---|
| Status | Draft hypothesis |
| Version | 0.1 |
| Last updated | 2026-09-20 |

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
  across these windows; broad positive net buying scores higher than a
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
  plus consistency across available periods.
- **Earnings quality (25%)**: revenue versus earnings divergence, margin and
  ratio trends, and recurring earnings behavior where the reports support it.
- **Cash-flow quality (25%)**: operating cash flow, free-cash-flow proxy, and
  the relationship between cash generation and reported earnings, subject to
  available statement fields.
- **Valuation (20%)**: PE, PB, PS, dividend yield, payout ratio, and available
  historical or peer context. Peer comparison is allowed only after checking
  that peers are economically comparable; API classification is a starting
  point, not proof.

The calculation must support sector-aware inputs. Banks should use the relevant
financial-sector fields instead of forcing non-financial metrics.

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
