import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { App } from '../app/App'
import { createQueryClient } from '../api/query'
import { categoryBreakdown, monthlySnapshots, shareholderCategories } from '../features/shareholders/composition'
import type { ShareholderResponse } from '../types/research'

vi.mock('../components/Chart', () => ({
  Chart: ({ option, label }: { option: { series: { data: (number | null)[] }[] }; label: string }) =>
    <div role="img" aria-label={label} data-series={JSON.stringify(option.series.map(series => series.data))} />,
  useChartTheme: () => ({ chartBase: {}, chartColors: { text: '#111', grid: '#ddd', blue: '#002fa7' } }),
}))

const year = Number(new Intl.DateTimeFormat('en-US', { year: 'numeric', timeZone: 'Asia/Jakarta' }).format(new Date()))
const fixture: ShareholderResponse = {
  symbol: 'BBCA', as_of: `${year}-08-31`, status: 'complete', sources: [], missing_inputs: [], year,
  supported_years: [year - 1, year],
  categories: [
    { key: 'corporate_l', label: 'Corporate Local' }, { key: 'corporate_f', label: 'Corporate Foreign' },
    { key: 'individual_l', label: 'Individual Local' }, { key: 'individual_f', label: 'Individual Foreign' },
  ],
  series: [
    { date: `${year}-07-31`, shares_number: 100, holdings: { corporate_l: 40, corporate_f: 10, individual_l: 50, individual_f: 0 }, total_local: 90, total_foreign: 10, shareholder_count: 12, shareholder_count_change: 2 },
    { date: `${year}-08-31`, shares_number: 100, holdings: { corporate_l: 60, corporate_f: 10, individual_l: 20, individual_f: 10 }, total_local: 80, total_foreign: 20, shareholder_count: 10, shareholder_count_change: -2 },
  ],
}

test('monthly category stacks use origin fields and preserve months without snapshots', () => {
  const categories = shareholderCategories(fixture.categories)
  const august = fixture.series[1]
  expect(categories.map(category => category.label)).toEqual(['Corporate', 'Individual'])
  expect(categoryBreakdown(august, categories, 'all').rows.map(row => row.value)).toEqual([70, 30])
  expect(categoryBreakdown(august, categories, 'local').rows.map(row => row.value)).toEqual([60, 20])
  expect(categoryBreakdown(august, categories, 'foreign').rows.map(row => row.value)).toEqual([10, 10])
  expect(monthlySnapshots(fixture.series, year).map(point => point?.date ?? null)).toEqual([
    null, null, null, null, null, null, `${year}-07-31`, `${year}-08-31`, null, null, null, null,
  ])
  const incomplete = { ...august, holdings: { ...august.holdings, corporate_f: null } }
  expect(categoryBreakdown(incomplete, categories, 'all').incomplete).toBe(true)
  expect(categoryBreakdown(incomplete, categories, 'all').rows[0].value).toBeNull()
})

test('shareholder page toggles chart shares and composition without another request', async () => {
  const fetcher = vi.fn(() => Promise.resolve(new Response(JSON.stringify(fixture), { status: 200 })))
  vi.stubGlobal('fetch', fetcher)
  render(<QueryClientProvider client={createQueryClient()}><MemoryRouter initialEntries={['/shareholders/BBCA']}><App /></MemoryRouter></QueryClientProvider>)
  const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Reported holdings by category' })
  const details = screen.getByRole('complementary', { name: 'Shareholder category details' })
  expect(within(details).getByText('70')).toBeInTheDocument()
  expect(screen.getAllByRole('combobox')).toHaveLength(3) // appearance, year, category month
  await user.click(screen.getByRole('button', { name: 'Foreign' }))
  expect(within(details).getAllByText('10')).toHaveLength(2)
  await user.click(screen.getByRole('button', { name: 'Composition %' }))
  const composition = screen.getByRole('img', { name: /monthly foreign investor shareholder category composition percentages/i })
  const bars = JSON.parse(composition.getAttribute('data-series') ?? '[]') as (number | null)[][]
  expect(bars.map(series => series[7])).toEqual([50, 50])
  expect(bars.every(series => series[0] === null)).toBe(true)
  expect(screen.getByRole('heading', { name: 'Shareholder count by month' }).closest('section')).toHaveTextContent('Change vs prior month: -2')
  expect(fetcher).toHaveBeenCalledTimes(1)
})

test('historical year fetches again and retains composition when counts are null', async () => {
  const pastYear = year - 1
  const past: ShareholderResponse = { ...fixture, year: pastYear, as_of: `${pastYear}-08-31`, status: 'partial',
    missing_inputs: [{ key: 'shareholders.count', reason: 'Some counts were not reported' }],
    series: fixture.series.map(point => ({ ...point, date: point.date.replace(`${year}-`, `${pastYear}-`), shareholder_count: null, shareholder_count_change: null })) }
  const fetcher = vi.fn((url: string) => Promise.resolve(new Response(JSON.stringify(url.includes(`year=${pastYear}`) ? past : fixture), { status: 200 })))
  vi.stubGlobal('fetch', fetcher)
  render(<QueryClientProvider client={createQueryClient()}><MemoryRouter initialEntries={['/shareholders/BBCA']}><App /></MemoryRouter></QueryClientProvider>)
  await screen.findByRole('heading', { name: 'Reported holdings by category' })
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Shareholder year' }), String(pastYear))
  await screen.findByText(`Shareholder counts were not reported for ${pastYear}. Category holdings remain available above.`)
  expect(screen.getByRole('complementary', { name: 'Shareholder category details' })).toHaveTextContent('Corporate')
  expect(fetcher.mock.calls.map(call => call[0])).toEqual([
    `/api/v1/stocks/BBCA/shareholders?year=${year}`,
    `/api/v1/stocks/BBCA/shareholders?year=${pastYear}`,
  ])
  expect(screen.queryByText('Shareholder data is unavailable')).not.toBeInTheDocument()
})

test('shareholder search has its own entry and does not open IntelScore', async () => {
  const fetcher = vi.fn((url: string) => Promise.resolve(new Response(JSON.stringify({ ...fixture, symbol: url.includes('/SINI/') ? 'SINI' : 'BBCA' }), { status: 200 })))
  vi.stubGlobal('fetch', fetcher)
  render(<QueryClientProvider client={createQueryClient()}><MemoryRouter initialEntries={['/shareholders']}><App /></MemoryRouter></QueryClientProvider>)
  expect(screen.getByRole('heading', { name: /Which company's shareholders/ })).toBeInTheDocument()
  expect(fetcher).not.toHaveBeenCalled()
  await userEvent.type(screen.getByRole('textbox', { name: 'Shareholder IDX symbol' }), 'SINI')
  await userEvent.click(screen.getByRole('button', { name: 'Open Shareholders' }))
  await screen.findByRole('heading', { name: 'Reported holdings by category' })
  expect(fetcher.mock.calls[0][0]).toBe(`/api/v1/stocks/SINI/shareholders?year=${year}`)
  await userEvent.click(screen.getByRole('link', { name: 'IntelScore' }))
  expect(screen.getByRole('heading', { name: 'Which company are you researching?' })).toBeInTheDocument()
  expect(fetcher).toHaveBeenCalledTimes(1)
})
