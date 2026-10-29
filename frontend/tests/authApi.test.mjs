import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { iniciarSesionApi, obtenerTerminosRegistro, obtenerUsuario, registrarApi } from '../src/api/authApi.ts'

const fetchOriginal = globalThis.fetch
const administrador = { id: 1, email: '', nombre: 'Administrador', username: 'admin', es_admin: true }
afterEach(() => { globalThis.fetch = fetchOriginal })

test('todos los accesos envían username, incluidos los identificadores heredados', async () => {
  const credenciales = []
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/csrf/') return Response.json({ csrfToken: 'token' })
    assert.equal(url, '/api/auth/login/')
    assert.equal(opciones.credentials, 'same-origin')
    assert.equal(opciones.headers['X-CSRFToken'], 'token')
    const datos = JSON.parse(opciones.body)
    credenciales.push(datos)
    return Response.json({ usuario: datos.username === 'admin'
      ? administrador
      : { id: 2, email: '', nombre: 'Estudiante', username: datos.username, es_admin: false } })
  }
  assert.deepEqual(await iniciarSesionApi('admin', 'admin'), { usuario: administrador })
  assert.equal((await iniciarSesionApi('estudiante@gmail.com', 'clave-propia')).usuario.es_admin, false)
  assert.equal((await iniciarSesionApi(' ESTUDIANTE49 ', 'clave-propia')).usuario.username, 'estudiante49')
  assert.deepEqual(credenciales, [
    { username: 'admin', password: 'admin' },
    { username: 'estudiante@gmail.com', password: 'clave-propia' },
    { username: 'estudiante49', password: 'clave-propia' },
  ])
})

test('la comprobación de sesión admite respuestas anteriores sin username y rechaza un username inválido', async () => {
  const { username: _username, ...usuarioAnterior } = administrador
  globalThis.fetch = async () => Response.json({ usuario: usuarioAnterior })
  assert.deepEqual(await obtenerUsuario(), { usuario: usuarioAnterior })
  globalThis.fetch = async () => Response.json({ usuario: { ...administrador, username: 42 } })
  await assert.rejects(obtenerUsuario(), /sesión no válida/)
})

test('registro envía la aceptación explícita y la versión que se mostró al estudiante', async () => {
  const terminos = { version: 'conversaciones-30-dias-v1', dias_retencion: 30, texto: 'Cada mensaje nuevo se elimina a los 30 días de su envío.', alcance: 'mensajes_nuevos', copias_seguridad: 'gestion_separada' }
  const estudiante = { id: 2, email: '', username: 'estudiante49', nombre: 'Ana', es_admin: false }
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/auth/terminos/') return Response.json(terminos)
    if (url === '/api/csrf/') return Response.json({ csrfToken: 'token' })
    assert.equal(url, '/api/auth/registro/')
    assert.deepEqual(JSON.parse(opciones.body), { nombre: 'Ana', username: 'estudiante49', password: 'Clave!72851', acepta_terminos: true, version_terminos: terminos.version })
    return Response.json({ usuario: estudiante })
  }
  assert.deepEqual(await obtenerTerminosRegistro(), terminos)
  assert.deepEqual(await registrarApi('Ana', ' ESTUDIANTE49 ', 'Clave!72851', { acepta_terminos: true, version_terminos: terminos.version }), { usuario: estudiante })
})

test('no se solicita registrar una cuenta sin aceptación explícita o sin versión de términos', async () => {
  let peticiones = 0
  globalThis.fetch = async () => { peticiones += 1; throw new Error('No debe enviarse una solicitud') }
  await assert.rejects(registrarApi('Ana', 'estudiante49', 'Clave!72851', { acepta_terminos: false, version_terminos: 'conversaciones-30-dias-v1' }), /acepta los términos/)
  await assert.rejects(registrarApi('Ana', 'estudiante49', 'Clave!72851', { acepta_terminos: true, version_terminos: '' }), /acepta los términos/)
  assert.equal(peticiones, 0)
})

test('el registro rechaza formatos inválidos antes de contactar con el servidor', async () => {
  let peticiones = 0
  globalThis.fetch = async () => { peticiones += 1; throw new Error('No debe enviarse') }
  const acepta = { acepta_terminos: true, version_terminos: 'conversaciones-30-dias-v1' }
  for (const username of ['ab', 'a'.repeat(41), '4alumno', 'ana@gmail.com', 'niño', 'álvaro', 'Kevin', 'ana uno', '.ana', 'ana/uno']) {
    await assert.rejects(registrarApi('Ana', username, 'Clave!72851', acepta), /usuario debe tener/)
  }
  assert.equal(peticiones, 0)
})

test('un fallo o contrato de términos incompleto impide asumir una política de conservación', async () => {
  globalThis.fetch = async () => Response.json({ version: 'incompleta', dias_retencion: 30 })
  await assert.rejects(obtenerTerminosRegistro(), /comprobar los términos/)
  globalThis.fetch = async () => Response.json({ error: 'Servicio no disponible' }, { status: 503 })
  await assert.rejects(obtenerTerminosRegistro(), /Servicio no disponible/)
})
