from types import SimpleNamespace
from django.test import SimpleTestCase
from .frecuencias import frecuencia_explicita, frecuencia_periodo, frecuencia_respuesta


class FrecuenciasTests(SimpleTestCase):
    def evidencia(self, cita, indicador='presion_tiempo', senal='dificultad', contexto=None):
        mensaje = SimpleNamespace(contenido=contexto or cita, remitente='usuario', analisis_estado='listo')
        return SimpleNamespace(cita=cita, mensaje=mensaje, indicador=indicador, senal=senal)

    def test_cinco_frecuencias_literalmente_declaradas(self):
        for texto, valor in [('Nunca', 1), ('Rara vez', 2), ('Algunas veces', 3), ('Casi siempre', 4), ('Siempre', 5)]:
            with self.subTest(texto=texto):
                e = self.evidencia(f'Esta semana {texto.lower()} me falta tiempo para las tareas.', senal='ausencia_explicita' if valor == 1 else 'dificultad')
                self.assertEqual(frecuencia_explicita(e), valor)

    def test_frecuencia_de_recurso_no_frecuencia_de_dificultad(self):
        e = self.evidencia('Esta semana casi siempre organizo mis tareas.', 'planificacion', 'recurso')
        self.assertEqual(frecuencia_explicita(e), 4)
        e.senal = 'dificultad'
        self.assertIsNone(frecuencia_explicita(e))
        e = self.evidencia('Esta semana nunca pido ayuda para las tareas.', 'busqueda_soporte', 'ausencia_explicita')
        self.assertEqual(frecuencia_explicita(e), 1)

    def test_ambiguedades_otro_periodo_otro_sujeto_y_negaciones(self):
        for cita in [
            'Siempre me falta tiempo.',
            'Esta semana no siempre me falta tiempo.',
            'Esta semana casi nunca me falta tiempo.',
            'Esta semana creo que siempre me falta tiempo.',
            'Esta semana mi amigo siempre tiene muchas tareas.',
            'Esta semana digo que antes siempre me falta tiempo.',
            'Esta semana cuando hay examen siempre me falta tiempo.',
            'Esta semana siempre me falta tiempo, pero rara vez me falta tiempo para otra tarea.',
            'Esta semana no me falta tiempo.',
            'Esta semana tengo cinco tareas y envié muchos mensajes.',
        ]:
            with self.subTest(cita=cita):
                self.assertIsNone(frecuencia_explicita(self.evidencia(cita)))

    def test_no_usa_frecuencia_de_otra_clausula_o_del_asistente(self):
        e = self.evidencia('Esta semana siempre juego y me falta tiempo para la tarea.')
        self.assertIsNone(frecuencia_explicita(e))
        e = self.evidencia('Esta semana siempre me falta tiempo para las tareas.')
        e.mensaje.remitente = 'asistente'
        self.assertIsNone(frecuencia_explicita(e))
        e.mensaje.remitente = 'usuario'
        e.mensaje.analisis_estado = 'pendiente'
        self.assertIsNone(frecuencia_explicita(e))
        e.mensaje.analisis_estado = 'listo'
        e.mensaje.contenido = 'Un texto diferente'
        self.assertIsNone(frecuencia_explicita(e))

    def test_no_atribuye_enfermedad_o_lesion_al_colegio(self):
        cita = 'Esta semana siempre me duele la cabeza por un resfrío, no por el colegio.'
        self.assertIsNone(frecuencia_explicita(self.evidencia(cita, 'sintomas_fisicos')))
        cita = 'Esta semana algunas veces me duele la cabeza por estudiar.'
        self.assertEqual(frecuencia_explicita(self.evidencia(cita, 'sintomas_fisicos')), 3)

    def test_conflicto_no_se_promedia_ni_se_cambia_a_cero(self):
        a = self.evidencia('Esta semana siempre me falta tiempo para las tareas.')
        b = self.evidencia('Esta semana rara vez me falta tiempo para las tareas.')
        self.assertEqual(frecuencia_periodo([a, b], 'presion_tiempo'), 'Sin información')
        self.assertEqual(frecuencia_periodo([], 'presion_tiempo'), 'Sin información')
        self.assertEqual(frecuencia_periodo([a, a], 'presion_tiempo'), 5)

    def test_respuesta_breve_requiere_pregunta_semanal_univoca(self):
        mensaje = self.evidencia('Casi siempre.').mensaje
        self.assertEqual(frecuencia_respuesta(mensaje), {})
        mensaje._pregunta_frecuencia = '¿Con qué frecuencia te falta tiempo para las tareas esta semana?'
        self.assertEqual(frecuencia_respuesta(mensaje), {'presion_tiempo': 4})
        for pregunta in [
            '¿Con qué frecuencia te falta tiempo para las tareas?',
            '¿Con qué frecuencia te falta tiempo esta semana y pides ayuda para las tareas?',
            '¿Con qué frecuencia no organizas tus tareas esta semana?',
            '¿Con qué frecuencia esta semana pides ayuda para las tareas? ¿Siempre?',
        ]:
            mensaje._pregunta_frecuencia = pregunta
            self.assertEqual(frecuencia_respuesta(mensaje), {})
