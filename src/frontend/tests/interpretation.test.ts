import type { Research } from '../types/research'
import response from './data/research-response.json'
import {
  scoreBand,
  dataConfidence,
  keyInsights,
  researchSummary,
  rupiah,
} from '../features/scores/interpretation'
import { getPriceHistory, ApiError } from '../api/client'
import { priceResponse } from './fixtures'

const sample = () => structuredClone(response) as Research

test.each([
  [null, 'Unavailable'],
  [0, 'Weak'],
  [49.99, 'Weak'],
  [50, 'Neutral'],
  [59.99, 'Neutral'],
  [60, 'Positive'],
  [69.99, 'Positive'],
  [70, 'Strong'],
  [100, 'Strong'],
] as const)('display band for %s is %s', (value, band) => {
  expect(scoreBand(value)).toBe(band)
})

test('mixed evidence receives an explicit summary without changing any backend field', () => {
  const data = sample()
  data.scores.combined.value = 57.17
  data.scores.flow.value = 47.61
  data.scores.fundamental.value = 71.5
  data.scores.flow.components.forEach((c) => {
    c.value = c.key === 'foreign_flow' ? 30 : 48
  })
  data.scores.fundamental.components.forEach((c) => {
    c.value = ['earnings', 'cash_flow'].includes(c.key) ? 85 : 65
  })
  const before = structuredClone(data)
  const summary = researchSummary(data)
  expect(summary.band).toBe('Neutral')
  expect(summary.driver).toMatch(/earnings.*cash flow/)
  expect(summary.risk).toMatch(/Foreign flow is weak/)
  expect(data).toEqual(before)
})

test('confidence describes coverage and freshness, including partial fields and missing dates', () => {
  const data = sample()
  expect(dataConfidence(data).level).toBe('High')
  data.missing_inputs.push({ key: 'fundamentals.capital_expenditure', reason: 'Unavailable' })
  expect(dataConfidence(data).level).toBe('Medium')
  data.sources[0].is_stale = true
  expect(dataConfidence(data).level).toBe('Low')
  expect(researchSummary(data).risk).toContain('stale')
  data.sources[0].is_stale = false
  data.flow.foreign_flow.series.pop()
  expect(dataConfidence(data).level).toBe('Low')
})

test('missing scores and components never produce a fabricated driver or score', () => {
  const data = sample()
  data.scores.combined.value = null
  data.scores.flow.value = null
  data.scores.flow.components = []
  data.scores.fundamental.components = []
  const summary = researchSummary(data)
  expect(summary.band).toBe('Unavailable')
  expect(summary.driver).toContain('No component evidence')
  expect(summary.confidence.level).toBe('Low')
  expect(summary.risk).toContain('coverage is incomplete')
})

test('key insights retain direction, units and category with a maximum of five facts', () => {
  const data = sample()
  data.flow.foreign_flow.net_inflow_idr = -244_100_000_000
  expect(rupiah(-244_100_000_000)).toBe('Rp244.1B')
  const insights = keyInsights(data)
  expect(insights.length).toBeLessThanOrEqual(5)
  expect(insights[0].text).toContain('Rp244.1B net sell')
  expect(new Set(insights.map((i) => i.category))).toEqual(
    new Set(['Flow', 'Fundamental', 'Risk', 'Data Quality']),
  )
})

test('existing price-history endpoint validates symbol, range and numeric closes', async () => {
  const mock = vi.fn(() =>
    Promise.resolve(new Response(JSON.stringify(priceResponse('3m')), { status: 200 })),
  )
  vi.stubGlobal('fetch', mock)
  const result = await getPriceHistory('BBCA', '3m', new AbortController().signal)
  expect(result.range).toBe('3m')
  expect(mock.mock.calls[0]).toEqual(
    expect.arrayContaining(['/api/v1/stocks/BBCA/price-history?range=3m']),
  )
  await expect(getPriceHistory('OTHR', '3m', new AbortController().signal)).rejects.toBeInstanceOf(
    ApiError,
  )
  await expect(getPriceHistory('BBCA', '1m', new AbortController().signal)).rejects.toBeInstanceOf(
    ApiError,
  )
  mock.mockImplementation(() =>
    Promise.resolve(
      new Response(
        JSON.stringify({ ...priceResponse('3m'), series: [{ date: '2026-09-22', close: null }] }),
        { status: 200 },
      ),
    ),
  )
  await expect(getPriceHistory('BBCA', '3m', new AbortController().signal)).rejects.toBeInstanceOf(
    ApiError,
  )
})
