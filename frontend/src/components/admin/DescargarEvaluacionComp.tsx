import { useState } from 'react'
import { Download } from 'lucide-react'
import { obtenerEvaluacion } from '../../api/exportacionApi'
import BotonUI from '../../ui/BotonUI'

function DescargarEvaluacionComp({ alumnos }: { alumnos: number[] }) {
  const [descargando, setDescargando] = useState(false)
  const [error, setError] = useState('')

  async function descargar() {
    if (descargando) return
    setDescargando(true)
    setError('')
    try {
      const archivo = await obtenerEvaluacion(alumnos)
      const url = URL.createObjectURL(archivo)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `evaluacion-conversacion-${new Date().toISOString().slice(0, 10)}.xlsx`
      document.body.appendChild(enlace)
      enlace.click()
      enlace.remove()
      setTimeout(() => URL.revokeObjectURL(url), 10_000)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo descargar el archivo.')
    } finally {
      setDescargando(false)
    }
  }

  return <div className="space-y-2">
    <BotonUI onClick={descargar} disabled={descargando || !alumnos.length || alumnos.length > 110} aria-busy={descargando}>
      <Download size={17} aria-hidden="true" />{descargando ? 'Preparando Excel…' : `Descargar Excel · ${alumnos.length} ${alumnos.length === 1 ? 'estudiante' : 'estudiantes'}`}
    </BotonUI>
    <p className="max-w-xl text-xs leading-relaxed text-slate-500">Excel de {alumnos.length} {alumnos.length === 1 ? 'estudiante' : 'estudiantes'}: ID, usuario y frecuencias declaradas por indicador en su periodo de actividad. Los datos insuficientes aparecen como «Sin información».</p>
    {alumnos.length > 110 && <p className="text-xs text-amber-700">La descarga admite hasta 110 estudiantes.</p>}
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
  </div>
}

export default DescargarEvaluacionComp
