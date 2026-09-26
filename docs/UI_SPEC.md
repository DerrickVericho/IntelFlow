# IntelFlow UI Specification

| Field | Value |
|---|---|
| Status | Draft / living document |
| Priority | IntelScore MVP first |
| Target | Desktop-first web application |
| Wireframe | [IntelFlow — Draft 1 Wireframe](https://www.figma.com/design/W6bVLXxogPXpcd43p6NkmE) |

The current Figma draft contains the four screen shells and shared
sidebar/content layout. Detailed content remains to be completed after the
Figma tool limit resets and this information architecture is reviewed. The
frontend MVP can proceed without that reset using the documented wireframe and
the implemented backend contract as its design/data references.

The generated IntelScore visual reference is stored at
[`docs/assets/intelflow-intelscore-wireframe-v1.png`](./assets/intelflow-intelscore-wireframe-v1.png).
It uses sample evidence for layout illustration only. The backend now provides
`draft-v0.2` numeric scores when adequate inputs exist; unavailable scores are
null. The implemented contract takes precedence over sample values or labels
in the image: liquidity is share volume, financial histories are annual, and
quarterly YoY snapshots have no fabricated quarter label or sparkline.

![IntelFlow IntelScore wireframe](./assets/intelflow-intelscore-wireframe-v1.png)

## Information architecture

The persistent left sidebar contains:

1. **Home** — product overview and entry point.
2. **IntelScore** — the hackathon MVP and primary symbol research experience.
3. **Shareholder Composition** — nice-to-have monthly ownership analysis.
4. **Stockchart** — nice-to-have price, volume, and broker-flow exploration.

The current desktop wireframe uses a 1440 × 1024 frame, a 240 px sidebar, and a
1200 px main-content region. The first visual pass uses Inter typography, a
small CSS-variable token layer, and CSS Modules. The visual direction is a dark,
professional research dashboard: visual emphasis serves the readable analysis,
not a trading signal. Final brand polish can follow the validated MVP.

## Approved MVP interaction and hierarchy

- Home accepts an exact IDX symbol and navigates to the selected IntelScore URL;
  it does not offer autocomplete until a reliable ticker directory exists.
- Home offers BBCA as a real IDX ticker example. Opening it requests the
  backend; no synthetic market data is bundled with the running UI.
- Ticker input accepts exactly four letters, case-insensitively, with optional
  `.JK`; malformed input is rejected before a research request.
- IntelScore is ordered as header/freshness, three separate scores and research
  state, key points, flow evidence, fundamental evidence, then source detail.
- Score breakdowns and dated evidence render inline for the MVP. A drawer or a
  dedicated detail route is deferred.
- Shareholder Composition and Stockchart are labelled `Coming later` and do not
  masquerade as functioning analysis until their screens are delivered.
- The UI must use explicit text and numbers for score and data states; color is
  supplementary, not the only way to communicate status.

## Home

Purpose: explain IntelFlow quickly and move the user into a symbol-first
analysis.

Required content:

- product name and one-sentence flow-first proposition;
- concise explanation that flow is the primary signal and fundamentals are the
  supporting context;
- prominent IDX symbol search/input and IntelScore call to action;
- short “how it works” explanation for Flow, Fundamental, and Combined scores;
- non-advisory disclaimer and Sectors data attribution.

## IntelScore — MVP

Purpose: present a complete, synthesized research view for one ticker without
requiring users to assemble raw Sectors responses themselves.

Required content:

- symbol/company header, symbol switcher, last-updated time, and source-period
  summary;
- separate Flow Score, Fundamental Score, and Combined Score values from 0–100;
- concise key points describing the strongest evidence, conflicts, and missing
  data without producing a buy/sell recommendation;
- broker accumulation/distribution evidence for the supported windows;
- foreign-flow and liquidity context;
- shallow growth, earnings, cash-flow, and valuation support;
- visible source dates and an explanation/drill-down path for each score;
- explicit loading, invalid-symbol, partial-data, stale-data, upstream-error,
  and no-data states.

Scores must never rely on color alone. Numeric values, labels, and supporting
text remain visible for accessibility and interpretation.

## Shareholder Composition — nice to have

Purpose: show how ownership composition changes from month to month for the
selected symbol.

Expected content:

- monthly stacked bar chart;
- legend for the available shareholder categories;
- year or supported-period control;
- shareholder-count change and notable month-over-month movements;
- freshness indicator appropriate to monthly data.

The exact categories must follow available normalized data rather than be
invented by the frontend.

## Stockchart — nice to have

Purpose: inspect market movement together with broker participation for one
symbol.

Expected content:

- range selector for 1 week, 1 month, and 3 months;
- price and volume visualization;
- top three buyer and top three seller brokers selected by default for the
  active range;
- broker selector that lets users add or remove displayed brokers;
- clearly differentiated price, buyer, and seller series with readable
  tooltips and dates;
- a warning when history is incomplete for the requested range.

## Shared interaction rules

- The selected symbol lives in the URL and remains consistent across pages.
- Navigation must make MVP versus nice-to-have scope clear during development;
  unfinished routes should not appear functional.
- The frontend displays backend-derived scores and evidence and never recreates
  scoring formulas.
- Fresh, stale, partial, and unavailable data are visibly distinct.
- Charts require text summaries or accessible labels for their main insight.
- Mobile behavior is deferred until the desktop MVP works, but layouts should
  avoid assumptions that make later responsive work unnecessarily difficult.

## Open UI decisions

- Final brand palette and score-state colors.
- Exact IntelScore chart hierarchy and density.
- Broker-selector interaction once the expected number of brokers is known.
- Responsive navigation behavior after the desktop MVP is validated.

## Implemented MVP decisions — 2026-09-23

- Home (`/`) and symbol entry (`/intel-score`) lead to
  `/stocks/:symbol/intel-score`. Symbols are trimmed, uppercased and stripped of
  an optional `.JK`. Validation checks syntax only, matching the backend rule;
  it does not claim that a ticker exists. There is no default real ticker fetch.
- The selected flow evidence window is shareable as `?window=1d` or `5d`;
  omission means `20d`. Browser back/forward restores the selection. Unsupported
  windows explicitly fall back to 20D. Scores and key points remain on the fixed
  20-observation research window and are labelled accordingly.
- Dark navy surfaces, mint/blue/lavender score accents and locally bundled Inter
  implement the documented dark direction. Colors distinguish sections, not
  scoring thresholds. The generated light wireframe remains a hierarchy reference.
- Key points precede flow evidence. Broker bars show signed IDR with all supplied
  ranked rows; top-3/5/10 comparisons show actual participant counts. Foreign
  cumulative flow and volume/baseline charts include textual summaries and exact
  value tables. Liquidity is shares, never inferred trading value.
- Fundamental groups use a two-column desktop grid for readable metric labels.
  Each group charts one supplied annual metric; all metrics expand inline to
  show their annual values, missing reasons and source links. Undated quarterly
  YoY snapshots have no chart or invented quarter label. Gaps stay null.
- Score breakdowns expand inline with backend values, base weights, reasons and
  source references. Null scores say `Not calculated`; null evidence says
  `Unavailable`. Numeric direction is explicitly not a claim of improvement.
- The source table separates observation date, financial/valuation period,
  effective window, retrieval timestamp (WIB), and backend stale flags. Partial
  and stale notices can coexist. A source without a stale flag is described as
  `Not flagged stale`, not as real-time or guaranteed fresh.
- Loading replaces evidence when switching tickers/windows. A failed flow request
  stays inside its section; the scores remain available. HTTP 404 is `No data
  found`, 422 is `Invalid request`, and network/503 errors provide a retry and
  request ID when supplied. No automatic retry or focus/reconnect refetch runs.
- Home has no automatic market-data request. Opening the BBCA example or
  submitting a ticker uses the same backend research route.
- Sidebar is 240px on wide screens; compact screens wrap to top navigation and
  single-column cards. Keyboard focus, a skip link, form labels, textual status,
  reduced motion and chart alternatives are included. Mobile polish is deferred.

Run instructions and test-only verification live in [FRONTEND.md](./FRONTEND.md).
