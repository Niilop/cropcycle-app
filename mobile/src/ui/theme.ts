export const colors = {
  background: '#F5F6F0',
  surface: '#FFFFFF',
  soil: '#EDE4D3',
  text: '#1E2A1F',
  muted: '#5A6A5B',
  border: '#D5DCCD',
  primary: '#2E6B3A',
  primaryText: '#FFFFFF',
  primarySoft: '#E3EFE2',
  selected: '#D9942B',
  danger: '#A3402F',
  dangerSoft: '#F7E6E2',
  grid: '#E4E8DD',
}

// Bed fill per crop family: a display aid only, not an agronomic rule.
const familyPalette = [
  '#CFE3C0',
  '#F2D4A7',
  '#C9DDF0',
  '#EFC9C3',
  '#DCD2EE',
  '#F4E3A1',
  '#C4E6DE',
  '#E8D0B8',
  '#D6E6A8',
  '#F0CFE0',
]

export function familyColor(familyId: number | undefined): string {
  return familyId === undefined ? colors.soil : familyPalette[familyId % familyPalette.length]
}

export const space = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 }
export const radius = { sm: 6, md: 10, lg: 16 }
// Large touch targets for garden use (≥ 48 dp).
export const touch = 48
export const WIDE_BREAKPOINT = 900
