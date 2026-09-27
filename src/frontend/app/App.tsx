import { Component, Suspense, lazy, useEffect, useRef, type ReactNode } from 'react'
import { NavLink, Outlet, Route, Routes, useLocation, useMatch } from 'react-router'
import { HomePage } from '../pages/HomePage'
import { Loading } from '../components/States'
import { Icon } from '../components/Icon'
import { SymbolSearch } from '../components/SymbolSearch'
import { ThemeControl } from '../components/ThemeControl'
import { ui } from '../components/ui'

const IntelScorePage = lazy(() => import('../pages/IntelScorePage').then(module => ({ default: module.IntelScorePage })))

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() { return this.state.failed ? <div className={ui.errorBox} role="alert"><h1>Unable to display this research</h1><p>The response could not be rendered. Reload the page to try again.</p><button className={ui.secondary} onClick={() => window.location.reload()}>Reload page</button></div> : this.props.children }
}

function Shell() {
  const match = useMatch('/stocks/:symbol/intel-score')
  const location = useLocation()
  const main = useRef<HTMLElement>(null)
  const previousPath = useRef(location.pathname)
  useEffect(() => {
    if (previousPath.current !== location.pathname) {
      main.current?.focus(); window.scrollTo(0, 0)
      previousPath.current = location.pathname
    }
  }, [location.pathname])
  const navClass = (active: boolean) => `flex min-h-11 items-center gap-2 rounded-xl px-3 py-2 md:gap-3 md:px-4 md:py-3 text-sm hover:no-underline ${active ? 'bg-accent-soft font-semibold text-accent' : 'text-muted hover:bg-raised hover:text-ink'}`
  return <div className="min-h-dvh md:flex">
    <a className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:rounded-xl focus:bg-accent focus:p-3 focus:text-on-accent" href="#main">Skip to content</a>
    <aside className="flex flex-row flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-4 md:flex-col md:items-stretch md:justify-start md:fixed md:inset-y-0 md:left-0 md:z-10 md:w-56 md:border-r md:border-b-0 md:py-8">
      <NavLink to="/" className="flex items-center gap-2 text-xl sm:text-2xl font-semibold tracking-tight text-ink hover:no-underline md:mb-12"><span className="flex size-10 items-center justify-center rounded-xl bg-accent text-on-accent"><Icon name="flow" size={25} /></span>IntelFlow</NavLink>
      <p className="mb-3 hidden px-4 text-xs font-medium text-muted md:block">Workspace</p>
      <nav className="flex gap-2 md:flex-col" aria-label="Main navigation">
        <NavLink to="/" end className={({ isActive }) => navClass(isActive)}><Icon name="home" />Home</NavLink>
        <NavLink to={match ? `/stocks/${match.params.symbol}/intel-score` : '/intel-score'} className={({ isActive }) => navClass(isActive || !!match)}><Icon name="chart" />IntelScore</NavLink>
      </nav>
      <div className="mt-auto hidden px-4 pt-8 text-xs text-muted md:block"><p>Indonesia Stock Exchange</p><p className="mt-2">Powered by SectorsAPI</p></div>
    </aside>
    <div className="flex min-w-0 flex-1 flex-col md:ml-56">
      <div className="flex min-h-18 flex-wrap items-center justify-between gap-4 border-b border-line px-5 py-3 text-sm text-muted sm:px-8"><span className={match ? "hidden xl:inline" : ""}>Workspace <span className="mx-3 text-control">/</span> <strong className="font-medium text-ink">{location.pathname === '/' ? 'Overview' : match?.params.symbol ?? 'Company research'}</strong></span><div className="flex w-full min-w-0 items-center gap-3 xl:w-auto">{match && <SymbolSearch key={match.params.symbol} initial={match.params.symbol} compact />}<ThemeControl /></div></div>
      <main ref={main} id="main" tabIndex={-1} className="mx-auto w-full max-w-[1480px] min-w-0 flex-1 px-4 py-6 sm:px-8 sm:py-8 lg:px-10">
        <Boundary key={location.pathname}><Suspense fallback={<Loading text="Opening research workspace…" />}><Outlet /></Suspense></Boundary>
      </main>
      {!match && <footer className="flex flex-wrap justify-between gap-3 border-t border-line px-5 py-6 text-xs text-muted sm:px-8"><span>Powered by SectorsAPI</span><span>Not Financial Advice</span></footer>}
    </div>
  </div>
}

export function App() {
  return <Routes><Route element={<Shell />}>
    <Route index element={<HomePage />} />
    <Route path="intel-score" element={<HomePage researchEntry />} />
    <Route path="stocks/:symbol/intel-score" element={<IntelScorePage />} />
    <Route path="*" element={<div className={ui.empty}><h1>Page not found</h1><p>Start with an IDX symbol from the Home page.</p><NavLink to="/">Back to Home</NavLink></div>} />
  </Route></Routes>
}
