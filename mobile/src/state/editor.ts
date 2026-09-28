import { create } from 'zustand'

// Transient editing state for the garden screen; server data lives in TanStack Query.
interface EditorState {
  year: number
  selectedBedId: number | null
  layoutMode: boolean
  setYear: (year: number) => void
  selectBed: (bedId: number | null) => void
  setLayoutMode: (on: boolean) => void
}

export const useEditor = create<EditorState>((set) => ({
  year: new Date().getFullYear(),
  selectedBedId: null,
  layoutMode: false,
  setYear: (year) => set({ year }),
  selectBed: (selectedBedId) => set({ selectedBedId }),
  setLayoutMode: (layoutMode) => set({ layoutMode }),
}))
