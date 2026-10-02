import { useEffect, useRef } from 'react'
import { init, use as registerECharts, type ComposeOption } from 'echarts/core'
import {
  BarChart,
  CandlestickChart,
  LineChart,
  type BarSeriesOption,
  type CandlestickSeriesOption,
  type LineSeriesOption,
} from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  type GridComponentOption,
  type TooltipComponentOption,
  type LegendComponentOption,
} from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import type { EChartsType } from 'echarts/core'
import { useTheme } from '../app/theme'

registerECharts([
  BarChart,
  CandlestickChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  AriaComponent,
  SVGRenderer,
])
export type ChartOption = ComposeOption<
  | BarSeriesOption
  | CandlestickSeriesOption
  | LineSeriesOption
  | GridComponentOption
  | TooltipComponentOption
  | LegendComponentOption
>
export function useChartTheme() {
  useTheme()
  const styles = getComputedStyle(document.documentElement)
  const token = (name: string) => styles.getPropertyValue(name).trim()
  const chartColors = {
    teal: token('--teal'),
    red: token('--red'),
    blue: token('--blue'),
    amber: token('--amber'),
    text: token('--chart-label'),
    grid: token('--border-soft'),
  }
  const chartBase: ChartOption = {
    animation: false,
    backgroundColor: 'transparent',
    textStyle: {
      fontFamily: 'Helvetica Neue, Arial, sans-serif',
      fontSize: 13,
      color: chartColors.text,
    },
    grid: { top: 40, left: 68, right: 24, bottom: 38 },
    tooltip: {
      trigger: 'axis',
      renderMode: 'richText',
      confine: true,
      backgroundColor: token('--panel-raised'),
      borderColor: token('--border'),
      textStyle: { color: token('--text'), fontSize: 13 },
    },
  }
  return { chartColors, chartBase }
}
export function Chart({
  option,
  label,
  height = 240,
  onItemClick,
}: {
  option: ChartOption
  label: string
  height?: number | string
  onItemClick?: (index: number) => void
}) {
  const element = useRef<HTMLDivElement>(null)
  const chart = useRef<EChartsType | null>(null)
  const clickHandler = useRef(onItemClick)
  useEffect(() => {
    clickHandler.current = onItemClick
  }, [onItemClick])
  useEffect(() => {
    const instance = init(element.current!, undefined, { renderer: 'svg' })
    chart.current = instance
    instance.on('click', (params) => {
      if (typeof params.dataIndex === 'number') clickHandler.current?.(params.dataIndex)
    })
    const observer = new ResizeObserver(() => instance.resize())
    observer.observe(element.current!)
    return () => {
      observer.disconnect()
      instance.dispose()
      chart.current = null
    }
  }, [])
  useEffect(() => {
    chart.current?.setOption(option, true)
  }, [option])
  return (
    <div
      ref={element}
      className="intelflow-chart w-full min-w-0 overflow-hidden"
      style={{ height }}
      role="img"
      aria-label={label}
    />
  )
}
