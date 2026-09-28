import type { ReactNode } from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

import { colors, space } from './theme'

interface Props {
  title?: string
  actions?: ReactNode
  children: ReactNode
  /** Scrolls by default; screens with their own layout (the garden canvas) opt out. */
  scroll?: boolean
  maxWidth?: number
}

export function Screen({ title, actions, children, scroll = true, maxWidth = 720 }: Props) {
  const body = <View style={[styles.body, { maxWidth }]}>{children}</View>
  return (
    <SafeAreaView style={styles.safe} edges={['top', 'left', 'right']}>
      {(title || actions) && (
        <View style={styles.header}>
          {!!title && (
            <Text accessibilityRole="header" style={styles.title} numberOfLines={1}>
              {title}
            </Text>
          )}
          <View style={styles.actions}>{actions}</View>
        </View>
      )}
      {scroll ? (
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {body}
        </ScrollView>
      ) : (
        <View style={styles.fill}>{children}</View>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: space.sm,
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
  },
  title: { flexShrink: 1, fontSize: 24, fontWeight: '700', color: colors.text },
  actions: { flexDirection: 'row', alignItems: 'center', gap: space.sm, marginLeft: 'auto' },
  scroll: { padding: space.lg, alignItems: 'center' },
  body: { width: '100%', gap: space.md },
  fill: { flex: 1 },
})
