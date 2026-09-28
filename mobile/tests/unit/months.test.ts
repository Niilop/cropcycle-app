import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  fromIndex,
  segmentInYear,
  toIndex,
  touchesYear,
  windowFromMonths,
} from '../../src/lib/months.ts'

test('year-month index round trip', () => {
  assert.equal(fromIndex(toIndex('2026-10')), '2026-10')
  assert.equal(toIndex('2027-01') - toIndex('2026-12'), 1)
})

test('segments clip cross-year windows to the shown year', () => {
  assert.deepEqual(segmentInYear('2026-04', '2026-06', 2026), {
    from: 3,
    to: 5,
    before: false,
    after: false,
  })
  // Autumn-planted garlic seen from each year.
  assert.deepEqual(segmentInYear('2026-10', '2027-07', 2026), {
    from: 9,
    to: 11,
    before: false,
    after: true,
  })
  assert.deepEqual(segmentInYear('2026-10', '2027-07', 2027), {
    from: 0,
    to: 6,
    before: true,
    after: false,
  })
  assert.equal(segmentInYear('2026-10', '2027-07', 2028), null)
  assert.ok(touchesYear('2026-10', '2027-07', 2027))
  assert.ok(!touchesYear('2026-10', '2027-07', 2025))
})

test('an earlier end month ends the next year', () => {
  assert.deepEqual(windowFromMonths(2026, 10, 7), { start: '2026-10', end: '2027-07' })
  assert.deepEqual(windowFromMonths(2027, 4, 6), { start: '2027-04', end: '2027-06' })
})
