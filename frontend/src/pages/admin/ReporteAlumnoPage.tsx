import { Link, useParams } from 'react-router-dom'
import MarcoAdminComp from '../../components/admin/MarcoAdminComp'
import EstadoCargaComp from '../../components/admin/EstadoCargaComp'
import DimensionReporteComp from '../../components/admin/DimensionReporteComp'
import { useReportes } from '../../hooks/useReportes'
import { formatearPeriodo } from '../../utils/fechas'

function ReporteAlumnoPage() {
  const { id } = useParams()
  const { datos, cargando, error, refrescar } = useReportes(Number(id))
  return (
    <MarcoAdminComp titulo={datos ? `Reporte · Semana ${datos.numero}` : 'Reporte semanal'} descripcion="Información obtenida de la conversación de esta semana, organizada según las dimensiones e indicadores del proyecto.">
      <Link to={datos ? `/administrador/alumnos/${datos.alumno.id}` : '/administrador'} className="mb-5 inline-block text-sm font-medium text-blue-600 hover:underline">← Volver al estudiante</Link>
      <EstadoCargaComp cargando={cargando} error={error} reintentar={refrescar} />
      {datos && <>
        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><h2 className="text-lg font-semibold [overflow-wrap:anywhere]">{datos.alumno.nombre}</h2><p className="mt-1 text-sm text-slate-500 [overflow-wrap:anywhere]">{datos.alumno.email}</p></div><span className={`rounded-full px-3 py-1.5 text-xs font-medium ${datos.estado === 'listo' ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-700'}`}>{datos.estado === 'listo' ? 'Reporte disponible' : 'Reporte en proceso'}</span></div>
          <p className="mt-4 text-xs leading-relaxed text-slate-500">{formatearPeriodo(datos.inicio, datos.fin)} · Hora de Lima</p>
          <p className="mt-2 text-xs text-slate-500">{datos.mensajes_estudiante} mensajes del estudiante · {datos.total_evidencias} fragmentos de evidencia</p>
          <h3 className="mt-6 text-sm font-semibold">Resumen semanal</h3>
          <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-600 [overflow-wrap:anywhere]">{datos.resumen || (datos.estado === 'pendiente' ? 'El sistema está procesando la conversación. Este reporte se actualizará automáticamente.' : 'No se dispone de información suficiente en este periodo.')}</p>
          {datos.nota && <p className="mt-5 rounded-xl bg-slate-50 p-4 text-xs leading-relaxed text-slate-500">{datos.nota}</p>}
        </section>
        <div className="space-y-5">{datos.dimensiones.map((dimension) => <DimensionReporteComp key={dimension.id} dimension={dimension} />)}</div>
      </>}
    </MarcoAdminComp>
  )
}

export default ReporteAlumnoPage
