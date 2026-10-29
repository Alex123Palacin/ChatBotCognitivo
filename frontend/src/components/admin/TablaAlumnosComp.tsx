import { Link } from 'react-router-dom'
import type { Alumno } from '../../types/alumno'
import { formatearFecha } from '../../utils/fechas'

function TablaAlumnosComp({ alumnos, hayRegistrados }: { alumnos: Alumno[]; hayRegistrados: boolean }) {
  const vacio = hayRegistrados ? 'No hay estudiantes en esta selección.' : 'Todavía no hay estudiantes registrados.'
  return <div className="min-w-0">
    <div className="grid gap-3 md:hidden">
      {alumnos.map(a => <article key={a.id} className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-base font-semibold [overflow-wrap:anywhere]">{a.username}</h2>
        {a.nombre && a.nombre !== a.username && <p className="mt-1 text-sm text-slate-500 [overflow-wrap:anywhere]">{a.nombre}</p>}
        <dl className="mt-4 grid grid-cols-2 gap-4 text-xs"><div><dt className="text-slate-500">Mensajes del estudiante</dt><dd className="mt-1 text-lg font-semibold">{a.mensajes_estudiante}</dd></div><div><dt className="text-slate-500">Reportes</dt><dd className="mt-1 text-lg font-semibold">{a.reportes_total}</dd></div><div className="col-span-2"><dt className="text-slate-500">Primer mensaje</dt><dd className="mt-1 text-sm">{a.primer_mensaje ? formatearFecha(a.primer_mensaje, true) : 'Sin mensajes'}</dd></div></dl>
        <Link to={`/administrador/alumnos/${a.id}`} className="mt-4 flex min-h-11 items-center justify-center rounded-xl bg-blue-50 px-4 text-sm font-semibold text-blue-700">Ver análisis<span className="sr-only"> de {a.username}</span></Link>
      </article>)}
      {!alumnos.length && <p className="rounded-xl bg-white p-5 text-sm text-slate-500">{vacio}</p>}
    </div>
    <div className="hidden max-w-full overflow-x-auto rounded-2xl border border-slate-200 bg-white md:block">
      <table className="w-full text-left text-sm"><thead className="border-b border-slate-100 bg-slate-50 text-xs text-slate-500"><tr><th className="px-5 py-4">Usuario</th><th className="px-5 py-4">Primer mensaje</th><th className="px-5 py-4">Mensajes</th><th className="px-5 py-4">Reportes</th><th className="px-5 py-4"><span className="sr-only">Ver estudiante</span></th></tr></thead>
        <tbody className="divide-y divide-slate-100">{alumnos.map(a => <tr key={a.id} className="hover:bg-blue-50/40"><td className="max-w-56 px-5 py-5"><p className="font-medium [overflow-wrap:anywhere]">{a.username}</p>{a.nombre !== a.username && <p className="mt-1 text-xs text-slate-500 [overflow-wrap:anywhere]">{a.nombre}</p>}</td><td className="px-5 py-5">{a.primer_mensaje ? formatearFecha(a.primer_mensaje, true) : 'Sin mensajes'}</td><td className="px-5 py-5">{a.mensajes_estudiante}</td><td className="px-5 py-5">{a.reportes_total}</td><td className="px-5 py-5"><Link to={`/administrador/alumnos/${a.id}`} className="inline-flex min-h-11 items-center font-semibold text-blue-600">Ver análisis<span className="sr-only"> de {a.username}</span></Link></td></tr>)}
          {!alumnos.length && <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500">{vacio}</td></tr>}
        </tbody>
      </table>
    </div>
  </div>
}

export default TablaAlumnosComp
