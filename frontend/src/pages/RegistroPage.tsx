import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import MarcoAuthComp from '../components/auth/MarcoAuthComp'
import { useAuth } from '../hooks/useAuth'
import BotonUI from '../ui/BotonUI'
import InputUI from '../ui/InputUI'

function RegistroPage() {
  const { registrar } = useAuth()
  const navigate = useNavigate()
  const [nombre, setNombre] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [acepta, setAcepta] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (enviando) return
    if (password !== confirmacion) { setError('Las contraseñas no coinciden.'); return }
    if (!email.trim().toLowerCase().endsWith('@gmail.com')) { setError('Utiliza tu dirección de Gmail para crear la cuenta.'); return }
    if (!acepta) { setError('Revisa y acepta el uso de la conversación antes de continuar.'); return }
    setEnviando(true)
    setError('')
    try {
      await registrar(nombre, email, password)
      navigate('/chat', { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo crear la cuenta.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoAuthComp titulo="Crea tu cuenta" descripcion="Tendrás un chat personal que podrás continuar durante cuatro semanas.">
      <form onSubmit={enviar} className="space-y-5">
        <InputUI id="nombre" etiqueta="¿Cómo te llamas?" autoComplete="given-name" required maxLength={80} value={nombre} onChange={(event) => setNombre(event.target.value)} disabled={enviando} />
        <InputUI id="email" etiqueta="Tu dirección de Gmail" type="email" autoComplete="username" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} disabled={enviando} placeholder="tuusuario@gmail.com" />
        <div>
          <InputUI id="password" etiqueta="Elige una contraseña para esta cuenta" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} disabled={enviando} />
          <p className="mt-2 text-xs leading-relaxed text-slate-500">Usa al menos 8 caracteres. Esta contraseña pertenece a Chatbot Cognitivo; no escribas la de tu Gmail.</p>
        </div>
        <InputUI id="confirmacion" etiqueta="Repite tu contraseña" type="password" autoComplete="new-password" required minLength={8} maxLength={128} value={confirmacion} onChange={(event) => setConfirmacion(event.target.value)} disabled={enviando} />
        <label className="flex items-start gap-3 rounded-xl bg-blue-50/70 p-4 text-xs leading-relaxed text-slate-600">
          <input type="checkbox" required checked={acepta} onChange={(event) => setAcepta(event.target.checked)} disabled={enviando} className="mt-0.5 size-4 shrink-0 accent-blue-600" />
          <span>Entiendo que mi conversación se guardará y se analizará para generar reportes semanales. El administrador podrá ver esos reportes y los fragmentos que los sustentan. Los resultados son orientativos y no constituyen un diagnóstico.</span>
        </label>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <BotonUI type="submit" className="w-full" disabled={enviando}>{enviando ? 'Creando cuenta…' : 'Crear cuenta y comenzar'}</BotonUI>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">¿Ya tienes una cuenta? <Link to="/login" className="font-semibold text-blue-600 hover:underline">Iniciar sesión</Link></p>
    </MarcoAuthComp>
  )
}

export default RegistroPage
