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
- `exceptions.py` defines failures that callers can handle without depending on
  `requests` exceptions.
- `schemas/` will describe Sectors response payloads after representative
  samples have been reviewed. These provider schemas contain only fields used
  by IntelFlow and must not become the application's shared domain models.
- Representative outputs for all eight selected endpoints are stored in
  `output-schema/`; the modeling policy is defined in `docs/SCHEMA.md`.

The Sectors layer returns raw decoded JSON for now. It must not contain scoring
or other product-level business logic.

```text
Application service -> SectorsGateway -> CachedSectorsGateway
                                      -> cache hit
                                      -> SectorsClient -> Sectors API
```

`SectorsClient` remains responsible only for HTTP communication. Cache behavior
is added by a gateway wrapper so the client is still usable and testable without
a cache.

## API application

- `src/backend/main.py` creates the FastAPI application, exposes `/health`,
  adds request logging, and converts Sectors exceptions into safe HTTP errors.
- `src/backend/logger.py` owns the shared console logging format, log level,
  and per-request correlation ID.
- Future feature routes should be added as separate routers and registered by
  the app factory rather than implemented directly in `main.py`.

Run locally with:

```powershell
uv run uvicorn src.backend.main:app --reload
```

## Backend responsibilities

The backend should be split by responsibility rather than placing all behavior
inside route handlers.

```text
src/backend/
├── main.py                 # FastAPI app construction and global handlers
├── logger.py               # Shared structured logging
├── api/
│   ├── routes/             # HTTP endpoints grouped by feature
│   │   ├── stocks.py
│   │   ├── broker_flow.py
│   │   ├── shareholders.py
│   │   └── fundamentals.py
│   └── schemas/            # Public request/response models
├── domain/
│   └── models/             # Stable internal records shared by services/cache/scoring
├── services/
│   └── stock_analysis.py   # Coordinates data needed for a stock analysis
├── sectors/
│   ├── client.py           # Raw Sectors HTTP implementation
│   ├── gateway.py          # Contract used by services
│   ├── exceptions.py       # Sectors-specific failures
│   ├── schemas/            # Sectors-specific response payload models
│   └── mapper.py            # Converts provider payloads into domain models
├── scoring/
│   ├── broker_flow.py
│   ├── fundamental.py
│   └── combined.py
├── cache/                  # Cache interface, Redis implementation, key/TTL policy
└── tests/
```

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
| Sectors provider payload | `sectors/schemas/` | Sectors client and mapper |
| Internal domain model | `domain/models/` | Services, scoring, and domain-result cache |
| Public HTTP request/response | `api/schemas/` | FastAPI routes and frontend contract |

This prevents a field change from Sectors from automatically changing the
public API. Cache implementations are generic and do not own financial schemas;
they serialize either a provider payload or a domain result as selected by the
caller. The frontend keeps generated or handwritten TypeScript types matching
only the public HTTP schemas.

### Initial backend workflow

For a request such as `GET /api/v1/stocks/BBCA/broker-flow?window=5d`:

1. Route validates the symbol and window.
2. Service converts `5d` into effective trading/date parameters.
3. Service requests broker, foreign-flow, and liquidity inputs.
4. A cached Sectors gateway checks the cache before delegating a paid request
   to the HTTP client.
5. Raw responses are normalized into internal records.
6. Broker scoring functions calculate components and evidence.
7. Route returns a stable JSON response to the frontend.

## Draft backend HTTP API

These are product-facing IntelFlow endpoints, not direct mirrors of Sectors
paths. Exact schemas will be defined after response samples are reviewed.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Process health |
| `GET /api/v1/stocks/{symbol}/overview` | Identity, three scores, top drivers, and data dates |
| `GET /api/v1/stocks/{symbol}/broker-flow?window=1d` | Broker accumulation/distribution for a selected window |
| `GET /api/v1/stocks/{symbol}/foreign-flow?window=20d` | Foreign flow series and summary |
| `GET /api/v1/stocks/{symbol}/prices?range=3m` | Price and volume series for charting |
| `GET /api/v1/stocks/{symbol}/shareholders?year=2026` | Monthly shareholder composition and changes |
| `GET /api/v1/stocks/{symbol}/fundamentals` | Fundamental score, components, periods, and evidence |

Example chart response shape:

```json
{
  "symbol": "BBCA",
  "range": "3m",
  "as_of": "2026-09-18",
  "series": [
    {
      "date": "2026-09-18",
      "open": 8000,
      "high": 8125,
      "low": 7950,
      "close": 8075,
      "volume": 92000000
    }
  ]
}
```

The frontend receives numeric values and dates. It decides whether to render a
line, candlestick, area, or bar chart without changing the underlying data.

## Frontend responsibilities

```text
src/frontend/
├── app/                    # App bootstrapping, routes, and shared layout
├── pages/
│   ├── SearchPage
│   ├── StockOverviewPage
│   ├── BrokerFlowPage
│   ├── PriceChartPage
│   ├── ShareholdersPage
│   └── FundamentalsPage
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

1. **Search page** accepts one IDX symbol.
2. **Stock overview** shows company identity, Flow Score, Fundamental Score,
   Combined Score, top evidence, and data dates.
3. **Broker flow page** switches between 1D, 5D, and 20D and shows top
   accumulation/distribution.
4. **Price chart page** renders three months of price and volume data.
5. **Shareholders page** renders monthly local/foreign/category composition and
   shareholder-count changes.
6. **Fundamentals page** explains growth, earnings, cash-flow, and valuation
   components when those fields are available.

### Frontend data rules

- The selected symbol should live in the URL so pages can be bookmarked, for
  example `/stocks/BBCA/broker-flow`.
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
| Tooltip and range-tab interaction | No | Yes |
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
| Current price, broker flow, foreign flow window | 1 hour |
| Historical date-bounded market/flow window | 30 days |
| Shareholder composition | 3 days |
| Free-float list | 7 days |
| Company Report: overview or valuation | 12 hours |
| Company Report: financials, ownership, management, peers | 7 days |
| Revenue segments | 7 days |

These TTLs are product defaults, not claims about Sectors update frequency, and
should be adjusted after observing the actual endpoint refresh behavior. Do not
give the complete Company Report one long TTL: `overview` and `valuation`
contain price-sensitive fields, while statement and ownership sections change
far less frequently. Do not cache authentication, validation, rate-limit, or
unexpected upstream errors.
Historical score snapshots and a permanent database are deferred until the
basic analysis flow works.

## Nice-to-have AI layer

AI/news research is added after the deterministic workflow is stable:

```text
Sectors evidence + cited web sources -> AI research service -> sourced brief
```

The AI layer may explain or summarize scores but may not modify them. Its routes,
prompts, retrieval logic, and citations should remain separate from deterministic
scoring code.

## Suggested implementation order

1. Define the minimal Sectors response models in `docs/SCHEMA.md` from the
   reviewed samples in `output-schema/`.
2. Implement `CacheStore`, its Redis implementation, canonical keys, and the
   cached Sectors gateway with tests.
3. Implement Sectors mappers from provider schemas into domain models.
4. Implement price, broker-flow, foreign-flow, and shareholder backend routes.
5. Build the frontend shell, symbol routing, and detail pages using stable or
   mocked backend JSON.
6. Finalize and test scoring formulas.
7. Add the overview endpoint that combines scores and evidence.
8. Add AI/news research only after the MVP workflow is reliable.
