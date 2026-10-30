import MarcoAdminComp from '../../components/admin/MarcoAdminComp'
import EstadoCargaComp from '../../components/admin/EstadoCargaComp'
import TablaAlumnosComp from '../../components/admin/TablaAlumnosComp'
import DescargarEvaluacionComp from '../../components/admin/DescargarEvaluacionComp'
import { useAlumnos } from '../../hooks/useAlumnos'

function AdminPage() {
  const { alumnos, estudio, cargando, error, refrescar } = useAlumnos()
  return <MarcoAdminComp titulo="Panel administrativo" descripcion="Siete indicadores de análisis cualitativo, organizados en las tres dimensiones del proyecto.">
    <EstadoCargaComp cargando={cargando} error={error} reintentar={refrescar} />
    {!cargando && <>
      <div className="mb-6">
        <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5"><p className="text-sm font-medium text-blue-800">Casos seleccionados</p><p className="mt-2 text-3xl font-semibold">{estudio?.seleccionados ?? 0}</p><p className="mt-2 text-xs text-slate-600">{estudio ? '11 de septiembre de 2026, de 13:00 a 18:00 · Lima' : 'La muestra del estudio todavía no está configurada.'}</p></div>
      </div>
      <details className="mb-6 rounded-xl border border-slate-200 bg-white p-4 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">Dimensiones e indicadores</summary>
        <dl className="mt-4 grid gap-4 text-xs leading-6 sm:grid-cols-3">
          <div><dt className="font-semibold">Estresores académicos</dt><dd>Sobrecarga académica y presión del tiempo.</dd></div>
          <div><dt className="font-semibold">Síntomas</dt><dd>Síntomas físicos y psicológicos.</dd></div>
          <div><dt className="font-semibold">Estrategias de afrontamiento</dt><dd>Planificación, automotivación y búsqueda de soporte.</dd></div>
        </dl>
      </details>
      {estudio && estudio.seleccionados !== estudio.tamano && <p role="alert" className="mb-4 text-sm text-amber-800">La muestra guardada está incompleta. No se ha realizado un nuevo sorteo.</p>}
      <div className="mb-6"><DescargarEvaluacionComp alumnos={estudio && estudio.seleccionados === estudio.tamano ? alumnos.map(a => a.id) : []} /></div>
      <p className="mb-4 text-sm text-slate-500">{alumnos.length} estudiantes en el listado · La selección no cambia al actualizar la página.</p>
      <TablaAlumnosComp alumnos={alumnos} hayRegistrados={alumnos.length > 0} />
    </>}
  </MarcoAdminComp>
}

export default AdminPage
