import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Research } from '../../types/research'
import { getPriceHistory } from '../../api/client'
import { Chart, useChartTheme, type ChartOption } from '../../components/Chart'
import { compact, date, number } from '../../utils/format'
import { ui } from '../../components/ui'

type Range = '1m' | '3m' | '1y'
function EmptyTrend({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex min-h-40 flex-col justify-center rounded-xl border border-dashed border-control bg-canvas p-5">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm text-muted">{message}</p>
    </div>
  )
}

function MiniTrend({
  points,
  name,
  unit,
  color,
}: {
  points: { date: string; value: number | null }[]
  name: string
  unit: string
  color: string
}) {
  const { chartBase, chartColors } = useChartTheme()
  const option: ChartOption = {
    ...chartBase,
    grid: { top: 15, right: 16, bottom: 40, left: 65 },
    tooltip: {
      ...chartBase.tooltip,
      valueFormatter: (value) => `${number(Number(value))} ${unit}`,
    },
    xAxis: {
      type: 'category',
      data: points.map((point) => point.date),
      axisLabel: {
        color: chartColors.text,
        fontSize: 13,
        formatter: (value) => date(value).replace(/ \d{4}$/, ''),
      },
      axisLine: { lineStyle: { color: chartColors.grid } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: {
        color: chartColors.text,
        fontSize: 13,
        formatter: (value) => (name === 'Share price' ? number(value, 0) : compact(value)),
      },
      splitLine: { lineStyle: { color: chartColors.grid } },
    },
    series: [
      {
        type: 'line',
        name,
        data: points.map((point) => point.value),
        connectNulls: false,
        showSymbol: points.length < 3,
        symbolSize: 7,
        lineStyle: { color, width: 2.5 },
        itemStyle: { color },
      },
    ],
  }
  const first = points.find((point) => point.value !== null)
  const last = [...points].reverse().find((point) => point.value !== null)
  return (
    <>
      <div className="mb-3 flex flex-wrap justify-between gap-2 text-sm text-muted">
        <span>
          First: {number(first?.value ?? null)} {unit}
        </span>
        <span>
          Last: {number(last?.value ?? null)} {unit}
        </span>
      </div>
      <Chart
        option={option}
        label={`${name}, ${unit}, ${date(first?.date ?? null)} to ${date(last?.date ?? null)}. First ${number(first?.value ?? null)}, last ${number(last?.value ?? null)}. Missing observations remain gaps.`}
        height={180}
      />
    </>
  )
}

export function Trends({ data }: { data: Research }) {
  const [range, setRange] = useState<Range>('1m')
  const { chartColors } = useChartTheme()
  const priceRange = range === '3m' ? '3m' : '1m'
  const query = useQuery({
    queryKey: ['price-history', data.symbol, priceRange],
    queryFn: ({ signal }) => getPriceHistory(data.symbol, priceRange, signal),
    enabled: range !== '1y',
  })
  const prices = query.data?.series ?? []
  // Foreign flow is only supplied for the aggregate's observed dates. Align gaps
  // to those dates; never invent long-range totals or infer daily score history.
  const cutoff = new Date(`${data.flow.effective_end ?? data.as_of}T00:00:00Z`)
  cutoff.setUTCDate(cutoff.getUTCDate() - 29)
  const foreign = data.flow.liquidity.series
    .filter((point) => new Date(`${point.date}T00:00:00Z`) >= cutoff)
    .map((point) => ({
      date: point.date,
      value:
        data.flow.foreign_flow.series.find((item) => item.date === point.date)?.net_inflow_idr ??
        null,
    }))
  const foreignCount = foreign.filter((point) => point.value !== null).length
  const hasForeign = foreignCount >= 2
  return (
    <section className={ui.panel} aria-labelledby="trends-title">
      <div className={ui.sectionHeading}>
        <div>
          <h2 id="trends-title">Change over time</h2>
          <p className="mt-2 text-sm text-muted">
            Available observations, with their actual coverage dates.
          </p>
        </div>
        <div
          className="flex gap-1 rounded-xl border border-line bg-canvas p-1"
          role="group"
          aria-label="Trend period"
        >
          {(['1m', '3m', '1y'] as const).map((item) => {
            const active = range === item
            return (
              <button
                type="button"
                className={`min-h-11 rounded-lg border px-4 text-sm font-semibold ${active ? 'border-period-active bg-period-active text-on-period-active' : 'border-control bg-surface text-ink hover:bg-raised'}`}
                aria-pressed={active}
                key={item}
                onClick={() => setRange(item)}
              >
                {item.toUpperCase()}
              </button>
            )
          })}
        </div>
      </div>
      <div className="grid gap-6 xl:grid-cols-3">
        <article aria-label="Overall Score trend" className="min-w-0">
          <h3 className="mb-4 text-lg">Overall Score</h3>
          <EmptyTrend
            title="Score history unavailable"
            message="Only the current score is available. No prior-week or prior-month comparison can be shown."
          />
        </article>
        <article aria-label="Share price trend" className="min-w-0">
          <h3 className="mb-4 text-lg">
            Share price <span className="text-sm font-normal text-muted">IDR</span>
          </h3>
          {range === '1y' ? (
            <EmptyTrend
              title="1Y price history unavailable"
              message="Price history currently supports up to 3M. Select 1M or 3M for available closes."
            />
          ) : query.isPending ? (
            <p className="min-h-40 py-10 text-sm text-muted" role="status">
              Loading price history…
            </p>
          ) : query.isError ? (
            <EmptyTrend
              title="Price history unavailable"
              message="The selected history could not be loaded. Other research remains available."
            />
          ) : prices.length < 2 ? (
            <EmptyTrend
              title="Not enough price observations"
              message="At least two dated closes are needed to display a trend."
            />
          ) : (
            <>
              <MiniTrend
                points={prices.map((point) => ({ date: point.date, value: point.close }))}
                name="Share price"
                unit="IDR"
                color={chartColors.blue}
              />
              <p className="mt-3 text-sm text-muted">
                {date(prices[0].date)} – {date(prices.at(-1)!.date)} · {prices.length} closes
                {query.data?.incomplete_history || query.data?.status === 'partial'
                  ? ' · Partial coverage'
                  : ''}
                {query.data?.status === 'stale' ||
                query.data?.sources.some((source) => source.is_stale)
                  ? ' · Update needed'
                  : ''}
              </p>
            </>
          )}
        </article>
        <article aria-label="Foreign flow trend" className="min-w-0">
          <h3 className="mb-4 text-lg">
            Daily foreign flow <span className="text-sm font-normal text-muted">IDR</span>
          </h3>
          {range !== '1m' ? (
            <EmptyTrend
              title={`${range.toUpperCase()} foreign-flow history unavailable`}
              message={`The current research includes only ${data.flow.trading_days} trading observations. Longer history is not available.`}
            />
          ) : !hasForeign ? (
            <EmptyTrend
              title="Not enough foreign-flow observations"
              message="At least two dated foreign-flow values are needed to display a trend."
            />
          ) : (
            <>
              <MiniTrend
                points={foreign}
                name="Daily foreign net flow"
                unit="IDR"
                color={chartColors.teal}
              />
              <p className="mt-3 text-sm text-muted">
                {date(foreign[0].date)} – {date(foreign.at(-1)!.date)} · {foreignCount} available
                observations. Available 1M subset; not a complete calendar-month history.
              </p>
            </>
          )}
        </article>
      </div>
    </section>
  )
}
