import { ErrorApi, peticionFlujoApi } from './http.ts'

export function obtenerEvaluacion(alumnos: number[]): Promise<Blob> {
  if (!alumnos.length || alumnos.length > 100 || alumnos.some((id) => !Number.isSafeInteger(id) || id <= 0)) {
    return Promise.reject(new ErrorApi('Selecciona entre 1 y 100 estudiantes para descargar.'))
  }
  const ids = [...new Set(alumnos)].join(',')
  return peticionFlujoApi(`/api/admin/evaluacion.xlsx?alumnos=${ids}`, { timeout: 60_000 }, async (respuesta) => {
    if (!respuesta.headers.get('Content-Type')?.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
      throw new ErrorApi('El servidor no devolvió un archivo Excel válido.', respuesta.status)
    }
    return respuesta.blob()
  })
}
