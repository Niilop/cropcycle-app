import { getLocales } from 'expo-localization'
import { useMemo } from 'react'

import { ApiError } from '@/api/client'
import { format, localizedName, type Locale } from '@/lib/names'
import { usePreferences } from '@/state/preferences'

import { messages, type Messages } from './messages'

function deviceLocale(): Locale {
  try {
    return getLocales()[0]?.languageCode === 'fi' ? 'fi' : 'en'
  } catch {
    return 'en'
  }
}

export interface I18n {
  locale: Locale
  m: Messages
  f: typeof format
  name: (names: Record<string, string>) => string
  month: (month: number) => string
  errorText: (error: unknown) => string
}

export function useI18n(): I18n {
  const preference = usePreferences((state) => state.locale)
  const locale: Locale = preference === 'auto' ? deviceLocale() : preference
  return useMemo(() => {
    const m = messages[locale]
    return {
      locale,
      m,
      f: format,
      name: (names) => localizedName(names, locale),
      month: (month) => m.months[month - 1] ?? String(month),
      errorText: (error) => {
        if (error instanceof ApiError) {
          if (error.kind === 'network') return m.errors.network
          if (error.kind === 'timeout') return m.errors.timeout
          if (error.status < 500 && error.message) return error.message
        }
        return m.errors.generic
      },
    }
  }, [locale])
}
