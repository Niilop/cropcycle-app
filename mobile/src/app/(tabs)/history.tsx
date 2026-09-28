import { Redirect } from 'expo-router'
import { useMemo, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'

import { useCrops, useGarden, useGardenPlantings } from '@/api/queries'
import type { Planting } from '@/api/types'
import { useI18n } from '@/i18n'
import { parseYearMonth } from '@/lib/months'
import { usePreferences } from '@/state/preferences'
import { Chip, ErrorNotice, Loading, Muted } from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, familyColor, radius, space } from '@/ui/theme'

export default function HistoryScreen() {
  const gardenId = usePreferences((state) => state.gardenId)
  if (gardenId === null) return <Redirect href="/gardens" />
  return <History gardenId={gardenId} />
}

function History({ gardenId }: { gardenId: number }) {
  const { m, f, name, month, errorText } = useI18n()
  const [bedFilter, setBedFilter] = useState<number | null>(null)
  const garden = useGarden(gardenId)
  const plantings = useGardenPlantings(gardenId)
  const crops = useCrops()

  const bedsById = useMemo(
    () => new Map((garden.data?.beds ?? []).map((b) => [b.id, b])),
    [garden.data],
  )
  const cropsById = useMemo(() => new Map((crops.data ?? []).map((c) => [c.id, c])), [crops.data])
  const byYear = useMemo(() => {
    const groups = new Map<number, Planting[]>()
    for (const p of plantings.data ?? []) {
      if (bedFilter !== null && p.bed_id !== bedFilter) continue
      groups.set(p.year, [...(groups.get(p.year) ?? []), p])
    }
    return [...groups.entries()].sort(([a], [b]) => b - a)
  }, [plantings.data, bedFilter])

  const bedName = (id: number) => {
    const bed = bedsById.get(id)
    if (!bed) return '?'
    return bed.archived_at ? f(m.history.archived, { name: bed.name }) : bed.name
  }
  const range = (p: Planting) => {
    const s = parseYearMonth(p.start_month)
    const e = parseYearMonth(p.end_month)
    return `${month(s.month)}${s.year !== p.year ? ` ${s.year}` : ''} – ${month(e.month)}${
      e.year !== p.year ? ` ${e.year}` : ''
    }`
  }

  if (garden.isPending || plantings.isPending) return <Loading label={m.common.loading} />
  const error = garden.error ?? plantings.error ?? crops.error
  const bedsWithHistory = [...new Set((plantings.data ?? []).map((p) => p.bed_id))]
    .map((id) => bedsById.get(id))
    .filter((bed) => bed !== undefined)
    .sort((a, b) => a.name.localeCompare(b.name))

  return (
    <Screen title={m.history.title}>
      {error && <ErrorNotice message={errorText(error)} onRetry={() => void plantings.refetch()} />}
      {bedsWithHistory.length > 1 && (
        <View style={styles.filters}>
          <Chip
            label={m.history.allBeds}
            selected={bedFilter === null}
            onPress={() => setBedFilter(null)}
          />
          {bedsWithHistory.map((bed) => (
            <Chip
              key={bed.id}
              label={bedName(bed.id)}
              selected={bedFilter === bed.id}
              onPress={() => setBedFilter(bed.id)}
            />
          ))}
        </View>
      )}
      {!byYear.length && <Muted>{m.history.empty}</Muted>}
      {byYear.map(([year, items]) => (
        <View key={year} style={styles.card}>
          <Text accessibilityRole="header" style={styles.year}>
            {year}
          </Text>
          {items
            .sort(
              (a, b) =>
                bedName(a.bed_id).localeCompare(bedName(b.bed_id)) ||
                a.start_month.localeCompare(b.start_month),
            )
            .map((p) => {
              const crop = cropsById.get(p.crop_id)
              return (
                <View key={p.id} style={styles.row}>
                  <View
                    style={[styles.swatch, { backgroundColor: familyColor(crop?.family_id) }]}
                  />
                  <Text style={styles.bed}>{bedName(p.bed_id)}</Text>
                  <Text style={styles.crop}>{crop ? name(crop.names) : '?'}</Text>
                  <Text style={styles.range}>{range(p)}</Text>
                </View>
              )
            })}
        </View>
      ))}
    </Screen>
  )
}

const styles = StyleSheet.create({
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    padding: space.lg,
    gap: space.sm,
  },
  year: { fontSize: 20, fontWeight: '700', color: colors.text },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: space.sm,
    minHeight: 36,
  },
  swatch: { width: 14, height: 14, borderRadius: 4, borderWidth: 1, borderColor: '#9FAF95' },
  bed: { fontSize: 15, fontWeight: '600', color: colors.muted, minWidth: 90 },
  crop: { fontSize: 16, color: colors.text, flexGrow: 1 },
  range: { fontSize: 15, color: colors.muted },
})
