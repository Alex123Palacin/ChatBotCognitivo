from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from chat.models import Mensaje
from reportes.models import Evidencia
from .test_carga import CargaTests
from .cargar import guardar
from .ampliar import Ampliacion


class AmpliacionTests(CargaTests):
    def preparar_ampliacion(self):
        self.preparar()
        datos = json.loads(Path(__file__).with_name('ampliacion.json').read_text(encoding='utf-8'))
        datos['personas'] = datos['personas'][:2]
        ruta = self.base / 'ampliacion.json'
        guardar(ruta, datos)
        self.ampliacion = Ampliacion(self.carga, ruta)
        objetos = []
        for mid, p in self.ampliacion.previstos.items():
            objetos.append({'model': 'chat.mensaje', 'pk': str(mid), 'fields': {'usuario': p['usuario_id'], 'sesion': p['sesion_id'], 'contenido': p['contenido'] or 'Te escucho, puedes contarme lo que necesites.', 'fecha': p['fecha'].isoformat(), 'remitente': p['remitente'], 'clave_envio': str(p['clave_envio']) if p['clave_envio'] else None, 'respuesta_a': str(p['respuesta_a_id']) if p['respuesta_a_id'] else None, 'analisis_estado': 'listo'}})
        return {'lote': self.carga.lote, 'ampliacion_sha256': self.ampliacion.sha, 'origen': datos['origen'], 'objetos': objetos}

    def incorporar(self, paquete):
        with patch.object(self.carga, 'respaldo'):
            return self.ampliacion.incorporar(paquete)

    def test_importacion_idempotente_no_toca_cuentas_ni_originales(self):
        paquete = self.preparar_ampliacion()
        original = self.carga.mensaje(self.carga.personas[0], 1, 0, self.carga.personas[0]['semanas'][0][0])
        identidad = self.admin.password
        self.incorporar(paquete)
        self.incorporar(paquete)
        self.assertEqual(Mensaje.objects.count(), 65)
        self.assertEqual(Mensaje.objects.get(pk=original.pk).contenido, original.contenido)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, identidad)
        for p in self.ampliacion.previstos.values():
            sesion = self.ampliacion.sesiones[p['sesion_id']]
            self.assertTrue(sesion.inicio < p['fecha'] < sesion.fin)
        self.assertEqual(self.ampliacion.estado()['analizados'], 32)

    def test_propietario_fecha_y_paquete_incompleto_se_rechazan(self):
        original = self.preparar_ampliacion()
        for campo, valor in [('usuario', self.admin.pk), ('fecha', '2030-01-01T00:00:00+00:00'), ('respuesta_a', str(uuid.uuid4()))]:
            paquete = deepcopy(original)
            paquete['objetos'][0]['fields'][campo] = valor
            with self.assertRaises(ValueError):
                self.incorporar(paquete)
            self.assertEqual(Mensaje.objects.count(), 0)
        original['objetos'].pop()
        with self.assertRaises(ValueError):
            self.incorporar(original)

    def test_no_reemplaza_una_respuesta_existente(self):
        paquete = self.preparar_ampliacion()
        self.incorporar(paquete)
        respuesta = next(o for o in paquete['objetos'] if o['fields']['remitente'] == 'asistente')
        respuesta['fields']['contenido'] = 'Respuesta distinta'
        with self.assertRaises(ValueError):
            self.incorporar(paquete)
        self.assertFalse(Mensaje.objects.filter(contenido='Respuesta distinta').exists())

    def test_cita_falsa_no_se_importa(self):
        paquete = self.preparar_ampliacion()
        paquete['objetos'].append({'model': 'reportes.evidencia', 'pk': 1, 'fields': {'mensaje': paquete['objetos'][0]['pk'], 'indicador': 'planificacion', 'senal': 'recurso', 'cita': 'Cita que nunca escribió.', 'observacion': 'Observación'}})
        with self.assertRaises(ValueError):
            self.incorporar(paquete)
        self.assertEqual(Evidencia.objects.count(), 0)
