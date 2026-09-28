// Year-month windows as exchanged with the API ("YYYY-MM"), see D012.
// Pure functions only: no React Native imports, so Node's test runner can load this file.

export type YearMonth = string

export function formatYearMonth(year: number, month: number): YearMonth {
  return `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`
}

export function parseYearMonth(value: YearMonth): { year: number; month: number } {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  if (!match) throw new Error(`Invalid year-month: ${value}`)
  return { year: Number(match[1]), month: Number(match[2]) }
}

export function toIndex(value: YearMonth): number {
  const { year, month } = parseYearMonth(value)
  return year * 12 + month - 1
}

export function fromIndex(index: number): YearMonth {
  return formatYearMonth(Math.floor(index / 12), (index % 12) + 1)
}

export function touchesYear(start: YearMonth, end: YearMonth, year: number): boolean {
  return parseYearMonth(start).year <= year && year <= parseYearMonth(end).year
}

export interface YearSegment {
  /** First and last month column (0–11) inside the year. */
  from: number
  to: number
  /** The window continues before January or after December. */
  before: boolean
  after: boolean
}

export function segmentInYear(start: YearMonth, end: YearMonth, year: number): YearSegment | null {
  const first = year * 12
  const last = first + 11
  const s = toIndex(start)
  const e = toIndex(end)
  if (e < first || s > last) return null
  return {
    from: Math.max(s, first) - first,
    to: Math.min(e, last) - first,
    before: s < first,
    after: e > last,
  }
}

/** A window from a start (year, month) to an end month; an earlier end month means next year. */
export function windowFromMonths(
  startYear: number,
  startMonth: number,
  endMonth: number,
): { start: YearMonth; end: YearMonth } {
  const endYear = endMonth < startMonth ? startYear + 1 : startYear
  return { start: formatYearMonth(startYear, startMonth), end: formatYearMonth(endYear, endMonth) }
}
