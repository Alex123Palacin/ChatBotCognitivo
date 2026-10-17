import { useCallback } from 'react'
import { obtenerAlumnos } from '../api/alumnosApi'
import { useDatosAdmin } from './useDatosAdmin'

export function useAlumnos() {
  const cargar = useCallback((signal: AbortSignal) => obtenerAlumnos(signal), [])
  const estado = useDatosAdmin(cargar)
  return { ...estado, alumnos: estado.datos?.alumnos ?? [] }
}
