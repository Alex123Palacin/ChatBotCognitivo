import { peticionApi } from './http.ts'
import { guardarTokenAdmin, tokenAdmin } from './sesionAdmin.ts'
import type { AceptacionTerminos, RespuestaAuth, TerminosRegistro, Usuario } from '../types/auth'

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
  const credenciales = { username: identificador.trim().toLowerCase(), password }
  const datos = await peticionApi<{ usuario: unknown; admin_pestana?: string }>('/api/auth/login/', { method: 'POST', body: credenciales })
  guardarTokenAdmin(typeof datos.admin_pestana === 'string' ? datos.admin_pestana : '')
  return { usuario: validarUsuario(datos.usuario) }
}

export async function obtenerTerminosRegistro(): Promise<TerminosRegistro> {
  const datos = await peticionApi<TerminosRegistro>('/api/auth/terminos/')
  if (!datos || typeof datos.version !== 'string' || !datos.version.trim()
    || datos.dias_retencion !== 90 || typeof datos.texto !== 'string' || !datos.texto.trim()
    || datos.base_plazo !== 'ultimo_inicio_sesion' || datos.alcance !== 'mensajes_nuevos' || datos.copias_seguridad !== 'gestion_separada') {
    throw new Error('No se pudieron comprobar los términos de conservación. Vuelve a intentarlo.')
  }
  return datos
}

export async function registrarApi(nombre: string, username: string, password: string, aceptacion: AceptacionTerminos): Promise<RespuestaAuth> {
  if (aceptacion?.acepta_terminos !== true || !aceptacion.version_terminos?.trim()) {
    throw new Error('Lee y acepta los términos de conservación antes de crear tu cuenta.')
  }
  if (!/^[A-Za-z][A-Za-z0-9._-]{2,39}$/.test(username.trim())) {
    throw new Error('El usuario debe tener entre 3 y 40 caracteres y empezar con una letra; usa letras sin tildes, números, punto, guion o guion bajo.')
  }
  const datos = await peticionApi<{ usuario: unknown }>('/api/auth/registro/', { method: 'POST', body: { ...(nombre ? { nombre } : {}), username: username.trim().toLowerCase(), password, acepta_terminos: aceptacion.acepta_terminos, version_terminos: aceptacion.version_terminos } })
  return { usuario: validarUsuario(datos.usuario) }
}

export async function cerrarSesionApi(): Promise<{ usuario: null }> {
  const token = tokenAdmin()
  const respuesta = await peticionApi<{ usuario: null }>('/api/auth/logout/', { method: 'POST' })
  if (tokenAdmin() === token) guardarTokenAdmin('')
  return respuesta
}
