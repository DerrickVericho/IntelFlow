# Sectors Schema Strategy

This is the modeling policy for responses in `output-schema/`. It keeps the
integration typed without reproducing every field returned by Sectors.

## Core rule

Validate the subset needed by IntelFlow before accepting a fresh response into
the cache, but store the complete decoded JSON. On a cache hit, validate the raw
payload again before mapping it. Provider models use Pydantic with
`extra="ignore"`, so a new upstream field does not break parsing and unused
fields do not leak into domain or frontend contracts.

Do not make every field optional. A field is optional only when the samples or
official contract show that it may be missing or `null`. Required inputs for a
calculation should fail validation clearly rather than silently becoming zero.

```text
fresh: Sectors JSON -> provider validation -> Redis raw payload -> mapper
hit:   Redis raw payload -> provider validation                  -> mapper
                                                               -> domain model
                                                               -> scoring / API
```

## Model only what IntelFlow consumes

| Sample | Provider models | Initial typed fields |
|---|---|---|
| Daily transaction | `DailyTransactionRow` | symbol, date, OHLC, volume, market cap |
| Foreign flow | `ForeignFlowResponse`, `ForeignFlowRow` | wrapper dates and all four flow values |
| Top buyers/sellers | `TopBrokersResponse`, `BrokerRankRow` | filters, rank, broker code, total and foreign IDR flows |
| Broker activity | `BrokerActivityResponse`, `BrokerDay`, `BrokerActivityRow` | broker code; buy, sell, net and foreign values/lots used by scoring or UI |
| Free float | `FreeFloatRow` | symbol, company name, free-float ratio |
| Revenue segments | `RevenueSegmentsResponse`, `SegmentEdge` | financial year, source, target, value |
| Shareholders | `ShareholderResponse`, `ShareholderSnapshot` | date, totals, category holdings, shareholder counts |
| Company report | section-specific models | only requested sections and fields described below |

The repeated list wrappers do not need separate business abstractions. A
Pydantic `RootModel[list[...]]` may be used for flat array responses such as
daily transactions and free float.

## Company Report

Do not create one exhaustive model for all eight sections. IntelFlow should
request only the sections required by a use case and model them independently:

- `CompanyReportIdentity`: `symbol`, `company_name`.
- `OverviewSection`: classification, listing information, market cap, latest
  price/date, and only other fields displayed by the product.
- `ValuationSection`: latest price/date, forward PE, and typed historical
  valuation rows. `intrinsic_value` and daily price change are intentionally
  ignored because IntelFlow does not publish target prices and obtains price
  movement from the transaction endpoint.
- `FinancialsSection`: quarterly growth, EPS history, selected historical
  statement rows, and ratio groups used by Fundamental Score. The provider
  schema uses one general cross-sector subset; sector-specific fields remain
  available only in the cached raw payload until a product requirement needs
  them.
- Other sections are added only when a feature consumes them.

Dynamic year/date keys are dictionaries, not generated model attributes. For
example, historical EPS can be `dict[str, HistoricalEps]`, and a dated price
extreme can remain `dict[str, int]` until the mapper converts it into a stable
domain record.

### Selected valuation fields

- Annual `PB`, `PE`, `PS`, and `PCF`.
- Peer averages for `PB`, `PE`, and `PS`.
- Forward PE when available.

Negative or extreme ratios remain in the provider model as evidence but must
not be interpreted as "cheap" automatically. Scoring must first check that the
underlying denominator is positive and economically meaningful.

### Selected financial fields

- Growth: revenue, earnings, EPS history, and quarterly revenue/earnings growth.
- Earnings quality: operating profit, net and operating margins, ROA, and ROE.
- Cash-flow quality: operating cash flow, free cash flow, and capital
  expenditure.
- Balance-sheet sanity: assets, equity, liabilities, debt, cash, debt/assets,
  debt/equity, and current ratio.
- No bank-, insurer-, miner-, or other sector-specific fields are part of the
  initial typed schema.
- Revenue segments may support a later visualization, but segment-level
  profitability is not stored or scored in the MVP.

### Stored inputs and derived metrics

The provider schema stores source facts, not precomputed scores. The first
fundamental mapper/scorer may derive only these compact metrics:

| Area | Stored source fields | Derived metric or check |
|---|---|---|
| Growth | quarterly YoY growth, annual revenue, earnings, EPS | direction and multi-period consistency |
| Earnings | earnings, operating profit, net/operating margin, ROA, ROE | profitability trend and revenue/earnings divergence |
| Cash flow | operating cash flow, free cash flow, capex | positive cash generation and OCF/earnings conversion |
| Balance sheet | assets, liabilities, equity, debt, cash, debt ratios, current ratio | positive equity and leverage/liquidity sanity flags |
| Valuation | annual PE, PB, PS, PCF, peer averages, optional forward PE | current versus own history and provider peer context |

Balance-sheet checks support interpretation and guardrails; they are not a
separate score component in the initial 30/25/25/20 formula.

Every Company Report section on the response envelope is optional because the
API returns only explicitly requested sections.

The financial schema remains provisional until a field-presence matrix has been
generated from representative cached reports across several sectors. The final
selection is based on product use and observed availability, not on one ticker.

## Null and numeric policy

- Keep missing financial values as `None`; never coerce them to zero.
- Use `date` for stable date fields after provider validation.
- Use `int` for IDR, share, lot, volume, and count values where the API returns
  whole numbers.
- Use `float` for ratios and per-share averages unless decimal precision becomes
  a demonstrated scoring requirement.
- Normalize `.JK`, labels, period selection, and sector-specific semantics in a
  mapper, not in provider schemas.

## Boundary rules

- Provider schemas currently live in `src/backend/sectors/schemas/`. They model Sectors
  payloads and must not be reused as public frontend response contracts.
- Stable models consumed by services and scoring live in
  `src/backend/models/`.
- Public request/response models live in `src/backend/schemas/`.
- Redis stores versioned raw provider JSON and does not import any financial
  model.
- Frontend types follow IntelFlow HTTP schemas, never Sectors provider schemas.

The default tests use repository-owned synthetic payloads for every supported
provider operation. They check required fields, forward compatibility with an
unknown field, and rejection of missing or invalid inputs before caching.
They do not read the ignored `output-schema/` directory, so a clean checkout
executes the same checks. The opt-in live Sectors test checks a real historical
Daily Transaction response through the client and gateway; it can consume one
API credit. Local samples remain useful for manual schema research, but are
not a condition for the automated suite to pass.

## Implemented frontend boundary

The async `CachedSectorsGateway` returns validated provider models with their
cache retrieval timestamp. The synchronous `SectorsClient` still returns raw
JSON; its blocking I/O runs in a worker thread. Domain evidence models are split
across `models/common.py`, `flow.py`, `fundamentals.py`, `scoring.py`, and
`research.py`. Public response schemas are similarly grouped under
`schemas/` by endpoint section and remain visible in OpenAPI.

Fundamental histories in the current schemas are annual. Quarterly YoY values
have no confirmed quarter label and must have an empty historical series.
Shareholder `supported_years` means a supported query range, not confirmed
availability for the selected symbol. No quarterly financial history or
synthetic complete ownership breakdown is inferred from the samples.
