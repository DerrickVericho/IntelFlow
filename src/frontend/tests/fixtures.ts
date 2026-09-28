import response from './data/research-response.json' with { type: 'json' }
import type { PriceResponse } from '../types/research'

export function priceResponse(range: '1m' | '3m' = '1m'): PriceResponse {
  return {
    symbol: response.symbol,
    as_of: response.as_of,
    status: 'complete',
    sources: response.sources,
    missing_inputs: [],
    range,
    effective_start: response.flow.effective_start,
    effective_end: response.flow.effective_end,
    incomplete_history: true,
    series: response.flow.liquidity.series.map((point) => ({
      date: point.date,
      close: point.close_idr,
      volume: point.volume_shares,
      open: null,
      high: null,
      low: null,
      market_cap: null,
    })),
  }
}
