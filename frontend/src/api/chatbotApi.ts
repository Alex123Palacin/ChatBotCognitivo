import { ErrorApi, peticionApi, peticionFlujoApi } from './http.ts'
import type { EstadoChat, SolicitudChat } from '../types/chatbot'

function validarChat(datos: EstadoChat): EstadoChat {
  if (!datos || !Array.isArray(datos.mensajes) || !Array.isArray(datos.sesiones)
    || typeof datos.respuesta_pendiente !== 'boolean' || typeof datos.programa_finalizado !== 'boolean'
    || datos.mensajes.some((mensaje) => typeof mensaje.id !== 'string'
      || typeof mensaje.contenido !== 'string' || !['usuario', 'asistente'].includes(mensaje.remitente)
      || !Number.isFinite(Date.parse(mensaje.fecha)))) {
    throw new Error('El backend devolvió una respuesta no válida para el chat.')
  }
  return datos
}

export async function obtenerChat(signal?: AbortSignal): Promise<EstadoChat> {
  return validarChat(await peticionApi<EstadoChat>('/api/chat/', { signal }))
}

export async function enviarMensajeChat(datos: SolicitudChat, signal: AbortSignal): Promise<EstadoChat> {
  // El análisis semanal se procesa por separado; aquí esperamos solo la respuesta del chat.
  return validarChat(await peticionApi<EstadoChat>('/api/chat/', {
    method: 'POST', body: datos, signal, timeout: 195_000,
  }))
}

export async function enviarMensajeChatFlujo(datos: SolicitudChat, signal: AbortSignal,
  alFragmento: (contenido: string) => void): Promise<EstadoChat> {
  return peticionFlujoApi('/api/chat/flujo/', {
    method: 'POST', body: datos, signal, timeout: 195_000,
  }, async (respuesta) => {
    if (!respuesta.headers.get('Content-Type')?.includes('application/x-ndjson') || !respuesta.body) {
      throw new ErrorApi('Django devolvió una respuesta no válida para el chat.', respuesta.status)
    }
    const lector = respuesta.body.getReader()
    const decodificador = new TextDecoder()
    let pendiente = ''

    function procesarLinea(linea: string): EstadoChat | null {
      signal.throwIfAborted()
      if (!linea.trim()) return null
      let evento
      try { evento = JSON.parse(linea) } catch {
        throw new ErrorApi('La respuesta del chat llegó incompleta. Intenta nuevamente.')
      }
      if (evento?.tipo === 'fragmento') {
        if (typeof evento.contenido !== 'string') throw new ErrorApi('El chat recibió un fragmento no válido.')
        alFragmento(evento.contenido)
      }
      if (evento?.tipo === 'error') {
        throw new ErrorApi(typeof evento.error === 'string' ? evento.error : 'No se pudo completar la respuesta.')
      }
      if (evento?.tipo === 'estado') return validarChat(evento.chat)
      // Inicio, latidos y metadatos no forman parte del mensaje visible.
      return null
    }

    try {
      while (true) {
        const { value, done } = await lector.read()
        pendiente += done ? decodificador.decode() : decodificador.decode(value, { stream: true })
        let salto
        while ((salto = pendiente.indexOf('\n')) !== -1) {
          const linea = pendiente.slice(0, salto)
          pendiente = pendiente.slice(salto + 1)
          const estado = procesarLinea(linea)
          if (estado) return estado
        }
        if (done) {
          const estado = procesarLinea(pendiente)
          if (estado) return estado
          throw new ErrorApi('La conexión se interrumpió antes de completar la respuesta. Tu mensaje se conserva; puedes reintentar.')
        }
      }
    } finally {
      await lector.cancel().catch(() => undefined)
      lector.releaseLock()
    }
  })
}
