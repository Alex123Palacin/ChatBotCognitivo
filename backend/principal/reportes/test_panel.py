from datetime import timedelta
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from chat.models import Mensaje
from ml.analisis import INDICADORES
from sesiones.services import iniciar_programa
from usuarios.models import Perfil
from .models import Evidencia, ReporteSemanal


class PanelActualTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alumno = User.objects.create_user(username='alumna@gmail.com', email='alumna@gmail.com', first_name='Ana', password='SolBosque!7285')
        self.admin = User.objects.create_user(username='administrador', password='SolBosque!7285', is_staff=True)
        self.perfil = Perfil.objects.create(usuario=self.alumno)
        self.ahora = timezone.now()
        self.client.force_login(self.admin)
        self.ruta = f'/api/admin/alumnos/{self.alumno.pk}/'

    def iniciar(self, dias=1):
        iniciar_programa(self.perfil, self.ahora - timedelta(days=dias))
        return self.alumno.semanas.get(numero=min(4, dias // 7 + 1))

    def mensaje(self, semana, contenido='Hola', analizado=True, fecha=None, indicadores=None):
        mensaje = Mensaje.objects.create(usuario=self.alumno, sesion=semana, contenido=contenido, remitente='usuario', fecha=fecha or self.ahora - timedelta(hours=1), clave_envio=uuid.uuid4(), analisis_estado='listo' if analizado else 'pendiente')
        for indicador in indicadores or []:
            Evidencia.objects.create(mensaje=mensaje, indicador=indicador, cita=contenido, observacion=f'Relato del estudiante: {contenido}', senal='recurso' if INDICADORES[indicador]['dimension'] == 'afrontamiento' else 'dificultad')
        return mensaje

    def test_cuenta_sin_chat_no_tiene_reporte_actual_y_metricas_son_cero(self):
        datos = self.client.get(self.ruta).json()
        self.assertIsNone(datos['reporte_actual'])
        self.assertIsNone(datos['alumno']['inicio_programa'])
        self.assertIsNone(datos['alumno']['primer_mensaje'])
        self.assertEqual(datos['alumno']['dias_conversacion'], 0)
        self.assertEqual(datos['alumno']['mensajes_estudiante'], 0)

    def test_semana_vacia_no_afirma_que_puede_describir_indicadores(self):
        self.iniciar(dias=8)
        datos = self.client.get(self.ruta).json()
        actual = datos['reporte_actual']
        self.assertEqual(actual['numero'], 2)
        self.assertEqual(actual['estado'], 'en_curso')
        self.assertEqual(actual['cobertura']['estado'], 'sin_mensajes')
        self.assertFalse(actual['cobertura']['puede_describir_indicadores'])
        self.assertEqual(len(actual['cobertura']['indicadores_pendientes']), 7)

    def test_un_solo_mensaje_con_cita_permite_describir_solo_su_indicador(self):
        semana = self.iniciar()
        self.mensaje(semana, 'Me falta tiempo para entregar las tareas', indicadores=['presion_tiempo'])
        actual = self.client.get(self.ruta).json()['reporte_actual']
        self.assertEqual(actual['mensajes_estudiante'], 1)
        self.assertEqual(actual['total_evidencias'], 1)
        self.assertEqual(actual['cobertura']['estado'], 'parcial')
        self.assertTrue(actual['cobertura']['puede_describir_indicadores'])
        self.assertEqual(actual['cobertura']['indicadores_con_evidencia'], 1)
        self.assertEqual(actual['cobertura']['dimensiones_con_evidencia'], 1)
        self.assertEqual(len(actual['cobertura']['indicadores_pendientes']), 6)
        self.assertEqual(actual['dimensiones'][0]['indicadores'][1]['evidencias'][0]['cita'], 'Me falta tiempo para entregar las tareas')

    def test_mensaje_analizado_sin_evidencia_no_se_confunde_con_estres_bajo(self):
        semana = self.iniciar()
        self.mensaje(semana)
        cobertura = self.client.get(self.ruta).json()['reporte_actual']['cobertura']
        self.assertEqual(cobertura['estado'], 'sin_evidencia')
        self.assertFalse(cobertura['puede_describir_indicadores'])
        self.assertEqual(cobertura['mensajes_analizados'], 1)
        self.assertIn('no demuestra ausencia de estrés', cobertura['mensaje'])

    def test_cobertura_completa_de_siete_no_es_diagnostico_y_pendientes_tienen_prioridad(self):
        semana = self.iniciar()
        # Fixture de citas ya validadas; un único relato puede abarcar los siete temas.
        contenido = 'Tengo muchas tareas, me falta tiempo, duermo mal por estudiar y me preocupan los exámenes. Organizo horarios, recuerdo mi meta y pido ayuda a mi docente.'
        self.mensaje(semana, contenido, indicadores=list(INDICADORES))
        cobertura = self.client.get(self.ruta).json()['reporte_actual']['cobertura']
        self.assertEqual(cobertura['estado'], 'completa')
        self.assertEqual(cobertura['indicadores_con_evidencia'], 7)
        self.assertEqual(cobertura['dimensiones_con_evidencia'], 3)
        self.assertEqual(cobertura['indicadores_pendientes'], [])
        self.assertIn('no es una puntuación SISCO ni un diagnóstico', cobertura['mensaje'])
        self.mensaje(semana, 'Quiero contar algo más', analizado=False)
        cobertura = self.client.get(self.ruta).json()['reporte_actual']['cobertura']
        self.assertEqual(cobertura['estado'], 'analisis_pendiente')
        self.assertEqual(cobertura['analisis_pendientes'], 1)
        self.assertTrue(cobertura['puede_describir_indicadores'])

    def test_metricas_acumuladas_cuentan_dias_y_mensajes_del_estudiante(self):
        semana2 = self.iniciar(dias=8)
        semana1 = self.alumno.semanas.get(numero=1)
        primer = self.mensaje(semana1, 'La semana pasada tuve tareas', fecha=self.ahora - timedelta(days=7))
        segundo = self.mensaje(semana2, 'Hoy quiero conversar', fecha=self.ahora - timedelta(hours=1))
        tercero = self.mensaje(semana2, 'También hay otro asunto', analizado=False, fecha=segundo.fecha + timedelta(seconds=30))
        Mensaje.objects.create(usuario=self.alumno, sesion=semana2, remitente='asistente', contenido='Te escucho.', fecha=self.ahora, analisis_estado='listo')
        datos = self.client.get(self.ruta).json()
        alumno = datos['alumno']
        self.assertEqual(alumno['primer_mensaje'], primer.fecha.isoformat())
        self.assertEqual(alumno['ultimo_mensaje'], tercero.fecha.isoformat())
        self.assertEqual(alumno['dias_conversacion'], 2)
        self.assertEqual(alumno['mensajes_estudiante'], 3)
        self.assertEqual(alumno['mensajes_analizados'], 2)
        self.assertEqual(alumno['analisis_pendientes'], 1)
        self.assertEqual(datos['reporte_actual']['mensajes_estudiante'], 2)
        self.assertEqual(datos['reporte_actual']['cobertura']['mensajes_analizados'], 1)

    @patch('reportes.services.analizar_mensaje')
    def test_get_actual_no_crea_reportes_ni_cambia_semanas_ni_dispara_inferencia(self, modelo):
        self.iniciar(dias=8)
        estados = list(self.alumno.semanas.values_list('estado', flat=True))
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(self.ruta)
            listado = self.client.get('/api/admin/alumnos/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(listado.status_code, 200)
        escrituras = [q['sql'] for q in consultas.captured_queries if q['sql'].lstrip().upper().startswith(('INSERT ', 'UPDATE ', 'DELETE ', 'REPLACE '))]
        self.assertEqual(escrituras, [])
        self.assertEqual(list(self.alumno.semanas.values_list('estado', flat=True)), estados)
        self.assertEqual(ReporteSemanal.objects.count(), 0)
        self.assertEqual(respuesta.json()['sesiones'][0]['estado'], 'cerrada')
        modelo.assert_not_called()
        self.assertIn('no-store', respuesta.headers['Cache-Control'])

    def test_programa_terminado_muestra_snapshot_final_de_semana_cuatro(self):
        semana = self.iniciar(dias=29)
        self.mensaje(semana, 'Pido ayuda a mi docente', fecha=semana.inicio + timedelta(hours=1), indicadores=['busqueda_soporte'])
        actual = self.client.get(self.ruta).json()['reporte_actual']
        self.assertEqual(actual['numero'], 4)
        self.assertEqual(actual['estado'], 'finalizado')
        self.assertEqual(actual['cobertura']['estado'], 'parcial')
        self.assertEqual(ReporteSemanal.objects.count(), 0)

    def test_estudiante_y_anonimo_no_acceden_a_snapshot_administrativo(self):
        self.iniciar()
        self.client.force_login(self.alumno)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.ruta).status_code, 401)
