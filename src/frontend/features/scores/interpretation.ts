import type { Component, Research } from '../../types/research'
import { number } from '../../utils/format'

// Presentation bands only. Backend scores and weights are never recalculated.
export function scoreBand(value: number | null) {
  if (value === null || !Number.isFinite(value)) return 'Unavailable'
  if (value < 50) return 'Weak'
  if (value < 60) return 'Neutral'
  if (value < 70) return 'Positive'
  return 'Strong'
}
export type Band = ReturnType<typeof scoreBand>
export const componentInfo: Record<string, { name: string; help: string }> = {
  liquidity: {
    name: 'Liquidity',
    help: 'Daily transaction value estimate against an IDR 5 billion benchmark.',
  },
  foreign_flow: {
    name: 'Foreign flow',
    help: 'Net balance of foreign-ranked brokers, weighted by foreign investor participation.',
  },
  broker_flow: {
    name: 'Broker flow',
    help: 'Independent 5-day and 20-day top broker balance, daily direction, and concentration, weighted 65% and 35%.',
  },
  growth: { name: 'Growth', help: 'Annual revenue and earnings growth.' },
  earnings: { name: 'Earnings', help: 'Profitability, margins, and returns on assets and equity.' },
  cash_flow: {
    name: 'Cash flow',
    help: 'Available cash flow observations from the latest three financial years.',
  },
  valuation: {
    name: 'Valuation',
    help: 'Eligible ratios from the latest three years relative to earlier company history.',
  },
  flow: { name: 'Flow', help: 'Broker activity, foreign participation, and liquidity.' },
  fundamental: { name: 'Fundamental', help: 'Growth, earnings, cash flow, and valuation.' },
}
export const componentName = (key: string) => componentInfo[key]?.name ?? key.replace(/_/g, ' ')
const describe = (component: Component) =>
  `${componentName(component.key).toLowerCase()} (${number(component.value, 1)}/100)`

export function dataConfidence(data: Research): {
  level: 'High' | 'Medium' | 'Low'
  reason: string
} {
  const components = [...data.scores.flow.components, ...data.scores.fundamental.components]
  const missingScore = [
    data.scores.flow.value,
    data.scores.fundamental.value,
    data.scores.combined.value,
  ].some((value) => value === null)
  if (missingScore)
    return { level: 'Low', reason: 'One or more aggregate scores cannot be calculated.' }
  if (data.status === 'stale' || data.sources.some((source) => source.is_stale))
    return { level: 'Low', reason: 'Some source data needs an update.' }
  const tradingDates = new Set(data.flow.liquidity.series.map((point) => point.date))
  const foreignDates = new Set(data.flow.foreign_flow.series.map((point) => point.date))
  const brokerDates = data.flow.broker_summary.daily
    ? new Set(data.flow.broker_summary.daily.map((point) => point.date))
    : null
  if (
    data.flow.incomplete_history ||
    data.flow.trading_days < 20 ||
    tradingDates.size < 20 ||
    [...tradingDates].some(
      (day) => !foreignDates.has(day) || (brokerDates !== null && !brokerDates.has(day)),
    ) ||
    components.some((c) => c.value === null)
  )
    return { level: 'Low', reason: 'Scored evidence or trading-date coverage is incomplete.' }
  const requiredSources = [
    'daily',
    'broker_top',
    ...(data.flow.broker_summary_5d ? ['broker_top_5d'] : []),
    'foreign_flow',
    'company_financials',
    'company_valuation',
  ]
  const dated = requiredSources.every((key) =>
    data.sources.some((source) => source.key === key && (source.as_of || source.period)),
  )
  const completeComponents = [
    'liquidity',
    'foreign_flow',
    'broker_flow',
    'growth',
    'earnings',
    'cash_flow',
    'valuation',
  ].every((key) => components.some((c) => c.key === key && c.value !== null))
  if (data.status === 'partial' || data.missing_inputs.length || !dated || !completeComponents)
    return {
      level: 'Medium',
      reason: 'Scores are available, but some inputs or source dates are missing.',
    }
  return {
    level: 'High',
    reason: 'All score components are available; no source is flagged stale.',
  }
}

export function researchSummary(data: Research): {
  band: Band
  meaning: string
  driver: string
  risk: string
  confidence: ReturnType<typeof dataConfidence>
} {
  const available = [...data.scores.flow.components, ...data.scores.fundamental.components].filter(
    (c): c is Component & { value: number } => c.value !== null && Number.isFinite(c.value),
  )
  const strongest = [...available].sort((a, b) => b.value - a.value).slice(0, 2)
  const weakest = [...available].sort((a, b) => a.value - b.value)[0]
  const driver = strongest.length
    ? `${strongest.every((c) => c.value >= 70) ? 'Strong support from' : 'Most support from'} ${strongest.map(describe).join(' and ')}.`
    : 'No component evidence is available to identify a driver.'
  const partialFlow = data.missing_inputs.some((item) =>
    [
      'flow.window',
      'foreign_flow',
      'broker_top',
      'broker_top_5d',
      'broker_foreign_top',
      'broker_activity',
      'liquidity.value',
    ].includes(item.key),
  )
  const risk =
    data.scores.flow.value === null
      ? 'Flow coverage is incomplete; market participation cannot be confirmed.'
      : data.scores.fundamental.value === null
        ? 'Fundamental coverage is incomplete; business support cannot be confirmed.'
        : partialFlow
          ? 'Flow coverage is partial; the overall score uses the available observations and may change when missing data arrives.'
          : data.status === 'stale' || data.sources.some((source) => source.is_stale)
            ? 'Some source data is stale; current conditions may differ.'
            : weakest
              ? `${componentName(weakest.key)} ${weakest.value < 50 ? 'is weak' : weakest.value < 60 ? 'has neutral support' : 'provides the least support'} (${number(weakest.value, 1)}/100).`
              : 'Insufficient component evidence to assess the main limitation.'
  const band = scoreBand(data.scores.combined.value)
  const meaning =
    band === 'Strong'
      ? 'Strong combined support from the scored evidence.'
      : band === 'Positive'
        ? 'Evidence leans positive, with limitations to monitor.'
        : band === 'Neutral'
          ? 'Mixed evidence; neither side provides a clear overall lead.'
          : band === 'Weak'
            ? 'Limited support across the combined evidence.'
            : 'Evidence is incomplete; an overall assessment is unavailable.'
  return { band, meaning, driver, risk, confidence: dataConfidence(data) }
}

export function rupiah(value: number) {
  return `Rp${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(Math.abs(value))}`
}

export function keyInsights(data: Research) {
  const result: { category: 'Flow' | 'Fundamental' | 'Risk' | 'Data Quality'; text: string }[] = []
  const foreign = data.flow.foreign_flow.net_inflow_idr
  if (foreign !== null)
    result.push({
      category: 'Flow',
      text: `Foreign investors: ${rupiah(foreign)} ${foreign < 0 ? 'net sell' : foreign > 0 ? 'net buy' : 'net flow'} over ${data.flow.trading_days} observations.`,
    })
  const breadth = data.flow.broker_summary.breadth.find((b) => b.top_n === 5)
  if (breadth && breadth.buyer_count && breadth.seller_count)
    result.push({
      category: 'Flow',
      text: `Top 5 broker balance: ${rupiah(breadth.balance_idr)} ${breadth.balance_idr < 0 ? 'seller-side' : breadth.balance_idr > 0 ? 'buyer-side' : 'balanced'}. Coverage: ${breadth.buyer_count}/5 buyers, ${breadth.seller_count}/5 sellers.`,
    })
  const facts = data.fundamentals.groups
    .flatMap((group) => group.metrics)
    .filter(
      (metric) =>
        ['earnings', 'operating_cash_flow'].includes(metric.key) &&
        metric.availability === 'available' &&
        metric.value !== null,
    )
  if (facts.length)
    result.push({
      category: 'Fundamental',
      text:
        facts
          .map(
            (metric) =>
              `${metric.key === 'earnings' ? 'Earnings' : 'Operating cash flow'} ${metric.value! < 0 ? '-' : ''}${rupiah(metric.value!)} (${metric.period ?? 'undated'})`,
          )
          .join('; ') + '.',
    })
  else
    result.push({
      category: 'Fundamental',
      text:
        data.scores.fundamental.value === null
          ? 'Fundamental support is unavailable.'
          : `Fundamental support: ${scoreBand(data.scores.fundamental.value).toLowerCase()}, ${number(data.scores.fundamental.value, 1)}/100.`,
    })
  const summary = researchSummary(data)
  result.push({ category: 'Risk', text: summary.risk })
  result.push({
    category: 'Data Quality',
    text: `${summary.confidence.level} coverage confidence. ${summary.confidence.reason}`,
  })
  return result.slice(0, 5)
}
