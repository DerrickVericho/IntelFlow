import { Navigate, useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getResearch } from '../api/client'
import { DataStatus, ErrorState, Loading } from '../components/States'
import { ResearchFooter } from '../components/Sources'
import { Scores } from '../features/scores/Scores'
import { FlowSection } from '../features/flow/FlowSection'
import { Fundamentals } from '../features/fundamentals/Fundamentals'
import { compact, date, metricValue, number, normalizeSymbol, validSymbol } from '../utils/format'
import type { Window } from '../types/research'
import { ui } from '../components/ui'
import { keyInsights } from '../features/scores/interpretation'
import { Trends } from '../features/trends/Trends'

export function IntelScorePage() {
  const { symbol: raw = '' } = useParams()
  const symbol = normalizeSymbol(raw)
  const valid = validSymbol(symbol)
  const [params, setParams] = useSearchParams()
  const requestedWindow = params.get('window')
  const validWindow = requestedWindow === null || ['1d', '5d', '20d'].includes(requestedWindow)
  const window: Window = validWindow && requestedWindow ? (requestedWindow as Window) : '20d'
  const query = useQuery({
    queryKey: ['research', symbol],
    queryFn: ({ signal }) => getResearch(symbol, signal),
    enabled: valid && raw === symbol,
  })
  const data = query.data
  useEffect(() => {
    document.title = `${symbol} · IntelScore | IntelFlow`
    return () => {
      document.title = 'IntelFlow · IDX research'
    }
  }, [symbol])
  if (valid && raw !== symbol)
    return (
      <Navigate to={`/stocks/${symbol}/intel-score${params.size ? `?${params}` : ''}`} replace />
    )
  const change = data?.company.change_idr
  const changePercent = data?.company.change_percent
  const hasChange = typeof change === 'number' && typeof changePercent === 'number'
  const liquidity = data?.flow.liquidity
  return (
    <div className="space-y-6">
      {!valid ? (
        <div className={ui.errorBox} role="alert">
          <h1>Invalid ticker format</h1>
          <p>Use exactly four letters. The .JK suffix is optional.</p>
        </div>
      ) : (
        <>
          {query.isPending && (
            <>
              <header className="flex flex-wrap items-center justify-between gap-6">
                <h1>Researching {symbol}</h1>
              </header>
              <Loading />
            </>
          )}
          {query.isError && (
            <ErrorState
              error={query.error}
              retry={() => void query.refetch()}
              allowSearch={false}
            />
          )}
          {data && (
            <>
              <header
                aria-label="Company market summary"
                className="overflow-hidden rounded-2xl border border-line bg-surface"
              >
                <div className="grid items-center gap-5 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_auto]">
                  <div className="flex min-w-0 items-center gap-4">
                    <span className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-accent-soft text-base font-bold text-accent">
                      {symbol}
                    </span>
                    <div>
                      <div className="mb-1 flex flex-wrap items-center gap-2 text-sm text-muted">
                        <span>IDX · {symbol}</span>
                        <span>{data.company.sector ?? 'Sector unavailable'}</span>
                      </div>
                      <h1 className="text-xl tracking-tight sm:text-2xl">
                        {data.company.name ?? symbol}
                      </h1>
                      {data.company.sub_sector && (
                        <p className="mt-1 text-sm text-muted">{data.company.sub_sector}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 lg:max-w-sm lg:justify-end">
                    <div
                      className="text-4xl font-semibold tracking-tight tabular-nums"
                      data-testid="last-close"
                    >
                      {data.company.last_close_idr === null ? (
                        'Price unavailable'
                      ) : (
                        <>
                          <span className="mr-2 text-sm font-normal text-muted">IDR</span>
                          {number(data.company.last_close_idr)}
                        </>
                      )}
                    </div>
                    {hasChange ? (
                      <p
                        data-testid="price-change"
                        className={`pb-1 text-base font-semibold tabular-nums ${change > 0 ? 'text-positive' : change < 0 ? 'text-negative' : 'text-muted'}`}
                      >
                        {change > 0 ? 'Up' : change < 0 ? 'Down' : 'Unchanged'}{' '}
                        {change > 0 ? '+' : ''}
                        {number(change)} ({changePercent > 0 ? '+' : ''}
                        {number(changePercent)}%)
                      </p>
                    ) : (
                      <p className="text-sm text-muted">Change unavailable</p>
                    )}
                    <p className="w-full text-sm text-muted">
                      Close · {date(data.company.close_date ?? data.as_of)}
                      {hasChange ? ` · vs. ${date(data.company.previous_close_date)}` : ''}
                    </p>
                  </div>
                </div>
                <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-t border-line bg-canvas px-5 py-4 sm:grid-cols-4 sm:px-7 [&_dt]:text-sm [&_dt]:text-muted [&_dd]:mt-1 [&_dd]:text-lg [&_dd]:font-semibold [&_dd]:tabular-nums">
                  <div>
                    <dt>Volume · shares</dt>
                    <dd data-testid="header-volume">
                      {compact(liquidity?.latest_volume_shares ?? null)}
                    </dd>
                  </div>
                  <div>
                    <dt>Avg. volume · {liquidity?.baseline_window ?? 20} prior observations</dt>
                    <dd data-testid="header-average-volume">
                      {compact(liquidity?.average_volume_shares ?? null)}
                    </dd>
                  </div>
                  <div>
                    <dt>Volume / average</dt>
                    <dd>{metricValue(liquidity?.latest_vs_average_ratio ?? null, 'ratio')}</dd>
                  </div>
                  <div>
                    <dt>Previous close · IDR</dt>
                    <dd>{number(data.company.previous_close_idr ?? null)}</dd>
                  </div>
                </dl>
              </header>
              {query.isError && (
                <p className={ui.notice}>
                  Showing the last successful response. Refresh failed; the displayed evidence has
                  not been updated.
                </p>
              )}
              <DataStatus data={data} />
              <Scores data={data} />
              <section className={ui.panel} aria-labelledby="key-points">
                <h2 id="key-points" className="mb-5 text-xl">
                  Key points
                </h2>
                <ul className="grid gap-5 lg:grid-cols-2">
                  {keyInsights(data).map((point, i) => (
                    <li key={i} className="border-l-2 border-accent/40 pl-4">
                      <h3 className="text-sm font-medium text-muted">{point.category}</h3>
                      <p className="mt-1 text-base">{point.text}</p>
                    </li>
                  ))}
                </ul>
              </section>
              <Trends key={`trends-${symbol}`} data={data} />
              {!validWindow && (
                <p className={ui.notice} role="status">
                  Unsupported evidence window. Showing the default 20D; choose 1D, 5D, or 20D below.
                </p>
              )}
              <FlowSection
                key={symbol}
                data={data}
                window={window}
                setWindow={(next) => {
                  const updated = new URLSearchParams(params)
                  if (next === '20d') updated.delete('window')
                  else updated.set('window', next)
                  setParams(updated)
                }}
              />
              <Fundamentals data={data} />
              <ResearchFooter data={data} />
            </>
          )}
        </>
      )}
    </div>
  )
}
