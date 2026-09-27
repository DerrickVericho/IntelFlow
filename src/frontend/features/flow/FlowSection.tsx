import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { Research, Window } from '../../types/research'
import { getFlow } from '../../api/client'
import { Chart, useChartTheme, type ChartOption } from '../../components/Chart'
import { DataStatus, ErrorState, Loading } from '../../components/States'
import { ReportingPeriod } from '../../components/Sources'
import { compact, date, idr, metricValue, number } from '../../utils/format'
import { ui } from '../../components/ui'
import { investorBrokerView, type InvestorFilter } from './investor'

export function FlowSection({ data, window, setWindow }: { data: Research; window: Window; setWindow: (window: Window) => void }) {
  const [investor, setInvestor] = useState<InvestorFilter>('all')
  const { chartBase, chartColors } = useChartTheme()
  const axis = { axisLabel: { color: chartColors.text, fontSize: 12 }, axisLine: { lineStyle: { color: chartColors.grid } } }
  const query = useQuery({ queryKey: ['flow', data.symbol, window], queryFn: ({ signal }) => getFlow(data.symbol, window, signal), enabled: window !== '20d' })
  const response = window === '20d' ? data : query.data
  const flow = response?.flow
  const brokers = flow?.broker_summary.brokers ?? []
  const brokerView = investorBrokerView(brokers, investor)
  const pairs = brokerView.pairs
  const investorLabel = investor === 'all' ? 'All investors' : investor === 'foreign' ? 'Foreign investors' : 'Local investors'
  const foreign = flow?.foreign_flow
  const liquidity = flow?.liquidity
  const brokerOption: ChartOption = { ...chartBase,
    grid: { top: 40, left: 68, right: 24, bottom: 64 },
    tooltip: { ...chartBase.tooltip, trigger: 'item', formatter: '{b}\n{a}: {c} IDR' },
    xAxis: { type: 'category', data: pairs.map(pair => `#${pair.rank}`), ...axis, axisLine: { onZero: false, lineStyle: { color: chartColors.grid } }, axisLabel: { interval: 0, margin: 30, color: chartColors.text } },
    yAxis: { type: 'value', ...axis, axisLabel: { formatter: (value: number) => compact(value), color: chartColors.text }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: (['buyer', 'seller'] as const).map(side => ({ type: 'bar', name: side === 'buyer' ? 'Net buy' : 'Net sell', stack: 'rank', stackStrategy: 'samesign', barMaxWidth: 34,
      itemStyle: { color: side === 'buyer' ? chartColors.teal : chartColors.red },
      label: { show: true, position: side === 'buyer' ? 'top' : 'bottom', formatter: '{b}', color: chartColors.text, fontSize: 13 },
      data: pairs.map(pair => { const broker = pair[side]; return broker ? { name: broker.broker_code, value: broker.net_idr } : { value: null } }),
    })),
  }
  const foreignOption: ChartOption = { ...chartBase,
    xAxis: { type: 'category', data: foreign?.series.map(p => p.date), ...axis },
    yAxis: { type: 'value', ...axis, axisLabel: { formatter: (value: number) => compact(value), color: chartColors.text }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: [{ type: 'line', name: 'Cumulative net foreign · IDR', showSymbol: true, symbolSize: 4, data: foreign?.series.map(p => p.cumulative_net_inflow_idr), lineStyle: { color: chartColors.teal, width: 2 }, itemStyle: { color: chartColors.teal }, areaStyle: { color: chartColors.teal, opacity: 0.07 }, connectNulls: false }],
  }
  const volumeOption: ChartOption = { ...chartBase,
    legend: { top: 0, textStyle: { color: chartColors.text }, itemWidth: 12, itemHeight: 8 },
    xAxis: { type: 'category', data: liquidity?.series.map(p => p.date), ...axis },
    yAxis: { type: 'value', ...axis, axisLabel: { formatter: (value: number) => compact(value), color: chartColors.text }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: [{ type: 'bar', name: 'Volume · shares', data: liquidity?.series.map(p => p.volume_shares), itemStyle: { color: chartColors.blue, opacity: 0.65 }, barMaxWidth: 14 }, { type: 'line', name: 'Preceding 20-observation mean', showSymbol: false, data: liquidity?.series.map(p => p.average_volume_shares), lineStyle: { color: chartColors.teal, type: 'dashed', width: 2 }, itemStyle: { color: chartColors.teal }, connectNulls: false }],
  }
  return <section className={ui.panel} aria-labelledby="flow-title">
    <div className={ui.sectionHeading}><div><h2 id="flow-title">Flow activity</h2></div>
      <div className="inline-flex gap-1 rounded-xl border border-line bg-canvas p-1" role="group" aria-label="Flow evidence window">{(['1d', '5d', '20d'] as Window[]).map(item => {
        const active = window === item
        return <button type="button" className={`min-h-10 rounded-lg border px-4 text-sm font-semibold ${active ? 'border-period-active bg-period-active text-on-period-active' : 'border-control bg-surface text-ink hover:bg-raised'}`} key={item} aria-pressed={active} onClick={() => setWindow(item)}>{item.toUpperCase()}</button>
      })}</div>
    </div>
    {window !== '20d' && query.isPending && <Loading text={`Loading ${window.toUpperCase()} flow evidence…`} />}
    {window !== '20d' && query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {response && flow && foreign && liquidity && <>
      {window !== '20d' && <DataStatus data={response} />}
      <div className="mb-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted"><span>{date(flow.effective_start)} – {date(flow.effective_end)}</span><span>{flow.trading_days} observed trading {flow.trading_days === 1 ? 'day' : 'days'}</span></div>
      {flow.incomplete_history && <p className={ui.notice}>Incomplete history · Fewer observations are available than requested.</p>}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-6"><h3>Broker accumulation / distribution</h3><span className={ui.muted}>IDR · ranked net participants</span></div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex flex-wrap gap-1 rounded-xl border border-line bg-canvas p-1" role="group" aria-label="Broker investor filter">
          {(['all', 'foreign', 'local'] as InvestorFilter[]).map(item => {
            const active = investor === item
            return <button type="button" key={item} aria-pressed={active} onClick={() => setInvestor(item)} className={`min-h-10 rounded-lg border px-4 text-sm font-semibold ${active ? 'border-period-active bg-period-active text-on-period-active' : 'border-control bg-surface text-ink hover:bg-raised'}`}>{item === 'all' ? 'All investors' : item === 'foreign' ? 'Foreign' : 'Local'}</button>
          })}
        </div>
        <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm [&_span:first-child]:text-positive [&_span:last-child]:text-negative"><span>Net buyers above zero</span><span>Net sellers below zero</span></div>
      </div>
      {investor === 'all'
        ? <p className="mt-3 text-sm text-muted">Provider-ranked broker flow across all investors. Broker code does not indicate investor origin.</p>
        : <p className="mt-3 text-sm text-muted">{investorLabel} net among {brokerView.covered} of {brokerView.total} brokers in the overall-ranked list. {investor === 'local' ? 'Local net = total net − foreign net. ' : ''}Showing up to 10 per side, re-ranked within this list, not the whole market. Broker code does not indicate investor origin.</p>}
      {investor !== 'all' && brokerView.covered < brokerView.total && <p className="mt-2 text-sm text-muted">{brokerView.total - brokerView.covered} brokers without foreign net data are omitted.</p>}
      {pairs.length ? <><p className="my-3 text-sm text-muted xl:hidden">Scroll horizontally to see all ranks.</p><div className="overflow-x-auto rounded-xl focus-visible:outline-2 focus-visible:outline-accent" tabIndex={0} role="region" aria-label="Broker comparison chart"><div className="min-w-[580px]"><Chart option={brokerOption} label={`${investorLabel} net among ${brokers.length} brokers paired by rank. Net buyers above zero and net sellers below zero, in IDR. Exact values follow in the broker table.`} height={360} /></div></div></> : <p className={ui.empty}>{brokers.length ? `No non-zero ${investorLabel.toLowerCase()} net is available among these brokers.` : 'No broker observations available for this window.'}</p>}
      <p className="mt-3 text-sm text-muted">Bars pair brokers by rank, not by transaction.</p>
      <section className="mt-6 min-w-0 space-y-3" aria-labelledby="broker-net-title"><h3 id="broker-net-title" className="text-base">Broker net activity · {investorLabel}</h3>
        {pairs.length ? <div className={`${ui.tableScroll} max-h-80`} tabIndex={0} role="region" aria-label="Broker net activity table"><table><caption>{investorLabel} net activity paired by rank. All amounts in IDR.</caption><thead><tr><th>Rank</th><th>Buyer</th><th className="text-right whitespace-nowrap tabular-nums">Net buy</th><th>Seller</th><th className="text-right whitespace-nowrap tabular-nums">Net sell</th></tr></thead><tbody>{pairs.map(pair => <tr key={pair.rank}><td>{pair.rank}</td><td><strong>{pair.buyer?.broker_code ?? '—'}</strong></td><td className="text-right whitespace-nowrap tabular-nums">{pair.buyer ? `+${number(pair.buyer.net_idr)}` : '—'}</td><td><strong>{pair.seller?.broker_code ?? '—'}</strong></td><td className="text-right whitespace-nowrap tabular-nums">{pair.seller ? number(pair.seller.net_idr) : '—'}</td></tr>)}</tbody></table></div> : <p className={ui.empty}>No broker net activity is available for this investor view.</p>}
      </section>
      <section className="my-6" aria-label="Overall ranked broker balance"><h3 className="text-base">Overall ranked broker balance · all investors</h3><p className="mt-1 mb-3 text-sm text-muted">These balances describe ranked participants, not the whole exchange.</p><div className="grid gap-4 rounded-xl bg-canvas p-5 sm:grid-cols-3 [&_strong]:text-xl [&_strong]:font-semibold [&_strong]:tabular-nums [&_p]:mt-2 [&_p]:text-sm [&_p]:text-muted">{flow.broker_summary.breadth.map(b => <div key={b.top_n}><span className={ui.eyebrow}>Top {b.top_n} balance</span><strong>{idr(b.balance_idr)}</strong><p>Buyer {idr(b.buyer_net_idr)} · Seller {idr(b.seller_net_idr)}</p><p>{b.buyer_count}/{b.top_n} buyers · {b.seller_count}/{b.top_n} sellers · balance ratio {number(b.balance_ratio)}</p></div>)}</div></section>
      <div className="mt-8 grid gap-8 border-t border-line pt-8 xl:grid-cols-2">
        <article className="min-w-0"><h3>Foreign investor flow</h3><div className="mt-5 mb-1 text-3xl font-semibold tracking-tight tabular-nums">{idr(foreign.net_inflow_idr)}</div><p className={ui.muted}>Net inflow · all markets · {flow.window.toUpperCase()}</p>
          <dl className="my-5 space-y-3 text-sm [&_div]:flex [&_div]:justify-between [&_div]:gap-4 [&_dt]:text-muted [&_dd]:text-right"><div><dt>Buy / sell</dt><dd>{idr(foreign.buy_idr)} / {idr(foreign.sell_idr)}</dd></div><div><dt>Average foreign share</dt><dd>{metricValue(foreign.average_foreign_share_percent, 'percent')}</dd></div><div><dt>Positive / negative days</dt><dd>{foreign.series.length ? `${foreign.positive_days} / ${foreign.negative_days}` : 'Unavailable'}</dd></div></dl>
          {foreign.series.length ? <Chart option={foreignOption} label={`Cumulative foreign net inflow in IDR. Window total ${idr(foreign.net_inflow_idr)}; ${foreign.positive_days} positive and ${foreign.negative_days} negative days.`} height={200} /> : <p className={ui.empty}>No foreign-flow timeline available.</p>}
        </article>
        <article className="min-w-0"><h3>Liquidity context</h3><div className="mt-5 mb-1 text-3xl font-semibold tracking-tight tabular-nums">{metricValue(liquidity.latest_vs_average_ratio, 'ratio')}</div><p className={ui.muted}>Latest volume vs. preceding {liquidity.baseline_window} observations</p>
          <dl className="my-5 space-y-3 text-sm [&_div]:flex [&_div]:justify-between [&_div]:gap-4 [&_dt]:text-muted [&_dd]:text-right"><div><dt>Latest volume</dt><dd>{compact(liquidity.latest_volume_shares)}{liquidity.latest_volume_shares !== null ? ' shares' : ''}</dd></div><div><dt>Baseline mean</dt><dd>{compact(liquidity.average_volume_shares)}{liquidity.average_volume_shares !== null ? ' shares' : ''}</dd></div><div><dt>Baseline</dt><dd>Excludes the plotted day</dd></div></dl>
          {liquidity.series.length ? <Chart option={volumeOption} label={`Daily volume in shares and preceding ${liquidity.baseline_window}-observation mean. Latest volume ${compact(liquidity.latest_volume_shares)} shares. Missing baselines remain gaps.`} height={200} /> : <p className={ui.empty}>No volume timeline available.</p>}
        </article>
      </div>
      <section className="mt-6 min-w-0 space-y-3"><h3 className="text-base">Daily foreign flow</h3><div className={`${ui.tableScroll} max-h-80`} tabIndex={0} role="region" aria-label="Trading values"><table><caption>Foreign investor flow · IDR</caption><thead><tr><th>Date</th><th>Net inflow</th><th>Cumulative net</th><th>Foreign share</th></tr></thead><tbody>{foreign.series.map(p => <tr key={p.date}><td>{date(p.date)}</td><td>{number(p.net_inflow_idr)}</td><td>{number(p.cumulative_net_inflow_idr)}</td><td>{metricValue(p.foreign_share_percent, 'percent')}</td></tr>)}</tbody></table></div></section>
      <section className="mt-6 min-w-0 space-y-3"><h3 className="text-base">Daily volume</h3><div className={`${ui.tableScroll} max-h-80`} tabIndex={0} role="region" aria-label="Trading values"><table><caption>Volume in shares. The ratio uses the preceding average.</caption><thead><tr><th>Date</th><th>Volume</th><th>Volume / average</th></tr></thead><tbody>{liquidity.series.map(p => <tr key={p.date}><td>{date(p.date)}</td><td>{number(p.volume_shares)}</td><td>{metricValue(p.volume_ratio, 'ratio')}</td></tr>)}</tbody></table></div></section>
      {window !== '20d' && <div className="mt-5"><ReportingPeriod sources={response.sources} /></div>}
    </>}
  </section>
}
