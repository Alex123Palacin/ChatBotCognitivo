import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase
from openpyxl import load_workbook
from io import BytesIO

from chat.models import Mensaje
from reportes.estudio import CLAVE_ESTUDIO, acotar_mensajes
from reportes.exportacion import crear_excel
from reportes.models import MuestraEstudio, Evidencia
from sesiones.models import SesionSemanal
from usuarios.models import Perfil


class CorreccionFechaTests(TransactionTestCase):
    def setUp(self):
        self.zona = ZoneInfo('America/Lima')
        self.fecha = datetime(2026, 9, 11, 14, 34, 12, 123456, tzinfo=self.zona)
        User = get_user_model()
        User.objects.bulk_create([User(username=f'estudiante{i}', password='!', date_joined=self.fecha)
                                  for i in range(136)])
        ids = list(User.objects.order_by('pk').values_list('pk', flat=True))
        self.muestra = MuestraEstudio.objects.create(clave=CLAVE_ESTUDIO, poblacion_ids=ids,
            inicio=self.fecha.replace(hour=13, minute=0), fin=self.fecha.replace(hour=18, minute=0))
        self.muestra.usuarios.set(ids[:110])
        self.usuario = User.objects.get(pk=ids[0])
        self.perfil = Perfil.objects.create(usuario=self.usuario, inicio_programa=self.fecha,
            ultima_actividad=self.fecha, origen_datos='demostracion')
        self.sesion = SesionSemanal.objects.create(usuario=self.usuario, numero=1, inicio=self.fecha, fin=None)
        self.mensaje = Mensaje.objects.create(usuario=self.usuario, sesion=self.sesion, fecha=self.fecha,
            contenido='Tengo demasiadas tareas.', remitente='usuario', analisis_estado='listo')
        Evidencia.objects.create(mensaje=self.mensaje, indicador='sobrecarga_academica',
            cita=self.mensaje.contenido, observacion='Dificultad relatada.', senal='dificultad')
        self.prueba = User.objects.create_user('sujetoprueba', date_joined=self.fecha)
        s = SesionSemanal.objects.create(usuario=self.prueba, numero=1, inicio=self.fecha, fin=None)
        Mensaje.objects.create(usuario=self.prueba, sesion=s, fecha=self.fecha, contenido='hola', remitente='usuario')

    def ejecutar(self, carpeta, aplicar=False):
        salida = StringIO()
        call_command('corregir_fecha_estudio', fecha_original='2026-09-11', fecha_correcta='2026-09-10',
                     directorio=carpeta, aplicar=aplicar, stdout=salida)
        return json.loads(salida.getvalue())

    def test_simulacion_sin_mutar_ni_crear_archivos(self):
        with TemporaryDirectory() as carpeta:
            resultado = self.ejecutar(carpeta)
            self.assertEqual(resultado['mensajes_por_cambiar'], 1)
            self.assertFalse(resultado['aplicado'])
            self.assertFalse(list(Path(carpeta).iterdir()))
            self.mensaje.refresh_from_db()
            self.assertEqual(self.mensaje.fecha, self.fecha)

    def test_aplica_con_respaldo_horas_identicas_y_prueba_intacta(self):
        protegidos = list(get_user_model().objects.exclude(pk__in=self.muestra.usuarios.all()).values())
        mensajes_prueba = list(self.prueba.mensajes_chat.values())
        with TemporaryDirectory() as carpeta:
            resultado = self.ejecutar(carpeta, True)
            self.assertTrue(resultado['aplicado'])
            with closing(sqlite3.connect(resultado['respaldo'])) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertIn('2026-09-11', db.execute('SELECT fecha FROM chat_mensaje WHERE usuario_id=?',
                                                    [self.usuario.pk]).fetchone()[0])
            registro = json.loads(Path(resultado['auditoria']).read_text(encoding='utf-8'))
            self.assertEqual(registro['estado'], 'aplicado')
            self.assertEqual(len(registro['usuarios']), 110)
            for c in registro['cambios']:
                antes, despues = datetime.fromisoformat(c['antes']), datetime.fromisoformat(c['despues'])
                self.assertEqual(antes.astimezone(self.zona).time(), despues.astimezone(self.zona).time())
                self.assertEqual(antes - despues, timedelta(days=1))
            self.mensaje.refresh_from_db(); self.perfil.refresh_from_db()
            self.assertEqual(self.mensaje.fecha, self.fecha - timedelta(days=1))
            self.assertEqual(self.mensaje.contenido, 'Tengo demasiadas tareas.')
            self.assertEqual(self.perfil.origen_datos, 'demostracion')
            self.assertEqual(Evidencia.objects.count(), 1)
            self.assertEqual(protegidos, list(get_user_model().objects.exclude(pk__in=self.muestra.usuarios.all()).values()))
            self.assertEqual(mensajes_prueba, list(self.prueba.mensajes_chat.values()))
            self.assertEqual(acotar_mensajes(Mensaje.objects.filter(usuario=self.usuario)).count(), 1)
            excel = load_workbook(BytesIO(crear_excel([self.usuario])))
            self.assertEqual(excel['Evidencias']['H2'].value.date().isoformat(), '2026-09-10')
            self.assertIn('2026-09-10', str(list(excel['Ficha'].values)))
            self.assertEqual(self.ejecutar(carpeta, True)['campos_por_cambiar'], 0)
            self.assertEqual(len(list(Path(carpeta).glob('*.sqlite3'))), 1)

    def test_no_cambia_actividad_posterior_ni_login_ni_terminos(self):
        posterior = self.fecha + timedelta(days=50)
        Perfil.objects.filter(pk=self.perfil.pk).update(ultima_actividad=posterior, terminos_aceptados_en=posterior)
        get_user_model().objects.filter(pk=self.usuario.pk).update(last_login=posterior)
        with TemporaryDirectory() as carpeta:
            self.ejecutar(carpeta, True)
        self.perfil.refresh_from_db(); self.usuario.refresh_from_db()
        self.assertEqual(self.perfil.ultima_actividad, posterior)
        self.assertEqual(self.perfil.terminos_aceptados_en, posterior)
        self.assertEqual(self.usuario.last_login, posterior)

    def test_muestra_incompleta_no_se_fuerza(self):
        self.muestra.usuarios.remove(self.usuario)
        with TemporaryDirectory() as carpeta, self.assertRaises(CommandError):
            self.ejecutar(carpeta, True)

    def test_ventana_distinta_no_se_fuerza(self):
        self.muestra.inicio -= timedelta(days=5); self.muestra.save()
        with TemporaryDirectory() as carpeta, self.assertRaises(CommandError):
            self.ejecutar(carpeta, True)
