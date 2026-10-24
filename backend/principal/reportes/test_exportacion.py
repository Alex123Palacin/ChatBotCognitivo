from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from openpyxl import load_workbook

from chat.models import Mensaje
from sesiones.services import iniciar_programa
from usuarios.models import Perfil
from .models import Evidencia, ReporteSemanal
from .exportacion import crear_excel


class ExportacionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin', is_staff=True)
        self.usuario = User.objects.create_user(username='estudiante', first_name='Alumna', email='privado@gmail.com')
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
            Evidencia.objects.create(mensaje=m, indicador=indicador, cita=cita, observacion='Organiza sus tareas.', senal=senal)
        return m

    def libro(self):
        respuesta = self.client.get(self.ruta)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('no-store', respuesta.headers['Cache-Control'])
        self.assertIn('attachment;', respuesta.headers['Content-Disposition'])
        return load_workbook(BytesIO(respuesta.content))

    def test_exporta_semanas_1_y_4_con_fuentes_y_procedencia(self):
        m1 = self.mensaje(1, 'No logro organizar las tareas.', cita='No logro organizar las tareas.', senal='dificultad')
        m4 = self.mensaje(4, 'Hago una lista de pendientes.', cita='Hago una lista de pendientes.')
        with patch('reportes.services.analizar_mensaje') as modelo:
            libro = self.libro()
            modelo.assert_not_called()
        self.assertEqual(libro.sheetnames, ['Ficha', 'Estudiantes', 'Comparación', 'Semanas', 'Evidencias', 'Conversaciones'])
        fila = next(f for f in libro['Comparación'].iter_rows(min_row=2, values_only=True) if f[4] == 'Planificación')
        self.assertEqual(fila[6], 'Dificultad expresada')
        self.assertEqual(fila[10], 'Recurso de afrontamiento')
        self.assertIn(m1.contenido, fila[8])
        self.assertIn(m4.contenido, fila[12])
        self.assertIn('ficticios', fila[2])
        self.assertEqual(libro['Evidencias'].max_row, 3)
        valores = str(list(libro['Conversaciones'].values))
        self.assertIn(str(m1.pk), valores)
        self.assertIn(str(m4.pk), valores)
        self.assertNotIn(self.usuario.email, str([list(h.values) for h in libro]))
        self.assertEqual(ReporteSemanal.objects.count(), 0)

    def test_faltantes_y_pendientes_no_son_cero_ni_se_reemplaza_semana4(self):
        self.mensaje(3, 'La tercera semana no reemplaza el cierre', cita='La tercera semana')
        self.mensaje(4, 'Todavía no analizado', estado='pendiente', cita='Todavía')
        libro = self.libro()
        fila = list(libro['Comparación'].values)[5]
        self.assertEqual(fila[5], 'Sin mensajes')
        self.assertEqual(fila[6], 'Sin evidencia suficiente')
        self.assertIn('pendiente', fila[9])
        self.assertEqual(fila[10], 'Sin evidencia suficiente')
        self.assertEqual(libro['Evidencias'].max_row, 2)
        self.semanas[4].delete()
        fila = list(self.libro()['Comparación'].values)[5]
        self.assertEqual(fila[9], 'Semana no registrada')

    def test_descarta_cita_inventada_y_fechas_fuera_del_periodo(self):
        self.mensaje(1, 'Solo este texto', cita='Texto ajeno')
        m = self.mensaje(4, 'Una lista', cita='Una lista')
        Mensaje.objects.filter(pk=m.pk).update(fecha=self.semanas[4].fin)
        libro = self.libro()
        self.assertEqual(libro['Evidencias'].max_row, 1)
        self.assertEqual(libro['Conversaciones'].max_row, 2)

    def test_contenido_es_texto_no_formula_y_fecha_es_excel_en_lima(self):
        m = self.mensaje(1, '=HYPERLINK("https://ejemplo.invalid", "clic")')
        libro = self.libro()
        self.assertEqual(libro['Conversaciones']['E2'].data_type, 's')
        self.assertEqual(libro['Conversaciones']['E2'].value, m.contenido)
        self.assertEqual(libro['Conversaciones']['C2'].value.hour, m.fecha.astimezone(__import__('zoneinfo').ZoneInfo('America/Lima')).hour)
        self.assertIsNone(libro['Conversaciones']['C2'].value.tzinfo)

    def test_ningun_otro_estudiante_se_incluye(self):
        respuesta = self.client.get(self.ruta)
        libro = load_workbook(BytesIO(respuesta.content))
        self.assertNotIn('Otro', str([list(h.values) for h in libro]))

    def test_anonimo_estudiante_y_seleccion_invalida_rechazados(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.ruta).status_code, 401)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(self.ruta).status_code, 403)
        self.client.force_login(self.admin)
        for valor in ('', 'abc', '1,,2', ',1', ','.join(['1'] * 101)):
            self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': valor}).status_code, 400)
        self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': self.admin.pk}).status_code, 404)
        self.assertEqual(self.client.get('/api/admin/evaluacion.xlsx', {'alumnos': 9999999}).status_code, 404)

    def test_semana_en_curso_se_marca_provisional_y_futuro_no_aparece(self):
        m = self.mensaje(4, 'Ordeno mis tareas', cita='Ordeno mis tareas')
        ahora = m.fecha + timedelta(hours=1)
        futuro = self.mensaje(4, 'Texto del futuro', cita='Texto del futuro')
        Mensaje.objects.filter(pk=futuro.pk).update(fecha=ahora + timedelta(hours=1))
        libro = load_workbook(BytesIO(crear_excel([self.usuario], ahora=ahora)))
        self.assertIn('provisional', list(libro['Comparación'].values)[5][9])
        self.assertNotIn('Texto del futuro', str(list(libro['Conversaciones'].values)))
