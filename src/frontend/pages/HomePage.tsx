import { Link } from 'react-router'
import { SymbolSearch } from '../components/SymbolSearch'
import { Icon } from '../components/Icon'
import s from './home.module.css'
import ui from '../components/ui.module.css'

export function HomePage({ researchEntry = false }: { researchEntry?: boolean }) {
  return <>
    <section className={s.hero}>
      <div className={s.eyebrow}><span /> A CLEARER VIEW OF INDONESIAN EQUITIES</div>
      <h1>{researchEntry ? <>One symbol.<br /><em>The full context.</em></> : <>Start with the flow.<br /><em>See the bigger picture.</em></>}</h1>
      <p className={s.lede}>Follow broker activity and foreign capital. Put the movement in context with company fundamentals—all in one research workspace.</p>
      <div className={s.searchArea}><SymbolSearch large /><p className={s.searchHelp}>Enter an exact IDX ticker. Uppercase, lowercase, and .JK are supported.</p></div>
      <div className={s.exampleLink}><span>Contoh saham IDX</span><Link to="/stocks/BBCA/intel-score">Lihat IntelScore BBCA <Icon name="arrow" size={16} /></Link></div>
      <div className={s.heroDecoration} aria-hidden="true"><div /><div /><div /><div /><div /><div /><div /></div>
    </section>
    <section className={s.method} aria-labelledby="method-title">
      <div className={ui.sectionHeading}><div><span className={ui.eyebrow}>THE INTELFLOW APPROACH</span><h2 id="method-title">Three perspectives. One research view.</h2></div><span className={ui.muted}>Flow first. Fundamentals for context.</span></div>
      <div className={s.steps}>
        <article className={s.step}><span className={s.stepNumber}>01 / FOLLOW</span><span className={s.stepIcon}><Icon name="flow" size={26} /></span><h3>Flow Score</h3><p>Understand broker accumulation, foreign flow, and activity relative to the stock’s own volume history.</p><span className={s.stepTag}>Where is participation moving?</span></article>
        <article className={s.step}><span className={s.stepNumber}>02 / CONTEXTUALIZE</span><span className={s.stepIcon}><Icon name="document" size={26} /></span><h3>Fundamental Score</h3><p>Inspect growth, earnings, cash flow, and valuation to understand the business behind the activity.</p><span className={s.stepTag}>What does the business show?</span></article>
        <article className={s.step}><span className={s.stepNumber}>03 / CONNECT</span><span className={s.stepIcon}><Icon name="layers" size={26} /></span><h3>Combined Score</h3><p>Bring both perspectives together, with separate scores and a transparent, dated evidence trail.</p><span className={s.stepTag}>How do the perspectives align?</span></article>
      </div>
    </section>
    <div className={s.principles}><div><span>01</span><strong>Evidence you can inspect</strong><p>Source periods, missing inputs, and score components stay visible.</p></div><div><span>02</span><strong>Your research. Your judgment.</strong><p>Draft research scores provide context, not trading instructions.</p></div></div>
  </>
}
