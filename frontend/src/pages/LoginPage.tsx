import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import MarcoAuthComp from '../components/auth/MarcoAuthComp'
import { useAuth } from '../hooks/useAuth'
import BotonUI from '../ui/BotonUI'
import InputUI from '../ui/InputUI'

function LoginPage() {
  const { iniciarSesion, error: errorConexion, refrescarUsuario } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      const usuario = await iniciarSesion(email, password)
      navigate(usuario.es_admin ? '/administrador' : '/chat', { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo iniciar sesión.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoAuthComp titulo="Bienvenido de nuevo" descripcion="Inicia sesión para continuar tu conversación y tu acompañamiento.">
      {errorConexion && <div role="alert" className="mb-5 rounded-xl bg-blue-50 p-3 text-sm text-blue-900">{errorConexion}<button type="button" className="mt-2 block font-semibold underline underline-offset-2" onClick={() => { void refrescarUsuario() }}>Comprobar conexión</button></div>}
      <form onSubmit={enviar} className="space-y-5">
        <InputUI id="email" etiqueta="Correo electrónico" type="email" autoComplete="username" required maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} disabled={enviando} placeholder="tuusuario@gmail.com" />
        <InputUI id="password" etiqueta="Contraseña de tu cuenta" type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} disabled={enviando} />
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <BotonUI type="submit" className="w-full" disabled={enviando}>{enviando ? 'Iniciando sesión…' : 'Iniciar sesión'}</BotonUI>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500">¿Aún no tienes una cuenta? <Link to="/registro" className="font-semibold text-blue-600 hover:underline">Crear cuenta</Link></p>
      <p className="mt-4 text-center text-xs text-slate-500"><Link to="/administrador" className="hover:text-blue-600 hover:underline">Acceso de administrador</Link></p>
    </MarcoAuthComp>
  )
}

export default LoginPage
