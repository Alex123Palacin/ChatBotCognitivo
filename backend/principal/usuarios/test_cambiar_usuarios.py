from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings

from chat.models import Mensaje
from reportes.models import Evidencia, ReporteSemanal
from sesiones.models import SesionSemanal
from usuarios.carga_actividad import importar_paquete, validar_paquete
from usuarios.test_carga_actividad import paquete_prueba
from usuarios.cambio_usuarios import ejecutar


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
class CambiarUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'CaminosDeLima!58327'
        cls.datos = paquete_prueba(make_password(cls.password))
        with patch('usuarios.carga_actividad._crear_respaldo', return_value='/privado/respaldo.sqlite3'):
            importar_paquete(validar_paquete(cls.datos), aplicar=True, validar_entorno=False)

    def setUp(self):
        self.mapa = {'schema': 'chatcognitivo.usuarios.v1', 'lote': 'usuarios-prueba-v1', 'cuentas': [
            {'anterior': c['email'], 'nuevo': f'estudiante{n+49}', 'nombre_anterior': c['nombre'],
             'fecha_alta': c['fecha_alta'], 'primer_mensaje_id': c['mensajes'][0]['id'], 'ultimo_mensaje_id': c['mensajes'][-1]['id']}
            for n, c in enumerate(self.datos['cuentas'])]}
        self.backup = patch('usuarios.carga_actividad._crear_respaldo', return_value='/privado/respaldo.sqlite3')
        self.backup_mock = self.backup.start()
        self.addCleanup(self.backup.stop)

    def convertir(self, aplicar=True):
        return ejecutar(self.mapa, aplicar=aplicar, validar_entorno=False)

    def test_validacion_sin_escrituras_ni_respaldo(self):
        antes = list(get_user_model().objects.values())
        self.assertEqual(self.convertir(False)['por_cambiar'], 2)
        self.assertEqual(antes, list(get_user_model().objects.values()))
        self.backup_mock.assert_not_called()

    def test_conserva_ids_passwords_conversaciones_analisis_fechas_y_admin(self):
        admin = get_user_model().objects.create_user('admin', password=self.password, is_staff=True)
        admin_datos = list(get_user_model().objects.filter(pk=admin.pk).values())
        antes = [list(m.objects.values()) for m in (Mensaje, Evidencia, ReporteSemanal, SesionSemanal)]
        identidades = list(get_user_model().objects.filter(is_staff=False).order_by('pk').values_list('pk', 'password'))
        self.assertEqual(self.convertir()['convertidas'], 2)
        self.assertEqual(antes, [list(m.objects.values()) for m in (Mensaje, Evidencia, ReporteSemanal, SesionSemanal)])
        self.assertEqual(identidades, list(get_user_model().objects.filter(is_staff=False).order_by('pk').values_list('pk', 'password')))
        self.assertEqual(admin_datos, list(get_user_model().objects.filter(pk=admin.pk).values()))
        usuario = authenticate(username='estudiante49', password=self.password)
        self.assertIsNotNone(usuario)
        self.assertEqual((usuario.first_name, usuario.email), ('estudiante49', ''))
        self.assertIsNone(authenticate(username=self.datos['cuentas'][0]['email'], password=self.password))
        self.backup_mock.assert_called_once()

    def test_repeticion_no_duplica_y_conserva_cambio_de_password_posterior(self):
        self.convertir()
        usuario = get_user_model().objects.get(username='estudiante49')
        usuario.set_password('NuevaClavePropia!74825')
        usuario.save(update_fields=['password'])
        self.backup_mock.reset_mock()
        self.assertEqual(self.convertir()['ya_convertidas'], 2)
        self.assertEqual(get_user_model().objects.count(), 2)
        self.assertTrue(get_user_model().objects.get(pk=usuario.pk).check_password('NuevaClavePropia!74825'))
        self.backup_mock.assert_not_called()

    def test_colision_caseinsensitive_cancela_todo(self):
        get_user_model().objects.create_user('ESTUDIANTE50')
        with self.assertRaises(ValueError):
            self.convertir()
        self.assertTrue(get_user_model().objects.filter(username=self.datos['cuentas'][0]['email']).exists())
        self.backup_mock.assert_not_called()

    def test_ancla_ajena_o_administrador_no_se_cambia(self):
        original = deepcopy(self.mapa)
        self.mapa['cuentas'][0]['primer_mensaje_id'] = self.mapa['cuentas'][1]['primer_mensaje_id']
        with self.assertRaises(ValueError):
            self.convertir()
        self.mapa = original
        get_user_model().objects.filter(username=self.datos['cuentas'][0]['email']).update(is_staff=True)
        with self.assertRaises(ValueError):
            self.convertir()

    def test_error_intermedio_revierte_el_lote(self):
        original = QuerySet.update
        veces = 0
        def fallar(qs, **kwargs):
            nonlocal veces
            if qs.model is get_user_model() and 'username' in kwargs:
                veces += 1
                if veces == 2:
                    raise RuntimeError('fallo controlado')
            return original(qs, **kwargs)
        with patch.object(QuerySet, 'update', fallar), self.assertRaises(RuntimeError):
            self.convertir()
        self.assertFalse(get_user_model().objects.filter(username='estudiante49').exists())
        self.assertEqual(get_user_model().objects.filter(username__endswith='@example.com').count(), 2)
