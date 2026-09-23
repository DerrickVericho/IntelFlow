# IntelFlow Backend API Contract

Status: implemented, living contract. Update this file, public models, frontend
types, and tests together when endpoints change. The executable schema is
`GET /openapi.json`; interactive documentation is at `/docs`.
Provider contracts are separately documented in `docs/API.md`.

## Endpoints

All requests are GET. Research paths are prefixed with `/api/v1/stocks/{symbol}`.
Symbols must contain exactly four letters; lowercase and an optional `.JK` suffix
are accepted. Responses normalize to uppercase without suffix.

| Path | Input | Output |
|---|---|---|
| `/health` (outside the prefix) | None | `status`, `dependencies.redis`; 503 if Redis unavailable |
| `/intel-score` | Symbol | Company, three scores, key points, full 20-observation flow block, fundamentals, provenance |
| `/flow` | Required `window=1d/5d/20d` | Same flow block, using last 1/5/20 observed trading dates |
| `/price-history` | Required `range=1w/1m/3m` | OHLC/volume series; effective dates and incomplete-history flag |
| `/shareholders` | Optional `year`, defaults to current Jakarta year | Monthly holdings, category definitions, totals and counts |
| `/broker-series` | Required `range=1w/1m/3m`; optional comma-separated `brokers` | Default and selected brokers, available codes, daily/cumulative flow series |

Market chart ranges are trailing 7/30/90 calendar days inclusive, ending no
later than the current UTC date. Before 07:00 WIB this is the previous Jakarta
calendar date. Response `as_of` still comes from the latest observed trading
date, not from the requested range end. Shareholder years use Jakarta time.
No endpoint calls a paid source for malformed query input. Home can navigate to
IntelScore using the user's ticker without an extra search endpoint.

## Common analytical envelope

| Field | Type / meaning |
|---|---|
| `symbol` | Normalized ticker |
| `as_of` | Latest observed market/snapshot date, nullable for empty datasets |
| `status` | `complete`, `partial`, or `stale`; partial takes precedence |
| `missing_inputs[]` | `{key, reason}`; includes unavailable score components |
| `sources[]` | `{key, provider, as_of, period, fetched_at, effective_start, effective_end, is_stale}` |

Date fields are ISO dates; timestamps are timezone-aware. Retrieval time is
separate from observation date. Undated fundamentals are never labeled with
today's date. Source stale flags remain visible even when status is partial.
Missing values are null, not zero. Percent uses percentage points (12.4 = 12.4%).

## IntelScore payload

| Block | Contents |
|---|---|
| `company` | Nullable `name, sector, sub_sector, last_close_idr` |
| `scores.flow/fundamental/combined` | `value` (0–100 or null), `reason`, `components[]` |
| Score component | `key, value, weight, reason, source_keys[]`; weights are percentages |
| Score metadata | `calculation_version, calculated_at, input_periods, research_state` inside `scores` |
| `key_points[]` | `kind, title, text, source_keys[]`; deterministic evidence/conflict/risk/unavailable text |
| `flow` | Full chart block described below |
| `fundamentals` | Four metric groups described below |

Scores use `draft-v0.2`, with exact rules in `docs/SCORING.md`. They are
research hypotheses awaiting calibration. Scores are calculated on the fixed
20-observation flow window; changing a flow tab changes evidence only.
`input_periods` identifies flow start/end, financial year, and valuation year.

## Flow chart block

`flow` contains `window, effective_start, effective_end, trading_days,
incomplete_history, broker_summary, foreign_flow, liquidity`.

| Chart / card | Data |
|---|---|
| Broker bars/table | `broker_summary.brokers[] = {broker_code, side, rank, buy_idr, sell_idr, net_idr, foreign_net_idr}` |
| Top 3/5/10 comparison | `broker_summary.breadth[] = {top_n, buyer_net_idr, seller_net_idr, balance_idr, balance_ratio, buyer_count, seller_count}` |
| Foreign summary | `foreign_flow.net_inflow_idr, buy_idr, sell_idr, average_foreign_share_percent, positive_days, negative_days` |
| Foreign timeline | `foreign_flow.series[] = {date, net_inflow_idr, cumulative_net_inflow_idr, foreign_share_percent}` |
| Liquidity cards | `liquidity.baseline_window, latest_volume_shares, average_volume_shares, latest_vs_average_ratio` |
| Liquidity timeline | `liquidity.series[] = {date, close_idr, volume_shares, average_volume_shares, volume_ratio, baseline_observations}` |

Top-N compares the N ranked net buyers against the N ranked net sellers, not
net buying of the entire exchange. Seller net values are signed negative.
`balance_ratio = (buyer_net + seller_net) / (abs(buyer_net) + abs(seller_net))`;
zero denominator returns null. Counts expose fewer-than-N results.

Liquidity averages use the 20 preceding observations, excluding the plotted day.
Insufficient history or zero mean produces a null ratio. No actual trading-value
claim is derived from close × volume.

Example liquidity point:

```json
{
  "date": "2026-09-18",
  "close_idr": 8075,
  "volume_shares": 92000000,
  "average_volume_shares": 76500000,
  "volume_ratio": 1.2026,
  "baseline_observations": 20
}
```

## Fundamental chart block

`fundamentals = {reporting_period, currency, groups[]}`.
Each group has `key, label, score, metrics[]`.
Each metric has `key, label, value, unit, period, period_type, availability,
reason, direction, series[], source_keys[]`.

| Group | Metric keys |
|---|---|
| Growth | `revenue_growth_yoy, earnings_growth_yoy, quarterly_revenue_growth_yoy, quarterly_earnings_growth_yoy` |
| Earnings | `revenue, earnings, operating_pnl, net_profit_margin, operating_profit_margin, roa, roe` |
| Cash flow | `operating_cash_flow, free_cash_flow, capital_expenditure, cash_conversion` |
| Valuation | `pe, pb, ps, pcf, pe_peer_avg, pb_peer_avg, ps_peer_avg` |

`series[] = {period, value}` is chronological and preserves null gaps.
Financial and valuation histories are **annual**. Quarterly YoY snapshots have
`period_type: quarterly_yoy_undated`, null period and empty series because the
provider schema supplies no quarter label/history.
Direction is numeric `up/down/flat/unknown`, not a claim of improvement.
Units are `idr/percent/ratio`. A negative valuation may be displayed as evidence
but is excluded from scoring. See scoring documentation for other guardrails.

```json
{
  "key": "revenue_growth_yoy",
  "label": "Revenue growth YoY",
  "value": 12.4,
  "unit": "percent",
  "period": "2025",
  "period_type": "annual",
  "availability": "available",
  "reason": null,
  "direction": "up",
  "series": [{"period": "2024", "value": 8.6}, {"period": "2025", "value": 12.4}],
  "source_keys": ["company_financials"]
}
```

## Additional chart endpoints

| Endpoint | Concrete fields beyond the envelope |
|---|---|
| Price history | `range, effective_start, effective_end, incomplete_history, series[]`; point: `date, open, high, low, close, volume, market_cap` (IDR prices, shares volume) |
| Shareholders | `year, supported_years[], categories[{key,label}], series[]`; point: `date, shares_number, holdings{category: shares}, total_local, total_foreign, shareholder_count, shareholder_count_change` |
| Broker series | `range, effective_start, effective_end, incomplete_history, default_brokers[], selected_brokers[], available_brokers[], series[]`; series: `broker_code, points[]`; point: `date, buy_idr, sell_idr, net_idr, cumulative_net_idr` |

Shareholder years are supported from 2021 to the current year; supported years
are not a promise that a particular symbol has data in all those years.
Category keys preserve `_l/_f` origin. Holdings may not cover all issued shares;
the frontend must not silently normalize them to 100% of issued shares.

Broker selection accepts up to 10 two-character codes. Default selection ranks
positive/negative cumulative net flow over the same retrieved period, taking
three of each. The backend fetches all brokers in cached <=14-day chunks, so
changing selected brokers does not require new upstream calls.
Missing daily broker rows remain null; cumulative values become null after a
gap. Incomplete chunks are reported and never silently treated as zero.

## Error shape

```json
{"error":{"code":"DATA_NOT_FOUND","message":"No observations available.","request_id":"..."}}
```

- 404: no symbol/dataset observations; not conclusive proof the ticker is invalid.
- 422: invalid symbol syntax, window, range, year, or broker selection.
- 503: cache unavailable or required upstream unavailable/rate-limited/invalid.
- 500: unexpected internal error, with a safe message and request ID.

Useful partial results return 200. Raw upstream errors, validation payloads,
credentials and API keys are never returned. `X-Request-ID` matches the error
and log correlation ID. CORS origins are configured through `CORS_ORIGINS`.
