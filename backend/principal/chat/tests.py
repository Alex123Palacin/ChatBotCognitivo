from datetime import timedelta
import json
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ml.ollama import ErrorModelo
from sesiones.models import SesionSemanal
from sesiones.services import iniciar_programa
from usuarios.models import Perfil
from .models import Mensaje


class ChatPersistenteTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username='ana@gmail.com', email='ana@gmail.com', password='SolBosque!7285', first_name='Ana')
        self.perfil = Perfil.objects.create(usuario=self.usuario)
        self.client.force_login(self.usuario)

    def enviar(self, texto='Tengo muchos trabajos esta semana', clave=None):
        return self.client.post('/api/chat/', json.dumps({'mensaje': texto, 'clave_envio': str(clave or uuid.uuid4())}), content_type='application/json')

    @patch('chat.services.responder_conversacion', return_value='Parece una semana exigente. ¿Qué te preocupa más ahora?')
    def test_primer_mensaje_crea_conversacion_abierta_y_historial_persiste(self, modelo):
        respuesta = self.enviar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()['mensajes']), 2)
        self.assertEqual(len(respuesta.json()['sesiones']), 1)
        self.assertIsNone(SesionSemanal.objects.get().fin)
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(len(self.client.get('/api/chat/').json()['mensajes']), 2)
        self.assertEqual(modelo.call_args.args[0][-1]['role'], 'user')

    @patch('chat.services.responder_conversacion', return_value='Te escucho.')
    def test_reenvio_es_idempotente_y_no_duplica_mensaje_o_respuesta(self, modelo):
        clave = uuid.uuid4()
        self.assertEqual(self.enviar(clave=clave).status_code, 200)
        self.assertEqual(self.enviar(clave=clave).status_code, 200)
        self.assertEqual(modelo.call_count, 1)
        self.assertEqual(Mensaje.objects.count(), 2)
        self.assertEqual(self.enviar('Texto diferente', clave).status_code, 409)

    @patch('chat.services.responder_conversacion', side_effect=ErrorModelo('Ollama no responde.'))
    def test_fallo_modelo_guarda_mensaje_y_permite_reintentar_misma_clave(self, modelo):
        clave = uuid.uuid4()
        self.assertEqual(self.enviar(clave=clave).status_code, 503)
        estado = self.client.get('/api/chat/').json()
        self.assertEqual(len(estado['mensajes']), 1)
        self.assertEqual(estado['mensaje_pendiente']['clave_envio'], str(clave))
        self.assertEqual(estado['mensaje_pendiente']['estado'], 'error')
        self.assertFalse(estado['respuesta_pendiente'])
        self.assertEqual(self.enviar('Mensaje distinto').status_code, 409)
        modelo.side_effect = None
        modelo.return_value = 'Podemos hablar de lo que más te preocupa.'
        self.assertEqual(self.enviar(clave=clave).status_code, 200)
        self.assertEqual(Mensaje.objects.count(), 2)

    @patch('chat.services.responder_conversacion', return_value='Aquí estoy.')
    def test_continuar_historico_conserva_fechas_y_no_bloquea_a_los_28_dias(self, modelo):
        inicio = timezone.now() - timedelta(days=8)
        iniciar_programa(self.perfil, inicio)
        fechas_historicas = list(SesionSemanal.objects.values_list('pk', 'inicio', 'fin'))
        self.assertEqual(self.enviar().json()['mensajes'][0]['sesion_numero'], 5)
        self.assertEqual(SesionSemanal.objects.count(), 5)
        with patch('chat.services.timezone.now', return_value=inicio + timedelta(days=28)):
            # Al adelantar 20 días también vence la cookie Django de 14 días.
            self.client.force_login(self.usuario)
            self.assertEqual(self.enviar('Otro mensaje').status_code, 200)
            self.assertFalse(self.client.get('/api/chat/').json()['programa_finalizado'])
        self.assertEqual(list(SesionSemanal.objects.filter(fin__isnull=False).values_list('pk', 'inicio', 'fin')), fechas_historicas)

    @patch('chat.services.responder_conversacion', return_value='Te escucho.')
    def test_historial_personal_no_expone_otros_estudiantes(self, modelo):
        self.enviar()
        otro = get_user_model().objects.create_user(username='otra@gmail.com', password='SolBosque!7285')
        self.client.force_login(otro)
        self.assertEqual(self.client.get('/api/chat/').json()['mensajes'], [])

    @patch('chat.services.responder_conversacion')
    def test_no_acepta_dos_respuestas_simultaneas(self, modelo):
        self.perfil.respuesta_hasta = timezone.now() + timedelta(seconds=60)
        self.perfil.respuesta_token = str(uuid.uuid4())
        self.perfil.save()
        self.assertEqual(self.enviar().status_code, 409)
        modelo.assert_not_called()

    def test_entrada_invalida_no_inicia_programa(self):
        self.assertEqual(self.enviar(' ').status_code, 400)
        self.assertEqual(SesionSemanal.objects.count(), 0)

    @patch('chat.services.responder_conversacion', return_value='Podemos seguir conversando.')
    def test_cruzar_siete_dias_no_divide_ni_borra_la_conversacion(self, modelo):
        inicio = timezone.now()
        iniciar_programa(self.perfil, inicio)
        fin_primera_semana = inicio + timedelta(days=7)
        with patch('chat.services.timezone.now', return_value=fin_primera_semana - timedelta(microseconds=1)):
            respuesta = self.enviar('El mensaje de la primera semana')
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json()['sesion_actual']['numero'], 5)
        with patch('chat.services.timezone.now', return_value=fin_primera_semana):
            respuesta = self.enviar('Ahora sigo en la siguiente semana')
            self.assertEqual(respuesta.status_code, 200)
            datos = respuesta.json()
            self.assertEqual(datos['sesion_actual']['numero'], 5)
            alumnos = [m for m in datos['mensajes'] if m['remitente'] == 'usuario']
            self.assertEqual([m['sesion_numero'] for m in alumnos], [5, 5])
            self.assertEqual(len(datos['mensajes']), 4)
            self.assertEqual(datos['sesiones'][0]['estado'], 'cerrada')

    @patch('chat.services.responder_conversacion', side_effect=ErrorModelo('Ollama no responde.'))
    def test_mensaje_guardado_antes_del_fin_se_recupera_despues_de_cuatro_semanas(self, modelo):
        inicio = timezone.now() - timedelta(days=27)
        iniciar_programa(self.perfil, inicio)
        fin_programa = inicio + timedelta(days=28)
        clave = uuid.uuid4()
        with patch('chat.services.timezone.now', return_value=fin_programa - timedelta(microseconds=1)):
            self.assertEqual(self.enviar('Último relato antes del cierre', clave).status_code, 503)
        modelo.side_effect = None
        modelo.return_value = 'Te escucho; gracias por compartirlo.'
        with patch('chat.services.timezone.now', return_value=fin_programa):
            respuesta = self.enviar('Último relato antes del cierre', clave)
            self.assertEqual(respuesta.status_code, 200)
            self.assertFalse(respuesta.json()['programa_finalizado'])
            self.assertEqual([m['sesion_numero'] for m in respuesta.json()['mensajes']], [5, 5])
            self.assertEqual(self.enviar('Un mensaje nuevo fuera del programa').status_code, 200)
            self.assertEqual(SesionSemanal.objects.count(), 5)
            self.assertEqual(Mensaje.objects.count(), 4)
