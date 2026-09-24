import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const testResponse = JSON.parse(readFileSync(new URL('../data/research-response.json', import.meta.url), 'utf8'))

test.beforeEach(async ({ page }) => {
  // Browser tests exercise the frontend contract without reaching Sectors.
  await page.route('**/*', route => {
    const host = new URL(route.request().url()).hostname
    return ['127.0.0.1', 'localhost'].includes(host)
      ? route.continue()
      : route.abort('blockedbyclient')
  })
  await page.route('**/api/v1/**', route => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/stocks/BBCA/intel-score') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(testResponse) })
    }
    if (url.pathname === '/api/v1/stocks/BBCA/flow' && url.searchParams.get('window') === '5d') {
      const response = { ...testResponse, flow: { ...testResponse.flow, window: '5d', trading_days: 5 } }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(response) })
    }
    return route.abort('blockedbyclient')
  })
})

test('Home opens the BBCA example and renders backend score fields', async ({ page }) => {
  const calls: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Start with the flow')
  await page.getByRole('link', { name: 'Lihat IntelScore BBCA' }).click()
  await expect(page).toHaveURL(/\/stocks\/BBCA\/intel-score$/)
  await expect(page.getByText('Test response company')).toBeVisible()
  expect(calls).toHaveLength(1)
  for (const key of ['flow', 'fundamental', 'combined'] as const) {
    await expect(page.getByTestId(`score-${key}`)).toContainText(String(testResponse.scores[key].value))
  }
  await expect(page.getByRole('img').first()).toBeVisible()

  await page.getByRole('button', { name: '5D', exact: true }).click()
  await expect(page.getByText('5 observed trading days')).toBeVisible()
  expect(calls).toHaveLength(2)
  expect(calls[1]).toContain('/flow?window=5d')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('ticker syntax is enforced before a backend request', async ({ page }) => {
  const calls: string[] = []
  page.on('request', request => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })

  await page.goto('/stocks/BAD!/intel-score')
  await expect(page.getByRole('heading', { name: 'Invalid ticker format' })).toBeVisible()
  expect(calls).toHaveLength(0)

  await page.goto('/')
  await page.getByRole('textbox', { name: 'IDX symbol' }).fill('bbca.jk')
  await page.getByRole('button', { name: 'Open IntelScore' }).click()
  await expect(page).toHaveURL(/\/stocks\/BBCA\/intel-score$/)
  await expect(page.getByText('Test response company')).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
