import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { cerrarSesionApi, iniciarSesionApi, obtenerUsuario, registrarApi } from '../../api/authApi'
import { AuthContext } from '../../hooks/useAuth'
import type { AceptacionTerminos, Usuario } from '../../types/auth'

function AuthProviderComp({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  // Impide que una petición antigua restaure una sesión que acaba de cerrarse.
  const versionSesion = useRef(0)

  function avisarOtrasPestanas() {
    try { localStorage.setItem('chatbot-cognitivo-sesion', crypto.randomUUID()) }
    catch { /* Algunas configuraciones del navegador deshabilitan este almacenamiento. */ }
  }

  const refrescarUsuario = useCallback(async () => {
    const version = ++versionSesion.current
    setCargando(true)
    setError('')
    try {
      const datos = await obtenerUsuario()
      if (version === versionSesion.current) setUsuario(datos.usuario)
    } catch (fallo) {
      if (version === versionSesion.current) {
        setUsuario(null)
        setError(fallo instanceof Error ? fallo.message : 'No se pudo comprobar la sesión.')
      }
    } finally {
      if (version === versionSesion.current) setCargando(false)
    }
  }, [])

  useEffect(() => {
    let cancelado = false
    const version = versionSesion.current
    void obtenerUsuario().then((datos) => {
      if (!cancelado && version === versionSesion.current) setUsuario(datos.usuario)
    }).catch((fallo: unknown) => {
      if (!cancelado && version === versionSesion.current) setError(fallo instanceof Error ? fallo.message : 'No se pudo comprobar la sesión.')
    }).finally(() => {
      if (!cancelado && version === versionSesion.current) setCargando(false)
    })
    const alCaducar = () => {
      versionSesion.current += 1
      setUsuario(null)
      setCargando(false)
      setError('Tu sesión terminó. Inicia sesión para continuar.')
    }
    const alRevisar = () => { void refrescarUsuario() }
    const alCambiarPestana = (event: StorageEvent) => {
      if (event.key === 'chatbot-cognitivo-sesion') void refrescarUsuario()
    }
    window.addEventListener('sesion-caducada', alCaducar)
    window.addEventListener('sesion-revisar', alRevisar)
    window.addEventListener('storage', alCambiarPestana)
    return () => {
      cancelado = true
      window.removeEventListener('sesion-caducada', alCaducar)
      window.removeEventListener('sesion-revisar', alRevisar)
      window.removeEventListener('storage', alCambiarPestana)
    }
  }, [refrescarUsuario])

  async function iniciarSesion(identificador: string, password: string): Promise<Usuario> {
    const version = ++versionSesion.current
    const datos = await iniciarSesionApi(identificador.trim().toLowerCase(), password)
    if (version === versionSesion.current) {
      setUsuario(datos.usuario)
      setCargando(false)
      setError('')
      avisarOtrasPestanas()
    }
    return datos.usuario
  }

  async function registrar(nombre: string, username: string, password: string, aceptacion: AceptacionTerminos): Promise<Usuario> {
    const version = ++versionSesion.current
    const datos = await registrarApi(nombre.trim(), username.trim().toLowerCase(), password, aceptacion)
    if (version === versionSesion.current) {
      setUsuario(datos.usuario)
      setCargando(false)
      setError('')
      avisarOtrasPestanas()
    }
    return datos.usuario
  }

  async function cerrarSesion(): Promise<void> {
    const version = ++versionSesion.current
    await cerrarSesionApi()
    if (version === versionSesion.current) {
      setUsuario(null)
      setCargando(false)
      setError('')
      avisarOtrasPestanas()
    }
  }

  return (
    <AuthContext.Provider value={{ usuario, cargando, error, refrescarUsuario, iniciarSesion, registrar, cerrarSesion }}>
      {children}
    </AuthContext.Provider>
  )
}

export default AuthProviderComp
