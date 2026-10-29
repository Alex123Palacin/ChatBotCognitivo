from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from chat.models import Mensaje
from sesiones.models import SesionSemanal
from usuarios.models import Perfil
from usuarios.retencion import VERSION_TERMINOS, VERSION_ANTERIOR, limpiar_conversaciones


class RetencionAccesoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.ahora = timezone.now()
        self.acceso = self.ahora - timedelta(days=100)
        self.u = get_user_model().objects.create_user('alumno90', password='BosqueLluvia!8724', last_login=self.acceso)
        self.p = Perfil.objects.create(usuario=self.u, terminos_version=VERSION_TERMINOS, terminos_aceptados_en=self.acceso)
        self.s = SesionSemanal.objects.create(usuario=self.u, numero=1, inicio=self.acceso, fin=None)
        self.m = Mensaje.objects.create(usuario=self.u, sesion=self.s, remitente='usuario', fecha=self.acceso + timedelta(days=3), contenido='Mensaje', analisis_estado='listo')

    def test_90_dias_desde_login_no_desde_mensaje(self):
        self.assertEqual(self.m.eliminar_despues_de, self.acceso + timedelta(days=90))
        self.assertEqual(limpiar_conversaciones(ahora=self.acceso + timedelta(days=89))['mensajes_vencidos'], 0)
        self.assertEqual(limpiar_conversaciones(ahora=self.acceso + timedelta(days=90))['mensajes_vencidos'], 1)

    def test_login_correcto_renueva_y_me_o_login_fallido_no(self):
        r = self.client.post('/api/auth/login/', json.dumps({'username': 'alumno90', 'password': 'BosqueLluvia!8724'}), content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.u.refresh_from_db(); self.m.refresh_from_db()
        plazo = self.u.last_login + timedelta(days=90)
        self.assertEqual(self.m.eliminar_despues_de, plazo)
        self.client.get('/api/auth/me/')
        self.client.post('/api/auth/login/', json.dumps({'username': 'alumno90', 'password': 'Incorrecta!'}), content_type='application/json')
        self.m.refresh_from_db()
        self.assertEqual(self.m.eliminar_despues_de, plazo)
        self.assertEqual(limpiar_conversaciones(ahora=self.ahora)['mensajes_vencidos'], 0)

    def test_no_reescribe_30_dias_ni_inscribe_historial_sin_consentimiento(self):
        Mensaje.objects.filter(pk=self.m.pk).update(retencion_version=VERSION_ANTERIOR, eliminar_despues_de=self.m.fecha + timedelta(days=30))
        antiguo_plazo = self.m.fecha + timedelta(days=30)
        self.client.post('/api/auth/login/', json.dumps({'username': 'alumno90', 'password': 'BosqueLluvia!8724'}), content_type='application/json')
        self.m.refresh_from_db()
        self.assertEqual(self.m.eliminar_despues_de, antiguo_plazo)
        self.p.terminos_version = ''; self.p.terminos_aceptados_en = None; self.p.save()
        nuevo = Mensaje.objects.create(usuario=self.u, sesion=self.s, remitente='usuario', fecha=self.ahora, contenido='Historial')
        self.assertIsNone(nuevo.eliminar_despues_de)

    def test_registro_solo_usuario_guarda_politica_y_no_nombre_personal(self):
        r = self.client.post('/api/auth/registro/', json.dumps({'username': 'ESTUDIANTE49', 'password': 'BosqueLluvia!8724', 'acepta_terminos': True, 'version_terminos': VERSION_TERMINOS}), content_type='application/json')
        self.assertEqual(r.status_code, 201)
        u = get_user_model().objects.get(username='estudiante49')
        self.assertEqual((u.first_name, u.email), ('estudiante49', ''))
        self.assertEqual(r.json()['usuario']['retencion_dias'], 90)
        self.assertEqual(r.json()['usuario']['retencion_desde'], 'ultimo_inicio_sesion')

    def test_limpieza_conserva_cuenta_al_vencer(self):
        self.assertEqual(limpiar_conversaciones(aplicar=True, ahora=self.ahora)['mensajes_eliminados'], 1)
        self.assertTrue(get_user_model().objects.filter(pk=self.u.pk).exists())
