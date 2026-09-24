export const normalizeSymbol = (value: string) => value.trim().toUpperCase().replace(/\.JK$/, '')
export const validSymbol = (value: string) => /^[A-Z]{4}$/.test(value)
export const number = (value: number | null, maximumFractionDigits = 2) => value === null ? 'Unavailable' : new Intl.NumberFormat('en-US', { maximumFractionDigits }).format(value)
export const compact = (value: number | null) => value === null ? 'Unavailable' : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(value)
export const idr = (value: number | null) => value === null ? 'Unavailable' : `IDR ${compact(value)}`
export const metricValue = (value: number | null, unit: string) => value === null ? 'Unavailable' : unit === 'idr' ? idr(value) : `${number(value)}${unit === 'percent' ? '%' : '×'}`
export const date = (value: string | null) => !value ? 'Undated' : /^\d{4}$/.test(value) ? value : new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Jakarta' }).format(new Date(value))
export const timestamp = (value: string) => `${new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Jakarta' }).format(new Date(value))} WIB`
export const label = (value: string) => value.replace(/_/g, ' ')
