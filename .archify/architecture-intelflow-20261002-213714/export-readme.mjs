import { chromium } from 'playwright'
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'

const pagePath = resolve('.archify/architecture-intelflow-20261002-213714/intelflow-architecture-v2.html')
const browser = await chromium.launch({
  executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  headless: true,
  args: ['--disable-gpu'],
})

try {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, acceptDownloads: true })
  await page.goto(pathToFileURL(pagePath).href)
  for (const [format, destination] of [
    ['svg', 'static/intelflow-architecture.svg'],
    ['png', '.archify/architecture-intelflow-20261002-213714/diagram-preview.png'],
  ]) {
    await page.locator('#btn-export').click()
    const download = page.waitForEvent('download')
    await page.locator(`button[data-format="${format}"]`).click()
    await (await download).saveAs(resolve(destination))
  }
} finally {
  await browser.close()
}
