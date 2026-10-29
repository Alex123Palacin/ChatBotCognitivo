import type { PerfilIndicadores } from '../../types/reporte'

const grupos = [
  { id: 'estresores', nombre: 'Estresores académicos' },
  { id: 'sintomas', nombre: 'Síntomas' },
  { id: 'afrontamiento', nombre: 'Estrategias de afrontamiento' },
]
const etiquetas = ['Nunca', 'Rara vez', 'Algunas veces', 'Casi siempre', 'Siempre']

export default function PerfilIndicadoresComp({ perfil }: { perfil: PerfilIndicadores }) {
  return <section aria-label="Perfil de los siete indicadores" className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
    <h2 className="text-xl font-semibold">Perfil de los siete indicadores</h2>
    <p className="mt-2 text-sm leading-6 text-slate-500">Las barras representan frecuencias expresadas en la conversación. Las etiquetas describen la evidencia cualitativa disponible.</p>
    <div className="mt-6 space-y-7">
      {grupos.map(grupo => <div key={grupo.id}>
        <h3 className="mb-4 text-sm font-semibold text-slate-800">{grupo.nombre}</h3>
        <div className="space-y-5">{perfil.indicadores.filter(i => i.dimension === grupo.id).map(i => <div key={i.id} className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,13rem)_minmax(0,1fr)] sm:gap-4">
          <div className="min-w-0"><p className="text-sm font-medium text-slate-800">{i.nombre}</p><div className="mt-1 flex flex-wrap gap-1 text-[11px]">
            {i.dificultad && <span className="rounded bg-amber-50 px-2 py-1 text-amber-800">Dificultad relatada</span>}
            {i.recurso && <span className="rounded bg-teal-50 px-2 py-1 text-teal-800">Recurso utilizado</span>}
            {i.ausencia_explicita && <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">Ausencia explícita</span>}
            {!i.con_evidencia && <span className="text-slate-500">Sin información</span>}
          </div></div>
          <div className="min-w-0 self-center">
            {i.frecuencia !== null ? <>
              <div role="meter" aria-label={`Frecuencia de ${i.nombre}`} aria-valuemin={1} aria-valuemax={5} aria-valuenow={i.frecuencia} aria-valuetext={etiquetas[i.frecuencia - 1]} className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div className={`h-full rounded-full ${i.dimension === 'afrontamiento' ? 'bg-teal-500' : 'bg-blue-500'}`} style={{ width: `${i.frecuencia * 20}%` }} />
              </div>
              <p className="mt-1 text-xs text-slate-600">{i.frecuencia} de 5 · {etiquetas[i.frecuencia - 1]}</p>
            </> : <div className="rounded-lg border border-dashed border-slate-200 px-3 py-2 text-xs text-slate-500">Frecuencia no precisada</div>}
          </div>
        </div>)}</div>
      </div>)}
    </div>
    <p className="mt-6 text-xs leading-6 text-slate-500">1 Nunca · 2 Rara vez · 3 Algunas veces · 4 Casi siempre · 5 Siempre. En estresores y síntomas, un valor mayor describe más frecuencia de dificultad; en afrontamiento, más uso del recurso. No se suman en un nivel global de estrés.</p>
    <div className="mt-6 rounded-xl bg-blue-50/70 p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-slate-900">Síntesis de lo expresado</h3>
      <p className="mt-2 text-sm leading-7 text-slate-700">{perfil.resumen || 'Todavía no hay información para describir los indicadores.'}</p>
    </div>
  </section>
}
