import { useState, useEffect, type ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthContext, saveAuth, clearAuth, getToken, getStoredUser, type AuthContextValue } from './lib/auth'
import type { User } from './lib/api'

import Login       from './pages/Login'
import Dashboard   from './pages/Dashboard'
import Assets      from './pages/Assets'
import AssetDetail from './pages/AssetDetail'
import Tickets     from './pages/Tickets'
import TicketDetail from './pages/TicketDetail'
import Maintenance from './pages/Maintenance'
import Scan        from './pages/Scan'

function AuthGuard({ children }: { children: ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [user, setUser]   = useState<User | null>(getStoredUser)
  const [token, setToken] = useState<string | null>(getToken)

  const authValue: AuthContextValue = {
    user,
    token,
    login: (t, u) => {
      saveAuth(t, u)
      setToken(t)
      setUser(u)
    },
    logout: () => {
      clearAuth()
      setToken(null)
      setUser(null)
    },
  }

  return (
    <AuthContext.Provider value={authValue}>
      <BrowserRouter>
        <Routes>
          <Route path="/login"          element={<Login />} />
          <Route path="/scan/:assetId"  element={<Scan />} />
          <Route path="/dashboard"      element={<AuthGuard><Dashboard /></AuthGuard>} />
          <Route path="/assets"         element={<AuthGuard><Assets /></AuthGuard>} />
          <Route path="/assets/:id"     element={<AuthGuard><AssetDetail /></AuthGuard>} />
          <Route path="/tickets"        element={<AuthGuard><Tickets /></AuthGuard>} />
          <Route path="/tickets/:id"    element={<AuthGuard><TicketDetail /></AuthGuard>} />
          <Route path="/maintenance"    element={<AuthGuard><Maintenance /></AuthGuard>} />
          <Route path="*"               element={<Navigate to={token ? '/dashboard' : '/login'} replace />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
