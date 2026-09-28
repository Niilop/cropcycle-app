import { defineConfig, devices } from '@playwright/test'

const port = 18082

// Tests run against the exported web build with a fake API (e2e/fake-api.ts).
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: !!process.env.CI,
  reporter: 'list',
  use: { baseURL: `http://localhost:${port}`, trace: 'retain-on-failure', locale: 'en-US' },
  projects: [
    {
      name: 'tablet',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1180, height: 820 } },
    },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: `npm run export:test && node e2e/serve.mjs ${port} dist-test`,
    url: `http://localhost:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
  },
})
