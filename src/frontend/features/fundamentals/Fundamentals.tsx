import type { Metric, Research } from '../../types/research'
import { Chart, useChartTheme, type ChartOption } from '../../components/Chart'
import { compact, metricValue, number } from '../../utils/format'
import { ui } from '../../components/ui'

function AnnualChart({ metric }: { metric: Metric }) {
  const { chartBase, chartColors } = useChartTheme()
  const option: ChartOption = { ...chartBase, grid: { top: 12, left: 58, right: 12, bottom: 28 },
    xAxis: { type: 'category', data: metric.series.map(p => p.period), axisLabel: { color: chartColors.text }, axisLine: { lineStyle: { color: chartColors.grid } } },
    yAxis: { type: 'value', axisLabel: { color: chartColors.text, formatter: (value: number) => compact(value) }, splitLine: { lineStyle: { color: chartColors.grid } } },
    series: [{ type: 'line', name: `${metric.label} · ${metric.unit}`, data: metric.series.map(p => p.value), connectNulls: false, symbolSize: 5, lineStyle: { color: chartColors.blue, width: 2 }, itemStyle: { color: chartColors.blue } }],
  }
  return <Chart option={option} label={`${metric.label}, annual history in ${metric.unit}. Missing years remain gaps; exact values in the annual history table.`} height={130} />
}

export function Fundamentals({ data }: { data: Research }) {
  return <section className={ui.panel} aria-labelledby="fundamentals-title">
    <div className={ui.sectionHeading}><h2 id="fundamentals-title">Fundamentals</h2><span className={ui.badge}>Financial year {data.fundamentals.reporting_period ?? 'unavailable'}</span></div>
    {data.fundamentals.groups.length === 0 && <p className={ui.empty}>No fundamental metrics available.</p>}
    <div className="grid gap-8 2xl:grid-cols-2">{data.fundamentals.groups.map(group => {
      const featured = group.metrics.find(metric => metric.period_type === 'annual' && metric.series.some(p => p.value !== null))
      const years = [...new Set(group.metrics.flatMap(metric => metric.series.map(point => point.period)))].sort()
      return <article key={group.key} className="min-w-0 border-t border-line pt-6">
        <div className="mb-4 flex items-center justify-between gap-4"><h3>{group.label}</h3><span className="text-sm font-medium tabular-nums">{group.score === null ? 'N/A' : `${number(group.score)} / 100`}</span></div>
        {featured && <><p className="mb-2 text-sm text-muted">{featured.label} · annual · {featured.unit.toUpperCase()}</p><AnnualChart metric={featured} /></>}
        <div className={`${ui.tableScroll} mt-4`} tabIndex={0} role="region" aria-label={`${group.label} annual history`}>
          <table><caption className="sr-only">{group.label}: latest values and annual history</caption>
            <thead><tr><th scope="col">Metric</th><th scope="col" className="text-right">Latest</th>{years.map(year => <th key={year} scope="col" className="text-right">{year}</th>)}</tr></thead>
            <tbody>{group.metrics.map(metric => <tr key={metric.key}>
              <th scope="row" className="min-w-44 bg-transparent font-medium text-ink">{metric.label}<span className="mt-1 block text-sm font-normal text-muted">{metric.period_type === 'quarterly_yoy_undated' ? 'Quarterly YoY · undated' : `${metric.unit.toUpperCase()} · ${metric.period ?? 'Undated'}`}</span>{metric.reason && <span className="mt-1 block max-w-xs text-sm font-normal text-muted">{metric.reason}</span>}</th>
              <td className="whitespace-nowrap text-right font-semibold">{metric.availability === 'unavailable' ? 'Unavailable' : metricValue(metric.value, metric.unit)}</td>
              {years.map(year => <td key={year} className="whitespace-nowrap text-right text-muted">{metric.period_type === 'quarterly_yoy_undated' ? 'N/A' : metricValue(metric.series.find(point => point.period === year)?.value ?? null, metric.unit)}</td>)}
            </tr>)}</tbody>
          </table>
        </div>
      </article>
    })}</div>
    <p className="mt-6 text-sm text-muted">Undated quarterly snapshots are excluded from scoring. Negative valuation ratios do not imply a low valuation.</p>
  </section>
}
