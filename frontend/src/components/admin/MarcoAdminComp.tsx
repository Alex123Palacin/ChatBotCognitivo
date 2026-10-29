import { useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import IconButtonUI from '../../ui/IconButtonUI'

function MarcoAdminComp({ titulo, descripcion, children }: { titulo: string; descripcion: string; children: ReactNode }) {
  const { usuario, cerrarSesion } = useAuth()
  const navigate = useNavigate()
  const [saliendo, setSaliendo] = useState(false)
  const [error, setError] = useState('')

  async function salir() {
    if (saliendo) return
    setSaliendo(true)
    setError('')
    try {
      await cerrarSesion()
      navigate('/administrador', { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cerrar la sesión.')
    } finally {
      setSaliendo(false)
    }
  }

  return (
    <div className="min-h-dvh bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <header className="border-b border-slate-200 bg-white/95">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
          <Link to="/administrador" className="text-base font-semibold text-slate-900 sm:text-lg">Chatbot Cognitivo <span className="ml-2 inline-block text-xs font-normal text-slate-500">Administración</span></Link>
          <div className="flex items-center gap-3">
            <span className="max-w-52 truncate text-sm text-slate-500">{usuario?.nombre || usuario?.username}</span>
            <IconButtonUI etiqueta="Cerrar sesión" disabled={saliendo} onClick={() => { void salir() }}><LogOut size={19} /></IconButtonUI>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-10">
        <nav aria-label="Administración" className="mb-7"><Link to="/administrador" className="rounded-lg bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100">Estudiantes y reportes</Link></nav>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{titulo}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-500">{descripcion}</p>
        {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
        <div className="mt-7">{children}</div>
      </main>
    </div>
  )
}

export default MarcoAdminComp
