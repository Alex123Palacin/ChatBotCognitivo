import { useEffect } from 'react'
import type { RefObject } from 'react'
import { ArrowUp } from 'lucide-react'
import IconButtonUI from '../ui/IconButtonUI'

interface EntradaChatProps {
  texto: string
  cambiarTexto: (texto: string) => void
  enviar: () => void
  cargando: boolean
  entradaRef: RefObject<HTMLTextAreaElement | null>
}

function EntradaChatComp({ texto, cambiarTexto, enviar, entradaRef, cargando }: EntradaChatProps) {
  useEffect(() => {
    const entrada = entradaRef.current
    if (!entrada) return
    entrada.style.height = 'auto'
    entrada.style.height = `${Math.min(entrada.scrollHeight, 144)}px`
  }, [texto, entradaRef])

  return (
    <footer className="z-10 shrink-0 px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))] sm:px-8 sm:pb-5">
      <div className="mx-auto max-w-3xl">
        <form onSubmit={(event) => { event.preventDefault(); enviar() }} className="rounded-2xl border border-slate-200 bg-white px-4 pt-3 pb-2 shadow-lg shadow-slate-200/30 transition focus-within:border-blue-300 focus-within:ring-3 focus-within:ring-blue-100/50 sm:px-5">
          <label htmlFor="mensaje" className="sr-only">Escribe tu mensaje</label>
          <textarea
            ref={entradaRef}
            id="mensaje"
            value={texto}
            onChange={(event) => cambiarTexto(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault()
                enviar()
              }
            }}
            placeholder="Escribe tu mensaje..."
            rows={1}
            readOnly={cargando}
            maxLength={2000}
            aria-describedby="ayuda-entrada"
            className="block max-h-36 min-h-10 w-full resize-none bg-transparent py-2 text-base leading-6 text-slate-700 outline-none placeholder:text-slate-400 sm:text-[15px]"
          />
          <div className="flex items-center justify-between gap-3">
            <p id="ayuda-entrada" className="text-[10px] text-slate-400"><span className="hidden sm:inline">Enter para enviar · Shift + Enter para una nueva línea</span><span className="sm:hidden">Una conversación a tu ritmo</span></p>
            <IconButtonUI etiqueta="Enviar mensaje" type="submit" disabled={!texto.trim() || cargando} className="size-9 rounded-xl bg-linear-to-br from-blue-600 to-indigo-500 text-white hover:text-white disabled:from-slate-200 disabled:to-slate-200 disabled:text-slate-400 disabled:opacity-100">
              <ArrowUp size={20} />
            </IconButtonUI>
          </div>
        </form>
        <p className="mt-3 text-center text-[10px] leading-4 text-slate-400">Chatbot Cognitivo · Bienestar Académico</p>
      </div>
    </footer>
  )
}

export default EntradaChatComp
