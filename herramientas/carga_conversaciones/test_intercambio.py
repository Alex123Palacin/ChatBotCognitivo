"""Verifica la importación en la base temporal de Django."""
from copy import deepcopy
from contextlib import closing
import sqlite3
from unittest.mock import patch

from chat.models import Mensaje
from reportes.models import Evidencia
from .test_carga import CargaTests
from .intercambio import incorporar, paquete
from .auditar import auditar


class IntercambioTests(CargaTests):
    def generar(self):
        self.preparar()
        with patch('reportes.services.analizar_mensaje', side_effect=self.analisis), patch('ml.conversacion.responder_conversacion_stream', side_effect=lambda *a: (s for s in ['Te escucho. ¿Qué te preocupa más?'])):
            self.carga.procesar(max_pasos=2, pausa=0)
        return deepcopy(paquete(self.carga))

    def test_importa_solo_mensajes_y_conserva_cuentas(self):
        datos = self.generar()
        esperado = list(Mensaje.objects.values_list('id', 'contenido', 'fecha'))
        evidencia = list(Evidencia.objects.values_list('mensaje_id', 'cita'))
        clave_admin = self.admin.password
        Mensaje.objects.all().delete()
        incorporar(self.carga, datos)
        self.assertEqual(list(Mensaje.objects.values_list('id', 'contenido', 'fecha')), esperado)
        self.assertEqual(list(Evidencia.objects.values_list('mensaje_id', 'cita')), evidencia)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, clave_admin)
        incorporar(self.carga, datos)
        self.assertEqual(Mensaje.objects.count(), 4)

    def test_rechaza_propietario_y_no_modifica_mensajes(self):
        datos = self.generar()
        m = next(o for o in datos['objetos'] if o['model'] == 'chat.mensaje')
        m['fields']['usuario'] = self.admin.pk
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)
        self.assertEqual(Mensaje.objects.count(), 4)

    def test_rechaza_cita_no_literal(self):
        datos = self.generar()
        e = next(o for o in datos['objetos'] if o['model'] == 'reportes.evidencia')
        e['fields']['cita'] = 'Una afirmación inventada que no aparece.'
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)

    def test_rechaza_cambios_en_respuesta_ya_existente(self):
        datos = self.generar()
        m = next(o for o in datos['objetos'] if o['model'] == 'chat.mensaje' and o['fields']['remitente'] == 'asistente')
        m['fields']['contenido'] = 'Texto diferente del guardado en el servidor.'
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)
        self.assertFalse(Mensaje.objects.filter(contenido=m['fields']['contenido']).exists())

    def test_rechaza_borrado_de_mensajes_existentes(self):
        datos = self.generar()
        datos['objetos'] = [o for o in datos['objetos'] if o['model'] not in {'chat.mensaje', 'reportes.evidencia'}]
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)
        self.assertEqual(Mensaje.objects.count(), 4)

    def test_rechaza_analisis_pendiente(self):
        datos = self.generar()
        m = next(o for o in datos['objetos'] if o['model'] == 'chat.mensaje')
        m['fields']['analisis_estado'] = 'pendiente'
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)

    def test_rechaza_fecha_ajena_al_calendario(self):
        datos = self.generar()
        m = next(o for o in datos['objetos'] if o['model'] == 'chat.mensaje')
        m['fields']['fecha'] = '2030-01-01T12:00:00Z'
        with self.assertRaises(ValueError):
            incorporar(self.carga, datos)

    def test_auditoria_verifica_accesos_y_conservacion_del_admin(self):
        with closing(sqlite3.connect(str(self.carga.carpeta / 'respaldo-anterior.sqlite3'))) as copia:
            copia.execute('CREATE TABLE auth_user (id, username, email, password, is_staff, is_superuser)')
            copia.execute('INSERT INTO auth_user VALUES (?, ?, ?, ?, ?, ?)',
                          (self.admin.pk, self.admin.username, self.admin.email, self.admin.password, self.admin.is_staff, self.admin.is_superuser))
            copia.commit()
        self.preparar()
        with patch('reportes.services.analizar_mensaje', side_effect=self.analisis), patch('ml.conversacion.responder_conversacion_stream', side_effect=lambda *a: (s for s in ['Te escucho.'])):
            self.carga.procesar(pausa=0)
        resultado = auditar(self.carga)
        self.assertTrue(resultado['estado']['completo'])
        self.assertEqual(resultado['cuentas_previas_conservadas'], 1)
        self.assertEqual(resultado['credenciales_verificadas'], 2)
        self.assertTrue((self.carga.carpeta / 'auditoria-final.json').exists())
