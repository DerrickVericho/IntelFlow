import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Navigate, useParams } from 'react-router'
import { ApiError, getShareholders } from '../api/client'
import { Chart, useChartTheme, type ChartOption } from '../components/Chart'
import { DataStatus, Loading } from '../components/States'
import { ui } from '../components/ui'
import {
  categoryBreakdown,
  monthlySnapshots,
  shareholderCategories,
  type CompositionMode,
  type InvestorOrigin,
} from '../features/shareholders/composition'
import { compact, date, number, normalizeSymbol, validSymbol } from '../utils/format'
import type { ShareholderResponse } from '../types/research'

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const categoryColors: Record<string, string> = {
  corporate: '--share-corporate',
  individual: '--share-individual',
  mutual_fund: '--share-mutual-fund',
  other: '--share-other',
  financial_institutions: '--share-financial-institutions',
  securities_companies: '--share-securities-companies',
  insurance: '--share-insurance',
  pension_fund: '--share-pension-fund',
  foundation: '--share-foundation',
}
const originLabels: Record<InvestorOrigin, string> = {
  all: 'All',
  local: 'Local',
  foreign: 'Foreign',
}
const currentYear = () =>
  Number(
    new Intl.DateTimeFormat('en-US', { year: 'numeric', timeZone: 'Asia/Jakarta' }).format(
      new Date(),
    ),
  )
const percentage = (part: number, whole: number) =>
  whole > 0 ? `${number((part / whole) * 100, 2)}%` : 'Unavailable'

function NoSnapshots({ symbol, year }: { symbol: string; year: number }) {
  return (
    <section className={ui.empty} role="status">
      <h2 className="text-xl">
        No shareholder snapshots for {symbol} in {year}
      </h2>
      <p className="mt-2">
        No monthly composition data was returned for this symbol and year. Choose another year or
        search another company.
      </p>
    </section>
  )
}

function ShareholdersError({
  error,
  retry,
  symbol,
  year,
}: {
  error: Error
  retry: () => void
  symbol: string
  year: number
}) {
  const api = error instanceof ApiError ? error : null
  if (api?.status === 404) return <NoSnapshots symbol={symbol} year={year} />
  return (
    <section className={ui.errorBox} role="alert">
      <h2>Shareholder data is unavailable</h2>
      <p>
        {api?.code === 'UPSTREAM_RATE_LIMIT'
          ? 'The data request limit has been reached. Please try again later.'
          : 'We could not retrieve shareholder data for this year right now. Choose another year or try again later.'}
      </p>
      {(!api || api.status === 0 || api.status >= 500) && (
        <button className={`${ui.secondary} mt-5`} onClick={retry}>
          Try again
        </button>
      )}
    </section>
  )
}

function Segmented<T extends string>({
  label,
  values,
  value,
  onChange,
}: {
  label: string
  values: { key: T; text: string }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-canvas p-1"
    >
      {values.map((item) => (
        <button
          key={item.key}
          type="button"
          aria-pressed={item.key === value}
          onClick={() => onChange(item.key)}
          className={`min-h-10 rounded-lg border px-3 text-sm font-semibold sm:px-4 ${item.key === value ? 'border-period-active bg-period-active text-on-period-active' : 'border-control bg-surface text-ink hover:bg-raised'}`}
        >
          {item.text}
        </button>
      ))}
    </div>
  )
}

function ShareholderContent({ data }: { data: ShareholderResponse }) {
  const [origin, setOrigin] = useState<InvestorOrigin>('all')
  const [mode, setMode] = useState<CompositionMode>('shares')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const { chartBase, chartColors } = useChartTheme()
  const categories = shareholderCategories(data.categories)
  const snapshots = monthlySnapshots(data.series, data.year)
  const available = snapshots.filter((point) => point !== null)
  const countAvailable = available.some((point) => point.shareholder_count !== null)
  const selected =
    available.find((point) => point.date === selectedDate) ?? available.at(-1) ?? null
  const selectedBreakdown = selected ? categoryBreakdown(selected, categories, origin) : null
  const styles = getComputedStyle(document.documentElement)
  const color = (key: string) => styles.getPropertyValue(categoryColors[key] ?? '--muted').trim()
  const axis = {
    axisLabel: { color: chartColors.text, fontSize: 12 },
    axisLine: { lineStyle: { color: chartColors.grid } },
  }
  const barOption: ChartOption = {
    ...chartBase,
    grid: { top: 20, left: 64, right: 20, bottom: 38 },
    tooltip: {
      ...chartBase.tooltip,
      trigger: 'item',
      formatter: mode === 'percent' ? '{b}\n{a}: {c}%' : '{b}\n{a}: {c} shares',
    },
    xAxis: {
      type: 'category',
      data: months,
      ...axis,
      axisTick: { alignWithLabel: true },
      axisLabel: { color: chartColors.text, fontSize: 12, interval: 0 },
    },
    yAxis: {
      type: 'value',
      max: mode === 'percent' ? 100 : undefined,
      ...axis,
      axisLabel: {
        color: chartColors.text,
        formatter: (value: number) => (mode === 'percent' ? `${value}%` : compact(value)),
      },
      splitLine: { lineStyle: { color: chartColors.grid } },
    },
    series: categories.map((category) => ({
      type: 'bar' as const,
      name: category.label,
      stack: 'categories',
      barMaxWidth: 42,
      itemStyle: { color: color(category.key) },
      data: snapshots.map((point) => {
        if (!point) return null
        const breakdown = categoryBreakdown(point, categories, origin)
        const value = breakdown.rows.find((row) => row.key === category.key)?.value
        return value === null || value === undefined
          ? null
          : mode === 'percent'
            ? breakdown.reported > 0
              ? Number(((value / breakdown.reported) * 100).toFixed(4))
              : null
            : value
      }),
    })),
  }
  const countOption: ChartOption = {
    ...chartBase,
    grid: { top: 18, left: 64, right: 20, bottom: 36 },
    tooltip: { ...chartBase.tooltip, trigger: 'item', formatter: '{b}\n{a}: {c}' },
    xAxis: {
      type: 'category',
      data: months,
      ...axis,
      axisLabel: { color: chartColors.text, fontSize: 12, interval: 0 },
    },
    yAxis: {
      type: 'value',
      scale: true,
      minInterval: 1,
      ...axis,
      axisLabel: { color: chartColors.text, formatter: (value: number) => compact(value) },
      splitLine: { lineStyle: { color: chartColors.grid } },
    },
    series: [
      {
        type: 'line',
        name: 'Shareholders',
        data: snapshots.map((point) => point?.shareholder_count ?? null),
        connectNulls: false,
        showSymbol: true,
        symbolSize: 9,
        lineStyle: { color: chartColors.blue, width: 2 },
        itemStyle: { color: chartColors.blue },
      },
    ],
  }
  const chartDescription = available
    .map(
      (point) =>
        `${date(point.date)}: ${categories
          .map((category) => {
            const value = categoryBreakdown(point, categories, origin).rows.find(
              (row) => row.key === category.key,
            )?.value
            return `${category.label} ${number(value ?? null)}`
          })
          .join(', ')}`,
    )
    .join('. ')
  const coverageGaps = available.some(
    (point) => categoryBreakdown(point, categories, origin).incomplete,
  )
  if (available.length === 0) return <NoSnapshots symbol={data.symbol} year={data.year} />
  return (
    <div className="space-y-6">
      <DataStatus data={data} />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(310px,380px)]">
        <section className={ui.panel} aria-labelledby="composition-title">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 id="composition-title">Reported holdings by category</h2>
              <p className="mt-1 text-sm text-muted">Monthly snapshots · {data.year}</p>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Segmented
              label="Investor origin"
              value={origin}
              onChange={setOrigin}
              values={(['all', 'local', 'foreign'] as InvestorOrigin[]).map((key) => ({
                key,
                text: originLabels[key],
              }))}
            />
            <Segmented
              label="Bar chart view"
              value={mode}
              onChange={setMode}
              values={[
                { key: 'shares', text: 'Shares' },
                { key: 'percent', text: 'Composition %' },
              ]}
            />
          </div>
          <p className="mt-3 text-sm text-muted">
            {mode === 'percent'
              ? 'Each month shows the share of reported category holdings for the selected investor origin.'
              : 'Bars show reported shares for the selected investor origin.'}{' '}
            Select a month to inspect its categories.
          </p>
          {available.length ? (
            <Chart
              option={barOption}
              label={`Monthly ${origin} investor shareholder category ${mode === 'percent' ? 'composition percentages' : 'holdings in shares'}. ${chartDescription}`}
              height={330}
              onItemClick={(index) => {
                const point = snapshots[index]
                if (point) setSelectedDate(point.date)
              }}
            />
          ) : (
            <p className={`${ui.empty} mt-5`}>
              No shareholder snapshots are available for {data.year}. Choose another year.
            </p>
          )}
          {available.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm">
              {categories.map((category) => (
                <span key={category.key} className="inline-flex items-center gap-2 text-ink">
                  <span
                    aria-hidden="true"
                    className="size-2.5 rounded-sm"
                    style={{ backgroundColor: color(category.key) }}
                  />
                  {category.label}
                </span>
              ))}
            </div>
          )}
          {coverageGaps && (
            <p className="mt-4 text-sm text-muted">
              Category holdings do not fully match the reported investor totals in every month.
              Composition percentages use available category holdings only.
            </p>
          )}
        </section>
        <aside className={ui.panel} aria-label="Shareholder category details">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl">Category details</h2>
            {available.length > 0 && (
              <select
                aria-label="Selected shareholder month"
                className="min-h-11 rounded-xl border border-control bg-surface px-3 text-sm text-ink"
                value={selected?.date ?? ''}
                onChange={(event) => setSelectedDate(event.target.value)}
              >
                {available.map((point) => (
                  <option key={point.date} value={point.date}>
                    {date(point.date)}
                  </option>
                ))}
              </select>
            )}
          </div>
          {selected && selectedBreakdown ? (
            <>
              <dl className="mt-6 space-y-3 border-b border-line pb-6 text-sm [&_div]:flex [&_div]:justify-between [&_div]:gap-4 [&_dt]:text-muted [&_dd]:text-right [&_dd]:font-semibold [&_dd]:tabular-nums">
                <div>
                  <dt>Issued shares</dt>
                  <dd>{number(selected.shares_number)}</dd>
                </div>
                <div>
                  <dt>Local holdings</dt>
                  <dd>{number(selected.total_local)}</dd>
                </div>
                <div>
                  <dt>Foreign holdings</dt>
                  <dd>{number(selected.total_foreign)}</dd>
                </div>
                <div>
                  <dt>Reported categories · {originLabels[origin]}</dt>
                  <dd>{number(selectedBreakdown.reported)}</dd>
                </div>
              </dl>
              <h3 className="mt-6 mb-3 text-base">{originLabels[origin]} holdings by category</h3>
              <ul className="space-y-3">
                {[...selectedBreakdown.rows]
                  .sort((a, b) => (b.value ?? -1) - (a.value ?? -1))
                  .map((row) => (
                    <li key={row.key} className="flex items-center justify-between gap-3 text-sm">
                      <span className="inline-flex min-w-0 items-center gap-2">
                        <span
                          aria-hidden="true"
                          className="size-2.5 shrink-0 rounded-sm"
                          style={{ backgroundColor: color(row.key) }}
                        />
                        {row.label}
                      </span>
                      <span className="shrink-0 text-right tabular-nums">
                        <strong>{number(row.value)}</strong>
                        <span className="ml-2 text-muted">
                          {row.value === null
                            ? '—'
                            : percentage(row.value, selectedBreakdown.reported)}
                        </span>
                      </span>
                    </li>
                  ))}
              </ul>
              {selectedBreakdown.incomplete && (
                <p className="mt-5 text-sm text-muted">
                  Reported category holdings do not match the {originLabels[origin].toLowerCase()}{' '}
                  investor total for this month.
                </p>
              )}
            </>
          ) : (
            <p className="mt-6 text-sm text-muted">
              No category details are available for this year.
            </p>
          )}
        </aside>
      </div>
      <section className={ui.panel} aria-labelledby="shareholder-count-title">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 id="shareholder-count-title">Shareholder count by month</h2>
            <p className="mt-1 text-sm text-muted">Reported number of shareholders</p>
          </div>
          {selected && (
            <p className="text-sm tabular-nums">
              <span className="text-muted">{date(selected.date)} · </span>
              <strong className="text-xl">{number(selected.shareholder_count)}</strong>
              <span className="ml-3 text-muted">Change vs prior month: </span>
              <strong
                className={
                  selected.shareholder_count_change !== null &&
                  selected.shareholder_count_change < 0
                    ? 'text-negative'
                    : selected.shareholder_count_change !== null &&
                        selected.shareholder_count_change > 0
                      ? 'text-positive'
                      : 'text-ink'
                }
              >
                {selected.shareholder_count_change !== null && selected.shareholder_count_change > 0
                  ? '+'
                  : ''}
                {number(selected.shareholder_count_change)}
              </strong>
            </p>
          )}
        </div>
        {countAvailable ? (
          <Chart
            option={countOption}
            label={`Monthly shareholder counts. ${available.map((point) => `${date(point.date)}: ${number(point.shareholder_count)}, change ${number(point.shareholder_count_change)}`).join('. ')}`}
            height={230}
            onItemClick={(index) => {
              const point = snapshots[index]
              if (point) setSelectedDate(point.date)
            }}
          />
        ) : (
          <p className={`${ui.empty} mt-5`}>
            Shareholder counts were not reported for {data.year}. Category holdings remain available
            above.
          </p>
        )}
      </section>
      <footer className="flex flex-wrap justify-between gap-3 border-t border-line pt-5 text-sm text-muted">
        <span>
          Source: SectorsAPI · monthly snapshots{data.as_of ? ` · latest ${date(data.as_of)}` : ''}
        </span>
        <span>For research purposes only — not investment advice.</span>
      </footer>
    </div>
  )
}

export function ShareholdersPage() {
  const { symbol: raw = '' } = useParams()
  const symbol = normalizeSymbol(raw)
  const valid = validSymbol(symbol)
  const [year, setYear] = useState(currentYear)
  const query = useQuery({
    queryKey: ['shareholders', symbol, year],
    queryFn: ({ signal }) => getShareholders(symbol, year, signal),
    enabled: valid && raw === symbol,
  })
  useEffect(() => {
    document.title = `${symbol} · Shareholders | IntelFlow`
    return () => {
      document.title = 'IntelFlow · IDX research'
    }
  }, [symbol])
  if (valid && raw !== symbol) return <Navigate to={`/shareholders/${symbol}`} replace />
  const years =
    query.data?.supported_years ??
    Array.from({ length: currentYear() - 2020 }, (_, index) => currentYear() - index)
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-sm font-medium text-muted">IDX · {symbol}</p>
          <h1>Shareholder composition</h1>
          <p className="mt-2 text-sm text-muted">
            Monthly ownership categories and shareholder count
          </p>
        </div>
        <label className="flex items-center gap-3 text-sm text-muted">
          Year{' '}
          <select
            aria-label="Shareholder year"
            className="min-h-11 rounded-xl border border-control bg-surface px-4 text-ink"
            value={year}
            onChange={(event) => setYear(Number(event.target.value))}
          >
            {years.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </header>
      {!valid && (
        <div className={ui.errorBox} role="alert">
          <h2>Invalid ticker format</h2>
          <p>Use exactly four letters. The .JK suffix is optional.</p>
        </div>
      )}
      {valid && query.isPending && <Loading text="Loading shareholder composition…" />}
      {valid && query.isError && (
        <ShareholdersError
          error={query.error}
          retry={() => void query.refetch()}
          symbol={symbol}
          year={year}
        />
      )}
      {query.data && <ShareholderContent key={`${symbol}-${year}`} data={query.data} />}
    </div>
  )
}
