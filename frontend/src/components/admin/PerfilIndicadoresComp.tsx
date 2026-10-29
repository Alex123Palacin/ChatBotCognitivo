import type { PerfilIndicadores } from '../../types/reporte'
import { formatearFecha } from '../../utils/fechas'

const grupos = [
  { id: 'estresores', nombre: 'Estresores académicos' },
  { id: 'sintomas', nombre: 'Síntomas' },
  { id: 'afrontamiento', nombre: 'Estrategias de afrontamiento' },
]
const coloresEstado: Record<PerfilIndicadores['indicadores'][number]['estado'], string> = {
  dificultad_reportada: 'bg-amber-50 text-amber-900 ring-amber-200',
  recurso_reportado: 'bg-teal-50 text-teal-900 ring-teal-200',
  ausencia_explicita: 'bg-blue-50 text-blue-900 ring-blue-200',
  relato_mixto: 'bg-violet-50 text-violet-900 ring-violet-200',
  no_mencionado: 'bg-slate-100 text-slate-700 ring-slate-200',
  analisis_pendiente: 'bg-orange-50 text-orange-900 ring-orange-200',
  sin_mensajes: 'bg-slate-100 text-slate-700 ring-slate-200',
}

export default function PerfilIndicadoresComp({ perfil }: { perfil: PerfilIndicadores }) {
  return <section aria-label="Perfil cualitativo de los siete indicadores" className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
    <h2 className="text-xl font-semibold">Perfil cualitativo de los siete indicadores</h2>
    <p className="mt-2 text-sm leading-6 text-slate-500">Cada indicador describe lo expresado por el estudiante y las citas que respaldan su análisis.</p>
    {perfil.analisis_pendientes > 0 && <p role="status" className="mt-4 rounded-xl bg-amber-50 p-3 text-xs leading-6 text-amber-900">Quedan {perfil.analisis_pendientes} mensajes por analizar. El perfil muestra la evidencia disponible y puede ampliarse.</p>}
    <div className="mt-6 space-y-7">
      {grupos.map(grupo => <div key={grupo.id}>
        <h3 className="mb-4 text-sm font-semibold text-slate-800">{grupo.nombre}</h3>
        <div className="space-y-3">{perfil.indicadores.filter(i => i.dimension === grupo.id).map(i => <article key={i.id} className="min-w-0 rounded-xl border border-slate-200 p-4 sm:p-5">
          <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
            <h4 className="min-w-0 text-sm font-semibold text-slate-800 [overflow-wrap:anywhere]">{i.nombre}</h4>
            <span className={`max-w-full rounded-full px-3 py-1 text-xs leading-5 ring-1 ring-inset ${coloresEstado[i.estado]}`}>{i.etiqueta}</span>
          </div>
          <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600 [overflow-wrap:anywhere]">{i.analisis}</p>
          {i.evidencias.length > 0 && <details className="mt-4 border-t border-slate-100 pt-3">
            <summary className="min-h-9 cursor-pointer text-xs font-semibold leading-6 text-blue-700">Citas de respaldo ({i.evidencias.length})</summary>
            <div className="mt-2 space-y-3">{i.evidencias.map((evidencia, indice) => <figure key={`${i.id}-${indice}`} className="min-w-0 rounded-lg bg-slate-50 p-3">
              <blockquote className="whitespace-pre-line border-l-2 border-blue-200 pl-3 text-sm leading-7 text-slate-700 [overflow-wrap:anywhere]">“{evidencia.cita}”</blockquote>
              <figcaption className="mt-2 space-y-1 text-xs leading-6 text-slate-500 [overflow-wrap:anywhere]">
                <p>{evidencia.observacion}</p>
                <p>Mensaje del estudiante · {formatearFecha(evidencia.fecha, true)}</p>
              </figcaption>
            </figure>)}</div>
            {i.total_evidencias > i.evidencias.length && <p className="mt-2 text-xs leading-6 text-slate-500">Se muestran {i.evidencias.length} de {i.total_evidencias} evidencias. Puedes consultar las demás en el análisis de la conversación.</p>}
          </details>}
        </article>)}</div>
      </div>)}
    </div>
    <p className="mt-6 text-xs leading-6 text-slate-500">Lo no mencionado se registra como tal. La ausencia de una dificultad se indica únicamente cuando el estudiante la expresó.</p>
    <div className="mt-6 rounded-xl bg-blue-50/70 p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-slate-900">Síntesis de lo expresado</h3>
      <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-700 [overflow-wrap:anywhere]">{perfil.resumen || 'Aún no hay conversación registrada para elaborar la síntesis.'}</p>
    </div>
  </section>
}
