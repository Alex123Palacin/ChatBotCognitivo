export interface MensajeChat {
  id: string
  contenido: string
  remitente: 'usuario' | 'asistente'
  fecha: Date
  resultado?: ResultadoCuestionario | null
}

export interface OpcionPregunta {
  valor: string
  texto: string
}

export interface PreguntaChat {
  id: string
  texto: string
  opciones: OpcionPregunta[]
  indicador?: string
  numero?: number
  total?: number
}

interface Puntaje {
  id: string
  nombre: string
  promedio: number | null
  respondidas: number
  total: number
  dimension?: string
}

export interface ResultadoCuestionario {
  instrumento: string
  periodo: string
  respondidas: number
  total: number
  indicadores: Puntaje[]
  dimensiones: Puntaje[]
  respuestas: { id: string; pregunta: string; valor: number | null }[]
  nota: string
}

export interface SolicitudChat {
  sesion_id: string | null
  mensaje: string
  pregunta_id: string | null
  opcion?: string
}

export interface RespuestaChat {
  sesion_id: string
  contenido: string
  pregunta: PreguntaChat | null
  resultado: ResultadoCuestionario | null
}
