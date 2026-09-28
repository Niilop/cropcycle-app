// Bed geometry in metres (garden plane, origin top-left). Pure functions only.

export interface Rect {
  x: number
  y: number
  width: number
  height: number
}

export const SNAP_M = 0.1
export const MIN_BED_M = 0.2
const MIN_EXTENT = { width: 8, height: 5 }
const MARGIN_M = 1

/** Round to the 0.1 m grid without floating-point noise (e.g. 1.2000000002). */
export function snap(value: number): number {
  return Math.round(value / SNAP_M) / (1 / SNAP_M)
}

export function snapSize(value: number): number {
  return Math.max(MIN_BED_M, snap(value))
}

/** The garden area to show: all beds plus a margin, never smaller than a minimum extent. */
export function viewExtent(beds: Rect[]): Rect {
  if (!beds.length) return { x: 0, y: 0, ...MIN_EXTENT }
  const x = Math.min(0, ...beds.map((b) => b.x)) - (beds.some((b) => b.x < 0) ? MARGIN_M : 0)
  const y = Math.min(0, ...beds.map((b) => b.y)) - (beds.some((b) => b.y < 0) ? MARGIN_M : 0)
  const right = Math.max(...beds.map((b) => b.x + b.width)) + MARGIN_M
  const bottom = Math.max(...beds.map((b) => b.y + b.height)) + MARGIN_M
  return {
    x,
    y,
    width: Math.max(MIN_EXTENT.width, right - x),
    height: Math.max(MIN_EXTENT.height, bottom - y),
  }
}

/** Pixels per metre so that the extent fits the view. */
export function fitScale(view: { width: number; height: number }, extent: Rect): number {
  if (view.width <= 0 || view.height <= 0) return 0
  return Math.min(view.width / extent.width, view.height / extent.height)
}

export function overlaps(a: Rect, b: Rect, gap = 0): boolean {
  return (
    a.x < b.x + b.width + gap &&
    b.x < a.x + a.width + gap &&
    a.y < b.y + b.height + gap &&
    b.y < a.y + a.height + gap
  )
}

/** First free spot for a new bed, scanning rows left to right on a 0.5 m grid. */
export function freePosition(
  beds: Rect[],
  size: { width: number; height: number },
  rowWidth = 12,
): { x: number; y: number } {
  const step = 0.5
  for (let y = 0; y < 1000; y += step) {
    for (let x = 0; x + size.width <= Math.max(rowWidth, size.width); x += step) {
      const candidate = { x, y, ...size }
      if (!beds.some((bed) => overlaps(candidate, bed, 0.3))) return { x, y }
    }
  }
  return { x: 0, y: 0 }
}
