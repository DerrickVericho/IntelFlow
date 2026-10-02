# IntelFlow Architecture

This is a working draft. The structure may be simplified or expanded as the
product and API response samples become clearer.

## Core decision

The backend is the authoritative layer for data retrieval, normalization,
caching, and scoring. The frontend communicates with it through HTTP and is
responsible for interaction and visualization.

The backend does not generate chart images. It returns normalized chart series;
the frontend renders line, bar, and composition charts from those values.

```text
User
  -> React frontend
  -> IntelFlow HTTP API
  -> application service
  -> cache or Sectors API
  -> normalization
  -> scoring
  -> JSON response
  -> frontend chart/table/card
```

### Why scoring belongs in the backend

- The Sectors API key remains private.
- Every client receives the same score for the same formula and inputs.
- Formula changes are versioned in one place.
- Sectors responses and API credits can be cached centrally.
- Score evidence can be returned together with its input dates.

The frontend may format values, sort display rows, toggle ranges, and control
visual state. It must not independently reproduce the scoring formulas.

## Sectors integration

`src/backend/sectors/` is the boundary between IntelFlow and Sectors Financial
API v2.

- `gateway.py` defines the operations required by the application.
- `client.py` handles HTTP transport, authentication, parameters, logging, and
  upstream error mapping.
- `src/backend/exceptions/sectors.py` defines failures that callers can handle
  without depending on `requests` exceptions.
- `src/backend/sectors/schemas/` describes the reviewed Sectors response payloads.
  These provider schemas contain only fields used by IntelFlow and must not
  become the application's public frontend models.
- Representative outputs for all eight selected endpoints are stored in
  `output-schema/`; the modeling policy is defined in `docs/SCHEMA.md`.

The HTTP client returns raw decoded JSON. The async cached gateway validates
and returns typed provider models with their original fetched timestamps.
It contains no scoring formulas.

```text
Application service -> SectorsGateway -> CachedSectorsGateway
                                      -> cache hit
                                      -> SectorsClient -> Sectors API
```

`SectorsClient` remains responsible only for HTTP communication. Cache behavior
is added by a gateway wrapper so the client is still usable and testable without
a cache.

Market-data requests use a shared safe range end no later than the UTC calendar
date. This prevents a new Jakarta date from being sent before UTC midnight,
when the Daily Transaction endpoint can reject future `end` dates with 400.
The service uses one end date for its daily and foreign inputs, and the gateway
applies the same bound before any paid request. The latest observed trading
date remains separate from this requested range end.

Implemented async strategy: Redis uses its async client; synchronous requests
transport runs through `asyncio.to_thread`. Each worker thread owns a requests
Session, so concurrent upstream calls do not share mutable Session state. The
gateway checks Redis first but does not serialize cache misses: concurrent
requests for the same uncached key may both spend a Sectors credit. A response
cached before the later request's lookup is still reused. This favors response
latency over miss coalescing for the current small user base; Redis remains
required, and rate/credit limits still apply. No process-local or distributed
request lock is currently used.

## API application

- `src/backend/main.py` assembles the FastAPI application and exposes `/health`.
- `src/backend/middleware.py` owns request correlation, client IP, timing and
  access logging. `src/backend/exceptions/registry.py` registers safe handlers.
- `src/backend/logger.py` owns console formatting and request context: readable
  colored text in development, JSON lines in production.
- Future feature routes should be added as separate routers and registered by
  the app factory rather than implemented directly in `main.py`.

The research router is `api/routes.py`. Public schemas and domain models are
split by product section. The route-compatible `ResearchService` facade inherits
focused service classes for flow, aggregate IntelScore, price history,
shareholders, and broker series. Shared provider/date helpers live in
`services/base.py`. Routes are implemented for all five research/chart use
cases. See `docs/BACKEND_READINESS.md` for coverage.

Run locally with:

```powershell
uv run uvicorn src.backend.main:app --reload
```

## Backend responsibilities

The backend should be split by responsibility rather than placing all behavior
inside route handlers.

```text
src/backend/
├── main.py                 # FastAPI app construction and health
├── middleware.py           # Request logging, correlation and client IP
├── logger.py               # Console text or JSON logging
├── api/routes.py           # Thin research HTTP routes
├── schemas/                # Public HTTP request/response models by section
├── models/                 # Stable normalized domain models by section
├── exceptions/             # Typed failures and HTTP handler registry
│   ├── base.py
│   ├── cache.py
│   ├── configuration.py
│   ├── research.py
│   ├── registry.py
│   └── sectors.py
├── services/
│   ├── research.py          # Existing route-facing service facade
│   ├── base.py              # Shared provider access and date helpers
│   ├── flow.py              # Flow evidence by trading window
│   ├── intel_score.py       # Aggregate company research and scores
│   ├── prices.py            # OHLC and volume history
│   ├── shareholders.py      # Monthly shareholder composition
│   ├── brokers.py           # Ranked broker timelines
│   └── utils.py             # Pure service-level normalization and date helpers
├── sectors/
│   ├── client.py           # Raw Sectors HTTP implementation
│   ├── gateway.py          # Contract used by services
│   ├── cached.py            # Typed cache-first implementation
│   ├── adapters.py          # Operation-to-provider-schema validators
│   ├── types.py             # Shared Retrieved[T] result contract
│   ├── utils.py             # Request, cache-key, TTL, and validation helpers
│   ├── mapper.py            # Converts provider payloads into domain models
│   └── schemas/             # Partial Sectors provider response models
├── scoring/
│   ├── research.py          # Combines scores and returns research metadata
│   ├── flow.py              # Builds the Flow Score
│   ├── fundamentals.py      # Builds the Fundamental Score
│   ├── components.py        # Calculates individual evidence components
│   └── utils.py             # Shared score aggregation and numeric helpers
├── cache/                   # Cache interface and Redis implementation
└── tests/
```

The scoring package exposes three calculation steps: flow, fundamentals, and
their combined result. Component formulas remain small pure functions, while
the top-level research calculation only coordinates results and metadata.
Every backend function, including test helpers, annotates every parameter and
its return type. This makes dependencies and nullable results visible at the
function boundary and allows static analysis without inferring runtime intent.

### Backend layer boundaries

| Layer | Responsibility | Must not do |
|---|---|---|
| Routes | Validate HTTP input and return response schemas | Call Sectors directly or contain formulas |
| Services | Coordinate a complete use case | Know frontend rendering details |
| Sectors | Retrieve upstream data and map upstream errors | Calculate product scores |
| Domain models | Represent normalized IntelFlow concepts | Depend on HTTP or frontend details |
| Sectors mapper | Convert provider schemas into domain models | Perform HTTP calls |
| Scoring | Pure deterministic calculations and evidence | Access secrets or make network calls |
| Cache | Store and retrieve serialized values by key and TTL | Know scoring or HTTP-route behavior |

### Schema ownership

IntelFlow intentionally uses three schema categories rather than one shared
`schemas/` directory:

| Schema | Location | Used by |
|---|---|---|
| Sectors provider payload | `sectors/schemas/` | Sectors gateway and mapper |
| Internal domain model | `models/` | Services, scoring, and domain-result cache |
| Public HTTP request/response | `schemas/` | FastAPI routes and frontend contract |

This prevents a field change from Sectors from automatically changing the
public API. Cache implementations are generic and do not own financial schemas;
they serialize either a provider payload or a domain result as selected by the
caller. The frontend keeps generated or handwritten TypeScript types matching
only the public HTTP schemas.

Files inside `models/` and `schemas/` follow the product section they
represent. Only strict base records, provenance, and response-envelope fields
belong in `base.py` or `common.py`. Backend exception classes live in
`exceptions/` by subsystem rather than inside configuration, services, cache,
or provider transport modules.

### Initial backend workflow

For a request such as `GET /api/v1/stocks/BBCA/broker-flow?range=5d`:

1. Route validates the symbol and range.
2. Service selects the last 5/20/60 observed price dates, then uses actual
   first/last price dates for the ranking.
3. Service requests period top brokers and daily broker activity in at most
   14-calendar-day chunks.
4. A cached Sectors gateway checks the cache before delegating a paid request
   to the HTTP client.
5. Raw responses are normalized into internal records.
6. The service aligns daily net-lot quantities with price dates and converts
   them to shares. A missing broker in a reported daily summary counts as zero
   activity; a missing whole day creates a gap. Subsequent cumulative totals
   sum reported days only.
7. Route returns a stable chart response without calculating scores.

## Backend HTTP contract

The product-facing endpoints expose synthesized IntelFlow use cases rather than
mirror Sectors paths one-for-one. The first contract is:

| Endpoint | Scope |
|---|---|
| `GET /health` | Infrastructure health only |
| `GET /api/v1/stocks/{symbol}/intel-score` | Complete initial IntelScore payload |
| `GET /api/v1/stocks/{symbol}/flow?window=1d\|5d\|20d` | Window-specific flow evidence |
| `GET /api/v1/stocks/{symbol}/shareholders?year=YYYY` | Nice-to-have shareholder chart data |
| `GET /api/v1/stocks/{symbol}/price-history?range=1w\|1m\|3m` | Nice-to-have price/volume series |
| `GET /api/v1/stocks/{symbol}/broker-series?range=1w\|1m\|3m&brokers=YP,BK` | Nice-to-have selectable broker series |
| `GET /api/v1/stocks/{symbol}/broker-flow?range=5d\|1m\|3m` | Overlaid OHLC and broker net-share series, period ranks and daily top-five quantities |

The concise living client contract lives in `src/backend/API_CONTRACT.md`.
Detailed frontend field requirements, call triggers, and Sectors input mapping
live in `PLAN.md`. Public Pydantic schemas become the executable contract when
implementation starts; all three must remain synchronized.

The aggregate IntelScore endpoint prevents the browser from coordinating raw
provider requests. Window-specific flow is separate so changing a tab does not
reload company fundamentals. Price history and broker series are also separate
because broker selection changes more often than price history.

Chart responses contain normalized numeric values, dates, units, and source
freshness. The frontend chooses line, candlestick, area, or bar presentation
without changing the underlying data.

For 1-month and 3-month broker series, the backend splits Sectors Broker
Activity requests into non-overlapping chunks no longer than 14 days, caches
them independently, merges dates, and filters broker codes locally. The
frontend never knows about this provider constraint.

## Frontend responsibilities

The frontend MVP is implemented using Vite, React, TypeScript, React Router,
TanStack Query, modular Apache ECharts (SVG renderer), and Tailwind CSS v4 through
the official Vite plugin. The npm package and lockfile live at the repository root; the Vite root is `src/frontend`.
Routes are `/`, `/intel-score`, and `/stocks/:symbol/intel-score`. The research
route is lazy-loaded so Home does not load chart code before navigation.

The browser uses only same-origin `/api/v1/stocks/...` URLs. Vite proxies to the
local IntelFlow backend on port 8000.
Production Nginx proxies `/api/` to `backend:8000` and serves the SPA with deep-link
fallback. No browser configuration includes Sectors credentials or provider URLs.

Query keys include symbol and, for evidence, the window. One initial aggregate
request supplies scores, fundamentals and 20D evidence. The 1D/5D controls fetch
only the flow endpoint; returning to 20D reuses the aggregate. A separate
`price-history` query key contains the symbol and fixed 3M range and feeds the
Change over time candlestick chart without changing score state. The browser
does not request `broker-series` for this chart. Query cancellation passes
AbortSignal to fetch; data is not carried over between query keys.
Browser query cache freshness (five minutes) is independent of backend source
staleness. Retry, focus refetch and reconnect refetch are disabled to avoid
implicit repeat requests. Missing values remain null. The frontend presentation layer maps existing scores
to documented bands and coverage categories without altering score arithmetic.

The page PDF builder is lazy-loaded when Save as PDF is clicked. It captures
the dedicated IntelScore content wrapper, excluding the application shell and
export button, as a high-resolution image and tiles it across A4 PDF pages.
Desktop-width captures use landscape orientation while narrow captures use
portrait. The current theme, charts, tables, and evidence window are preserved
visually; text is rasterized. PDF generation is local to the browser and adds
no Sectors or backend request.

The running frontend has no synthetic data mode. Unit and browser tests isolate
the HTTP contract with test-only response data; the normal Compose stack uses
the backend and its cache. See `docs/FRONTEND.md` for run instructions.

```text
src/frontend/
├── app/                    # App bootstrapping, routes, and shared layout
├── pages/
│   ├── HomePage
│   ├── IntelScorePage
│   ├── ShareholderCompositionPage
│   └── BrokerFlowPage
├── features/
│   ├── symbol-search/
│   ├── scores/
│   ├── broker-flow/
│   ├── price-chart/
│   ├── shareholders/
│   └── fundamentals/
├── components/             # Shared cards, tables, loading and error states
├── api/                    # IntelFlow backend HTTP client functions
├── types/                  # Frontend response types matching backend schemas
└── utils/                  # Display-only formatting helpers
```

### Initial pages

1. **Home** explains IntelFlow, accepts one IDX symbol, and leads into the
   primary analysis.
2. **IntelScore — MVP** shows company identity, Flow Score, Fundamental Score,
   Combined Score, key points, charts, evidence, and data dates.
3. **Shareholder Composition — nice to have** renders monthly stacked
   composition and shareholder-count changes.
4. **BrokerFlow — implemented draft** shows synchronized 5D, 1M, or 3M stock OHLC
   candlesticks and cumulative daily net-share lines for each period's
   independently ranked top-five buyer and seller brokers overlaid in one
   chart area. Price uses the left axis and share quantity the right axis;
   horizontal net-IDR rankings follow below. The browser
   consumes a backend contract; the backend combines the Sectors top-broker
   ranking with daily broker activity retrieved in at most 14-calendar-day
   chunks. Its full-width chart opens a dated top-five buyer/seller net-share
   dialog when a date is selected. The page does not recalculate scores.

### Frontend data rules

- The selected symbol should live in the URL so pages can be bookmarked, for
  example `/broker-flow/BBCA`.
- Page components call functions from `api/`; they do not call Sectors.
- Components render backend values and do not recreate score formulas.
- Loading, invalid-symbol, upstream-error, and unavailable-data states must be
  explicit.
- Dates and units are display concerns, but financial values must not be
  silently changed or imputed.

## Chart ownership

| Concern | Backend | Frontend |
|---|---:|---:|
| Fetch Sectors price/shareholder data | Yes | No |
| Cache paid responses | Yes | No |
| Normalize dates and numeric fields | Yes | No |
| Select requested range | Yes | Sends the requested range |
| Calculate score or evidence | Yes | No |
| Choose chart type/colors/layout | No | Yes |
| Tooltip and chart interaction | No | Yes |
| Format IDR, percentages, and labels | Returns raw value/unit | Yes |

## Data and cache strategy

For the hackathon MVP, use Redis behind a small cache interface. API calls cost
credits and the backend is restarted frequently during development, so a
process-local cache no longer provides sufficient protection.

```text
CacheStore
├── get(key)
└── set(key, value, ttl_seconds)

Implementation -> RedisCache
```

Use one application-level Redis client/connection pool, created during FastAPI
startup and closed during shutdown. Configure it with `REDIS_URL`; do not embed
hostnames or credentials in source code. Redis persistence is optional because
cached Sectors data can be fetched again, but the Redis container should use a
named volume if cache survival across Redis container recreation is desired.

Local Redis is provisioned by `compose.yaml`, bound only to `127.0.0.1`, with a
healthcheck, append-only persistence, and a named volume. Redis is a required
backend dependency: FastAPI pings it during startup and aborts startup with a
clear error when it is unavailable. This prevents an unnoticed cache outage
from turning every request into a paid Sectors call.

For the first implementation, cache the complete decoded Sectors provider
payload after minimal provider-schema validation. Keep domain mapping and
scoring outside the cached gateway:

```text
First equivalent request  -> fetch -> validate -> cache raw payload -> map -> score
Repeated equivalent call  -> cache raw payload -> validate           -> map -> score
```

This directly saves Sectors API calls while keeping deterministic calculations
cheap and current with the deployed formula. A separate cache for normalized or
scored results should only be added later if measurement shows it is useful.

Cache keys must use canonical parameters and include endpoint, normalized
symbol, requested sections, effective dates, and a cache version. Sort list-like
parameters such as Company Report sections before constructing the key.
Different windows such as 1D, 5D, and 20D must never share an ambiguous cache
key. A shape such as `intelflow:sectors:v1:<operation>:<sha256(params)>` avoids
oversized keys while keeping invalidation versioned.

Initial TTL guidance:

| Data | Draft TTL |
|---|---:|
| Current daily price, broker flow, foreign flow window | 6 hours |
| Date-bounded market/flow window ending more than 7 days ago | 30 days |
| Shareholder composition for the current year | 7 days |
| Shareholder composition for prior years | 90 days |
| Free-float list | 7 days |
| Company Report: overview or valuation | 12 hours |
| Company Report: financials, ownership, management, peers | 14 days |
| Revenue segments | 30 days |

These TTLs are product defaults, not claims about Sectors update frequency, and
should be adjusted after observing the actual endpoint refresh behavior. Do not
give the complete Company Report one long TTL: `overview` and `valuation`
contain price-sensitive fields, while statement and ownership sections change
far less frequently. Do not cache authentication, validation, rate-limit, or
unexpected upstream errors.
Historical score snapshots and a permanent database are deferred until the
basic analysis flow works.

## Logging and operations

- Application logs go only to stdout. `APP_ENV=development` produces readable
  colored text on a terminal; `APP_ENV=production` produces JSON lines.
- Request correlation IDs, route, status, latency, cache outcome, and safe
  upstream error categories are recorded where relevant. Request logs also
  include the direct client IP; trusted-proxy configuration is required before
  interpreting forwarded addresses. Routine `/health` checks are omitted from
  access logs to avoid container log noise.
- API keys, authorization headers, credentials, and complete financial-response
  bodies must never be logged.
- Container log collection and retention are handled by the runtime; no backend
  log volume is mounted.
- Exception logging includes type and stack locations only, avoiding exception
  values and source-code lines that could reveal credentials or raw payloads.
- Metrics, traces, dashboards, and alerting are future improvements. The first
  useful measurements are route latency, cache outcomes,
  Sectors call count/credit use, upstream failures, and source freshness. The
  existing request and cache logs are the current operational baseline.

## Deployment

- The backend and frontend each have their own production-oriented Dockerfile.
- The root Compose configuration runs frontend, backend, and Redis together and
  defines health checks and explicit service dependencies.
- Runtime configuration comes from environment variables. Images must not bake
  secrets into layers and should use non-root users where practical.
- Redis uses a named volume. Backend logs go to stdout and the container runtime
  controls collection and retention.

## Testing expectations

Every service and pure scoring unit requires focused tests for its normal path
and meaningful edge cases. At minimum these cover invalid symbols/windows,
missing or nullable provider fields, empty histories, zero denominators,
insufficient observations, malformed upstream payloads, timeout/rate-limit
mapping, cache hit/miss/corruption behavior, and partial upstream availability.

## Nice-to-have AI layer

AI/news research is added after the deterministic workflow is stable:

```text
Sectors evidence + cited web sources -> AI research service -> sourced brief
```

The AI layer may explain or summarize scores but may not modify them. Its routes,
prompts, retrieval logic, and citations should remain separate from deterministic
scoring code.

## Suggested implementation order

1. **Backend foundation:** finish minimal provider schemas, cache abstraction,
   Redis integration, canonical keys, TTL policy, structured console logs,
   the exception registry, and their tests.
2. **Backend IntelScore:** map the required provider data into domain models,
   finalize and test deterministic scoring, define the reviewed HTTP contract,
   and implement the IntelScore application service and route.
3. **Backend packaging:** add the backend Dockerfile, health checks, environment
   configuration, and Compose integration with Redis.
4. **Frontend boilerplate:** build the shared layout, sidebar, Home, symbol
   routing, IntelScore page structure, API client boundary, states, and mocked
   data before wiring the stable contract.
5. **Frontend integration:** connect IntelScore to the backend, implement charts
   and key points, and verify responsive, loading, stale, partial, and error
   states.
6. **Refinement:** Shareholder Composition and BrokerFlow are implemented as
   separate pages; future work can consider AI/news research and other enhancements.
