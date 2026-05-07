import { createContext, useContext } from 'react'
import type { User } from './api'

const TOKEN_KEY = 'token'
const USER_KEY  = 'auth_user'

// ── Token storage ─────────────────────────────────────────────────────────────

export function saveAuth(token: string, user: User): void {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

// ── Auth context ──────────────────────────────────────────────────────────────

export interface AuthContextValue {
  user: User | null
  token: string | null
  login: (token: string, user: User) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue>({
  user:   null,
  token:  null,
  login:  () => {},
  logout: () => {},
})

export function useAuth(): AuthContextValue {
  return useContext(AuthContext)
}
