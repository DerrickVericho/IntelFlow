// Public IntelFlow HTTP models only. Keep aligned with backend/API_CONTRACT.md.
export type Window = '1d' | '5d' | '20d'
export interface Source {
  key: string; provider: string; as_of: string | null; period: string | null
  fetched_at: string; effective_start: string | null; effective_end: string | null; is_stale: boolean
}
export interface Envelope {
  symbol: string; as_of: string | null; status: 'complete' | 'partial' | 'stale'
  sources: Source[]; missing_inputs: { key: string; reason: string }[]
}
export interface Component { key: string; value: number | null; weight: number; reason: string | null; source_keys: string[] }
export interface Score { value: number | null; reason: string | null; components: Component[] }
export interface Broker { broker_code: string; side: 'buyer' | 'seller'; rank: number; buy_idr: number; sell_idr: number; net_idr: number; foreign_net_idr: number | null }
export interface FlowEvidence {
  window: Window; effective_start: string | null; effective_end: string | null; trading_days: number; incomplete_history: boolean
  broker_summary: {
    brokers: Broker[]
    breadth: { top_n: number; buyer_net_idr: number; seller_net_idr: number; balance_idr: number; balance_ratio: number | null; buyer_count: number; seller_count: number }[]
  }
  foreign_flow: {
    net_inflow_idr: number | null; buy_idr: number | null; sell_idr: number | null; average_foreign_share_percent: number | null; positive_days: number; negative_days: number
    series: { date: string; net_inflow_idr: number; cumulative_net_inflow_idr: number; foreign_share_percent: number | null }[]
  }
  liquidity: {
    baseline_window: number; latest_volume_shares: number | null; average_volume_shares: number | null; latest_vs_average_ratio: number | null
    series: { date: string; close_idr: number; volume_shares: number; average_volume_shares: number | null; volume_ratio: number | null; baseline_observations: number }[]
  }
}
export interface Metric {
  key: string; label: string; value: number | null; unit: 'idr' | 'percent' | 'ratio'; period: string | null
  period_type: 'annual' | 'quarterly_yoy_undated'; availability: 'available' | 'unavailable'; reason: string | null
  direction: 'up' | 'down' | 'flat' | 'unknown'; series: { period: string; value: number | null }[]; source_keys: string[]
}
export interface MetricGroup { key: string; label: string; score: number | null; metrics: Metric[] }
export interface FlowResponse extends Envelope { flow: FlowEvidence }
export interface PriceResponse extends Envelope {
  range: '1m' | '3m'; effective_start: string | null; effective_end: string | null; incomplete_history: boolean
  series: { date: string; open: number | null; high: number | null; low: number | null; close: number; volume: number; market_cap: number | null }[]
}
export interface ShareholderPoint {
  date: string; shares_number: number; holdings: Record<string, number | null>
  total_local: number; total_foreign: number
  shareholder_count: number | null; shareholder_count_change: number | null
}
export interface ShareholderResponse extends Envelope {
  year: number; supported_years: number[]
  categories: { key: string; label: string }[]
  series: ShareholderPoint[]
}
export interface Research extends FlowResponse {
  company: { name: string | null; sector: string | null; sub_sector: string | null; last_close_idr: number | null; close_date: string | null; previous_close_idr: number | null; previous_close_date: string | null; change_idr: number | null; change_percent: number | null }
  scores: {
    flow: Score; fundamental: Score; combined: Score
    calculation_version: string; calculated_at: string; input_periods: Record<string, string | null>; research_state: string
  }
  key_points: { kind: 'evidence' | 'risk' | 'conflict' | 'unavailable'; category: 'flow' | 'fundamental' | 'coverage'; title: string; text: string; items: string[]; source_keys: string[] }[]
  fundamentals: { reporting_period: string | null; currency: string; groups: MetricGroup[] }
}
