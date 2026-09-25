import { Navigate, useParams, useSearchParams } from 'react-router'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getResearch } from '../api/client'
import { SymbolSearch } from '../components/SymbolSearch'
import { DataStatus, ErrorState, Loading } from '../components/States'
import { SourceRefs, SourceTable } from '../components/Sources'
import { Scores } from '../features/scores/Scores'
import { FlowSection } from '../features/flow/FlowSection'
import { Fundamentals } from '../features/fundamentals/Fundamentals'
import { date, idr, normalizeSymbol, validSymbol } from '../utils/format'
import type { Window } from '../types/research'
import s from './research.module.css'
import ui from '../components/ui.module.css'

export function IntelScorePage() {
  const { symbol: raw = '' } = useParams()
  const symbol = normalizeSymbol(raw)
  const valid = validSymbol(symbol)
  const [params, setParams] = useSearchParams()
  const requestedWindow = params.get('window')
  const validWindow = requestedWindow === null || ['1d', '5d', '20d'].includes(requestedWindow)
  const window: Window = validWindow && requestedWindow ? requestedWindow as Window : '20d'
  const query = useQuery({ queryKey: ['research', symbol], queryFn: ({ signal }) => getResearch(symbol, signal), enabled: valid && raw === symbol })
  const data = query.data
  useEffect(() => { document.title = `${symbol} · IntelScore | IntelFlow`; return () => { document.title = 'IntelFlow · IDX research' } }, [symbol])
  if (valid && raw !== symbol) return <Navigate to={`/stocks/${symbol}/intel-score${params.size ? `?${params}` : ''}`} replace />
  return <div className={s.page}>
    <header className={s.header}><div><span className={ui.eyebrow}>SYMBOL RESEARCH</span><h1>IntelScore <span className={s.symbol}>{symbol}</span></h1><p className={ui.muted}>Read the flow. Understand the fundamentals.</p></div><SymbolSearch key={symbol} initial={symbol} /></header>
    {!valid ? <div className={ui.errorBox} role="alert"><h2>Invalid ticker format</h2><p>Use exactly four letters. The .JK suffix is optional. No research request was sent.</p></div> : <>
      {query.isPending && <Loading />}
      {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
      {data && <>
        <div className={s.company}><div><h2>{data.company.name ?? 'Company identity unavailable'}</h2><p>{data.company.sector ?? 'Sector unavailable'}{data.company.sub_sector ? ` / ${data.company.sub_sector}` : ''} <span>·</span> Last close <strong>{idr(data.company.last_close_idr)}</strong></p></div><div className={s.freshness}><span className={data.status === 'complete' ? ui.badge : ui.badgeWarning}>{data.status === 'complete' ? 'Complete inputs' : `${data.status} inputs`}</span><span>Observed {date(data.as_of)}</span></div></div>
        {query.isError && <p className={ui.notice}>Showing the last successful response. Refresh failed; the displayed evidence has not been updated.</p>}
        <DataStatus data={data} />
        <Scores data={data} />
        <section className={s.keyPoints} aria-labelledby="key-points"><div className={ui.sectionHeading}><div><span className={ui.eyebrow}>THE RESEARCH BRIEF</span><h2 id="key-points">Key points</h2></div><span className={ui.muted}>Backend evidence · fixed 20-observation window</span></div><div className={s.pointGrid}>{data.key_points.map((point, i) => <article key={`${point.kind}-${i}`}><span className={point.kind === 'evidence' ? ui.badge : ui.badgeWarning}>{point.kind}</span><h3>{point.title}</h3><p>{point.text}</p><SourceRefs keys={point.source_keys} sources={data.sources} /></article>)}</div>{data.key_points.length === 0 && <p className={ui.muted}>No key points supplied for this symbol.</p>}</section>
        {!validWindow && <p className={ui.notice} role="status">Unsupported evidence window. Showing the default 20D; choose 1D, 5D, or 20D below.</p>}
        <FlowSection key={symbol} data={data} window={window} setWindow={next => { const updated = new URLSearchParams(params); if (next === '20d') updated.delete('window'); else updated.set('window', next); setParams(updated) }} />
        <Fundamentals data={data} />
        <section className={ui.panel} aria-labelledby="sources-title"><div className={ui.sectionHeading}><div><span className={ui.eyebrow}>03 / THE EVIDENCE TRAIL</span><h2 id="sources-title">Sources & data freshness</h2><p className={ui.muted}>Observation dates describe the data. Retrieval times describe when the backend fetched it.</p></div></div><SourceTable sources={data.sources} /></section>
      </>}
    </>}
  </div>
}
