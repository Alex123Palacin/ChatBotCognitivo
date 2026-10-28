import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ml.ollama import ErrorModelo
from usuarios.models import Perfil
from .models import Mensaje


class FlujoChatTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username='flujo@gmail.com', first_name='Ana')
        Perfil.objects.create(usuario=self.usuario)
        self.client.force_login(self.usuario)

    def enviar(self, clave=None, texto='Me preocupan las tareas del colegio'):
        return self.client.post('/api/chat/flujo/', json.dumps({
            'mensaje': texto, 'clave_envio': str(clave or uuid.uuid4()),
        }), content_type='application/json')

    def eventos(self, respuesta):
        return [json.loads(linea) for linea in respuesta.streaming_content]

    @patch('chat.services.responder_conversacion_stream')
    def test_entrega_texto_antes_de_guardar_la_respuesta_completa(self, modelo):
        modelo.return_value = iterador = (texto for texto in ['Podemos ', 'ir paso a paso.'])
        respuesta = self.enviar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('application/x-ndjson', respuesta['Content-Type'])
        self.assertEqual(respuesta['X-Accel-Buffering'], 'no')
        flujo = iter(respuesta.streaming_content)
        self.assertEqual(json.loads(next(flujo))['tipo'], 'inicio')
        self.assertEqual(json.loads(next(flujo)), {'tipo': 'fragmento', 'contenido': 'Podemos '})
        self.assertEqual(Mensaje.objects.filter(remitente='asistente').count(), 0)
        self.usuario.perfil.refresh_from_db()
        self.assertIsNotNone(self.usuario.perfil.respuesta_hasta)
        resto = [json.loads(linea) for linea in flujo]
        self.assertEqual(resto[-1]['tipo'], 'estado')
        self.assertEqual(resto[-1]['chat']['mensajes'][-1]['contenido'], 'Podemos ir paso a paso.')
        self.assertEqual(Mensaje.objects.count(), 2)
        self.usuario.perfil.refresh_from_db()
        self.assertIsNone(self.usuario.perfil.respuesta_hasta)
        self.assertEqual(len(resto[-1]['chat']['sesiones']), 1)
        self.assertIsNone(resto[-1]['chat']['sesion_actual']['fin'])
        iterador.close()

    @patch('chat.services.responder_conversacion_stream')
    def test_reintento_no_duplica_ni_vuelve_a_generar(self, modelo):
        modelo.return_value = (texto for texto in ['Te escucho.'])
        clave = uuid.uuid4()
        self.eventos(self.enviar(clave))
        repetido = self.eventos(self.enviar(clave))
        self.assertEqual(modelo.call_count, 1)
        self.assertEqual(Mensaje.objects.count(), 2)
        self.assertEqual([e['tipo'] for e in repetido], ['inicio', 'estado'])

    @patch('chat.services.responder_conversacion_stream')
    def test_fallo_parcial_no_guarda_asistente_y_permite_reintento(self, modelo):
        def interrumpido():
            yield 'Vamos '
            raise ErrorModelo('La generación se interrumpió.')
        modelo.return_value = interrumpido()
        clave = uuid.uuid4()
        eventos = self.eventos(self.enviar(clave))
        self.assertEqual(eventos[-1]['tipo'], 'error')
        self.assertEqual(Mensaje.objects.count(), 1)
        self.assertEqual(self.client.get('/api/chat/').json()['mensaje_pendiente']['estado'], 'error')
        modelo.return_value = (texto for texto in ['Podemos empezar por una tarea.'])
        self.assertEqual(self.eventos(self.enviar(clave))[-1]['tipo'], 'estado')
        self.assertEqual(Mensaje.objects.count(), 2)

    @patch('chat.services.responder_conversacion_stream')
    def test_cerrar_navegador_cierra_modelo_y_libera_reserva(self, modelo):
        cerrado = []
        def interrumpido():
            try:
                yield 'Podemos '
                yield 'seguir.'
            finally:
                cerrado.append(True)
        modelo.return_value = interrumpido()
        respuesta = self.enviar()
        flujo = iter(respuesta.streaming_content)
        next(flujo)
        next(flujo)
        respuesta.close()
        self.assertEqual(cerrado, [True])
        self.assertFalse(Mensaje.objects.filter(remitente='asistente').exists())
        self.usuario.perfil.refresh_from_db()
        self.assertIsNone(self.usuario.perfil.respuesta_hasta)

    @patch('chat.services.responder_conversacion_stream')
    def test_entrada_invalida_y_acceso_se_comprueban(self, modelo):
        self.assertEqual(self.eventos(self.enviar(texto=' '))[-1]['tipo'], 'error')
        self.assertEqual(Mensaje.objects.count(), 0)
        self.assertEqual(self.client.get('/api/chat/flujo/').status_code, 405)
        self.client.logout()
        self.assertEqual(self.enviar().status_code, 401)
        admin = get_user_model().objects.create_user(username='administrador', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.enviar().status_code, 403)
        modelo.assert_not_called()

    def test_stream_no_desactiva_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post('/api/chat/flujo/', '{}', content_type='application/json').status_code, 403)

    def test_saludo_escolar_usa_flujo_real_sin_consultar_ollama(self):
        with patch('ml.conversacion.generar_flujo') as modelo:
            eventos = self.eventos(self.enviar(texto='Hola'))
        modelo.assert_not_called()
        self.assertEqual(eventos[-1]['tipo'], 'estado')
        self.assertIn('colegio', eventos[-1]['chat']['mensajes'][-1]['contenido'])
