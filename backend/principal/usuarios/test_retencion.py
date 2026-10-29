from datetime import timedelta
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from chat.models import Mensaje
from reportes.models import Evidencia, ReporteSemanal
from sesiones.models import SesionSemanal
from usuarios.models import Perfil
from usuarios.retencion import DIAS_RETENCION, VERSION_TERMINOS, limpiar_conversaciones


class TerminosRegistroTests(TestCase):
    def registrar(self, **extra):
        datos = {'username': 'nueva49', 'nombre': 'Ana', 'password': 'BosqueLluvia!8724', **extra}
        return self.client.post('/api/auth/registro/', json.dumps(datos), content_type='application/json')

    def test_requiere_aceptacion_booleana_y_version_presentada_vigente(self):
        for valor in (None, False, 'true', 1, 'si'):
            with self.subTest(valor=valor):
                self.assertEqual(self.registrar(acepta_terminos=valor, version_terminos=VERSION_TERMINOS).status_code, 400)
        self.assertEqual(self.registrar(acepta_terminos=True).status_code, 400)
        self.assertEqual(self.registrar(acepta_terminos=True, version_terminos='otra-version').status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

    def test_registra_aceptacion_con_hora_del_servidor_y_conserva_cuenta(self):
        antes = timezone.now()
        respuesta = self.registrar(acepta_terminos=True, version_terminos=VERSION_TERMINOS)
        self.assertEqual(respuesta.status_code, 201)
        perfil = Perfil.objects.get()
        self.assertEqual(perfil.terminos_version, VERSION_TERMINOS)
        self.assertGreaterEqual(perfil.terminos_aceptados_en, antes)
        self.assertLessEqual(perfil.terminos_aceptados_en, timezone.now())
        self.assertTrue(perfil.usuario.check_password('BosqueLluvia!8724'))
        self.assertTrue(respuesta.json()['usuario']['terminos_aceptados'])
        self.assertEqual(respuesta.json()['usuario']['retencion_dias'], 30)
        self.assertEqual(respuesta.json()['usuario']['version_terminos'], VERSION_TERMINOS)

    def test_sesion_heredada_no_anuncia_plazo_no_aceptado(self):
        usuario = get_user_model().objects.create_user(username='heredada@gmail.com', password='BosqueLluvia!8724')
        Perfil.objects.create(usuario=usuario)
        self.client.force_login(usuario)
        datos = self.client.get('/api/auth/me/').json()['usuario']
        self.assertFalse(datos['terminos_aceptados'])
        self.assertIsNone(datos['retencion_dias'])
        self.assertIsNone(datos['version_terminos'])

    def test_publica_politica_con_alcance_explicito_sin_datos_personales(self):
        respuesta = self.client.get('/api/auth/terminos/')
        self.assertEqual(respuesta.status_code, 200)
        politica = respuesta.json()
        self.assertEqual(politica['version'], VERSION_TERMINOS)
        self.assertEqual(politica['dias_retencion'], 30)
        self.assertIn('cada mensaje', politica['texto'])
        self.assertEqual(politica['copias_seguridad'], 'gestion_separada')
        self.assertIn('no-store', respuesta.headers['Cache-Control'])


class RetencionMensajesTests(TestCase):
    def setUp(self):
        self.ahora = timezone.now()
        self.usuario = get_user_model().objects.create_user(username='nueva@gmail.com', password='BosqueLluvia!8724')
        self.perfil = Perfil.objects.create(
            usuario=self.usuario,
            terminos_version=VERSION_TERMINOS,
            terminos_aceptados_en=self.ahora - timedelta(days=40),
        )
        self.sesion = SesionSemanal.objects.create(
            usuario=self.usuario, numero=1, inicio=self.ahora - timedelta(days=40),
            fin=self.ahora + timedelta(days=1), estado='activa',
        )

    def mensaje(self, dias=0, **extra):
        return Mensaje.objects.create(
            usuario=self.usuario, sesion=self.sesion, contenido='Texto sintético de prueba',
            remitente='usuario', fecha=self.ahora - timedelta(days=dias), **extra,
        )

    def test_plazo_desde_cada_mensaje_y_no_desde_el_registro(self):
        mensaje = self.mensaje(dias=2)
        self.assertEqual(mensaje.eliminar_despues_de, mensaje.fecha + timedelta(days=DIAS_RETENCION))
        self.assertEqual(mensaje.retencion_version, VERSION_TERMINOS)
        posterior = self.mensaje()
        self.assertGreater(posterior.eliminar_despues_de, mensaje.eliminar_despues_de)

    def test_no_asigna_plazo_a_datos_anteriores_o_usuarios_sin_aceptacion(self):
        antiguo = self.mensaje(dias=50)
        self.assertIsNone(antiguo.eliminar_despues_de)
        self.perfil.terminos_aceptados_en = None
        self.perfil.terminos_version = ''
        self.perfil.save()
        heredado = self.mensaje(dias=32)
        self.assertIsNone(heredado.eliminar_despues_de)
        heredado.contenido = 'Edición no inscribe datos antiguos'
        heredado.save()
        self.assertIsNone(heredado.eliminar_despues_de)
        resultado = limpiar_conversaciones(aplicar=True, ahora=self.ahora)
        self.assertEqual(resultado['mensajes_eliminados'], 0)
        self.assertEqual(Mensaje.objects.count(), 2)

    def test_bulk_create_asigna_plazo_solo_si_corresponde(self):
        mensajes = [Mensaje(usuario=self.usuario, sesion=self.sesion, remitente='usuario', contenido='Prueba', fecha=self.ahora)]
        Mensaje.objects.bulk_create(mensajes)
        self.assertEqual(Mensaje.objects.get().eliminar_despues_de, self.ahora + timedelta(days=30))

    def test_version_nueva_de_perfil_no_cancela_el_plazo_ya_aceptado_de_mensajes(self):
        mensaje = self.mensaje(dias=31)
        self.perfil.terminos_version = 'terminos-futuros'
        self.perfil.terminos_aceptados_en = self.ahora
        self.perfil.save()
        self.assertEqual(limpiar_conversaciones(aplicar=True, ahora=self.ahora)['mensajes_eliminados'], 1)
        self.assertFalse(Mensaje.objects.filter(pk=mensaje.pk).exists())

    def test_borra_limite_exacto_evidencias_y_resumen_sin_borrar_recientes_cuenta_o_sesion(self):
        vencido = self.mensaje(dias=30)
        reciente = self.mensaje(dias=29)
        Evidencia.objects.create(mensaje=vencido, indicador='planificacion', cita='Cita antigua', observacion='Observación antigua', senal='presente')
        Evidencia.objects.create(mensaje=reciente, indicador='planificacion', cita='Cita reciente', observacion='Observación reciente', senal='presente')
        ReporteSemanal.objects.create(sesion=self.sesion, resumen='Resumen que contenía la cita antigua')
        previo = limpiar_conversaciones(ahora=self.ahora)
        self.assertFalse(previo['aplicado'])
        self.assertEqual(previo['mensajes_vencidos'], 1)
        self.assertTrue(Mensaje.objects.filter(pk=vencido.pk).exists())
        resultado = limpiar_conversaciones(aplicar=True, ahora=self.ahora)
        self.assertEqual(resultado['mensajes_eliminados'], 1)
        self.assertFalse(Mensaje.objects.filter(pk=vencido.pk).exists())
        self.assertTrue(Mensaje.objects.filter(pk=reciente.pk).exists())
        self.assertEqual(Evidencia.objects.count(), 1)
        self.assertFalse(ReporteSemanal.objects.exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.usuario.pk).exists())
        self.assertTrue(SesionSemanal.objects.filter(pk=self.sesion.pk).exists())

    def test_no_borra_conversacion_en_respuesta_activa_ni_cascada_de_respuesta_heredada(self):
        padre = self.mensaje(dias=31)
        respuesta = Mensaje.objects.create(usuario=self.usuario, sesion=self.sesion, contenido='Respuesta', remitente='asistente', fecha=padre.fecha, respuesta_a=padre)
        self.perfil.respuesta_hasta = self.ahora + timedelta(minutes=2)
        self.perfil.save()
        self.assertEqual(limpiar_conversaciones(aplicar=True, ahora=self.ahora)['mensajes_eliminados'], 0)
        self.perfil.respuesta_hasta = None
        self.perfil.save()
        Mensaje.objects.filter(pk=respuesta.pk).update(eliminar_despues_de=None)
        self.assertEqual(limpiar_conversaciones(aplicar=True, ahora=self.ahora)['mensajes_eliminados'], 0)
        self.assertEqual(Mensaje.objects.count(), 2)

    def test_comando_simula_por_defecto_y_solo_aplica_con_flag(self):
        vencido = self.mensaje(dias=31)
        salida = StringIO()
        call_command('limpiar_conversaciones', stdout=salida)
        self.assertFalse(json.loads(salida.getvalue())['aplicado'])
        self.assertTrue(Mensaje.objects.filter(pk=vencido.pk).exists())
        call_command('limpiar_conversaciones', aplicar=True, stdout=StringIO())
        self.assertFalse(Mensaje.objects.filter(pk=vencido.pk).exists())

    @patch('sesiones.management.commands.procesar_semanas.procesar_pendientes', return_value=0)
    def test_worker_ejecuta_limpieza_automatica_sin_visitas_al_chat(self, analizar):
        vencido = self.mensaje(dias=31)
        call_command('procesar_semanas', stdout=StringIO())
        self.assertFalse(Mensaje.objects.filter(pk=vencido.pk).exists())
