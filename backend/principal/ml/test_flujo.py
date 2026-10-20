import json
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from .ollama import ErrorModelo, generar_flujo, precalentar_modelo


@override_settings(OLLAMA_URL='http://127.0.0.1:11434', OLLAMA_MODEL='deepseek-r1:8b',
                   OLLAMA_TIMEOUT=2, OLLAMA_KEEP_ALIVE='-1', OLLAMA_NUM_CTX=4096, OLLAMA_NUM_GPU=0)
class ModeloFlujoTests(SimpleTestCase):
    def conexion(self, eventos):
        respuesta = MagicMock(status=200)
        respuesta.__iter__.return_value = iter(json.dumps(e).encode() for e in eventos)
        conexion = MagicMock()
        conexion.getresponse.return_value = respuesta
        return conexion

    def generar(self, eventos):
        conexion = self.conexion(eventos)
        with patch('ml.ollama.http.client.HTTPConnection', return_value=conexion):
            return list(generar_flujo([{'role': 'user', 'content': 'Tengo un examen'}], directo=True)), conexion

    def test_stream_oculta_razonamiento_y_conserva_utf8(self):
        fragmentos, conexion = self.generar([
            {'response': '<thi', 'done': False},
            {'response': 'nk>Privado', 'done': False},
            {'response': '</thi', 'done': False},
            {'response': 'nk>¿Cómo te ', 'done': False, 'thinking': 'Privado'},
            {'response': 'fue en el colegio?', 'done': True, 'done_reason': 'stop'},
        ])
        self.assertEqual(''.join(fragmentos), '¿Cómo te fue en el colegio?')
        self.assertGreater(len(fragmentos), 1)
        cuerpo = json.loads(conexion.request.call_args.kwargs['body'])
        self.assertTrue(cuerpo['stream'])
        self.assertTrue(cuerpo['raw'])
        self.assertEqual(cuerpo['keep_alive'], -1)

    def test_acepta_contenido_nativo_sin_leer_thinking(self):
        fragmentos, _ = self.generar([
            {'message': {'thinking': 'Privado', 'content': ''}, 'done': False},
            {'message': {'content': 'Hola, te escucho.'}, 'done': True},
        ])
        self.assertEqual(''.join(fragmentos), 'Hola, te escucho.')

    def test_no_confirma_truncamiento_eof_o_pensamiento_incompleto(self):
        casos = [
            [{'response': 'Texto cortado', 'done': True, 'done_reason': 'length'}],
            [{'response': 'Sin final', 'done': False}],
            [{'response': 'Hola ', 'done': False}, {'response': '<thi', 'done': True}],
            [{'response': 'Hola <think>oculto', 'done': True}],
            [{'response': '<think>Solo privado</think>', 'done': True}],
        ]
        for eventos in casos:
            with self.subTest(eventos=eventos), self.assertRaises(ErrorModelo):
                self.generar(eventos)

    def test_cierre_sin_apertura_no_se_entrega_como_respuesta(self):
        partes, _ = self.generar([
            {'response': 'Pri', 'done': False},
            {'response': 'vado</think>Hola', 'done': True},
        ])
        self.assertEqual(''.join(partes), 'Hola')
        with self.assertRaises(ErrorModelo):
            self.generar([{'response': 'Texto ya emitido ', 'done': False},
                          {'response': 'más</think>Hola', 'done': True}])

    def test_cerrar_consumidor_cierra_socket_sin_esperar_final(self):
        conexion = self.conexion([{'response': 'Primera palabra ', 'done': False},
                                 {'response': 'final.', 'done': True}])
        with patch('ml.ollama.http.client.HTTPConnection', return_value=conexion):
            flujo = generar_flujo([])
            self.assertEqual(next(flujo), 'Primera palabra ')
            flujo.close()
        conexion.sock.shutdown.assert_called_once()

    def test_precalienta_mismo_contexto_con_keep_alive_numerico(self):
        respuesta = MagicMock()
        respuesta.__enter__.return_value = MagicMock()
        with patch('ml.ollama.urlopen', return_value=respuesta) as llamada, patch('ml.ollama.json.load', return_value={'done': True}):
            precalentar_modelo()
        cuerpo = json.loads(llamada.call_args.args[0].data)
        self.assertIn('estudiantes de colegio', cuerpo['prompt'])
        self.assertTrue(cuerpo['raw'])
        self.assertEqual(cuerpo['keep_alive'], -1)
        self.assertEqual(cuerpo['options'], {'num_ctx': 4096, 'num_gpu': 0, 'num_predict': 1})

    def test_fallo_precalentamiento_no_impide_abrir_sitio(self):
        salida = StringIO()
        with patch('chat.management.commands.precalentar_modelo.precalentar_modelo', side_effect=ErrorModelo('No disponible')):
            call_command('precalentar_modelo', stdout=salida, stderr=salida)
        self.assertIn('Se volverá a intentar', salida.getvalue())
