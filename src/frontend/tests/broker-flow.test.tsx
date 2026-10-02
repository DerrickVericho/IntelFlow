import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { App } from '../app/App'
import { createQueryClient } from '../api/query'
import type { BrokerFlowResponse } from '../types/research'

vi.mock('../components/Chart', () => ({
  Chart: ({ label, onItemClick }: { label: string; onItemClick?: (index: number) => void }) => (
    <button type="button" aria-label={label} onClick={() => onItemClick?.(1)}>
      Chart date 2
    </button>
  ),
  useChartTheme: () => ({
    chartBase: { tooltip: {} },
    chartColors: { text: '#111', grid: '#ddd', teal: '#087652', red: '#b72e3d' },
  }),
}))

const response: BrokerFlowResponse = {
  symbol: 'BBCA',
  as_of: '2026-09-30',
  status: 'complete',
  sources: [],
  missing_inputs: [],
  range: '5d',
  effective_start: '2026-09-29',
  effective_end: '2026-09-30',
  incomplete_history: false,
  excluded_price_dates: [],
  prices: [
    {
      date: '2026-09-29',
      open: 7400,
      high: 7500,
      low: 7350,
      close: 7450,
      volume: 100,
      market_cap: null,
    },
    {
      date: '2026-09-30',
      open: 7450,
      high: 7550,
      low: 7400,
      close: 7525,
      volume: 120,
      market_cap: null,
    },
  ],
  top_buyers: [{ rank: 1, broker_code: 'A1', net_idr: 168_000_000_000 }],
  top_sellers: [{ rank: 1, broker_code: 'B2', net_idr: -155_000_000_000 }],
  broker_series: [
    {
      broker_code: 'A1',
      side: 'buyer',
      points: [
        { date: '2026-09-29', net_shares: 1000, cumulative_net_shares: 1000 },
        { date: '2026-09-30', net_shares: 2000, cumulative_net_shares: 3000 },
      ],
    },
    {
      broker_code: 'B2',
      side: 'seller',
      points: [
        { date: '2026-09-29', net_shares: -1000, cumulative_net_shares: -1000 },
        { date: '2026-09-30', net_shares: -3000, cumulative_net_shares: -4000 },
      ],
    },
  ],
  days: [
    {
      date: '2026-09-29',
      available: true,
      top_buyers: [{ broker_code: 'A1', shares: 1000 }],
      top_sellers: [{ broker_code: 'B2', shares: 1000 }],
    },
    {
      date: '2026-09-30',
      available: true,
      top_buyers: [{ broker_code: 'A1', shares: 2000 }],
      top_sellers: [{ broker_code: 'B2', shares: 3000 }],
    },
  ],
}

test('BrokerFlow opens daily top net-share rankings and changes period', async () => {
  const fetcher = vi.fn((url: string) => {
    const range = new URL(url, 'http://localhost').searchParams.get('range')
    return Promise.resolve(new Response(JSON.stringify({ ...response, range }), { status: 200 }))
  })
  vi.stubGlobal('fetch', fetcher)
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.removeAttribute('open')
    this.dispatchEvent(new Event('close'))
  }
  render(
    <QueryClientProvider client={createQueryClient()}>
      <MemoryRouter initialEntries={['/broker-flow/BBCA']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Price × cumulative broker flow' })
  expect(screen.getByRole('link', { name: 'BrokerFlow' })).toHaveAttribute('aria-current', 'page')
  await user.click(
    screen.getByRole('button', { name: /price candlesticks and cumulative net shares/i }),
  )
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByRole('heading', { name: '30 Sept 2026' })).toBeInTheDocument()
  expect(
    within(dialog).getByRole('heading', { name: 'Top 5 net buyers · shares' }),
  ).toBeInTheDocument()
  expect(
    within(dialog).getByRole('heading', { name: 'Top 5 net sellers · shares' }),
  ).toBeInTheDocument()
  expect(within(dialog).getByText('3,000')).toBeInTheDocument()
  await user.click(within(dialog).getByRole('button', { name: 'Close' }))
  await user.click(screen.getByRole('button', { name: '1M' }))
  await screen.findByRole('heading', { name: 'Price × cumulative broker flow' })
  expect(fetcher.mock.calls.map((call) => call[0])).toEqual([
    '/api/v1/stocks/BBCA/broker-flow?range=5d',
    '/api/v1/stocks/BBCA/broker-flow?range=1m',
  ])
})
