import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { enviarMensajeChat, obtenerChat } from '../src/api/chatbotApi.ts'

const fetchOriginal = globalThis.fetch
const ventanaOriginal = globalThis.window
const solicitud = { clave_envio: 'c9d880fd-d418-41fd-93f8-a66bb77e6e63', mensaje: 'Hola' }
const estado = {
  mensajes: [{ id: '1', contenido: 'Hola', remitente: 'usuario', fecha: '2026-10-08T12:00:00Z', sesion_numero: 1 }],
  sesiones: [], sesion_actual: null, programa_finalizado: false, respuesta_pendiente: false,
}
const json = (datos, status = 200) => Response.json(datos, { status })
afterEach(() => {
  globalThis.fetch = fetchOriginal
  if (ventanaOriginal === undefined) delete globalThis.window
  else globalThis.window = ventanaOriginal
})

test('recupera el historial mediante una lectura sin solicitar CSRF', async () => {
  const llamadas = []
  globalThis.fetch = async (url, opciones) => {
    llamadas.push(url)
    assert.equal(opciones.credentials, 'same-origin')
    assert.equal(opciones.method, 'GET')
    return json(estado)
  }
  assert.deepEqual(await obtenerChat(), estado)
  assert.deepEqual(llamadas, ['/api/chat/'])
})

test('un backend apagado falla antes de enviar el mensaje', async () => {
  const llamadas = []
  globalThis.fetch = async (url) => {
    llamadas.push(url)
    return new Response('', { status: 500 })
  }
  await assert.rejects(enviarMensajeChat(solicitud, new AbortController().signal), /Django/)
  assert.deepEqual(llamadas, ['/api/csrf/'])
})

test('envía token CSRF y clave estable para no duplicar mensajes en un reintento', async () => {
  const cuerpos = []
  let token = 0
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/csrf/') return json({ csrfToken: `token-${++token}` })
    assert.equal(url, '/api/chat/')
    assert.equal(opciones.headers['X-CSRFToken'], `token-${token}`)
    cuerpos.push(JSON.parse(opciones.body))
    return json(estado)
  }
  await enviarMensajeChat(solicitud, new AbortController().signal)
  await enviarMensajeChat(solicitud, new AbortController().signal)
  assert.deepEqual(cuerpos, [solicitud, solicitud])
  assert.equal(token, 2)
})

test('muestra el error de Ollama que devuelve Django', async () => {
  globalThis.fetch = async (url) => url === '/api/csrf/'
    ? json({ csrfToken: 'token' }) : json({ error: 'Ollama no está disponible.' }, 503)
  await assert.rejects(enviarMensajeChat(solicitud, new AbortController().signal), /Ollama no está disponible/)
})

test('rechaza un historial con mensajes o fechas inválidos', async () => {
  globalThis.fetch = async () => json({ ...estado, mensajes: [{ ...estado.mensajes[0], fecha: 'incorrecta' }] })
  await assert.rejects(obtenerChat(), /respuesta no válida/)
})

test('rechaza otro servidor que responde HTML en lugar de la API', async () => {
  globalThis.fetch = async () => new Response('<html>Otro proyecto</html>')
  await assert.rejects(obtenerChat(), /respuesta no válida/)
})

test('una conexión rechazada muestra cómo iniciar el backend', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(enviarMensajeChat(solicitud, new AbortController().signal), /puerto 8000/)
})

test('comprueba cambios de rol al leer el chat sin confundir un POST rechazado por CSRF', async () => {
  const eventos = []
  globalThis.window = { dispatchEvent: (event) => eventos.push(event.type) }
  globalThis.fetch = async (url) => url === '/api/csrf/'
    ? json({ csrfToken: 'token' }) : json({ error: 'Acceso rechazado.' }, 403)

  await assert.rejects(obtenerChat(), /Acceso rechazado/)
  assert.deepEqual(eventos, ['sesion-revisar'])
  eventos.length = 0
  await assert.rejects(enviarMensajeChat(solicitud, new AbortController().signal), /Acceso rechazado/)
  assert.deepEqual(eventos, [])
})
