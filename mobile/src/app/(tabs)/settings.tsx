import { router } from 'expo-router'
import { StyleSheet, Text, View } from 'react-native'

import { apiBaseUrl } from '@/api/config'
import { useGarden } from '@/api/queries'
import { useSession } from '@/auth/session'
import { useI18n } from '@/i18n'
import { usePreferences, type LocalePreference } from '@/state/preferences'
import { Button, Chip, Muted, SectionTitle } from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, space } from '@/ui/theme'

export default function SettingsScreen() {
  const { m } = useI18n()
  const locale = usePreferences((state) => state.locale)
  const gardenId = usePreferences((state) => state.gardenId)
  const garden = useGarden(gardenId)
  const user = useSession((state) => state.user)
  const languages: [LocalePreference, string][] = [
    ['auto', m.settings.automatic],
    ['en', 'English'],
    ['fi', 'Suomi'],
  ]

  return (
    <Screen title={m.settings.title}>
      <SectionTitle>{m.settings.language}</SectionTitle>
      <View style={styles.row}>
        {languages.map(([value, label]) => (
          <Chip
            key={value}
            label={label}
            selected={locale === value}
            onPress={() => usePreferences.getState().setLocale(value)}
          />
        ))}
      </View>

      <SectionTitle>{m.settings.garden}</SectionTitle>
      <Text style={styles.value}>{garden.data?.name ?? '—'}</Text>
      <Button
        label={m.garden.changeGarden}
        variant="secondary"
        icon="swap-horizontal"
        onPress={() => router.push('/gardens')}
      />

      <SectionTitle>{m.settings.account}</SectionTitle>
      {user && (
        <Text style={styles.value}>
          {user.username} · {user.email}
        </Text>
      )}
      <Button
        label={m.settings.signOut}
        variant="danger"
        icon="logout"
        onPress={() => void useSession.getState().signOut()}
      />

      <SectionTitle>{m.settings.server}</SectionTitle>
      <Muted>{apiBaseUrl()}</Muted>
    </Screen>
  )
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  value: { fontSize: 17, color: colors.text },
})
