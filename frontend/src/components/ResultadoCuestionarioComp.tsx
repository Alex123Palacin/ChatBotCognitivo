import type { ResultadoCuestionario } from '../types/chatbot'

function ResultadoCuestionarioComp({ resultado }: { resultado: ResultadoCuestionario }) {
  const numero = (valor: number | null) => valor === null ? 'Incompleto' : `${valor.toLocaleString('es-PE', { maximumFractionDigits: 2 })} / 5`

  return (
    <section aria-label="Resultados del cuestionario" className="mt-4 rounded-2xl border border-blue-100 bg-white p-4 sm:p-5">
      <h2 className="text-base font-semibold text-slate-800">Tu resumen por indicadores</h2>
      <p className="mt-2 text-xs leading-5 text-slate-500">{resultado.periodo} · {resultado.respondidas} de {resultado.total} preguntas respondidas.</p>
      <div className="mt-4 space-y-3">
        {resultado.dimensiones.map((dimension) => (
          <div key={dimension.id} className="rounded-xl bg-slate-50 p-3">
            <div className="flex flex-wrap justify-between gap-2 text-sm font-semibold"><h3>{dimension.nombre}</h3><span>{numero(dimension.promedio)}</span></div>
            <dl className="mt-3 space-y-2">
              {resultado.indicadores.filter((indicador) => indicador.dimension === dimension.id).map((indicador) => (
                <div key={indicador.id} className="flex flex-wrap justify-between gap-2 text-xs text-slate-600"><dt>{indicador.nombre} ({indicador.respondidas}/{indicador.total})</dt><dd>{numero(indicador.promedio)}</dd></div>
              ))}
            </dl>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs leading-5 text-slate-600">{resultado.nota}</p>
      <details className="mt-4 text-xs text-slate-600">
        <summary className="cursor-pointer rounded py-2 font-semibold focus-visible:outline-2 focus-visible:outline-blue-600">Ver mis respuestas y cómo se calcula</summary>
        <p className="my-3 leading-5">Promedio del indicador = suma de sus dos respuestas ÷ 2. Cada dimensión promedia sus preguntas (4, 4 y 6). Solo se muestran promedios cuando todas las preguntas correspondientes están respondidas. La conversación abierta no añade puntos.</p>
        <ol className="list-inside list-decimal space-y-3">
          {resultado.respuestas.map((respuesta) => <li key={respuesta.id} className="leading-5">{respuesta.pregunta} <strong>{respuesta.valor === null ? 'Sin respuesta' : `${respuesta.valor} / 5`}</strong></li>)}
        </ol>
      </details>
    </section>
  )
}

export default ResultadoCuestionarioComp
