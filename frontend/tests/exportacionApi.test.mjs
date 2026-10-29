import assert from 'node:assert/strict'
import { afterEach, test } from 'node:test'
import { obtenerEvaluacion } from '../src/api/exportacionApi.ts'

const original = globalThis.fetch
afterEach(() => { globalThis.fetch = original })
test('descarga Excel de los estudiantes seleccionados con la sesión actual', async () => {
  globalThis.fetch = async (url, opciones) => {
    assert.equal(url, '/api/admin/evaluacion.xlsx?alumnos=5,6')
    assert.equal(opciones.credentials, 'same-origin')
    return new Response('archivo', { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' } })
  }
  assert.equal(await (await obtenerEvaluacion([5, 6, 5])).text(), 'archivo')
})
test('rechaza selección vacía, html y accesos sin autorización', async () => {
  await assert.rejects(obtenerEvaluacion([]), /Selecciona/)
  globalThis.fetch = async () => new Response('<html>login</html>', { headers: { 'Content-Type': 'text/html' } })
  await assert.rejects(obtenerEvaluacion([5]), /Excel válido/)
  globalThis.fetch = async () => Response.json({ error: 'Inicia sesión para continuar.' }, { status: 401 })
  await assert.rejects(obtenerEvaluacion([5]), /Inicia sesión/)
})

test('descarga los 110 seleccionados en una solicitud y rechaza exceder el límite', async () => {
  const ids = Array.from({ length: 110 }, (_, i) => i + 1)
  globalThis.fetch = async (url) => {
    assert.equal(url, `/api/admin/evaluacion.xlsx?alumnos=${ids.join(',')}`)
    return new Response('archivo', { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' } })
  }
  assert.equal(await (await obtenerEvaluacion(ids)).text(), 'archivo')
  await assert.rejects(obtenerEvaluacion([...ids, 111]), /Selecciona/)
})
