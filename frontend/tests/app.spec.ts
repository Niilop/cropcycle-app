import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const user = {
  id: 1,
  username: 'tester',
  email: 'tester@example.com',
  created_at: '2026-01-01T12:00:00Z',
  settings: {},
}
const garden = {
  id: 1,
  name: 'Allotment',
  created_at: '2026-01-01T12:00:00Z',
  updated_at: '2026-01-01T12:00:00Z',
}

async function mockApi(page: Page) {
  const gardens: (typeof garden)[] = []
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname
      const method = route.request().method()
      if (path === '/api/auth/login') {
        expect(route.request().postData()).toContain('username=tester')
        await route.fulfill({ json: { access_token: 'test-token', token_type: 'bearer' } })
      } else if (path === '/api/auth/register') {
        expect(route.request().postDataJSON()).toMatchObject({
          email: user.email,
          username: user.username,
        })
        await route.fulfill({ status: 201, json: user })
      } else {
        expect(route.request().headers().authorization).toBe('Bearer test-token')
        if (path === '/api/auth/me') await route.fulfill({ json: user })
        else if (path === '/api/gardens' && method === 'GET') {
          await route.fulfill({ json: gardens })
        } else if (path === '/api/gardens' && method === 'POST') {
          const body = route.request().postDataJSON()
          expect(Object.keys(body)).toEqual(['name'])
          const created = { ...garden, ...body, id: gardens.length + 1 }
          gardens.push(created)
          await route.fulfill({ status: 201, json: created })
        } else await route.fulfill({ status: 404, json: { detail: 'Not found' } })
      }
    },
  )
}

async function signIn(page: Page) {
  await page.getByLabel('Email or username').fill('tester')
  await page.getByLabel('Password', { exact: true }).fill('a-long-test-password')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
}

test.beforeEach(async ({ page }) => {
  await mockApi(page)
})

test('overview and unknown routes', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Plan what grows where.' })).toBeVisible()
  await page.goto('/missing')
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible()
})

test('protected route, garden creation, account and sign out', async ({ page }) => {
  await page.goto('/gardens')
  await expect(page).toHaveURL(/\/login$/)
  await signIn(page)
  await expect(page).toHaveURL(/\/gardens$/)
  await expect(page.getByRole('heading', { name: 'No gardens yet' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Create garden' })).toBeDisabled()
  await page.getByLabel('Name', { exact: true }).fill('Allotment')
  await page.getByRole('button', { name: 'Create garden' }).click()
  await expect(page.getByRole('status')).toHaveText('Garden created.')
  await expect(page.getByRole('listitem').filter({ hasText: 'Allotment' })).toBeVisible()
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue('')
  await page.getByRole('link', { name: 'Account', exact: true }).click()
  await expect(page.getByText('tester@example.com', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/login$/)
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([])
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([])
})

test('registration and server validation errors', async ({ page }) => {
  await page.goto('/register')
  await page.getByLabel('Email', { exact: true }).fill(user.email)
  await page.getByLabel('Username', { exact: true }).fill(user.username)
  await page.getByLabel('Password', { exact: true }).fill('a-long-test-password')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('status')).toHaveText('Account created. You can now sign in.')
  await page.route('**/api/auth/login', (route) =>
    route.fulfill({
      status: 422,
      json: { detail: [{ loc: ['body', 'username'], msg: 'Invalid username' }] },
    }),
  )
  await signIn(page)
  await expect(page.getByRole('alert')).toHaveText('Invalid username')
})

test('expired credentials clear the session', async ({ page }) => {
  await page.goto('/login')
  await signIn(page)
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  await page.route('**/api/gardens', (route) =>
    route.fulfill({
      status: 401,
      json: { detail: 'Invalid or expired token' },
    }),
  )
  await page.getByRole('link', { name: 'Gardens', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('button', { name: 'Sign out' })).toHaveCount(0)
})

test('failed saves keep the draft and allow retry', async ({ page }) => {
  await page.goto('/gardens')
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'No gardens yet' })).toBeVisible()
  await page.getByLabel('Name', { exact: true }).fill('Keep my draft')
  let failure: 'network' | 'server' | null = 'network'
  await page.route('**/api/gardens', (route) => {
    if (route.request().method() !== 'POST' || !failure) return route.fallback()
    const current = failure
    failure = current === 'network' ? 'server' : null
    return current === 'network'
      ? route.abort()
      : route.fulfill({ status: 503, json: { detail: 'Please try again' } })
  })
  await page.getByRole('button', { name: 'Create garden' }).click()
  await expect(page.getByRole('alert')).toHaveText('Cannot reach the server. Please try again.')
  await page.getByRole('button', { name: 'Create garden' }).click()
  await expect(page.getByRole('alert')).toHaveText('Please try again')
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue('Keep my draft')
  await page.getByRole('button', { name: 'Create garden' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: 'Keep my draft' })).toBeVisible()
})
