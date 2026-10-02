# Sectors API Contract — Project Scope

This document is the working API reference for AI agents in this project. It
covers only the endpoints currently selected for the project, not the complete
Sectors Financial API.

- Base URL: <code>https://api.sectors.app/v2/</code>
- Response format: JSON
- Authentication: raw API key in the <code>Authorization</code> header, without
  a <code>Bearer</code> prefix
- API version: v2
- Last verified: 2026-09-20
- Primary reference: [Sectors Financial API](https://docs.sectors.app/api-references)

Response examples below are representative and may be abbreviated. Use the
field tables and linked official references for the complete nested schemas.

## Global Contract

All endpoints in this document use HTTP <code>GET</code>, have no request body,
and require these headers:

~~~http
Authorization: <api-key>
Accept: application/json
~~~

Example Bash environment variable:

~~~bash
export SECTORS_API_KEY="replace-with-your-api-key"
~~~

Never store an API key in source code, sample output, logs, or the repository.
Keep the trailing slash on endpoint paths to avoid redirects.

### Shared errors

| Status | Meaning | Agent action |
|---|---|---|
| <code>400</code> | Invalid parameter or date window | Fix the request; do not retry unchanged |
| <code>404</code> | Symbol or requested data was not found | Validate the symbol and data availability |
| <code>429</code> | Rate limit or credit limit exceeded | Stop retrying and report the failure |

~~~json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Consider upgrading."
}
~~~

### Agent usage rules

1. Check the local cache before calling a paid endpoint.
2. Do not automatically retry <code>400</code>, <code>404</code>, or
   <code>429</code> responses.
3. For Company Report, always send an explicit <code>sections</code> list.
4. Use <code>YYYY-MM-DD</code> for all dates.
5. IDX symbols may be provided as <code>BBCA</code> or <code>BBCA.JK</code>.
6. Use a distinct cache name whenever request parameters represent different
   datasets.

## Endpoint Summary

| Area | Endpoint | Credit cost |
|---|---|---:|
| Company Screener | <code>GET /v2/free-float/</code> | 1 per 100 companies |
| Transaction Data | <code>GET /v2/daily/{symbol}/</code> | 1 |
| Detailed Reports | <code>GET /v2/company/get-segments/{symbol}/</code> | 1 |
| Detailed Reports | <code>GET /v2/company/report/{symbol}/</code> | 1 per section; all sections = 8 |
| Detailed Reports | <code>GET /v2/company/shareholders-composition/{symbol}/</code> | 1 |
| Brokers | <code>GET /v2/broker-summary/{symbol}/</code> | 1 |
| Brokers | <code>GET /v2/broker-summary/{symbol}/top/</code> | 2 |
| Brokers | <code>GET /v2/foreign-flow/{symbol}/</code> | 1 |

---

## Company Screener

### Free Float Market Analysis

**Endpoint:** <code>GET /v2/free-float/</code>  
**Cost:** 1 credit per 100 returned companies, rounded up  
**Reference:** [Free Float Market Analysis](https://docs.sectors.app/api-references/v2/indonesia/screener/free-float)

Returns the free-float ratio of IDX-listed companies, ordered from the highest
<code>free_float</code>. Free float is derived from the
<code>share_percentage</code> of the Public entry in the major shareholders
list.

#### Request

All filters are optional and mutually exclusive. Send at most one filter in a
single request.

| Location | Parameter | Type | Example |
|---|---|---|---|
| query | <code>sector</code> | string | <code>infrastructures</code> |
| query | <code>sub_sector</code> | string | <code>banks</code> |
| query | <code>industry</code> | string | <code>oil-gas</code> |
| query | <code>sub_industry</code> | string | <code>coal-production</code> |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/free-float/?sub_industry=coal-production" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/free-float/?sub_industry=coal-production HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

The response is a flat JSON array.

| Field | Type | Description |
|---|---|---|
| <code>symbol</code> | string | Ticker symbol with the <code>.JK</code> suffix |
| <code>company_name</code> | string | Company name |
| <code>free_float</code> | number | Decimal ratio; <code>0.45</code> means 45% |

~~~json
[
  {
    "symbol": "PADI.JK",
    "company_name": "Minna Padi Investama Sekuritas Tbk",
    "free_float": 0.999
  }
]
~~~

---

## Transaction Data

### Daily Transaction Data

**Endpoint:** <code>GET /v2/daily/{symbol}/</code>  
**Cost:** 1 credit  
**Default window:** Last 30 calendar days  
**Maximum window:** 90 calendar days  
**Reference:** [Daily Transaction Data](https://docs.sectors.app/api-references/v2/indonesia/transaction/daily)

Returns daily OHLC prices, trading volume, and market capitalization for one IDX
symbol. A future <code>end</code> date returns <code>400</code>. Requests wider
than 90 days are clamped to the most recent 90 days ending at
<code>end</code>.

IntelFlow uses the earlier of the Jakarta and UTC calendar dates for explicit
market-data range ends. This conservative client policy avoids sending the new
Jakarta date during 00:00–06:59 WIB while it is still the previous date in UTC.
Sectors does not document which timezone it uses for its future-date check, so
this policy does not assert an upstream timezone guarantee.

The API has no <code>limit</code> parameter. To obtain the latest 60 trading
observations, request a 90-calendar-day window, sort by <code>date</code>, and
take the final 60 records locally.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol, for example <code>SINI</code> |
| query | <code>start</code> | no | Start date; defaults to 30 days before <code>end</code> |
| query | <code>end</code> | no | End date; defaults to today |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/daily/SINI/?start=2026-06-22&end=2026-09-20" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/daily/SINI/?start=2026-06-22&end=2026-09-20 HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

The response is a flat JSON array with one object per trading date.

| Field | Type | Description |
|---|---|---|
| <code>symbol</code> | string | Ticker symbol with the <code>.JK</code> suffix |
| <code>date</code> | date | Trading date |
| <code>open</code> | integer or null | Opening price in IDR |
| <code>high</code> | integer or null | Intraday high in IDR |
| <code>low</code> | integer or null | Intraday low in IDR |
| <code>close</code> | integer | Closing price in IDR |
| <code>volume</code> | integer | Trading volume in shares |
| <code>market_cap</code> | integer | Market capitalization in IDR |

~~~json
[
  {
    "symbol": "BBCA.JK",
    "date": "2025-05-02",
    "close": 8975,
    "open": 9000,
    "high": 9000,
    "low": 8850,
    "volume": 92219000,
    "market_cap": 1095329638012500
  }
]
~~~

Endpoint-specific failures include <code>400</code> for an invalid date format or
a future <code>end</code>, and <code>404</code> for an unknown symbol.

---

## Detailed Reports

### Company Revenue Segments

**Endpoint:** <code>GET /v2/company/get-segments/{symbol}/</code>  
**Cost:** 1 credit  
**Reference:** [Company Revenue Segments](https://docs.sectors.app/api-references/v2/indonesia/report/company-segments)

Returns a revenue and cost breakdown as <code>source → target</code> edges ready
for a Sankey graph. Segment data is not available for every company.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol, for example <code>ADMR</code> |
| query | <code>financial_year</code> | no | Defaults to the latest available year |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/company/get-segments/ADMR/?financial_year=2025" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/company/get-segments/ADMR/?financial_year=2025 HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

| Field | Type | Description |
|---|---|---|
| <code>symbol</code> | string | Company symbol |
| <code>financial_year</code> | integer | Financial year of the returned data |
| <code>revenue_breakdown</code> | array | Segment edges |
| <code>revenue_breakdown[].value</code> | number | Edge value |
| <code>revenue_breakdown[].source</code> | string | Source node |
| <code>revenue_breakdown[].target</code> | string | Target node |

~~~json
{
  "symbol": "BBCA.JK",
  "financial_year": 2025,
  "revenue_breakdown": [
    {
      "value": 67446394000000,
      "source": "Loans",
      "target": "Interest Income"
    }
  ]
}
~~~

Endpoint-specific failures include <code>400</code> for an invalid year and
<code>404</code> when the symbol/year combination has no segment data.

### Company Report — Tentative

**Endpoint:** <code>GET /v2/company/report/{symbol}/</code>  
**Cost:** 1 credit per section; omitting <code>sections</code> requests all 8
sections and costs 8 credits  
**Project status:** Selected for fundamental context. Request only the minimum
sections needed; `financials` and `valuation` are the initial Fundamental Score
inputs.
**Reference:** [Company Report](https://docs.sectors.app/api-references/v2/indonesia/report/company-report)

Returns a comprehensive fundamental report. Agents must request only the
sections needed for the task to control both credit use and context size.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol |
| query | <code>sections</code> | strongly recommended | Comma-separated section names |

Valid sections:

| Section | Main content |
|---|---|
| <code>overview</code> | Profile, classification, market cap, price, ESG, tags |
| <code>valuation</code> | PE/PB/PS, intrinsic value, historical valuation |
| <code>future</code> | Forecasts and analyst ratings |
| <code>financials</code> | EPS, historical statements, ratios, and growth |
| <code>dividend</code> | Dividend history, yield, and payout ratio |
| <code>management</code> | Executives and executive shareholdings |
| <code>ownership</code> | Major shareholders and ownership structure |
| <code>peers</code> | Peer comparison |

The following request costs 2 credits:

~~~bash
curl --request GET --url "https://api.sectors.app/v2/company/report/SINI/?sections=overview,financials" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/company/report/SINI/?sections=overview,financials HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

The response contains <code>symbol</code>, <code>company_name</code>, and only
the requested sections. Every section is an object except
<code>peers</code>, which is an array.

~~~json
{
  "symbol": "BBCA.JK",
  "company_name": "PT Bank Central Asia Tbk.",
  "overview": {
    "listing_board": "Main",
    "industry": "Banks",
    "sector": "Financials",
    "market_cap": 753611199412500,
    "last_close_price": 6175
  },
  "financials": {
    "eps": 471.4536454633092,
    "historical_financials": [],
    "historical_financial_ratio": [],
    "yoy_quarter_earnings_growth": 0.0387073681660018,
    "yoy_quarter_revenue_growth": 0.0110150546891309
  }
}
~~~

### Shareholders Composition

**Endpoint:** <code>GET /v2/company/shareholders-composition/{symbol}/</code>  
**Cost:** 1 credit  
**Reference:** [Shareholders Composition](https://docs.sectors.app/api-references/v2/indonesia/company/shareholders-composition)

Returns monthly shareholder-composition snapshots for one calendar year, split
by local (<code>_l</code>) and foreign (<code>_f</code>) investor categories.
Data is available from 2021 onward.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol, for example <code>SINI</code> |
| query | <code>year</code> | no | Defaults to the current year; future years are rejected |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/company/shareholders-composition/SINI/?year=2026" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/company/shareholders-composition/SINI/?year=2026 HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

| Field | Type | Description |
|---|---|---|
| <code>symbol</code> | string | Symbol with the <code>.JK</code> suffix |
| <code>year</code> | integer | Snapshot year |
| <code>data[].date</code> | date | Snapshot date |
| <code>data[].shares_number</code> | integer | Number of issued shares |
| <code>data[].*_l</code> / <code>*_f</code> | integer | Local/foreign category holdings |
| <code>data[].total_l</code> / <code>total_f</code> | integer | Total local/foreign holdings |
| <code>data[].numbers_of_shareholders</code> | integer or null | Number of shareholders, sometimes not reported in historical snapshots |
| <code>data[].change_in_shareholders</code> | integer or null | Change in shareholder count, sometimes not reported in historical snapshots |

Investor categories include insurance, corporate, pension fund, financial
institutions, individual, mutual fund, securities companies, foundation, and
other.

Verified against the provider for SINI: the 2025 and 2024 year queries each
return 12 monthly composition rows, while shareholder-count fields are null in
some historical rows. IntelFlow preserves these nulls and still displays their
category holdings. A provider 404 for a shareholder symbol/year dataset becomes
an empty IntelFlow shareholder result; transport or provider failures remain
errors. The supported year range does not guarantee data for every symbol/year.

~~~json
{
  "symbol": "BBCA.JK",
  "year": 2026,
  "data": [
    {
      "date": "2026-06-30",
      "shares_number": 123275050000,
      "individual_l": 11100401696,
      "individual_f": 326180480,
      "total_l": 16303936654,
      "total_f": 36149754466,
      "numbers_of_shareholders": 797115,
      "change_in_shareholders": 29745
    }
  ]
}
~~~

---

## Brokers

### Broker Activity Per Symbol

**Endpoint:** <code>GET /v2/broker-summary/{symbol}/</code>  
**Cost:** 1 credit  
**Maximum window:** 14 days  
**Reference:** [Broker Activity Per Symbol](https://docs.sectors.app/api-references/v2/indonesia/brokers/broker-summary-by-symbol)

Returns per-broker daily activity for one symbol, grouped by trading date. The
data includes value, lots, frequency, average prices, net flow, and the foreign
investor portion.

The 20-observation Flow Score requests this endpoint in successive windows of
at most 14 calendar days. It uses each dated broker's `bval` and `nval` for
top-3/top-5 consistency and concentration, alongside the separate ranked top
broker endpoint. This adds one paid call per uncached chunk (normally two or
three for 20 trading observations). Missing chunks remain gaps in score
coverage; broker code or broker origin does not identify investor origin.
BrokerFlow uses the same endpoint for up to three months of daily observations,
partitioned into at most 14-calendar-day requests. It converts signed `nlot`
to net shares at 100 shares per lot for cumulative lines; daily popup lists
rank positive and negative `nlot` independently and show absolute shares.
Its 5D/1M/3M controls select the latest 5/20/60 price sessions with positive
volume and valid OHLC, and the request spans their actual first and last dates.
Dated price rows without a drawable traded candle, including ones after the
latest valid candle, are returned separately as `excluded_price_dates` and do
not generate broker-line points. The API does not use a zero-volume or null-OHLC
row as evidence of a formal exchange suspension. When a dated broker
summary is returned but a ranked broker code is absent, IntelFlow treats that
broker as having no reported activity on that day. A missing entire daily
summary remains an explicit gap. Cumulative values after such a gap sum
reported days only.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol |
| query | <code>broker_code</code> | no | Filter to one broker, for example <code>MG</code> |
| query | <code>start</code> | no | Defaults to 14 days before <code>end</code> |
| query | <code>end</code> | no | Defaults to today |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/broker-summary/SINI/?start=2026-09-01&end=2026-09-14&broker_code=MG" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/broker-summary/SINI/?start=2026-09-01&end=2026-09-14&broker_code=MG HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

| Group | Fields | Meaning |
|---|---|---|
| wrapper | <code>symbol</code>, <code>start</code>, <code>end</code> | Symbol and effective range |
| grouping | <code>data[].date</code>, <code>data[].summary[]</code> | Activity grouped by date |
| identity | <code>broker_code</code> | Broker code |
| buy | <code>bfreq</code>, <code>blot</code>, <code>bval</code>, <code>bavg_per_share</code> | Buy frequency, lots, value, average price |
| sell | <code>sfreq</code>, <code>slot</code>, <code>sval</code>, <code>savg_per_share</code> | Sell frequency, lots, value, average price |
| net | <code>nlot</code>, <code>nval</code>, <code>navg_per_share</code> | Net lots/value and average price |
| foreign | <code>f_b*</code>, <code>f_s*</code> | Foreign-investor portion |
| domestic | <code>d_bavg_per_share</code>, <code>d_savg_per_share</code> | Domestic average prices |

~~~json
{
  "symbol": "BBCA.JK",
  "start": "2025-05-01",
  "end": "2025-05-14",
  "data": [
    {
      "date": "2025-05-02",
      "summary": [
        {
          "broker_code": "AF",
          "bfreq": 1,
          "blot": 55,
          "bval": 48950000,
          "sfreq": 1,
          "slot": 50,
          "sval": 44875000,
          "nlot": 5,
          "nval": 4075000
        }
      ]
    }
  ]
}
~~~

### Top Buyers and Sellers Per Symbol

**Endpoint:** <code>GET /v2/broker-summary/{symbol}/top/</code>  
**Cost:** 2 credits  
**Default window:** 90 days  
**Reference:** [Top Buyers and Sellers Per Symbol](https://docs.sectors.app/api-references/v2/indonesia/brokers/broker-summary-top)

Ranks the brokers accumulating and distributing one symbol.
<code>origin</code> uses the broker registry classification, while
<code>foreign=true</code> ranks by the foreign-investor portion of each broker's
flow.

For the fixed 20-observation score, IntelFlow requests this endpoint three
times: `foreign=false` for independent 20-day and 5-day all-investor broker
rankings, and `foreign=true` for the 20-day Foreign Flow component. All use
`cohort=all`, `origin=all`, and `n_brokers=10`; the date range and foreign flag
make each a distinct cached dataset. With `foreign=true`, the ranking follows
`foreign_net_idr`; `net_idr` still describes all-investor net and must not be
used as the foreign score's ranked balance. Shorter evidence tabs request only
their selected `foreign=false` ranking.
BrokerFlow makes a separate `foreign=false`, `cohort=all`, `origin=all`,
`n_brokers=5` request for its effective price-date range. Its period rankings
use `net_idr`; the cumulative chart lines use dated `nlot` from the daily
broker endpoint.

#### Request

| Location | Parameter | Required | Default or valid values |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol |
| query | <code>start</code> | no | 90 days before <code>end</code> |
| query | <code>end</code> | no | Today |
| query | <code>cohort</code> | no | <code>all</code>, <code>institutional</code>, <code>mixed</code>, <code>retail</code>, <code>unknown</code> |
| query | <code>origin</code> | no | <code>all</code>, <code>domestic</code>, <code>foreign</code> |
| query | <code>foreign</code> | no | Boolean; default <code>false</code> |
| query | <code>n_brokers</code> | no | Default 10; range 1–90 |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/broker-summary/SINI/top/?cohort=retail&origin=all&foreign=false&n_brokers=10&start=2026-07-01&end=2026-09-20" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/broker-summary/SINI/top/?cohort=retail&origin=all&foreign=false&n_brokers=10&start=2026-07-01&end=2026-09-20 HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

| Field | Type | Description |
|---|---|---|
| <code>symbol</code>, <code>start</code>, <code>end</code> | string/date | Symbol and effective range |
| <code>origin</code>, <code>cohort</code>, <code>foreign</code> | string/boolean | Effective filters |
| <code>top_buyers</code> / <code>top_sellers</code> | array | Ranked brokers |
| <code>*.rank</code>, <code>*.broker_code</code> | integer/string | Rank and code |
| <code>*.net_idr</code>, <code>*.buy_idr</code>, <code>*.sell_idr</code> | integer | Total flow |
| <code>*.foreign_net_idr</code> | integer | Net foreign-investor flow |
| <code>*.foreign_buy_idr</code>, <code>*.foreign_sell_idr</code> | integer | Foreign buy/sell |

~~~json
{
  "symbol": "BBCA.JK",
  "start": "2025-05-01",
  "end": "2025-05-14",
  "origin": "all",
  "cohort": "all",
  "foreign": false,
  "top_buyers": [
    {
      "rank": 1,
      "broker_code": "KZ",
      "net_idr": 645536242500,
      "buy_idr": 1163325432500,
      "sell_idr": 517789190000,
      "foreign_net_idr": 687991035000
    }
  ],
  "top_sellers": [
    {
      "rank": 1,
      "broker_code": "BK",
      "net_idr": -318961117500,
      "buy_idr": 561727337500,
      "sell_idr": 880688455000,
      "foreign_net_idr": -333245172500
    }
  ]
}
~~~

### Daily Net Foreign Inflow

**Endpoint:** <code>GET /v2/foreign-flow/{symbol}/</code>  
**Cost:** 1 credit  
**Maximum window:** 90 days  
**Reference:** [Daily Net Foreign Inflow](https://docs.sectors.app/api-references/v2/indonesia/brokers/foreign-flow-by-symbol)

Returns daily net foreign inflow in IDR. A positive value means foreign
investors were net buyers; a negative value means they were net sellers. The
classification is based on investor origin, not broker ownership. Use
<code>IHSG</code> for the market-wide aggregate series.

#### Request

| Location | Parameter | Required | Description |
|---|---|---:|---|
| path | <code>symbol</code> | yes | IDX symbol or <code>IHSG</code> |
| query | <code>start</code> | no | Defaults to 90 days before <code>end</code> |
| query | <code>end</code> | no | Defaults to today |

~~~bash
curl --request GET --url "https://api.sectors.app/v2/foreign-flow/SINI/?start=2026-07-01&end=2026-09-20" --header "Authorization: $SECTORS_API_KEY" --header "Accept: application/json"
~~~

~~~http
GET /v2/foreign-flow/SINI/?start=2026-07-01&end=2026-09-20 HTTP/1.1
Host: api.sectors.app
Authorization: <api-key>
Accept: application/json
~~~

#### Response 200

| Field | Type | Description |
|---|---|---|
| <code>symbol</code>, <code>start</code>, <code>end</code> | string/date | Symbol and effective range |
| <code>data[].date</code> | date | Trading date |
| <code>data[].net_foreign_inflow</code> | integer | Net foreign flow in IDR |
| <code>data[].foreign_buy_idr</code> | integer | Foreign buy value |
| <code>data[].foreign_sell_idr</code> | integer | Foreign sell value |
| <code>data[].foreign_share</code> | number | Foreign fraction of two-sided turnover |

~~~json
{
  "symbol": "BBCA.JK",
  "start": "2025-05-01",
  "end": "2025-05-05",
  "data": [
    {
      "date": "2025-05-02",
      "net_foreign_inflow": 146476750000,
      "foreign_buy_idr": 558094712500,
      "foreign_sell_idr": 411617962500,
      "foreign_share": 0.5875
    }
  ]
}
~~~

---

## Endpoint Selection Guide

| Information need | Endpoint |
|---|---|
| Screen public-share availability | Free Float Market Analysis |
| Retrieve daily OHLC, volume, and market cap | Daily Transaction Data |
| Explain company revenue sources | Company Revenue Segments |
| Retrieve a cross-topic fundamental package | Company Report with minimum sections |
| Track local/foreign investor composition | Shareholders Composition |
| Inspect detailed daily broker activity | Broker Activity Per Symbol |
| Identify top accumulating/distributing brokers | Top Buyers and Sellers Per Symbol |
| Measure foreign-investor sentiment and capital flow | Daily Net Foreign Inflow |

## Source-of-Truth Policy

If implementation behavior differs from this document, treat the official
Sectors API reference as the source of truth and update this file. Never guess a
parameter name or response shape because every trial request may consume API
credits.
