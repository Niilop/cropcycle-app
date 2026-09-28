import { create } from 'zustand'

import { api, ApiError, configureClient } from '@/api/client'
import type { Token, User } from '@/api/types'
import { getItem, removeItem, setItem } from '@/lib/storage'

const TOKEN_KEY = 'cropcycle.token'
const USER_KEY = 'cropcycle.user'

type Status = 'loading' | 'signedOut' | 'signedIn'

interface SessionState {
  status: Status
  token: string | null
  user: User | null
  restore: () => Promise<void>
  signIn: (identifier: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

export const useSession = create<SessionState>((set, get) => ({
  status: 'loading',
  token: null,
  user: null,

  // Start signed in from storage so the app opens offline, then confirm in the background.
  async restore() {
    const [token, storedUser] = await Promise.all([getItem(TOKEN_KEY), getItem(USER_KEY)])
    if (!token) {
      set({ status: 'signedOut' })
      return
    }
    let user: User | null = null
    try {
      user = storedUser ? (JSON.parse(storedUser) as User) : null
    } catch {
      user = null
    }
    set({ status: 'signedIn', token, user })
    try {
      const fresh = await api<User>('/auth/me')
      set({ user: fresh })
      await setItem(USER_KEY, JSON.stringify(fresh))
    } catch (error) {
      // 401 already signed the user out through the client hook; keep the session otherwise.
      if (!(error instanceof ApiError)) throw error
    }
  },

  async signIn(identifier, password) {
    const { access_token } = await api<Token>('/auth/login', {
      method: 'POST',
      form: { username: identifier.trim(), password },
    })
    set({ token: access_token })
    let user: User
    try {
      user = await api<User>('/auth/me')
    } catch (error) {
      set({ token: null })
      throw error
    }
    await Promise.all([setItem(TOKEN_KEY, access_token), setItem(USER_KEY, JSON.stringify(user))])
    set({ status: 'signedIn', user })
  },

  async register(email, username, password) {
    await api<User>('/auth/register', {
      method: 'POST',
      json: { email: email.trim(), username: username.trim(), password },
    })
    await get().signIn(username, password)
  },

  async signOut() {
    set({ status: 'signedOut', token: null, user: null })
    await Promise.all([removeItem(TOKEN_KEY), removeItem(USER_KEY)])
  },
}))

configureClient({
  getToken: () => useSession.getState().token,
  onUnauthorized: () => void useSession.getState().signOut(),
})
