import type { Envelope } from '../types/research'
import { ApiError } from '../api/client'
import s from './ui.module.css'

export function Loading({ text = 'Loading research and dated evidence…' }: { text?: string }) {
  return <div className={s.loading} role="status"><span className={s.spinner} />{text}<div className={s.skeleton} /><div className={s.skeleton} /></div>
}
export function ErrorState({ error, retry }: { error: Error; retry: () => void }) {
  const api = error instanceof ApiError ? error : null
  const title = api?.status === 404 ? 'No data found' : api?.status === 422 ? 'Invalid request' : 'Research temporarily unavailable'
  return <div className={s.errorBox} role="alert"><h2>{title}</h2><p>{error.message}</p>
    {api?.status === 404 && <p>No observations were returned. This does not confirm that the ticker is invalid.</p>}
    {api?.requestId && <p className={s.muted}>Request ID: <code>{api.requestId}</code></p>}
    {api?.status !== 404 && api?.status !== 422 && <button className={s.secondary} onClick={retry}>Try again</button>}
  </div>
}
export function DataStatus({ data }: { data: Envelope }) {
  const stale = data.status === 'stale' || data.sources.some(source => source.is_stale)
  return <div className={s.statusStack}>
    {data.status === 'partial' && <div className={s.notice} role="status"><strong>Partial data</strong> · Some inputs are unavailable. Available evidence is shown; missing values are never zero.</div>}
    {stale && <div className={s.notice} role="status"><strong>Stale data</strong> · One or more sources are marked stale by the backend. Check their observation dates below.</div>}
    {data.missing_inputs.length > 0 && <details className={s.missing}><summary>Missing inputs ({data.missing_inputs.length})</summary><ul>{data.missing_inputs.map((item, i) => <li key={`${item.key}-${i}`}><strong>{item.key}</strong>: {item.reason}</li>)}</ul></details>}
  </div>
}
