import { ArrowUpRight, BookOpen, CalendarDays, CloudSun, Focus } from 'lucide-react'

const sugerencias = [
  { texto: 'Tengo muchos exámenes', detalle: 'Vamos paso a paso', icono: BookOpen, color: 'bg-blue-50 text-blue-600' },
  { texto: 'No puedo concentrarme', detalle: 'Encuentra un poco de claridad', icono: Focus, color: 'bg-indigo-50 text-indigo-500' },
  { texto: 'Me siento abrumado', detalle: 'Date un espacio para hablar', icono: CloudSun, color: 'bg-sky-50 text-sky-600' },
  { texto: 'Necesito organizarme', detalle: 'Empieza con algo pequeño', icono: CalendarDays, color: 'bg-violet-50 text-violet-500' },
]

function InicioChatComp({ alSeleccionar }: { alSeleccionar: (texto: string) => void }) {
  return (
    <section aria-labelledby="bienvenida" className="mx-auto flex w-full max-w-2xl flex-col items-center px-5 py-8 text-center sm:px-8 sm:py-12">
      <p className="mb-3 text-[10px] font-semibold tracking-[0.2em] text-blue-600 uppercase sm:text-[11px]">Un espacio para ti</p>
      <h1 id="bienvenida" className="max-w-lg text-[30px] leading-[1.2] font-semibold tracking-[-0.045em] text-slate-800 sm:text-[42px]">Hola, estoy aquí para <span className="text-blue-600">acompañarte</span></h1>
      <p className="mt-4 max-w-md text-sm leading-6 text-slate-500 sm:text-[15px]">Puedes contarme cómo te has sentido con tus estudios.<br className="hidden sm:block" /> A tu ritmo, una conversación a la vez.</p>

      <div className="mt-9 w-full sm:mt-10">
        <p className="mb-4 text-xs text-slate-500">Si no sabes por dónde empezar…</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {sugerencias.map(({ texto, detalle, icono: Icono, color }) => (
            <button key={texto} type="button" onClick={() => alSeleccionar(texto)} className="group flex min-h-22 items-center gap-3.5 rounded-2xl border border-slate-200/90 bg-white/90 p-4 text-left shadow-xs transition duration-200 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md hover:shadow-blue-100/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 motion-reduce:transform-none motion-reduce:transition-none">
              <span className={`flex size-10 shrink-0 items-center justify-center rounded-xl ${color}`}><Icono size={20} strokeWidth={1.6} /></span>
              <span className="flex-1"><span className="block text-[13px] font-semibold text-slate-700">{texto}</span><span className="mt-1 block text-[11px] text-slate-500">{detalle}</span></span>
              <ArrowUpRight size={15} className="shrink-0 text-slate-300 transition group-hover:text-blue-500" />
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

export default InicioChatComp
