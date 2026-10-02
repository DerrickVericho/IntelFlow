import { expect, test } from '@playwright/test'
import type { BrokerFlowResponse } from '../../types/research'

const dates = ['2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30']
const response = {
  symbol: 'BBCA',
  as_of: dates[4],
  status: 'complete',
  sources: [],
  missing_inputs: [],
  range: '5d',
  effective_start: dates[0],
  effective_end: dates[4],
  incomplete_history: false,
  excluded_price_dates: [],
  prices: dates.map((date, index) => ({
    date,
    open: 7400 + index * 20,
    high: 7510 + index * 20,
    low: 7330 + index * 20,
    close: 7450 + index * 20,
    volume: 100_000_000,
    market_cap: null,
  })),
  top_buyers: ['YP', 'CC', 'PD', 'AK', 'DR'].map((broker_code, index) => ({
    rank: index + 1,
    broker_code,
    net_idr: (160 - index * 24) * 1_000_000_000,
  })),
  top_sellers: ['BK', 'NI', 'RX', 'MG', 'DH'].map((broker_code, index) => ({
    rank: index + 1,
    broker_code,
    net_idr: -(150 - index * 22) * 1_000_000_000,
  })),
  broker_series: [
    ...['YP', 'CC', 'PD', 'AK', 'DR'].map((broker_code, index) => ({
      broker_code,
      side: 'buyer',
      points: dates.map((date, day) => ({
        date,
        net_shares: (150 - index * 20) * 1000,
        cumulative_net_shares: (day + 1) * (150 - index * 20) * 1000,
      })),
    })),
    ...['BK', 'NI', 'RX', 'MG', 'DH'].map((broker_code, index) => ({
      broker_code,
      side: 'seller',
      points: dates.map((date, day) => ({
        date,
        net_shares: -(140 - index * 18) * 1000,
        cumulative_net_shares: -(day + 1) * (140 - index * 18) * 1000,
      })),
    })),
  ],
  days: dates.map((date) => ({
    date,
    available: true,
    top_buyers: ['YP', 'CC', 'PD', 'AK', 'DR'].map((broker_code, index) => ({
      broker_code,
      shares: (150 - index * 20) * 1000,
    })),
    top_sellers: ['BK', 'NI', 'RX', 'MG', 'DH'].map((broker_code, index) => ({
      broker_code,
      shares: (140 - index * 18) * 1000,
    })),
  })),
}

test('BrokerFlow uses the available width and opens a dated broker dialog', async ({ page }) => {
  await page.route('**/api/v1/stocks/BBCA/broker-flow?range=*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(response) }),
  )
  await page.goto('/broker-flow/BBCA')
  const chart = page.getByRole('img', { name: /price candlesticks and cumulative net shares/i })
  await expect(chart).toBeVisible()
  const chartBox = await chart.boundingBox()
  const mainBox = await page.locator('main').boundingBox()
  expect(chartBox).not.toBeNull()
  expect(mainBox).not.toBeNull()
  expect(chartBox!.width).toBeGreaterThan(mainBox!.width * 0.7)
  await page.screenshot({ path: 'src/frontend/test-results/broker-flow-chart.png', fullPage: true })
  await page.getByRole('combobox', { name: 'Inspect trading day' }).selectOption(dates[4])
  const dialog = page.getByRole('dialog', { name: /30 Sept 2026/i })
  await expect(dialog).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'Top 5 net buyers · shares' })).toBeVisible()
  await expect(dialog.getByRole('heading', { name: 'Top 5 net sellers · shares' })).toBeVisible()
  await page.screenshot({
    path: 'src/frontend/test-results/broker-flow-dialog.png',
    fullPage: true,
  })
  await dialog.getByRole('button', { name: 'Close' }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(chart).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({
    path: 'src/frontend/test-results/broker-flow-mobile.png',
    fullPage: true,
  })
})

test('ten broker lines have distinct colors in light and dark themes', async ({ page }) => {
  await page.route('**/api/v1/stocks/BBCA/broker-flow?range=*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(response) }),
  )
  await page.goto('/broker-flow/BBCA')
  const chart = page.getByRole('img', { name: /price candlesticks and cumulative net shares/i })
  await expect(chart).toBeVisible()
  const swatches = chart.locator('..').locator('button[aria-pressed] span[aria-hidden="true"]')
  await expect(swatches).toHaveCount(10)
  const colors = () =>
    swatches.evaluateAll((elements) =>
      elements.map((element) => getComputedStyle(element).borderTopColor),
    )
  const light = await colors()
  expect(new Set(light).size).toBe(10)
  await page.getByRole('combobox', { name: 'Color theme' }).selectOption('dark')
  const dark = await colors()
  expect(new Set(dark).size).toBe(10)
  expect(dark).not.toEqual(light)
  await page.screenshot({
    path: 'src/frontend/test-results/broker-flow-ten-colors-dark.png',
    fullPage: true,
  })
})

test('analysis search entries share placement and input width', async ({ page }) => {
  const boxes = []
  for (const path of ['/intel-score', '/shareholders', '/broker-flow']) {
    await page.goto(path)
    const box = await page.locator('main form').boundingBox()
    expect(box).not.toBeNull()
    boxes.push(box!)
  }
  expect(boxes[0].x).toBe(boxes[2].x)
  expect(boxes[1].x).toBe(boxes[2].x)
  expect(boxes[0].width).toBe(boxes[2].width)
  expect(boxes[1].width).toBe(boxes[2].width)
})

test('BrokerFlow discloses missing broker days and lets later points remain', async ({ page }) => {
  const partial = structuredClone(response) as BrokerFlowResponse
  partial.status = 'partial'
  partial.missing_inputs = [
    { key: 'broker_flow.daily', reason: 'Daily broker activity is missing for some price dates.' },
  ]
  partial.excluded_price_dates = ['2026-10-01']
  partial.days[2].available = false
  partial.days[2].top_buyers = []
  partial.days[2].top_sellers = []
  for (const broker of partial.broker_series) {
    broker.points[2].net_shares = null
    broker.points[2].cumulative_net_shares = null
  }
  await page.route('**/api/v1/stocks/BBCA/broker-flow?range=*', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(partial) }),
  )
  await page.goto('/broker-flow/BBCA')
  await expect(page.getByText(/Broker activity covers 4 of 5 trading sessions/)).toBeVisible()
  await expect(page.getByText(/No broker summary was returned for 28 Sept 2026/)).toBeVisible()
  await expect(
    page.getByText(/Price records without a valid candle or positive volume were excluded on 01 Oct 2026/),
  ).toBeVisible()
  await expect(
    page.getByRole('img', { name: /price candlesticks and cumulative net shares/i }),
  ).toBeVisible()
  expect(partial.broker_series[0].points[3].cumulative_net_shares).not.toBeNull()
  await page.getByRole('combobox', { name: 'Inspect trading day' }).selectOption(dates[2])
  await expect(
    page.getByText('Broker activity was not returned for this trading date.'),
  ).toBeVisible()
})
