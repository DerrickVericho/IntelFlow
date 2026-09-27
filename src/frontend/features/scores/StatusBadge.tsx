import type { Band } from './interpretation'

export const bandStyle: Record<Band, string> = {
  Strong: 'text-positive bg-positive-soft border-positive/40',
  Positive: 'text-accent bg-accent-soft border-accent/40',
  Neutral: 'text-caution bg-warning border-warning-line',
  Weak: 'text-negative bg-negative-soft border-negative/40',
  Unavailable: 'text-muted bg-raised border-control',
}
export function StatusBadge({ band }: { band: Band }) {
  return <span className={`inline-flex items-center rounded-lg border px-3 py-1 text-sm font-semibold ${bandStyle[band]}`}>{band}</span>
}
