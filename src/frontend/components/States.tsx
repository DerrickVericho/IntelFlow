import type { Envelope } from '../types/research'
import { ApiError } from '../api/client'
import { SymbolSearch } from './SymbolSearch'
import { sourceLabel } from './Sources'
import { label } from '../utils/format'
import { ui as s } from './ui'

export function Loading({ text = 'Loading research and dated evidence…' }: { text?: string }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-7 text-muted" role="status">
      <span className="mr-3 inline-block size-4 animate-spin rounded-full border-2 border-line border-t-accent motion-reduce:animate-none" />
      {text}
      <div className="mt-5 h-14 rounded-xl bg-raised last:w-2/3" />
      <div className="mt-5 h-14 rounded-xl bg-raised last:w-2/3" />
    </div>
  )
}
export function ErrorState({
  error,
  retry,
  allowSearch = false,
}: {
  error: Error
  retry: () => void
  allowSearch?: boolean
}) {
  const api = error instanceof ApiError ? error : null
  const title =
    api?.status === 404
      ? 'No data found'
      : api?.status === 422
        ? 'Invalid request'
        : 'Research temporarily unavailable'
  const description =
    api?.status === 404
      ? 'No observations were returned for this ticker. This does not confirm that the ticker is invalid. Try another company to continue your research.'
      : api?.status === 422
        ? 'Check the ticker or selected period and try again.'
        : api?.status === 429
          ? 'The data request limit has been reached. Please return later.'
          : 'We could not load the research right now. Check your connection or try again in a moment.'
  const canRetry = !api || api.status === 0 || api.status >= 500
  return (
    <div className={s.errorBox} role="alert">
      <h2>{title}</h2>
      <p>{description}</p>
      <div className="mt-6 flex flex-wrap items-center gap-4">
        {allowSearch && <SymbolSearch />}
        {canRetry && (
          <button className={s.secondary} onClick={retry}>
            Try again
          </button>
        )}
      </div>
    </div>
  )
}

function availability(items: Envelope['missing_inputs']) {
  const groups = new Map<string, Set<string>>()
  for (const item of items) {
    // Aggregate score messages repeat their underlying input limitations.
    const group = item.key.startsWith('scores.')
      ? 'Scores'
      : item.key.startsWith('fundamentals.') ||
          item.key.startsWith('company_financial') ||
          item.key === 'company_valuation'
        ? 'Fundamentals'
        : item.key === 'company_overview'
          ? 'Company overview'
          : item.key === 'shareholders.count'
            ? 'Shareholder count'
            : item.key === 'foreign_flow'
              ? 'Foreign flow'
              : item.key === 'liquidity.baseline'
                ? 'Volume chart context'
                : item.key.startsWith('liquidity')
                  ? 'Liquidity data'
                  : item.key === 'broker_top' ||
                      item.key === 'broker_top_5d' ||
                      item.key === 'broker_foreign_top' ||
                      item.key === 'broker_activity'
                    ? 'Broker activity'
                    : item.key === 'flow.window'
                      ? 'Trading history'
                      : 'Research data'
    const description = item.key.startsWith('fundamentals.')
      ? label(item.key.slice('fundamentals.'.length))
      : ''
    const values = groups.get(group) ?? new Set<string>()
    if (description) values.add(description)
    groups.set(group, values)
  }
  return Array.from(groups, ([name, metrics]) => ({
    name,
    description: metrics.size
      ? `Unavailable: ${Array.from(metrics).join(', ')}. Other reported metrics remain available.`
      : name === 'Scores'
        ? 'One or more scores need additional evidence. Each affected score explains what is missing.'
        : name === 'Foreign flow'
          ? 'Foreign investor data is unavailable or does not cover every trading date. Check the Flow Score coverage note.'
          : name === 'Volume chart context'
            ? 'Some dates lack earlier volume observations for the comparison chart. The IDR liquidity score uses the available daily values.'
            : name === 'Liquidity data'
              ? 'Some dates lack valid closing price or share volume for the liquidity score.'
              : name === 'Broker activity'
                ? 'Broker rankings or daily broker observations are incomplete for the selected dates.'
                : name === 'Trading history'
                  ? 'Fewer trading observations are available than the selected period requires.'
                  : name === 'Company overview'
                    ? 'Company details are unavailable. Available trading evidence is shown below.'
                    : name === 'Shareholder count'
                      ? 'Some monthly counts or changes were not reported. Available category holdings remain visible.'
                      : 'Some reported values are unavailable.',
  }))
}
export function DataStatus({ data }: { data: Envelope }) {
  const staleSources = data.sources.filter((source) => source.is_stale)
  return (
    <div className="grid gap-3 empty:hidden">
      {(data.status === 'partial' || data.missing_inputs.length > 0) && (
        <div className={s.notice} role="status">
          <strong>Some data is unavailable</strong>
          <ul className="mt-2 space-y-1">
            {availability(data.missing_inputs).map((group) => (
              <li key={group.name}>
                <strong>{group.name}:</strong> {group.description}
              </li>
            ))}
          </ul>
          {data.missing_inputs.length === 0 && (
            <p>
              The provider returned partial coverage. Check source dates before comparing results.
            </p>
          )}
        </div>
      )}
      {(data.status === 'stale' || staleSources.length > 0) && (
        <div className={s.notice} role="status">
          <strong>Some sources need an update</strong>
          <p>
            {staleSources.length
              ? staleSources.map((source) => sourceLabel(source.key)).join(', ')
              : 'Research data'}{' '}
            may be out of date. Observation dates are listed below.
          </p>
        </div>
      )}
    </div>
  )
}
