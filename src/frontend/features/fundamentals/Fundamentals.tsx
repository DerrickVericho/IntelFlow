import type { Metric, Research } from '../../types/research'
import { Chart, chartBase, chartColors, type ChartOption } from '../../components/Chart'
import { SourceRefs } from '../../components/Sources'
import { compact, metricValue, number } from '../../utils/format'
import s from './fundamentals.module.css'
import ui from '../../components/ui.module.css'

function AnnualChart({ metric }: { metric: Metric }) {
  const option: ChartOption = { ...chartBase, grid: { top: 12, left: 58, right: 12, bottom: 28 },
    xAxis: { type: 'category', data: metric.series.map(p => p.period), axisLabel: { color: chartColors.text }, axisLine: { lineStyle: { color: chartColors.grid } } },
    yAxis: { type: 'value', axisLabel: { color: chartColors.text, formatter: (value: number) => compact(value) }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: [{ type: 'line', name: `${metric.label} · ${metric.unit}`, data: metric.series.map(p => p.value), connectNulls: false, symbolSize: 5, lineStyle: { color: chartColors.blue, width: 2 }, itemStyle: { color: chartColors.blue } }],
  }
  return <Chart option={option} label={`${metric.label}, annual history in ${metric.unit}. Missing years remain gaps; exact values in the adjacent history table.`} height={130} />
}

export function Fundamentals({ data }: { data: Research }) {
  return <section className={ui.panel} aria-labelledby="fundamentals-title">
    <div className={ui.sectionHeading}><div><span className={ui.eyebrow}>02 / BUSINESS CONTEXT</span><h2 id="fundamentals-title">Fundamental support</h2><p className={ui.muted}>Annual financial history. Quarterly YoY snapshots are undated.</p></div><span className={ui.badge}>Financial period {data.fundamentals.reporting_period ?? 'unavailable'}</span></div>
    {data.fundamentals.groups.length === 0 && <p className={ui.empty}>No fundamental metrics available.</p>}
    <div className={s.groups}>{data.fundamentals.groups.map(group => {
      const featured = group.metrics.find(metric => metric.period_type === 'annual' && metric.series.some(p => p.value !== null))
      return <article key={group.key} className={s.group}><div className={s.groupHeading}><h3>{group.label}</h3><span>{group.score === null ? 'Not calculated' : `${number(group.score)} / 100`}</span></div>
        {featured && <><p className={s.featuredLabel}>{featured.label} · annual · {featured.unit.toUpperCase()}</p><AnnualChart metric={featured} /></>}
        <div className={s.metrics}>{group.metrics.map(metric => <details key={metric.key} className={s.metric}><summary><span>{metric.label}<small>{metric.period_type === 'quarterly_yoy_undated' ? 'Quarterly YoY · undated' : `Annual · ${metric.period ?? 'period unavailable'}`}</small></span><strong>{metric.availability === 'unavailable' ? 'Unavailable' : metricValue(metric.value, metric.unit)}</strong></summary>
          <div className={s.metricDetail}>{metric.reason && <p>{metric.reason}</p>}<p>Numeric direction: {metric.direction}. Direction alone does not imply improvement.</p>
            {metric.period_type === 'quarterly_yoy_undated' ? <p>No quarter label or history supplied. This snapshot is not used in scoring.</p> : metric.series.length ? <table><caption>{metric.label} · annual history</caption><thead><tr><th>Year</th><th>{metric.unit.toUpperCase()}</th></tr></thead><tbody>{metric.series.map(point => <tr key={point.period}><td>{point.period}</td><td>{metricValue(point.value, metric.unit)}</td></tr>)}</tbody></table> : <p>No annual history available.</p>}
            <SourceRefs keys={metric.source_keys} sources={data.sources} />
          </div>
        </details>)}</div>
      </article>
    })}</div>
    <p className={s.note}>Negative valuation ratios remain visible as evidence; they do not imply a low valuation. Expand a metric to inspect its period, availability, and source.</p>
  </section>
}
