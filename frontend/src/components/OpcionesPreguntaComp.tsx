import type { OpcionPregunta, PreguntaChat } from '../types/chatbot'

interface OpcionesProps {
  pregunta: PreguntaChat
  alMarcar: (opcion: OpcionPregunta) => void
  deshabilitado: boolean
}

function OpcionesPreguntaComp({ pregunta, alMarcar, deshabilitado }: OpcionesProps) {
  return (
    <fieldset disabled={deshabilitado} aria-label={pregunta.texto} className="mt-5 min-w-0 rounded-2xl border border-blue-100 bg-blue-50/60 p-4">
      <legend className="px-2 text-xs font-semibold text-blue-700">
        {pregunta.numero ? `Pregunta ${pregunta.numero} de ${pregunta.total} · ${pregunta.indicador}` : 'Puedes responder aquí o escribir en el chat'}
      </legend>
      {pregunta.numero && <p className="mb-3 text-xs text-slate-500">Piensa en las últimas dos semanas.</p>}
      <div className="flex flex-wrap gap-2">
        {pregunta.opciones.map((opcion) => (
          <button key={opcion.valor} type="button" onClick={() => alMarcar(opcion)} className="min-h-11 rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm text-blue-800 transition hover:border-blue-500 hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-wait disabled:opacity-50">
            {opcion.texto}
          </button>
        ))}
      </div>
    </fieldset>
  )
}

export default OpcionesPreguntaComp
