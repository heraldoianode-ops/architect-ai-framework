'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'

interface JWTPayload {
  sub: string
  email: string
  role: string
  exp: number
}

interface AuthContextType {
  token: string | null
  user: JWTPayload | null
  login: (token: string) => void
  logout: () => void
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType>({
  token: null, user: null,
  login: () => {}, logout: () => {}, isAdmin: false,
})

function decodeJWT(token: string): JWTPayload | null {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload))
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<JWTPayload | null>(null)
  const router = useRouter()

  useEffect(() => {
    const stored = localStorage.getItem('auth_token')
    if (stored) {
      const decoded = decodeJWT(stored)
      if (decoded && decoded.exp * 1000 > Date.now()) {
        setToken(stored)
        setUser(decoded)
      } else {
        localStorage.removeItem('auth_token')
      }
    }
  }, [])

  const login = (t: string) => {
    localStorage.setItem('auth_token', t)
    setToken(t)
    setUser(decodeJWT(t))
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
    router.push('/login')
  }

  return (
    <AuthContext.Provider value={{ token, user, login, logout, isAdmin: user?.role === 'administrador' }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
