import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Navigate, useParams } from 'react-router'
import { getBrokerFlow } from '../api/client'
import { Chart, useChartTheme, type ChartOption } from '../components/Chart'
import { DataStatus, ErrorState, Loading } from '../components/States'
import { ui } from '../components/ui'
import type { BrokerFlowRange, BrokerFlowResponse } from '../types/research'
import { compact, date, number, normalizeSymbol, validSymbol } from '../utils/format'

const ranges: { value: BrokerFlowRange; label: string }[] = [
  { value: '5d', label: '5D' },
  { value: '1m', label: '1M' },
  { value: '3m', label: '3M' },
]

const signed = (value: number) =>
  `${value > 0 ? '+' : value < 0 ? '−' : ''}${compact(Math.abs(value))}`

function DayList({
  title,
  rows,
  color,
}: {
  title: string
  rows: BrokerFlowResponse['days'][number]['top_buyers']
  color: 'positive' | 'negative'
}) {
  return (
    <section>
      <h3 className="mb-3 text-base font-semibold">{title}</h3>
      {rows.length ? (
        <ol className="space-y-2">
          {rows.map((row, index) => (
            <li
              key={row.broker_code}
              className="grid grid-cols-[1.5rem_3.5rem_minmax(0,1fr)_auto] items-center gap-2 border-b border-line py-2 text-sm tabular-nums"
            >
              <span className="text-muted">{index + 1}</span>
              <strong>{row.broker_code}</strong>
              <span className="h-2 overflow-hidden rounded-sm bg-raised" aria-hidden="true">
                <span
                  className={`block h-full ${color === 'positive' ? 'bg-positive' : 'bg-negative'}`}
                  style={{ width: `${(row.shares / rows[0].shares) * 100}%` }}
                />
              </span>
              <strong>{number(row.shares, 0)}</strong>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-muted">No reported broker quantity for this side.</p>
      )}
    </section>
  )
}

function DayDialog({
  day,
  onClose,
}: {
  day: BrokerFlowResponse['days'][number]
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const element = dialog.current
    element?.showModal()
    return () => {
      if (element?.open) element.close()
    }
  }, [])
  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      aria-labelledby="broker-day-title"
      className="m-auto max-h-[90dvh] w-[min(92vw,800px)] overflow-y-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl backdrop:bg-[#0b192b]/70"
    >
      <div className="border-b border-line px-5 py-5 sm:px-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="mb-1 text-sm text-muted">Daily broker activity</p>
            <h2 id="broker-day-title" className="text-2xl">
              {date(day.date)}
            </h2>
          </div>
          <button type="button" className={ui.secondary} onClick={() => dialog.current?.close()}>
            Close
          </button>
        </div>
        <p className="mt-3 text-sm text-muted">
          Top brokers by net buy and net sell quantity on this date. Values are shares.
        </p>
      </div>
      <div className="grid gap-7 px-5 py-6 sm:grid-cols-2 sm:px-7">
        {day.available ? (
          <>
            <DayList title="Top 5 net buyers · shares" rows={day.top_buyers} color="positive" />
            <DayList title="Top 5 net sellers · shares" rows={day.top_sellers} color="negative" />
          </>
        ) : (
          <p className="text-sm text-muted sm:col-span-2">
            Broker activity was not returned for this trading date.
          </p>
        )}
      </div>
      <p className="border-t border-line px-5 py-4 text-xs text-muted sm:px-7">
        Daily lists rank net share quantity. Period rankings below the chart use net IDR.
      </p>
    </dialog>
  )
}

function Ranking({
  title,
  rows,
  maximum,
  side,
  focused,
  onFocus,
}: {
  title: string
  rows: BrokerFlowResponse['top_buyers']
  maximum: number
  side: 'buyer' | 'seller'
  focused: string | null
  onFocus: (broker: string | null) => void
}) {
  return (
    <section className={ui.panel} aria-label={title}>
      <h2 className="text-xl">{title}</h2>
      <p className="mt-1 text-sm text-muted">Period net value · IDR</p>
      {rows.length ? (
        <ol className="mt-6 space-y-4">
          {rows.map((row) => (
            <li key={row.broker_code}>
              <button
                type="button"
                aria-pressed={focused === row.broker_code}
                aria-label={`Highlight broker ${row.broker_code}`}
                className="grid w-full grid-cols-[1.5rem_2.5rem_minmax(0,1fr)_auto] items-center gap-2 text-left text-sm tabular-nums hover:text-accent focus-visible:rounded-sm focus-visible:outline-2 focus-visible:outline-accent"
                onClick={() => onFocus(focused === row.broker_code ? null : row.broker_code)}
              >
                <span className="text-muted">{row.rank}</span>
                <strong>{row.broker_code}</strong>
                <span
                  className="h-3 min-w-0 overflow-hidden rounded-sm bg-raised"
                  aria-hidden="true"
                >
                  <span
                    className={`block h-full ${side === 'buyer' ? 'bg-positive' : 'bg-negative'}`}
                    style={{ width: `${(Math.abs(row.net_idr) / maximum) * 100}%` }}
                  />
                </span>
                <strong className="text-right">{signed(row.net_idr)}</strong>
              </button>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-6 text-sm text-muted">No ranked brokers were returned for this period.</p>
      )}
    </section>
  )
}

function BrokerFlowContent({ data }: { data: BrokerFlowResponse }) {
  const [focused, setFocused] = useState<string | null>(null)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const { chartBase, chartColors } = useChartTheme()
  const styles = getComputedStyle(document.documentElement)
  const colors = Array.from({ length: 10 }, (_, index) =>
    styles.getPropertyValue(`--broker-line-${index + 1}`).trim(),
  )
  const dates = data.prices.map((point) => point.date)
  const candles = data.prices.map((point) => {
    if (
      point.open === null ||
      point.low === null ||
      point.high === null ||
      point.volume <= 0 ||
      point.open <= 0 ||
      point.close <= 0 ||
      point.low <= 0 ||
      point.low > Math.min(point.open, point.close) ||
      point.high < Math.max(point.open, point.close)
    )
      return [null, null, null, null]
    return [point.open, point.close, point.low, point.high]
  })
  const shareValues = data.broker_series.flatMap((broker) =>
    broker.points.map((point) => point.cumulative_net_shares).filter((value) => value !== null),
  )
  const shareMax = Math.max(1, ...shareValues.map((value) => Math.abs(value))) * 1.15
  const option: ChartOption = {
    ...chartBase,
    color: colors,
    grid: { top: 52, right: 80, bottom: 52, left: 78, containLabel: false },
    tooltip: { ...chartBase.tooltip, trigger: 'axis', axisPointer: { type: 'cross' } },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLabel: {
        color: chartColors.text,
        fontSize: 12,
        hideOverlap: true,
        formatter: (value) => date(value).replace(/ \d{4}$/, ''),
      },
      axisLine: { lineStyle: { color: chartColors.grid } },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Price · IDR',
        position: 'left',
        scale: true,
        nameTextStyle: { color: chartColors.text, align: 'left' },
        axisLabel: { color: chartColors.text, formatter: (value: number) => number(value, 0) },
        splitLine: { lineStyle: { color: chartColors.grid } },
      },
      {
        type: 'value',
        name: 'Net shares',
        position: 'right',
        min: -shareMax,
        max: shareMax,
        nameTextStyle: { color: chartColors.text, align: 'right' },
        axisLabel: { color: chartColors.text, formatter: (value: number) => signed(value) },
        splitLine: { show: false },
        axisLine: { show: true, lineStyle: { color: chartColors.grid } },
      },
    ],
    series: [
      {
        type: 'candlestick',
        name: 'Share price · IDR',
        yAxisIndex: 0,
        data: candles,
        barMaxWidth: 20,
        itemStyle: {
          color: chartColors.teal,
          color0: chartColors.red,
          borderColor: chartColors.teal,
          borderColor0: chartColors.red,
          opacity: 0.83,
        },
        z: 2,
      },
      ...data.broker_series.map((series, index) => ({
        type: 'line' as const,
        name: `${series.broker_code} · ${series.side}`,
        yAxisIndex: 1,
        data: series.points.map((point) => point.cumulative_net_shares),
        connectNulls: false,
        showSymbol: false,
        smooth: false,
        lineStyle: {
          color: colors[index],
          type: series.side === 'seller' ? ('dashed' as const) : ('solid' as const),
          width: focused === series.broker_code ? 3.5 : 1.9,
          opacity: focused && focused !== series.broker_code ? 0.16 : 0.9,
        },
        itemStyle: { color: colors[index] },
        z: focused === series.broker_code ? 5 : 3,
      })),
    ],
  }
  const selectedDay = data.days.find((day) => day.date === selectedDate)
  const maxRank = Math.max(
    1,
    ...[...data.top_buyers, ...data.top_sellers].map((row) => Math.abs(row.net_idr)),
  )
  const missingBrokerDates = data.days.filter((day) => !day.available).map((day) => day.date)
  const coveredBrokerDays = dates.length - missingBrokerDates.length
  const shortDates = (values: string[]) =>
    `${values.slice(0, 5).map(date).join(', ')}${values.length > 5 ? `, +${values.length - 5} more` : ''}`
  return (
    <div className="space-y-5">
      <DataStatus data={data} />
      <section className="min-w-0 rounded-2xl border border-line bg-surface p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl">Price × cumulative broker flow</h2>
            <p className="mt-2 text-sm text-muted">
              Candlesticks use the left price axis. Broker lines use the right cumulative net shares
              axis. Top five brokers are ranked by period net IDR. Solid lines are net buyers;
              dashed lines are net sellers. Each broker has its own color.
            </p>
          </div>
          <label className="flex items-center gap-3 text-sm text-muted">
            Inspect day
            <select
              aria-label="Inspect trading day"
              className="min-h-11 rounded-xl border border-control bg-surface px-3 text-sm text-ink"
              value=""
              onChange={(event) => setSelectedDate(event.target.value)}
            >
              <option value="">Choose a date</option>
              {data.days.map((day) => (
                <option key={day.date} value={day.date}>
                  {date(day.date)}
                </option>
              ))}
            </select>
          </label>
        </div>
        {dates.length ? (
          <>
            <Chart
              option={option}
              label={`${data.symbol} price candlesticks and cumulative net shares for ${data.broker_series.length} period-ranked brokers, ${date(data.effective_start)} to ${date(data.effective_end)}. Click a candle or line to inspect a day.`}
              height="clamp(440px, 62vh, 720px)"
              onItemClick={(index) => setSelectedDate(dates[index] ?? null)}
            />
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-2 text-sm">
              {data.broker_series.map((series, index) => (
                <button
                  key={`${series.side}-${series.broker_code}`}
                  type="button"
                  aria-pressed={focused === series.broker_code}
                  className={`inline-flex min-h-8 items-center gap-2 rounded-md px-1 text-ink hover:text-accent focus-visible:outline-2 focus-visible:outline-accent ${focused && focused !== series.broker_code ? 'opacity-40' : ''}`}
                  onClick={() =>
                    setFocused(focused === series.broker_code ? null : series.broker_code)
                  }
                >
                  <span
                    aria-hidden="true"
                    className={`w-5 border-t-[3px] ${series.side === 'seller' ? 'border-dashed' : ''}`}
                    style={{ borderColor: colors[index] }}
                  />
                  {series.broker_code} <span className="sr-only">{series.side}</span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-sm text-muted">
              {date(data.effective_start)} – {date(data.effective_end)} · {dates.length} traded
              price sessions. Select a date or click the chart for daily broker quantities.
            </p>
            {data.excluded_price_dates.length > 0 && (
              <p className="mt-3 rounded-lg border border-warning-line bg-warning px-4 py-3 text-sm text-ink">
                Price records without a valid candle or positive volume were excluded on{' '}
                {shortDates(data.excluded_price_dates)}. Broker lines only cover plotted price
                sessions.
              </p>
            )}
            {coveredBrokerDays < dates.length && (
              <p className="mt-3 rounded-lg border border-warning-line bg-warning px-4 py-3 text-sm text-ink">
                Broker activity covers {coveredBrokerDays} of {dates.length} trading sessions. No
                broker summary was returned for {shortDates(missingBrokerDates)}. These dates appear
                as gaps; later cumulative values include only reported days.
              </p>
            )}
          </>
        ) : (
          <p className={ui.empty}>No dated price observations were returned for this period.</p>
        )}
      </section>
      <div className="grid gap-5 lg:grid-cols-2">
        <Ranking
          title="Top 5 net buyers"
          rows={data.top_buyers}
          maximum={maxRank}
          side="buyer"
          focused={focused}
          onFocus={setFocused}
        />
        <Ranking
          title="Top 5 net sellers"
          rows={data.top_sellers}
          maximum={maxRank}
          side="seller"
          focused={focused}
          onFocus={setFocused}
        />
      </div>
      <footer className="flex flex-wrap justify-between gap-3 border-t border-line pt-5 text-sm text-muted">
        <span>Source: SectorsAPI · latest {date(data.as_of)}</span>
        <span>Broker origin does not identify investor origin. For research only.</span>
      </footer>
      {selectedDay && (
        <DayDialog key={selectedDay.date} day={selectedDay} onClose={() => setSelectedDate(null)} />
      )}
    </div>
  )
}

export function BrokerFlowPage() {
  const { symbol: raw = '' } = useParams()
  const symbol = normalizeSymbol(raw)
  const valid = validSymbol(symbol)
  const [range, setRange] = useState<BrokerFlowRange>('5d')
  const query = useQuery({
    queryKey: ['broker-flow', symbol, range],
    queryFn: ({ signal }) => getBrokerFlow(symbol, range, signal),
    enabled: valid && raw === symbol,
  })
  useEffect(() => {
    document.title = `${symbol} · BrokerFlow | IntelFlow`
    return () => {
      document.title = 'IntelFlow · IDX research'
    }
  }, [symbol])
  if (valid && raw !== symbol) return <Navigate to={`/broker-flow/${symbol}`} replace />
  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="mb-2 text-sm font-medium text-muted">IDX · {symbol}</p>
          <h1>BrokerFlow</h1>
          <p className="mt-2 text-sm text-muted">
            Compare share price with the brokers leading accumulation and distribution.
          </p>
        </div>
        <div
          role="group"
          aria-label="BrokerFlow period"
          className="inline-flex gap-1 rounded-xl border border-line bg-canvas p-1"
        >
          {ranges.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={range === item.value}
              onClick={() => setRange(item.value)}
              className={`min-h-11 rounded-lg px-4 text-sm font-semibold ${range === item.value ? 'bg-period-active text-on-period-active' : 'bg-surface text-ink hover:bg-raised'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>
      {!valid && (
        <div className={ui.errorBox} role="alert">
          <h2>Invalid ticker format</h2>
          <p>Use exactly four letters. The .JK suffix is optional.</p>
        </div>
      )}
      {valid && query.isPending && <Loading text="Loading BrokerFlow…" />}
      {valid && query.isError && (
        <ErrorState error={query.error} retry={() => void query.refetch()} allowSearch={false} />
      )}
      {query.data && <BrokerFlowContent key={`${symbol}-${range}`} data={query.data} />}
    </div>
  )
}
