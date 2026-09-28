import { randomUUID } from 'node:crypto'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import type { Garden, Token } from '../src/api/types'

const password = 'smoke-test-password-123'

async function register(page: Page, username: string) {
  await page.goto('/register')
  await page.getByLabel('Email', { exact: true }).fill(`${username}@example.com`)
  await page.getByLabel('Username', { exact: true }).fill(username)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Create account', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
}

async function signIn(page: Page, username: string) {
  await page.getByLabel('Email or username').fill(username)
  await page.getByLabel('Password', { exact: true }).fill(password)
  const login = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/auth/login',
  )
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  const response = await login
  expect(response.status()).toBe(200)
  const token: Token = await response.json()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  return { Authorization: `Bearer ${token.access_token}` }
}

test('real registration, login, persistence, ownership and garden planning API', async ({
  page,
}) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  const username = `smoke-${randomUUID()}`
  const ready = await page.request.get('/api/ready')
  expect(ready.status()).toBe(200)
  await register(page, username)
  const ownerHeaders = await signIn(page, username)
  await page.getByRole('link', { name: 'Gardens', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No gardens yet' })).toBeVisible()
  await page.getByLabel('Name', { exact: true }).fill('Smoke allotment')
  const creation = page.waitForResponse(
    (response) =>
      new URL(response.url()).pathname === '/api/gardens' && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Create garden' }).click()
  const created = await creation
  expect(created.status()).toBe(201)
  const garden: Garden = await created.json()
  await expect(page.getByRole('status')).toHaveText('Garden created.')

  // The seeded catalogue and domain API work through Nginx and PostgreSQL.
  const crops = await page.request.get('/api/crops', { headers: ownerHeaders })
  expect(crops.status()).toBe(200)
  const garlic = (await crops.json()).find((crop: { slug: string }) => crop.slug === 'garlic')
  expect(garlic.names.fi).toContain('Valkosipuli')
  const bed = await page.request.post(`/api/gardens/${garden.id}/beds`, {
    headers: ownerHeaders,
    data: { name: 'Bed A', x: 0, y: 0, width: 1.2, height: 4 },
  })
  expect(bed.status()).toBe(201)
  const bedId = (await bed.json()).id
  const planting = await page.request.post(`/api/beds/${bedId}/plantings`, {
    headers: ownerHeaders,
    data: { crop_id: garlic.id, year: 2026 },
  })
  expect(planting.status()).toBe(201)
  expect(await planting.json()).toMatchObject({ start_month: '2025-10', end_month: '2026-07' })
  const plan = await page.request.post('/api/plans', {
    headers: ownerHeaders,
    data: { garden_id: garden.id, year: 2027 },
  })
  expect(plan.status()).toBe(201)
  const planId = (await plan.json()).id
  const placement = await page.request.post(`/api/plans/${planId}/placements`, {
    headers: ownerHeaders,
    data: { bed_id: bedId, crop_id: garlic.id },
  })
  expect(placement.status()).toBe(201)
  expect(await placement.json()).toMatchObject({ locked: true, source: 'manual' })
  const carrot = (await crops.json()).find((crop: { slug: string }) => crop.slug === 'carrot')
  const secondBed = await page.request.post(`/api/gardens/${garden.id}/beds`, {
    headers: ownerHeaders,
    data: { name: 'Bed B', x: 3, y: 0, width: 1.2, height: 4 },
  })
  expect(secondBed.status()).toBe(201)
  const requested = await page.request.post(`/api/plans/${planId}/crops`, {
    headers: ownerHeaders,
    data: { crop_id: carrot.id, quantity: 1 },
  })
  expect(requested.status()).toBe(201)
  const suitability = await page.request.get(
    `/api/plans/${planId}/suitability?crop_id=${carrot.id}`,
    {
      headers: ownerHeaders,
    },
  )
  expect(suitability.status()).toBe(200)
  expect(await suitability.json()).toHaveLength(2)
  const layout = await page.request.post(`/api/plans/${planId}/generate-layout`, {
    headers: ownerHeaders,
  })
  expect(layout.status()).toBe(200)
  const generated = await layout.json()
  expect(generated.unplaced).toEqual([])
  expect(generated.plan.placements).toHaveLength(2)
  expect(generated.plan.placements[1]).toMatchObject({
    crop_id: carrot.id,
    bed_id: (await secondBed.json()).id,
    source: 'suggested',
    locked: false,
  })

  // A new page/session must load the saved record from the real API.
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  await signIn(page, username)
  await expect(page.getByRole('listitem').filter({ hasText: 'Smoke allotment' })).toBeVisible()

  await page.getByRole('button', { name: 'Sign out' }).click()
  const otherName = `other-${randomUUID()}`
  await register(page, otherName)
  const otherHeaders = await signIn(page, otherName)
  await page.getByRole('link', { name: 'Gardens', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'No gardens yet' })).toBeVisible()
  const gardenPath = `/api/gardens/${garden.id}`
  expect((await page.request.get(gardenPath)).status()).toBe(401)
  for (const path of [gardenPath, `/api/beds/${bedId}/plantings`, `/api/plans/${planId}`]) {
    expect((await page.request.get(path, { headers: otherHeaders })).status()).toBe(404)
  }
  const rename = await page.request.put(gardenPath, {
    headers: otherHeaders,
    data: { name: 'Unauthorized edit' },
  })
  expect(rename.status()).toBe(404)
  const stored = await page.request.get(gardenPath, { headers: ownerHeaders })
  expect(stored.status()).toBe(200)
  const storedGarden = await stored.json()
  expect(storedGarden.name).toBe('Smoke allotment')
  expect(storedGarden.beds.map((bed: { id: number }) => bed.id)).toContain(bedId)

  expect((await page.request.delete(gardenPath, { headers: ownerHeaders })).status()).toBe(204)
  expect((await page.request.get(gardenPath, { headers: ownerHeaders })).status()).toBe(404)
  expect(errors).toEqual([])
})
