import { Link } from 'react-router'
import { SymbolSearch } from '../components/SymbolSearch'
import { Icon } from '../components/Icon'

export function HomePage({ researchEntry = false }: { researchEntry?: boolean }) {
  if (researchEntry)
    return (
      <section className="max-w-3xl py-8 sm:py-14">
        <h1>Which company are you researching?</h1>
        <p className="mt-5 mb-8 max-w-xl text-muted">
          Broker activity, foreign flow, and company fundamentals for one IDX ticker.
        </p>
        <SymbolSearch large />
        <Link
          className="mt-5 inline-flex items-center gap-2 text-sm font-medium"
          to="/stocks/BBCA/intel-score"
        >
          Explore BBCA <Icon name="arrow" size={16} />
        </Link>
      </section>
    )
  return (
    <>
      <section className="pt-6 pb-12 sm:pt-10 sm:pb-16">
        <h1 className="max-w-5xl text-[clamp(2.1rem,4vw,3.75rem)] leading-[1.12] tracking-[-0.045em]">
          Start with the flow.
          <br />
          <span className="text-accent">Understand the business.</span>
        </h1>
        <p className="mt-6 max-w-xl text-base text-muted">
          Broker activity, foreign capital, and company fundamentals. A connected view of Indonesian
          equities.
        </p>
        <div className="mt-8">
          <SymbolSearch large />
        </div>
        <Link
          className="mt-5 inline-flex items-center gap-2 text-sm font-medium"
          to="/stocks/BBCA/intel-score"
        >
          Explore BBCA <Icon name="arrow" size={16} />
        </Link>
      </section>
      <section
        aria-label="Research perspectives"
        className="grid gap-6 border-t border-line py-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)] lg:gap-14"
      >
        <div>
          <h2 className="text-2xl">Capital meets context.</h2>
          <p className="mt-4 max-w-sm text-sm text-muted">
            Three independent scores connect market participation with reported business
            performance.
          </p>
        </div>
        <div className="divide-y divide-line">
          <article className="flex gap-4 pb-6">
            <span className="text-accent">
              <Icon name="flow" size={24} />
            </span>
            <div>
              <h3>Broker & foreign flow</h3>
              <p className="mt-2 text-sm text-muted">
                Ranked broker activity, foreign participation, and volume against recent history.
              </p>
            </div>
          </article>
          <article className="flex gap-4 py-6">
            <span className="text-accent">
              <Icon name="document" size={24} />
            </span>
            <div>
              <h3>Company fundamentals</h3>
              <p className="mt-2 text-sm text-muted">
                Growth, earnings, cash generation, and valuation with annual reporting periods.
              </p>
            </div>
          </article>
          <article className="flex gap-4 pt-6">
            <span className="text-accent">
              <Icon name="layers" size={24} />
            </span>
            <div>
              <h3>Overall Score</h3>
              <p className="mt-2 text-sm text-muted">
                Flow and fundamental support, with component values and weights always visible.
              </p>
            </div>
          </article>
        </div>
      </section>
    </>
  )
}
