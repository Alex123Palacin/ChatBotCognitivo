# Backend del Chatbot Cognitivo

Django recibe los mensajes de React y consulta el modelo local `deepseek-r1:8b` de Ollama.
La carpeta `principal/ml/` es un paquete Python normal, **no una app Django**: no está en
`INSTALLED_APPS`, no tiene modelos ni migraciones.

## Iniciar

Desde `backend/`, con Ollama abierto y el modelo ya descargado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd principal
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

Desde `frontend/`, en otra terminal: `npm run dev`. Abre `http://localhost:5173/chat`.
Vite reenvía `/api/` a Django; el navegador no consulta directamente Ollama.

Configuración en `principal/settings.py`:

- `OLLAMA_MODEL`: `deepseek-r1:8b` (también admite una variable de entorno).
- `OLLAMA_URL`: `http://127.0.0.1:11434` (también admite una variable de entorno).
- `OLLAMA_TIMEOUT`: 180 segundos.
- `num_predict`: 1400 en `ml/ollama.py`. El modelo puede consumir parte del presupuesto
  en razonamiento interno; este no se envía al navegador.

## Responsabilidades

| Archivo | Responsabilidad |
| --- | --- |
| `principal/ml/ollama.py` | Envía el historial a Ollama, define las instrucciones del asistente y trata los errores del modelo. |
| `principal/ml/conversacion.py` | Controla presentación, conversación, cuestionario, pausas y resumen. La IA no decide el orden ni cambia los puntajes. |
| `principal/ml/cuestionario.py` | Contiene las 14 preguntas, las opciones de frecuencia y el cálculo de promedios. |
| `principal/ml/tests.py` | Prueba cálculos, omisiones, transiciones, seguridad básica y endpoints con Ollama sustituido por un mock. |
| `principal/principal/chat_views.py` | Recibe JSON, valida entradas y guarda temporalmente el estado de cada conversación. |
| `principal/principal/urls.py` | Define los endpoints. |

## Recorrido de la conversación

1. El estudiante escribe. Ollama responde y se pregunta cómo desea que lo llamen.
2. Apodo opcional. Puede elegir **Prefiero no decirlo**.
3. Grado: **5.º de secundaria**, **Otro grado** o **Prefiero no decirlo**.
4. Pregunta abierta: **¿Cómo te está yendo con tus estudios y qué te preocupa más estos días?**
5. La IA reconoce su contexto. El estudiante elige **Empezar cuestionario** o **Seguir conversando**.
6. Si acepta, responde las 14 preguntas sobre **las últimas dos semanas**.
7. Después de las preguntas 4 y 8 se ofrecen dos reflexiones abiertas:
   **¿Qué situación escolar te está generando más presión?** y
   **¿Cómo afectan estas preocupaciones a tu día a día?** Se pueden omitir.
8. Al terminar, se muestran los promedios y una interpretación breve generada por Ollama.
   Se puede seguir conversando sobre el resultado.

En cada pregunta de frecuencia hay siete botones:
**Nunca (1)**, **Rara vez (2)**, **Algunas veces (3)**, **Casi siempre (4)**,
**Siempre (5)**, **Prefiero omitir esta pregunta**, **Pausar cuestionario**.
También se puede escribir el número del 1 al 5 o el nombre de la frecuencia.
El texto libre recibe atención del modelo, pero no se convierte automáticamente en un puntaje.

La pausa permite conversar, retomar donde se quedó o ver un resultado parcial.
“Nuevo chat” y “Limpiar conversación” comienzan de nuevo.

## Las 14 preguntas

Todas empiezan con «¿Con qué frecuencia…?» y se refieren a las últimas dos semanas.

| N.º | Indicador | Pregunta |
| --- | --- | --- |
| 1 | Sobrecarga académica | ¿Con qué frecuencia la cantidad de tareas te ha parecido difícil de manejar? |
| 2 | Sobrecarga académica | ¿Con qué frecuencia has sentido que se juntaban demasiados trabajos o exámenes? |
| 3 | Presión del tiempo | ¿Con qué frecuencia has sentido que te faltaba tiempo para terminar tus tareas? |
| 4 | Presión del tiempo | ¿Con qué frecuencia los plazos de entrega te han generado presión? |
| 5 | Síntomas físicos | ¿Con qué frecuencia has tenido dificultad para dormir al pensar en tus estudios? |
| 6 | Síntomas físicos | ¿Con qué frecuencia has notado tensión o cansancio físico en momentos de preocupación por tus estudios? |
| 7 | Síntomas psicológicos | ¿Con qué frecuencia te has sentido preocupado o nervioso por tus responsabilidades escolares? |
| 8 | Síntomas psicológicos | ¿Con qué frecuencia las preocupaciones escolares te han dificultado concentrarte? |
| 9 | Planificación | ¿Con qué frecuencia has organizado un horario para tus tareas y tu descanso? |
| 10 | Planificación | ¿Con qué frecuencia has dividido una tarea grande en pasos pequeños? |
| 11 | Automotivación | ¿Con qué frecuencia has reconocido tus avances, aunque fueran pequeños? |
| 12 | Automotivación | ¿Con qué frecuencia te has animado a seguir intentando después de una dificultad escolar? |
| 13 | Búsqueda de soporte | ¿Con qué frecuencia has pedido ayuda para comprender una tarea o un tema difícil? |
| 14 | Búsqueda de soporte | ¿Con qué frecuencia has hablado con alguien de confianza sobre tus preocupaciones escolares? |

## Cómo se calcula

Este es un **cuestionario exploratorio propio**, basado en los siete indicadores de la tabla
de la tesis. No es una transcripción ni una versión validada del inventario SISCO.
El promedio es un resumen descriptivo de respuestas ordinales; no tiene baremos clínicos.

- Cada indicador promedia sus dos respuestas: `(respuesta 1 + respuesta 2) / 2`.
- Estímulos estresores: promedio de las preguntas 1–4.
- Síntomas: promedio de las preguntas 5–8.
- Estrategias de afrontamiento: promedio de las preguntas 9–14.
- Los promedios se redondean a dos decimales, en una escala de 1 a 5.
- Solo se calcula un promedio si todas las preguntas de ese indicador o dimensión tienen respuesta.
  Una omisión se conserva como `null`; nunca como cero. Se muestra **Incompleto**.
- Una puntuación mayor en estresores/síntomas indica mayor frecuencia reportada.
- Una puntuación mayor en afrontamiento indica mayor frecuencia de uso de estrategias.
  **No indica mayor estrés**. No se invierte ni se mezcla con las otras dimensiones.
- No se calcula un puntaje global, porcentaje de estrés ni nivel leve/moderado/severo.
- Apodo, grado, conversación y reflexiones no añaden puntos. La IA solo usa ese contenido como contexto.

Ejemplo: sobrecarga con respuestas 4 y 5 da **4.5/5**. Planificación con respuestas
2 y 3 da **2.5/5**. Son frecuencias de aspectos diferentes, no probabilidades ni diagnósticos.

Los datos estructurados siempre proceden de Python. La interpretación en lenguaje natural
procede de Ollama y puede contener errores. Si la IA falla al interpretar el resultado,
los puntajes calculados siguen disponibles y se informa de ello.

Esta etapa no incluye medición pretest/postest ni demuestra una reducción del estrés.

## API REST

- `GET /api/csrf/`: obtiene el token CSRF.
- `POST /api/chat/`: procesa un mensaje o una opción.
- `DELETE /api/chat/<sesion_id>/`: elimina la conversación temporal.

Primer mensaje:

```json
{"sesion_id": null, "mensaje": "Hola, tengo varios exámenes", "pregunta_id": null}
```

Respuesta a una opción (usar el identificador de sesión devuelto por el servidor):

```json
{"sesion_id": "identificador_de_32_caracteres", "pregunta_id": "sobrecarga_1", "opcion": "4", "mensaje": "Casi siempre (4)"}
```

La respuesta incluye `sesion_id`, `contenido`, `pregunta` (opciones y progreso) y,
al finalizar, `resultado`. La API valida el identificador de la pregunta para evitar
aplicar una respuesta antigua a otra pregunta.

Los POST y DELETE requieren el encabezado `X-CSRFToken` y la cookie que se obtiene con el GET.
Errores: 400 entrada inválida; 403 CSRF; 409 otra respuesta en curso; 410 sesión caducada;
503 Ollama no disponible. El frontend muestra el error y conserva la respuesta para reintentar.

## Estado y límites de esta etapa local

Las conversaciones están en la caché de memoria de Django y caducan tras dos horas sin uso.
No se escriben chats en SQLite ni se usa almacenamiento local del navegador. Al recargar
React se pierde el identificador del chat; al reiniciar Django se pierde la caché.
La caché local está pensada para un único proceso de desarrollo, no para varios workers.
Limpiar el chat cancela la espera en React y solicita su eliminación en Django; una
generación de Ollama ya iniciada puede continuar hasta terminar, sin mostrarse en el chat nuevo.

Hay una regla básica para interrumpir el cuestionario ante algunas expresiones explícitas
de autolesión/peligro y orientar a apoyo humano. No detecta todos los casos ni sustituye
un protocolo profesional para trabajar con estudiantes menores de edad.

## Verificación

Desde `backend/principal/`:

```powershell
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py test ml
```

Referencias de implementación: [API Chat de Ollama](https://docs.ollama.com/api/chat)
y [CSRF de Django](https://docs.djangoproject.com/en/6.0/howto/csrf/).
El instrumento original se identifica en [Barraza, 2007](https://editorialupd.mx/revistas/index.php/ined/article/view/54);
las preguntas breves de esta versión son propias y no se presentan como ese instrumento.
