import { Component, Suspense, lazy, useEffect, useRef, type ReactNode } from 'react'
import { NavLink, Outlet, Route, Routes, useLocation, useMatch } from 'react-router'
import { HomePage } from '../pages/HomePage'
import { Loading } from '../components/States'
import { Icon } from '../components/Icon'
import s from './shell.module.css'
import ui from '../components/ui.module.css'

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
  return <div className={s.shell}>
    <a className={s.skip} href="#main">Skip to content</a>
    <aside className={s.sidebar}>
      <NavLink to="/" className={s.brand}><span className={s.brandIcon}><Icon name="flow" size={25} /></span><span>IntelFlow<small>MARKET INTELLIGENCE</small></span></NavLink>
      <div className={s.navLabel}>WORKSPACE</div>
      <nav aria-label="Main navigation">
        <NavLink to="/" end className={({ isActive }) => isActive ? s.active : s.navItem}><Icon name="home" />Home</NavLink>
        <NavLink to={match ? `/stocks/${match.params.symbol}/intel-score` : '/intel-score'} className={({ isActive }) => isActive || match ? s.active : s.navItem}><Icon name="chart" />IntelScore<span className={s.mvp}>MVP</span></NavLink>
        <div className={s.navLabel}>EXPLORE</div>
        <div className={s.disabled} aria-disabled="true"><Icon name="people" /><span>Shareholder Composition<small>Coming later</small></span></div>
        <div className={s.disabled} aria-disabled="true"><Icon name="layers" /><span>Stockchart<small>Coming later</small></span></div>
      </nav>
      <div className={s.sidebarFoot}><span className={s.marketDot} /> INDONESIA STOCK EXCHANGE<p>Follow the flow.<br />Understand the context.</p><small>Research workspace · v0.1</small></div>
    </aside>
    <div className={s.workspace}>
      <div className={s.topbar}><span>Workspace <span className={s.slash}>/</span> <strong>{location.pathname === '/' ? 'Overview' : 'IntelScore research'}</strong></span><span className={s.market}>IDX <span>·</span> Indonesia</span></div>
      <main ref={main} id="main" tabIndex={-1} className={s.main}>
        <Boundary key={location.pathname}><Suspense fallback={<Loading text="Opening research workspace…" />}><Outlet /></Suspense></Boundary>
      </main>
      <footer className={s.footer}><span>IntelFlow <span className={s.slash}>/</span> Powered by Sectors data</span><span>For educational and research purposes. Not investment advice.</span></footer>
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
