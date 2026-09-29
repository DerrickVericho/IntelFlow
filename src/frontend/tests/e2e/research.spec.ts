import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { priceResponse } from '../fixtures'

const testResponse = JSON.parse(
  readFileSync(new URL('../data/research-response.json', import.meta.url), 'utf8'),
)

test.beforeEach(async ({ page }) => {
  // Browser tests exercise the frontend contract without reaching Sectors.
  await page.route('**/*', (route) => {
    const host = new URL(route.request().url()).hostname
    return ['127.0.0.1', 'localhost'].includes(host)
      ? route.continue()
      : route.abort('blockedbyclient')
  })
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/stocks/BBCA/price-history') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(priceResponse(url.searchParams.get('range') === '3m' ? '3m' : '1m')),
      })
    }
    if (url.pathname === '/api/v1/stocks/BBCA/intel-score') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(testResponse),
      })
    }
    if (url.pathname === '/api/v1/stocks/BBCA/flow' && url.searchParams.get('window') === '5d') {
      const response = {
        ...testResponse,
        flow: { ...testResponse.flow, window: '5d', trading_days: 5 },
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(response),
      })
    }
    return route.abort('blockedbyclient')
  })
})

test('Home opens the BBCA example and renders backend score fields', async ({ page }) => {
  const calls: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })

  await page.goto('/')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Start with the flow')
  await page.getByRole('link', { name: 'Explore BBCA' }).click()
  await expect(page).toHaveURL(/\/stocks\/BBCA\/intel-score$/)
  await expect(page.getByText('Test response company')).toBeVisible()
  await expect(
    page.getByRole('img', { name: /^Three-month share price candlesticks/ }),
  ).toBeVisible()
  expect(calls).toHaveLength(2)
  for (const key of ['flow', 'fundamental', 'combined'] as const) {
    await expect(page.getByTestId(`score-${key}`)).toContainText(
      String(testResponse.scores[key].value),
    )
  }
  await expect(page.getByRole('img', { name: /brokers paired by rank/ })).toBeVisible()

  await page.getByRole('button', { name: '5D', exact: true }).click()
  await expect(page.getByText('5 observed trading days')).toBeVisible()
  expect(calls).toHaveLength(3)
  expect(calls[2]).toContain('/flow?window=5d')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('broker investor filter updates chart and net table without another request', async ({
  page,
}) => {
  const calls: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })
  await page.goto('/stocks/BBCA/intel-score')
  await expect(page.getByText('Test response company')).toBeVisible()
  const flow = page.getByRole('region', { name: 'Flow activity' })
  const filter = flow.getByRole('group', { name: 'Broker investor filter' })
  const table = flow.getByRole('region', { name: 'Broker net activity table' })
  const chart = flow.getByRole('img', { name: /brokers paired by rank/ })
  await expect(chart).toBeVisible()
  await expect(
    page.getByRole('img', { name: /^Three-month share price candlesticks/ }),
  ).toBeVisible()
  const initialCalls = calls.length
  const initialFlowScore = await page.getByTestId('score-flow').textContent()

  await filter.getByRole('button', { name: 'Foreign' }).click()
  await expect(table.getByRole('row').nth(1)).toContainText('B0')
  await expect(table.getByRole('row').nth(1)).toContainText('+100')
  await expect(chart.locator('text').filter({ hasText: /^S0$/ })).toHaveCount(0)
  await expect(flow).toContainText('re-ranked within this list, not the whole market')

  await filter.getByRole('button', { name: 'Local' }).click()
  await expect(table.getByRole('row').nth(1)).toContainText('+19,900')
  await expect(table.getByRole('row').nth(1)).toContainText('-10,100')
  await expect(chart.locator('text').filter({ hasText: /^S0$/ })).toBeVisible()
  await expect(flow).toContainText('Local net = total net − foreign net')
  await expect(page.getByTestId('score-flow')).toHaveText(initialFlowScore!)
  expect(calls).toHaveLength(initialCalls)

  await flow.getByRole('button', { name: '5D', exact: true }).click()
  await expect(flow.getByText('5 observed trading days')).toBeVisible()
  await expect(filter.getByRole('button', { name: 'Local' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(table.getByRole('row').nth(1)).toContainText('+19,900')
  expect(calls).toHaveLength(initialCalls + 1)

  await filter.getByRole('button', { name: 'All investors' }).click()
  await expect(table.getByRole('row').nth(1)).toContainText('+20,000')
  await expect(page.getByText('Broker trading values · IDR')).toHaveCount(0)
  const volume = flow.getByRole('heading', { name: 'Daily volume' }).locator('..')
  await expect(volume.getByRole('columnheader', { name: 'Prior average' })).toHaveCount(0)
  await expect(volume.getByRole('columnheader', { name: 'Earlier observations' })).toHaveCount(0)
  expect(calls).toHaveLength(initialCalls + 1)
})

test('ticker syntax is enforced before a backend request', async ({ page }) => {
  const calls: string[] = []
  page.on('request', (request) => {
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

test('themes preserve research state, recolor charts, and survive reload', async ({
  page,
}, testInfo) => {
  const calls: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/stocks/BBCA/intel-score')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await expect(page.locator('html')).toHaveCSS('color-scheme', 'light only')
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(237, 243, 250)')
  await expect(page.getByText('Test response company')).toBeVisible()
  await expect(page.getByText('Up +1 (+0.09%)')).toBeVisible()
  const chart = page.getByRole('img', { name: /brokers paired by rank/ })
  const buyer = chart.locator('text').filter({ hasText: /^B0$/ })
  const seller = chart.locator('text').filter({ hasText: /^S0$/ })
  await expect(buyer).toBeVisible()
  await expect(seller).toBeVisible()
  await expect(buyer).toHaveAttribute('fill', '#243247')
  await expect(buyer).toHaveCSS('fill', 'rgb(36, 50, 71)')
  const buyerBox = (await buyer.boundingBox())!
  const sellerBox = (await seller.boundingBox())!
  expect(
    Math.abs(buyerBox.x + buyerBox.width / 2 - (sellerBox.x + sellerBox.width / 2)),
  ).toBeLessThan(2)
  expect(buyerBox.y).toBeLessThan(sellerBox.y)
  const lightFill = await chart.locator('path[fill="#087652"]').count()
  expect(lightFill).toBeGreaterThan(0)
  await page.screenshot({ path: testInfo.outputPath('research-light.png'), fullPage: true })

  await page.getByRole('button', { name: '5D', exact: true }).click()
  await expect(page).toHaveURL(/window=5d/)
  await expect(page.getByText('5 observed trading days')).toBeVisible()
  await page.getByRole('combobox', { name: 'Color theme' }).selectOption('dark')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(11, 25, 43)')
  await expect(chart.locator('text').filter({ hasText: /^B0$/ })).toHaveAttribute('fill', '#edf1f8')
  await expect(chart.locator('text').filter({ hasText: /^B0$/ })).toHaveCSS(
    'fill',
    'rgb(237, 241, 248)',
  )
  await expect(
    page
      .getByRole('article', { name: 'Flow Score' })
      .getByText('Liquidity', { exact: false })
      .first(),
  ).toBeVisible()
  await expect(page).toHaveURL(/window=5d/)
  await expect(page.getByTestId('score-flow')).toContainText(String(testResponse.scores.flow.value))
  expect(calls).toHaveLength(3)
  await expect(chart.locator('path[fill="#65dab3"]').first()).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('research-dark.png'), fullPage: true })

  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByRole('combobox', { name: 'Color theme' })).toHaveValue('dark')
  await page.getByRole('combobox', { name: 'Color theme' }).selectOption('system')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.emulateMedia({ colorScheme: 'dark' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('research-mobile-dark.png'), fullPage: true })
  await page.getByRole('combobox', { name: 'Color theme' }).selectOption('light')
  await expect(page.locator('html')).toHaveCSS('color-scheme', 'light only')
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(237, 243, 250)')
  await expect(chart.locator('text').filter({ hasText: /^B0$/ })).toHaveAttribute('fill', '#243247')
  await expect(chart.locator('text').filter({ hasText: /^B0$/ })).toHaveCSS(
    'fill',
    'rgb(36, 50, 71)',
  )
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('research-mobile-light.png'), fullPage: true })
})

test('Home and error recovery work in both themes', async ({ page }, testInfo) => {
  await page.route('**/api/v1/stocks/NONE/intel-score', (route) =>
    route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ error: { message: 'No observations.', request_id: 'test-no-data' } }),
    }),
  )
  for (const theme of ['light', 'dark']) {
    await page.goto('/')
    await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
    await page.screenshot({ path: testInfo.outputPath('home-' + theme + '.png'), fullPage: true })
    await page.getByRole('textbox', { name: 'IDX symbol' }).fill('NONE')
    await page.getByRole('button', { name: 'Open IntelScore' }).click()
    await expect(page.getByRole('heading', { name: 'No data found' })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('error-' + theme + '.png') })
    await page.getByRole('textbox', { name: 'IDX symbol' }).fill('BBCA')
    await page.getByRole('button', { name: 'Open IntelScore' }).click()
    await expect(page.getByText('Test response company')).toBeVisible()
  }
})

test('partial and stale evidence stays understandable in both themes', async ({
  page,
}, testInfo) => {
  const partial = structuredClone(testResponse)
  partial.status = 'partial'
  partial.sources[0].is_stale = true
  partial.company.change_idr = null
  partial.company.change_percent = null
  partial.scores.flow.value = null
  partial.scores.flow.reason = 'Foreign flow covers 19 of 20 trading dates. Missing: 2026-09-21.'
  partial.scores.combined.value = null
  partial.scores.combined.reason = 'Flow score unavailable'
  partial.missing_inputs = [{ key: 'foreign_flow', reason: partial.scores.flow.reason }]
  await page.route('**/api/v1/stocks/BBCA/intel-score', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(partial) }),
  )
  await page.goto('/stocks/BBCA/intel-score')
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
    await expect(page.getByText('Some data is unavailable')).toBeVisible()
    await expect(page.getByText('Some sources need an update')).toBeVisible()
    await expect(page.getByText('Change unavailable')).toBeVisible()
    await expect(page.getByTestId('score-flow')).toHaveText('N/A')
    await expect(page.getByText(partial.scores.flow.reason, { exact: true }).first()).toBeVisible()
    await page.screenshot({
      path: testInfo.outputPath('partial-' + theme + '.png'),
      fullPage: true,
    })
  }
})

test('decision dashboard hierarchy, reporting footer and direct evidence work at all widths', async ({
  page,
}, testInfo) => {
  const calls: string[] = []
  page.on('request', (request) => {
    if (request.url().includes('/api/v1/')) calls.push(request.url())
  })
  await page.goto('/stocks/BBCA/intel-score')
  await expect(page.getByRole('heading', { name: 'Test response company' })).toBeVisible()
  const overall = page.getByRole('article', { name: 'Overall Score', exact: true })
  const flow = page.getByRole('article', { name: 'Flow Score' })
  const fundamental = page.getByRole('article', { name: 'Fundamental Score' })
  const a = (await overall.boundingBox())!,
    b = (await flow.boundingBox())!,
    c = (await fundamental.boundingBox())!
  expect(a.x).toBeLessThan(b.x)
  expect(Math.abs(a.y - b.y)).toBeLessThan(2)
  expect(Math.abs(b.x - c.x)).toBeLessThan(2)
  expect(c.y).toBeGreaterThan(b.y + b.height)
  expect(Math.abs(a.y + a.height - c.y - c.height)).toBeLessThan(2)
  await expect(overall.getByText(/vs\. 1 week ago|vs\. 1 month ago/)).toHaveCount(0)
  await expect(page.locator('details, summary, a[href^="#source"]')).toHaveCount(0)
  await expect(
    page.getByText(/draft-v|fundamentals\.capital_expenditure|What the evidence shows/),
  ).toHaveCount(0)
  await expect(page.getByRole('region', { name: 'Data attribution' })).toContainText(
    'Powered by SectorsAPI',
  )
  await expect(page.getByRole('table').first()).toBeVisible()
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 1000 })
    for (const theme of ['light', 'dark']) {
      await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      )
      if (width === 1440 || width === 390) {
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.screenshot({ path: testInfo.outputPath(`v2-${width}-${theme}.png`) })
      }
    }
  }
  expect(calls).toHaveLength(2)
})

test('change over time shows only a fixed three-month candlestick chart', async ({ page }) => {
  const calls: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/api/v1/')) calls.push(r.url())
  })
  await page.goto('/stocks/BBCA/intel-score')
  const trends = page.getByRole('region', { name: 'Change over time' })
  await expect(
    trends.getByRole('img', { name: /^Three-month share price candlesticks/ }),
  ).toBeVisible()
  await expect(trends.getByText('Share price · 3M')).toBeVisible()
  await expect(trends.getByText(/Daily foreign flow/)).toHaveCount(0)
  await expect(trends.getByText(/Buyer B1 ·|Seller S1 ·/)).toHaveCount(0)
  await expect(trends.getByRole('article', { name: 'Overall Score trend' })).toHaveCount(0)
  await expect(trends.getByRole('button', { name: /1M|3M/ })).toHaveCount(0)
  expect(calls.filter((c) => c.includes('price-history?range=3m'))).toHaveLength(1)
  expect(calls.filter((c) => c.includes('broker-series'))).toHaveLength(0)
  await expect(page.getByTestId('score-combined')).toContainText(
    String(testResponse.scores.combined.value),
  )
})

test('score text has readable contrast and labels in both themes', async ({ page }, testInfo) => {
  await page.goto('/stocks/BBCA/intel-score')
  await expect(page.getByTestId('score-combined')).toBeVisible()
  for (const theme of ['dark', 'light']) {
    await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
    const failures = await page
      .getByRole('region', { name: 'Research scores' })
      .evaluate((section) => {
        const canvas = document.createElement('canvas')
        canvas.width = canvas.height = 1
        const context = canvas.getContext('2d')!
        const rgba = (css: string) => {
          context.clearRect(0, 0, 1, 1)
          context.fillStyle = css
          context.fillRect(0, 0, 1, 1)
          return Array.from(context.getImageData(0, 0, 1, 1).data)
        }
        const luminance = (color: number[]) =>
          color
            .slice(0, 3)
            .map((n) => n / 255)
            .map((n) => (n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4))
            .reduce((sum, n, i) => sum + n * [0.2126, 0.7152, 0.0722][i], 0)
        const background = (element: Element | null): number[] => {
          if (!element) return [255, 255, 255]
          const c = rgba(getComputedStyle(element).backgroundColor)
          const a = c[3] / 255
          if (a === 1) return c
          const parent = background(element.parentElement)
          return c.slice(0, 3).map((v, i) => v * a + parent[i] * (1 - a))
        }
        return [...section.querySelectorAll('*')]
          .filter(
            (e) =>
              e instanceof HTMLElement &&
              [...e.childNodes].some((n) => n.nodeType === Node.TEXT_NODE && n.textContent?.trim()),
          )
          .flatMap((element) => {
            const style = getComputedStyle(element),
              text = luminance(rgba(style.color)),
              bg = luminance(background(element))
            const ratio = (Math.max(text, bg) + 0.05) / (Math.min(text, bg) + 0.05)
            return ratio < 4.5 || parseFloat(style.fontSize) < 14
              ? [{ text: element.textContent?.slice(0, 60), ratio, fontSize: style.fontSize }]
              : []
          })
      })
    expect(failures).toEqual([])
    await expect(page.getByRole('meter', { name: 'Foreign flow score' })).toHaveAttribute(
      'aria-valuetext',
      /Strong/,
    )
    await page
      .getByRole('region', { name: 'Research scores' })
      .screenshot({ path: testInfo.outputPath(`decision-scores-${theme}.png`) })
  }
})

test('every numeric component has a visible bar in light and dark themes', async ({ page }) => {
  const response = structuredClone(testResponse)
  const flowValues = [0, 55, 65]
  const fundamentalValues = [75, 62.7, null, 100]
  response.scores.flow.components.forEach((component: { value: number | null }, index: number) => {
    component.value = flowValues[index]
  })
  response.scores.fundamental.components.forEach(
    (component: { value: number | null }, index: number) => {
      component.value = fundamentalValues[index]
    },
  )
  await page.route('**/api/v1/stocks/BBCA/intel-score', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(response) }),
  )
  await page.goto('/stocks/BBCA/intel-score')
  const scores = page.getByRole('region', { name: 'Research scores' })
  await expect(scores.getByRole('meter', { name: 'Earnings score' })).toHaveAttribute(
    'aria-valuenow',
    '62.7',
  )
  await expect(scores.getByRole('img', { name: 'Cash flow score' })).toHaveAttribute(
    'aria-valuetext',
    'Unavailable',
  )

  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
    const expectedFill = theme === 'light' ? 'rgb(36, 89, 181)' : 'rgb(156, 191, 255)'
    const bars = await scores.getByRole('meter').evaluateAll((nodes) =>
      nodes.map((node) => {
        const fill = node.firstElementChild as HTMLElement
        const track = node as HTMLElement
        return {
          value: Number(node.getAttribute('aria-valuenow')),
          band: node.getAttribute('aria-valuetext'),
          fillColor: getComputedStyle(fill).backgroundColor,
          trackColor: getComputedStyle(track).backgroundColor,
          width: fill.getBoundingClientRect().width,
          trackWidth: track.getBoundingClientRect().width,
          height: fill.getBoundingClientRect().height,
        }
      }),
    )
    expect(bars).toHaveLength(6)
    for (const bar of bars) {
      expect(bar.fillColor, bar.band ?? undefined).toBe(expectedFill)
      expect(bar.fillColor, bar.band ?? undefined).not.toBe(bar.trackColor)
      expect(bar.fillColor, bar.band ?? undefined).not.toBe('rgba(0, 0, 0, 0)')
      expect(bar.height, bar.band ?? undefined).toBeGreaterThan(0)
      expect(bar.width, bar.band ?? undefined).toBeGreaterThanOrEqual(4)
      if (bar.value > 0) expect(bar.width / bar.trackWidth).toBeCloseTo(bar.value / 100, 1)
    }
  }
})

test('period button boundaries remain readable in light and dark themes', async ({ page }) => {
  await page.goto('/stocks/BBCA/intel-score')
  const trends = page.getByRole('region', { name: 'Change over time' })
  const flow = page.getByRole('region', { name: 'Flow activity' })
  await expect(trends).toBeVisible()
  await expect(flow).toBeVisible()
  const assertPeriodContrast = async () => {
    const states = await page.locator('button[aria-pressed]').evaluateAll((buttons) => {
      const canvas = document.createElement('canvas')
      canvas.width = canvas.height = 1
      const context = canvas.getContext('2d')!
      const rgba = (css: string) => {
        context.clearRect(0, 0, 1, 1)
        context.fillStyle = css
        context.fillRect(0, 0, 1, 1)
        return Array.from(context.getImageData(0, 0, 1, 1).data)
      }
      const luminance = (color: number[]) =>
        color
          .slice(0, 3)
          .map((n) => n / 255)
          .map((n) => (n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4))
          .reduce((sum, n, i) => sum + n * [0.2126, 0.7152, 0.0722][i], 0)
      return buttons.map((button) => {
        const style = getComputedStyle(button)
        const foreground = luminance(rgba(style.color)),
          background = luminance(rgba(style.backgroundColor))
        return {
          label: button.textContent,
          pressed: button.getAttribute('aria-pressed') === 'true',
          ratio:
            (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05),
          background: style.backgroundColor,
          border: style.borderTopColor,
        }
      })
    })
    expect(states.length).toBeGreaterThanOrEqual(6)
    for (const state of states) {
      expect(state.background, state.label ?? undefined).not.toBe('rgba(0, 0, 0, 0)')
      if (!state.pressed) expect(state.border, state.label ?? undefined).not.toBe(state.background)
      expect(state.ratio, state.label ?? undefined).toBeGreaterThanOrEqual(4.5)
    }
  }
  for (const theme of ['light', 'dark']) {
    await page.getByRole('combobox', { name: 'Color theme' }).selectOption(theme)
    await assertPeriodContrast()
    await flow.getByRole('button', { name: '5D', exact: true }).click()
    await expect(flow.getByText('5 observed trading days')).toBeVisible()
    await assertPeriodContrast()
  }
})

test('missing price history leaves scores intact and shows no fabricated chart', async ({
  page,
}) => {
  await page.route('**/api/v1/stocks/BBCA/price-history?range=3m', (r) =>
    r.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { message: 'Test unavailable' } }),
    }),
  )
  await page.goto('/stocks/BBCA/intel-score')
  await expect(page.getByText('Price history unavailable', { exact: true })).toBeVisible()
  await expect(page.getByTestId('score-combined')).toContainText(
    String(testResponse.scores.combined.value),
  )
})
