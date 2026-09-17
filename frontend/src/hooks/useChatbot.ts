import { useEffect, useRef, useState } from 'react'
import type { MensajeChat } from '../types/chatbot'

export function useChatbot() {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [texto, setTexto] = useState('')
  const finConversacionRef = useRef<HTMLDivElement>(null)
  const entradaRef = useRef<HTMLTextAreaElement>(null)

  // Desplaza la conversación hasta el último mensaje.
  useEffect(() => {
    if (mensajes.length === 0) {
      finConversacionRef.current?.parentElement?.scrollTo({ top: 0, behavior: 'instant' })
      return
    }
    finConversacionRef.current?.scrollIntoView({ block: 'end' })
  }, [mensajes])

  function enviarMensaje(sugerencia?: string) {
    const contenido = (sugerencia ?? texto).trim()
    if (!contenido) return

    const mensajeUsuario: MensajeChat = {
      id: crypto.randomUUID(),
      contenido,
      remitente: 'usuario',
      fecha: new Date(),
    }

    const respuesta: MensajeChat = {
      id: crypto.randomUUID(),
      contenido: 'hola',
      remitente: 'asistente',
      fecha: new Date(),
    }

    setMensajes((actuales) => [...actuales, mensajeUsuario, respuesta])
    setTexto('')
    entradaRef.current?.focus({ preventScroll: true })
  }

  function limpiarConversacion() {
    setMensajes([])
    setTexto('')
    entradaRef.current?.focus({ preventScroll: true })
  }

  return {
    mensajes, texto, setTexto, enviarMensaje, limpiarConversacion,
    finConversacionRef, entradaRef,
  }
}
