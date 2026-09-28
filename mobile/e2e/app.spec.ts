import { expect, test, type Page } from '@playwright/test'

import { FakeApi } from './fake-api'

let api: FakeApi

test.beforeEach(async ({ page }) => {
  api = new FakeApi()
  await api.install(page)
})

async function register(page: Page) {
  await page.goto('/')
  await page.getByText('New here? Create an account').click()
  await page.getByLabel('Email', { exact: true }).fill('grower@example.com')
  await page.getByLabel('Username', { exact: true }).fill('grower')
  await page.getByLabel('Password', { exact: true }).fill(api.password)
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByText('Your gardens')).toBeVisible()
}

async function gardenWithBeds(page: Page, count: number) {
  await register(page)
  await page.getByLabel('Garden name').fill('Allotment')
  await page.getByRole('button', { name: 'Create garden' }).click()
  await expect(page.getByText('No beds yet. Add your first bed to start.')).toBeVisible()
  for (let i = 1; i <= count; i++) {
    await page.getByRole('button', { name: 'Add bed' }).first().click()
    await expect(page.getByRole('button', { name: new RegExp(`^Bed Bed ${i},`) })).toBeVisible()
  }
}

test('register, create a garden and record sequential and cross-year crops', async ({ page }) => {
  await gardenWithBeds(page, 2)
  expect(api.registered).toBe(true)

  await page.getByRole('button', { name: /^Bed Bed 1,/ }).click()
  await page.getByRole('button', { name: 'Add crop' }).click()
  await page.getByLabel('Search crops').fill('pot')
  await expect(page.getByRole('button', { name: 'Carrot', exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Potato', exact: true }).click()
  await expect(page.getByText('Typical: May – Sep')).toBeVisible()
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('button', { name: /^Bed Bed 1, Potato/ })).toBeVisible()
  expect(api.plantings[0]).toMatchObject({ start_month: '2026-05', end_month: '2026-09' })

  // A second crop in the same season, after the first, with chosen months.
  await page.getByRole('button', { name: 'Add crop' }).click()
  await page.getByRole('button', { name: 'Carrot', exact: true }).click()
  await page.getByRole('button', { name: 'Choose months' }).click()
  await page.getByRole('button', { name: 'Jul', exact: true }).first().click()
  await page.getByRole('button', { name: 'Oct', exact: true }).last().click()
  await expect(page.getByText('Jul – Oct', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('button', { name: /^Bed Bed 1, Potato, Carrot/ })).toBeVisible()
  expect(api.plantings[1]).toMatchObject({
    year: 2026,
    start_month: '2026-07',
    end_month: '2026-10',
  })

  // Autumn-planted garlic occupies the bed in both calendar years.
  await page.getByRole('button', { name: 'Close' }).click()
  await page.getByRole('button', { name: /^Bed Bed 2,/ }).click()
  await page.getByRole('button', { name: 'Add crop' }).click()
  await page.getByRole('button', { name: 'Garlic', exact: true }).click()
  await expect(page.getByText('Typical: Oct (previous year) – Jul')).toBeVisible()
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('button', { name: /^Bed Bed 2, Garlic/ })).toBeVisible()
  await page.getByRole('button', { name: 'Previous year' }).first().click()
  await expect(page.getByRole('button', { name: /^Bed Bed 2, Garlic/ })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Bed Bed 1, empty/ })).toBeVisible()

  // Edit and remove from the bed panel (remove asks for a second tap).
  await page.getByRole('button', { name: 'Next year' }).first().click()
  await page.getByRole('button', { name: /^Bed Bed 1,/ }).click()
  await page.getByRole('button', { name: 'Remove Carrot' }).click()
  expect(api.plantings).toHaveLength(3)
  await page.getByRole('button', { name: 'Remove Carrot' }).click()
  await expect(page.getByRole('button', { name: /^Bed Bed 1, Potato$/ })).toBeVisible()
  expect(api.plantings).toHaveLength(2)

  await page.getByText('History', { exact: true }).last().click()
  // Tabs stay mounted (the garden panel is behind this one); History renders last.
  await expect(page.getByText('Oct 2025 – Jul').last()).toBeVisible()
  await expect(page.getByText('May – Sep').last()).toBeVisible()
})

test('layout editing by dragging and by typing sizes', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'phone', 'Dragging is covered on the tablet layout.')
  await gardenWithBeds(page, 2)
  await page.getByRole('button', { name: 'Edit layout' }).click()
  const bed = page.getByTestId(/^bed-\d+$/).nth(1)
  const box = (await bed.boundingBox())!
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
  await page.mouse.down()
  await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 100, { steps: 8 })
  await page.mouse.up()
  await expect.poll(() => api.beds[1].y).toBeGreaterThan(0)
  expect(Number.isInteger(api.beds[1].y * 10)).toBe(true)

  // Tap-first alternative: select the bed and use the steppers.
  await page
    .getByTestId(/^bed-\d+$/)
    .nth(0)
    .click()
  await expect(page.getByText('Position and size')).toBeVisible()
  await page.getByRole('button', { name: 'Width (m) +' }).click()
  await expect.poll(() => api.beds[0].width).toBe(1.3)
  await page.getByLabel('Length (m)', { exact: true }).fill('2,5')
  await page.getByLabel('Length (m)', { exact: true }).press('Enter')
  await expect.poll(() => api.beds[0].height).toBe(2.5)

  await page.getByRole('button', { name: 'Remove bed' }).click()
  await page.getByRole('button', { name: 'Tap again to remove. Its history is kept.' }).click()
  await expect.poll(() => api.beds[0].archived_at).not.toBeNull()
  await expect(page.getByTestId(/^bed-\d+$/)).toHaveCount(1)
})

test('Finnish language and a session that survives reload', async ({ page }) => {
  await gardenWithBeds(page, 1)
  await page.getByText('Settings', { exact: true }).last().click()
  await page.getByRole('button', { name: 'Suomi' }).click()
  await expect(page.getByText('Kieli')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Kirjaudu ulos')).toBeVisible()
  await page.getByText('Puutarha', { exact: true }).last().click()
  await expect(page.getByRole('button', { name: 'Lisää penkki' }).first()).toBeVisible()

  await page.getByText('Asetukset', { exact: true }).last().click()
  await page.getByRole('button', { name: 'Kirjaudu ulos' }).click()
  await expect(page.getByText('Suunnittele, mitä kasvaa missäkin.')).toBeVisible()
})

test('expired sessions return to sign-in, and failed saves can be retried', async ({ page }) => {
  await gardenWithBeds(page, 1)

  api.failNext = '/beds/'
  await page.getByRole('button', { name: /^Bed Bed 1,/ }).click()
  await page.getByRole('button', { name: 'Add crop' }).click()
  await page.getByRole('button', { name: 'Potato', exact: true }).click()
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(
    page.getByText('Cannot reach the server. Check your connection and try again.'),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Save' }).click()
  await expect(page.getByRole('button', { name: /^Bed Bed 1, Potato/ })).toBeVisible()

  // The server rejects the stored token on the next start.
  api.password = 'changed-password-123'
  await page.route('http://api.test/auth/me', (route) =>
    route.fulfill({
      status: 401,
      headers: { 'Access-Control-Allow-Origin': '*' },
      json: { detail: 'Invalid or expired token' },
    }),
  )
  await page.reload()
  await expect(page.getByText('Plan what grows where.')).toBeVisible()
})
