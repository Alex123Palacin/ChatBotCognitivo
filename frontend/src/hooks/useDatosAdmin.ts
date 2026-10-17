import { useEffect, useState } from 'react'

// Mantiene los listados y reportes actualizados sin recargar la página.
export function useDatosAdmin<T>(cargar: (signal: AbortSignal) => Promise<T>) {
  const [resultado, setResultado] = useState<{
    cargar: typeof cargar | null
    revision: number
    datos: T | null
    error: string
  }>({ cargar: null, revision: -1, datos: null, error: '' })
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    let cancelado = false
    let peticion: AbortController | null = null
    let enCurso = false
    async function actualizar() {
      if (enCurso) return
      enCurso = true
      peticion = new AbortController()
      try {
        const resultado = await cargar(peticion.signal)
        if (!cancelado) setResultado({ cargar, revision, datos: resultado, error: '' })
      } catch (fallo) {
        if (!cancelado && !peticion.signal.aborted) {
          setResultado((anterior) => ({
            cargar, revision,
            datos: anterior.cargar === cargar && anterior.revision === revision ? anterior.datos : null,
            error: fallo instanceof Error ? fallo.message : 'No se pudo cargar la información.',
          }))
        }
      } finally {
        enCurso = false
      }
    }

    void actualizar()
    const intervalo = window.setInterval(() => { void actualizar() }, 30_000)
    return () => {
      cancelado = true
      peticion?.abort()
      window.clearInterval(intervalo)
    }
  }, [cargar, revision])

  const cargando = resultado.cargar !== cargar || resultado.revision !== revision
  return {
    datos: cargando ? null : resultado.datos,
    cargando,
    error: cargando ? '' : resultado.error,
    refrescar: () => setRevision((actual) => actual + 1),
  }
}
