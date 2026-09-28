import { MaterialCommunityIcons } from '@expo/vector-icons'
import { router } from 'expo-router'
import { useState } from 'react'
import { Pressable, StyleSheet, Text } from 'react-native'

import { useCreateGarden, useGardens } from '@/api/queries'
import { useI18n } from '@/i18n'
import { usePreferences } from '@/state/preferences'
import { useEditor } from '@/state/editor'
import {
  Button,
  ErrorNotice,
  Field,
  IconButton,
  Loading,
  Muted,
  SectionTitle,
} from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, radius, space, touch } from '@/ui/theme'

export default function Gardens() {
  const { m, errorText } = useI18n()
  const gardens = useGardens()
  const create = useCreateGarden()
  const activeId = usePreferences((state) => state.gardenId)
  const [name, setName] = useState('')

  const open = (id: number) => {
    usePreferences.getState().setGardenId(id)
    useEditor.getState().selectBed(null)
    router.replace('/')
  }

  return (
    <Screen
      title={m.gardens.title}
      actions={
        activeId !== null && router.canGoBack() ? (
          <IconButton icon="close" label={m.common.back} onPress={() => router.back()} />
        ) : null
      }
    >
      {gardens.isPending && <Loading label={m.common.loading} />}
      {gardens.error && (
        <ErrorNotice message={errorText(gardens.error)} onRetry={() => void gardens.refetch()} />
      )}
      {gardens.data?.length === 0 && <Muted>{m.gardens.empty}</Muted>}
      {gardens.data?.map((garden) => (
        <Pressable
          key={garden.id}
          accessibilityRole="button"
          onPress={() => open(garden.id)}
          style={({ pressed }) => [
            styles.garden,
            garden.id === activeId && styles.active,
            pressed && styles.pressed,
          ]}
        >
          <MaterialCommunityIcons name="sprout" size={26} color={colors.primary} />
          <Text style={styles.gardenName}>{garden.name}</Text>
          <MaterialCommunityIcons name="chevron-right" size={26} color={colors.muted} />
        </Pressable>
      ))}

      <SectionTitle>{m.gardens.create}</SectionTitle>
      <Field label={m.gardens.name} value={name} onChangeText={setName} maxLength={100} />
      {create.error && <ErrorNotice message={errorText(create.error)} />}
      <Button
        label={m.gardens.create}
        icon="plus"
        disabled={!name.trim()}
        busy={create.isPending}
        onPress={() =>
          create.mutate(name.trim(), {
            onSuccess: (garden) => {
              setName('')
              open(garden.id)
            },
          })
        }
      />
    </Screen>
  )
}

const styles = StyleSheet.create({
  garden: {
    minHeight: touch + 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    paddingHorizontal: space.lg,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  active: { borderColor: colors.primary, borderWidth: 2 },
  pressed: { opacity: 0.75 },
  gardenName: { flex: 1, fontSize: 18, fontWeight: '600', color: colors.text },
})
