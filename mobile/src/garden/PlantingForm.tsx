import { useMemo, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'

import type { Crop, Planting, PlantingWrite } from '@/api/types'
import { useI18n } from '@/i18n'
import { parseYearMonth, windowFromMonths } from '@/lib/months'
import { Button, Chip, ErrorNotice, Field, Muted, SectionTitle, YearSwitch } from '@/ui/components'
import { familyColor, space } from '@/ui/theme'

interface Props {
  crops: Crop[]
  year: number
  initial?: Planting
  busy: boolean
  error: string | null
  onSubmit: (body: PlantingWrite) => void
  onCancel: () => void
}

interface Custom {
  startYearOffset: -1 | 0
  startMonth: number
  endMonth: number
}

function customFromCrop(crop: Crop): Custom {
  return {
    startYearOffset: crop.default_start_year_offset === -1 ? -1 : 0,
    startMonth: crop.default_start_month,
    endMonth: crop.default_end_month,
  }
}

function customFromPlanting(planting: Planting): Custom {
  const start = parseYearMonth(planting.start_month)
  return {
    startYearOffset: start.year < planting.year ? -1 : 0,
    startMonth: start.month,
    endMonth: parseYearMonth(planting.end_month).month,
  }
}

/** Record a crop in a bed: pick the crop, the season year, and the typical or chosen months. */
export function PlantingForm({ crops, year, initial, busy, error, onSubmit, onCancel }: Props) {
  const { m, f, name, month } = useI18n()
  const [query, setQuery] = useState('')
  const [cropId, setCropId] = useState<number | null>(initial?.crop_id ?? null)
  const [seasonYear, setSeasonYear] = useState(initial?.year ?? year)
  const [typical, setTypical] = useState(!initial)
  const [custom, setCustom] = useState<Custom | null>(initial ? customFromPlanting(initial) : null)
  const crop = crops.find((c) => c.id === cropId)

  const matches = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return crops
      .filter(
        (c) =>
          !needle ||
          name(c.names).toLocaleLowerCase().includes(needle) ||
          c.names.en?.toLocaleLowerCase().includes(needle),
      )
      .sort((a, b) => name(a.names).localeCompare(name(b.names)))
  }, [crops, query, name])

  const window = crop && (custom ?? customFromCrop(crop))
  const describe = (c: Custom) => {
    const startLabel =
      c.startYearOffset === -1
        ? f(m.planting.previousYearMonth, { month: month(c.startMonth) })
        : month(c.startMonth)
    const endLabel =
      c.endMonth < c.startMonth && c.startYearOffset === 0
        ? f(m.planting.nextYearMonth, { month: month(c.endMonth) })
        : month(c.endMonth)
    return `${startLabel} – ${endLabel}`
  }

  const submit = () => {
    if (!crop) return
    if (typical || !window) {
      onSubmit({ crop_id: crop.id, year: seasonYear })
      return
    }
    const { start, end } = windowFromMonths(
      seasonYear + window.startYearOffset,
      window.startMonth,
      window.endMonth,
    )
    onSubmit({ crop_id: crop.id, year: seasonYear, start_month: start, end_month: end })
  }

  const update = (change: Partial<Custom>) => window && setCustom({ ...window, ...change })

  return (
    <View style={styles.form}>
      <SectionTitle>{initial ? m.planting.editTitle : m.planting.addTitle}</SectionTitle>
      <Field label={m.planting.search} value={query} onChangeText={setQuery} autoCorrect={false} />
      <View style={styles.wrap}>
        {matches.map((c) => (
          <Chip
            key={c.id}
            label={name(c.names)}
            color={familyColor(c.family_id)}
            selected={c.id === cropId}
            onPress={() => {
              setCropId(c.id)
              if (!initial) setCustom(null)
            }}
          />
        ))}
        {!matches.length && <Muted>{m.planting.noMatches}</Muted>}
      </View>

      <Text style={styles.label}>{m.planting.year}</Text>
      <YearSwitch
        year={seasonYear}
        onChange={setSeasonYear}
        previousLabel={m.garden.previousYear}
        nextLabel={m.garden.nextYear}
      />

      <View style={styles.wrap}>
        <Chip label={m.planting.typical} selected={typical} onPress={() => setTypical(true)} />
        <Chip label={m.planting.custom} selected={!typical} onPress={() => setTypical(false)} />
      </View>
      {crop && typical && (
        <Muted>{f(m.planting.typicalWindow, { window: describe(customFromCrop(crop)) })}</Muted>
      )}
      {!crop && <Muted>{m.planting.pickCrop}</Muted>}
      {crop && !typical && window && (
        <View style={styles.custom}>
          <Text style={styles.label}>{m.planting.starts}</Text>
          <View style={styles.wrap}>
            <Chip
              label={m.planting.previousYear}
              selected={window.startYearOffset === -1}
              onPress={() => update({ startYearOffset: -1 })}
            />
            <Chip
              label={m.planting.sameYear}
              selected={window.startYearOffset === 0}
              onPress={() => update({ startYearOffset: 0 })}
            />
          </View>
          <MonthGrid value={window.startMonth} onChange={(startMonth) => update({ startMonth })} />
          <Text style={styles.label}>{m.planting.ends}</Text>
          <MonthGrid value={window.endMonth} onChange={(endMonth) => update({ endMonth })} />
          <Muted>{describe(window)}</Muted>
        </View>
      )}

      {error && <ErrorNotice message={error} />}
      <View style={styles.actions}>
        <Button label={m.common.cancel} variant="secondary" onPress={onCancel} />
        <Button label={m.common.save} onPress={submit} disabled={!crop} busy={busy} />
      </View>
    </View>
  )
}

function MonthGrid({ value, onChange }: { value: number; onChange: (month: number) => void }) {
  const { m } = useI18n()
  return (
    <View style={styles.wrap}>
      {m.months.map((label, index) => (
        <Chip
          key={label}
          label={label}
          selected={value === index + 1}
          onPress={() => onChange(index + 1)}
        />
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  form: { gap: space.md },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  label: { fontSize: 14, fontWeight: '600' },
  custom: { gap: space.sm },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: space.sm },
})
