# Backend readiness for frontend integration

Status: implemented draft backend. The comprehensive IntelScore screen has an
endpoint and typed data for every agreed MVP block. Provider coverage for each
IDX ticker still depends on available dated inputs.

## Field-level frontend audit

| Frontend requirement | Endpoint / fields | Result |
|---|---|---|
| Symbol/company header | `intel-score.company`, envelope symbol and sources | Ready; identity may be null on partial Company Report failure |
| Flow/Fundamental/Combined cards | `scores.*.value`, components, reasons, version, periods | Ready; null is explicit when minimum evidence is absent |
| Top accumulating/distributing brokers | `flow.broker_summary.brokers[]` | Ready; signed IDR, buy/sell values, ranks and broker codes |
| Top 3/5/10 comparison | `flow.broker_summary.breadth[]` | Ready; buyer and seller sums, counts, signed balance and ratio |
| Recent broker scoring evidence | `flow.broker_summary_5d` | Ready; independently ranked 5-day Top 3/5 evidence, weighted 65% against 35% for 20-day evidence |
| 1D/5D/20D evidence tabs | `/flow?window=...` | Ready; same block as initial research response |
| Foreign flow chart and cards | `flow.foreign_flow.series[]`, totals, day counts | Ready; investor origin kept distinct from broker origin |
| Liquidity chart and cards | `flow.liquidity.series[]`, latest volume/ratio | Ready; 20 preceding observations required for each baseline |
| Fundamental cards/sparklines | `fundamentals.groups[].metrics[].series[]` | Ready for annual history; quarterly snapshots deliberately undated |
| Research key points | `key_points[]`, source references | Ready; deterministic synthesis, no LLM requirement |
| Source freshness / missing states | `sources[]`, `missing_inputs[]`, `status` | Ready; cache fetch time separated from observation date |
| Monthly shareholder stacked bars | `/shareholders` categories/holdings/totals/counts | Backend ready, optional frontend work |
| Price/volume chart | `/price-history` OHLC and volume series | Fixed 3M OHLC consumed by the IntelScore Change over time chart; standalone Stockchart remains optional |
| Default top 3 buyers/sellers and broker selector | `/broker-series` defaults, available/selected codes, series | Backend ready but not requested by the current IntelScore chart; future overlays must account for paid calls and 14-day provider chunks |

The initial IntelScore screen requests the aggregate research response and the
fixed 3M price history. Flow tab changes request only `/flow`; quarterly/annual
report sections remain cached independently. Broker-series remains available
for a future standalone chart or overlay but is not fetched by this screen.

## Reviewable artifacts

- Public contract: `src/backend/API_CONTRACT.md`.
- Machine-readable contract: running backend `/openapi.json`.
- Test-only response data under `src/frontend/tests/data/`; never presented by
  the running application as current market data.
- Original provider samples are tested separately without changing their dates
  or symbol labels.

## Verification and limitations

Automated tests cover provider parsing, normalized response shapes, cache hits,
raw-field retention, corrupted entries, concurrent misses, separate parameters,
nullable/insufficient data, meaningful valuation denominators, source gaps,
invalid queries, upstream errors, console log modes and exception redaction.
An opt-in real Redis test verifies cache survival across gateway recreation.

Verified in this workspace on 2026-09-22:

- 48 tests passed, including the real Redis integration test and all nine local
  provider sample files. One third-party Starlette/AnyIO deprecation warning
  remains; it does not affect the assertions.
- Python compilation and `git diff --check` passed.
- Backend Docker image built successfully using the runtime dependency group.
- Redis and backend started through Compose. `/health` returned healthy Redis.

Reverified locally on 2026-09-23 after the backend cleanup: 58 backend tests
passed with test doubles. Container stdout showed JSON request logs with client
IP and request ID. No live Sectors call was made. The temporary synthetic
frontend stack used for that verification has since been removed.
- The running container's `/openapi.json` lists all five research/chart routes
  and exposes typed nested chart properties.

Remaining work before a production/demo claim:

1. Run a live Sectors smoke test for the full IntelScore inputs. Historical
   shareholder queries for SINI in 2025 and 2024 were checked separately on
   2026-09-27: both returned 12 snapshots, with some historical shareholder
   counts or changes null. This does not validate other symbols or full score
   coverage. Offline fixtures do not prove current provider availability,
   account permissions, or credits for the remaining endpoints.
2. Annual financial history cannot generate a quarterly history chart. The
   latest quarterly YoY values have no confirmed quarter label in the schema.
3. A recent IPO, suspension, short history, or missing broker/foreign observations
   can leave scores null. Charts show available evidence and missing reasons.
4. Financial statement publication dates and same-period valuation denominators
   are not fully supplied. Period and retrieval timestamps are preserved;
   historical statements must not be presented as live financial results.
5. Redis is checked before each paid request, but concurrent misses for the
   same key are intentionally not coalesced. They can spend duplicate credits
   even in one worker; additional workers/replicas increase that chance. This
   is the current latency-over-credit tradeoff, not a guarantee of one call per
   key. Expired Redis entries are not served.
6. Market staleness uses a seven-calendar-day heuristic, and price interval
   coverage is approximate without an authoritative IDX trading calendar.
7. Shareholder totals can cover less than issued shares. The frontend must show
   the coverage instead of silently turning the categories into 100% ownership.

AI/news, peer-comparison pages, revenue-segment analysis and frontend rendering
remain outside this backend milestone.
