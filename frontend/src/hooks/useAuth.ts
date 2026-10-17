import { createContext, useContext } from 'react'
import type { Usuario } from '../types/auth'

export interface EstadoAuth {
  usuario: Usuario | null
  cargando: boolean
  error: string
  refrescarUsuario: () => Promise<void>
  iniciarSesion: (identificador: string, password: string) => Promise<Usuario>
  registrar: (nombre: string, email: string, password: string) => Promise<Usuario>
  cerrarSesion: () => Promise<void>
}

export const AuthContext = createContext<EstadoAuth | null>(null)

export function useAuth(): EstadoAuth {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de AuthProviderComp.')
  return contexto
}
