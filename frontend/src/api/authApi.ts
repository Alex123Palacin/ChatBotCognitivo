import { peticionApi } from './http.ts'
import type { RespuestaAuth, Usuario } from '../types/auth'

function validarUsuario(valor: unknown): Usuario {
  if (!valor || typeof valor !== 'object') throw new Error('Django devolvió una sesión no válida.')
  const usuario = valor as Partial<Usuario>
  if (!Number.isInteger(usuario.id) || Number(usuario.id) < 1 || typeof usuario.email !== 'string'
    || typeof usuario.nombre !== 'string' || typeof usuario.es_admin !== 'boolean') {
    throw new Error('Django devolvió una sesión no válida.')
  }
  if (usuario.username !== undefined && typeof usuario.username !== 'string') {
    throw new Error('Django devolvió una sesión no válida.')
  }
  return usuario as Usuario
}

export async function obtenerUsuario(): Promise<{ usuario: Usuario | null }> {
  const datos = await peticionApi<{ usuario: unknown }>('/api/auth/me/')
  return { usuario: datos.usuario === null ? null : validarUsuario(datos.usuario) }
}

export async function iniciarSesionApi(identificador: string, password: string): Promise<RespuestaAuth> {
  const credenciales = identificador.includes('@') ? { email: identificador, password } : { username: identificador, password }
  const datos = await peticionApi<{ usuario: unknown }>('/api/auth/login/', { method: 'POST', body: credenciales })
  return { usuario: validarUsuario(datos.usuario) }
}

export async function registrarApi(nombre: string, email: string, password: string): Promise<RespuestaAuth> {
  const datos = await peticionApi<{ usuario: unknown }>('/api/auth/registro/', { method: 'POST', body: { nombre, email, password } })
  return { usuario: validarUsuario(datos.usuario) }
}

export function cerrarSesionApi(): Promise<{ usuario: null }> {
  return peticionApi('/api/auth/logout/', { method: 'POST' })
}
