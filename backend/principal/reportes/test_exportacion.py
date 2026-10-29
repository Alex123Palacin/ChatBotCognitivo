from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook

from chat.models import Mensaje
from sesiones.services import iniciar_programa, iniciar_conversacion
from usuarios.models import Perfil
from .models import Evidencia, ReporteSemanal
from .exportacion import crear_excel


class ExportacionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', is_staff=True)
        self.usuario = User.objects.create_user(username='estudiante', first_name='Nombre privado', email='privado@gmail.com')
        self.otro = User.objects.create_user(username='otro', first_name='Otro')
        self.perfil = Perfil.objects.create(usuario=self.usuario, origen_datos='demostracion')
        self.ahora = timezone.now()
        iniciar_programa(self.perfil, self.ahora - timedelta(days=30))
        self.semanas = {s.numero: s for s in self.usuario.semanas.all()}
        self.ruta = f'/api/admin/evaluacion.xlsx?alumnos={self.usuario.pk}'
        self.client.force_login(self.admin)

    def mensaje(self, numero, texto, estado='listo', cita=None, indicador='planificacion', senal='recurso'):
        sesion = self.semanas[numero]
        m = Mensaje.objects.create(usuario=self.usuario, sesion=sesion, contenido=texto, remitente='usuario', fecha=sesion.inicio + timedelta(hours=1), analisis_estado=estado)
        if cita:
            Evidencia.objects.create(mensaje=m, indicador=indicador, cita=cita, observacion='Relato del estudiante.', senal=senal)
        return m

    def libro(self):
        respuesta = self.client.get(self.ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('no-store', respuesta.headers['Cache-Control'])
        self.assertIn('attachment;', respuesta.headers['Content-Disposition'])
        return load_workbook(BytesIO(respuesta.content))

    def valor(self, libro, indicador):
        filas = list(libro['Resultados'].values)
        return filas[1][filas[0].index(f'Actividad · {indicador}')]

    def test_exporta_id_y_siete_valores_de_actividad_sin_datos_personales(self):
        self.mensaje(1, 'Esta semana casi siempre organizo mis tareas.', cita='casi siempre organizo mis tareas')
        self.mensaje(4, 'Esta semana casi siempre organizo mis tareas.', cita='casi siempre organizo mis tareas')
        with patch('reportes.services.analizar_mensaje') as modelo:
            libro = self.libro()
            modelo.assert_not_called()
        self.assertEqual(libro.sheetnames, ['Resultados', 'Ficha'])
        self.assertEqual(libro['Resultados'].max_column, 9)
        self.assertEqual(libro['Resultados']['A2'].value, f'Estudiante {self.usuario.pk}')
        self.assertEqual(libro['Resultados']['B2'].value, self.usuario.username)
        self.assertEqual(self.valor(libro, 'Planificación'), 4)
        contenido = str([list(h.values) for h in libro])
        self.assertNotIn(self.usuario.first_name, contenido)
        self.assertNotIn(self.usuario.email, contenido)
        self.assertNotIn('Inicial · S1', contenido)
        self.assertNotIn('Final · S4', contenido)
        self.assertEqual(ReporteSemanal.objects.count(), 0)

    def test_procedencia_solo_en_ficha_y_solo_si_hay_registros_generados(self):
        libro = self.libro()
        self.assertNotIn('Demostración', str(list(libro['Resultados'].values)))
        self.assertIn('Demostración', str(list(libro['Ficha'].values)))
        self.perfil.origen_datos = 'conversacion'
        self.perfil.save(update_fields=['origen_datos'])
        libro = self.libro()
        contenido = str([list(h.values) for h in libro]).casefold()
        self.assertNotIn('demostración', contenido)
        self.assertNotIn('fictici', contenido)

    def test_periodo_abierto_exporta_evidencia_sin_exigir_semanas_o_cierre(self):
        sesion = iniciar_conversacion(self.perfil, self.ahora - timedelta(hours=1))
        self.assertIsNone(sesion.fin)
        texto = 'Esta semana casi siempre organizo mis tareas.'
        mensaje = Mensaje.objects.create(
            usuario=self.usuario, sesion=sesion, contenido=texto,
            remitente='usuario', fecha=self.ahora - timedelta(minutes=5), analisis_estado='listo',
        )
        Evidencia.objects.create(mensaje=mensaje, indicador='planificacion', cita=texto,
                                observacion='Frecuencia explícita del estudiante.', senal='recurso')
        libro = self.libro()
        self.assertEqual(libro['Resultados'].max_column, 9)
        self.assertEqual(self.valor(libro, 'Planificación'), 4)

    def test_pendientes_no_se_califican_y_se_incluye_toda_la_actividad_real(self):
        self.mensaje(3, 'Esta semana siempre organizo mis tareas.', cita='siempre organizo mis tareas')
        self.mensaje(4, 'Esta semana siempre organizo mis tareas.', estado='pendiente', cita='siempre organizo mis tareas')
        libro = self.libro()
        self.assertEqual(self.valor(libro, 'Planificación'), 'Sin información')
        self.semanas[4].delete()
        self.assertEqual(self.valor(self.libro(), 'Planificación'), 5)

    def test_descarta_citas_inventadas_y_fechas_fuera_de_sesion(self):
        self.mensaje(1, 'Solo este texto', cita='Esta semana siempre organizo mis tareas.')
        m = self.mensaje(4, 'Esta semana siempre organizo mis tareas.', cita='siempre organizo mis tareas')
        Mensaje.objects.filter(pk=m.pk).update(fecha=self.semanas[4].fin)
        libro = self.libro()
        self.assertEqual(self.valor(libro, 'Planificación'), 'Sin información')

    def test_conflictos_no_se_promedian(self):
        for frecuencia in ('rara vez', 'siempre'):
            texto = f'Esta semana {frecuencia} organizo mis tareas.'
            self.mensaje(1, texto, cita=texto)
        self.assertEqual(self.valor(self.libro(), 'Planificación'), 'Sin información')

    def test_no_exporta_formulas_desde_mensajes_y_fecha_es_lima(self):
        self.mensaje(1, '=HYPERLINK("https://ejemplo.invalid", "clic")')
        libro = self.libro()
        for hoja in libro:
            for fila in hoja:
                self.assertTrue(all(c.data_type != 'f' for c in fila))
        fecha = dict(libro['Ficha'].values)['Exportado']
        self.assertEqual(fecha.hour, timezone.localtime().hour)
        self.assertIsNone(fecha.tzinfo)

    def test_ningun_otro_estudiante_se_incluye(self):
        libro = self.libro()
        self.assertEqual(libro['Resultados'].max_row, 2)
        self.assertNotIn(f'Estudiante {self.otro.pk}', str(list(libro['Resultados'].values)))

    def test_anonimo_estudiante_y_seleccion_invalida_rechazados(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.ruta).status_code, 401)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)
        self.client.force_login(self.admin)
        for valor in ('', 'abc', '1,,2', ',1', ','.join(['1'] * 111)):
            self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': valor}).status_code, 400)
        self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': self.admin.pk}).status_code, 404)
        self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': 9999999}).status_code, 404)

    def test_actividad_en_curso_no_inventa_una_medicion_final(self):
        m = self.mensaje(4, 'Esta semana siempre organizo mis tareas.', cita='siempre organizo mis tareas')
        ahora = m.fecha + timedelta(hours=1)
        libro = load_workbook(BytesIO(crear_excel([self.usuario], ahora=ahora)))
        self.assertEqual(self.valor(libro, 'Planificación'), 5)
        self.assertFalse(any('Inicial' in str(celda.value) or 'Final ·' in str(celda.value) for celda in libro['Resultados'][1]))

    def test_respuesta_corta_usa_solo_pregunta_inmediata_de_la_misma_sesion(self):
        padre = self.mensaje(1, 'Me falta tiempo para las tareas.')
        pregunta = Mensaje.objects.create(usuario=self.usuario, sesion=self.semanas[1], remitente='asistente', contenido='¿Con qué frecuencia te falta tiempo para las tareas esta semana?', fecha=padre.fecha + timedelta(seconds=20), respuesta_a=padre, analisis_estado='listo')
        respuesta = self.mensaje(1, 'Casi siempre.')
        Mensaje.objects.filter(pk=respuesta.pk).update(fecha=pregunta.fecha + timedelta(seconds=20))
        self.assertEqual(self.valor(self.libro(), 'Presión del tiempo'), 4)
        Mensaje.objects.filter(pk=respuesta.pk).update(fecha=pregunta.fecha + timedelta(hours=3))
        self.assertEqual(self.valor(self.libro(), 'Presión del tiempo'), 'Sin información')
