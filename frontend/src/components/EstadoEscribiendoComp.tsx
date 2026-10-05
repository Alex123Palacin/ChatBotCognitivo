function EstadoEscribiendoComp() {
  return (
    <div role="status" className="mt-5 flex items-center gap-3 text-xs text-slate-500">
      <div aria-hidden="true" className="flex gap-1.5 rounded-2xl border border-slate-200 bg-white px-4 py-4">
        {[0, 1, 2].map((indice) => <span key={indice} style={{ animationDelay: `${indice * 150}ms` }} className="size-1.5 rounded-full bg-blue-500 motion-safe:animate-bounce" />)}
      </div>
      <span>Chatbot Cognitivo está escribiendo…</span>
    </div>
  )
}

export default EstadoEscribiendoComp
