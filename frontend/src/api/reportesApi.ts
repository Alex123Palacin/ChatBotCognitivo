import { peticionApi } from './http.ts'
import type { Reporte, ResumenReporte } from '../types/reporte'

export function obtenerReportesAlumno(id: number, signal?: AbortSignal): Promise<{ reportes: ResumenReporte[] }> {
  return peticionApi(`/api/admin/alumnos/${id}/reportes/`, { signal })
}

export function obtenerReporte(id: number, signal?: AbortSignal): Promise<Reporte> {
  return peticionApi(`/api/admin/reportes/${id}/`, { signal })
}
