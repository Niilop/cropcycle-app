import { MaterialCommunityIcons } from '@expo/vector-icons'
import { Tabs } from 'expo-router'
import type { ComponentProps } from 'react'
import type { ColorValue } from 'react-native'

import { useI18n } from '@/i18n'
import { colors } from '@/ui/theme'

type IconName = ComponentProps<typeof MaterialCommunityIcons>['name']

function icon(name: IconName) {
  function TabIcon({ color, size }: { color: ColorValue; size: number }) {
    return <MaterialCommunityIcons name={name} color={color as string} size={size} />
  }
  return TabIcon
}

export default function TabLayout() {
  const { m } = useI18n()
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { minHeight: 64, backgroundColor: colors.surface },
        tabBarLabelStyle: { fontSize: 13, fontWeight: '600' },
      }}
    >
      <Tabs.Screen name="index" options={{ title: m.tabs.garden, tabBarIcon: icon('sprout') }} />
      <Tabs.Screen
        name="plan"
        options={{ title: m.tabs.plan, tabBarIcon: icon('clipboard-list-outline') }}
      />
      <Tabs.Screen
        name="history"
        options={{ title: m.tabs.history, tabBarIcon: icon('history') }}
      />
      <Tabs.Screen
        name="settings"
        options={{ title: m.tabs.settings, tabBarIcon: icon('cog-outline') }}
      />
    </Tabs>
  )
}
