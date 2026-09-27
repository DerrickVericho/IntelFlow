import type { Research, Source } from '../types/research'
import { date, label } from '../utils/format'

const names: Record<string, string> = {
  daily: 'Price & volume', broker_top: '20-day broker rankings', broker_top_5d: '5-day broker rankings', broker_foreign_top: 'Foreign investor broker rankings', broker_activity: 'Daily broker activity', foreign_flow: 'Foreign investor flow',
  company_overview: 'Company overview', company_financials: 'Financial statements', company_valuation: 'Valuation',
}
export const sourceLabel = (key: string) => names[key] ?? label(key)

export function ReportingPeriod({ sources }: { sources: Source[] }) {
  const latestByKey = new Map<string, Source>()
  for (const source of sources) {
    if (source.key === 'company_overview') continue
    const previous = latestByKey.get(source.key)
    if (!previous || (source.as_of ?? '') > (previous.as_of ?? '')) latestByKey.set(source.key, source)
  }
  return <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">{[...latestByKey.values()].map(source => <span key={source.key}>{sourceLabel(source.key)}: {source.period ?? date(source.as_of)}{source.is_stale ? ' · Update needed' : ''}</span>)}</div>
}

export function ResearchFooter({ data }: { data: Research }) {
  const years = [...new Set(data.fundamentals.groups.flatMap(group => group.metrics.flatMap(metric => metric.series.map(point => point.period))))].sort()
  return <section aria-label="Data attribution" className="flex flex-col gap-4 border-t border-line pt-6 text-sm">
    <div className="flex flex-wrap justify-between gap-3"><strong>Powered by SectorsAPI</strong><span className="text-muted">For research purposes only — not investment advice.</span></div>
    <p className="text-sm text-muted">Financial history: {years.length ? years.length === 1 ? years[0] : `${years[0]}–${years.at(-1)}` : 'unavailable'} · Latest report: {data.fundamentals.reporting_period ?? 'unavailable'}</p>
    <ReportingPeriod sources={data.sources} />
  </section>
}
