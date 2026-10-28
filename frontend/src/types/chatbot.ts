export interface MensajeChat {
  id: string
  contenido: string
  remitente: 'usuario' | 'asistente'
  fecha: string
  sesion_numero: number
  clave_envio?: string
  respuesta_estado?: 'pendiente' | 'respondido' | 'error'
}

export interface SesionSemanal {
  id: number
  numero: number
  inicio: string
  fin: string | null
  estado: 'activa' | 'pendiente' | 'cerrada'
  reporte_id: number | null
}

export interface MensajePendiente {
  clave_envio: string
  mensaje: string
  estado: 'pendiente' | 'error'
}

export interface EstadoChat {
  mensajes: MensajeChat[]
  sesiones: SesionSemanal[]
  sesion_actual: SesionSemanal | null
  programa_finalizado: boolean
  respuesta_pendiente: boolean
  mensaje_pendiente?: MensajePendiente | null
}

export interface SolicitudChat {
  mensaje: string
  clave_envio: string
}
