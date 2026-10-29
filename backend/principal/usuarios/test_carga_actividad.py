from copy import deepcopy
from contextlib import closing
from datetime import datetime, timedelta
import hashlib
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import FieldDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from chat.models import Mensaje
from reportes.models import Evidencia, ReporteSemanal
from sesiones.models import SesionSemanal
from usuarios.carga_actividad import ERROR_VERSION, MIGRACIONES_REQUERIDAS, ErrorCarga, _crear_respaldo, comprobar_entorno, importar_paquete, leer_paquete, validar_paquete
from usuarios.models import Perfil
from usuarios.retencion import limpiar_conversaciones


def paquete_prueba(password_hash, cuentas=2):
    inicio = datetime.fromisoformat('2026-09-11T13:00:00-05:00')
    personas = []
    for numero in range(1, cuentas + 1):
        clave = f'a{numero:03}'
        mensajes = []
        for turno in range(20):
            id_usuario = uuid.uuid5(uuid.NAMESPACE_URL, f'actividad/prueba/{clave}/{turno}/usuario')
            id_asistente = uuid.uuid5(uuid.NAMESPACE_URL, f'actividad/prueba/{clave}/{turno}/asistente')
            texto = 'Tengo demasiadas tareas del colegio y me cuesta terminar todo.' if turno == 2 else f'Voy revisando el ejercicio {turno + 1}, ya te cuento.'
            evidencias = [{'indicador': 'sobrecarga_academica', 'senal': 'dificultad', 'cita': texto, 'observacion': f'El estudiante relata una dificultad: «{texto}».'}] if turno == 2 else []
            mensajes.append({'id': str(id_usuario), 'remitente': 'usuario', 'contenido': texto, 'fecha': (inicio + timedelta(minutes=turno * 14 + numero)).isoformat(), 'respuesta_a': None, 'evidencias': evidencias})
            mensajes.append({'id': str(id_asistente), 'remitente': 'asistente', 'contenido': f'Podemos revisar ese paso {turno + 1} juntos.', 'fecha': (inicio + timedelta(minutes=turno * 14 + numero, seconds=25)).isoformat(), 'respuesta_a': str(id_usuario), 'evidencias': []})
        personas.append({'clave': clave, 'nombre': f'Alumna Nombre Apellido {numero}', 'email': f'alumna.apellido.{numero}@example.com', 'password_hash': password_hash, 'fecha_alta': (inicio - timedelta(minutes=5)).isoformat(), 'inicio': mensajes[0]['fecha'], 'mensajes': mensajes})
    return {'schema': 'chatcognitivo.actividad.v1', 'lote': 'actividad-prueba-20260911', 'fecha': '2026-09-11', 'zona_horaria': 'America/Lima', 'ventana_inicio': inicio.isoformat(), 'ventana_fin': (inicio + timedelta(hours=5)).isoformat(), 'origen': 'demostracion', 'analisis_metodo': 'anotacion_estructurada_v1', 'cuentas': personas}


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
class CargaActividadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'CaminosDeLima!58327'
        cls.password_hash = make_password(cls.password)

    def setUp(self):
        self.datos = paquete_prueba(self.password_hash)
        self.respaldo = patch('usuarios.carga_actividad._crear_respaldo', return_value='/privado/respaldo.sqlite3')
        self.respaldo_mock = self.respaldo.start()
        self.addCleanup(self.respaldo.stop)

    def importar(self, datos=None, aplicar=True):
        return importar_paquete(validar_paquete(datos or self.datos), aplicar=aplicar, validar_entorno=False)

    def test_validacion_no_crea_usuarios_mensajes_ni_respaldo(self):
        resultado = self.importar(aplicar=False)
        self.assertEqual(resultado['cuentas_nuevas'], 2)
        self.assertEqual(resultado['mensajes'], 80)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Mensaje.objects.exists())
        self.respaldo_mock.assert_not_called()

    def test_importa_relaciones_reportes_sin_falsificar_aceptacion(self):
        resultado = self.importar()
        self.assertEqual(resultado['cuentas_creadas'], 2)
        self.assertEqual(Mensaje.objects.count(), 80)
        self.assertEqual(Mensaje.objects.filter(remitente='asistente', respuesta_a__remitente='usuario').count(), 40)
        self.assertEqual(Evidencia.objects.count(), 2)
        self.assertEqual(ReporteSemanal.objects.filter(estado='listo', mensajes_estudiante=20).count(), 2)
        self.assertEqual(SesionSemanal.objects.filter(fin=None, estado='activa').count(), 2)
        for perfil in Perfil.objects.select_related('usuario'):
            self.assertEqual(perfil.origen_datos, 'demostracion')
            self.assertEqual(perfil.terminos_version, '')
            self.assertIsNone(perfil.terminos_aceptados_en)
            self.assertTrue(perfil.usuario.check_password(self.password))
            self.assertFalse(perfil.usuario.is_staff)
            self.assertFalse(perfil.usuario.is_superuser)
        self.assertFalse(Mensaje.objects.filter(eliminar_despues_de__isnull=False).exists())
        self.assertIn('esta carga no ejecutó inferencia', ReporteSemanal.objects.first().nota)
        self.assertEqual(limpiar_conversaciones(aplicar=False)['mensajes_vencidos'], 0)

    def test_repetir_tras_login_y_nuevo_chat_no_duplica_ni_cambia_actividad(self):
        self.importar()
        usuario = get_user_model().objects.order_by('pk').first()
        usuario.last_login = timezone.now()
        usuario.save(update_fields=['last_login'])
        ahora = timezone.now()
        Perfil.objects.filter(usuario=usuario).update(ultima_actividad=ahora, conectado=True)
        extra = Mensaje.objects.create(usuario=usuario, sesion=usuario.semanas.get(), remitente='usuario', contenido='Volví para continuar.', fecha=ahora, clave_envio=uuid.uuid4())
        resultado = self.importar()
        self.assertEqual(resultado['cuentas_creadas'], 0)
        self.assertEqual(resultado['cuentas_existentes'], 2)
        self.assertEqual(Mensaje.objects.count(), 81)
        self.assertTrue(Mensaje.objects.filter(pk=extra.pk).exists())
        self.assertEqual(Perfil.objects.get(usuario=usuario).ultima_actividad, ahora)
        self.assertTrue(Perfil.objects.get(usuario=usuario).conectado)
        self.assertEqual(self.respaldo_mock.call_count, 1)

    def test_login_chat_y_panel_usan_los_registros_importados(self):
        self.importar()
        cuenta = self.datos['cuentas'][0]
        respuesta = self.client.post('/api/auth/login/', json.dumps({'email': cuenta['email'], 'password': self.password}), content_type='application/json')
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.json()['usuario']['terminos_aceptados'])
        chat = self.client.get('/api/chat/').json()
        self.assertEqual(len(chat['mensajes']), 40)
        self.assertFalse(chat['programa_finalizado'])
        self.assertIsNone(chat['sesion_actual']['fin'])
        usuario = get_user_model().objects.get(username=cuenta['email'])
        admin = get_user_model().objects.create_user('administracion', is_staff=True)
        self.client.force_login(admin)
        detalle = self.client.get(f'/api/admin/alumnos/{usuario.pk}/')
        self.assertEqual(detalle.status_code, 200)
        self.assertEqual(detalle.json()['reporte_actual']['cobertura']['analisis_pendientes'], 0)
        self.assertEqual(detalle.json()['reporte_actual']['total_evidencias'], 1)
        excel = self.client.get(f'/api/admin/evaluacion.xlsx?alumnos={usuario.pk}')
        self.assertEqual(excel.status_code, 200)
        self.assertTrue(excel.content.startswith(b'PK'))

    def test_colision_cuenta_impide_todo_y_conserva_cuenta_original(self):
        original = get_user_model().objects.create_user(self.datos['cuentas'][1]['email'], password='OtraClave!78856')
        hash_anterior = original.password
        with self.assertRaises(ErrorCarga):
            self.importar()
        self.assertEqual(get_user_model().objects.count(), 1)
        original.refresh_from_db()
        self.assertEqual(original.password, hash_anterior)
        self.assertFalse(Mensaje.objects.exists())
        self.respaldo_mock.assert_not_called()

    def test_colision_correo_con_mayusculas_no_se_adopta(self):
        get_user_model().objects.create_user('cuenta-distinta', email=self.datos['cuentas'][0]['email'].upper())
        with self.assertRaises(ErrorCarga):
            self.importar()
        self.assertFalse(Mensaje.objects.exists())

    def test_mensaje_o_evidencia_modificada_rechaza_reimportacion(self):
        self.importar()
        mensaje = Mensaje.objects.filter(remitente='usuario').first()
        Mensaje.objects.filter(pk=mensaje.pk).update(contenido='Contenido modificado posteriormente.')
        with self.assertRaises(ErrorCarga):
            self.importar()
        mensaje.refresh_from_db()
        self.assertEqual(mensaje.contenido, 'Contenido modificado posteriormente.')
        Mensaje.objects.filter(pk=mensaje.pk).update(contenido=self.datos['cuentas'][0]['mensajes'][0]['contenido'])
        Evidencia.objects.all().update(observacion='Otra observación.')
        with self.assertRaises(ErrorCarga):
            self.importar()
        self.assertEqual(Evidencia.objects.first().observacion, 'Otra observación.')

    def test_colision_identificador_con_otro_propietario(self):
        usuario = get_user_model().objects.create_user('cuenta-ajena')
        sesion = SesionSemanal.objects.create(usuario=usuario, numero=1, inicio=timezone.now(), fin=None)
        Mensaje.objects.create(id=self.datos['cuentas'][0]['mensajes'][0]['id'], usuario=usuario, sesion=sesion, contenido='Mensaje ajeno', fecha=timezone.now(), remitente='usuario')
        with self.assertRaises(ErrorCarga):
            self.importar()
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Mensaje.objects.get().contenido, 'Mensaje ajeno')

    def test_fallo_intermedio_revierte_lote_entero_despues_del_respaldo(self):
        from reportes.services import actualizar_reporte
        def actualizar(sesion):
            if sesion.usuario.username == self.datos['cuentas'][1]['email']:
                raise RuntimeError('Fallo inducido después de la primera cuenta')
            return actualizar_reporte(sesion)
        with patch('usuarios.carga_actividad.actualizar_reporte', side_effect=actualizar):
            with self.assertRaises(RuntimeError):
                self.importar()
        self.respaldo_mock.assert_called_once()
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Mensaje.objects.exists())
        self.assertFalse(Evidencia.objects.exists())
        self.assertFalse(ReporteSemanal.objects.exists())

    def test_no_acepta_permisos_campos_extra_fuente_alterada_ni_hash_inutilizable(self):
        cambios = [
            lambda d: d.update(origen='conversacion'),
            lambda d: d.update(analisis_metodo='modelo'),
            lambda d: d['cuentas'][0].update(is_staff=True),
            lambda d: d['cuentas'][0].update(password_hash='!inutilizable'),
            lambda d: d['cuentas'][0].update(email='persona@gmail.com'),
        ]
        for cambiar in cambios:
            datos = deepcopy(self.datos)
            cambiar(datos)
            with self.subTest(cambiar=cambiar), self.assertRaises(ErrorCarga):
                validar_paquete(datos)

    def test_no_acepta_fechas_fuera_de_horario_o_sin_zona(self):
        for fecha in ('2026-09-11T18:00:01-05:00', '2026-09-11T12:59:59-05:00', '2026-09-11T13:00:00'):
            datos = deepcopy(self.datos)
            datos['cuentas'][0]['mensajes'][4]['fecha'] = fecha
            with self.subTest(fecha=fecha), self.assertRaises(ErrorCarga):
                validar_paquete(datos)

    def test_no_acepta_respuestas_ajenas_citas_inventadas_o_senales_incompatibles(self):
        cambios = [
            lambda d: d['cuentas'][0]['mensajes'][1].update(respuesta_a=d['cuentas'][1]['mensajes'][0]['id']),
            lambda d: d['cuentas'][0]['mensajes'][4]['evidencias'][0].update(cita='Una cita que no existe.'),
            lambda d: d['cuentas'][0]['mensajes'][4]['evidencias'][0].update(senal='recurso'),
            lambda d: d['cuentas'][0]['mensajes'][1]['evidencias'].append(d['cuentas'][0]['mensajes'][4]['evidencias'][0]),
            lambda d: d['cuentas'][1]['mensajes'][0].update(id=d['cuentas'][0]['mensajes'][0]['id']),
        ]
        for cambiar in cambios:
            datos = deepcopy(self.datos)
            cambiar(datos)
            with self.subTest(cambiar=cambiar), self.assertRaises(ErrorCarga):
                validar_paquete(datos)

    def test_sha256_y_comando_predeterminado_solo_validan(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'actividad.json'
            contenido = json.dumps(self.datos, ensure_ascii=False).encode('utf-8')
            archivo.write_bytes(contenido)
            huella = hashlib.sha256(contenido).hexdigest()
            with self.assertRaises(ErrorCarga):
                leer_paquete(archivo, '0' * 64)
            self.assertEqual(leer_paquete(archivo, huella)['_conteos']['mensajes'], 80)
            with patch('usuarios.carga_actividad.comprobar_entorno'):
                salida = StringIO()
                call_command('cargar_actividad', str(archivo), sha256=huella, stdout=salida)
                self.assertEqual(json.loads(salida.getvalue())['modo'], 'validar')
                self.assertFalse(get_user_model().objects.exists())
                with self.assertRaises(CommandError):
                    call_command('cargar_actividad', str(archivo), sha256='0' * 64)

    def test_entorno_rechaza_base_ausente_sin_crearla(self):
        from django.db import connection
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'no-existe.sqlite3'
            with patch.dict(connection.settings_dict, {'NAME': str(archivo)}):
                with self.assertRaises(ErrorCarga):
                    comprobar_entorno()
            self.assertFalse(archivo.exists())

    def test_json_rechaza_campos_repetidos_aunque_huella_coincida(self):
        with TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / 'repetido.json'
            contenido = b'{"schema":"uno","schema":"dos"}'
            archivo.write_bytes(contenido)
            with self.assertRaises(ErrorCarga):
                leer_paquete(archivo, hashlib.sha256(contenido).hexdigest())


class RespaldoActividadTests(TestCase):
    def test_respaldo_sqlite_consistente_no_sobrescribe(self):
        from django.db import connection
        with TemporaryDirectory() as carpeta:
            origen = Path(carpeta) / 'origen.sqlite3'
            destino = Path(carpeta) / 'privado' / 'respaldo.sqlite3'
            with closing(sqlite3.connect(origen)) as db:
                with db:
                    db.execute('CREATE TABLE datos (valor TEXT NOT NULL)')
                    db.execute('INSERT INTO datos VALUES (?)', ('conservar',))
            with patch.dict(connection.settings_dict, {'NAME': str(origen)}):
                self.assertEqual(_crear_respaldo(destino), str(destino))
                with self.assertRaises(ErrorCarga):
                    _crear_respaldo(destino)
                with self.assertRaises(ErrorCarga):
                    _crear_respaldo(origen)
            with closing(sqlite3.connect(destino)) as db:
                self.assertEqual(db.execute('SELECT valor FROM datos').fetchone(), ('conservar',))


class VersionServicioCargaTests(TestCase):
    def test_detecta_codigo_antiguo_aunque_la_base_exista(self):
        original = Perfil._meta.get_field
        def campo(nombre):
            if nombre == 'terminos_version':
                raise FieldDoesNotExist(nombre)
            return original(nombre)
        with patch.object(Perfil._meta, 'get_field', side_effect=campo):
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                comprobar_entorno()

    def test_detecta_modelo_con_fin_obligatorio(self):
        campo = SesionSemanal._meta.get_field('fin')
        with patch.object(campo, 'null', False), patch('usuarios.carga_actividad._crear_respaldo') as respaldo:
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                importar_paquete({}, aplicar=True)
            respaldo.assert_not_called()
            self.assertFalse(get_user_model().objects.exists())

    def entorno_temporal(self, carpeta):
        # Solo se sustituye el nombre del fichero para la comprobación de ruta.
        # El test runner ya mantiene una conexión abierta a su base temporal;
        # las lecturas de esquema permanecen en esa conexión de prueba.
        from django.db import connection
        archivo = Path(carpeta) / 'ruta-validada.sqlite3'
        archivo.touch()
        return patch.dict(connection.settings_dict, {'NAME': str(archivo)})

    def test_grafo_antiguo_no_pasa_por_estar_completo(self):
        with TemporaryDirectory() as carpeta, self.entorno_temporal(carpeta), patch('usuarios.carga_actividad.MigrationExecutor') as executor:
            executor.return_value.loader.disk_migrations = {('usuarios', '0001_initial'): object()}
            executor.return_value.loader.applied_migrations = {('usuarios', '0001_initial'): object()}
            executor.return_value.migration_plan.return_value = []
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                comprobar_entorno()

    def test_migracion_requerida_sin_aplicar_es_rechazada(self):
        with TemporaryDirectory() as carpeta, self.entorno_temporal(carpeta), patch('usuarios.carga_actividad.MigrationExecutor') as executor:
            executor.return_value.loader.disk_migrations = dict.fromkeys(MIGRACIONES_REQUERIDAS)
            executor.return_value.loader.applied_migrations = dict.fromkeys(MIGRACIONES_REQUERIDAS - {('chat', '0002_retencion_mensajes')})
            executor.return_value.migration_plan.return_value = []
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                comprobar_entorno()

    def test_detecta_columnas_ausentes_aunque_migraciones_se_marcaron_aplicadas(self):
        from django.db import connection
        original = connection.introspection.get_table_description
        def descripcion(cursor, tabla):
            columnas = original(cursor, tabla)
            return [campo for campo in columnas if campo.name != 'retencion_version'] if tabla == 'chat_mensaje' else columnas
        with TemporaryDirectory() as carpeta, self.entorno_temporal(carpeta), patch.object(connection.introspection, 'get_table_description', side_effect=descripcion):
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                comprobar_entorno()

    def test_esquema_actual_con_fin_nullable_supera_validacion(self):
        with TemporaryDirectory() as carpeta, self.entorno_temporal(carpeta):
            comprobar_entorno()

    def test_detecta_fin_no_nullable_en_base_aunque_modelo_sea_actual(self):
        from django.db import connection
        original = connection.introspection.get_table_description
        def descripcion(cursor, tabla):
            columnas = original(cursor, tabla)
            if tabla == 'sesiones_sesionsemanal':
                return [SimpleNamespace(name=campo.name, null_ok=False) if campo.name == 'fin' else campo for campo in columnas]
            return columnas
        with TemporaryDirectory() as carpeta, self.entorno_temporal(carpeta), patch.object(connection.introspection, 'get_table_description', side_effect=descripcion):
            with self.assertRaisesMessage(ErrorCarga, ERROR_VERSION):
                comprobar_entorno()
