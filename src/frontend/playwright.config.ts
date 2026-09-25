import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e', outputDir: './test-results/browser', fullyParallel: false, workers: 1,
  use: { ...devices['Desktop Chrome'], channel: process.env.PLAYWRIGHT_CHANNEL, baseURL: 'http://127.0.0.1:5173', viewport: { width: 1440, height: 1024 }, trace: 'retain-on-failure' },
})
