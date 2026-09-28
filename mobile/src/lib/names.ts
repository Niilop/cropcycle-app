export type Locale = 'en' | 'fi'

/** Catalogue names are stored per locale (D014); fall back to English. */
export function localizedName(names: Record<string, string>, locale: Locale): string {
  return names[locale] || names.en || Object.values(names)[0] || ''
}

export function format(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in params ? String(params[key]) : match,
  )
}
