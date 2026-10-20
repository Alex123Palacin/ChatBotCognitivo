import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { enviarMensajeChat, enviarMensajeChatFlujo, obtenerChat } from '../src/api/chatbotApi.ts'

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

const codificador = new TextEncoder()
const evento = (datos) => `${JSON.stringify(datos)}\n`
const respuestaFlujo = (texto) => new Response(new ReadableStream({
  start(controlador) {
    // Divide también dentro de letras UTF-8, sin depender de los límites de red.
    const bytes = codificador.encode(texto)
    for (let indice = 0; indice < bytes.length; indice += 3) controlador.enqueue(bytes.slice(indice, indice + 3))
    controlador.close()
  },
}), { headers: { 'Content-Type': 'application/x-ndjson; charset=utf-8' } })

test('muestra fragmentos antes del estado final y conserva su orden, espacios y acentos', async () => {
  let controlador
  const fragmentos = []
  let recibirPrimerTexto
  const primerTexto = new Promise((resolve) => { recibirPrimerTexto = resolve })
  const cuerpos = []
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/csrf/') return json({ csrfToken: 'token' })
    assert.equal(url, '/api/chat/flujo/')
    assert.equal(opciones.credentials, 'same-origin')
    assert.equal(opciones.headers['X-CSRFToken'], 'token')
    cuerpos.push(JSON.parse(opciones.body))
    return new Response(new ReadableStream({
      start(actual) {
        controlador = actual
        actual.enqueue(codificador.encode(`\n${evento({ tipo: 'inicio' })}${evento({ tipo: 'fragmento', contenido: 'Hola, ' })}`))
      },
    }), { headers: { 'Content-Type': 'application/x-ndjson' } })
  }
  let completado = false
  const resultado = enviarMensajeChatFlujo(solicitud, new AbortController().signal, (texto) => {
    fragmentos.push(texto)
    recibirPrimerTexto()
  }).then((chat) => { completado = true; return chat })
  await primerTexto
  assert.deepEqual(fragmentos, ['Hola, '])
  assert.equal(completado, false, 'el texto aparece sin esperar a que termine la IA')
  controlador.enqueue(codificador.encode(evento({ tipo: 'fragmento', contenido: '¿cómo va tu colegio? 💙' })))
  controlador.enqueue(codificador.encode(evento({ tipo: 'estado', chat: estado })))
  controlador.close()
  assert.deepEqual(await resultado, estado)
  assert.equal(fragmentos.join(''), 'Hola, ¿cómo va tu colegio? 💙')
  assert.deepEqual(cuerpos, [solicitud])
})

test('reconstruye líneas cortadas y UTF-8, ignora metadatos y admite estado final sin salto de línea', async () => {
  const fragmentos = []
  globalThis.fetch = async (url) => url === '/api/csrf/'
    ? json({ csrfToken: 'token' })
    : respuestaFlujo(`\r\n${evento({ tipo: 'inicio' })}${evento({ tipo: 'razonamiento', contenido: 'No mostrar' })}${evento({ tipo: 'fragmento', contenido: 'Mañana en el colegio 💙' })}${JSON.stringify({ tipo: 'estado', chat: estado })}`)
  assert.deepEqual(await enviarMensajeChatFlujo(solicitud, new AbortController().signal, (texto) => fragmentos.push(texto)), estado)
  assert.deepEqual(fragmentos, ['Mañana en el colegio 💙'])
})

test('propaga errores durante el flujo y conserva la misma clave al reintentar', async () => {
  const cuerpos = []
  const fragmentos = []
  let token = 0
  globalThis.fetch = async (url, opciones) => {
    if (url === '/api/csrf/') return json({ csrfToken: `token-${++token}` })
    assert.equal(opciones.headers['X-CSRFToken'], `token-${token}`)
    cuerpos.push(JSON.parse(opciones.body))
    return respuestaFlujo(evento({ tipo: 'fragmento', contenido: 'Hola' }) + evento({ tipo: 'error', error: 'Ollama no está disponible.' }))
  }
  for (let intento = 0; intento < 2; intento += 1) {
    await assert.rejects(enviarMensajeChatFlujo(solicitud, new AbortController().signal, (texto) => fragmentos.push(texto)), /Ollama no está disponible/)
  }
  assert.deepEqual(cuerpos, [solicitud, solicitud])
  assert.deepEqual(fragmentos, ['Hola', 'Hola'])
})

test('rechaza un flujo interrumpido, un evento inválido y un servidor que devuelve HTML', async () => {
  const respuestas = [
    respuestaFlujo(evento({ tipo: 'fragmento', contenido: 'Hola' })),
    respuestaFlujo('{no es json}\n'),
    respuestaFlujo(evento({ tipo: 'fragmento', contenido: 42 })),
    respuestaFlujo(evento({ tipo: 'estado', chat: { ...estado, mensajes: [{}] } })),
    new Response('<html>Otro proyecto</html>', { headers: { 'Content-Type': 'text/html' } }),
  ]
  globalThis.fetch = async (url) => url === '/api/csrf/' ? json({ csrfToken: 'token' }) : respuestas.shift()
  for (let intento = 0; intento < 5; intento += 1) {
    await assert.rejects(enviarMensajeChatFlujo(solicitud, new AbortController().signal, () => undefined), /interrumpió|incompleta|no válid/)
  }
})

test('el flujo avisa al caducar la sesión y no confunde un rechazo CSRF con un cambio de rol', async () => {
  const eventos = []
  let status = 401
  globalThis.window = { dispatchEvent: (actual) => eventos.push(actual.type) }
  globalThis.fetch = async (url) => url === '/api/csrf/' ? json({ csrfToken: 'token' }) : json({ error: 'Acceso rechazado.' }, status)
  await assert.rejects(enviarMensajeChatFlujo(solicitud, new AbortController().signal, () => undefined), /Acceso rechazado/)
  assert.deepEqual(eventos, ['sesion-caducada'])
  eventos.length = 0
  status = 403
  await assert.rejects(enviarMensajeChatFlujo(solicitud, new AbortController().signal, () => undefined), /Acceso rechazado/)
  assert.deepEqual(eventos, [])
})

test('cancelar una respuesta detiene su lectura y libera la conexión', async () => {
  const controlador = new AbortController()
  let cancelado = false
  globalThis.fetch = async (url) => url === '/api/csrf/' ? json({ csrfToken: 'token' })
    : new Response(new ReadableStream({
      start(actual) {
        actual.enqueue(codificador.encode(evento({ tipo: 'fragmento', contenido: 'Hola' }) + evento({ tipo: 'estado', chat: estado })))
      },
      cancel() { cancelado = true },
    }), { headers: { 'Content-Type': 'application/x-ndjson' } })
  await assert.rejects(enviarMensajeChatFlujo(solicitud, controlador.signal, () => controlador.abort()), { name: 'AbortError' })
  assert.equal(cancelado, true)
})
