import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { App } from '../app/App'
import { createQueryClient } from '../api/query'
import testResponse from './data/research-response.json'
import { priceResponse } from './fixtures'
import type { Research } from '../types/research'
import { metricValue, normalizeSymbol, validSymbol } from '../utils/format'
import { getResearch, ApiError } from '../api/client'

vi.mock('../components/Chart', () => ({
  Chart: ({ label }: { label: string }) => <div role="img" aria-label={label} />,
  useChartTheme: () => ({
    chartBase: {},
    chartColors: { text: '', grid: '', teal: '', red: '', blue: '' },
  }),
}))
const reply = (data: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } }),
  )
function mount(path = '/stocks/BBCA/intel-score') {
  const client = createQueryClient()
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return client
}
function mockApi(data: Research = structuredClone(testResponse) as Research) {
  const fetcher = vi.fn((url: string) =>
    reply(url.includes('/price-history?') ? priceResponse('3m') : data),
  )
  vi.stubGlobal('fetch', fetcher)
  return fetcher
}

test('normalizes ticker syntax and preserves null, zero and percent units', () => {
  expect(normalizeSymbol(' bbca.jk ')).toBe('BBCA')
  expect(validSymbol('BBCA')).toBe(true)
  expect(validSymbol('ABC')).toBe(false)
  expect(validSymbol('ABCDE')).toBe(false)
  expect(validSymbol('AB1D')).toBe(false)
  expect(validSymbol('BAD!')).toBe(false)
  expect(metricValue(null, 'percent')).toBe('Unavailable')
  expect(metricValue(0, 'percent')).toBe('0%')
  expect(metricValue(12.4, 'percent')).toBe('12.4%')
})

test('Home exact symbol navigation makes one aggregate request and shows backend scores', async () => {
  const fetcher = mockApi()
  mount('/')
  const user = userEvent.setup()
  await user.type(screen.getByRole('textbox', { name: 'IDX symbol' }), ' bbca.jk ')
  await user.click(screen.getByRole('button', { name: 'Open IntelScore' }))
  await screen.findByText('Test response company')
  expect(screen.getByRole('link', { name: 'Shareholders' })).toHaveAttribute(
    'href',
    '/shareholders',
  )
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(fetcher.mock.calls[0]).toEqual(expect.arrayContaining(['/api/v1/stocks/BBCA/intel-score']))
  for (const key of ['flow', 'fundamental', 'combined'] as const)
    expect(screen.getByTestId(`score-${key}`)).toHaveTextContent(
      String(testResponse.scores[key].value),
    )
})

test('invalid URL ticker never requests the backend', () => {
  const fetcher = mockApi()
  mount('/stocks/BAD!/intel-score')
  expect(screen.getByText('Invalid ticker format')).toBeInTheDocument()
  expect(fetcher).not.toHaveBeenCalled()
})

test('invalid Home submission is accessible and does not fetch', async () => {
  const fetcher = mockApi()
  mount('/')
  await userEvent.click(screen.getByRole('button', { name: 'Open IntelScore' }))
  expect(screen.getByRole('alert')).toHaveTextContent('Invalid ticker format')
  expect(fetcher).not.toHaveBeenCalled()
})

test('flow tabs request only evidence; scores remain from aggregate and 20D reuses it', async () => {
  const data = structuredClone(testResponse) as Research
  const fetcher = vi.fn((url: string) =>
    url.includes('/price-history?')
      ? reply(priceResponse('3m'))
      : url.includes('/flow?')
        ? reply({ ...data, flow: { ...data.flow, window: '5d', trading_days: 5 } })
        : reply(data),
  )
  vi.stubGlobal('fetch', fetcher)
  mount()
  await screen.findByText('Test response company')
  await userEvent.click(screen.getByRole('button', { name: '5D' }))
  await screen.findByText('5 observed trading days')
  expect(fetcher).toHaveBeenCalledTimes(3)
  expect(fetcher.mock.calls.map((call) => call[0])).toContain('/api/v1/stocks/BBCA/flow?window=5d')
  expect(screen.getByTestId('score-flow')).toHaveTextContent(String(testResponse.scores.flow.value))
  await userEvent.click(screen.getByRole('button', { name: '20D' }))
  await screen.findByText('20 observed trading days')
  expect(fetcher).toHaveBeenCalledTimes(3)
})

test('partial and stale are simultaneous, unavailable score never becomes zero', async () => {
  const data = structuredClone(testResponse) as Research
  data.status = 'partial'
  data.sources[0].is_stale = true
  data.scores.flow = { value: null, reason: 'Foreign source missing.', components: [] }
  data.missing_inputs = [{ key: 'foreign_flow', reason: 'Source unavailable.' }]
  mockApi(data)
  mount()
  await screen.findByText('Some data is unavailable')
  expect(screen.getByText('Some sources need an update')).toBeInTheDocument()
  expect(screen.getByTestId('score-flow')).toHaveTextContent('N/A')
  expect(screen.getByText('Foreign source missing.')).toBeInTheDocument()
  expect(screen.getByText('Not calculated')).toBeInTheDocument()
  expect(screen.queryByText('Data availability details (1)')).not.toBeInTheDocument()
  expect(document.querySelector('details')).toBeNull()
})

test('a partial foreign date keeps numeric Flow and Overall scores with low confidence', async () => {
  const data = structuredClone(testResponse) as Research
  data.status = 'partial'
  data.flow.foreign_flow.series = data.flow.foreign_flow.series.slice(1)
  data.missing_inputs = [{ key: 'foreign_flow', reason: 'One date not reported' }]
  data.scores.flow.reason = 'Partial coverage: foreign flow covers 19 of 20 dates.'
  data.scores.combined.reason = 'Includes a Flow Score with partial coverage.'
  mockApi(data)
  mount()
  await screen.findByText('Test response company')
  expect(screen.getByTestId('score-flow')).toHaveTextContent(String(data.scores.flow.value))
  expect(screen.getByTestId('score-combined')).toHaveTextContent(String(data.scores.combined.value))
  expect(screen.getByTestId('data-confidence')).toHaveTextContent('Low')
  expect(
    screen.getAllByText(/overall score uses the available observations/).length,
  ).toBeGreaterThan(0)
  expect(screen.queryByText(/full Flow Score cannot be calculated/)).not.toBeInTheDocument()
})

test('a zero component keeps its colored marker and numeric zero', async () => {
  const data = structuredClone(testResponse) as Research
  data.scores.fundamental.components.find((component) => component.key === 'cash_flow')!.value = 0
  mockApi(data)
  mount()
  await screen.findByText('Test response company')
  const meter = within(screen.getByRole('article', { name: 'Fundamental Score' })).getByRole(
    'meter',
    { name: 'Cash flow score' },
  )
  expect(meter).toHaveAttribute('aria-valuenow', '0')
  expect(meter.firstElementChild).toHaveClass('score-meter-fill', 'min-w-[4px]')
})

test('empty sections and undated quarterly snapshots have explicit states', async () => {
  const data = structuredClone(testResponse) as Research
  data.flow.broker_summary = { brokers: [], breadth: [] }
  data.flow.foreign_flow.series = []
  data.flow.liquidity.series = []
  mockApi(data)
  mount()
  await screen.findByText('No broker observations available for this window.')
  expect(screen.getByText('No foreign-flow timeline available.')).toBeInTheDocument()
  expect(screen.getByText('No volume timeline available.')).toBeInTheDocument()
  expect(screen.getAllByText('Quarterly YoY · undated')).toHaveLength(2)
})

test.each([404, 422, 503])(
  'HTTP %s has distinct messaging and no automatic retries',
  async (status) => {
    const fetcher = vi.fn(() =>
      reply(
        { error: { code: 'TEST', message: 'Test failure', request_id: 'test-request' } },
        status,
      ),
    )
    vi.stubGlobal('fetch', fetcher)
    mount()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      status === 404
        ? 'No data found'
        : status === 422
          ? 'Invalid request'
          : 'Research temporarily unavailable',
    )
    expect(alert).not.toHaveTextContent('test-request')
    expect(alert).not.toHaveTextContent('Test failure')
    if (status === 404)
      expect(alert).toHaveTextContent('does not confirm that the ticker is invalid')
    if (status === 503) {
      await userEvent.click(within(alert).getByRole('button', { name: 'Try again' }))
      await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
    } else expect(fetcher).toHaveBeenCalledTimes(1)
  },
)

test('loading is visible; previous ticker is absent while the next ticker loads', async () => {
  let resolveNext: (r: Response) => void = () => {}
  const fetcher = vi.fn((url: string) =>
    url.includes('/OTHR/')
      ? new Promise<Response>((resolve) => {
          resolveNext = resolve
        })
      : reply(testResponse),
  )
  vi.stubGlobal('fetch', fetcher)
  mount()
  await screen.findByText('Test response company')
  const user = userEvent.setup()
  await user.clear(screen.getByRole('textbox', { name: 'IDX symbol' }))
  await user.type(screen.getByRole('textbox', { name: 'IDX symbol' }), 'OTHR')
  await user.click(screen.getByRole('button', { name: 'Open IntelScore' }))
  await screen.findByText('Loading research and dated evidence…')
  expect(screen.queryByTestId('score-flow')).not.toBeInTheDocument()
  expect(screen.queryByText('Test response company')).not.toBeInTheDocument()
  resolveNext(
    new Response(
      JSON.stringify({
        ...testResponse,
        symbol: 'OTHR',
        company: { ...testResponse.company, name: 'Other test company' },
      }),
    ),
  )
  await screen.findByText('Other test company')
})

test('network failure maps safely and abort remains cancellable', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
  )
  await expect(getResearch('BBCA', new AbortController().signal)).rejects.toBeInstanceOf(ApiError)
  const controller = new AbortController()
  controller.abort()
  await expect(getResearch('BBCA', controller.signal)).rejects.toBeInstanceOf(TypeError)
})

test('revision v2 exposes market context and score components without internal labels or disclosures', async () => {
  const data = structuredClone(testResponse) as Research
  data.status = 'partial'
  data.missing_inputs = [
    { key: 'fundamentals.capital_expenditure', reason: 'Internal unavailable diagnostic' },
  ]
  mockApi(data)
  mount()
  await screen.findByText('Test response company')
  expect(screen.getByTestId('header-volume')).toHaveTextContent(
    new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(
      data.flow.liquidity.latest_volume_shares!,
    ),
  )
  expect(screen.getByTestId('header-average-volume')).not.toHaveTextContent('Unavailable')
  const overall = screen.getByRole('article', { name: 'Overall Score' })
  expect(within(overall).getByText('Combined')).toBeVisible()
  expect(within(overall).getByText('60%')).toBeVisible()
  expect(
    within(screen.getByRole('article', { name: 'Flow Score' })).getByText('Liquidity'),
  ).toBeVisible()
  expect(document.querySelectorAll('details, summary, a[href^="#source"]')).toHaveLength(0)
  expect(screen.queryByText(/fundamentals\.capital_expenditure/)).not.toBeInTheDocument()
  expect(screen.queryByText(/draft-v/)).not.toBeInTheDocument()
  expect(screen.getByText(/Unavailable: capital expenditure/)).toBeInTheDocument()
  expect(screen.getByRole('region', { name: 'Data attribution' })).toHaveTextContent(
    'not investment advice',
  )
})

test.each([-1, 0, 1])(
  'price change %s retains its sign and accessible direction',
  async (change) => {
    const data = structuredClone(testResponse) as Research
    data.company.change_idr = change
    data.company.change_percent = change / 10
    data.flow.liquidity.latest_volume_shares = 0
    data.flow.liquidity.average_volume_shares = null
    mockApi(data)
    mount()
    await screen.findByText('Test response company')
    expect(screen.getByTestId('price-change')).toHaveTextContent(
      change > 0 ? 'Up +1 (+0.1%)' : change < 0 ? 'Down -1 (-0.1%)' : 'Unchanged 0 (0%)',
    )
    expect(screen.getByTestId('header-volume')).toHaveTextContent('0')
    expect(screen.getByTestId('header-average-volume')).toHaveTextContent('Unavailable')
  },
)
