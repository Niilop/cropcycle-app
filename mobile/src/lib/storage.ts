import * as SecureStore from 'expo-secure-store'
import { Platform } from 'react-native'

// Native: the OS keychain/keystore via SecureStore (D006). Web has no secure storage, so the
// web build (used for development and tests) falls back to localStorage.
const web = Platform.OS === 'web'

export async function getItem(key: string): Promise<string | null> {
  try {
    return web
      ? (globalThis.localStorage?.getItem(key) ?? null)
      : await SecureStore.getItemAsync(key)
  } catch {
    return null
  }
}

export async function setItem(key: string, value: string): Promise<void> {
  try {
    if (web) globalThis.localStorage?.setItem(key, value)
    else await SecureStore.setItemAsync(key, value)
  } catch {
    // Storage can be unavailable (private browsing); the session then lasts until reload.
  }
}

export async function removeItem(key: string): Promise<void> {
  try {
    if (web) globalThis.localStorage?.removeItem(key)
    else await SecureStore.deleteItemAsync(key)
  } catch {
    // Nothing to clean up.
  }
}
