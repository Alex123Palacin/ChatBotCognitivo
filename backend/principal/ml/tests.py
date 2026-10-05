from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, SimpleTestCase

from .conversacion import nuevo_estado, pendiente, procesar
from .cuestionario import PREGUNTAS, calcular_resultado
from .ollama import ErrorModelo


class PuntajesTests(SimpleTestCase):
    def test_promedios_separados_y_sin_total_global(self):
        respuestas = {p[0]: 2 if i < 8 else 5 for i, p in enumerate(PREGUNTAS)}
        resultado = calcular_resultado(respuestas)
        self.assertEqual([d['promedio'] for d in resultado['dimensiones']], [2, 2, 5])
        self.assertEqual(resultado['respondidas'], 14)
        self.assertNotIn('nivel', resultado)
        self.assertNotIn('puntaje_global', resultado)

    def test_omision_no_cuenta_como_cero(self):
        respuestas = {p[0]: 4 for p in PREGUNTAS}
        respuestas['sobrecarga_1'] = None
        resultado = calcular_resultado(respuestas)
        self.assertIsNone(resultado['indicadores'][0]['promedio'])
        self.assertIsNone(resultado['dimensiones'][0]['promedio'])
        self.assertEqual(resultado['dimensiones'][1]['promedio'], 4)
        self.assertEqual(resultado['respondidas'], 13)

    def test_limites_y_redondeo(self):
        self.assertEqual(calcular_resultado({p[0]: 1 for p in PREGUNTAS})['dimensiones'][0]['promedio'], 1)
        respuestas = {p[0]: 5 for p in PREGUNTAS}
        respuestas['sobrecarga_1'] = 4
        self.assertEqual(calcular_resultado(respuestas)['dimensiones'][0]['promedio'], 4.75)
        for valor in (0, 6, True, '3', 2.5):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                calcular_resultado({'sobrecarga_1': valor})


class ConversacionTests(SimpleTestCase):
    def setUp(self):
        self.modelo = patch('ml.conversacion.responder', return_value='Gracias por contármelo.').start()
        self.addCleanup(patch.stopall)
        self.estado = nuevo_estado()

    def enviar(self, texto='', opcion=None):
        actual = pendiente(self.estado)
        return procesar(self.estado, texto, opcion, actual['id'] if actual else None)

    def iniciar_test(self):
        self.enviar('Hola')
        self.enviar('Alex')
        self.enviar(opcion='quinto')
        self.enviar('Tengo muchas tareas')
        self.assertEqual(self.estado['etapa'], 'decision')
        self.enviar(opcion='empezar')

    def test_presentacion_test_reflexiones_y_resultado(self):
        self.iniciar_test()
        for i in range(14):
            self.assertEqual(pendiente(self.estado)['numero'], i + 1)
            salida = self.enviar(opcion='3')
            if self.estado['etapa'] == 'reflexion':
                self.enviar('Me preocupan los exámenes')
        self.assertEqual(self.estado['etapa'], 'finalizado')
        self.assertEqual(salida['resultado']['respondidas'], 14)
        self.assertEqual(len(self.estado['respuestas']), 14)
        self.assertEqual(self.estado['perfil']['nombre'], 'Alex')
        self.assertIsNone(self.enviar('¿Qué puedo hacer?')['resultado'])

    def test_no_puntua_texto_libre(self):
        self.iniciar_test()
        self.enviar('Estoy preocupado')
        self.assertEqual(self.estado['respuestas'], {})
        self.assertEqual(self.estado['indice'], 0)
        self.enviar('Casi siempre')
        self.assertEqual(self.estado['respuestas']['sobrecarga_1'], 4)

    def test_pausa_y_resultado_parcial(self):
        self.iniciar_test()
        self.enviar(opcion='5')
        self.enviar(opcion='pausar')
        self.enviar(opcion='retomar')
        self.assertEqual(self.estado['indice'], 1)
        self.enviar(opcion='omitir')
        self.enviar(opcion='pausar')
        salida = self.enviar(opcion='terminar')
        self.assertEqual(salida['resultado']['respondidas'], 1)
        self.assertTrue(all(d['promedio'] is None for d in salida['resultado']['dimensiones']))

    def test_rechaza_opcion_y_pregunta_ajenas(self):
        self.iniciar_test()
        with self.assertRaises(ValueError):
            self.enviar(opcion='6')
        with self.assertRaises(ValueError):
            procesar(self.estado, '3', '3', 'otra_pregunta')
        self.assertEqual(self.estado['indice'], 0)

    def test_crisis_interrumpe_sin_puntuar(self):
        self.iniciar_test()
        salida = self.enviar('No quiero vivir')
        self.assertEqual(self.estado['etapa'], 'apoyo')
        self.assertIsNone(salida['pregunta'])
        self.assertEqual(self.estado['respuestas'], {})

    def test_resultado_disponible_si_falla_interpretacion(self):
        self.iniciar_test()
        self.estado['indice'] = 13
        self.estado['respuestas'] = {p[0]: 2 for p in PREGUNTAS[:13]}
        self.modelo.side_effect = ErrorModelo('Sin conexión')
        salida = self.enviar(opcion='2')
        self.assertEqual(salida['resultado']['respondidas'], 14)
        self.assertIn('no estuvo disponible', salida['contenido'])


class ApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.modelo = patch('ml.conversacion.responder', return_value='Hola.').start()
        self.addCleanup(patch.stopall)
        self.client = Client(enforce_csrf_checks=True)
        self.token = self.client.get('/api/csrf/').json()['csrfToken']

    def enviar(self, datos):
        return self.client.post('/api/chat/', datos, content_type='application/json', HTTP_X_CSRFTOKEN=self.token)

    def test_csrf_y_validacion(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/api/chat/', {}, content_type='application/json').status_code, 403)
        for datos in ([], {}, {'mensaje': ' '}, {'mensaje': 'a' * 2001}, {'mensaje': 1}, {'mensaje': 'Hola', 'opcion': []}):
            with self.subTest(datos=type(datos).__name__):
                self.assertEqual(self.enviar(datos).status_code, 400)

    def test_sesion_borrar_y_caducidad(self):
        salida = self.enviar({'mensaje': 'Hola'}).json()
        sesion_id = salida['sesion_id']
        self.assertEqual(len(sesion_id), 32)
        self.assertEqual(self.client.delete(f'/api/chat/{sesion_id}/', HTTP_X_CSRFTOKEN=self.token).status_code, 200)
        self.assertEqual(self.enviar({'sesion_id': sesion_id, 'mensaje': 'Alex', 'pregunta_id': 'nombre'}).status_code, 410)

    def test_fallo_modelo_no_avanza_estado(self):
        salida = self.enviar({'mensaje': 'Hola'}).json()
        sesion_id = salida['sesion_id']
        self.enviar({'sesion_id': sesion_id, 'pregunta_id': 'nombre', 'mensaje': 'Alex'})
        self.enviar({'sesion_id': sesion_id, 'pregunta_id': 'grado', 'opcion': 'quinto'})
        self.modelo.side_effect = ErrorModelo('Sin conexión')
        datos = {'sesion_id': sesion_id, 'pregunta_id': 'contexto', 'mensaje': 'Tengo tareas'}
        self.assertEqual(self.enviar(datos).status_code, 503)
        self.assertEqual(cache.get('chat:' + sesion_id)['etapa'], 'contexto')
        self.modelo.side_effect = None
        self.assertEqual(self.enviar(datos).json()['pregunta']['id'], 'decision')

    def test_sesiones_no_comparten_datos(self):
        primera = self.enviar({'mensaje': 'Hola'}).json()['sesion_id']
        segunda = self.enviar({'mensaje': 'Hola'}).json()['sesion_id']
        self.enviar({'sesion_id': primera, 'pregunta_id': 'nombre', 'mensaje': 'Ana'})
        self.assertEqual(cache.get('chat:' + segunda)['perfil'], {})
