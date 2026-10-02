import { useId, useState } from 'react'
import { useNavigate } from 'react-router'
import { normalizeSymbol, validSymbol } from '../utils/format'
import { Icon } from './Icon'
import { ui } from './ui'

export function SymbolSearch({
  initial = '',
  large = false,
  compact = false,
  destination = 'intel-score',
}: {
  initial?: string
  large?: boolean
  compact?: boolean
  destination?: 'intel-score' | 'shareholders' | 'broker-flow'
}) {
  const [value, setValue] = useState(initial)
  const [error, setError] = useState(false)
  const id = useId()
  const navigate = useNavigate()
  return (
    <form
      className={large ? 'w-full max-w-2xl' : compact ? 'min-w-0 flex-1 sm:w-64' : 'w-full sm:w-72'}
      onSubmit={(event) => {
        event.preventDefault()
        const symbol = normalizeSymbol(value)
        if (!validSymbol(symbol)) {
          setError(true)
          return
        }
        setError(false)
        setValue(symbol)
        navigate(
          destination === 'shareholders'
            ? `/shareholders/${symbol}`
            : destination === 'broker-flow'
              ? `/broker-flow/${symbol}`
              : `/stocks/${symbol}/intel-score`,
        )
      }}
      noValidate
    >
      <label className="sr-only" htmlFor={id}>
        {destination === 'shareholders'
          ? 'Shareholder IDX symbol'
          : destination === 'broker-flow'
            ? 'BrokerFlow IDX symbol'
            : 'IDX symbol'}
      </label>
      <div
        className={`flex items-center gap-2 rounded-xl border border-control bg-surface p-1.5 pl-4 text-muted shadow-sm ${large ? 'flex-wrap sm:flex-nowrap sm:p-2 sm:pl-5' : ''}`}
      >
        <Icon name="search" />
        <input
          className={`min-w-0 flex-1 bg-transparent text-base text-ink outline-offset-2 placeholder:text-muted ${compact ? 'py-1.5' : 'py-3'}`}
          id={id}
          value={value}
          autoComplete="off"
          spellCheck={false}
          placeholder={large ? 'Enter IDX symbol, e.g. BBCA' : 'Ticker, e.g. BBCA'}
          aria-invalid={error}
          aria-describedby={error ? `${id}-error` : undefined}
          onChange={(event) => {
            setValue(event.target.value)
            setError(false)
          }}
        />
        <button
          className={`${compact ? ui.secondary : ui.primary} ${large ? 'w-full sm:w-auto' : 'px-3 py-2'}`}
          type="submit"
          aria-label={
            destination === 'shareholders'
              ? 'Open Shareholders'
              : destination === 'broker-flow'
                ? 'Open BrokerFlow'
                : 'Open IntelScore'
          }
        >
          {large
            ? destination === 'shareholders'
              ? 'Explore Shareholders'
              : destination === 'broker-flow'
                ? 'Explore BrokerFlow'
                : 'Explore IntelScore'
            : 'Go'}
          <Icon name="arrow" size={16} />
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className="mt-2 text-sm text-negative" role="alert">
          Invalid ticker format. Use exactly four letters. The .JK suffix is optional.
        </p>
      )}
    </form>
  )
}
