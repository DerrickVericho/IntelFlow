import { useQuery } from '@tanstack/react-query'
import type { Research, Window } from '../../types/research'
import { getFlow } from '../../api/client'
import { Chart, chartBase, chartColors, type ChartOption } from '../../components/Chart'
import { DataStatus, ErrorState, Loading } from '../../components/States'
import { SourceRefs, SourceTable } from '../../components/Sources'
import { compact, date, idr, metricValue, number } from '../../utils/format'
import s from './flow.module.css'
import ui from '../../components/ui.module.css'

const axis = { axisLabel: { color: chartColors.text }, axisLine: { lineStyle: { color: chartColors.grid } } }
export function FlowSection({ data, window, setWindow }: { data: Research; window: Window; setWindow: (window: Window) => void }) {
  const query = useQuery({ queryKey: ['flow', data.symbol, window], queryFn: ({ signal }) => getFlow(data.symbol, window, signal), enabled: window !== '20d' })
  const response = window === '20d' ? data : query.data
  const flow = response?.flow
  const brokers = flow?.broker_summary.brokers ?? []
  const foreign = flow?.foreign_flow
  const liquidity = flow?.liquidity
  const brokerOption: ChartOption = { ...chartBase,
    xAxis: { type: 'category', data: brokers.map(b => b.broker_code), ...axis, axisLabel: { interval: 0, color: chartColors.text } },
    yAxis: { type: 'value', ...axis, axisLabel: { formatter: (value: number) => compact(value), color: chartColors.text }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: [{ type: 'bar', name: 'Net flow · IDR', barMaxWidth: 32, data: brokers.map(b => ({ value: b.net_idr, itemStyle: { color: b.net_idr >= 0 ? chartColors.teal : chartColors.red, borderRadius: b.net_idr >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3] } })) }],
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
    <div className={ui.sectionHeading}><div><span className={ui.eyebrow}>01 / CAPITAL PARTICIPATION</span><h2 id="flow-title">Flow evidence</h2><p className={ui.muted}>Observed broker activity, foreign flow, and share volume.</p></div>
      <div className={s.tabs} role="group" aria-label="Flow evidence window">{(['1d', '5d', '20d'] as Window[]).map(item => <button key={item} aria-pressed={window === item} onClick={() => setWindow(item)}>{item.toUpperCase()}</button>)}</div>
    </div>
    {window !== '20d' && query.isPending && <Loading text={`Loading ${window.toUpperCase()} flow evidence…`} />}
    {window !== '20d' && query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {response && flow && foreign && liquidity && <>
      {window !== '20d' && <DataStatus data={response} />}
      <div className={s.windowMeta}><span>{date(flow.effective_start)} – {date(flow.effective_end)}</span><span>{flow.trading_days} observed trading {flow.trading_days === 1 ? 'day' : 'days'}</span><span>Evidence window {flow.window.toUpperCase()}</span></div>
      {flow.incomplete_history && <p className={ui.notice}>Incomplete history · Fewer observations are available than requested.</p>}
      <div className={s.chartHeading}><h3>Net broker accumulation / distribution</h3><span className={ui.muted}>IDR · ranked net participants</span></div>
      <div className={s.legend}><span>＋ Net accumulation</span><span>− Net distribution</span></div>
      {brokers.length ? <Chart option={brokerOption} label={`${brokers.length} ranked brokers with signed net flow in IDR. Exact values follow in the broker table.`} height={270} /> : <p className={ui.empty}>No broker observations available for this window.</p>}
      <p className={s.chartNote}>Ranked broker slices do not represent net flow of the entire exchange. Broker origin does not identify investor origin.</p>
      <SourceRefs keys={['broker_top']} sources={response.sources} prefix={window === '20d' ? 'source' : 'flow-source'} />
      <details className={s.tableDetails}><summary>Inspect broker values ({brokers.length})</summary><div className={ui.tableScroll}><table><thead><tr><th>Broker</th><th>Side / rank</th><th>Buy (IDR)</th><th>Sell (IDR)</th><th>Net (IDR)</th><th>Foreign net (IDR)</th></tr></thead><tbody>{brokers.map(b => <tr key={`${b.side}-${b.broker_code}`}><td>{b.broker_code}</td><td>{b.side} / {b.rank}</td><td>{number(b.buy_idr)}</td><td>{number(b.sell_idr)}</td><td>{number(b.net_idr)}</td><td>{number(b.foreign_net_idr)}</td></tr>)}</tbody></table></div></details>
      <div className={s.breadth}>{flow.broker_summary.breadth.map(b => <div key={b.top_n}><span className={ui.eyebrow}>TOP {b.top_n} COMPARISON</span><strong>{idr(b.balance_idr)}</strong><p>Buyer {idr(b.buyer_net_idr)} · Seller {idr(b.seller_net_idr)}</p><p>{b.buyer_count}/{b.top_n} buyers · {b.seller_count}/{b.top_n} sellers · balance ratio {number(b.balance_ratio)}</p></div>)}</div>
      <div className={s.contextGrid}>
        <article className={s.context}><h3>Foreign investor flow</h3><div className={s.contextValue}>{idr(foreign.net_inflow_idr)}</div><p className={ui.muted}>Net inflow · all markets · {flow.window.toUpperCase()}</p>
          <dl className={s.stats}><div><dt>Buy / sell</dt><dd>{idr(foreign.buy_idr)} / {idr(foreign.sell_idr)}</dd></div><div><dt>Average foreign share</dt><dd>{metricValue(foreign.average_foreign_share_percent, 'percent')}</dd></div><div><dt>Positive / negative days</dt><dd>{foreign.series.length ? `${foreign.positive_days} / ${foreign.negative_days}` : 'Unavailable'}</dd></div></dl>
          {foreign.series.length ? <Chart option={foreignOption} label={`Cumulative foreign net inflow in IDR. Window total ${idr(foreign.net_inflow_idr)}; ${foreign.positive_days} positive and ${foreign.negative_days} negative days.`} height={200} /> : <p className={ui.empty}>No foreign-flow timeline available.</p>}
          <SourceRefs keys={['foreign_flow']} sources={response.sources} prefix={window === '20d' ? 'source' : 'flow-source'} />
        </article>
        <article className={s.context}><h3>Liquidity context</h3><div className={s.contextValue}>{metricValue(liquidity.latest_vs_average_ratio, 'ratio')}</div><p className={ui.muted}>Latest volume vs. preceding {liquidity.baseline_window} observations</p>
          <dl className={s.stats}><div><dt>Latest volume</dt><dd>{compact(liquidity.latest_volume_shares)}{liquidity.latest_volume_shares !== null ? ' shares' : ''}</dd></div><div><dt>Baseline mean</dt><dd>{compact(liquidity.average_volume_shares)}{liquidity.average_volume_shares !== null ? ' shares' : ''}</dd></div><div><dt>Baseline</dt><dd>Excludes the plotted day</dd></div></dl>
          {liquidity.series.length ? <Chart option={volumeOption} label={`Daily volume in shares and preceding ${liquidity.baseline_window}-observation mean. Latest volume ${compact(liquidity.latest_volume_shares)} shares. Missing baselines remain gaps.`} height={200} /> : <p className={ui.empty}>No volume timeline available.</p>}
          <SourceRefs keys={['daily']} sources={response.sources} prefix={window === '20d' ? 'source' : 'flow-source'} />
        </article>
      </div>
      <details className={s.tableDetails}><summary>Inspect daily foreign flow and liquidity</summary><div className={ui.tableScroll}><table><caption>Foreign investor flow · IDR</caption><thead><tr><th>Date</th><th>Net inflow</th><th>Cumulative net</th><th>Foreign share</th></tr></thead><tbody>{foreign.series.map(p => <tr key={p.date}><td>{date(p.date)}</td><td>{number(p.net_inflow_idr)}</td><td>{number(p.cumulative_net_inflow_idr)}</td><td>{metricValue(p.foreign_share_percent, 'percent')}</td></tr>)}</tbody></table><table><caption>Liquidity · share volume</caption><thead><tr><th>Date</th><th>Volume</th><th>Baseline mean</th><th>Volume ratio</th><th>Baseline observations</th></tr></thead><tbody>{liquidity.series.map(p => <tr key={p.date}><td>{date(p.date)}</td><td>{number(p.volume_shares)}</td><td>{number(p.average_volume_shares)}</td><td>{metricValue(p.volume_ratio, 'ratio')}</td><td>{p.baseline_observations}</td></tr>)}</tbody></table></div></details>
      {window !== '20d' && <div className={s.flowSources}><h3>Sources for this evidence window</h3><SourceTable sources={response.sources} prefix="flow-source" /></div>}
    </>}
  </section>
}
