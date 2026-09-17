import { useState } from 'react'
import BarraLateralComp from '../components/BarraLateralComp'
import CabeceraChatComp from '../components/CabeceraChatComp'
import EntradaChatComp from '../components/EntradaChatComp'
import InicioChatComp from '../components/InicioChatComp'
import MensajeChatComp from '../components/MensajeChatComp'
import { useChatbot } from '../hooks/useChatbot'

function ChatbotPage() {
  const {
    mensajes, texto, setTexto, enviarMensaje,
    limpiarConversacion, finConversacionRef, entradaRef,
  } = useChatbot()
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <>
      <div className="flex h-dvh min-h-0 overflow-hidden bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
        <BarraLateralComp
          abierto={menuAbierto}
          cerrar={() => setMenuAbierto(false)}
          nuevaConversacion={limpiarConversacion}
          limpiarConversacion={limpiarConversacion}
          hayMensajes={mensajes.length > 0}
          tituloConversacion={mensajes.find((mensaje) => mensaje.remitente === 'usuario')?.contenido}
        />
        <main className="flex min-w-0 flex-1 flex-col">
          <CabeceraChatComp abrirMenu={() => setMenuAbierto(true)} />
          <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain [scrollbar-width:thin]">
            {mensajes.length === 0 ? (
              <div className="my-auto"><InicioChatComp alSeleccionar={enviarMensaje} /></div>
            ) : (
              <div className="mx-auto w-full max-w-3xl px-4 py-7 sm:px-6 sm:py-9">
                <div className="mb-8 flex items-center gap-4" aria-hidden="true"><span className="h-px flex-1 bg-slate-200/70" /><span className="text-[10px] font-medium tracking-wider text-slate-400 uppercase">Hoy</span><span className="h-px flex-1 bg-slate-200/70" /></div>
                <div role="log" aria-label="Conversación con Chatbot Cognitivo" aria-live="polite" aria-relevant="additions" className="space-y-6">
                  {mensajes.map((mensaje) => <MensajeChatComp key={mensaje.id} mensaje={mensaje} />)}
                </div>
              </div>
            )}
            <div ref={finConversacionRef} />
          </div>
          <EntradaChatComp texto={texto} cambiarTexto={setTexto} enviar={enviarMensaje} entradaRef={entradaRef} />
        </main>
      </div>
    </>
  )
}

export default ChatbotPage
