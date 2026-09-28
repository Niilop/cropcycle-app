import { useMemo, useState } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'

import {
  useArchiveBed,
  useCreatePlanting,
  useDeletePlanting,
  useUpdateBed,
  useUpdatePlanting,
} from '@/api/queries'
import type { Bed, BedWrite, Crop, Planting, PlantingWrite } from '@/api/types'
import { useI18n } from '@/i18n'
import { snap, snapSize, MIN_BED_M } from '@/lib/geometry'
import { parseYearMonth, touchesYear } from '@/lib/months'
import {
  Button,
  ErrorNotice,
  Field,
  IconButton,
  Muted,
  SectionTitle,
  Stepper,
} from '@/ui/components'
import { colors, familyColor, radius, space } from '@/ui/theme'

import { PlantingForm } from './PlantingForm'
import { Timeline } from './Timeline'

interface Props {
  gardenId: number
  bed: Bed
  year: number
  plantings: Planting[]
  crops: Crop[]
  layoutMode: boolean
  onClose: () => void
}

type Editing = { kind: 'none' } | { kind: 'add' } | { kind: 'edit'; planting: Planting }

export function BedPanel({ gardenId, bed, year, plantings, crops, layoutMode, onClose }: Props) {
  const { m, f, name, month, errorText } = useI18n()
  const [editing, setEditing] = useState<Editing>({ kind: 'none' })
  const [confirm, setConfirm] = useState<string | null>(null)
  // Shown only while renaming; otherwise the saved name. The screen remounts this panel
  // (key) when another bed is selected, which also resets the editing state.
  const [nameDraft, setNameDraft] = useState<string | null>(null)

  const updateBed = useUpdateBed(gardenId)
  const archiveBed = useArchiveBed(gardenId)
  const createPlanting = useCreatePlanting(gardenId)
  const updatePlanting = useUpdatePlanting(gardenId)
  const deletePlanting = useDeletePlanting(gardenId)
  const cropsById = useMemo(() => new Map(crops.map((c) => [c.id, c])), [crops])

  const thisYear = plantings.filter((p) => touchesYear(p.start_month, p.end_month, year))
  const earlier = plantings.filter((p) => p.year < year && !thisYear.includes(p))
  const cropName = (id: number) => {
    const crop = cropsById.get(id)
    return crop ? name(crop.names) : '?'
  }
  const range = (p: Planting) => {
    const s = parseYearMonth(p.start_month)
    const e = parseYearMonth(p.end_month)
    return `${month(s.month)}${s.year !== p.year ? ` ${s.year}` : ''} – ${month(e.month)}${
      e.year !== p.year ? ` ${e.year}` : ''
    }`
  }

  const saveBed = (change: Partial<BedWrite>) => {
    const body: BedWrite = {
      name: bed.name,
      x: bed.x,
      y: bed.y,
      width: bed.width,
      height: bed.height,
      ...change,
    }
    updateBed.mutate({ id: bed.id, body })
  }
  const saveName = () => {
    if (nameDraft === null) return
    const trimmed = nameDraft.trim()
    setNameDraft(null)
    if (trimmed && trimmed !== bed.name) saveBed({ name: trimmed })
  }

  const submitPlanting = (body: PlantingWrite) => {
    const done = { onSuccess: () => setEditing({ kind: 'none' }) }
    if (editing.kind === 'edit') updatePlanting.mutate({ id: editing.planting.id, body }, done)
    else createPlanting.mutate({ bedId: bed.id, body }, done)
  }
  const formMutation = editing.kind === 'edit' ? updatePlanting : createPlanting

  const removePlanting = (id: number) => {
    if (confirm !== `planting-${id}`) {
      setConfirm(`planting-${id}`)
      return
    }
    setConfirm(null)
    deletePlanting.mutate(id)
  }

  const plantingRow = (p: Planting) => (
    <View key={p.id} style={styles.row}>
      <View
        style={[
          styles.swatch,
          { backgroundColor: familyColor(cropsById.get(p.crop_id)?.family_id) },
        ]}
      />
      <View style={styles.rowText}>
        <Text style={styles.rowTitle}>{cropName(p.crop_id)}</Text>
        <Text style={styles.rowDetail}>{range(p)}</Text>
      </View>
      <IconButton
        icon="pencil-outline"
        label={`${m.common.edit} ${cropName(p.crop_id)}`}
        onPress={() => setEditing({ kind: 'edit', planting: p })}
      />
      <Button
        label={confirm === `planting-${p.id}` ? m.common.remove : ''}
        icon="trash-can-outline"
        variant={confirm === `planting-${p.id}` ? 'danger' : 'ghost'}
        compact
        accessibilityLabel={`${m.common.remove} ${cropName(p.crop_id)}`}
        onPress={() => removePlanting(p.id)}
      />
    </View>
  )

  const byYear = new Map<number, Planting[]>()
  for (const p of earlier) byYear.set(p.year, [...(byYear.get(p.year) ?? []), p])

  return (
    <ScrollView contentContainerStyle={styles.panel} keyboardShouldPersistTaps="handled">
      <View style={styles.header}>
        <View style={styles.headerName}>
          <Field
            label={m.bed.name}
            value={nameDraft ?? bed.name}
            onChangeText={setNameDraft}
            onBlur={saveName}
            onSubmitEditing={saveName}
            maxLength={100}
          />
        </View>
        <IconButton icon="close" label={m.common.close} onPress={onClose} />
      </View>
      {updateBed.error && <ErrorNotice message={errorText(updateBed.error)} />}

      {editing.kind !== 'none' ? (
        <PlantingForm
          key={editing.kind === 'edit' ? editing.planting.id : 'new'}
          crops={crops}
          year={year}
          initial={editing.kind === 'edit' ? editing.planting : undefined}
          busy={formMutation.isPending}
          error={formMutation.error ? errorText(formMutation.error) : null}
          onSubmit={submitPlanting}
          onCancel={() => {
            formMutation.reset()
            setEditing({ kind: 'none' })
          }}
        />
      ) : (
        <>
          <SectionTitle>{f(m.bed.inYear, { year })}</SectionTitle>
          {thisYear.length ? (
            <>
              <Timeline
                year={year}
                rows={thisYear.map((p) => ({
                  id: p.id,
                  label: cropName(p.crop_id),
                  color: familyColor(cropsById.get(p.crop_id)?.family_id),
                  start: p.start_month,
                  end: p.end_month,
                }))}
              />
              {thisYear.map(plantingRow)}
            </>
          ) : (
            <Muted>{f(m.bed.nothingInYear, { year })}</Muted>
          )}
          {deletePlanting.error && <ErrorNotice message={errorText(deletePlanting.error)} />}
          <Button label={m.bed.addCrop} icon="plus" onPress={() => setEditing({ kind: 'add' })} />

          <SectionTitle>{m.bed.history}</SectionTitle>
          {byYear.size ? (
            [...byYear.entries()]
              .sort(([a], [b]) => b - a)
              .map(([historyYear, items]) => (
                <View key={historyYear} style={styles.yearGroup}>
                  <Text style={styles.yearLabel}>{historyYear}</Text>
                  {items.map(plantingRow)}
                </View>
              ))
          ) : (
            <Muted>{m.bed.noHistory}</Muted>
          )}
        </>
      )}

      {layoutMode && editing.kind === 'none' && (
        <>
          <SectionTitle>{m.bed.layout}</SectionTitle>
          <View style={styles.steppers}>
            <Stepper
              label={m.bed.x}
              value={bed.x}
              step={0.1}
              onChange={(v) => saveBed({ x: snap(v) })}
            />
            <Stepper
              label={m.bed.y}
              value={bed.y}
              step={0.1}
              onChange={(v) => saveBed({ y: snap(v) })}
            />
            <Stepper
              label={m.bed.width}
              value={bed.width}
              step={0.1}
              min={MIN_BED_M}
              onChange={(v) => saveBed({ width: snapSize(v) })}
            />
            <Stepper
              label={m.bed.height}
              value={bed.height}
              step={0.1}
              min={MIN_BED_M}
              onChange={(v) => saveBed({ height: snapSize(v) })}
            />
          </View>
          {archiveBed.error && <ErrorNotice message={errorText(archiveBed.error)} />}
          <Button
            label={confirm === 'archive' ? m.bed.archiveConfirm : m.bed.archive}
            icon="trash-can-outline"
            variant="danger"
            busy={archiveBed.isPending}
            onPress={() => {
              if (confirm !== 'archive') {
                setConfirm('archive')
                return
              }
              archiveBed.mutate(bed.id, { onSuccess: onClose })
            }}
          />
        </>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  panel: { padding: space.lg, gap: space.md },
  header: { flexDirection: 'row', alignItems: 'flex-end', gap: space.sm },
  headerName: { flex: 1 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingVertical: space.xs,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  swatch: {
    width: 14,
    height: 14,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: '#9FAF95',
  },
  rowText: { flex: 1 },
  rowTitle: { fontSize: 16, fontWeight: '600', color: colors.text },
  rowDetail: { fontSize: 14, color: colors.muted },
  yearGroup: { gap: space.xs },
  yearLabel: { fontSize: 15, fontWeight: '700', color: colors.muted },
  steppers: { flexDirection: 'row', flexWrap: 'wrap', gap: space.md },
})
