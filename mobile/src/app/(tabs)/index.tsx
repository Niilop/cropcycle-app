import { Redirect, router } from 'expo-router'
import { useCallback, useEffect, useMemo } from 'react'
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'

import { ApiError } from '@/api/client'
import { useCreateBed, useCrops, useGarden, useGardenPlantings, useUpdateBed } from '@/api/queries'
import type { Bed, BedWrite } from '@/api/types'
import { BedPanel } from '@/garden/BedPanel'
import { GardenCanvas, type BedTileData } from '@/garden/GardenCanvas'
import { useI18n } from '@/i18n'
import { freePosition } from '@/lib/geometry'
import { touchesYear } from '@/lib/months'
import { useEditor } from '@/state/editor'
import { usePreferences } from '@/state/preferences'
import { Button, ErrorNotice, Loading, Muted, YearSwitch } from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, familyColor, radius, space, WIDE_BREAKPOINT } from '@/ui/theme'

const NEW_BED = { width: 1.2, height: 3 }

export default function GardenScreen() {
  const gardenId = usePreferences((state) => state.gardenId)
  if (gardenId === null) return <Redirect href="/gardens" />
  return <GardenEditor gardenId={gardenId} />
}

function GardenEditor({ gardenId }: { gardenId: number }) {
  const { m, f, name, errorText } = useI18n()
  const { width } = useWindowDimensions()
  const wide = width >= WIDE_BREAKPOINT
  const { year, selectedBedId, layoutMode, setYear, selectBed, setLayoutMode } = useEditor()

  const garden = useGarden(gardenId)
  const plantings = useGardenPlantings(gardenId)
  const crops = useCrops()
  const createBed = useCreateBed(gardenId)
  const updateBed = useUpdateBed(gardenId)

  // A garden deleted elsewhere: forget it and choose again.
  const missing = garden.error instanceof ApiError && garden.error.status === 404
  useEffect(() => {
    if (missing) usePreferences.getState().setGardenId(null)
  }, [missing])

  const beds = useMemo(
    () => (garden.data?.beds ?? []).filter((bed) => bed.archived_at === null),
    [garden.data],
  )
  const cropsById = useMemo(() => new Map((crops.data ?? []).map((c) => [c.id, c])), [crops.data])
  const items: BedTileData[] = useMemo(
    () =>
      beds.map((bed) => {
        const current = (plantings.data ?? [])
          .filter((p) => p.bed_id === bed.id && touchesYear(p.start_month, p.end_month, year))
          .sort((a, b) => a.start_month.localeCompare(b.start_month))
        const names = current.map((p) => {
          const crop = cropsById.get(p.crop_id)
          return crop ? name(crop.names) : '?'
        })
        return {
          bed,
          subtitle: names.join(' → '),
          color: familyColor(cropsById.get(current[0]?.crop_id ?? -1)?.family_id),
          accessibilityLabel: f(m.garden.bedLabel, {
            name: bed.name,
            crops: names.join(', ') || m.garden.empty,
          }),
        }
      }),
    [beds, plantings.data, cropsById, year, name, f, m],
  )
  const selected = beds.find((bed) => bed.id === selectedBedId) ?? null

  // Stable callbacks keep the canvas's drag handlers intact while a gesture is in progress.
  const { mutate: mutateBed } = updateBed
  const save = useCallback(
    (bed: Bed, change: Partial<BedWrite>) =>
      mutateBed({
        id: bed.id,
        body: {
          name: bed.name,
          x: bed.x,
          y: bed.y,
          width: bed.width,
          height: bed.height,
          ...change,
        },
      }),
    [mutateBed],
  )
  // Tapping a bed always opens it; the panel's close button deselects.
  const onSelect = useCallback((id: number) => selectBed(id), [selectBed])
  const onMove = useCallback((bed: Bed, x: number, y: number) => save(bed, { x, y }), [save])
  const onResize = useCallback(
    (bed: Bed, w: number, h: number) => save(bed, { width: w, height: h }),
    [save],
  )

  if (missing) return <Redirect href="/gardens" />
  if (garden.isPending) return <Loading label={m.common.loading} />

  const addBed = () =>
    createBed.mutate(
      {
        name: f(m.garden.newBedName, { n: beds.length + 1 }),
        ...freePosition(beds, NEW_BED),
        ...NEW_BED,
      },
      { onSuccess: (bed) => selectBed(bed.id) },
    )

  const error = garden.error ?? plantings.error ?? crops.error ?? createBed.error ?? updateBed.error
  const panel = selected && (
    <BedPanel
      key={selected.id}
      gardenId={gardenId}
      bed={selected}
      year={year}
      plantings={(plantings.data ?? []).filter((p) => p.bed_id === selected.id)}
      crops={crops.data ?? []}
      layoutMode={layoutMode}
      onClose={() => selectBed(null)}
    />
  )

  return (
    <Screen scroll={false}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={m.garden.changeGarden}
          onPress={() => router.push('/gardens')}
          style={styles.gardenName}
        >
          <Text numberOfLines={1} style={styles.title}>
            {garden.data?.name}
          </Text>
          <Text style={styles.change}>{m.garden.changeGarden}</Text>
        </Pressable>
        <YearSwitch
          year={year}
          onChange={setYear}
          previousLabel={m.garden.previousYear}
          nextLabel={m.garden.nextYear}
        />
        <View style={styles.actions}>
          <Button
            label={layoutMode ? m.garden.doneLayout : m.garden.editLayout}
            icon={layoutMode ? 'check' : 'vector-square-edit'}
            variant={layoutMode ? 'primary' : 'secondary'}
            onPress={() => setLayoutMode(!layoutMode)}
          />
          <Button
            label={m.garden.addBed}
            icon="plus"
            variant="secondary"
            busy={createBed.isPending}
            onPress={addBed}
          />
        </View>
      </View>
      {error && (
        <View style={styles.notice}>
          <ErrorNotice message={errorText(error)} onRetry={() => void garden.refetch()} />
        </View>
      )}
      {layoutMode && (
        <View style={styles.notice}>
          <Muted>{m.garden.layoutHint}</Muted>
        </View>
      )}

      <View style={[styles.body, wide && styles.bodyWide]}>
        <View style={styles.canvasArea}>
          {beds.length ? (
            <GardenCanvas
              items={items}
              selectedId={selectedBedId}
              layoutMode={layoutMode}
              onSelect={onSelect}
              onMove={onMove}
              onResize={onResize}
            />
          ) : (
            <View style={styles.empty}>
              <Muted>{m.garden.noBeds}</Muted>
              <Button
                label={m.garden.addBed}
                icon="plus"
                onPress={addBed}
                busy={createBed.isPending}
              />
            </View>
          )}
        </View>
        {/* Beside the garden on wide screens; below it on phones, so beds stay visible. */}
        {panel && <View style={wide ? styles.side : styles.sheet}>{panel}</View>}
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  gardenName: { flexShrink: 1, minHeight: 48, justifyContent: 'center', marginRight: 'auto' },
  title: { fontSize: 22, fontWeight: '700', color: colors.text },
  change: { fontSize: 13, color: colors.primary },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  notice: { paddingHorizontal: space.lg, paddingBottom: space.sm },
  body: { flex: 1 },
  bodyWide: { flexDirection: 'row' },
  canvasArea: { flex: 1, padding: space.md },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.lg,
    padding: space.xl,
  },
  side: {
    width: 400,
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
    backgroundColor: colors.surface,
  },
  sheet: {
    height: '58%',
    backgroundColor: colors.surface,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    borderTopWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 12,
  },
})
