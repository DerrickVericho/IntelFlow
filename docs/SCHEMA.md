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
- `ValuationSection`: current values needed by scoring and the typed historical
  valuation rows.
- `FinancialsSection`: quarterly growth, EPS history, historical statement rows,
  and ratio groups used by Fundamental Score.
- Other sections are added only when a feature consumes them.

Dynamic year/date keys are dictionaries, not generated model attributes. For
example, historical EPS can be `dict[str, HistoricalEps]`, and a dated price
extreme can remain `dict[str, int]` until the mapper converts it into a stable
domain record.

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

- Provider schemas live in `src/backend/sectors/schemas/`.
- Stable models consumed by services and scoring live in
  `src/backend/domain/models/`.
- Public request/response models live in `src/backend/api/schemas/`.
- Redis stores versioned raw provider JSON and does not import any financial
  model.
- Frontend types follow IntelFlow HTTP schemas, never Sectors provider schemas.

Tests should validate each model against its corresponding file in
`output-schema/`, include a new unknown field to verify forward compatibility,
and verify that a missing required scoring field produces an explicit error.
