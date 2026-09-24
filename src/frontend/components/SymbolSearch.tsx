import { useId, useState } from 'react'
import { useNavigate } from 'react-router'
import { normalizeSymbol, validSymbol } from '../utils/format'
import { Icon } from './Icon'
import s from './ui.module.css'

export function SymbolSearch({ initial = '', large = false }: { initial?: string; large?: boolean }) {
  const [value, setValue] = useState(initial)
  const [error, setError] = useState(false)
  const id = useId()
  const navigate = useNavigate()
  return <form className={large ? s.searchLarge : s.search} onSubmit={event => {
    event.preventDefault()
    const symbol = normalizeSymbol(value)
    if (!validSymbol(symbol)) { setError(true); return }
    setError(false); setValue(symbol); navigate(`/stocks/${symbol}/intel-score`)
  }} noValidate>
    <label className={s.srOnly} htmlFor={id}>IDX symbol</label>
    <div className={s.searchRow}><Icon name="search" /><input id={id} value={value} autoComplete="off" spellCheck={false} placeholder="Enter IDX symbol, e.g. BBCA" aria-invalid={error} aria-describedby={error ? `${id}-error` : undefined} onChange={event => { setValue(event.target.value); setError(false) }} />
      <button className={large ? s.primary : s.searchButton} type="submit" aria-label="Open IntelScore">{large ? 'Explore IntelScore' : 'Go'}<Icon name="arrow" size={16} /></button>
    </div>
    {error && <p id={`${id}-error`} className={s.errorText} role="alert">Invalid ticker format. Use exactly four letters. The .JK suffix is optional.</p>}
  </form>
}
