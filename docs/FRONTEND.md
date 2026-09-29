# IntelFlow frontend MVP

Home, IntelScore and Shareholders use Vite, React, TypeScript, React Router, TanStack Query,
Apache ECharts and Tailwind CSS v4 (official Vite plugin). The browser consumes only the IntelFlow backend
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
  reasons, periods and explicit display interpretations. Overall Score is the UI name for Combined
  Score; internal calculation identifiers remain in the API. The frontend does
  no score arithmetic.
- The initial aggregate request supplies scores, fundamentals and 20D flow
  evidence. The 1D/5D controls request only flow evidence; returning to 20D
  reuses the aggregate response. A separate price-history query loads 1M closes;
  the trend control can request 3M closes through the existing endpoint.
- Flow and annual fundamental charts use normalized backend arrays. Missing
  values stay null. Quarterly snapshots without a confirmed period are not
  given an invented history.
- A compact SectorsAPI footer shows observation dates, financial years and
  stale flags. Partial and stale notices can coexist. Retrieval timestamps and
  raw source identifiers are not shown in the UI.
- Requests are cancellable. There is no automatic retry, polling, or focus and
  reconnect refetch, limiting surprise paid calls. Errors use plain-English recovery messages; internal request IDs remain in the API.
- Navigation always shows Home, IntelScore and Shareholders. IntelScore and
  Shareholders have separate symbol-search entries and routes; switching
  sections does not carry the previous section's ticker or fetch its data.
- The Shareholders page loads monthly backend snapshots for a chosen year. Its
  stacked bar can switch between share counts and category composition percent,
  with independent All/Local/Foreign investor controls. The right panel retains
  selected-month category details; shareholder count uses a single full-width
  chart with an inline count and change. Missing months remain gaps, and
  category totals that differ from reported investor totals are disclosed.
- Changing the shareholder year fetches that year from the backend. Historical
  null counts remain gaps while category holdings continue to render. A missing
  symbol/year dataset has a neutral empty state, separate from a real service
  failure. Partial Flow and Overall Scores retain their numeric values when
  at least 16 of 20 foreign and volume observations are present; the coverage
  warning and Low confidence remain visible.

## Appearance and evidence presentation

Light, Dark, and System are available from the persistent Appearance control.
System is the default; the explicit choice is stored in `intelflow-theme` and
applied by the head script before rendering. `app/theme.ts` synchronizes system
and storage changes without changing research query state. All CSS and ECharts
colors use the semantic tokens in `app/theme.css`; charts update their existing
instances. The interface uses Helvetica Neue with Arial fallback.

Home has an editorial overview; `/intel-score` is a concise ticker entry screen.
Company research begins with identity, backend-supplied dated close/change,
latest volume, prior average volume and their ratio.
Key points format up to five facts from typed response values into Flow,
Fundamental, Risk and Data Quality bullets. Broker bars pair buyers and
sellers by provider rank above/below zero; paired tables and full trading values
are directly visible. Overall Score sits left of the stacked Flow and Fundamental
Scores. Component values, status meters, weights and definitions are always visible.
Display bands, drivers, risks and coverage confidence are defined in SCORING.md.
No historical scores or 1Y histories are fabricated; unsupported views explain
what is missing. Ticker search remains in the top navigation. Fundamental history
uses year-column tables. Disclosures, internal labels and source links are removed.
Partial states describe affected sections; full-page errors retain global ticker entry.
All product copy and implementation documentation are English.

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
Home, so they exercise navigation, score display, flow tabs, invalid-symbol
handling, error recovery, theme persistence, system changes, paired broker-bar
positions, chart recoloring, and responsive layout without contacting the
backend or Sectors. They also verify the new score hierarchy, header values, absence of internal
labels/disclosures, direct evidence tables, and theme switches preserving
the evidence URL, scores, and request count. Screenshots for both themes and
partial/stale states are written to the ignored test-results directory.
Tests do not claim that
the test response is current BBCA market data. Backend unit tests likewise use
test doubles and reviewed local provider samples.

The lazy-loaded research/chart bundle currently exceeds Vite's 500 kB advisory
(about 592 kB minified / 199 kB gzip). Home loads separately. Live provider
coverage and score calibration remain to be verified with authorized API calls.


## Tailwind maintenance

Use semantic utilities (`bg-surface`, `text-muted`, `border-line`) backed by
`app/theme.css`. Shared control and panel recipes are in `components/ui.ts`;
layout utilities live with their components. Keep CSS custom properties for
ECharts interoperability. Do not reintroduce per-component CSS Modules or render
backend calculation identifiers and missing-input paths as product copy.

The local Docker frontend serves a built image, not live source. After a UI
change, refresh only that service with `docker compose up -d --build --no-deps frontend`, or use the Vite development server when port 5173 is free.

Use `PLAYWRIGHT_BASE_URL` to target a separate local preview during browser tests.

If another local service owns host port 6379, set `$env:REDIS_PORT='6380'` before
Compose commands. The revision v2 verification session uses host port 6380;
Docker-internal Redis remains `redis:6379` and the existing data volume is retained.


## Revision v2 verification (2026-09-27)

- TypeScript and production build: passed.
- ESLint: passed.
- Component tests: 16 passed.
- Playwright against the rebuilt Docker frontend: 6 passed.
- Responsive checks: 320, 390, 768, 1024 and 1440px, light and dark themes.
- Screenshots reviewed for Home, market header, scores, broker charts, annual
  tables and attribution. Theme changes do not fetch research again.
- Browser research responses were intercepted; no paid provider calls were used.
- Existing chart-bundle size advisory remains; scoring and API contracts are unchanged.

## Decision dashboard verification (2026-09-27)

- TypeScript, production build and ESLint: passed.
- Unit/component tests: 30 passed. Browser tests against the rebuilt Docker
  frontend: 10 passed.
- Responsive checks cover 320, 390, 768, 1024 and 1440px in both themes.
- Score text meets a 4.5:1 contrast ratio in both themes; score labels are at
  least 14px. Status labels accompany color and component meters.
- Keyboard period selection, query caching, missing/error price history,
  unavailable score history and unsupported 1Y ranges are verified. Selected
  period labels maintain at least 4.5:1 contrast in both themes before and
  after switching periods.
- Desktop/mobile screenshots were reviewed. All provider-facing browser
  requests were intercepted; no paid provider calls were made.
- Numerical scoring and backend contracts remain unchanged. Historical score
  comparisons require data that the current API does not provide.
