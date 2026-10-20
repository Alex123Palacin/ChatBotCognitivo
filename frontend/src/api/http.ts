export class ErrorApi extends Error {
  status: number

  constructor(mensaje: string, status = 0) {
    super(mensaje)
    this.name = 'ErrorApi'
    this.status = status
  }
}

interface OpcionesApi {
  method?: string
  body?: unknown
  signal?: AbortSignal
  timeout?: number
}

async function obtenerCsrf(signal: AbortSignal): Promise<string> {
  const limite = AbortSignal.timeout(10_000)
  const combinado = AbortSignal.any([signal, limite])
  try {
    const respuesta = await fetch('/api/csrf/', { credentials: 'same-origin', signal: combinado })
    const datos = await respuesta.json().catch(() => null)
    if (!respuesta.ok || typeof datos?.csrfToken !== 'string') {
      throw new ErrorApi('No se pudo preparar la conexión con Django.', respuesta.status)
    }
    return datos.csrfToken
  } catch (error) {
    if (signal.aborted) throw error
    if (limite.aborted) throw new ErrorApi('Django no responde. Comprueba que el backend esté iniciado en el puerto 8000.')
    throw error
  }
}

export async function peticionApi<T>(ruta: string, opciones: OpcionesApi = {}): Promise<T> {
  return peticionFlujoApi(ruta, opciones, async (respuesta) => {
    const datos = await respuesta.json().catch(() => null)
    if (datos === null) throw new ErrorApi('Django devolvió una respuesta no válida.', respuesta.status)
    return datos as T
  })
}

// Comparte conexión, CSRF y control de sesión con las respuestas que llegan por partes.
export async function peticionFlujoApi<T>(ruta: string, opciones: OpcionesApi,
  leerRespuesta: (respuesta: Response) => Promise<T>): Promise<T> {
  const limite = AbortSignal.timeout(opciones.timeout ?? 15_000)
  const signal = opciones.signal ? AbortSignal.any([opciones.signal, limite]) : limite
  const method = opciones.method ?? 'GET'

  try {
    const headers: Record<string, string> = {}
    if (opciones.body !== undefined) headers['Content-Type'] = 'application/json'
    // Django cambia el token al iniciar sesión; por eso se obtiene antes de cada escritura.
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRFToken'] = await obtenerCsrf(signal)

    const respuesta = await fetch(ruta, {
      method, headers, credentials: 'same-origin', signal,
      ...(opciones.body === undefined ? {} : { body: JSON.stringify(opciones.body) }),
    })
    if (!respuesta.ok) {
      const datos = await respuesta.json().catch(() => null)
      if (respuesta.status === 401 && !signal.aborted && !ruta.includes('/auth/login/') && typeof window !== 'undefined') {
        window.dispatchEvent(new Event('sesion-caducada'))
      }
      const revisarRol = ruta.startsWith('/api/admin/') || (ruta === '/api/chat/' && method === 'GET')
      if (respuesta.status === 403 && !signal.aborted && revisarRol && typeof window !== 'undefined') {
        window.dispatchEvent(new Event('sesion-revisar'))
      }
      throw new ErrorApi(typeof datos?.error === 'string' ? datos.error : 'El servidor no pudo completar la solicitud.', respuesta.status)
    }
    return await leerRespuesta(respuesta)
  } catch (error) {
    if (opciones.signal?.aborted) throw error
    if (limite.aborted) throw new ErrorApi('El servidor está tardando demasiado. Intenta nuevamente.')
    if (error instanceof TypeError) throw new ErrorApi('No se pudo conectar con Django. Comprueba que el backend esté iniciado en el puerto 8000.')
    throw error
  }
}
