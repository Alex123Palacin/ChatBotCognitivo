import { Link } from 'react-router-dom'
import type { ResumenReporte } from '../../types/reporte'
import { formatearPeriodo } from '../../utils/fechas'

function TarjetaReporteComp({ reporte }: { reporte: ResumenReporte }) {
  const listo = reporte.estado === 'listo'
  return (
    <article className="flex flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm shadow-slate-100">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">Reporte de conversación</h3>
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${listo ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-700'}`}>{listo ? 'Disponible' : 'Procesando'}</span>
      </div>
      <p className="mt-2 text-xs leading-relaxed text-slate-500">{formatearPeriodo(reporte.inicio, reporte.fin)}</p>
      <p className="mt-4 line-clamp-3 text-sm leading-relaxed text-slate-600">{reporte.resumen || (listo ? 'No se dispone de información suficiente en este periodo.' : 'El sistema está analizando la conversación de este periodo.')}</p>
      <p className="mt-4 text-xs text-slate-500">{reporte.mensajes_estudiante} mensajes del estudiante · {reporte.total_evidencias} fragmentos de evidencia</p>
      <Link to={`/administrador/reportes/${reporte.id}`} className="mt-5 self-start rounded-lg text-sm font-semibold text-blue-600 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-600">Ver reporte</Link>
    </article>
  )
}

export default TarjetaReporteComp
