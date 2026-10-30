import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings

from usuarios.models import Perfil
from usuarios.retencion import VERSION_TERMINOS


class CuentasTests(TestCase):
    def setUp(self):
        cache.clear()

    def post(self, ruta, datos, cliente=None):
        if ruta == '/api/auth/registro/':
            datos = {'acepta_terminos': True, 'version_terminos': VERSION_TERMINOS, **datos}
        return (cliente or self.client).post(ruta, json.dumps(datos), content_type='application/json')

    def test_registro_usuario_guarda_hash_e_inicia_sesion(self):
        respuesta = self.post('/api/auth/registro/', {'username': ' ESTUDIANTE49 ', 'nombre': 'Ana', 'password': 'SolBosque!7285'})
        self.assertEqual(respuesta.status_code, 201)
        usuario = get_user_model().objects.get()
        self.assertEqual(usuario.username, 'estudiante49')
        self.assertEqual(usuario.email, '')
        self.assertTrue(usuario.check_password('SolBosque!7285'))
        self.assertFalse(usuario.is_staff)
        self.assertEqual(self.client.get('/api/auth/me/').json()['usuario']['nombre'], 'Ana')
        self.assertEqual(usuario.semanas.count(), 0)

    def test_registro_rechaza_usuario_invalido_clave_debil_y_duplicado(self):
        datos = {'username': 'ana@example.com', 'password': 'SolBosque!7285'}
        self.assertEqual(self.post('/api/auth/registro/', datos).status_code, 400)
        datos['username'] = 'ana49'
        datos['password'] = '12345678'
        self.assertEqual(self.post('/api/auth/registro/', datos).status_code, 400)
        datos['password'] = 'SolBosque!7285'
        self.assertEqual(self.post('/api/auth/registro/', datos).status_code, 201)
        self.assertEqual(self.post('/api/auth/registro/', datos).status_code, 409)

    def test_login_logout_y_password_incorrecta(self):
        get_user_model().objects.create_user(username='ana@gmail.com', email='ana@gmail.com', password='SolBosque!7285')
        self.assertEqual(self.post('/api/auth/login/', {'email': 'ana@gmail.com', 'password': 'incorrecta'}).status_code, 401)
        self.assertEqual(self.post('/api/auth/login/', {'email': 'ANA@gmail.com', 'password': 'SolBosque!7285'}).status_code, 200)
        self.assertEqual(self.post('/api/auth/logout/', {}).status_code, 200)
        self.assertIsNone(self.client.get('/api/auth/me/').json()['usuario'])

    def test_formatos_username_y_limites_ascii(self):
        for username in ('ab', 'a' * 41, '4alumno', '.ana', 'ana@gmail.com', 'niño', 'álvaro', 'Kevin', 'ana uno', 'ana/uno', None, 49):
            with self.subTest(username=username):
                self.assertEqual(self.post('/api/auth/registro/', {'username': username, 'password': 'BosqueLluvia!8724'}).status_code, 400)
        for username in ('Ana', 'A' * 40, 'Ana.49', 'Ana-49', 'Ana_49'):
            with self.subTest(username=username):
                r = self.post('/api/auth/registro/', {'username': username, 'password': 'BosqueLluvia!8724'})
                self.assertEqual(r.status_code, 201)
                self.assertEqual(r.json()['usuario']['username'], username.lower())

    def test_no_guarda_correo_ni_concede_privilegios_del_payload(self):
        r = self.post('/api/auth/registro/', {'username': 'estudiante49', 'nombre': 'Ana', 'password': 'BosqueLluvia!8724', 'email': 'ignorar@example.com', 'is_staff': True, 'is_superuser': True, 'groups': [1]})
        self.assertEqual(r.status_code, 201)
        u = get_user_model().objects.get(username='estudiante49')
        self.assertEqual(u.email, '')
        self.assertFalse(u.is_staff or u.is_superuser or u.groups.exists() or u.user_permissions.exists())
        self.assertEqual(self.client.get('/api/admin/alumnos/').status_code, 403)
        self.assertEqual(self.client.get('/api/auth/me/').json()['usuario']['username'], 'estudiante49')
        self.assertTrue(u.perfil.terminos_aceptados_en)
        self.assertEqual(r.json()['usuario']['retencion_dias'], 90)

    def test_duplicado_de_cuenta_anterior_sin_distinguir_mayusculas(self):
        u = get_user_model().objects.create_user(username='Estudiante49', password='BosqueLluvia!8724')
        original = u.password
        r = self.post('/api/auth/registro/', {'username': 'ESTUDIANTE49', 'password': 'BosqueLluvia!8724'})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(get_user_model().objects.count(), 1)
        u.refresh_from_db()
        self.assertEqual(u.password, original)
        r = self.post('/api/auth/login/', {'username': 'ESTUDIANTE49', 'password': 'BosqueLluvia!8724'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['usuario']['id'], u.pk)

    def test_login_no_elige_entre_identidades_ambiguas(self):
        for username in ('Estudiante49', 'estudiante49'):
            get_user_model().objects.create_user(username=username, password='BosqueLluvia!8724')
        self.assertEqual(self.post('/api/auth/login/', {'username': 'estudiante49', 'password': 'BosqueLluvia!8724'}).status_code, 401)

    def test_username_en_listado_y_detalle_administrativo(self):
        alumno = get_user_model().objects.create_user(username='estudiante49', password='BosqueLluvia!8724')
        admin = get_user_model().objects.create_user(username='admin', password='BosqueLluvia!8724', is_staff=True)
        self.client.force_login(admin)
        self.assertEqual(self.client.get('/api/admin/alumnos/').json()['alumnos'][0]['username'], 'estudiante49')
        self.assertEqual(self.client.get(f'/api/admin/alumnos/{alumno.pk}/').json()['alumno']['username'], 'estudiante49')

    @override_settings(DEBUG=True)
    def test_login_admite_username_de_estudiante_y_admin(self):
        get_user_model().objects.create_user(username='ana@gmail.com', email='ana@gmail.com', password='SolBosque!7285')
        respuesta = self.post('/api/auth/login/', {'username': ' ANA@GMAIL.COM ', 'password': 'SolBosque!7285'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['usuario']['username'], 'ana@gmail.com')
        self.post('/api/auth/logout/', {})
        call_command('preparar_admin', stdout=StringIO())
        respuesta = self.post('/api/auth/login/', {'username': ' ADMIN ', 'password': 'admin'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['usuario']['es_admin'])
        self.assertEqual(respuesta.json()['usuario']['username'], 'admin')
        self.assertEqual(self.client.get('/api/admin/alumnos/', HTTP_X_ADMIN_PESTANA=respuesta.json()['admin_pestana']).status_code, 200)

    def test_login_rechaza_datos_invalidos_con_error_generico(self):
        for datos in [
            {'username': ['admin'], 'password': 'admin'},
            {'username': 'admin', 'password': ['admin']},
            {'username': '', 'password': 'admin'},
            {'username': 'admin', 'password': 'incorrecta'},
        ]:
            respuesta = self.post('/api/auth/login/', datos)
            self.assertEqual(respuesta.status_code, 401)
            self.assertEqual(respuesta.json()['error'], 'Usuario o contraseña incorrectos.')

    def test_mutaciones_requieren_csrf_real(self):
        cliente = Client(enforce_csrf_checks=True)
        datos = {'username': 'csrf49', 'password': 'SolBosque!7285', 'acepta_terminos': True, 'version_terminos': VERSION_TERMINOS}
        self.assertEqual(self.post('/api/auth/registro/', datos, cliente).status_code, 403)
        token = cliente.get('/api/csrf/').json()['csrfToken']
        self.assertEqual(cliente.post('/api/auth/registro/', json.dumps(datos), content_type='application/json', HTTP_X_CSRFTOKEN=token).status_code, 201)
        token_nuevo = cliente.get('/api/csrf/').json()['csrfToken']
        self.assertEqual(cliente.post('/api/auth/logout/', '{}', content_type='application/json', HTTP_X_CSRFTOKEN=token_nuevo).status_code, 200)

    def test_acceso_anonimo_y_estudiante_a_reportes_se_deniega(self):
        self.assertEqual(self.client.get('/api/chat/').status_code, 401)
        usuario = get_user_model().objects.create_user(username='alumno@gmail.com', password='SolBosque!7285')
        self.client.force_login(usuario)
        self.assertEqual(self.client.get('/api/admin/alumnos/').status_code, 403)

    def test_respuestas_de_auth_chat_y_errores_no_se_almacenan_en_cache(self):
        for ruta in ['/api/csrf/', '/api/auth/me/', '/api/chat/', '/api/admin/alumnos/']:
            respuesta = self.client.get(ruta)
            self.assertIn('no-store', respuesta.headers['Cache-Control'])
            self.assertIn('private', respuesta.headers['Cache-Control'])
        usuario = get_user_model().objects.create_user(username='privado@gmail.com', password='SolBosque!7285')
        self.client.force_login(usuario)
        self.assertIn('no-store', self.client.get('/api/chat/').headers['Cache-Control'])
        self.assertIn('no-store', self.client.get('/api/auth/me/').headers['Cache-Control'])

    def test_fallo_csrf_devuelve_json_amigable_y_no_cacheable(self):
        cliente = Client(enforce_csrf_checks=True)
        respuesta = self.post('/api/auth/login/', {'email': 'alumno@gmail.com', 'password': 'incorrecta'}, cliente)
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn('sesión de seguridad', respuesta.json()['error'])
        self.assertIn('no-store', respuesta.headers['Cache-Control'])


@override_settings(DEBUG=True)
class PrepararAdminTests(TestCase):
    def preparar(self):
        call_command('preparar_admin', stdout=StringIO())

    def test_crea_admin_local_sin_privilegios_de_superusuario(self):
        self.preparar()
        usuario = get_user_model().objects.get(username='admin')
        self.assertTrue(usuario.check_password('admin'))
        self.assertNotEqual(usuario.password, 'admin')
        self.assertTrue(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(Perfil.objects.filter(usuario=usuario).exists())

    def test_no_resetea_contrasena_ni_privilegios_de_admin_existente(self):
        usuario = get_user_model().objects.create_user(
            username='admin', password='OtraContrasena!729', is_staff=True, is_superuser=True,
        )
        password_original = usuario.password
        self.preparar()
        self.preparar()
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, password_original)
        self.assertTrue(usuario.is_superuser)
        self.assertEqual(get_user_model().objects.filter(username='admin').count(), 1)

    def test_no_eleva_cuenta_existente_no_admin(self):
        usuario = get_user_model().objects.create_user(username='admin', password='OtraContrasena!729')
        with self.assertRaisesMessage(CommandError, 'No se modificó'):
            self.preparar()
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.check_password('OtraContrasena!729'))

    @override_settings(DEBUG=False)
    def test_no_crea_cuenta_predeterminada_en_produccion(self):
        with self.assertRaisesMessage(CommandError, 'DEBUG=True'):
            self.preparar()
        self.assertFalse(get_user_model().objects.filter(username='admin').exists())

    def test_runserver_prepara_admin_antes_del_servidor(self):
        from usuarios.management.commands.runserver import Command

        with patch('usuarios.management.commands.runserver.RunserverCommand.handle', return_value=None) as servidor:
            Command(stdout=StringIO()).handle()
        servidor.assert_called_once()
        self.assertTrue(get_user_model().objects.get(username='admin').check_password('admin'))
