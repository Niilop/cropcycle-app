import type { Page, Route } from '@playwright/test'

// In-memory stand-in for the CropCycle API, so browser tests need no backend or database.
// The app is exported with EXPO_PUBLIC_API_URL=http://api.test (see playwright.config.ts).
export const API = 'http://api.test'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Authorization, Content-Type, Accept',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
}

const families = [
  { id: 1, slug: 'solanaceae', names: { en: 'Nightshade family', fi: 'Koisokasvit' } },
  { id: 2, slug: 'amaryllidaceae', names: { en: 'Onion family', fi: 'Laukkakasvit' } },
  { id: 3, slug: 'apiaceae', names: { en: 'Carrot family', fi: 'Sarjakukkaiskasvit' } },
]
const crops = [
  {
    id: 1,
    slug: 'potato',
    names: { en: 'Potato', fi: 'Peruna' },
    family_id: 1,
    default_start_month: 5,
    default_end_month: 9,
    default_start_year_offset: 0,
  },
  {
    id: 2,
    slug: 'garlic',
    names: { en: 'Garlic', fi: 'Valkosipuli' },
    family_id: 2,
    default_start_month: 10,
    default_end_month: 7,
    default_start_year_offset: -1,
  },
  {
    id: 3,
    slug: 'carrot',
    names: { en: 'Carrot', fi: 'Porkkana' },
    family_id: 3,
    default_start_month: 5,
    default_end_month: 9,
    default_start_year_offset: 0,
  },
]

interface Bed {
  id: number
  garden_id: number
  name: string
  x: number
  y: number
  width: number
  height: number
  archived_at: string | null
}
interface Planting {
  id: number
  bed_id: number
  crop_id: number
  year: number
  start_month: string
  end_month: string
  coverage: number
  plan_id: null
}

const ym = (year: number, month: number) => `${year}-${String(month).padStart(2, '0')}`

export class FakeApi {
  user = {
    id: 1,
    email: 'grower@example.com',
    username: 'grower',
    created_at: '2026-01-01T00:00:00Z',
    settings: {},
  }
  password = 'a-long-test-password'
  registered = false
  gardens: { id: number; name: string; created_at: string; updated_at: string }[] = []
  beds: Bed[] = []
  plantings: Planting[] = []
  requests: string[] = []
  failNext: string | null = null
  private nextId = 1

  async install(page: Page) {
    await page.route(`${API}/**`, (route) => this.handle(route))
  }

  private async handle(route: Route) {
    const request = route.request()
    const method = request.method()
    if (method === 'OPTIONS') return route.fulfill({ status: 204, headers: cors })
    const url = new URL(request.url())
    const path = url.pathname
    this.requests.push(`${method} ${path}`)
    const reply = (status: number, json?: unknown) =>
      route.fulfill({
        status,
        headers: cors,
        contentType: 'application/json',
        body: json === undefined ? '' : JSON.stringify(json),
      })
    if (this.failNext && path.startsWith(this.failNext)) {
      this.failNext = null
      return route.abort('failed')
    }
    const body = () => request.postDataJSON()
    const id = () => this.nextId++
    const now = '2026-01-01T00:00:00Z'

    if (path === '/auth/register' && method === 'POST') {
      this.registered = true
      return reply(201, this.user)
    }
    if (path === '/auth/login' && method === 'POST') {
      const form = new URLSearchParams(request.postData() ?? '')
      return form.get('password') === this.password
        ? reply(200, { access_token: 'test-token', token_type: 'bearer' })
        : reply(401, { detail: 'Invalid credentials' })
    }
    if (request.headers().authorization !== 'Bearer test-token') {
      return reply(401, { detail: 'Invalid or expired token' })
    }
    if (path === '/auth/me') return reply(200, this.user)
    if (path === '/crops') return reply(200, crops)
    if (path === '/crop-families') return reply(200, families)
    if (path === '/gardens' && method === 'GET') return reply(200, this.gardens)
    if (path === '/gardens' && method === 'POST') {
      const garden = { id: id(), name: body().name, created_at: now, updated_at: now }
      this.gardens.push(garden)
      return reply(201, garden)
    }
    let match = /^\/gardens\/(\d+)$/.exec(path)
    if (match) {
      const garden = this.gardens.find((g) => g.id === Number(match![1]))
      if (!garden) return reply(404, { detail: 'Garden not found' })
      const all = url.searchParams.get('include_archived') === 'true'
      return reply(200, {
        ...garden,
        beds: this.beds.filter((b) => b.garden_id === garden.id && (all || !b.archived_at)),
      })
    }
    match = /^\/gardens\/(\d+)\/beds$/.exec(path)
    if (match && method === 'POST') {
      const bed: Bed = { id: id(), garden_id: Number(match[1]), archived_at: null, ...body() }
      this.beds.push(bed)
      return reply(201, bed)
    }
    match = /^\/gardens\/(\d+)\/plantings$/.exec(path)
    if (match) {
      const bedIds = new Set(
        this.beds.filter((b) => b.garden_id === Number(match![1])).map((b) => b.id),
      )
      return reply(
        200,
        this.plantings.filter((p) => bedIds.has(p.bed_id)),
      )
    }
    match = /^\/beds\/(\d+)$/.exec(path)
    if (match) {
      const bed = this.beds.find((b) => b.id === Number(match![1]))
      if (!bed) return reply(404, { detail: 'Bed not found' })
      if (method === 'PUT') Object.assign(bed, body())
      if (method === 'DELETE') {
        bed.archived_at = now
        return reply(204)
      }
      return reply(200, bed)
    }
    match = /^\/beds\/(\d+)\/plantings$/.exec(path)
    if (match && method === 'POST') {
      const planting = this.planting(Number(match[1]), body())
      this.plantings.push(planting)
      return reply(201, planting)
    }
    match = /^\/plantings\/(\d+)$/.exec(path)
    if (match) {
      const index = this.plantings.findIndex((p) => p.id === Number(match![1]))
      if (index < 0) return reply(404, { detail: 'Planting not found' })
      if (method === 'DELETE') {
        this.plantings.splice(index, 1)
        return reply(204)
      }
      this.plantings[index] = {
        ...this.planting(this.plantings[index].bed_id, body()),
        id: this.plantings[index].id,
      }
      return reply(200, this.plantings[index])
    }
    return reply(404, { detail: 'Not found' })
  }

  private planting(
    bedId: number,
    body: { crop_id: number; year: number; start_month?: string; end_month?: string },
  ): Planting {
    const crop = crops.find((c) => c.id === body.crop_id)!
    let { start_month, end_month } = body
    if (!start_month || !end_month) {
      const startYear = body.year + crop.default_start_year_offset
      start_month = ym(startYear, crop.default_start_month)
      end_month = ym(
        startYear + (crop.default_end_month < crop.default_start_month ? 1 : 0),
        crop.default_end_month,
      )
    }
    return {
      id: this.nextId++,
      bed_id: bedId,
      crop_id: crop.id,
      year: body.year,
      start_month,
      end_month,
      coverage: 1,
      plan_id: null,
    }
  }
}
