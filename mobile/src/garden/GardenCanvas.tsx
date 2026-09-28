import { MaterialCommunityIcons } from '@expo/vector-icons'
import { useMemo, useState } from 'react'
import { PanResponder, Pressable, StyleSheet, Text, View, type LayoutRectangle } from 'react-native'

import type { Bed } from '@/api/types'
import { fitScale, MIN_BED_M, snap, snapSize, viewExtent, type Rect } from '@/lib/geometry'
import { colors, radius } from '@/ui/theme'

export interface BedTileData {
  bed: Bed
  subtitle: string
  color: string
  accessibilityLabel: string
}

interface CanvasProps {
  items: BedTileData[]
  selectedId: number | null
  layoutMode: boolean
  onSelect: (bedId: number) => void
  onMove: (bed: Bed, x: number, y: number) => void
  onResize: (bed: Bed, width: number, height: number) => void
}

/** Scaled plan view of the garden. Beds are tapped to select; in layout mode they drag. */
export function GardenCanvas({
  items,
  selectedId,
  layoutMode,
  onSelect,
  onMove,
  onResize,
}: CanvasProps) {
  const [view, setView] = useState<Pick<LayoutRectangle, 'width' | 'height'>>({
    width: 0,
    height: 0,
  })
  const extent = useMemo(() => viewExtent(items.map((item) => item.bed)), [items])
  const scale = fitScale(view, extent)
  // Centred horizontally, anchored to the top so beds stay near the header.
  const offset = { left: (view.width - extent.width * scale) / 2, top: 0 }
  return (
    <View
      style={styles.canvas}
      onLayout={(event) => setView(event.nativeEvent.layout)}
      testID="garden-canvas"
    >
      {scale > 0 && (
        <View
          style={[
            styles.ground,
            { ...offset, width: extent.width * scale, height: extent.height * scale },
            layoutMode && styles.groundEditing,
          ]}
        >
          {items.map((item) => (
            <BedTile
              key={item.bed.id}
              item={item}
              scale={scale}
              extent={extent}
              selected={item.bed.id === selectedId}
              layoutMode={layoutMode}
              onSelect={onSelect}
              onMove={onMove}
              onResize={onResize}
            />
          ))}
          <View style={[styles.scaleBar, { width: scale }]}>
            <Text style={styles.scaleText}>1 m</Text>
          </View>
        </View>
      )}
    </View>
  )
}

interface TileProps extends Omit<CanvasProps, 'items' | 'selectedId'> {
  item: BedTileData
  scale: number
  extent: Rect
  selected: boolean
}

const TAP_SLOP_PX = 6

function BedTile(props: TileProps) {
  const { item, scale, extent, selected, layoutMode } = props
  const { bed } = item
  const [drag, setDrag] = useState({ dx: 0, dy: 0 })
  const [grow, setGrow] = useState({ dw: 0, dh: 0 })
  const { onSelect, onMove, onResize } = props

  // Rebuilt only when the bed, scale or (stable) callbacks change, not during a drag.
  const move = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onPanResponderMove: (_, g) => setDrag({ dx: g.dx, dy: g.dy }),
        onPanResponderRelease: (_, g) => {
          setDrag({ dx: 0, dy: 0 })
          if (Math.abs(g.dx) + Math.abs(g.dy) < TAP_SLOP_PX) onSelect(bed.id)
          else onMove(bed, snap(bed.x + g.dx / scale), snap(bed.y + g.dy / scale))
        },
        onPanResponderTerminate: () => setDrag({ dx: 0, dy: 0 }),
      }),
    [bed, scale, onSelect, onMove],
  )
  const resize = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onPanResponderMove: (_, g) => setGrow({ dw: g.dx, dh: g.dy }),
        onPanResponderRelease: (_, g) => {
          setGrow({ dw: 0, dh: 0 })
          if (Math.abs(g.dx) + Math.abs(g.dy) >= TAP_SLOP_PX) {
            onResize(bed, snapSize(bed.width + g.dx / scale), snapSize(bed.height + g.dy / scale))
          }
        },
        onPanResponderTerminate: () => setGrow({ dw: 0, dh: 0 }),
      }),
    [bed, scale, onResize],
  )

  const frame = {
    left: (bed.x - extent.x) * scale + drag.dx,
    top: (bed.y - extent.y) * scale + drag.dy,
    width: Math.max(MIN_BED_M * scale, bed.width * scale + grow.dw),
    height: Math.max(MIN_BED_M * scale, bed.height * scale + grow.dh),
  }
  const fontSize = Math.max(11, Math.min(16, scale * 0.28))
  const content = (
    <>
      <Text numberOfLines={1} style={[styles.bedName, { fontSize }]}>
        {bed.name}
      </Text>
      {!!item.subtitle && (
        <Text numberOfLines={3} style={[styles.bedCrops, { fontSize: fontSize - 1 }]}>
          {item.subtitle}
        </Text>
      )}
    </>
  )
  const style = [
    styles.bed,
    frame,
    { backgroundColor: item.color },
    selected && styles.bedSelected,
    layoutMode && styles.bedEditing,
  ]

  if (!layoutMode) {
    return (
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={item.accessibilityLabel}
        accessibilityState={{ selected }}
        onPress={() => onSelect(bed.id)}
        style={style}
        testID={`bed-${bed.id}`}
      >
        {content}
      </Pressable>
    )
  }
  return (
    <View
      accessibilityLabel={item.accessibilityLabel}
      style={style}
      testID={`bed-${bed.id}`}
      {...move.panHandlers}
    >
      {content}
      <View style={styles.handle} testID={`bed-${bed.id}-resize`} {...resize.panHandlers}>
        <MaterialCommunityIcons name="resize-bottom-right" size={18} color={colors.text} />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  canvas: { flex: 1, minHeight: 240, overflow: 'hidden' },
  ground: {
    position: 'absolute',
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.grid,
  },
  groundEditing: { borderStyle: 'dashed', borderColor: colors.primary },
  bed: {
    position: 'absolute',
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: '#9FAF95',
    padding: 4,
    overflow: 'hidden',
  },
  bedSelected: { borderWidth: 3, borderColor: colors.selected },
  bedEditing: { borderStyle: 'dashed' },
  bedName: { fontWeight: '700', color: colors.text },
  bedCrops: { color: colors.text },
  handle: {
    position: 'absolute',
    right: 0,
    bottom: 0,
    width: 36,
    height: 36,
    alignItems: 'flex-end',
    justifyContent: 'flex-end',
    padding: 2,
  },
  scaleBar: {
    position: 'absolute',
    left: 8,
    bottom: 8,
    height: 4,
    backgroundColor: colors.muted,
  },
  scaleText: { position: 'absolute', top: -18, left: 0, fontSize: 12, color: colors.muted },
})
