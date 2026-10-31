import json
from unittest.mock import patch
from django.test import SimpleTestCase

from .apoyo import RECURSOS, puede_preguntar, preparar_apoyo, respuesta_prioritaria
from .ollama import ErrorModelo
from .conversacion import preferencias_conversacion, responder_conversacion, responder_conversacion_stream, _opciones_respuesta


def usuario(texto):
    return {'role':'user','content':texto}


class ApoyoTests(SimpleTestCase):
    def test_recurso_sigue_disponible_si_falla_la_introduccion_del_modelo(self):
        h=[usuario('Estoy muy nervioso por el examen')]
        with patch('ml.conversacion.generar',side_effect=ErrorModelo('modelo no disponible')):
            salida=responder_conversacion(h)
        self.assertFalse(salida.startswith('\n'))
        self.assertIn(RECURSOS['anclaje']['texto'],salida)
        def fallo(*args,**kwargs):
            yield '{"respuesta":"'
            raise ErrorModelo('generación interrumpida')
        with patch('ml.conversacion.generar_flujo',side_effect=fallo):
            self.assertEqual(''.join(responder_conversacion_stream(h)),salida)
        self.assertEqual(_opciones_respuesta(h)['timeout'],8)

    def test_malestar_fisico_y_emocional_recibe_recurso_distinto_de_planificacion(self):
        for mensaje in ['Me duele el estómago antes del examen', 'Tengo miedo de fracasar en la exposición',
                        'No puedo dormir pensando en el examen']:
            with self.subTest(mensaje=mensaje), patch('ml.conversacion.generar',return_value=json.dumps({'respuesta':'Suena difícil llevar esa sensación ahora.'})) as modelo:
                salida=responder_conversacion([usuario(mensaje)])
                plan=preparar_apoyo([usuario(mensaje)],{})
                self.assertIn(plan['texto'],salida)
                self.assertNotIn('horario',salida)
                self.assertEqual(modelo.call_count,1)
                self.assertEqual(modelo.call_args.kwargs['limite'],96)

    def test_no_pregunta_en_cada_turno_y_respeta_peticion_explicita(self):
        self.assertTrue(puede_preguntar([usuario('Estoy nerviosa')],{}))
        historial=[{'role':'assistant','content':'¿Qué pasó en clase?'}, usuario('Hubo un examen')]
        self.assertFalse(puede_preguntar(historial,{}))
        self.assertFalse(puede_preguntar(historial,{'sin_preguntas':True}))
        self.assertTrue(puede_preguntar(historial,{'preguntas_solicitadas':True}))
        historial += [{'role':'assistant','content':'Fue una situación difícil.'},usuario('Sí'),
                      {'role':'assistant','content':'Podemos ir a tu ritmo.'},usuario('Me siento mejor')]
        self.assertTrue(puede_preguntar(historial,{}))

    def test_puede_conversar_sin_consejos_sin_prohibir_todas_las_preguntas(self):
        p=preferencias_conversacion(['solo quiero hablar'])
        self.assertTrue(p['solo_escucha']); self.assertFalse(p['sin_preguntas'])
        self.assertIsNone(preparar_apoyo([usuario('Estoy nervioso')],p))
        p=preferencias_conversacion(['no quiero que me hagas preguntas'])
        self.assertFalse(puede_preguntar([usuario('Estoy nervioso')],p))

    def test_no_repite_recurso_si_ya_lo_probo_y_no_funciono(self):
        h=[usuario('Estoy muy nervioso por el examen'),
           {'role':'assistant','content':RECURSOS['anclaje']['texto']}, usuario('No me funcionó')]
        plan=preparar_apoyo(h,{})
        self.assertEqual(plan['codigo'],'pensamiento')
        self.assertEqual(plan['pregunta'],'')

    def test_no_reaviva_malestar_cuando_cambia_de_tema_o_lo_niega(self):
        for mensaje in ['Ahora quiero hablar de fútbol','No tengo ansiedad ni dolor',
                        'Mi personaje en un cuento tiene ansiedad', 'Ya me siento mejor']:
            self.assertIsNone(preparar_apoyo([usuario(mensaje)],{}))
        plan=preparar_apoyo([usuario('No tengo dolor, pero estoy muy nerviosa')],{})
        self.assertEqual(plan['tema'],'preocupación o nervios relatados')

    def test_rechazos_de_ejercicios_y_respiracion_se_respetan(self):
        p=preferencias_conversacion(['no quiero ejercicios de respiración'])
        self.assertTrue(p['sin_respiracion'])
        p=preferencias_conversacion(['no quiero ejercicios'])
        plan=preparar_apoyo([usuario('Estoy nervioso')],p)
        self.assertFalse(RECURSOS[plan['codigo']]['ejercicio'])

    def test_molestias_graves_no_se_atribuyen_a_estres_ni_esperan_al_modelo(self):
        for mensaje in ['Tengo dolor fuerte de pecho y me falta el aire', 'No puedo respirar',
                        'Me duele el pecho desde ayer']:
            with self.subTest(mensaje=mensaje), patch('ml.conversacion.generar') as modelo:
                salida=responder_conversacion([usuario(mensaje)])
                self.assertIn('adulto',salida)
                self.assertNotIn('inhala',salida)
                modelo.assert_not_called()
        self.assertIsNone(respuesta_prioritaria([usuario('No tengo dolor de pecho y no tengo dificultad para respirar')]))

    def test_formato_completo_y_stream_muestran_el_mismo_recurso_sin_segunda_llamada(self):
        h=[usuario('Me tiemblan las manos antes de exponer')]
        datos=json.dumps({'respuesta':'Notar ese temblor antes de exponer puede ser incómodo.'})
        with patch('ml.conversacion.generar',return_value=datos):
            completa=responder_conversacion(h)
        with patch('ml.conversacion.generar_flujo',return_value=(c for c in datos)) as modelo:
            parcial=''.join(responder_conversacion_stream(h))
        self.assertEqual(completa,parcial)
        self.assertEqual(modelo.call_count,1)
        self.assertLessEqual(completa.count('?'),1)

    def test_preguntas_contextuales_no_duplican_informacion_ya_dada(self):
        plan=preparar_apoyo([usuario('Me duele la cabeza desde ayer')],{})
        self.assertEqual(plan['pregunta'],'')
        self.assertNotIn('pattern',_opciones_respuesta([usuario('Hoy fue un día raro')])['formato']['properties']['respuesta'])
