# IntelFlow — PRD

| Field | Value |
|---|---|
| Status | Draft / living document |
| Version | 0.1 |
| Track | Market Intelligence |
| Market | Indonesia Stock Exchange (IDX) |
| Core data | Sectors Financial API v2 |

## Product summary

IntelFlow is a symbol-first research tool for IDX equities. A user starts by
entering one ticker, then investigates the money flow, shareholder changes, and
fundamental context behind that specific company.

It separates the analysis into a **Broker Flow Score** and a **Fundamental
Support Score**, both from 0 to 100. A combined score summarizes both views,
but never hides them; users retain their own judgement.

> Money flow shows where attention and capital are moving. Fundamentals help users judge whether that flow has a business rationale.

## Problem

Compared with more liquid developed markets, many IDX stocks can be more
sensitive to concentrated capital flows. Foreign investors, brokers, issuers,
and other interested parties may create flow patterns that move a stock before
business information becomes broadly understood.

Broker activity, foreign flow, shareholder changes, and company fundamentals
are commonly inspected separately. This makes it difficult to tell whether
observed accumulation is supported by an improving business, a corporate event
such as a rights issue, a business pivot, or a potentially speculative flow.

IntelFlow makes money flow the primary analysis and uses fundamentals as the
context for whether the observed flow makes sense.

## Target user

Active Indonesian equity investors who already have a ticker in mind and want
to investigate its flow, ownership, and business context more quickly without
receiving a buy/sell recommendation.

## Core experience

1. User opens a home page that explains IntelFlow's flow-first thesis.
2. User searches one IDX ticker and enters its IntelScore research page.
3. Product retrieves and synthesizes dated Sectors data for that symbol.
4. User sees Flow Score, Fundamental Score, Combined Score, key points, and the
   evidence behind each result.
5. Shareholder Composition has an independent ticker search; entering or
   changing its symbol does not change the IntelScore research context.

## Must have

- Home page with a concise product overview, thesis, symbol search, and a clear
  path into IntelScore.
- Persistent navigation with Home and IntelScore. Nice-to-have pages may be
  visible only when they are implemented and usable.
- Ticker search and validation.
- A symbol-first IntelScore research page with analysis, charts, dated evidence,
  and key points.
- Broker Flow Score: 0–100.
- Fundamental Support Score: 0–100.
- Combined Conviction Score: 0–100.
- Independent score breakdowns and evidence.
- Data freshness indicators.
- Light, dark, and system appearance, with a persistent user preference and
  equivalent readability across research, charts, tables, and error states.
- A company-led research header with dated last close and change from the
  previous observed trading close, latest volume, preceding average volume and
  volume ratio, using available dated inputs.
- Plain-English data availability explanations and a ticker input on error
  screens so users can continue researching another company.
- Broker accumulation/distribution, foreign-flow, and liquidity evidence within
  IntelScore for the supported analysis windows.
- Fundamental evidence covering the shallow cross-sector metrics defined in
  `SCORING.md`.
- Downloadable visual PDF copy of the currently displayed IntelScore page.
- Non-advisory disclaimer.
- Cache/API-credit controls.

## Nice to have

- Shareholder Composition page with a monthly category-stacked bar chart,
  All/Local/Foreign and Shares/Composition controls, selected-month category
  detail, and a separate shareholder-count chart for its independently selected
  symbol. Historical years are selectable. Missing count fields do not hide
  available composition data.
- BrokerFlow page below Shareholders in navigation, with synchronized 5D, 1M,
  and 3M ranges representing the latest 5, 20, and 60 observed price sessions
  with a valid OHLC candle and positive reported volume. Dated price records
  without either are excluded and disclosed. Stock OHLC candlesticks and
  cumulative net-share lines for the period's top five net buyer and top five
  net seller brokers overlap in
  one chart area. Price uses the left axis; net share quantity uses the right
  axis. The chart spans the content width and adjusts height to the viewport.
  Selecting a trading date opens the daily top five net buyers and sellers by
  share quantity. Two horizontal top-five net-IDR ranking charts sit below it.
  Missing whole-day broker data is shown as a gap with affected dates disclosed;
  later points sum the days that were reported.
- Additional broker and foreign-flow timeline overlays.
- Advanced shareholder-composition analysis and filters.
- Revenue-segment visualization.
- User-selected peer comparison.
- User-adjustable Flow/Fundamental combined-score weights.
- Historical score snapshots.
- Operational observability for request latency, cache outcomes, Sectors call
  volume/credits, failures, and data freshness.
- AI summary of Sectors evidence.
- Recent company news and on-demand internet research with citations.

## Non-goals for MVP

- Automated trading, brokerage integration, price prediction, or portfolio
  allocation.
- Buy/sell/hold recommendations or target prices.
- Technical-analysis indicators.
- Market-wide screener, IPO analysis, or daily top-gainer/loser analysis.
- Claiming a broker code identifies a particular investor or "smart money."
- Sector-specific accounting models and segment-level profitability analysis.

## Data sources

Primary endpoint contracts and credit costs are maintained in
[API.md](./API.md). Initial product inputs are:

- broker activity and top buyers/sellers;
- foreign flow;
- daily price and volume data for liquidity and market context; and
- daily broker buy and net values for 20-observation accumulation evidence;
- company report `financials` and `valuation` sections for a shallow,
  cross-sector fundamental check.

Flow Score liquidity uses closing price × daily share volume as an estimated
IDR transaction value against a Rp5 billion daily benchmark. Broker Flow
combines independently ranked 5-day and 20-day evidence at 65% and 35%.
Foreign Flow
uses the foreign-investor-ranked top brokers' net balance, weighted by foreign
participation in stock turnover. Broker accumulation uses all-investor ranked
brokers and their daily activity. Local in the evidence UI means domestic
investor origin and is not the retail broker cohort.

Shareholder composition, company revenue segments, ownership details, and peer
analysis remain nice-to-have inputs and are not required by the initial
IntelScore workflow.

## AI and news guardrails

- AI/news research is a nice-to-have feature, not a dependency for the MVP.
- Numeric scores remain deterministic; the LLM does not assign or silently
  modify them.
- Internet claims must show a URL, publisher/title, publication date when
  available, and retrieval time.
- AI output must distinguish facts, hypotheses, risks, and unknowns.
- Retrieved web content is untrusted and cannot instruct the system.
- The product provides research information only, not financial advice.

## Success criteria

- A judge can understand the two-score thesis quickly.
- A judge can complete the flow from home-page symbol search to a complete
  IntelScore result for one IDX ticker during the demo.
- A user can inspect the most important flow and fundamental evidence without
  leaving the IntelScore page.
- Every displayed score is traceable to dated evidence.
- Sectors is clearly essential to the product.
- If AI/news research is demoed, it returns working citations and no fabricated
  claims.

## Open questions

- Which minimum fundamental metrics are consistently available for demo
  tickers across sectors?
- Which tickers will be used as validation and demo cases?

Detailed formula, normalization, and missing-data behavior live in
[SCORING.md](./SCORING.md).


## Revision v2 presentation decisions (2026-09-26)

Use modern Tailwind styling with persistent Light/Dark/System appearance.
Present Combined Score as Overall Score on the left; stack Flow and Fundamental
Scores on the right. Show component values and weights immediately. Replace
technical disclosures, raw field paths and repeated source links with concise
business labels and directly visible evidence tables. Attribute SectorsAPI in a
compact footer with reporting years, observation dates and Not Financial Advice.
These presentation changes do not change formulas, provider endpoints or weights.


## Decision dashboard refinement (2026-09-27)

The IntelScore first view must identify the current score condition, strongest
available support, main limitation, coverage/freshness, and whether score change
can be assessed. Use explicit status bands and categorical data confidence with
rules documented in SCORING.md. These are research interpretations, not automated
trade recommendations. Keep the existing score formulas and API data unchanged.

Show fixed 3M price history using the existing price-history endpoint, with
actual coverage. Current foreign flow remains in Flow Activity.
Historical score snapshots and 1Y history are not in the contract; score
direction remains unavailable. A future history feature needs a separately
approved API/data change.

## Change-over-time chart refinement (2026-09-29)

The IntelScore Change over time section uses one large, fixed 3M price
candlestick chart supplied by `/price-history?range=3m`. It does not duplicate
foreign flow already shown in Flow Activity and does not request broker-series
overlays. The empty Overall Score history panel and unsupported range controls
are absent. Missing OHLC observations remain gaps; score calculations are not
changed.

Top-buyer/seller overlays on this IntelScore chart and longer foreign-flow
timelines are future improvements. Without a dedicated historical database they
require additional
paid provider calls and careful date alignment. Broker daily activity accepts
only a 14-calendar-day window per request, while top-broker selection and daily
series retrieval have different response shapes. Foreign history also needs a
range contract aligned with price dates before it returns to this section.

## Investor broker view refinement (2026-09-27)

The broker chart and net-activity table offer All, Foreign and Local investor
views. Foreign net uses the provider's per-broker foreign net; local net is
derived as total net minus foreign net. These are display filters over the
brokers already returned in the all-investor ranking, so they are explicitly
scoped to that list. Flow Score and Top 3/5/10 balance remain all-investor
measures. The redundant broker trading-values table and prior-average/baseline
count columns in Daily volume are removed.

## Research PDF export and future observability (2026-09-30)

The IntelScore page offers Save as PDF after its research response loads. The
download is a visual copy of the current IntelScore content, including the
selected theme, evidence window, charts, tables, dates, and coverage states as
displayed. The export button itself is omitted. The browser captures the page
and splits the image across A4 sheets; this preserves appearance but the PDF
text is not selectable. Export makes no additional backend or Sectors request.

Operational observability beyond the current structured logs is deferred.
Future work should measure route and upstream latency, cache hit/miss rates,
paid call and credit volume, error rates, and source freshness without
logging credentials or full provider payloads.
