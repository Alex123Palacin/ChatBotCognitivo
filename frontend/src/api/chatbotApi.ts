import { peticionApi } from './http.ts'
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
