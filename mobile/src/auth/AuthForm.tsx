import { Link } from 'expo-router'
import { useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'

import { useI18n } from '@/i18n'
import { Button, ErrorNotice, Field } from '@/ui/components'
import { Screen } from '@/ui/Screen'
import { colors, space } from '@/ui/theme'

import { useSession } from './session'

export function AuthForm({ mode }: { mode: 'sign-in' | 'register' }) {
  const { m, errorText } = useI18n()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const register = mode === 'register'

  const submit = async () => {
    setPending(true)
    setError(null)
    try {
      if (register) await useSession.getState().register(email, username, password)
      else await useSession.getState().signIn(username, password)
    } catch (caught) {
      setError(errorText(caught))
      setPending(false)
    }
  }
  const ready = register
    ? email.trim() && username.trim() && password.length >= 12
    : username.trim() && password

  return (
    <Screen maxWidth={440}>
      <View style={styles.brand}>
        <Text style={styles.name}>CropCycle</Text>
        <Text style={styles.tagline}>{m.auth.tagline}</Text>
      </View>
      {register && (
        <Field
          label={m.auth.email}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
        />
      )}
      <Field
        label={register ? m.auth.username : m.auth.identifier}
        value={username}
        onChangeText={setUsername}
        autoCapitalize="none"
        autoComplete="username"
        autoCorrect={false}
      />
      <Field
        label={m.auth.password}
        hint={register ? m.auth.passwordHint : undefined}
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete={register ? 'new-password' : 'current-password'}
        onSubmitEditing={() => ready && void submit()}
      />
      {error && <ErrorNotice message={error} />}
      <Button
        label={register ? m.auth.register : m.auth.signIn}
        onPress={() => void submit()}
        disabled={!ready}
        busy={pending}
      />
      <Link href={register ? '/sign-in' : '/register'} replace style={styles.link}>
        {register ? m.auth.toSignIn : m.auth.toRegister}
      </Link>
    </Screen>
  )
}

const styles = StyleSheet.create({
  brand: { alignItems: 'center', gap: space.xs, marginVertical: space.xl },
  name: { fontSize: 34, fontWeight: '800', color: colors.primary },
  tagline: { fontSize: 17, color: colors.muted },
  link: { color: colors.primary, fontSize: 16, textAlign: 'center', padding: space.md },
})
