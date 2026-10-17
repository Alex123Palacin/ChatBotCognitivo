import type { MensajeChat } from '../types/chatbot'

function MensajeChatComp({ mensaje }: { mensaje: MensajeChat }) {
  const esUsuario = mensaje.remitente === 'usuario'
  const hora = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Lima' }).format(new Date(mensaje.fecha))

  return (
    <article aria-label={`Mensaje de ${esUsuario ? 'ti' : 'Chatbot Cognitivo'}`} className={`flex items-start gap-2.5 sm:gap-3 ${esUsuario ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] min-w-0 sm:max-w-[76%]">
        <p className={`mb-1.5 text-[11px] font-medium text-slate-500 ${esUsuario ? 'text-right' : ''}`}>{esUsuario ? 'Tú' : 'Chatbot Cognitivo'}</p>
        <div className={`rounded-2xl px-4 py-3.5 text-[14px] leading-7 wrap-anywhere whitespace-pre-wrap shadow-xs sm:px-5 ${esUsuario ? 'rounded-tr-sm bg-linear-to-br from-blue-600 to-indigo-500 text-white' : 'rounded-tl-sm border border-slate-200/90 bg-white text-slate-700'}`}>
          {mensaje.contenido}
        </div>
        <time dateTime={mensaje.fecha} className={`mt-1.5 block text-[10px] text-slate-500 ${esUsuario ? 'text-right' : ''}`}>{hora}</time>
      </div>
    </article>
  )
}

export default MensajeChatComp
