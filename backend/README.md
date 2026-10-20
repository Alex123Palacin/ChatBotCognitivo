# Backend del Chatbot Cognitivo

Django guarda cuentas, conversaciones, semanas, evidencias y reportes en SQLite. La carpeta `principal/ml/` sigue siendo un paquete Python normal: **no está en INSTALLED_APPS ni tiene tablas o migraciones**.

## Ejecutar

Con Ollama abierto, desde `backend/principal`:

```powershell
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py iniciar_backend
```

Este comando inicia Django en `127.0.0.1:8000` y el procesador semanal. Desde `frontend`, en otra terminal: `npm run dev`. El script `iniciar.ps1` de la raíz hace ambos pasos automáticamente.

En **http://localhost:5173/administrador** entra con usuario **`admin`** y contraseña **`admin`**. `iniciar_backend` y `runserver` preparan esta cuenta automáticamente para desarrollo (`DEBUG=True`). El comando `manage.py preparar_admin` también permite prepararla manualmente: es idempotente y conserva contraseñas/permisos existentes. No hay consultas de creación al cargar las apps. La cuenta nueva tiene permisos administrativos del panel, sin permisos de superusuario.

## Carpetas y archivos

Todas estas rutas se encuentran dentro de `backend/principal/`:

| Ruta | Responsabilidad |
| --- | --- |
| `manage.py` | Ejecuta comandos Django, migraciones, pruebas y servidores. |
| `principal/settings.py` | Base de datos, apps, zona horaria, cookies, CSRF y configuración de Ollama. |
| `principal/urls.py` | Conecta las rutas REST con las vistas. |
| `principal/http.py` | Comprueba métodos, autenticación y rol; devuelve errores JSON. |
| `usuarios/models.py` | Perfil del usuario: inicio del programa, última actividad y reserva de respuesta en curso. El usuario y su contraseña pertenecen al sistema de autenticación de Django. |
| `usuarios/views.py` | Registro, login, logout, usuario actual y token CSRF. El registro siempre crea un estudiante. |
| `usuarios/management/commands/crear_admin.py` | Crea el acceso administrativo pidiendo la contraseña sin mostrarla. |
| `usuarios/management/commands/preparar_admin.py` | Prepara la cuenta local solicitada `admin/admin` si todavía no existe. |
| `usuarios/management/commands/runserver.py` | Prepara el administrador antes de iniciar el servidor de desarrollo. |
| `chat/models.py` | Mensaje persistido, autor, semana, clave del envío, respuesta asociada y estado del análisis. |
| `chat/views.py` | API del historial y envío de mensajes del estudiante autenticado. |
| `chat/services.py` | Guarda antes de consultar Ollama, evita envíos duplicados, mantiene una sola respuesta por alumno y prepara historial/contexto. |
| `sesiones/models.py` | Semana numerada, comienzo, fin y estado. |
| `sesiones/services.py` | Crea cuatro periodos de siete días y actualiza las semanas activas/cerradas. |
| `sesiones/management/commands/procesar_semanas.py` | Proceso periódico que analiza mensajes pendientes y genera/actualiza reportes al vencer la semana. |
| `sesiones/management/commands/iniciar_backend.py` | Arranca servidor y procesador juntos para desarrollo. |
| `reportes/models.py` | Evidencia asociada al mensaje de origen y un único reporte por semana. |
| `reportes/services.py` | Valida/persiste evidencia, reintenta análisis, compone reportes y conclusiones por indicador. |
| `reportes/views.py` | Listado de alumnos, sus semanas/reportes y detalle de un reporte; solo para administradores. |
| `ml/ollama.py` | Cliente HTTP local de Ollama; controla contexto, formato JSON, tiempo de espera y errores. Oculta el razonamiento interno. |
| `ml/conversacion.py` | Instrucciones empáticas para la conversación libre. Sin fases de cuestionario. |
| `ml/analisis.py` | Define dimensiones/indicadores, extrae citas con un esquema JSON y sintetiza observaciones. |
| `*/migrations/` | Cambios de estructura de las tablas; sí se versionan. |
| `usuarios/tests.py`, `chat/tests.py`, `reportes/tests.py`, `ml/tests.py` | Comprueban permisos, sesiones, reintentos, semanas, reportes y validación del análisis. |

## Recorrido de un mensaje

1. La cookie de Django identifica al estudiante; no se acepta un identificador de otro alumno enviado por el navegador.
2. Se valida el texto y su `clave_envio`. La misma clave permite reintentar sin duplicar el mensaje.
3. Se guarda el mensaje. Si es el primero, se crean las cuatro semanas.
4. Se libera la transacción de base de datos antes de llamar a Ollama.
5. Ollama recibe conversación reciente, nombre o apodo, semana y contexto anterior sustentado en mensajes/citas. Su respuesta se guarda y se devuelve a React.
6. El procesador analiza el mensaje del estudiante por separado. Las respuestas del asistente nunca se convierten en evidencia.
7. Al vencer la semana se crea el reporte aunque el estudiante no vuelva a entrar. Si faltan análisis, aparece en proceso y se actualiza al completarlos.

Si el modelo falla, el mensaje permanece guardado. Si Django reinicia durante una respuesta, una reserva temporal vence y permite recuperar el envío. Las conversaciones ya no caducan por dos horas de inactividad.

## Análisis y reportes

Cada evidencia contiene indicador, cita literal, observación y una señal:

- `dificultad`: problema que el estudiante relata.
- `recurso`: estrategia de afrontamiento que dice utilizar.
- `ausencia_explicita`: algo que niega o un recurso cuya ausencia expresa. La observación explica qué negó.

Una cita debe existir exactamente en el mensaje de origen. No se usan frases inventadas, supuestas experiencias a partir de consejos ni indicadores desconocidos. La validación comprueba estructura y trazabilidad; no reemplaza la revisión de las interpretaciones del modelo.

Cada reporte contiene periodo, número de mensajes, resumen, las tres dimensiones, sus siete indicadores, conclusiones, citas, fechas y nota sobre información limitada. Sin información no se asigna estrés bajo. Los conteos describen cuánto material hay; no son un puntaje de estrés.

La consulta del alumno incluye `reporte_actual`, una lectura provisional de la semana vigente (o de la semana 4 si terminó el programa). Reutiliza únicamente evidencias guardadas: abrir el panel no dispara Ollama ni crea un reporte semanal anticipado. `cobertura` indica cuántos indicadores/dimensiones tienen citas, cuáles faltan y cuántos mensajes esperan análisis. `puede_describir_indicadores` significa que hay al menos un indicador sustentado; nunca equivale a una evaluación SISCO suficiente. Las métricas del alumno abarcan todo el programa: primer/último mensaje, días distintos con conversación y mensajes analizados/pendientes. Las consultas administrativas no escriben en las tablas.

El cuestionario de 14 preguntas fue eliminado. Esta versión **no aplica SISCO ni su escala 1–5**. Conserva las dimensiones/indicadores proporcionados en la tesis mediante un procedimiento cualitativo que todavía requiere validación metodológica para investigación.

## Endpoints

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | `/api/csrf/` | Token de protección CSRF. |
| POST | `/api/auth/registro/` | Nombre o apodo, Gmail y contraseña propia. |
| POST | `/api/auth/login/` | Iniciar sesión con `username` y `password`; también acepta `email` para compatibilidad. |
| POST | `/api/auth/logout/` | Cerrar sesión. |
| GET | `/api/auth/me/` | Usuario actual o null. |
| GET | `/api/chat/` | Historial, semanas y respuesta pendiente del propio alumno. |
| POST | `/api/chat/` | `mensaje` y `clave_envio` UUID. |
| POST | `/api/chat/flujo/` | Mismos datos; devuelve NDJSON con fragmentos y estado final. |
| GET | `/api/admin/alumnos/` | Estudiantes y actividad reciente. |
| GET | `/api/admin/alumnos/<id>/` | Alumno, métricas, cuatro semanas, reporte provisional y reportes acumulados. |
| GET | `/api/admin/reportes/<id>/` | Reporte con evidencias y conclusiones. |

`en_linea` indica actividad autenticada durante los últimos cinco minutos, y el logout lo desactiva. No significa una conexión permanente comprobada.

## Ollama y entrenamiento

Se usa `deepseek-r1:8b` ya descargado. No se modificaron sus pesos, no hubo fine-tuning, no se entrenó con el PDF y no se incorporó un dataset. Las instrucciones y los indicadores son contexto de inferencia.

Variables opcionales: `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_NUM_GPU`, `OLLAMA_NUM_CTX`, `OLLAMA_ANALYSIS_TIMEOUT`, `OLLAMA_CHAT_DIRECT`, `OLLAMA_CHAT_MAX_TOKENS` y `OLLAMA_KEEP_ALIVE`. La configuración local usa 16 capas de GPU y contexto de 4096 tokens; Compose usa CPU. Algunas versiones de DeepSeek continúan razonando internamente aunque se solicite `think:false`; por eso se conserva la plantilla directa comprobada.

El chat tiene 180 segundos de espera; el análisis en segundo plano dispone de 360 segundos. Si un estudiante envía un mensaje durante una inferencia analítica, el procesador cierra esa conexión para ceder el modelo al chat y reintenta el análisis después. Esta prioridad se aplica a todos los estudiantes que comparten el modelo, no solo al dueño del mensaje analizado.

El analizador y la conversación usan por defecto salida directa mediante [la API `/api/generate` de Ollama](https://docs.ollama.com/api/generate), con la plantilla verificada del `deepseek-r1:8b` instalado. La plantilla inicia la respuesta después de un bloque de pensamiento vacío. El chat envía instrucciones escolares compactas y hasta ocho mensajes recientes, conservando íntegro el último mensaje. Su presupuesto directo es como máximo 192 tokens, aunque las variables antiguas contengan 512; puede configurarse un límite inferior. Las etiquetas de pensamiento y el campo `thinking` no forman parte del mensaje visible. Una respuesta incompleta no se guarda como terminada.

`/api/chat/flujo/` transmite eventos `inicio`, `fragmento`, `estado` y `error` como líneas JSON. Comparte autenticación, CSRF, reserva por estudiante, prioridad sobre el worker e idempotencia con `/api/chat/`. Al desconectarse el consumidor se cierra Ollama y se libera la reserva; el mensaje del alumno permite un reintento con la misma clave. El frontend muestra el texto parcial y lo sustituye por el historial guardado cuando llega `estado`.

`precalentar_modelo` carga el modelo y procesa un token de las instrucciones comunes antes de iniciar Gunicorn; esa salida se descarta y no crea usuarios ni mensajes. En desarrollo se ejecuta en segundo plano al iniciar `runserver`. El valor predeterminado `OLLAMA_KEEP_ALIVE=-1` evita descargar el modelo de memoria durante las pausas. Se envía como número a la API para ser compatible con Ollama 0.18.2. Consulta la [documentación de precarga y keep_alive](https://docs.ollama.com/faq).

Puedes establecer `OLLAMA_CHAT_DIRECT=false` para restaurar `/api/chat` de Ollama con su presupuesto nativo de 1800 tokens, o `OLLAMA_ANALYSIS_DIRECT=false` para usar el modo nativo en el análisis. Los ejemplos ayudan a clasificar, pero no entrenan los pesos. El analizador mantiene su esquema y citas validadas. Mostrar texto progresivamente reduce la espera hasta ver la respuesta; la duración completa sigue dependiendo de la longitud, el modelo y el hardware.

La extracción utiliza el campo `format` de [las salidas estructuradas oficiales de Ollama](https://docs.ollama.com/capabilities/structured-outputs). Django valida nuevamente la cita y el indicador antes de guardar.

## Procesamiento y pruebas

```powershell
# Una pasada o ejecución continua
..\.venv\Scripts\python.exe manage.py procesar_semanas
..\.venv\Scripts\python.exe manage.py procesar_semanas --continuo --intervalo 15

# Comprobar el proyecto
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test usuarios chat reportes ml
```

Los tests sustituyen Ollama para probar de forma repetible los permisos y la lógica de almacenamiento. También se probó el modelo real con relatos de dos y siete indicadores, negaciones, ficción y una lesión deportiva, además del recorrido HTTP hasta el reporte automático. Las pruebas reales son una comprobación limitada, no una validación científica: el caso de negaciones omitió dos menciones de ausencia de síntomas, que quedaron sin información. Las citas permiten revisar qué se extrajo y qué se interpretó.

Mantén activo el procesador para los cierres automáticos. Al reiniciar, procesa las semanas vencidas sin alterar sus fechas. El archivo SQLite y los registros están excluidos de Git; conserva copias de tus datos si necesitas respaldarlos.
