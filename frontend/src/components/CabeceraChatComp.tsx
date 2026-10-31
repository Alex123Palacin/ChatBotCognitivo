import { Menu } from 'lucide-react'
import IconButtonUI from '../ui/IconButtonUI'

interface CabeceraProps {
  abrirMenu: () => void
}

function CabeceraChatComp({ abrirMenu }: CabeceraProps) {
  return (
    <div className="flex shrink-0 px-3 pt-3 md:hidden">
      <IconButtonUI etiqueta="Abrir menú" onClick={abrirMenu} aria-haspopup="dialog">
        <Menu size={21} />
      </IconButtonUI>
    </div>
  )
}

export default CabeceraChatComp
