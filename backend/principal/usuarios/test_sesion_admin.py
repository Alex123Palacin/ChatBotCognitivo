from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone


class SesionAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('admin_temporal', password='BosqueLluvia!8724', is_staff=True)
        respuesta = self.client.post('/api/auth/login/', {'username': self.admin.username, 'password': 'BosqueLluvia!8724'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.token = respuesta.json()['admin_pestana']
        self.cabeceras = {'HTTP_X_ADMIN_PESTANA': self.token}

    def test_pestana_sin_token_no_accede_ni_cierra_la_pestana_valida(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.client.get('/api/auth/me/', **self.cabeceras).status_code, 200)
        self.assertEqual(self.client.session.get_expiry_age(), 600)

    def test_consultas_automaticas_no_renuevan_inactividad(self):
        ultima = self.client.session['admin_actividad']
        self.client.get('/api/auth/me/', **self.cabeceras)
        self.assertEqual(self.client.session['admin_actividad'], ultima)
        with patch('usuarios.sesion_admin.timezone.now', return_value=timezone.now() + timedelta(minutes=10, seconds=1)):
            self.assertEqual(self.client.get('/api/admin/alumnos/', **self.cabeceras).status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_actividad_autorizada_renueva_y_caducada_no_se_reactiva(self):
        inicio = timezone.now()
        with patch('usuarios.sesion_admin.timezone.now', return_value=inicio + timedelta(minutes=8)):
            self.assertEqual(self.client.post('/api/auth/actividad-admin/', **self.cabeceras).status_code, 200)
        with patch('usuarios.sesion_admin.timezone.now', return_value=inicio + timedelta(minutes=12)):
            self.assertEqual(self.client.get('/api/auth/me/', **self.cabeceras).status_code, 200)
        with patch('usuarios.sesion_admin.timezone.now', return_value=inicio + timedelta(minutes=19)):
            self.assertEqual(self.client.post('/api/auth/actividad-admin/', **self.cabeceras).status_code, 401)

    def test_sin_token_puede_preparar_csrf_e_iniciar_sesion_nuevamente(self):
        self.assertEqual(self.client.get('/api/csrf/').status_code, 200)
        respuesta = self.client.post('/api/auth/login/', {'username': self.admin.username, 'password': 'BosqueLluvia!8724'}, content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotEqual(self.token, respuesta.json()['admin_pestana'])
        self.assertEqual(self.client.get('/api/auth/me/', **self.cabeceras).status_code, 401)

    def test_estudiante_conserva_su_sesion_y_no_puede_enviar_actividad_admin(self):
        alumno = get_user_model().objects.create_user('alumno_temporal')
        self.client.force_login(alumno)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/actividad-admin/').status_code, 403)
