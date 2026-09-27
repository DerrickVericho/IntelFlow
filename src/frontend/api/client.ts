import type { FlowResponse, PriceResponse, Research, Window } from '../types/research'

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public requestId?: string) { super(message) }
}
async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1/stocks/${path}`, { signal: AbortSignal.any([signal, AbortSignal.timeout(45_000)]), headers: { Accept: 'application/json' } })
  } catch (error) {
    if (signal.aborted) throw error
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the IntelFlow backend. Check your connection and try again.')
  }
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new ApiError(response.status, payload?.error?.code ?? 'API_ERROR', payload?.error?.message ?? 'The backend could not complete this request.', payload?.error?.request_id ?? response.headers.get('X-Request-ID'))
  }
  if (!payload || typeof payload !== 'object' || !Array.isArray(payload.sources)) {
    throw new ApiError(502, 'INVALID_RESPONSE', 'The backend returned an unreadable research response.')
  }
  return payload as T
}
export async function getResearch(symbol: string, signal: AbortSignal) {
  const data = await get<Research>(`${encodeURIComponent(symbol)}/intel-score`, signal)
  if (data.symbol !== symbol || !data.flow || !data.company || !data.scores || !data.fundamentals || !Array.isArray(data.fundamentals.groups) || !Array.isArray(data.key_points) || ['flow', 'fundamental', 'combined'].some(key => !data.scores[key as 'flow' | 'fundamental' | 'combined'])) {
    throw new ApiError(502, 'INVALID_RESPONSE', 'The backend returned an incomplete or mismatched research response.')
  }
  return data
}
export async function getFlow(symbol: string, window: Window, signal: AbortSignal) {
  const data = await get<FlowResponse>(`${encodeURIComponent(symbol)}/flow?window=${window}`, signal)
  if (data.symbol !== symbol || !data.flow || data.flow.window !== window) throw new ApiError(502, 'INVALID_RESPONSE', 'The backend returned evidence for a different symbol or window.')
  return data
}
export async function getPriceHistory(symbol: string, range: '1m' | '3m', signal: AbortSignal) {
  const data = await get<PriceResponse>(`${encodeURIComponent(symbol)}/price-history?range=${range}`, signal)
  if (data.symbol !== symbol || data.range !== range || !Array.isArray(data.series) || data.series.some(point => !/^\d{4}-\d{2}-\d{2}$/.test(point.date) || !Number.isFinite(point.close))) {
    throw new ApiError(502, 'INVALID_RESPONSE', 'The backend returned unreadable or mismatched price history.')
  }
  return data
}
