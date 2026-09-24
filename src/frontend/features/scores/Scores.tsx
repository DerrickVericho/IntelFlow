import type { Research } from '../../types/research'
import { number, label, date, timestamp } from '../../utils/format'
import { Icon } from '../../components/Icon'
import { SourceRefs } from '../../components/Sources'
import s from './scores.module.css'
import ui from '../../components/ui.module.css'

const definitions = [
  { key: 'flow', name: 'Flow Score', description: 'Broker, foreign flow & liquidity', icon: 'flow' },
  { key: 'fundamental', name: 'Fundamental Score', description: 'Growth, earnings, cash flow & valuation', icon: 'document' },
  { key: 'combined', name: 'Combined Score', description: 'Flow-first synthesis', icon: 'layers' },
] as const

export function Scores({ data }: { data: Research }) {
  const { scores, sources } = data
  return <section aria-label="Research scores">
    <div className={s.cards}>{definitions.map(definition => {
      const score = scores[definition.key]
      return <article key={definition.key} className={`${s.card} ${s[definition.key]}`} aria-label={definition.name}>
        <div className={s.cardHeading}><h2>{definition.name}</h2><span className={s.icon}><Icon name={definition.icon} /></span></div>
        <p className={s.description}>{definition.description}</p>
        <div className={s.value} data-testid={`score-${definition.key}`}>{score.value === null ? '—' : number(score.value)}<span>/ 100</span></div>
        <div className={s.track} aria-hidden="true"><span style={{ width: `${score.value ?? 0}%` }} /></div>
        <p className={s.caption}>{score.value === null ? 'Not calculated' : 'Backend-calculated · draft research score'}</p>
        {score.reason && <p className={s.reason}>{score.reason}</p>}
        <details className={s.breakdown}><summary>Score breakdown <span>↓</span></summary><div className={s.components}>{score.components.map(component => <div key={component.key} className={s.component}>
          <div><strong>{label(component.key)}</strong><span>{component.value === null ? 'Not calculated' : `${number(component.value)} / 100`}</span></div>
          <small>Base weight {number(component.weight)}%</small>{component.reason && <p>{component.reason}</p>}
          <SourceRefs keys={component.source_keys} sources={sources} />
        </div>)}{score.components.length === 0 && <p>No component details supplied.</p>}</div></details>
      </article>
    })}</div>
    <div className={s.researchState}><span className={ui.eyebrow}>RESEARCH STATE</span><strong>{label(scores.research_state)}</strong><span className={ui.badge}>{scores.calculation_version}</span></div>
    <div className={s.periods}>{Object.entries(scores.input_periods).map(([key, value]) => <span key={key}>{label(key)} <strong>{value ? date(value) : 'Unavailable'}</strong></span>)}<span>Calculated <strong>{timestamp(scores.calculated_at)}</strong></span></div>
    <p className={s.note}>Scores use the fixed 20-observation flow window. Evidence tabs do not change scores. Draft hypotheses, pending calibration.</p>
  </section>
}
