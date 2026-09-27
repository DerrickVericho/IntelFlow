import type { ShareholderPoint, ShareholderResponse } from '../../types/research'

export type InvestorOrigin = 'all' | 'local' | 'foreign'
export type CompositionMode = 'shares' | 'percent'

export interface ShareholderCategory { key: string; label: string }

export function shareholderCategories(categories: ShareholderResponse['categories']): ShareholderCategory[] {
  const seen = new Set<string>()
  return categories.flatMap(category => {
    if (!/_(l|f)$/.test(category.key)) return []
    const key = category.key.slice(0, -2)
    if (seen.has(key)) return []
    seen.add(key)
    return [{ key, label: key.replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase()) }]
  })
}

export function categoryHolding(point: ShareholderPoint, key: string, origin: InvestorOrigin): number | null {
  const local = point.holdings[`${key}_l`]
  const foreign = point.holdings[`${key}_f`]
  if (origin === 'local') return typeof local === 'number' && Number.isFinite(local) ? local : null
  if (origin === 'foreign') return typeof foreign === 'number' && Number.isFinite(foreign) ? foreign : null
  return typeof local === 'number' && Number.isFinite(local) && typeof foreign === 'number' && Number.isFinite(foreign)
    ? local + foreign : null
}

export function categoryBreakdown(point: ShareholderPoint, categories: ShareholderCategory[], origin: InvestorOrigin) {
  const rows = categories.map(category => ({ ...category, value: categoryHolding(point, category.key, origin) }))
  const reported = rows.reduce((total, row) => total + (row.value ?? 0), 0)
  const expected = origin === 'all' ? point.total_local + point.total_foreign : origin === 'local' ? point.total_local : point.total_foreign
  return { rows, reported, expected, incomplete: rows.some(row => row.value === null) || reported !== expected }
}

export function monthlySnapshots(series: ShareholderPoint[], year: number) {
  const months: (ShareholderPoint | null)[] = Array.from({ length: 12 }, () => null)
  for (const point of [...series].sort((a, b) => a.date.localeCompare(b.date))) {
    const month = Number(point.date.slice(5, 7)) - 1
    if (point.date.startsWith(`${year}-`) && month >= 0 && month < 12) months[month] = point
  }
  return months
}
