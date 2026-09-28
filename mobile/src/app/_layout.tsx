import { QueryClientProvider } from '@tanstack/react-query'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { useEffect } from 'react'
import { SafeAreaProvider } from 'react-native-safe-area-context'

import { queryClient } from '@/api/queries'
import { useSession } from '@/auth/session'
import { usePreferences } from '@/state/preferences'
import { Loading } from '@/ui/components'
import { colors } from '@/ui/theme'

export default function RootLayout() {
  const status = useSession((state) => state.status)
  const preferencesReady = usePreferences((state) => state.ready)

  useEffect(() => {
    void useSession.getState().restore()
    void usePreferences.getState().hydrate()
  }, [])

  // Another account must not see cached data from the previous one.
  useEffect(() => {
    if (status === 'signedOut') queryClient.clear()
  }, [status])

  if (status === 'loading' || !preferencesReady) return <Loading label="CropCycle" />

  const signedIn = status === 'signedIn'
  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Protected guard={signedIn}>
            <Stack.Screen name="(tabs)" />
            <Stack.Screen name="gardens" />
          </Stack.Protected>
          <Stack.Protected guard={!signedIn}>
            <Stack.Screen name="sign-in" />
            <Stack.Screen name="register" />
          </Stack.Protected>
        </Stack>
      </SafeAreaProvider>
    </QueryClientProvider>
  )
}
