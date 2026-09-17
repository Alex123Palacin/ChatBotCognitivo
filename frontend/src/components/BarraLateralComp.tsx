import { useEffect, useRef } from 'react'
import { MessageCircle, Plus, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import BotonUI from '../ui/BotonUI'
import IconButtonUI from '../ui/IconButtonUI'

interface BarraLateralProps {
  abierto: boolean
  cerrar: () => void
  nuevaConversacion: () => void
  limpiarConversacion: () => void
  tituloConversacion?: string
  hayMensajes: boolean
}

function BarraLateralComp({ abierto, cerrar, nuevaConversacion, limpiarConversacion, tituloConversacion, hayMensajes }: BarraLateralProps) {
  const dialogoRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    if (abierto && !dialogoRef.current?.open) dialogoRef.current?.showModal()
    if (!abierto && dialogoRef.current?.open) dialogoRef.current?.close()
  }, [abierto])

  function ejecutar(accion: () => void) {
    dialogoRef.current?.close()
    cerrar()
    accion()
  }

  const contenido = (
    <>
      <Link to="/chat" onClick={cerrar} aria-label="Bienestar Académico, inicio" className="flex items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-blue-600">
        <span className="text-[15px] leading-5 font-semibold tracking-tight">Bienestar<span className="block text-slate-500">Académico</span></span>
      </Link>

      <BotonUI onClick={() => ejecutar(nuevaConversacion)} className="mt-10 w-full"><Plus size={18} /> Nuevo chat</BotonUI>

      <div className="mt-9">
        <p className="mb-3 px-2 text-[10px] font-semibold tracking-[0.13em] text-slate-500 uppercase">Tu espacio</p>
        <div aria-current="true" className="flex items-start gap-3 rounded-xl border border-blue-100/80 bg-blue-50 px-3 py-3.5 text-blue-700">
          <MessageCircle size={18} className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <p className="text-[13px] font-semibold">Conversación actual</p>
            <p className="mt-1 truncate text-xs text-slate-500" title={tituloConversacion}>{tituloConversacion || 'Un nuevo comienzo'}</p>
          </div>
          <span className="mt-1.5 ml-auto size-1.5 shrink-0 rounded-full bg-blue-500" />
        </div>
      </div>

      <div className="mt-auto border-t border-slate-200 pt-4">
        <button type="button" onClick={() => ejecutar(limpiarConversacion)} disabled={!hayMensajes} className="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-[13px] text-slate-500 transition hover:bg-white hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-40">
          <Trash2 size={17} /> Limpiar conversación
        </button>
        <p className="mt-5 px-3 text-[10px] tracking-wide text-slate-400">BIENESTAR ACADÉMICO · 2026</p>
      </div>
    </>
  )

  return (
    <>
      <aside aria-label="Navegación del chat" className="hidden h-full w-64 shrink-0 flex-col border-r border-slate-200/80 bg-slate-50/90 px-5 py-7 md:flex xl:w-72 xl:px-6">{contenido}</aside>
      <dialog ref={dialogoRef} aria-label="Menú del chat" onCancel={cerrar} onClick={(event) => { if (event.target === event.currentTarget) cerrar() }} className="fixed inset-0 m-0 h-dvh max-h-none w-full max-w-none bg-transparent backdrop:bg-slate-900/35 backdrop:backdrop-blur-sm">
        <div className="relative flex h-full w-[min(19rem,85vw)] flex-col bg-slate-50 px-5 py-7 shadow-xl">
          <IconButtonUI etiqueta="Cerrar menú" onClick={cerrar} className="absolute top-6 right-2"><X size={19} /></IconButtonUI>
          {contenido}
        </div>
      </dialog>
    </>
  )
}

export default BarraLateralComp
