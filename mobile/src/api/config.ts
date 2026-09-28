import Constants from 'expo-constants'
import { Platform } from 'react-native'

const API_PORT = 8000

/**
 * The API address. EXPO_PUBLIC_API_URL wins; otherwise use port 8000 on the host that serves
 * the app: localhost in a browser, 10.0.2.2 in the Android emulator (when Expo Go was opened
 * with exp://10.0.2.2:8081), or the PC's network address when a phone scans the QR code.
 */
export function apiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_URL
  if (configured) return configured.replace(/\/+$/, '')
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:${API_PORT}`
  }
  const host = Constants.expoConfig?.hostUri?.split(':')[0]
  return `http://${host || 'localhost'}:${API_PORT}`
}
