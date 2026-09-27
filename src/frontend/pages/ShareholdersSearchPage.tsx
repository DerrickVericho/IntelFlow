import { SymbolSearch } from '../components/SymbolSearch'

export function ShareholdersSearchPage() {
  return <section className="max-w-3xl py-8 sm:py-14">
    <h1>Which company's shareholders are you exploring?</h1>
    <p className="mt-5 mb-8 max-w-xl text-muted">Explore monthly shareholder categories and shareholder counts for one IDX ticker.</p>
    <SymbolSearch large destination="shareholders" />
  </section>
}
