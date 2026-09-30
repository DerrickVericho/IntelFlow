# IntelFlow UI specification

Status: decision dashboard implemented, 2026-09-27. This specification supersedes the
previous disclosure-based layout and earlier single-theme wireframes.

## Design and implementation

The interface uses Tailwind CSS v4 through the official Vite plugin. Semantic
colors are mapped with `@theme inline` in `app/theme.css`; reusable control
recipes live in `components/ui.ts`. Page and component layouts use utility
classes. The retired CSS Modules are removed.

The visual direction is modern Swiss: pale-blue surfaces in Light, layered navy
surfaces in Dark, one blue brand accent,
Helvetica Neue / Arial, tabular financial values, clear hierarchy and 1px
section rules. Panels use 16px corners; controls use 12px corners. Body text is
16px, secondary text and dates are at least 14px in research content. Meaning never depends
on color alone. Product copy, code, tests and documentation are English.

The frontend-design skill informs the shared visual system. The taste skill
informs Home and the redesign audit; its marketing patterns are not applied to
data-heavy research. Home, IntelScore, and Shareholders have usable navigation.

## Appearance

- Light, Dark and System are available through the persistent Appearance control.
- First visit follows the OS. Preference persists under `intelflow-theme`.
- A head script applies the theme before rendering. Storage failures fall back
  to the system preference.
- Explicit Light appearance uses `color-scheme: only light` so browser automatic
  darkening cannot turn surfaces dark while chart labels retain light colors.
- Period controls use dedicated high-contrast foreground/background tokens in
  both appearances. SVG chart labels use an explicit appearance token and a
  rendered fill rule so broker codes, axes and legends stay readable.
- ECharts reads the same semantic variables and updates existing instances.
- Switching appearance preserves ticker, query cache and evidence period. It
  does not perform a data request. OS and cross-tab changes are synchronized.
- Desktop has a 224px sidebar; below 768px navigation moves above the content.
  Research stays inside the viewport; wide tables and charts scroll locally.

## Routes

- `/`: concise product overview, prominent ticker search and a real BBCA example.
- `/intel-score`: focused company search entry.
- `/stocks/:symbol/intel-score`: company research.
- Input accepts four letters and an optional `.JK` suffix, normalized to uppercase.
  Syntax validation does not prove the company exists.
- `/shareholders`: independent shareholder symbol search entry.
- `/shareholders/:symbol`: monthly shareholder composition and count. The old
  `/stocks/:symbol/shareholders` URL redirects here.
- `?window=1d` and `?window=5d` select flow evidence. Omission means 20D.
  Back/forward restores the period; unsupported values explicitly fall back.
- Home performs no market request before ticker submission or opening the example.

## Shareholder composition

- Shareholders has its own always-visible navigation item and symbol search.
  Opening it from IntelScore does not carry the IntelScore ticker; searching in
  Shareholders never opens IntelScore or requests its aggregate. The page
  requests the existing IntelFlow `/shareholders?year=` endpoint for the chosen
  year; it never contacts Sectors directly from the browser. Changing year
  requests that historical year. Supported years come from the response and do
  not imply observations for every month.
- One bar represents each available monthly snapshot. Bars stack the reported
  shareholder categories, combining matching `_l` and `_f` fields in All,
  using `_l` in Local and `_f` in Foreign. Investor origin and bar display
  mode are independent controls. Shares shows actual category holdings;
  Composition % divides each category by the sum of available category
  holdings for that month and investor origin. Empty months remain empty.
- The category panel stays alongside the chart on wide screens and below it
  on narrow screens. It shows the selected available month, issued shares,
  local and foreign totals, and each category's exact holdings and share of
  reported category holdings. Selecting a bar or the labeled month control
  updates the panel. Missing category values are not treated as zero. If
  category holdings do not match the reported investor total, the page explains
  the gap and never presents the categories as a complete share of issued stock.
- Shareholder count is one full-width chart without a second selected-month
  panel. Its heading includes the count and reported change for the selected
  month. Null historical counts and absent months remain gaps. If counts are
  missing for an entire year, the composition chart remains visible while the
  count section explains the missing data. A provider 404 for a symbol/year
  dataset appears as an empty state; true upstream failures have a separate
  shareholder-data error. Both charts and controls use theme-aware,
  high-contrast labels. Internal field names, request identifiers, retrieval
  diagnostics, provider errors and credentials never appear in the UI.

## Company market header

Ticker search lives in the global top navigation, including loading and error
states. The compact market header shows company name, ticker, sector/subsector,
last close in full IDR, signed nominal/percentage change and comparison dates.
The numeric direction is also written as Up, Down or Unchanged.

A statistics row shows latest volume in shares, the preceding 20-observation
average volume, volume/average, and previous close. These fields come directly
from the aggregate backend response; no new provider request or score calculation
is introduced. The average excludes the latest observation. Missing values
remain Unavailable, missing change says Change unavailable, and zero stays zero.

### PDF export

A labeled `Save as PDF` action sits immediately above the company market
summary, aligned right on wide screens and full width on narrow screens. It
appears after the research response is available. While the file is prepared,
the button shows progress and prevents duplicate clicks; a failure shows an
inline retryable error. The downloaded A4 PDF reproduces the dedicated
IntelScore content region visually, including its theme, charts, tables,
selected evidence window, source attribution, and coverage states. The app
shell and export action are excluded. Wide desktop captures use A4 landscape to
preserve the dashboard proportions; narrow captures use A4 portrait.
Text is rasterized rather than selectable. Export uses the rendered page and
does not start a paid provider request. Scrollable tables are captured at their
current visible scroll positions; export does not silently expand hidden rows.

## Score hierarchy

- Overall Score is the user-facing name for the backend Combined Score. Its
  card is prominent on the left, spanning both right-hand rows at 1280px and wider.
- Flow Score is top-right; Fundamental Score is bottom-right. All three align
  to the same outer grid and stack in this order on narrow screens.
- Components use aligned labels and values, labeled horizontal meters, secondary
  weights, and short visible definitions. Weak/Neutral/Positive/Strong/Unavailable
  appear in text; the palette uses amber and blue as well as financial red/green.
- Every numeric component meter uses the same blue fill within an appearance,
  independent of its Weak/Neutral/Positive/Strong label. The track and fill have
  explicit colors in Light and Dark. A valid zero keeps a small blue start
  marker; an unavailable component has no fill.
- Missing scores display N/A and Not calculated, with the backend reason visible.
  Available components can coexist with an unavailable aggregate.
- Flow scores always use 20 observations; evidence-period controls affect charts
  only. The score date range stays visible.
- Component definitions describe IDR liquidity against the Rp5 billion daily
  benchmark, foreign-ranked broker net balance weighted by foreign investor
  participation, and independently ranked 5-day/20-day all-investor broker
  balance, daily consistency, and concentration. Broker windows are weighted
  65% recent and 35% longer-term.
- With 20 trading observations and all three components, Flow and Overall
  Scores remain numeric when foreign, liquidity-value, or daily-broker coverage
  is 16–19 of the 20 dates. Their cards explain partial coverage; data confidence is Low.
  Fewer than 16 dated observations or an unavailable component keeps N/A.
- Calculation versions and retrieval diagnostics remain in the API and working
  documentation, not in the product UI. Current formulas are in SCORING.md.

## Decision summary and trends

Overall Score carries a large value, an explicit status and meaning, a Flow and
Fundamental summary, key driver, main risk and categorical data confidence.
Confidence rules and score bands are documented in SCORING.md. Score direction
is explicitly unavailable when historical snapshots are absent. The Overall
Score card does not show empty prior-week or prior-month comparison rows, and
historical scores must not be inferred from price changes.

A separate Change over time section fetches a fixed 3M dated OHLC series from
`price-history`. One full-width candlestick chart uses an IDR price axis and
shows its actual coverage dates. There are no range controls, broker overlays,
foreign-flow chart, or empty Overall Score history panel in this section.
Fewer than two price observations, unavailable history, or unavailable OHLC
yield explicit empty states without removing aggregate scores. Missing OHLC
observations remain gaps. Historical scores are not inferred from price history.

Broker overlays and longer foreign-flow timelines are deferred until historical
storage or a similarly reliable range-aligned retrieval strategy exists. The
current provider broker activity window is limited to 14 calendar days per
request, and foreign observations do not yet share the standalone price-history
range contract. Foreign evidence remains available in Flow Activity.

## Key points and flow

- Key points contains at most five concise facts grouped as Flow, Fundamental,
  Risk and Data Quality. They format typed response values, not parsed narrative.
  Currency uses compact Rp units (for example Rp244.1B net sell); ranked broker
  imbalance is not described as whole-market net flow. Annual earnings and OCF
  retain their years. Driver/risk and data confidence explain the main limitations.
- All-investor broker columns use provider ranks. The Foreign/Local control
  changes the broker chart and net-activity table together. Foreign net uses
  `foreign_net_idr`; local net is `net_idr - foreign_net_idr` when both values
  exist. Zero net and rows without a foreign breakdown are omitted in those
  views. Buyers and sellers are re-ranked separately, up to 10 per side, only
  among the brokers in the provider's all-investor top buyer/seller response.
  These views must not be called market-wide top foreign or local rankings.
  The filter makes no request and does not change scores.
- Each chart column pairs buyer and seller at the displayed rank. Buyers extend
  above zero; sellers below. Codes sit at bar ends; missing sides remain missing.
  A rank pair does not imply a transaction between brokers.
- Broker net activity, daily foreign flow and daily volume remain directly
  visible in labeled, keyboard-scrollable tables with sticky headings. The
  broker trading-values table is removed. Daily volume shows date, volume and
  volume/preceding-average ratio; the prior-average and baseline-count columns
  are removed.
- Top 3/5/10 balances remain labeled all-investor evidence, independent of the
  broker display filter. They describe ranked participants, not whole-exchange
  net flow. Broker origin remains distinct from investor origin.
- Foreign and volume charts retain gaps for missing data. Liquidity uses shares
  and the preceding-observation average, excluding the current observation.

## Fundamentals and attribution

- Growth, Earnings, Cash Flow and Valuation each show their component score,
  an available annual chart, and a table of latest and historical values.
- Annual years are columns. Quarterly snapshots remain explicitly undated, with
  no invented quarter/history, and are excluded from scoring.
- Missing metric reasons remain visible. Negative ratios are not called cheap.
- There are no disclosure toggles or source-anchor links in the research UI.
- A compact footer says Powered by SectorsAPI and
  For research purposes only — not investment advice. It lists
  the financial-history year span, latest report, observation dates/reporting
  periods, and stale flags. It replaces detailed source cards.
- Source keys, retrieval timestamps and calculation identifiers remain in API
  responses for traceability, but are not displayed as internal product labels.

## Availability, errors and accessibility

- Partial-data warnings appear once in plain-English groups. Raw field paths
  and duplicate availability disclosures are not rendered.
- Partial and stale states can coexist. Stale sources are named, with dates
  retained in the attribution footer; an absent stale flag is not a live-data claim.
- Loading replaces previous ticker/period evidence. The global ticker input remains available on full-page errors. A 404 means No data found, not a confirmed invalid ticker.
- Network/server errors offer manual retry. 404/422/429 are not retried unchanged.
  Internal error messages and request IDs stay out of the visible UI.
- A flow-only error stays within its section. Failed refreshes label retained data.
- No polling, automatic retries, focus refetch or reconnect refetch.
- Labeled inputs, skip navigation, visible focus, chart text alternatives,
  table captions/headers, keyboard scrolling and reduced motion are supported.

Run and verification instructions: [FRONTEND.md](./FRONTEND.md).
