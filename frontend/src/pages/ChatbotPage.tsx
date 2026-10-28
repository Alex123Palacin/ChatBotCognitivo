import { useState } from 'react'
import BarraLateralComp from '../components/BarraLateralComp'
import CabeceraChatComp from '../components/CabeceraChatComp'
import EntradaChatComp from '../components/EntradaChatComp'
import InicioChatComp from '../components/InicioChatComp'
import MensajeChatComp from '../components/MensajeChatComp'
import EstadoEscribiendoComp from '../components/EstadoEscribiendoComp'
import { useChatbot } from '../hooks/useChatbot'
import { formatearFecha } from '../utils/fechas'

function ChatbotPage() {
  const { chat, mensajes, texto, setTexto, enviarMensaje, recargarChat,
    finConversacionRef, entradaRef, cargando, cargandoHistorial, respuestaParcial, error, reintento } = useChatbot()
  const [menuAbierto, setMenuAbierto] = useState(false)

  return (
    <div className="flex h-dvh min-h-0 overflow-hidden bg-linear-to-br from-slate-50 via-blue-50/30 to-indigo-50/40">
      <BarraLateralComp abierto={menuAbierto} cerrar={() => setMenuAbierto(false)} />
      <main className="flex min-w-0 flex-1 flex-col">
        <CabeceraChatComp abrirMenu={() => setMenuAbierto(true)} />
        <div className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain [scrollbar-width:thin]">
          {cargandoHistorial && !chat ? <p role="status" className="m-auto p-6 text-sm text-slate-500">Recuperando tu conversación…</p> : mensajes.length === 0 ? (
            <div className="my-auto"><InicioChatComp /></div>
          ) : (
            <div className="mx-auto w-full max-w-3xl px-4 py-7 sm:px-6 sm:py-9">
              <div role="log" aria-label="Conversación con Chatbot Cognitivo" aria-live="polite" aria-relevant="additions" className="space-y-6">
                {mensajes.map((mensaje, indice) => (
                  <div key={mensaje.id}>
                    {(indice === 0 || formatearFecha(mensajes[indice - 1].fecha) !== formatearFecha(mensaje.fecha)) && (
                      <div className="mb-7 flex items-center gap-4">
                        <span className="h-px flex-1 bg-slate-200/70" />
                        <span className="text-[10px] font-medium tracking-wider text-slate-400 uppercase">{formatearFecha(mensaje.fecha)}</span>
                        <span className="h-px flex-1 bg-slate-200/70" />
                      </div>
                    )}
                    <MensajeChatComp mensaje={mensaje} />
                  </div>
                ))}
                {respuestaParcial?.contenido && <MensajeChatComp mensaje={respuestaParcial} />}
              </div>
              {cargando && !respuestaParcial?.contenido && <EstadoEscribiendoComp />}
            </div>
          )}
          <div ref={finConversacionRef} />
        </div>
        {error && (
          <div role="alert" className="mx-auto w-full max-w-3xl px-5 pt-3 text-sm text-red-700">
            <p>{error}</p>
            {reintento && !cargando
              ? <button type="button" onClick={() => { void enviarMensaje(true) }} className="mt-2 min-h-10 rounded-lg px-3 font-semibold underline focus-visible:outline-2 focus-visible:outline-blue-600">Reintentar respuesta</button>
              : !chat && <button type="button" onClick={() => { void recargarChat() }} className="mt-2 min-h-10 rounded-lg px-3 font-semibold underline">Volver a conectar</button>}
          </div>
        )}
        <EntradaChatComp texto={texto} cambiarTexto={setTexto} enviar={() => { void enviarMensaje() }} entradaRef={entradaRef} cargando={cargando || !chat || Boolean(reintento)} />
      </main>
    </div>
  )
}

export default ChatbotPage
