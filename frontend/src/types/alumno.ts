export interface Alumno {
  id: number
  nombre: string
  username: string
  email: string
  ultima_actividad: string | null
  en_linea: boolean
  semana_actual: number | null
  reportes_total: number
  primer_mensaje: string | null
  ultimo_mensaje: string | null
  inicio_programa: string | null
  dias_conversacion: number
  mensajes_estudiante: number
  mensajes_analizados: number
  analisis_pendientes: number
}

export interface SesionAlumno {
  id: number
  numero: number
  inicio: string
  fin: string | null
  estado: 'activa' | 'pendiente' | 'cerrada'
  reporte_id: number | null
}
