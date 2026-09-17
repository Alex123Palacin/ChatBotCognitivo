import { Menu } from 'lucide-react'
import IconButtonUI from '../ui/IconButtonUI'

interface CabeceraProps {
  abrirMenu: () => void
}

function CabeceraChatComp({ abrirMenu }: CabeceraProps) {
  return (
    <header className="z-10 flex shrink-0 items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 py-4 sm:px-7 md:px-9">
      <IconButtonUI etiqueta="Abrir menú" onClick={abrirMenu} className="-ml-2 md:hidden" aria-haspopup="dialog">
        <Menu size={21} />
      </IconButtonUI>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-3">
          <p className="text-base font-semibold tracking-tight">Chatbot Cognitivo</p>
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-emerald-700">
            <span className="size-1.5 rounded-full bg-emerald-500" /> En línea
          </span>
        </div>
        <p className="mt-1 truncate text-xs text-slate-500 sm:text-[13px]">Estoy aquí para escucharte y ayudarte con tus estudios.</p>
      </div>
    </header>
  )
}

export default CabeceraChatComp
