import type { CoberturaReporte, ReporteActual } from '../../types/reporte'
import { formatearPeriodo } from '../../utils/fechas'
import DimensionReporteComp from './DimensionReporteComp'

const etiquetas: Record<CoberturaReporte['estado'], string> = {
  sin_mensajes: 'Sin mensajes en esta semana',
  analisis_pendiente: 'Análisis en curso',
  sin_evidencia: 'Sin evidencia suficiente',
  parcial: 'Cobertura parcial de los indicadores',
  completa: 'Información para describir los 7 indicadores',
}

function ReporteActualComp({ reporte }: { reporte: ReporteActual }) {
  const { cobertura } = reporte
  return (
    <section aria-label="Análisis actual de la conversación" className="space-y-5">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">Análisis actual · Semana {reporte.numero}</h2>
          <span className="rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700">{reporte.estado === 'en_curso' ? 'Semana en curso' : 'Semana finalizada'}</span>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-500">{formatearPeriodo(reporte.inicio, reporte.fin)}</p>
        <p className="mt-3 text-sm leading-relaxed text-slate-500">El análisis se actualiza con los mensajes procesados. El reporte semanal se conserva al finalizar el periodo.</p>
        <div className={`mt-5 rounded-xl border p-4 ${cobertura.estado === 'completa' ? 'border-blue-200 bg-blue-50/70' : 'border-slate-200 bg-slate-50/70'}`}>
          <h3 className="text-sm font-semibold text-slate-800">{etiquetas[cobertura.estado]}</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{cobertura.mensaje}</p>
          <p className="mt-3 text-xs font-medium text-slate-600">{cobertura.indicadores_con_evidencia} de {cobertura.indicadores_totales} indicadores con evidencia · {cobertura.dimensiones_con_evidencia} de {cobertura.dimensiones_totales} dimensiones con evidencia</p>
          <progress aria-label="Indicadores con evidencia en la conversación" value={cobertura.indicadores_con_evidencia} max={cobertura.indicadores_totales} className="mt-3 h-2 w-full accent-blue-600" />
          {cobertura.indicadores_pendientes.length > 0 && <p className="mt-3 text-xs leading-relaxed text-slate-500">Sin evidencia suficiente: {cobertura.indicadores_pendientes.join(', ')}.</p>}
          <p className="mt-3 text-xs leading-relaxed text-slate-500">{cobertura.puede_describir_indicadores ? 'Los fragmentos disponibles permiten describir los indicadores que tienen evidencia.' : 'Aún falta evidencia para describir los indicadores de esta conversación.'} Esta descripción es orientativa y no establece un diagnóstico ni un nivel de estrés.</p>
        </div>
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-500">
          <span>{reporte.mensajes_estudiante} mensajes del estudiante esta semana</span>
          <span>{cobertura.mensajes_analizados} mensajes analizados</span>
          <span>{cobertura.analisis_pendientes} análisis pendientes</span>
          <span>{reporte.total_evidencias} fragmentos de evidencia</span>
        </div>
        <h3 className="mt-6 text-sm font-semibold">Resumen de la conversación</h3>
        <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600 [overflow-wrap:anywhere]">{reporte.resumen || 'Todavía no se dispone de información suficiente en este periodo.'}</p>
        {reporte.nota && <p className="mt-4 text-xs leading-relaxed text-slate-500">{reporte.nota}</p>}
      </div>
      <div className="space-y-5">{reporte.dimensiones.map((dimension) => <DimensionReporteComp key={dimension.id} dimension={dimension} />)}</div>
    </section>
  )
}

export default ReporteActualComp
