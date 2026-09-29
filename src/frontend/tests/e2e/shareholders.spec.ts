import { test, expect } from '@playwright/test'

const year = Number(
  new Intl.DateTimeFormat('en-US', { year: 'numeric', timeZone: 'Asia/Jakarta' }).format(
    new Date(),
  ),
)
const response = {
  symbol: 'BBCA',
  as_of: `${year}-08-31`,
  status: 'complete',
  sources: [],
  missing_inputs: [],
  year,
  supported_years: [year - 2, year - 1, year],
  categories: [
    { key: 'corporate_l', label: 'Corporate Local' },
    { key: 'corporate_f', label: 'Corporate Foreign' },
    { key: 'individual_l', label: 'Individual Local' },
    { key: 'individual_f', label: 'Individual Foreign' },
    { key: 'mutual_fund_l', label: 'Mutual Fund Local' },
    { key: 'mutual_fund_f', label: 'Mutual Fund Foreign' },
  ],
  series: [
    {
      date: `${year}-07-31`,
      shares_number: 120,
      holdings: {
        corporate_l: 40,
        corporate_f: 10,
        individual_l: 50,
        individual_f: 10,
        mutual_fund_l: 5,
        mutual_fund_f: 5,
      },
      total_local: 95,
      total_foreign: 25,
      shareholder_count: 20,
      shareholder_count_change: 3,
    },
    {
      date: `${year}-08-31`,
      shares_number: 120,
      holdings: {
        corporate_l: 60,
        corporate_f: 10,
        individual_l: 20,
        individual_f: 20,
        mutual_fund_l: 5,
        mutual_fund_f: 5,
      },
      total_local: 85,
      total_foreign: 35,
      shareholder_count: 18,
      shareholder_count_change: -2,
    },
  ],
}

test('shareholder controls update both themes without exposing internal fields', async ({
  page,
}) => {
  await page.route('**/*', (route) =>
    ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)
      ? route.continue()
      : route.abort('blockedbyclient'),
  )
  let requests = 0
  await page.route('**/api/v1/**', (route) => {
    requests += 1
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    })
  })
  await page.goto('/shareholders/BBCA')
  const chart = page.getByRole('img', {
    name: /monthly all investor shareholder category holdings/i,
  })
  await expect(chart).toBeVisible()
  await expect(
    page.getByRole('complementary', { name: 'Shareholder category details' }),
  ).toContainText('Corporate')
  await page.screenshot({
    path: 'src/frontend/test-results/shareholders-light.png',
    fullPage: true,
  })
  await page
    .getByRole('group', { name: 'Investor origin' })
    .getByRole('button', { name: 'Foreign' })
    .click()
  await page
    .getByRole('group', { name: 'Bar chart view' })
    .getByRole('button', { name: 'Composition %' })
    .click()
  await expect(
    page.getByRole('img', {
      name: /monthly foreign investor shareholder category composition percentages/i,
    }),
  ).toBeVisible()
  await expect(
    page
      .getByRole('group', { name: 'Bar chart view' })
      .getByRole('button', { name: 'Composition %' }),
  ).toHaveAttribute('aria-pressed', 'true')
  await expect(
    page.getByRole('complementary', { name: 'Shareholder category details' }),
  ).toContainText('Foreign holdings by category')
  await expect(
    page.getByRole('heading', { name: 'Shareholder count by month' }).locator('..').locator('..'),
  ).toContainText('Change vs prior month: -2')
  await page.getByRole('combobox', { name: 'Color theme' }).selectOption('dark')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(
    page.getByRole('img', {
      name: /monthly foreign investor shareholder category composition percentages/i,
    }),
  ).toBeVisible()
  await page.screenshot({ path: 'src/frontend/test-results/shareholders-dark.png', fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(await page.locator('body').innerText()).not.toMatch(
    /corporate_f|request_id|fetched_at|SECTORS_API_KEY/i,
  )
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(requests).toBe(1)
})

test('shareholder search and historical year remain independent of IntelScore', async ({
  page,
}) => {
  await page.route('**/*', (route) =>
    ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)
      ? route.continue()
      : route.abort('blockedbyclient'),
  )
  const requests: string[] = []
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    requests.push(url.pathname + url.search)
    const requestedYear = Number(url.searchParams.get('year'))
    const historical = requestedYear === year - 1
    const data = {
      ...response,
      symbol: 'SINI',
      year: requestedYear,
      as_of: `${requestedYear}-08-31`,
      status: historical ? 'partial' : 'complete',
      missing_inputs: historical
        ? [{ key: 'shareholders.count', reason: 'Counts unavailable' }]
        : [],
      series: response.series.map((point) => ({
        ...point,
        date: point.date.replace(`${year}-`, `${requestedYear}-`),
        shareholder_count: historical ? null : point.shareholder_count,
        shareholder_count_change: historical ? null : point.shareholder_count_change,
      })),
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data),
    })
  })
  await page.goto('/shareholders')
  await expect(page.getByRole('heading', { name: /Which company's shareholders/ })).toBeVisible()
  expect(requests).toHaveLength(0)
  await page.getByRole('textbox', { name: 'Shareholder IDX symbol' }).fill('SINI')
  await page.getByRole('button', { name: 'Open Shareholders' }).click()
  await expect(page).toHaveURL(/\/shareholders\/SINI$/)
  await expect(page.getByRole('heading', { name: 'Reported holdings by category' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Shareholder year' }).selectOption(String(year - 1))
  await expect(
    page.getByRole('img', { name: /monthly all investor shareholder category holdings/i }),
  ).toBeVisible()
  await expect(
    page.getByText(
      `Shareholder counts were not reported for ${year - 1}. Category holdings remain available above.`,
    ),
  ).toBeVisible()
  expect(requests).toEqual([
    `/api/v1/stocks/SINI/shareholders?year=${year}`,
    `/api/v1/stocks/SINI/shareholders?year=${year - 1}`,
  ])
  await page.getByRole('link', { name: 'IntelScore' }).click()
  await expect(page).toHaveURL(/\/intel-score$/)
  await expect(
    page.getByRole('heading', { name: 'Which company are you researching?' }),
  ).toBeVisible()
  expect(requests).toHaveLength(2)
})

test('missing shareholder dataset has an empty state instead of a service error', async ({
  page,
}) => {
  await page.route('**/*', (route) =>
    ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)
      ? route.continue()
      : route.abort('blockedbyclient'),
  )
  await page.route('**/api/v1/**', (route) => {
    if (
      route
        .request()
        .url()
        .includes(`year=${year - 1}`)
    )
      return route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'DATA_NOT_FOUND', message: 'No data' } }),
      })
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    })
  })
  await page.goto('/shareholders/BBCA')
  await expect(page.getByRole('heading', { name: 'Reported holdings by category' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Shareholder year' }).selectOption(String(year - 1))
  await expect(
    page.getByRole('heading', { name: `No shareholder snapshots for BBCA in ${year - 1}` }),
  ).toBeVisible()
  await expect(page.getByText('Shareholder data is unavailable')).toHaveCount(0)
})
