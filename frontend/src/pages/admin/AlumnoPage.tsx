import { Link, useParams } from 'react-router-dom'
import MarcoAdminComp from '../../components/admin/MarcoAdminComp'
import EstadoCargaComp from '../../components/admin/EstadoCargaComp'
import InformacionAlumnoComp from '../../components/admin/InformacionAlumnoComp'
import ReporteActualComp from '../../components/admin/ReporteActualComp'
import TarjetaReporteComp from '../../components/admin/TarjetaReporteComp'
import DescargarEvaluacionComp from '../../components/admin/DescargarEvaluacionComp'
import PerfilIndicadoresComp from '../../components/admin/PerfilIndicadoresComp'
import { useAlumno } from '../../hooks/useAlumno'

function AlumnoPage() {
  const { id } = useParams()
  const { datos, cargando, error, refrescar } = useAlumno(Number(id))
  return (
    <MarcoAdminComp titulo={datos?.alumno.nombre || 'Detalle del estudiante'} descripcion="Consulta la información registrada, la cobertura de los indicadores y el análisis actual de la conversación del estudiante.">
      <Link to="/administrador" className="mb-5 inline-block text-sm font-medium text-blue-600 hover:underline">← Volver a estudiantes</Link>
      <EstadoCargaComp cargando={cargando} error={error} reintentar={refrescar} />
      {datos && <div className="space-y-8">
        <InformacionAlumnoComp alumno={datos.alumno} />
        {datos.alumno.en_estudio ? <DescargarEvaluacionComp alumnos={[datos.alumno.id]} /> : <p className="text-sm text-slate-500">Esta cuenta no forma parte del reporte de investigación.</p>}
        {datos.reporte_actual ? <ReporteActualComp reporte={datos.reporte_actual} /> : (
          <section className="rounded-2xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold">Análisis actual de la conversación</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500">Todavía no hay mensajes del estudiante. El análisis aparecerá aquí a medida que participe en su chat.</p>
          </section>
        )}
        <section>
          <h2 className="mb-4 text-lg font-semibold">Historial de reportes</h2>
          {datos.reportes.length === 0 ? <p className="rounded-2xl border border-slate-200 bg-white p-6 text-sm leading-relaxed text-slate-500">Todavía no hay reportes guardados. Puedes consultar el análisis actual de la conversación desde aquí.</p> : <div className="grid gap-4 md:grid-cols-2">{datos.reportes.map((reporte) => <TarjetaReporteComp key={reporte.id} reporte={reporte} />)}</div>}
        </section>
        <PerfilIndicadoresComp perfil={datos.perfil_indicadores} />
      </div>}
    </MarcoAdminComp>
  )
}

export default AlumnoPage
