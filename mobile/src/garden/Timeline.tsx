import { StyleSheet, Text, View } from 'react-native'

import { useI18n } from '@/i18n'
import { segmentInYear, type YearMonth } from '@/lib/months'
import { colors, radius, space } from '@/ui/theme'

export interface TimelineRow {
  id: number
  label: string
  color: string
  start: YearMonth
  end: YearMonth
}

/** January–December of one year, with each crop's window clipped to it. */
export function Timeline({ year, rows }: { year: number; rows: TimelineRow[] }) {
  const { m, month } = useI18n()
  return (
    <View style={styles.timeline}>
      <View style={styles.months}>
        {m.monthsNarrow.map((letter, index) => (
          <Text key={index} style={styles.month}>
            {letter}
          </Text>
        ))}
      </View>
      {rows.map((row) => {
        const segment = segmentInYear(row.start, row.end, year)
        if (!segment) return null
        return (
          <View
            key={row.id}
            style={styles.track}
            accessibilityLabel={`${row.label}: ${month(segment.from + 1)}–${month(segment.to + 1)}`}
          >
            <View
              style={[
                styles.bar,
                {
                  left: `${(segment.from / 12) * 100}%`,
                  width: `${((segment.to - segment.from + 1) / 12) * 100}%`,
                  backgroundColor: row.color,
                },
                segment.before && styles.openStart,
                segment.after && styles.openEnd,
              ]}
            >
              <Text numberOfLines={1} style={styles.barText}>
                {segment.before ? '‹ ' : ''}
                {row.label}
                {segment.after ? ' ›' : ''}
              </Text>
            </View>
          </View>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  timeline: { gap: space.xs },
  months: { flexDirection: 'row' },
  month: { flex: 1, textAlign: 'center', fontSize: 12, color: colors.muted },
  track: { height: 30, backgroundColor: colors.background, borderRadius: radius.sm },
  bar: {
    position: 'absolute',
    top: 2,
    bottom: 2,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: '#9FAF95',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  openStart: { borderTopLeftRadius: 0, borderBottomLeftRadius: 0 },
  openEnd: { borderTopRightRadius: 0, borderBottomRightRadius: 0 },
  barText: { fontSize: 13, color: colors.text },
})
