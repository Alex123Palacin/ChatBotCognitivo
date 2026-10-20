import { useCallback, useEffect, useRef, useState } from 'react'
import { enviarMensajeChatFlujo, obtenerChat } from '../api/chatbotApi'
import type { EstadoChat, MensajeChat, SolicitudChat } from '../types/chatbot'

export function useChatbot() {
  const [chat, setChat] = useState<EstadoChat | null>(null)
  const [texto, setTexto] = useState('')
  const [cargandoHistorial, setCargandoHistorial] = useState(true)
  const [enviando, setEnviando] = useState(false)
  const [respuestaParcial, setRespuestaParcial] = useState<MensajeChat | null>(null)
  const [error, setError] = useState('')
  const [reintento, setReintento] = useState<SolicitudChat | null>(null)
  const peticion = useRef<AbortController | null>(null)
  const ultimoEnvio = useRef<SolicitudChat | null>(null)
  const revision = useRef(0)
  const montado = useRef(false)
  const finConversacionRef = useRef<HTMLDivElement>(null)
  const entradaRef = useRef<HTMLTextAreaElement>(null)
  const mensajes = chat?.mensajes ?? []
  const cargando = enviando || Boolean(chat?.respuesta_pendiente)

  const actualizarEstado = useCallback((estado: EstadoChat) => {
    setChat(estado)
    const pendiente = estado.mensaje_pendiente
    const envioLocal = ultimoEnvio.current
    const enviado = envioLocal
      ? estado.mensajes.find((mensaje) => mensaje.clave_envio === envioLocal.clave_envio)
      : null
    if (pendiente) {
      // Otra pestaña puede haber enviado primero. Conservamos el texto rechazado
      // como borrador mientras se recupera la respuesta que sí está guardada.
      if (envioLocal && !enviado && pendiente.clave_envio !== envioLocal.clave_envio) {
        setTexto((actual) => actual || envioLocal.mensaje)
      }
      ultimoEnvio.current = { mensaje: pendiente.mensaje, clave_envio: pendiente.clave_envio }
      setReintento(pendiente.estado === 'error' ? ultimoEnvio.current : null)
      setError(pendiente.estado === 'error' ? 'La última respuesta no se completó. Tu mensaje está guardado; puedes reintentar.' : '')
      return
    }
    if (envioLocal) {
      if (!enviado && estado.programa_finalizado) {
        ultimoEnvio.current = null
        setReintento(null)
        setError('El periodo finalizó antes de guardar tu último mensaje. Tu historial sigue disponible.')
        return
      }
      if (!enviado || enviado.respuesta_estado !== 'respondido') {
        setReintento(envioLocal)
        return
      }
    }
    ultimoEnvio.current = null
    setReintento(null)
    setError('')
  }, [])

  useEffect(() => {
    montado.current = true
    const controlador = new AbortController()
    async function actualizar() {
      if (peticion.current) return
      const revisionLectura = ++revision.current
      try {
        const estado = await obtenerChat(controlador.signal)
        if (controlador.signal.aborted || peticion.current || revisionLectura !== revision.current) return
        actualizarEstado(estado)
      } catch (fallo) {
        if (!controlador.signal.aborted && revisionLectura === revision.current) setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu chat.')
      } finally {
        if (!controlador.signal.aborted) setCargandoHistorial(false)
      }
    }
    void actualizar()
    const intervalo = setInterval(() => { if (!document.hidden) void actualizar() }, 20_000)
    const alVolver = () => { if (!document.hidden) void actualizar() }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      montado.current = false
      controlador.abort()
      peticion.current?.abort()
      peticion.current = null
      clearInterval(intervalo)
      document.removeEventListener('visibilitychange', alVolver)
    }
  }, [actualizarEstado])

  const ultimoId = mensajes.at(-1)?.id
  useEffect(() => {
    finConversacionRef.current?.scrollIntoView({ block: 'end' })
  }, [ultimoId, cargando, respuestaParcial?.contenido])

  async function enviarMensaje(repetir = false) {
    if (!chat || (chat.programa_finalizado && !repetir) || cargando || peticion.current || (reintento && !repetir)) return
    const solicitud = repetir ? reintento : { mensaje: texto.trim(), clave_envio: crypto.randomUUID() }
    if (!solicitud?.mensaje) return
    if (solicitud.mensaje.length > 2000) {
      setError('Escribe un mensaje de hasta 2000 caracteres.')
      return
    }
    const controlador = new AbortController()
    revision.current += 1
    peticion.current = controlador
    setEnviando(true)
    setRespuestaParcial(null)
    setError('')
    ultimoEnvio.current = solicitud
    setReintento(solicitud)
    if (!repetir) {
      setTexto('')
      setChat((actual) => actual && ({ ...actual, mensajes: [...actual.mensajes, {
        id: solicitud.clave_envio, contenido: solicitud.mensaje, remitente: 'usuario',
        fecha: new Date().toISOString(), sesion_numero: actual.sesion_actual?.numero ?? 1,
      }] }))
    }
    try {
      const estado = await enviarMensajeChatFlujo(solicitud, controlador.signal, (contenido) => {
        if (!montado.current || controlador.signal.aborted || peticion.current !== controlador) return
        setRespuestaParcial((actual) => ({
          id: `respuesta-${solicitud.clave_envio}`, contenido: (actual?.contenido ?? '') + contenido,
          remitente: 'asistente', fecha: actual?.fecha ?? new Date().toISOString(),
          sesion_numero: chat.sesion_actual?.numero ?? chat.mensajes.at(-1)?.sesion_numero ?? 1,
        }))
      })
      if (!montado.current || controlador.signal.aborted) return
      actualizarEstado(estado)
    } catch (fallo) {
      if (!montado.current || controlador.signal.aborted) return
      setError(fallo instanceof Error ? fallo.message : 'No se pudo obtener la respuesta.')
      // Un corte de conexión no borra lo que el servidor ya guardó.
      try {
        const estado = await obtenerChat(controlador.signal)
        if (montado.current && !controlador.signal.aborted) {
          actualizarEstado(estado)
        }
      } catch { /* Se conserva la misma clave para reintentar sin duplicar mensajes. */ }
    } finally {
      if (peticion.current === controlador) {
        peticion.current = null
        if (montado.current) {
          setRespuestaParcial(null)
          setEnviando(false)
          entradaRef.current?.focus({ preventScroll: true })
        }
      }
    }
  }

  async function recargarChat() {
    if (peticion.current) return
    const revisionLectura = ++revision.current
    setCargandoHistorial(true)
    try {
      const estado = await obtenerChat()
      if (montado.current && revisionLectura === revision.current) actualizarEstado(estado)
    } catch (fallo) {
      if (montado.current) setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu chat.')
    } finally {
      if (montado.current) setCargandoHistorial(false)
    }
  }

  return { chat, mensajes, texto, setTexto, enviarMensaje, recargarChat,
    cargando, cargandoHistorial, respuestaParcial, error, reintento, finConversacionRef, entradaRef }
}
