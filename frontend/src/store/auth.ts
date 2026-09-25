import { create } from 'zustand'
import { setToken, clearToken, getToken } from '@/lib/api'

interface AuthUser {
  user_id: string
  workspace_id: string
  name: string
  email: string
}

export interface AuthStore {
  user: AuthUser | null
  token: string | null
  setAuth: (user: AuthUser, token: string) => void
  logout: () => void
  loadFromStorage: () => void
}

export const DEMO_USER: AuthUser = {
  user_id: 'usr_demo_01',
  workspace_id: 'ws_demo_01',
  name: 'Demo Scout',
  email: 'demo@scoutiq.ai',
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: DEMO_USER,
  token: 'demo_token',
  setAuth: (user: AuthUser, token: string) => {
    setToken(token)
    if (typeof window !== 'undefined') {
      localStorage.setItem('scoutiq_user', JSON.stringify(user))
    }
    set({ user, token })
  },
  logout: () => {
    clearToken()
    set({ user: DEMO_USER, token: 'demo_token' })
  },
  loadFromStorage: () => {
    if (typeof window === 'undefined') return
    const token = getToken()
    const userStr = localStorage.getItem('scoutiq_user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        set({ user, token })
      } catch {}
    } else {
      set({ user: DEMO_USER, token: 'demo_token' })
    }
  },
}))
