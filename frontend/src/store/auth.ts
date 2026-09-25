import { create } from 'zustand'
import { setToken, clearToken, getToken } from '@/lib/api'

interface AuthUser {
  user_id: string
  workspace_id: string
  name: string
  email: string
}

interface AuthStore {
  user: AuthUser | null
  token: string | null
  setAuth: (user: AuthUser, token: string) => void
  logout: () => void
  loadFromStorage: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  setAuth: (user, token) => {
    setToken(token)
    if (typeof window !== 'undefined') {
      localStorage.setItem('scoutiq_user', JSON.stringify(user))
    }
    set({ user, token })
  },
  logout: () => {
    clearToken()
    set({ user: null, token: null })
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
    }
  },
}))
