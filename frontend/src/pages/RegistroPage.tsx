import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import MarcoAuthComp from '../components/auth/MarcoAuthComp'
import { useAuth } from '../hooks/useAuth'
import BotonUI from '../ui/BotonUI'
import InputUI from '../ui/InputUI'
import { obtenerTerminosRegistro } from '../api/authApi'
import type { TerminosRegistro } from '../types/auth'

function RegistroPage() {
  const { registrar } = useAuth()
  const navigate = useNavigate()
  const [nombre, setNombre] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [acepta, setAcepta] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [terminos, setTerminos] = useState<TerminosRegistro | null>(null)
  const [errorTerminos, setErrorTerminos] = useState('')
  const [intentoTerminos, setIntentoTerminos] = useState(0)

  useEffect(() => {
    let vigente = true
    void obtenerTerminosRegistro().then((datos) => {
      if (vigente) setTerminos(datos)
    }).catch((fallo: unknown) => {
      if (vigente) setErrorTerminos(fallo instanceof Error ? fallo.message : 'No se pudieron cargar los términos.')
    })
    return () => { vigente = false }
  }, [intentoTerminos])

  function reintentarTerminos() {
    setTerminos(null)
    setAcepta(false)
    setErrorTerminos('')
    setIntentoTerminos((actual) => actual + 1)
  }

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (enviando) return
    if (password !== confirmacion) { setError('Las contraseñas no coinciden.'); return }
    if (!/^[A-Za-z][A-Za-z0-9._-]{2,39}$/.test(username.trim())) { setError('El usuario debe tener entre 3 y 40 caracteres, empezar con una letra y usar solo letras sin tildes, números, punto, guion o guion bajo.'); return }
    if (!terminos || !acepta) { setError('Lee y acepta los términos de conservación de 30 días antes de continuar.'); return }
    setEnviando(true)
    setError('')
    try {
      await registrar(nombre, username.trim().toLowerCase(), password, { acepta_terminos: acepta, version_terminos: terminos.version })
      navigate('/chat', { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo crear la cuenta.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoAuthComp titulo="Crea tu cuenta" descripcion="Tendrás un chat personal para conversar a tu ritmo.">
      <form onSubmit={enviar} className="space-y-5">
        <InputUI id="nombre" etiqueta="¿Cómo te llamas?" autoComplete="given-name" required maxLength={80} value={nombre} onChange={(event) => setNombre(event.target.value)} disabled={enviando} />
        <div>
          <InputUI id="username" etiqueta="Elige tu usuario" type="text" autoComplete="username" autoCapitalize="none" spellCheck={false} required minLength={3} maxLength={40} pattern="[a-zA-Z][a-zA-Z0-9._\-]{2,39}" value={username} onChange={(event) => setUsername(event.target.value)} disabled={enviando} placeholder="estudiante49" aria-describedby="ayuda-usuario" />
          <p id="ayuda-usuario" className="mt-2 text-xs leading-relaxed text-slate-500">Entre 3 y 40 caracteres. Empieza con una letra; puedes usar letras sin tildes, números, punto, guion y guion bajo. Se guardará en minúsculas.</p>
        </div>
        <div>
          <InputUI id="password" etiqueta="Elige una contraseña para esta cuenta" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} disabled={enviando} />
          <p className="mt-2 text-xs leading-relaxed text-slate-500">Usa al menos 8 caracteres y una contraseña propia para Chatbot Cognitivo, difícil de adivinar.</p>
        </div>
        <InputUI id="confirmacion" etiqueta="Repite tu contraseña" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={confirmacion} onChange={(event) => setConfirmacion(event.target.value)} disabled={enviando} />
        <div className="rounded-xl bg-blue-50/70 p-4 text-xs leading-relaxed text-slate-600">
          <h2 className="font-semibold text-slate-800">Uso y conservación de tu conversación</h2>
          <p className="mt-2">Tu conversación se analizará para generar reportes orientativos. El administrador podrá verlos y consultar los fragmentos que los sustentan. Los resultados no constituyen un diagnóstico.</p>
          {terminos ? <p id="terminos-retencion" className="mt-2">{terminos.texto}</p> : errorTerminos ? <div className="mt-2"><p role="alert" className="text-red-700">{errorTerminos}</p><button type="button" onClick={reintentarTerminos} className="mt-2 min-h-10 font-semibold text-blue-700 underline">Volver a cargar los términos</button></div> : <p role="status" className="mt-2">Consultando los términos de conservación…</p>}
          <label className="mt-3 flex items-start gap-3">
            <input type="checkbox" required checked={acepta} onChange={(event) => setAcepta(event.target.checked)} disabled={enviando || !terminos} aria-describedby={terminos ? 'terminos-retencion' : undefined} className="mt-0.5 size-4 shrink-0 accent-blue-600" />
            <span>Acepto este uso de mi conversación y la eliminación automática de mis mensajes nuevos al cumplir 30 días desde su envío.</span>
          </label>
        </div>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <BotonUI type="submit" className="w-full" disabled={enviando || !terminos || !acepta}>{enviando ? 'Creando cuenta…' : 'Crear cuenta y comenzar'}</BotonUI>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">¿Ya tienes una cuenta? <Link to="/login" className="font-semibold text-blue-600 hover:underline">Iniciar sesión</Link></p>
    </MarcoAuthComp>
  )
}

export default RegistroPage
