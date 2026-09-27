import type { Research, Score } from '../../types/research'
import { number, date } from '../../utils/format'
import { componentInfo, componentName, researchSummary, scoreBand } from './interpretation'
import { StatusBadge } from './StatusBadge'

function Components({ score }: { score: Score }) {
  return <ul className="space-y-4">{score.components.map(component => {
    const band = scoreBand(component.value)
    return <li key={component.key} className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1.5">
      <div className="flex flex-wrap items-baseline gap-x-3"><span className="font-medium">{componentName(component.key)}</span><span className="text-sm text-muted">{number(component.weight)}% weight</span></div>
      <span className="whitespace-nowrap text-base font-semibold tabular-nums">{component.value === null ? 'N/A' : <>{number(component.value, 1)}<span className="text-sm font-normal text-muted"> / 100</span></>}</span>
      <div className="flex items-center gap-3"><div className="score-meter-track h-2 flex-1 overflow-hidden rounded-full" role={component.value === null ? "img" : "meter"} aria-label={`${componentName(component.key)} score`} aria-valuemin={component.value === null ? undefined : 0} aria-valuemax={component.value === null ? undefined : 100} aria-valuenow={component.value ?? undefined} aria-valuetext={component.value === null ? 'Unavailable' : `${number(component.value, 1)} out of 100, ${band}`}>
        {component.value !== null && <div className="score-meter-fill h-full min-w-[4px] rounded-full" style={{ width: `${component.value}%` }} />}
      </div></div><span className="text-right text-sm text-muted">{band}</span>
      <p className="col-span-2 text-sm text-muted">{componentInfo[component.key]?.help}</p>
      {component.reason && <p className="col-span-2 text-sm text-caution">{component.reason}</p>}
    </li>
  })}</ul>
}

export function Scores({ data }: { data: Research }) {
  const { scores } = data
  const summary = researchSummary(data)
  return <section aria-label="Research scores" className="space-y-4">
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]" data-testid="score-layout">
      <article aria-label="Overall Score" className="flex min-w-0 flex-col rounded-2xl border border-line bg-surface p-5 sm:p-7 xl:row-span-2">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl">Overall Score</h2><span className="text-sm text-muted">Combined</span></div>
        <div className="mt-5 flex flex-wrap items-center gap-5"><div className="text-[clamp(3.5rem,5vw,5rem)] font-semibold leading-none tracking-tight tabular-nums" data-testid="score-combined">{scores.combined.value === null ? 'N/A' : number(scores.combined.value)}{scores.combined.value !== null && <span className="ml-2 text-xl font-normal text-muted">/ 100</span>}</div><StatusBadge band={summary.band} /></div>
        <h3 className="mt-5 text-2xl leading-snug">Overall view: {summary.band}{summary.band === 'Neutral' ? ' / Watch' : ''}</h3>
        <p className="mt-2 text-base text-muted">{summary.meaning}</p><p className="mt-2 text-sm text-muted">Score direction: unavailable without historical snapshots.</p>
        {scores.combined.reason && <p className="mt-3 text-sm text-caution">{scores.combined.reason}</p>}
        <dl className="mt-5 space-y-4 border-t border-line pt-5">
          <div><dt className="flex flex-wrap items-center gap-3 text-sm text-muted">Data confidence <strong className="rounded-lg border border-control bg-raised px-2 py-1 text-base text-ink" data-testid="data-confidence">{summary.confidence.level}</strong></dt><dd className="mt-2 text-sm text-muted">{summary.confidence.reason} Coverage and freshness only, not forecast certainty.</dd></div>
          <div className="flex flex-wrap items-baseline justify-between gap-2"><dt className="text-muted">Fundamental</dt><dd className="font-semibold">{scoreBand(scores.fundamental.value)}{scores.fundamental.value !== null && ` (${number(scores.fundamental.value, 1)}/100)`}</dd></div>
          <div className="flex flex-wrap items-baseline justify-between gap-2"><dt className="text-muted">Flow</dt><dd className="font-semibold">{scoreBand(scores.flow.value)}{scores.flow.value !== null && ` (${number(scores.flow.value, 1)}/100)`}</dd></div>
          <div><dt className="text-sm font-medium text-muted">Key driver</dt><dd className="mt-1 text-base leading-relaxed">{summary.driver}</dd></div>
          <div className="rounded-xl border border-line bg-canvas p-4"><dt className="text-sm font-medium text-muted">Main risk</dt><dd className="mt-1 text-base leading-relaxed">{summary.risk}</dd></div>

        </dl>
        <p className="mt-5 text-sm text-muted">Combination: <strong>60%</strong> flow + <strong>40%</strong> fundamental.</p>
      </article>
      {(['flow', 'fundamental'] as const).map(key => {
        const score = scores[key]
        return <article key={key} aria-label={key === 'flow' ? 'Flow Score' : 'Fundamental Score'} className="min-w-0 rounded-2xl border border-line bg-surface p-5 sm:p-6">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl">{key === 'flow' ? 'Flow Score' : 'Fundamental Score'}</h2><p className="mt-1 text-sm text-muted">{key === 'flow' ? '20 trading observations' : `Financial year ${data.fundamentals.reporting_period ?? 'unavailable'}`}</p></div>
            <div className="text-right"><div className="mb-2 whitespace-nowrap text-3xl font-semibold tracking-tight tabular-nums" data-testid={`score-${key}`}>{score.value === null ? 'N/A' : number(score.value)}{score.value !== null && <span className="ml-1 text-sm font-normal text-muted">/ 100</span>}</div><StatusBadge band={scoreBand(score.value)} /></div>
          </div>
          {score.value === null && <p className="mb-2 text-base font-medium">Not calculated</p>}
          {score.reason && <p className="mb-4 text-sm text-caution">{score.reason}</p>}
          <Components score={score} />
        </article>
      })}
    </div>
    <p className="text-sm leading-relaxed text-muted">Score period: {date(scores.input_periods.flow_start ?? null)} – {date(scores.input_periods.flow_end ?? null)}. Bands: Weak &lt;50 · Neutral 50–59.99 · Positive 60–69.99 · Strong ≥70.</p>
  </section>
}
