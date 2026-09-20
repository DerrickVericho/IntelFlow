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

1. User searches an IDX ticker.
2. Product retrieves Sectors data for that symbol across multiple time windows.
3. User sees Flow Score, Fundamental Score, Combined Score, and the main
   evidence behind each result.
4. User explores broker accumulation/distribution, foreign flow, and
   shareholder-composition changes for 1-day, 5-day, 20-day, and other
   supported ranges.
5. User navigates from the stock overview to dedicated chart, shareholder, and
   broker-analysis pages.

## Must have

- Ticker search and validation.
- Broker Flow Score: 0–100.
- Fundamental Support Score: 0–100.
- Combined Conviction Score: 0–100.
- Independent score breakdowns and evidence.
- Data freshness indicators.
- Broker accumulation/distribution views for 1-day, 5-day, and 20-day ranges.
- Foreign-flow view for the selected symbol.
- Historical shareholder-composition view and shareholder-count change.
- Dedicated chart page with a three-month price/volume chart.
- Dedicated shareholder page with a monthly shareholder-composition bar chart.
- Dedicated broker-flow page.
- Non-advisory disclaimer.
- Cache/API-credit controls.

## Nice to have

- Broker and foreign-flow timeline overlays.
- Advanced shareholder-composition analysis.
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

## Data sources

Primary endpoint contracts and credit costs are maintained in
[API.md](./API.md). Initial product inputs are:

- broker activity and top buyers/sellers;
- foreign flow;
- company report sections for fundamentals, ownership, and peers;
- company revenue/cost segments;
- shareholder composition; and
- daily price, volume, and market-cap data.

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
- An IDX ticker can be analyzed end to end during the demo.
- A user can inspect accumulation/distribution and shareholder changes across
  the supported time ranges for one symbol.
- Every displayed score is traceable to dated evidence.
- Sectors is clearly essential to the product.
- If AI/news research is demoed, it returns working citations and no fabricated
  claims.

## Open questions

- Which initial observation windows and score thresholds are most useful?
- Which fundamental metrics are consistently available for demo tickers?
- How should the product handle bank versus non-bank metrics?
- Which tickers will be used as validation and demo cases?

Detailed formula, normalization, and missing-data behavior live in
[SCORING.md](./SCORING.md).
