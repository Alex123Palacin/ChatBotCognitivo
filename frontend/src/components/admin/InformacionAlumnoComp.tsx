import type { Alumno } from '../../types/alumno'
import { formatearFecha, formatearTiempoDesde } from '../../utils/fechas'

function InformacionAlumnoComp({ alumno }: { alumno: Alumno }) {
  const fechas = [
    { nombre: 'Inicio del acompañamiento', valor: alumno.inicio_programa ? formatearFecha(alumno.inicio_programa, true) : 'Aún no iniciado' },
    { nombre: 'Primer mensaje', valor: alumno.primer_mensaje ? formatearFecha(alumno.primer_mensaje, true) : 'Sin mensajes' },
    { nombre: 'Último mensaje', valor: alumno.ultimo_mensaje ? formatearFecha(alumno.ultimo_mensaje, true) : 'Sin mensajes' },
    { nombre: 'Última actividad', valor: formatearFecha(alumno.ultima_actividad, true) },
    { nombre: 'Tiempo desde el primer mensaje', valor: formatearTiempoDesde(alumno.primer_mensaje) },
  ]
  const cantidades = [
    { nombre: 'Días con mensajes', valor: alumno.dias_conversacion },
    { nombre: 'Mensajes del estudiante', valor: alumno.mensajes_estudiante },
    { nombre: 'Mensajes analizados', valor: alumno.mensajes_analizados },
    { nombre: 'Análisis pendientes', valor: alumno.analisis_pendientes },
  ]

  return (
    <section aria-label="Información del estudiante" className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm font-medium [overflow-wrap:anywhere]">Usuario: {alumno.username}</p>
        <span className={`rounded-full px-3 py-1 text-xs ${alumno.en_linea ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>{alumno.en_linea ? 'Activo recientemente' : 'Sin actividad reciente'}</span>
      </div>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {fechas.map((fecha) => <div key={fecha.nombre}><dt className="text-xs text-slate-500">{fecha.nombre}</dt><dd className="mt-1 text-sm font-medium text-slate-700">{fecha.valor}</dd></div>)}
      </dl>
      <dl className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {cantidades.map((cantidad) => <div key={cantidad.nombre} className="rounded-xl bg-slate-50 p-4"><dt className="text-xs text-slate-500">{cantidad.nombre}</dt><dd className="mt-1 text-xl font-semibold text-slate-900">{cantidad.valor}</dd></div>)}
      </dl>
      <p className="mt-4 text-xs leading-relaxed text-slate-500">Las fechas usan la hora de Lima. Los días con mensajes son fechas distintas de participación. El tiempo desde el primer mensaje incluye pausas e inactividad; no mide conversación continua. La actividad reciente corresponde a los últimos 5 minutos.</p>
    </section>
  )
}

export default InformacionAlumnoComp
