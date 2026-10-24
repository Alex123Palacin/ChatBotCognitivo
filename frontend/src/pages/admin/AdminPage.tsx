import { useState } from 'react'
import MarcoAdminComp from '../../components/admin/MarcoAdminComp'
import EstadoCargaComp from '../../components/admin/EstadoCargaComp'
import TablaAlumnosComp from '../../components/admin/TablaAlumnosComp'
import DescargarEvaluacionComp from '../../components/admin/DescargarEvaluacionComp'
import { useAlumnos } from '../../hooks/useAlumnos'
import InputUI from '../../ui/InputUI'

function AdminPage() {
  const { alumnos, cargando, error, refrescar } = useAlumnos()
  const [busqueda, setBusqueda] = useState('')
  const [soloActivos, setSoloActivos] = useState(false)
  const filtro = busqueda.trim().toLowerCase()
  const activos = alumnos.filter((alumno) => alumno.en_linea).length
  const visibles = alumnos.filter((alumno) => (!soloActivos || alumno.en_linea)
    && `${alumno.nombre} ${alumno.email}`.toLowerCase().includes(filtro))
  const tarjetas = [
    { titulo: 'Todos los estudiantes', cantidad: alumnos.length, descripcion: 'Cuentas de estudiantes registradas', activos: false },
    { titulo: 'Activos recientemente', cantidad: activos, descripcion: 'Actividad registrada en los últimos 5 minutos', activos: true },
  ]

  return (
    <MarcoAdminComp titulo="Panel administrativo" descripcion="Selecciona un estudiante para ver el análisis actual de su conversación y sus reportes semanales. La información se actualiza cada 30 segundos.">
      <EstadoCargaComp cargando={cargando} error={error} reintentar={refrescar} />
      {!cargando && <>
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          {tarjetas.map((tarjeta) => (
            <button
              key={tarjeta.titulo}
              type="button"
              aria-pressed={soloActivos === tarjeta.activos}
              onClick={() => setSoloActivos(tarjeta.activos)}
              className={`rounded-2xl border p-5 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 ${soloActivos === tarjeta.activos ? 'border-blue-200 bg-blue-50/70' : 'border-slate-200 bg-white hover:bg-slate-50'}`}
            >
              <span className="block text-sm font-medium text-slate-600">{tarjeta.titulo}</span>
              <span className="mt-2 block text-3xl font-semibold text-slate-900">{tarjeta.cantidad}</span>
              <span className="mt-2 block text-xs text-slate-500">{tarjeta.descripcion}</span>
            </button>
          ))}
        </div>
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div className="w-full max-w-sm"><InputUI id="busqueda" etiqueta="Buscar estudiante" type="search" value={busqueda} onChange={(event) => setBusqueda(event.target.value)} placeholder="Nombre o Gmail" /></div>
          <p className="text-sm text-slate-500">{visibles.length} estudiantes visibles · {soloActivos ? 'Solo actividad reciente' : 'Todos los estudiantes'}</p>
        </div>
        <TablaAlumnosComp alumnos={visibles} hayRegistrados={alumnos.length > 0} />
        <div className="mt-6"><DescargarEvaluacionComp alumnos={visibles.map((alumno) => alumno.id)} /></div>
      </>}
    </MarcoAdminComp>
  )
}

export default AdminPage
