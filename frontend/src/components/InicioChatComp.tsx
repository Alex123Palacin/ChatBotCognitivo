function InicioChatComp() {
  return (
    <section aria-labelledby="bienvenida" className="mx-auto flex w-full max-w-2xl flex-col items-center px-5 py-8 text-center sm:px-8 sm:py-12">
      <p className="mb-3 text-[10px] font-semibold tracking-[0.2em] text-blue-600 uppercase sm:text-[11px]">Un espacio para ti</p>
      <h1 id="bienvenida" className="max-w-lg text-[30px] leading-[1.2] font-semibold tracking-[-0.045em] text-slate-800 sm:text-[42px]">Hola, estoy aquí para <span className="text-blue-600">acompañarte</span></h1>
      <p className="mt-4 max-w-md text-sm leading-6 text-slate-500 sm:text-[15px]">Puedes contarme cómo te ha ido hoy, qué te preocupa o algo que quieras compartir. No necesitas seguir un orden: iremos a tu ritmo.</p>
      <p className="mt-8 max-w-md rounded-2xl border border-blue-100 bg-white/80 p-4 text-xs leading-5 text-slate-500">Este será tu mismo chat durante las cuatro semanas. Cada semana se elaborará un reporte académico para el administrador a partir de lo que compartas.</p>
    </section>
  )
}

export default InicioChatComp
