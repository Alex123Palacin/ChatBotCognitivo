import { useCallback } from 'react'
import { obtenerReporte } from '../api/reportesApi'
import { useDatosAdmin } from './useDatosAdmin'

export function useReportes(id: number) {
  const cargar = useCallback((signal: AbortSignal) => {
    if (!Number.isInteger(id) || id < 1) return Promise.reject(new Error('El reporte solicitado no es válido.'))
    return obtenerReporte(id, signal)
  }, [id])
  return useDatosAdmin(cargar)
}
