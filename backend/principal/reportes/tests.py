from datetime import timedelta
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db.models import F
from django.test import TestCase, override_settings
from django.utils import timezone

from chat.models import Mensaje
from ml.ollama import ErrorModelo
from sesiones.services import iniciar_programa
from usuarios.models import Perfil
from .models import Evidencia, ReporteSemanal
from .services import analizar_pendiente, cerrar_y_actualizar_reportes, procesar_pendientes


class ReportesSemanalesTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username='ana@gmail.com', email='ana@gmail.com', password='SolBosque!7285')
        self.admin = get_user_model().objects.create_user(username='admin@gmail.com', email='admin@gmail.com', password='SolBosque!7285', is_staff=True)
        self.perfil = Perfil.objects.create(usuario=self.usuario)
        self.inicio = timezone.now() - timedelta(days=8)
        iniciar_programa(self.perfil, self.inicio)
        self.semana = self.usuario.semanas.get(numero=1)

    def mensaje(self, contenido='Tengo tantos trabajos que no me alcanza el tiempo'):
        return Mensaje.objects.create(usuario=self.usuario, sesion=self.semana, contenido=contenido, remitente='usuario', fecha=self.inicio + timedelta(days=1), clave_envio=uuid.uuid4())

    @patch('reportes.services.analizar_mensaje', return_value=[{'indicador': 'presion_tiempo', 'cita': 'no me alcanza el tiempo', 'observacion': 'Expresa dificultad para alcanzar los plazos.', 'senal': 'dificultad'}])
    def test_cierre_sin_nueva_visita_con_una_sola_conversacion(self, modelo):
        mensaje = self.mensaje()
        call_command('procesar_semanas', verbosity=0)
        reporte = ReporteSemanal.objects.get(sesion=self.semana)
        self.assertEqual(reporte.estado, 'listo')
        self.assertEqual(reporte.mensajes_estudiante, 1)
        self.assertEqual(reporte.total_evidencias, 1)
        self.assertIn('Información limitada', reporte.nota)
        self.assertEqual(Evidencia.objects.get().mensaje_id, mensaje.pk)
        self.client.force_login(self.admin)
        detalle = self.client.get(f'/api/admin/reportes/{reporte.pk}/').json()
        self.assertEqual(len(detalle['dimensiones']), 3)
        self.assertEqual(sum(len(d['indicadores']) for d in detalle['dimensiones']), 7)
        evidencia = detalle['dimensiones'][0]['indicadores'][1]['evidencias'][0]
        self.assertEqual(evidencia['mensaje_id'], str(mensaje.pk))
        self.assertNotIn('puntaje', detalle)

    def test_cuatro_semanas_sin_conversacion_reportan_falta_de_informacion(self):
        cerrar_y_actualizar_reportes(self.inicio + timedelta(days=28))
        self.assertEqual(ReporteSemanal.objects.count(), 4)
        for reporte in ReporteSemanal.objects.all():
            self.assertEqual(reporte.estado, 'listo')
            self.assertEqual(reporte.total_evidencias, 0)
            self.assertIn('No hubo mensajes', reporte.resumen)
        cerrar_y_actualizar_reportes(self.inicio + timedelta(days=29))
        self.assertEqual(ReporteSemanal.objects.count(), 4)

    @patch('reportes.services.analizar_mensaje', side_effect=ErrorModelo('Modelo apagado'))
    def test_fallo_analisis_deja_reporte_pendiente_y_reintenta(self, modelo):
        mensaje = self.mensaje()
        procesar_pendientes()
        reporte = ReporteSemanal.objects.get()
        self.assertEqual(reporte.estado, 'pendiente')
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_estado, 'error')
        mensaje.analisis_hasta = None
        mensaje.save()
        modelo.side_effect = None
        modelo.return_value = []
        procesar_pendientes()
        reporte.refresh_from_db()
        self.assertEqual(reporte.estado, 'listo')
        self.assertEqual(reporte.total_evidencias, 0)

    @patch('reportes.services.analizar_mensaje', return_value=[{'indicador': 'sintomas_fisicos', 'cita': 'me duele la cabeza', 'observacion': 'Dolor de cabeza.', 'senal': 'dificultad'}])
    def test_no_guarda_citas_que_el_estudiante_nunca_escribio(self, modelo):
        mensaje = self.mensaje()
        self.assertTrue(analizar_pendiente(mensaje))
        self.assertEqual(Evidencia.objects.count(), 0)
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_estado, 'listo')

    @patch('reportes.services.analizar_mensaje', return_value=[])
    def test_mensaje_se_analiza_una_vez_y_asistente_no_se_usa_como_evidencia(self, modelo):
        self.mensaje()
        Mensaje.objects.create(usuario=self.usuario, sesion=self.semana, remitente='asistente', contenido='¿Duermes mal?', fecha=self.inicio + timedelta(days=1), analisis_estado='listo')
        procesar_pendientes()
        procesar_pendientes()
        self.assertEqual(modelo.call_count, 1)
        self.assertEqual(ReporteSemanal.objects.get().mensajes_estudiante, 1)

    def test_reporte_no_pertenece_a_cuentas_estudiante(self):
        cerrar_y_actualizar_reportes()
        reporte = ReporteSemanal.objects.get()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(f'/api/admin/reportes/{reporte.pk}/').status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/api/admin/alumnos/').json()['alumnos'][0]['reportes_total'], 1)

    @patch('reportes.services.analizar_mensaje')
    def test_reporte_acumula_todos_los_dias_y_conserva_recursos_y_dificultades(self, modelo):
        textos = [
            (0, 'Tengo muchos trabajos', 'sobrecarga_academica', 'dificultad', 'Relata acumulación de trabajos.'),
            (3, 'Duermo mal esta semana', 'sintomas_fisicos', 'dificultad', 'Relata una dificultad de sueño.'),
            (6, 'Organizo mis tareas en un calendario', 'planificacion', 'recurso', 'Relata el uso de un calendario para organizar tareas.'),
        ]
        for dia, texto, indicador, senal, observacion in textos:
            Mensaje.objects.create(usuario=self.usuario, sesion=self.semana, contenido=texto, remitente='usuario', fecha=self.inicio + timedelta(days=dia, hours=1), clave_envio=uuid.uuid4())
        modelo.side_effect = [
            [{'indicador': indicador, 'cita': texto, 'observacion': observacion, 'senal': senal}]
            for _, texto, indicador, senal, observacion in textos
        ]
        call_command('procesar_semanas', verbosity=0)
        reporte = ReporteSemanal.objects.get(sesion=self.semana)
        self.assertEqual(modelo.call_count, 3)
        self.assertEqual(reporte.mensajes_estudiante, 3)
        self.assertEqual(reporte.total_evidencias, 3)
        self.assertIn('3 días de conversación', reporte.resumen)
        self.assertEqual(reporte.estado, 'listo')
        self.client.force_login(self.admin)
        detalle = self.client.get(f'/api/admin/reportes/{reporte.pk}/')
        self.assertIn('no-store', detalle.headers['Cache-Control'])
        dimensiones = detalle.json()['dimensiones']
        self.assertEqual(dimensiones[0]['indicadores'][0]['evidencias'][0]['senal'], 'dificultad')
        self.assertEqual(dimensiones[2]['indicadores'][0]['evidencias'][0]['senal'], 'recurso')
        self.assertEqual(ReporteSemanal.objects.count(), 1)

    @patch('reportes.services.analizar_mensaje', return_value=[])
    def test_chat_de_otro_estudiante_pospone_analisis_pero_no_cierre_semanal(self, modelo):
        mensaje = self.mensaje()
        otro = get_user_model().objects.create_user(username='otra@gmail.com', password='SolBosque!7285')
        perfil_otro = Perfil.objects.create(usuario=otro, respuesta_hasta=timezone.now() + timedelta(seconds=60))
        self.assertEqual(procesar_pendientes(), 0)
        modelo.assert_not_called()
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_estado, 'pendiente')
        self.assertEqual(mensaje.analisis_intentos, 0)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.estado, 'cerrada')
        self.assertEqual(ReporteSemanal.objects.get().estado, 'pendiente')
        perfil_otro.respuesta_hasta = None
        perfil_otro.save()
        self.assertEqual(procesar_pendientes(), 1)
        self.assertEqual(ReporteSemanal.objects.get().estado, 'listo')

    @patch('reportes.services.analizar_mensaje')
    def test_callback_detecta_chat_nuevo_y_conserva_analisis_para_reintentar(self, modelo):
        mensaje = self.mensaje()
        otro = get_user_model().objects.create_user(username='nueva@gmail.com', password='SolBosque!7285')
        perfil_otro = Perfil.objects.create(usuario=otro)

        def inferencia_interrumpida(contenido, historial, cancelar):
            self.assertFalse(cancelar())
            Perfil.objects.filter(pk=perfil_otro.pk).update(respuesta_hasta=timezone.now() + timedelta(seconds=60))
            self.assertTrue(cancelar())
            raise ErrorModelo('Análisis pospuesto para atender el chat.')

        modelo.side_effect = inferencia_interrumpida
        self.assertEqual(procesar_pendientes(), 0)
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_estado, 'pendiente')
        self.assertEqual(Evidencia.objects.count(), 0)
        self.assertEqual(ReporteSemanal.objects.get().estado, 'pendiente')
        Perfil.objects.filter(pk=perfil_otro.pk).update(respuesta_hasta=None)
        Mensaje.objects.filter(pk=mensaje.pk).update(analisis_hasta=None)
        modelo.side_effect = None
        modelo.return_value = []
        self.assertEqual(procesar_pendientes(), 1)
        self.assertEqual(ReporteSemanal.objects.get().estado, 'listo')

    @override_settings(OLLAMA_ANALYSIS_TIMEOUT=360)
    @patch('reportes.services.analizar_mensaje')
    def test_reserva_del_analisis_dura_mas_que_su_timeout_configurado(self, modelo):
        mensaje = self.mensaje()
        ahora = timezone.now()

        def inferencia(contenido, historial, cancelar):
            mensaje.refresh_from_db()
            self.assertEqual(mensaje.analisis_hasta, ahora + timedelta(seconds=420))
            self.assertEqual(mensaje.analisis_estado, 'procesando')
            self.assertFalse(cancelar())
            return []

        modelo.side_effect = inferencia
        with patch('reportes.services.timezone.now', return_value=ahora):
            self.assertTrue(analizar_pendiente(mensaje))
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_estado, 'listo')
        self.assertIsNone(mensaje.analisis_hasta)

    @patch('reportes.services.analizar_mensaje')
    def test_worker_vencido_no_guarda_evidencias_despues_de_nuevo_analisis(self, modelo):
        mensaje = self.mensaje()
        evidencia_nueva = {'indicador': 'presion_tiempo', 'cita': 'no me alcanza el tiempo', 'observacion': 'Relata falta de tiempo.', 'senal': 'dificultad'}
        evidencia_vieja = {'indicador': 'sobrecarga_academica', 'cita': 'tantos trabajos', 'observacion': 'Resultado anterior a la nueva reserva.', 'senal': 'dificultad'}

        def inferencia_vieja(contenido, historial, cancelar):
            mensaje.refresh_from_db()
            self.assertEqual(mensaje.analisis_intentos, 1)
            # Simula que la primera llamada quedó suspendida y su reserva venció.
            Mensaje.objects.filter(pk=mensaje.pk).update(analisis_hasta=timezone.now() - timedelta(seconds=1))
            with patch('reportes.services.analizar_mensaje', return_value=[evidencia_nueva]):
                self.assertTrue(analizar_pendiente(mensaje))
            # La respuesta vieja llega cuando el nuevo worker ya terminó.
            return [evidencia_vieja]

        modelo.side_effect = inferencia_vieja
        self.assertFalse(analizar_pendiente(mensaje))
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.analisis_intentos, 2)
        self.assertEqual(mensaje.analisis_estado, 'listo')
        self.assertIsNone(mensaje.analisis_hasta)
        self.assertEqual(list(Evidencia.objects.values_list('indicador', flat=True)), ['presion_tiempo'])

    @patch('reportes.services.analizar_mensaje')
    def test_fallo_o_cancelacion_de_worker_vencido_no_modifica_reserva_nueva(self, modelo):
        for chat_activo in [False, True]:
            with self.subTest(chat_activo=chat_activo):
                Perfil.objects.filter(pk=self.perfil.pk).update(respuesta_hasta=None)
                mensaje = self.mensaje()
                nueva_fecha = timezone.now() + timedelta(seconds=420)

                def inferencia_vieja(contenido, historial, cancelar):
                    mensaje.refresh_from_db()
                    self.assertEqual(mensaje.analisis_intentos, 1)
                    Mensaje.objects.filter(pk=mensaje.pk).update(analisis_hasta=timezone.now() - timedelta(seconds=1))
                    # Otro worker adquirió la reserva y todavía está esperando a Ollama.
                    Mensaje.objects.filter(pk=mensaje.pk, analisis_hasta__lte=timezone.now()).update(analisis_intentos=F('analisis_intentos') + 1, analisis_estado='procesando', analisis_hasta=nueva_fecha)
                    if chat_activo:
                        Perfil.objects.filter(pk=self.perfil.pk).update(respuesta_hasta=timezone.now() + timedelta(seconds=60))
                    raise ErrorModelo('La llamada anterior falló o se canceló.')

                modelo.side_effect = inferencia_vieja
                self.assertFalse(analizar_pendiente(mensaje))
                mensaje.refresh_from_db()
                self.assertEqual(mensaje.analisis_estado, 'procesando')
                self.assertEqual(mensaje.analisis_intentos, 2)
                self.assertEqual(mensaje.analisis_hasta, nueva_fecha)
                self.assertEqual(mensaje.evidencias.count(), 0)
