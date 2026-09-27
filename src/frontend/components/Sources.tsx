import type { Research, Source } from '../types/research'
import { date, label } from '../utils/format'

const names: Record<string, string> = {
  daily: 'Price & volume', broker_top: 'Broker rankings', foreign_flow: 'Foreign investor flow',
  company_overview: 'Company overview', company_financials: 'Financial statements', company_valuation: 'Valuation',
}
export const sourceLabel = (key: string) => names[key] ?? label(key)

export function ReportingPeriod({ sources }: { sources: Source[] }) {
  return <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted">{sources.filter(source => source.key !== 'company_overview').map(source => <span key={source.key}>{sourceLabel(source.key)}: {source.period ?? date(source.as_of)}{source.is_stale ? ' · Update needed' : ''}</span>)}</div>
}

export function ResearchFooter({ data }: { data: Research }) {
  const years = [...new Set(data.fundamentals.groups.flatMap(group => group.metrics.flatMap(metric => metric.series.map(point => point.period))))].sort()
  return <section aria-label="Data attribution" className="flex flex-col gap-4 border-t border-line pt-6 text-sm">
    <div className="flex flex-wrap justify-between gap-3"><strong>Powered by SectorsAPI</strong><span className="text-muted">For research purposes only — not investment advice.</span></div>
    <p className="text-sm text-muted">Financial history: {years.length ? years.length === 1 ? years[0] : `${years[0]}–${years.at(-1)}` : 'unavailable'} · Latest report: {data.fundamentals.reporting_period ?? 'unavailable'}</p>
    <ReportingPeriod sources={data.sources} />
  </section>
}
