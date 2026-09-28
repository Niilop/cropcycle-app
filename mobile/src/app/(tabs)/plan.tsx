import { MaterialCommunityIcons } from '@expo/vector-icons'
import { StyleSheet, View } from 'react-native'

import { useI18n } from '@/i18n'
import { Muted } from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, space } from '@/ui/theme'

// Filled in by plan 002 Phase 4 (requested crops, placement, Fill remaining).
export default function PlanScreen() {
  const { m } = useI18n()
  return (
    <Screen title={m.plan.title}>
      <View style={styles.soon}>
        <MaterialCommunityIcons name="clipboard-list-outline" size={48} color={colors.primary} />
        <Muted>{m.plan.comingSoon}</Muted>
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  soon: { alignItems: 'center', gap: space.lg, padding: space.xl },
})
