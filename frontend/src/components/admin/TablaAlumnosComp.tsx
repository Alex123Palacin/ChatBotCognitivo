import { Link, useNavigate } from 'react-router-dom'
import type { Alumno } from '../../types/alumno'
import { formatearFecha } from '../../utils/fechas'

function TablaAlumnosComp({ alumnos, hayRegistrados }: { alumnos: Alumno[]; hayRegistrados: boolean }) {
  const navigate = useNavigate()
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm shadow-slate-100">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-slate-100 bg-slate-50/70 text-xs font-medium text-slate-500">
          <tr>
            <th scope="col" className="px-5 py-4">Estudiante</th>
            <th scope="col" className="px-5 py-4">Actividad</th>
            <th scope="col" className="px-5 py-4">Primer mensaje</th>
            <th scope="col" className="px-5 py-4">Mensajes</th>
            <th scope="col" className="px-5 py-4">Reportes</th>
            <th scope="col" className="px-5 py-4"><span className="sr-only">Ver estudiante</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {alumnos.map((alumno) => (
            <tr key={alumno.id} className="cursor-pointer transition hover:bg-blue-50/40" onClick={(event) => {
              if (!(event.target as HTMLElement).closest('a')) navigate(`/administrador/alumnos/${alumno.id}`)
            }}>
              <td className="px-5 py-5"><p className="font-medium text-slate-900">{alumno.nombre || 'Estudiante'}</p><p className="mt-1 text-xs text-slate-500">{alumno.email}</p></td>
              <td className="px-5 py-5">
                <span className={`whitespace-nowrap text-xs ${alumno.en_linea ? 'text-emerald-700' : 'text-slate-500'}`}>{alumno.en_linea ? 'Activo recientemente' : 'Sin actividad reciente'}</span>
                <p className="mt-1 whitespace-nowrap text-xs text-slate-400">{formatearFecha(alumno.ultima_actividad, true)}</p>
              </td>
              <td className="px-5 py-5 whitespace-nowrap text-slate-600">{alumno.primer_mensaje ? formatearFecha(alumno.primer_mensaje, true) : 'Sin mensajes'}</td>
              <td className="px-5 py-5 text-slate-600">{alumno.mensajes_estudiante}</td>
              <td className="px-5 py-5 whitespace-nowrap text-slate-600">{alumno.reportes_total}</td>
              <td className="px-5 py-5"><Link to={`/administrador/alumnos/${alumno.id}`} className="whitespace-nowrap font-semibold text-blue-600 hover:underline">Ver análisis</Link></td>
            </tr>
          ))}
          {alumnos.length === 0 && <tr><td colSpan={6} className="px-5 py-10 text-center text-sm text-slate-500">{hayRegistrados ? 'No hay estudiantes que coincidan con los filtros.' : 'Todavía no hay estudiantes registrados.'}</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

export default TablaAlumnosComp
