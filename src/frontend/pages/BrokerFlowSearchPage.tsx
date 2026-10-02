import { SymbolSearch } from '../components/SymbolSearch'

export function BrokerFlowSearchPage() {
  return (
    <section className="max-w-3xl py-8 sm:py-14">
      <h1>Which stock's broker flow are you exploring?</h1>
      <p className="mt-5 mb-8 max-w-xl text-muted">
        Compare price movement with broker activity for one IDX ticker.
      </p>
      <SymbolSearch large destination="broker-flow" />
    </section>
  )
}
