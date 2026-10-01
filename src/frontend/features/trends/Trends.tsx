import { useQuery } from '@tanstack/react-query'
import type { PriceResponse, Research } from '../../types/research'
import { getPriceHistory } from '../../api/client'
import { Chart, useChartTheme, type ChartOption } from '../../components/Chart'
import { date, number } from '../../utils/format'
import { ui } from '../../components/ui'

function EmptyTrend({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex min-h-40 flex-col justify-center rounded-xl border border-dashed border-control bg-canvas p-5">
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm text-muted">{message}</p>
    </div>
  )
}

function candle(point: PriceResponse['series'][number]): number[] | null {
  const { open, close, low, high } = point
  if (
    open === null ||
    low === null ||
    high === null ||
    open <= 0 ||
    close <= 0 ||
    low > Math.min(open, close) ||
    high < Math.max(open, close)
  )
    return null
  return [open, close, low, high]
}

function PriceChart({ price }: { price: PriceResponse }) {
  const { chartBase, chartColors } = useChartTheme()
  const dates = price.series.map((point) => point.date)
  const candles = price.series.map(candle)
  const option: ChartOption = {
    ...chartBase,
    grid: { top: 22, right: 24, bottom: 48, left: 69 },
    tooltip: {
      ...chartBase.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      valueFormatter: (value) =>
        Array.isArray(value)
          ? `O ${number(Number(value[0]), 0)} · C ${number(Number(value[1]), 0)} · L ${number(Number(value[2]), 0)} · H ${number(Number(value[3]), 0)} IDR`
          : `${number(Number(value), 0)} IDR`,
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: true,
      axisLabel: {
        color: chartColors.text,
        fontSize: 12,
        formatter: (value) => date(value).replace(/ \d{4}$/, ''),
      },
      axisLine: { lineStyle: { color: chartColors.grid } },
    },
    yAxis: {
      type: 'value',
      name: 'Price · IDR',
      nameTextStyle: { color: chartColors.text },
      scale: true,
      axisLabel: { color: chartColors.text, formatter: (value: number) => number(value, 0) },
      splitLine: { lineStyle: { color: chartColors.grid } },
    },
    series: [
      {
        type: 'candlestick',
        name: 'Share price',
        data: candles.map((value) => value ?? [null, null, null, null]),
        barMaxWidth: 16,
        itemStyle: {
          color: chartColors.teal,
          color0: chartColors.red,
          borderColor: chartColors.teal,
          borderColor0: chartColors.red,
        },
      },
    ],
  }
  const validCandles = candles.filter((value) => value !== null).length
  return (
    <>
      <div className="mb-3 flex flex-wrap justify-between gap-2 text-sm text-muted">
        <span>First close: {number(price.series[0]?.close ?? null, 0)} IDR</span>
        <span>Last close: {number(price.series.at(-1)?.close ?? null, 0)} IDR</span>
      </div>
      {validCandles ? (
        <div
          className="overflow-x-auto rounded-xl focus-visible:outline-2 focus-visible:outline-accent"
          tabIndex={0}
          role="region"
          aria-label="Three-month share price chart"
        >
          <div className="min-w-[640px]">
            <Chart
              option={option}
              label={`Three-month share price candlesticks, ${date(price.series[0]?.date ?? null)} to ${date(price.series.at(-1)?.date ?? null)}. Prices are in IDR. Missing OHLC observations remain gaps.`}
              height={390}
            />
          </div>
        </div>
      ) : (
        <EmptyTrend
          title="OHLC price data unavailable"
          message="Dated closes are available, but open, high, or low values are missing, so candlesticks cannot be shown."
        />
      )}
      <p className="mt-3 text-sm text-muted">
        {date(price.series[0].date)} – {date(price.series.at(-1)!.date)} · {validCandles} of{' '}
        {price.series.length} OHLC observations.
        {price.incomplete_history || price.status === 'partial' ? ' Partial price coverage.' : ''}
        {price.status === 'stale' || price.sources.some((source) => source.is_stale)
          ? ' Price update needed.'
          : ''}
      </p>
    </>
  )
}

export function Trends({ data }: { data: Research }) {
  const priceQuery = useQuery({
    queryKey: ['price-history', data.symbol, '3m'],
    queryFn: ({ signal }) => getPriceHistory(data.symbol, '3m', signal),
  })
  const prices = priceQuery.data?.series ?? []
  return (
    <section className={ui.panel} aria-labelledby="trends-title">
      <div>
        <h2 id="trends-title">Change over time</h2>
        <p className="mt-2 text-sm text-muted">
          Three-month share-price history, with actual coverage dates.
        </p>
      </div>
      <article aria-label="Share price trend" className="mt-6 min-w-0">
        <h3 className="mb-4 text-lg">
          Share price · 3M <span className="text-sm font-normal text-muted">IDR</span>
        </h3>
        {priceQuery.isPending ? (
          <p className="min-h-40 py-10 text-sm text-muted" role="status">
            Loading price history…
          </p>
        ) : priceQuery.isError ? (
          <EmptyTrend
            title="Price history unavailable"
            message="The three-month history could not be loaded. Other research remains available."
          />
        ) : prices.length < 2 ? (
          <EmptyTrend
            title="Not enough price observations"
            message="At least two dated prices are needed to display a trend."
          />
        ) : (
          <PriceChart price={priceQuery.data} />
        )}
      </article>
    </section>
  )
}
