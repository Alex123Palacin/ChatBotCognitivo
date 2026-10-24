import { Link, useParams } from 'react-router-dom'
import MarcoAdminComp from '../../components/admin/MarcoAdminComp'
import EstadoCargaComp from '../../components/admin/EstadoCargaComp'
import InformacionAlumnoComp from '../../components/admin/InformacionAlumnoComp'
import ReporteActualComp from '../../components/admin/ReporteActualComp'
import TarjetaReporteComp from '../../components/admin/TarjetaReporteComp'
import DescargarEvaluacionComp from '../../components/admin/DescargarEvaluacionComp'
import { useAlumno } from '../../hooks/useAlumno'
import { formatearPeriodo } from '../../utils/fechas'

const estados = { activa: 'En curso', pendiente: 'Próxima semana', cerrada: 'Finalizada' }

function AlumnoPage() {
  const { id } = useParams()
  const { datos, cargando, error, refrescar } = useAlumno(Number(id))
  return (
    <MarcoAdminComp titulo={datos?.alumno.nombre || 'Detalle del estudiante'} descripcion="Consulta la información registrada, la cobertura de los indicadores y el análisis actual de la conversación del estudiante.">
      <Link to="/administrador" className="mb-5 inline-block text-sm font-medium text-blue-600 hover:underline">← Volver a estudiantes</Link>
      <EstadoCargaComp cargando={cargando} error={error} reintentar={refrescar} />
      {datos && <div className="space-y-8">
        <InformacionAlumnoComp alumno={datos.alumno} />
        <DescargarEvaluacionComp alumnos={[datos.alumno.id]} />
        {datos.reporte_actual ? <ReporteActualComp reporte={datos.reporte_actual} /> : (
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold">Análisis actual de la conversación</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">Todavía no hay mensajes del estudiante. El análisis aparecerá aquí a medida que participe en su chat.</p>
          </section>
        )}
        <section>
          <h2 className="mb-4 text-lg font-semibold">Sesiones semanales</h2>
          {datos.sesiones.length === 0 ? <p className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">Las cuatro semanas comienzan cuando el estudiante envía su primer mensaje.</p> : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {datos.sesiones.map((sesion) => (
                <article key={sesion.id} className={`rounded-2xl border p-4 ${sesion.estado === 'activa' ? 'border-blue-200 bg-blue-50/70' : 'border-slate-200 bg-white'}`}>
                  <div className="flex items-center justify-between gap-2"><h3 className="text-sm font-semibold">Semana {sesion.numero}</h3><span className={`text-xs ${sesion.estado === 'activa' ? 'text-blue-600' : 'text-slate-500'}`}>{estados[sesion.estado]}</span></div>
                  <p className="mt-3 text-xs leading-relaxed text-slate-500">{formatearPeriodo(sesion.inicio, sesion.fin)}</p>
                </article>
              ))}
            </div>
          )}
        </section>
        <section>
          <h2 className="mb-4 text-lg font-semibold">Reportes semanales acumulados</h2>
          {datos.reportes.length === 0 ? <p className="rounded-2xl border border-slate-200 bg-white p-6 text-sm leading-relaxed text-slate-500">El primer reporte semanal se conservará al cerrar automáticamente la primera semana. Puedes consultar el análisis actual desde ahora.</p> : <div className="grid gap-4 md:grid-cols-2">{datos.reportes.map((reporte) => <TarjetaReporteComp key={reporte.id} reporte={reporte} />)}</div>}
        </section>
      </div>}
    </MarcoAdminComp>
  )
}

export default AlumnoPage
