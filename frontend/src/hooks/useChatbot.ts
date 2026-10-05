import { useEffect, useRef, useState } from 'react'
import { borrarConversacion, enviarMensajeChat } from '../api/chatbotApi'
import type { MensajeChat, OpcionPregunta, PreguntaChat } from '../types/chatbot'

export function useChatbot() {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [texto, setTexto] = useState('')
  const [pregunta, setPregunta] = useState<PreguntaChat | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const sesionId = useRef<string | null>(null)
  const peticion = useRef<AbortController | null>(null)
  const finConversacionRef = useRef<HTMLDivElement>(null)
  const entradaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => () => peticion.current?.abort(), [])

  // Desplaza la conversación hasta el último mensaje.
  useEffect(() => {
    if (mensajes.length === 0) {
      finConversacionRef.current?.parentElement?.scrollTo({ top: 0, behavior: 'instant' })
      return
    }
    finConversacionRef.current?.scrollIntoView({ block: 'end' })
  }, [mensajes, cargando])

  async function enviarMensaje(sugerencia?: string, opcion?: string) {
    const contenido = (sugerencia ?? texto).trim()
    if (!contenido || peticion.current) return
    if (contenido.length > 2000) {
      setError('Escribe un mensaje de hasta 2000 caracteres.')
      return
    }
    const controlador = new AbortController()
    peticion.current = controlador
    setCargando(true)
    setError('')

    const mensajeUsuario: MensajeChat = {
      id: crypto.randomUUID(),
      contenido,
      remitente: 'usuario',
      fecha: new Date(),
    }

    setMensajes((actuales) => [...actuales, mensajeUsuario])
    setTexto('')
    try {
      const respuesta = await enviarMensajeChat({
        sesion_id: sesionId.current, mensaje: contenido, pregunta_id: pregunta?.id ?? null, opcion,
      }, controlador.signal)
      if (controlador.signal.aborted) return
      sesionId.current = respuesta.sesion_id
      setPregunta(respuesta.pregunta)
      setMensajes((actuales) => [...actuales, {
        id: crypto.randomUUID(), contenido: respuesta.contenido,
        remitente: 'asistente', fecha: new Date(), resultado: respuesta.resultado,
      }])
    } catch (fallo) {
      if (!controlador.signal.aborted) {
        setError(fallo instanceof Error ? fallo.message : 'No se pudo enviar el mensaje.')
        setMensajes((actuales) => actuales.filter((mensaje) => mensaje.id !== mensajeUsuario.id))
        if (!opcion) setTexto(contenido)
      }
    } finally {
      if (peticion.current === controlador) {
        peticion.current = null
        setCargando(false)
        entradaRef.current?.focus({ preventScroll: true })
      }
    }
  }

  function limpiarConversacion() {
    peticion.current?.abort()
    peticion.current = null
    const anterior = sesionId.current
    sesionId.current = null
    setMensajes([])
    setTexto('')
    setPregunta(null)
    setCargando(false)
    setError('')
    entradaRef.current?.focus({ preventScroll: true })
    if (anterior) {
      void borrarConversacion(anterior).catch(() => {
        setError('Se limpió la pantalla, pero no se pudo borrar la sesión del servidor. Caducará tras dos horas de inactividad.')
      })
    }
  }

  function marcarOpcion(opcion: OpcionPregunta) {
    void enviarMensaje(opcion.texto, opcion.valor)
  }

  return {
    mensajes, texto, setTexto, enviarMensaje, limpiarConversacion,
    pregunta, marcarOpcion, cargando, error,
    finConversacionRef, entradaRef,
  }
}
