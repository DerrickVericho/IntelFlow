import type { Source } from '../types/research'
import { date, label, timestamp } from '../utils/format'
import s from './ui.module.css'

export function SourceRefs({ keys, sources, prefix = 'source' }: { keys: string[]; sources: Source[]; prefix?: string }) {
  return <div className={s.refs}>{keys.map(key => {
    const source = sources.find(item => item.key === key)
    return source ? <a key={key} href={`#${prefix}-${key}`}>{label(key)} · {source.period ?? date(source.as_of)}{source.is_stale ? ' · Stale' : ''}</a> : <span key={key}>{label(key)} · unavailable</span>
  })}</div>
}
export function SourceTable({ sources, prefix = 'source' }: { sources: Source[]; prefix?: string }) {
  return <div className={s.tableScroll}><table><caption className={s.srOnly}>Source observation dates, periods, retrieval timestamps and freshness</caption><thead><tr><th>Source / provider</th><th>Observation / period</th><th>Effective window</th><th>Retrieved</th><th>Freshness</th></tr></thead><tbody>
    {sources.map(source => <tr key={source.key} id={`${prefix}-${source.key}`}><td><strong>{label(source.key)}</strong><small>{source.provider}</small></td><td>{date(source.as_of)}{source.period && <small>Period {source.period}</small>}</td><td>{source.effective_start || source.effective_end ? `${date(source.effective_start)} – ${date(source.effective_end)}` : 'Not supplied'}</td><td>{timestamp(source.fetched_at)}</td><td><span className={source.is_stale ? s.badgeWarning : s.badge}>{source.is_stale ? 'Stale' : 'Not flagged stale'}</span></td></tr>)}
  </tbody></table>{sources.length === 0 && <p className={s.muted}>No source metadata available.</p>}</div>
}
