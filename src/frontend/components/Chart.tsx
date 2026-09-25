import { useEffect, useRef } from 'react'
import { init, use as registerECharts, type ComposeOption } from 'echarts/core'
import { BarChart, LineChart, type BarSeriesOption, type LineSeriesOption } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, AriaComponent, type GridComponentOption, type TooltipComponentOption, type LegendComponentOption } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import type { EChartsType } from 'echarts/core'
import s from './ui.module.css'

registerECharts([BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, SVGRenderer])
export type ChartOption = ComposeOption<BarSeriesOption | LineSeriesOption | GridComponentOption | TooltipComponentOption | LegendComponentOption>
export const chartColors = { teal: '#52d4b0', red: '#f08c90', blue: '#82acff', text: '#9aa9bd', grid: '#253043' }
export const chartBase: ChartOption = {
  animation: false, backgroundColor: 'transparent', textStyle: { fontFamily: 'Inter, sans-serif', color: chartColors.text },
  grid: { top: 34, left: 64, right: 18, bottom: 34 },
  tooltip: { trigger: 'axis', renderMode: 'richText', backgroundColor: '#182234', borderColor: '#35445c', textStyle: { color: '#edf2fa' } },
}
export function Chart({ option, label, height = 240 }: { option: ChartOption; label: string; height?: number }) {
  const element = useRef<HTMLDivElement>(null)
  const chart = useRef<EChartsType | null>(null)
  useEffect(() => {
    const instance = init(element.current!, undefined, { renderer: 'svg' })
    chart.current = instance
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(element.current!)
    return () => { observer.disconnect(); instance.dispose(); chart.current = null }
  }, [])
  useEffect(() => { chart.current?.setOption(option, true) }, [option])
  return <div ref={element} className={s.chart} style={{ height }} role="img" aria-label={label} />
}
