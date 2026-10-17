import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { iniciarSesionApi, obtenerUsuario } from '../src/api/authApi.ts'

const fetchOriginal = globalThis.fetch
const administrador = { id: 1, email: '', nombre: 'Administrador', username: 'admin', es_admin: true }
afterEach(() => { globalThis.fetch = fetchOriginal })

test('el administrador entra con username y el estudiante conserva el acceso por email', async () => {
  const credenciales = []
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/csrf/') return Response.json({ csrfToken: 'token' })
    assert.equal(url, '/api/auth/login/')
    assert.equal(opciones.credentials, 'same-origin')
    assert.equal(opciones.headers['X-CSRFToken'], 'token')
    const datos = JSON.parse(opciones.body)
    credenciales.push(datos)
    return Response.json({ usuario: datos.username
      ? administrador
      : { id: 2, email: datos.email, nombre: 'Estudiante', username: datos.email, es_admin: false } })
  }
  assert.deepEqual(await iniciarSesionApi('admin', 'admin'), { usuario: administrador })
  assert.equal((await iniciarSesionApi('estudiante@gmail.com', 'clave-propia')).usuario.es_admin, false)
  assert.deepEqual(credenciales, [
    { username: 'admin', password: 'admin' },
    { email: 'estudiante@gmail.com', password: 'clave-propia' },
  ])
})

test('la comprobación de sesión admite respuestas anteriores sin username y rechaza un username inválido', async () => {
  const { username: _username, ...usuarioAnterior } = administrador
  globalThis.fetch = async () => Response.json({ usuario: usuarioAnterior })
  assert.deepEqual(await obtenerUsuario(), { usuario: usuarioAnterior })
  globalThis.fetch = async () => Response.json({ usuario: { ...administrador, username: 42 } })
  await assert.rejects(obtenerUsuario(), /sesión no válida/)
})
