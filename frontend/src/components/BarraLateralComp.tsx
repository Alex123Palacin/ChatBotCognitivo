import { useEffect, useRef, useState } from 'react'
import { LogOut, MessageCircle, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import IconButtonUI from '../ui/IconButtonUI'

interface BarraLateralProps {
  abierto: boolean
  cerrar: () => void
}

function BarraLateralComp({ abierto, cerrar }: BarraLateralProps) {
  const { usuario, cerrarSesion } = useAuth()
  const aplicaRetencion = usuario?.terminos_aceptados === true && usuario.retencion_dias === 30
  const [error, setError] = useState('')
  const [saliendo, setSaliendo] = useState(false)
  const dialogoRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    if (abierto && !dialogoRef.current?.open) dialogoRef.current?.showModal()
    if (!abierto && dialogoRef.current?.open) dialogoRef.current?.close()
  }, [abierto])

  async function salir() {
    setSaliendo(true)
    setError('')
    try { await cerrarSesion() }
    catch (fallo) { setError(fallo instanceof Error ? fallo.message : 'No se pudo cerrar tu sesión.') }
    finally { setSaliendo(false) }
  }

  const contenido = (
    <>
      <Link to="/chat" onClick={cerrar} className="rounded-lg focus-visible:outline-2 focus-visible:outline-blue-600">
        <span className="text-[15px] leading-5 font-semibold tracking-tight">Chatbot<span className="block text-slate-500">Cognitivo</span></span>
      </Link>
      <div className="mt-10">
        <p className="mb-3 px-2 text-[10px] font-semibold tracking-[0.13em] text-slate-500 uppercase">Tu espacio</p>
        <div aria-current="page" className="flex items-start gap-3 rounded-xl border border-blue-100/80 bg-blue-50 px-3 py-3.5 text-blue-700">
          <MessageCircle size={18} className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-[13px] font-semibold">Mi conversación</p>
            <p className="mt-1 text-xs text-slate-500">Un espacio para conversar a tu ritmo</p>
          </div>
        </div>
      </div>
      <div className="mt-8">
        <p className="mb-3 px-2 text-[10px] font-semibold tracking-[0.13em] text-slate-500 uppercase">Sobre tu conversación</p>
        <p className="px-2 text-xs leading-5 text-slate-500">Puedes seguir compartiendo lo que necesites, sin etapas ni un orden obligatorio.</p>
        <p className="mt-3 px-2 text-xs leading-5 text-slate-500">{aplicaRetencion ? 'Tus mensajes nuevos se eliminan automáticamente al cumplir 30 días desde su envío, según los términos que aceptaste.' : 'Tu historial actual se conserva. La política de 30 días se aplica a las cuentas nuevas que la aceptan al registrarse.'}</p>
      </div>
      <div className="mt-auto border-t border-slate-200 pt-4">
        <p className="truncate px-3 text-xs font-semibold text-slate-700">{usuario?.nombre || 'Estudiante'}</p>
        <p className="mt-1 truncate px-3 text-[11px] text-slate-500" title={usuario?.username}>{usuario?.username}</p>
        <button type="button" onClick={() => { void salir() }} disabled={saliendo} className="mt-3 flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-[13px] text-slate-500 transition hover:bg-white hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-blue-600 disabled:opacity-40">
          <LogOut size={17} /> {saliendo ? 'Cerrando sesión…' : 'Cerrar sesión'}
        </button>
        {error && <p role="alert" className="px-3 text-xs text-red-700">{error}</p>}
      </div>
    </>
  )

  return (
    <>
      <aside aria-label="Navegación del chat" className="hidden h-full w-64 shrink-0 flex-col overflow-y-auto border-r border-slate-200/80 bg-slate-50/90 px-5 py-7 md:flex xl:w-72 xl:px-6">{contenido}</aside>
      <dialog ref={dialogoRef} aria-label="Menú del chat" onCancel={cerrar} onClick={(event) => { if (event.target === event.currentTarget) cerrar() }} className="fixed inset-0 m-0 h-dvh max-h-none w-full max-w-none bg-transparent backdrop:bg-slate-900/35 backdrop:backdrop-blur-sm">
        <div className="relative flex h-full w-[min(19rem,85vw)] flex-col overflow-y-auto bg-slate-50 px-5 py-7 shadow-xl">
          <IconButtonUI etiqueta="Cerrar menú" onClick={cerrar} className="absolute top-6 right-2"><X size={19} /></IconButtonUI>
          {contenido}
        </div>
      </dialog>
    </>
  )
}

export default BarraLateralComp
