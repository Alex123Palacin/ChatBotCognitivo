import { Menu } from 'lucide-react'
import IconButtonUI from '../ui/IconButtonUI'
import logo from '../assets/robot-junior.png'

interface CabeceraProps {
  abrirMenu: () => void
}

function CabeceraChatComp({ abrirMenu }: CabeceraProps) {
  return (
    <header className="z-10 flex shrink-0 items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 py-4 sm:px-7 md:px-9">
      <IconButtonUI etiqueta="Abrir menú" onClick={abrirMenu} className="-ml-2 md:hidden" aria-haspopup="dialog">
        <Menu size={21} />
      </IconButtonUI>
      <img src={logo} alt="Robot de Chatbot Cognitivo" className="size-12 shrink-0 object-contain sm:size-14" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="text-base font-semibold tracking-tight">Chatbot Cognitivo</p>
          <span className="text-[11px] font-medium text-blue-600">Tu espacio personal</span>
        </div>
        <p className="mt-1 truncate text-xs text-slate-500 sm:text-[13px]">Estoy aquí para escucharte y ayudarte con tus estudios.</p>
      </div>
    </header>
  )
}

export default CabeceraChatComp
