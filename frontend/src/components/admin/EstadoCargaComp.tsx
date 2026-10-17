function EstadoCargaComp({ cargando, error, reintentar }: { cargando: boolean; error: string; reintentar: () => void }) {
  if (cargando) return <p role="status" className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">Cargando información…</p>
  if (!error) return null
  return <div role="alert" className="mb-5 rounded-2xl border border-red-100 bg-white p-5 text-sm text-red-700">{error}<button type="button" onClick={reintentar} className="ml-3 font-semibold underline underline-offset-2">Reintentar</button></div>
}

export default EstadoCargaComp
