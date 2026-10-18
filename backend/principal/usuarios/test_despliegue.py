from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings


class AdministradorProduccionTests(TestCase):
    def preparar(self, password='BosqueClaro!8472', username='admin'):
        with patch.dict(os.environ, {'DJANGO_ADMIN_USERNAME': username, 'DJANGO_ADMIN_PASSWORD': password}):
            call_command('preparar_admin_produccion', stdout=StringIO())

    def test_crea_admin_con_hash_y_no_lo_resetea_al_reiniciar(self):
        self.preparar()
        usuario = get_user_model().objects.get(username='admin')
        self.assertTrue(usuario.check_password('BosqueClaro!8472'))
        self.assertTrue(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertEqual(usuario.perfil.usuario_id, usuario.pk)
        self.preparar(password='OtraClaveNueva!7294')
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('BosqueClaro!8472'))

    def test_rechaza_claves_vacias_y_de_desarrollo(self):
        for password in ('', 'admin'):
            with self.subTest(password=password):
                with self.assertRaises(CommandError):
                    self.preparar(password=password)
        self.assertFalse(get_user_model().objects.exists())

    def test_no_eleva_cuenta_existente(self):
        usuario = get_user_model().objects.create_user(username='admin', password='BosqueClaro!8472')
        with self.assertRaises(CommandError):
            self.preparar()
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_staff)

    def test_rechaza_admin_importado_con_clave_local(self):
        get_user_model().objects.create_user(username='admin', password='admin', is_staff=True)
        with self.assertRaisesMessage(CommandError, 'contraseña local'):
            self.preparar()

    def test_admin_local_solo_con_excepcion_explicita_y_usuario_admin(self):
        with patch.dict(os.environ, {'DJANGO_ALLOW_INSECURE_ADMIN': 'true'}):
            self.preparar(password='admin')
            self.preparar(password='admin')
            usuario = get_user_model().objects.get(username='admin')
            self.assertTrue(usuario.is_staff)
            self.assertTrue(usuario.check_password('admin'))
            self.assertNotEqual(usuario.password, 'admin')
            with self.assertRaises(CommandError):
                self.preparar(password='admin', username='otra_cuenta')


class ConfiguracionDespliegueTests(TestCase):
    def test_produccion_no_arranca_sin_clave_secreta(self):
        entorno = os.environ.copy()
        entorno['DJANGO_DEBUG'] = 'false'
        entorno.pop('DJANGO_SECRET_KEY', None)
        proceso = subprocess.run(
            [sys.executable, '-c', 'import principal.settings'],
            cwd=Path(__file__).resolve().parents[1], env=entorno,
            capture_output=True, text=True, timeout=10,
        )
        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', proceso.stderr)

    @override_settings(
        ALLOWED_HOSTS=['chatcognitivo.tech', 'localhost'],
        CSRF_TRUSTED_ORIGINS=['https://chatcognitivo.tech'],
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
    )
    def test_https_detras_del_proxy_permite_csrf_y_rechaza_otro_origen(self):
        cliente = Client(enforce_csrf_checks=True)
        token = cliente.get('/api/csrf/', HTTP_HOST='chatcognitivo.tech', HTTP_X_FORWARDED_PROTO='https').json()['csrfToken']
        self.assertTrue(cliente.cookies['csrftoken']['secure'])
        respuesta = cliente.post(
            '/api/auth/login/', json.dumps({}), content_type='application/json',
            HTTP_HOST='chatcognitivo.tech', HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN='https://chatcognitivo.tech', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(respuesta.status_code, 401)
        respuesta = cliente.post(
            '/api/auth/login/', '{}', content_type='application/json',
            HTTP_HOST='chatcognitivo.tech', HTTP_X_FORWARDED_PROTO='https',
            HTTP_ORIGIN='https://example.invalid', HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(respuesta.status_code, 403)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_salud_interna_no_redirige_ni_revela_datos(self):
        respuesta = self.client.get('/api/salud/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {'estado': 'ok'})
        self.assertIn('no-store', respuesta.headers['Cache-Control'])

    def test_salud_detecta_base_no_disponible(self):
        with patch('principal.http.connection.cursor', side_effect=DatabaseError('detalle privado')):
            respuesta = self.client.get('/api/salud/')
        self.assertEqual(respuesta.status_code, 503)
        self.assertNotIn('detalle privado', respuesta.content.decode())
