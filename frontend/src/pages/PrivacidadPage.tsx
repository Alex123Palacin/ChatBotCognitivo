import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { obtenerTerminosRegistro } from '../api/authApi'
import type { TerminosRegistro } from '../types/auth'
import MarcoAuthComp from '../components/auth/MarcoAuthComp'

export default function PrivacidadPage() {
  const [politica, setPolitica] = useState<TerminosRegistro | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let vigente = true
    void obtenerTerminosRegistro().then(p => { if (vigente) setPolitica(p) })
      .catch(() => { if (vigente) setError('No se pudo cargar la política. Vuelve a intentarlo más tarde.') })
    return () => { vigente = false }
  }, [])
  return <MarcoAuthComp titulo="Política de Privacidad" descripcion="Uso y conservación de tu conversación en Chatbot Cognitivo.">
    <div className="space-y-4 text-sm leading-7 text-slate-600">
      <p>El registro utiliza un nombre de usuario. No solicita tu nombre personal ni tu correo electrónico.</p>
      {politica ? <><p>{politica.texto}</p><p className="text-xs text-slate-500">Versión: {politica.version}</p></> : <p role={error ? 'alert' : 'status'}>{error || 'Cargando política…'}</p>}
      <p>Las condiciones anteriores de las cuentas existentes se conservan; no se atribuye una aceptación nueva por cambiar esta página.</p>
      <Link to="/registro" className="inline-block py-2 font-semibold text-blue-700 underline">Volver al registro</Link>
    </div>
  </MarcoAuthComp>
}
