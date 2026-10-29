import type { ReactNode } from 'react'

function MarcoAuthComp({ titulo, descripcion, children }: { titulo: string; descripcion: string; children: ReactNode }) {
  return (
    <main className="flex min-h-dvh min-w-0 items-start justify-center sm:items-center bg-linear-to-br from-slate-50 via-blue-50/60 to-indigo-50 px-4 py-6 sm:px-5 sm:py-10">
      <div className="w-full min-w-0 max-w-md">
        <p className="mb-6 text-center text-lg font-semibold text-slate-900">Chatbot Cognitivo</p>
        <section className="rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm shadow-blue-100 sm:p-9">
          <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">{descripcion}</p>
          <div className="mt-7">{children}</div>
        </section>
        <p className="mt-6 text-center text-xs [overflow-wrap:anywhere] leading-relaxed text-slate-500">Un espacio de conversación para acompañar tu bienestar académico.</p>
      </div>
    </main>
  )
}

export default MarcoAuthComp
