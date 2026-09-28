import { create } from 'zustand'

import { getItem, setItem } from '@/lib/storage'

const KEY = 'cropcycle.preferences'

export type LocalePreference = 'auto' | 'en' | 'fi'

interface Stored {
  locale: LocalePreference
  gardenId: number | null
}

interface PreferencesState extends Stored {
  ready: boolean
  hydrate: () => Promise<void>
  setLocale: (locale: LocalePreference) => void
  setGardenId: (gardenId: number | null) => void
}

const defaults: Stored = { locale: 'auto', gardenId: null }

function persist(state: Stored): void {
  void setItem(KEY, JSON.stringify({ locale: state.locale, gardenId: state.gardenId }))
}

export const usePreferences = create<PreferencesState>((set, get) => ({
  ...defaults,
  ready: false,
  async hydrate() {
    let stored: Partial<Stored> = {}
    try {
      stored = JSON.parse((await getItem(KEY)) ?? '{}') as Partial<Stored>
    } catch {
      stored = {}
    }
    set({
      locale: ['auto', 'en', 'fi'].includes(stored.locale ?? '') ? stored.locale! : 'auto',
      gardenId: typeof stored.gardenId === 'number' ? stored.gardenId : null,
      ready: true,
    })
  },
  setLocale(locale) {
    set({ locale })
    persist(get())
  },
  setGardenId(gardenId) {
    set({ gardenId })
    persist(get())
  },
}))
