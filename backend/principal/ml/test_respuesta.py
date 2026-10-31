import json
from django.test import SimpleTestCase

from .ollama import ErrorModelo
from .respuesta import leer_respuesta, texto_respuesta_flujo, sin_ofertas_repetidas


class RespuestaGuiadaTests(SimpleTestCase):
    def test_solo_escucha_no_repite_ofertas_partidas_entre_fragmentos(self):
        texto = 'Tu día suena cansado. Si quieres, puedo enseñarte un ejercicio. La música te acompañó un rato.'
        for corte in range(len(texto)+1):
            respuesta = ''.join(sin_ofertas_repetidas(iter([texto[:corte],texto[corte:]])))
            self.assertIn('Tu día suena cansado.', respuesta)
            self.assertIn('La música te acompañó un rato.', respuesta)
            self.assertNotIn('ejercicio', respuesta)

    def test_fragmentos_no_muestran_json_y_llegan_antes_del_final(self):
        consumidos = []
        def flujo():
            yield '{"respuesta":"Hola '
            consumidos.append('segundo')
            yield 'otra vez."}'
        texto = texto_respuesta_flujo(flujo())
        self.assertEqual(next(texto), 'Hola ')
        self.assertEqual(consumidos, [])
        self.assertEqual(''.join(texto), 'otra vez.')

    def test_cualquier_corte_conserva_comillas_saltos_acentos_y_emojis(self):
        valor = 'Dijo "hola".\nÁnimo, sigue a tu ritmo 🙂 y respeta \\ el texto.'
        for ascii in (True, False):
            datos = json.dumps({'respuesta': valor}, ensure_ascii=ascii)
            for corte in range(len(datos)+1):
                with self.subTest(corte=corte, ascii=ascii):
                    self.assertEqual(''.join(texto_respuesta_flujo(iter([datos[:corte],datos[corte:]]))), valor)
            self.assertEqual(''.join(texto_respuesta_flujo(iter(datos))), valor)

    def test_json_incompleto_o_ajeno_no_se_guarda_como_respuesta_terminada(self):
        for datos in ['{"respuesta":"incompleta', '{}', '{"respuesta":null}', '{"respuesta":[]}',
                      '{"respuesta": "", "otro": 1}', '{"respuesta": "Hola", "otro": 1}', 'Hola']:
            with self.subTest(datos=datos):
                with self.assertRaises(ErrorModelo):
                    leer_respuesta(datos)
                with self.assertRaises(ErrorModelo):
                    list(texto_respuesta_flujo(iter([datos])))
