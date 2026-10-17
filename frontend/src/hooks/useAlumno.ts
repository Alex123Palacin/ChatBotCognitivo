import { useCallback } from 'react'
import { obtenerDetalleAlumno } from '../api/alumnosApi'
import { useDatosAdmin } from './useDatosAdmin'

export function useAlumno(id: number) {
  const cargar = useCallback((signal: AbortSignal) => {
    if (!Number.isInteger(id) || id < 1) return Promise.reject(new Error('El estudiante solicitado no es válido.'))
    return obtenerDetalleAlumno(id, signal)
  }, [id])
  return useDatosAdmin(cargar)
}
