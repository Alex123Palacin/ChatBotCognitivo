import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import MarcoAuthComp from '../../components/auth/MarcoAuthComp'
import { useAuth } from '../../hooks/useAuth'
import BotonUI from '../../ui/BotonUI'
import InputUI from '../../ui/InputUI'

function LoginAdminPage() {
  const { iniciarSesion, error: errorConexion, refrescarUsuario } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  async function enviar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (enviando) return
    setEnviando(true)
    setError('')
    try {
      const usuario = await iniciarSesion(username, password)
      navigate(usuario.es_admin ? '/administrador' : '/chat', { replace: true })
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo iniciar sesión.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoAuthComp titulo="Acceso de administrador" descripcion="Consulta a los estudiantes, su actividad y los reportes de sus conversaciones.">
      {errorConexion && <div role="alert" className="mb-5 rounded-xl bg-blue-50 p-3 text-sm text-blue-900">{errorConexion}<button type="button" className="mt-2 block font-semibold underline underline-offset-2" onClick={() => { void refrescarUsuario() }}>Comprobar conexión</button></div>}
      <form onSubmit={enviar} className="space-y-5">
        <InputUI id="username" etiqueta="Usuario administrador" type="text" autoComplete="username" required maxLength={150} value={username} onChange={(event) => setUsername(event.target.value)} disabled={enviando} placeholder="admin" />
        <InputUI id="password" etiqueta="Contraseña" type="password" autoComplete="current-password" required maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} disabled={enviando} />
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <BotonUI type="submit" className="w-full" disabled={enviando}>{enviando ? 'Iniciando sesión…' : 'Entrar al sistema administrativo'}</BotonUI>
      </form>
      <p className="mt-6 text-center text-sm text-slate-500"><Link to="/login" className="font-medium text-blue-600 hover:underline">Acceso de estudiantes</Link></p>
    </MarcoAuthComp>
  )
}

export default LoginAdminPage
