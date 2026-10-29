import type { Alumno, SesionAlumno } from './alumno'

export interface ResumenReporte {
  id: number
  numero: number
  inicio: string
  fin: string
  estado: 'pendiente' | 'listo'
  mensajes_estudiante: number
  total_evidencias: number
  resumen: string
}

export interface Evidencia {
  id: number
  mensaje_id: string
  cita: string
  observacion: string
  senal: 'dificultad' | 'recurso' | 'ausencia_explicita'
  fecha: string
}

export interface IndicadorReporte {
  id: string
  nombre: string
  estado: 'con_evidencia' | 'sin_informacion'
  conclusion?: string
  evidencias: Evidencia[]
}

export interface DimensionReporte {
  id: string
  nombre: string
  indicadores: IndicadorReporte[]
}

export interface Reporte extends ResumenReporte {
  alumno: Alumno
  nota: string
  dimensiones: DimensionReporte[]
  perfil_indicadores: PerfilIndicadores
}

export interface CoberturaReporte {
  estado: 'sin_mensajes' | 'analisis_pendiente' | 'sin_evidencia' | 'parcial' | 'completa'
  indicadores_con_evidencia: number
  indicadores_totales: number
  dimensiones_con_evidencia: number
  dimensiones_totales: number
  puede_describir_indicadores: boolean
  mensaje: string
  indicadores_pendientes: string[]
  mensajes_analizados: number
  analisis_pendientes: number
}

export interface ReporteActual {
  numero: number | null
  inicio: string
  fin: string | null
  estado: 'en_curso' | 'finalizado'
  mensajes_estudiante: number
  total_evidencias: number
  resumen: string
  nota: string
  dimensiones: DimensionReporte[]
  cobertura: CoberturaReporte
}

export interface DetalleAlumno {
  alumno: Alumno
  sesiones: SesionAlumno[]
  reportes: ResumenReporte[]
  reporte_actual: ReporteActual | null
  perfil_indicadores: PerfilIndicadores
}

export interface PerfilIndicadores {
  indicadores: {
    id: string
    nombre: string
    dimension: 'estresores' | 'sintomas' | 'afrontamiento'
    frecuencia: number | null
    dificultad: boolean
    recurso: boolean
    ausencia_explicita: boolean
    con_evidencia: boolean
  }[]
  resumen: string
  mensajes_analizados: number
  analisis_pendientes: number
}
