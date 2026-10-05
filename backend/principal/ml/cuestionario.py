"""Cuestionario exploratorio propio basado en los indicadores de la tesis.

No reproduce el inventario SISCO ni aplica baremos clínicos.
"""

INDICADORES = {
    "sobrecarga": ("Sobrecarga académica", "estresores"),
    "tiempo": ("Presión del tiempo", "estresores"),
    "fisicos": ("Síntomas físicos", "sintomas"),
    "psicologicos": ("Síntomas psicológicos", "sintomas"),
    "planificacion": ("Planificación", "afrontamiento"),
    "automotivacion": ("Automotivación", "afrontamiento"),
    "soporte": ("Búsqueda de soporte", "afrontamiento"),
}

PREGUNTAS = [
    ("sobrecarga_1", "sobrecarga", "¿Con qué frecuencia la cantidad de tareas te ha parecido difícil de manejar?"),
    ("sobrecarga_2", "sobrecarga", "¿Con qué frecuencia has sentido que se juntaban demasiados trabajos o exámenes?"),
    ("tiempo_1", "tiempo", "¿Con qué frecuencia has sentido que te faltaba tiempo para terminar tus tareas?"),
    ("tiempo_2", "tiempo", "¿Con qué frecuencia los plazos de entrega te han generado presión?"),
    ("fisicos_1", "fisicos", "¿Con qué frecuencia has tenido dificultad para dormir al pensar en tus estudios?"),
    ("fisicos_2", "fisicos", "¿Con qué frecuencia has notado tensión o cansancio físico en momentos de preocupación por tus estudios?"),
    ("psicologicos_1", "psicologicos", "¿Con qué frecuencia te has sentido preocupado o nervioso por tus responsabilidades escolares?"),
    ("psicologicos_2", "psicologicos", "¿Con qué frecuencia las preocupaciones escolares te han dificultado concentrarte?"),
    ("planificacion_1", "planificacion", "¿Con qué frecuencia has organizado un horario para tus tareas y tu descanso?"),
    ("planificacion_2", "planificacion", "¿Con qué frecuencia has dividido una tarea grande en pasos pequeños?"),
    ("automotivacion_1", "automotivacion", "¿Con qué frecuencia has reconocido tus avances, aunque fueran pequeños?"),
    ("automotivacion_2", "automotivacion", "¿Con qué frecuencia te has animado a seguir intentando después de una dificultad escolar?"),
    ("soporte_1", "soporte", "¿Con qué frecuencia has pedido ayuda para comprender una tarea o un tema difícil?"),
    ("soporte_2", "soporte", "¿Con qué frecuencia has hablado con alguien de confianza sobre tus preocupaciones escolares?"),
]

ESCALA = ["Nunca", "Rara vez", "Algunas veces", "Casi siempre", "Siempre"]


def pregunta_actual(estado):
    indice = estado["indice"]
    identificador, indicador, texto = PREGUNTAS[indice]
    return {
        "id": identificador,
        "texto": texto,
        "indicador": INDICADORES[indicador][0],
        "numero": indice + 1,
        "total": len(PREGUNTAS),
        "opciones": [
            {"valor": str(i), "texto": f"{nombre} ({i})"}
            for i, nombre in enumerate(ESCALA, 1)
        ] + [
            {"valor": "omitir", "texto": "Prefiero omitir esta pregunta"},
            {"valor": "pausar", "texto": "Pausar cuestionario"},
        ],
    }


def calcular_resultado(respuestas):
    """Solo calcula promedios completos; una omisión nunca equivale a cero."""
    for identificador, valor in respuestas.items():
        if identificador not in {p[0] for p in PREGUNTAS}:
            raise ValueError("Pregunta desconocida.")
        if valor is not None and (type(valor) is not int or not 1 <= valor <= 5):
            raise ValueError("Las respuestas deben estar entre 1 y 5.")

    def resumen(ids):
        valores = [respuestas.get(i) for i in ids if respuestas.get(i) is not None]
        return {
            "respondidas": len(valores),
            "total": len(ids),
            "promedio": round(sum(valores) / len(valores), 2) if len(valores) == len(ids) else None,
        }

    indicadores = [
        {"id": clave, "nombre": nombre, "dimension": dimension,
         **resumen([p[0] for p in PREGUNTAS if p[1] == clave])}
        for clave, (nombre, dimension) in INDICADORES.items()
    ]
    dimensiones = [
        {"id": clave, "nombre": nombre,
         **resumen([p[0] for p in PREGUNTAS if INDICADORES[p[1]][1] == clave])}
        for clave, nombre in [
            ("estresores", "Estímulos estresores"),
            ("sintomas", "Síntomas"),
            ("afrontamiento", "Estrategias de afrontamiento"),
        ]
    ]
    return {
        "instrumento": "Cuestionario exploratorio de 14 preguntas · versión 1",
        "periodo": "Últimas dos semanas",
        "respondidas": sum(v is not None for v in respuestas.values()),
        "total": len(PREGUNTAS),
        "indicadores": indicadores,
        "dimensiones": dimensiones,
        "respuestas": [
            {"id": p[0], "pregunta": p[2], "valor": respuestas.get(p[0])}
            for p in PREGUNTAS
        ],
        "nota": "Resultado orientativo, no diagnóstico ni puntuación SISCO. En estresores y síntomas, un promedio mayor indica mayor frecuencia reportada. En afrontamiento, indica mayor frecuencia de uso de estrategias; no mayor estrés. No se calcula un puntaje global.",
    }
