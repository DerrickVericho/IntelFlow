// Shared Tailwind recipes keep controls consistent across research and recovery states.
export const ui = {
  muted: 'text-sm text-muted',
  eyebrow: 'mb-2 block text-sm font-medium text-muted',
  primary:
    'primary-action inline-flex min-h-11 items-center justify-center gap-2 whitespace-nowrap rounded-xl border px-5 py-3 text-sm font-semibold transition-[filter] hover:brightness-110',
  secondary:
    'inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-line bg-raised px-5 py-3 text-sm font-semibold text-ink hover:border-accent',
  panel: 'min-w-0 rounded-2xl border border-line bg-surface p-5 sm:p-7',
  sectionHeading: 'mb-6 flex flex-wrap items-center justify-between gap-4',
  badge: 'inline-flex rounded-lg bg-raised px-3 py-1.5 text-xs font-medium text-muted',
  badgeWarning: 'inline-flex rounded-lg bg-warning px-3 py-1.5 text-xs font-medium text-caution',
  notice:
    'rounded-xl border border-warning-line bg-warning px-5 py-4 text-sm leading-relaxed text-caution',
  errorBox:
    'rounded-2xl border border-line border-l-4 border-l-negative bg-surface p-6 sm:p-8 [&_p]:mt-3 [&_p]:max-w-prose [&_p]:text-muted',
  empty: 'my-4 rounded-xl border border-dashed border-line p-6 text-sm text-muted',
  tableScroll:
    'max-w-full overflow-auto rounded-xl border border-line focus-visible:outline-2 focus-visible:outline-accent',
} as const
