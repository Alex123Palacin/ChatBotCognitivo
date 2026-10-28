export function formatearFecha(valor: string | null, incluirHora = false): string {
  if (!valor) return 'Sin actividad'
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return 'Fecha no disponible'
  return fecha.toLocaleString('es-PE', {
    timeZone: 'America/Lima', day: '2-digit', month: 'short', year: 'numeric',
    ...(incluirHora ? { hour: '2-digit', minute: '2-digit' } : {}),
  })
}

export function formatearPeriodo(inicio: string, fin: string | null): string {
  return `${formatearFecha(inicio, true)} — ${fin ? formatearFecha(fin, true) : 'En curso'}`
}

export function formatearTiempoDesde(valor: string | null, ahora = Date.now()): string {
  if (!valor) return 'Sin mensajes'
  const inicio = Date.parse(valor)
  if (!Number.isFinite(inicio)) return 'Fecha no disponible'
  const minutos = Math.max(0, Math.floor((ahora - inicio) / 60_000))
  if (minutos < 1) return 'Menos de un minuto'
  const dias = Math.floor(minutos / 1440)
  const horas = Math.floor((minutos % 1440) / 60)
  const restantes = minutos % 60
  const cantidad = (numero: number, unidad: string) => `${numero} ${unidad}${numero === 1 ? '' : 's'}`
  if (dias > 0) return cantidad(dias, 'día') + (horas > 0 ? ` y ${cantidad(horas, 'hora')}` : '')
  if (horas > 0) return cantidad(horas, 'hora') + (restantes > 0 ? ` y ${cantidad(restantes, 'minuto')}` : '')
  return cantidad(minutos, 'minuto')
}
