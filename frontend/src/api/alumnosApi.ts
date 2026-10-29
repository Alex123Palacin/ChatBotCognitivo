import { peticionApi } from './http.ts'
import type { Alumno, Estudio } from '../types/alumno'
import type { DetalleAlumno } from '../types/reporte'

export function obtenerAlumnos(signal?: AbortSignal): Promise<{ alumnos: Alumno[]; estudio: Estudio | null }> {
  return peticionApi('/api/admin/alumnos/', { signal })
}

export function obtenerDetalleAlumno(id: number, signal?: AbortSignal): Promise<DetalleAlumno> {
  return peticionApi(`/api/admin/alumnos/${id}/`, { signal })
}
