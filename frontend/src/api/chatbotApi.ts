import type { RespuestaChat, SolicitudChat } from '../types/chatbot'

async function obtenerCsrf(signal?: AbortSignal): Promise<string> {
  const respuesta = await fetch('/api/csrf/', { credentials: 'same-origin', signal })
  if (!respuesta.ok) throw new Error('No se pudo conectar con el backend. Comprueba que Django esté iniciado.')
  const datos = await respuesta.json()
  return datos.csrfToken
}

export async function enviarMensajeChat(datos: SolicitudChat, signal: AbortSignal): Promise<RespuestaChat> {
  // El frontend solo llama a Django; Django se comunica con Ollama.
  const limite = AbortSignal.any([signal, AbortSignal.timeout(195_000)])
  try {
    const csrf = await obtenerCsrf(limite)
    const respuesta = await fetch('/api/chat/', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(datos), signal: limite,
    })
    const contenido = await respuesta.json().catch(() => null)
    if (!respuesta.ok) throw new Error(contenido?.error || 'El servidor no pudo responder. Comprueba que Django y Ollama estén iniciados.')
    return contenido
  } catch (error) {
    if (signal.aborted) throw error
    if (limite.aborted) throw new Error('La IA está tardando demasiado. Intenta enviar tu mensaje otra vez.')
    if (error instanceof TypeError) throw new Error('No se pudo conectar con el backend. Comprueba que Django esté iniciado.')
    throw error
  }
}

export async function borrarConversacion(sesionId: string): Promise<void> {
  const signal = AbortSignal.timeout(10_000)
  const csrf = await obtenerCsrf(signal)
  const respuesta = await fetch(`/api/chat/${sesionId}/`, {
    method: 'DELETE', headers: { 'X-CSRFToken': csrf }, credentials: 'same-origin', signal,
  })
  if (!respuesta.ok) throw new Error('No se pudo eliminar la conversación del servidor.')
}
