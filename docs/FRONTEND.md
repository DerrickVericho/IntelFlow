# IntelFlow frontend MVP

Home and IntelScore use Vite, React, TypeScript, React Router, TanStack Query,
Apache ECharts and CSS Modules. The browser consumes only the IntelFlow backend
contract. It does not contact Sectors or calculate scores.

## Run with real IDX data

Set `SECTORS_API_KEY` in a local, uncommitted `.env`. Start the backend and
Redis, then start the frontend:

```powershell
docker compose up -d redis
uv run uvicorn src.backend.main:app --reload
```

In another terminal:

```powershell
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api/v1` to the backend on port
8000. Home has an example link for the real IDX ticker `BBCA`; the link issues a
research request only when opened. A valid ticker and a cache miss can trigger
paid Sectors API calls. The UI reports missing, partial, stale and upstream
error states from the backend instead of substituting generated market data.

For the production-style local stack, use `docker compose up -d --build` and
open the same frontend port. This stack has frontend, backend and Redis; there
is no separate synthetic backend or fallback data source.

Ticker search accepts exactly four letters, case-insensitively, with an
optional `.JK` suffix. It checks syntax, not whether the ticker exists. The
backend repeats validation before provider work.

## Interface and data decisions

- Home performs no research request until a ticker is submitted or the BBCA
  example is opened. Deep links use `/stocks/:symbol/intel-score`.
- Three independent score cards display backend values, component weights,
  reasons, calculation version, periods and research state. The frontend does
  no score arithmetic.
- The initial aggregate request supplies scores, fundamentals and 20D flow
  evidence. The 1D/5D controls request only flow evidence; returning to 20D
  reuses the aggregate response.
- Flow and annual fundamental charts use normalized backend arrays. Missing
  values stay null. Quarterly snapshots without a confirmed period are not
  given an invented history.
- Source references show observation dates, periods and retrieval time in WIB.
  Partial and stale notices can coexist. A source without a stale flag is
  described as `Not flagged stale`, not guaranteed current.
- Requests are cancellable. There is no automatic retry, polling, or focus and
  reconnect refetch, limiting surprise paid calls. Errors and request IDs are
  visible when provided.
- Shareholder Composition and Stockchart remain labelled `Coming later`.

## Verification without provider calls

```powershell
npm run build
npm run lint
npm test
```

For the browser suite, keep `npm run dev` running in one terminal and run
`npm run test:e2e` in another. The browser suite intercepts all research API
requests, so the backend does not need to run for this check.

Component tests use an isolated contract response stored under
`src/frontend/tests/data/`. Browser tests intercept `/api/v1` before loading
Home, so they exercise navigation, score display, flow tabs and invalid-symbol
handling without contacting the backend or Sectors. Tests do not claim that
the test response is current BBCA market data. Backend unit tests likewise use
test doubles and reviewed local provider samples.

The lazy-loaded research/chart bundle currently exceeds Vite's 500 kB advisory
(about 575 kB minified / 195 kB gzip). Home loads separately. Live provider
coverage and score calibration remain to be verified with authorized API calls.
