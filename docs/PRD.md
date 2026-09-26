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
5. If the nice-to-have modules are available, the same symbol can be explored
   in dedicated Shareholder Composition and Stockchart pages.

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
- Broker accumulation/distribution, foreign-flow, and liquidity evidence within
  IntelScore for the supported analysis windows.
- Fundamental evidence covering the shallow cross-sector metrics defined in
  `SCORING.md`.
- Non-advisory disclaimer.
- Cache/API-credit controls.

## Nice to have

- Shareholder Composition page with a monthly stacked bar chart and
  shareholder-count changes for the selected symbol.
- Stockchart page with 1-week, 1-month, and 3-month ranges, price/volume data,
  default top-three buyer and seller broker overlays, and user-selectable
  brokers.
- Additional broker and foreign-flow timeline overlays.
- Advanced shareholder-composition analysis and filters.
- Revenue-segment visualization.
- User-selected peer comparison.
- User-adjustable Flow/Fundamental combined-score weights.
- Historical score snapshots and exportable research brief.
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
- company report `financials` and `valuation` sections for a shallow,
  cross-sector fundamental check.

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

- Which initial observation windows and score thresholds are most useful?
- Which minimum fundamental metrics are consistently available for demo
  tickers across sectors?
- Which tickers will be used as validation and demo cases?

Detailed formula, normalization, and missing-data behavior live in
[SCORING.md](./SCORING.md).
