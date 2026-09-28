import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  fitScale,
  freePosition,
  overlaps,
  snap,
  snapSize,
  viewExtent,
} from '../../src/lib/geometry.ts'

test('snapping to 0.1 m without float noise', () => {
  assert.equal(snap(1.23), 1.2)
  assert.equal(snap(0.1 + 0.2), 0.3)
  assert.equal(snap(-0.46), -0.5)
  assert.equal(snapSize(0.01), 0.2)
})

test('view extent covers beds with a margin and a minimum size', () => {
  assert.deepEqual(viewExtent([]), { x: 0, y: 0, width: 8, height: 5 })
  const extent = viewExtent([{ x: 2, y: 1, width: 10, height: 6 }])
  assert.deepEqual(extent, { x: 0, y: 0, width: 13, height: 8 })
  assert.equal(fitScale({ width: 1300, height: 400 }, extent), 50)
  assert.equal(fitScale({ width: 0, height: 400 }, extent), 0)
})

test('new beds go to the first free spot', () => {
  const size = { width: 1.2, height: 3 }
  assert.deepEqual(freePosition([], size), { x: 0, y: 0 })
  const beds = [{ x: 0, y: 0, width: 1.2, height: 3 }]
  const spot = freePosition(beds, size)
  assert.ok(!overlaps({ ...spot, ...size }, beds[0], 0.3))
  assert.deepEqual(spot, { x: 1.5, y: 0 })
})
