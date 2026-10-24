import type { DimensionReporte, Evidencia } from '../../types/reporte'
import { formatearFecha } from '../../utils/fechas'

const etiquetas: Record<Evidencia['senal'], string> = {
  dificultad: 'Dificultad expresada', recurso: 'Recurso de afrontamiento', ausencia_explicita: 'Ausencia expresada',
}

function DimensionReporteComp({ dimension }: { dimension: DimensionReporte }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <h2 className="border-b border-slate-100 bg-slate-50/70 px-5 py-4 text-lg font-semibold">{dimension.nombre}</h2>
      <div className="divide-y divide-slate-100">
        {dimension.indicadores.map((indicador) => (
          <div key={indicador.id} className="p-5">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-sm font-semibold text-slate-900">{indicador.nombre}</h3>
              <span className={`rounded-full px-2.5 py-1 text-xs ${indicador.evidencias.length ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>{indicador.evidencias.length ? 'Con evidencia' : 'Sin información suficiente'}</span>
            </div>
            {indicador.conclusion && <div className="mt-3 rounded-xl bg-blue-50/60 p-3"><p className="text-xs font-medium text-slate-500">Conclusión orientativa del indicador</p><p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-slate-700 [overflow-wrap:anywhere]">{indicador.conclusion}</p></div>}
            {indicador.evidencias.length === 0 ? (
              <p className="mt-3 text-sm leading-relaxed text-slate-500">El estudiante no aportó información suficiente sobre este indicador. Esto no demuestra ausencia de estrés.</p>
            ) : (
              <div className="mt-4 space-y-5">
                {indicador.evidencias.map((evidencia) => (
                  <article key={evidencia.id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                      <span>{etiquetas[evidencia.senal] ?? 'Información expresada'}</span>
                      <span>Mensaje #{evidencia.mensaje_id} · {formatearFecha(evidencia.fecha, true)}</span>
                    </div>
                    <p className="mt-3 text-xs font-medium text-slate-500">Fragmento del estudiante</p>
                    <blockquote className="mt-1 border-l-2 border-blue-200 pl-3 text-sm leading-relaxed text-slate-800 [overflow-wrap:anywhere]">“{evidencia.cita}”</blockquote>
                    <p className="mt-4 text-xs font-medium text-slate-500">Observación del sistema</p>
                    <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-slate-600 [overflow-wrap:anywhere]">{evidencia.observacion}</p>
                  </article>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

export default DimensionReporteComp
