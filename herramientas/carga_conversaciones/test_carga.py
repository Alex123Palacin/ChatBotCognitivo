"""Ejecutar con el test runner de Django; usa su base temporal, nunca la real."""
from contextlib import redirect_stdout
from datetime import timedelta
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from chat.models import Mensaje
from ml.ollama import ErrorModelo
from reportes.models import Evidencia
from usuarios.models import Perfil
from .cargar import Carga, guardar, historias
from . import continuar
from .ajustar_fechas import ajustar


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CargaTests(TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.base = Path(self.temporal.name)
        self.archivo = self.base / 'historias.json'
        datos = json.loads(Path(__file__).with_name('historias.json').read_text(encoding='utf-8'))
        datos['personas'] = datos['personas'][:2]
        guardar(self.archivo, datos)
        self.carga = Carga(self.archivo, self.base / 'privado', 'lote-independiente')
        self.admin = get_user_model().objects.create_user('administrador', password='clave-del-administrador', is_staff=True)
        self.salida = redirect_stdout(io.StringIO())
        self.salida.__enter__()
        self.addCleanup(self.salida.__exit__, None, None, None)

    def preparar(self):
        self.carga.cargar(respaldo=False)

    def test_archivo_completo_tiene_20_personas_y_80_semanas(self):
        personas, _ = historias(Path(__file__).with_name('historias.json'))
        self.assertEqual(len(personas), 20)
        self.assertEqual(sum(len(p['semanas']) for p in personas), 80)
        self.assertEqual(sum(len(s) for p in personas for s in p['semanas']), 160)

    def test_fechas_futuras_o_sin_zona_se_rechazan(self):
        for inicio in [timezone.now().isoformat(), '2026-01-01T09:00:00']:
            with self.subTest(inicio=inicio), self.assertRaises(ValueError):
                Carga(self.archivo, self.base / ('otra' + str(len(inicio))), 'otro-lote', inicio)

    def test_cuentas_y_semanas_son_idempotentes_y_no_cambian_admin(self):
        self.preparar()
        ids = list(get_user_model().objects.values_list('id', flat=True))
        self.carga.cargar(respaldo=False)
        self.assertEqual(ids, list(get_user_model().objects.values_list('id', flat=True)))
        for p in self.carga.personas:
            u = self.carga.usuario(p['clave'])
            self.assertFalse(u.is_staff)
            self.assertTrue(u.check_password(self.carga.manifiesto['cuentas'][p['clave']]['password']))
            sesiones = list(u.semanas.all())
            self.assertEqual([s.numero for s in sesiones], [1, 2, 3, 4])
            self.assertTrue(all(s.fin - s.inicio == timedelta(days=7) and s.fin < timezone.now() for s in sesiones))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.check_password('clave-del-administrador'))

    def test_colision_se_detecta_antes_de_crear_cuentas(self):
        self.carga.preparar()
        correo = self.carga.manifiesto['cuentas']['p02']['email']
        ajeno = get_user_model().objects.create_user(correo, email=correo, password='ajena')
        with self.assertRaises(ValueError):
            self.carga.cargar(respaldo=False)
        self.assertEqual(get_user_model().objects.count(), 2)
        self.assertTrue(get_user_model().objects.get(pk=ajeno.pk).check_password('ajena'))

    def test_recupera_corte_entre_commit_y_manifiesto(self):
        self.preparar()
        esperado = self.carga.usuario('p01').pk
        self.carga.manifiesto['cuentas']['p01']['id'] = None
        self.carga.persistir()
        self.carga.cargar(respaldo=False)
        self.assertEqual(self.carga.usuario('p01').pk, esperado)

    def test_cambio_de_historias_no_reutiliza_el_lote(self):
        datos = json.loads(self.archivo.read_text(encoding='utf-8'))
        datos['personas'][0]['semanas'][0][0] += ' Otra cosa.'
        guardar(self.archivo, datos)
        with self.assertRaises(ValueError):
            Carga(self.archivo, self.base / 'privado', 'lote-independiente')

    def analisis(self, contenido, historial, cancelar):
        return [{'indicador': 'sintomas_psicologicos', 'senal': 'dificultad', 'cita': contenido[:24], 'observacion': 'Observación del doble de prueba.'}]

    @patch('reportes.services.analizar_mensaje')
    @patch('ml.conversacion.responder_conversacion_stream')
    def test_carga_reanudable_con_respuestas_reportes_y_citas(self, responder, analizar):
        self.preparar()
        responder.side_effect = lambda historial, contexto: (parte for parte in ['Entiendo lo que cuentas. ', 'Podemos hablar de ello.'])
        analizar.side_effect = self.analisis
        self.carga.procesar(max_pasos=1, pausa=0)
        primero = Mensaje.objects.filter(remitente='usuario').get()
        self.assertEqual(primero.respuesta.fecha - primero.fecha, timedelta(seconds=20))
        self.assertEqual(primero.analisis_estado, 'listo')
        contexto_primero = responder.call_args.args[1]
        self.assertNotIn(self.carga.personas[0]['semanas'][0][1], contexto_primero['resumen'])
        self.carga.procesar(pausa=0)
        self.assertTrue(self.carga.estado()['completo'])
        self.assertEqual(Mensaje.objects.count(), 32)
        self.assertEqual(Evidencia.objects.count(), 16)
        self.assertEqual(self.carga.estado()['citas_invalidas'], 0)
        self.carga.procesar(pausa=0)
        self.assertEqual(Mensaje.objects.count(), 32)
        self.carga.exportar()
        self.assertTrue((self.carga.carpeta / 'resultados.json').exists())

    @patch('ml.conversacion.responder_conversacion_stream', side_effect=ErrorModelo('Sin conexión.'))
    def test_fallo_del_modelo_no_fabrica_respuesta_y_libera_reserva(self, responder):
        self.preparar()
        with self.assertRaises(ErrorModelo):
            self.carga.procesar(max_pasos=1, pausa=0)
        self.assertEqual(Mensaje.objects.filter(remitente='asistente').count(), 0)
        self.assertEqual(Perfil.objects.exclude(respuesta_token='').count(), 0)
        self.assertEqual(self.carga.estado()['respuestas'], 0)

    def test_limpieza_necesita_lote_exacto_y_conserva_administrador(self):
        self.preparar()
        self.carga.limpiar()
        self.assertEqual(get_user_model().objects.count(), 3)
        self.carga.limpiar('lote-independiente')
        self.assertEqual(list(get_user_model().objects.values_list('pk', flat=True)), [self.admin.pk])

    def test_identidad_modificada_impide_limpieza(self):
        self.preparar()
        u = self.carga.usuario('p02')
        u.is_staff = True; u.save(update_fields=['is_staff'])
        with self.assertRaises(ValueError):
            self.carga.limpiar('lote-independiente')
        self.assertEqual(get_user_model().objects.count(), 3)

    def test_supervisor_reanuda_y_detecta_fin(self):
        from types import SimpleNamespace
        carpeta = self.base / 'supervisado'
        carpeta.mkdir()
        llamadas = []

        def ejecutar(*args, **kwargs):
            llamadas.append(args)
            guardar(carpeta / 'estado.json', {'completo': len(llamadas) == 2})
            return SimpleNamespace(returncode=1 if len(llamadas) == 1 else 0)

        with patch.object(continuar.sys, 'argv', ['continuar.py', '--carpeta', str(carpeta)]), patch.object(continuar.subprocess, 'run', side_effect=ejecutar), patch.object(continuar.time, 'sleep'):
            continuar.main()
        self.assertEqual(len(llamadas), 2)
        estado = json.loads((carpeta / 'supervision' / 'estado.json').read_text())
        self.assertEqual(estado['estado'], 'completo')

    @patch('reportes.services.analizar_mensaje')
    @patch('ml.conversacion.responder_conversacion_stream')
    def test_recalendario_preserva_mensajes_y_permite_reanudar(self, responder, analizar):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        self.preparar()
        responder.side_effect = lambda h, c: (s for s in ['Podemos conversar sobre ello.'])
        analizar.side_effect = self.analisis
        self.carga.procesar(max_pasos=1, pausa=0)
        ids = set(Mensaje.objects.values_list('pk', flat=True))
        (self.carga.carpeta / 'detener').touch()
        with patch('django.utils.timezone.now', return_value=datetime(2026, 10, 23, 12, tzinfo=ZoneInfo('America/Lima'))):
            ajustar(self.carga, '2026-09-10', '2026-10-23')
            ajustar(self.carga, '2026-09-10', '2026-10-23')
        self.assertEqual(set(Mensaje.objects.values_list('pk', flat=True)), ids)
        self.assertEqual(self.carga.usuario('p01').semanas.first().inicio.date().isoformat(), '2026-09-10')
        self.assertEqual(self.carga.usuario('p02').semanas.last().fin.date().isoformat(), '2026-10-23')
        # Una pausa ordenada se retira solo al reanudar intencionalmente.
        (self.carga.carpeta / 'detener').rename(self.carga.carpeta / 'pausa-anterior')
        self.carga.procesar(pausa=0)
        self.assertTrue(self.carga.estado()['completo'])
        ultimo = Mensaje.objects.order_by('-fecha').first()
        self.assertEqual(ultimo.fecha.astimezone(ZoneInfo('America/Lima')).date().isoformat(), '2026-10-23')

    def test_rango_corto_se_rechaza_sin_cambiar_datos(self):
        self.preparar()
        inicio = self.carga.usuario('p01').perfil.inicio_programa
        (self.carga.carpeta / 'detener').touch()
        with self.assertRaises(ValueError):
            ajustar(self.carga, '2026-09-10', '2026-09-20')
        self.assertEqual(self.carga.usuario('p01').perfil.inicio_programa, inicio)
