# Cambios de conversación y conservación

Actualización del 28 de octubre de 2026 en **ChatBotCognitivo**.

## Conversación sin cuatro semanas

La web ya no muestra Semana 1–4, su selector ni el bloqueo por terminar cuatro sesiones. Las conversaciones nuevas tienen un periodo abierto. Continuar una cuenta antigua crea un periodo abierto adicional y conserva las fechas, mensajes y sesiones históricas.

El administrador ve la actividad disponible y sus fechas reales. La descarga incluye el ID del estudiante y siete columnas de frecuencias declaradas de la actividad, sin dividirlas artificialmente en una medición inicial y final. No se inventan puntuaciones ni fechas de una intervención.

Los nombres internos `SesionSemanal` y `procesar_semanas` se conservan por compatibilidad con los datos y el despliegue existentes. No obligan a dividir la interacción de la web en cuatro semanas.

## Aceptación y eliminación de mensajes

El registro consulta los términos vigentes al servidor. El checkbox empieza sin marcar; el backend exige aceptación explícita y la misma versión que se mostró. Se guardan versión y fecha de aceptación.

Los mensajes nuevos de cuentas creadas aceptando esta política caducan a los **30 días desde cada mensaje**. La cuenta permanece. El worker elimina los mensajes vencidos, sus evidencias y los reportes derivados que puedan conservar citas; deja para otro ciclo las respuestas en curso.

Las migraciones no inscriben las cuentas anteriores en esta política ni asignan vencimientos al historial existente. El aviso de las cuentas antiguas refleja esa diferencia. No se ejecutó la limpieza sobre la base real durante estos cambios.

Consultar [RETENCION_30_DIAS.md](RETENCION_30_DIAS.md) para simulación, operación y límites de las copias de seguridad. La limpieza necesita que el servicio `worker` siga funcionando. No elimina descargas o respaldos externos.

## Respuestas y configuración

Se separa `OLLAMA_CHAT_MODEL`, usado para responder al estudiante, de `OLLAMA_MODEL`, usado para extraer evidencias en segundo plano. DeepSeek permanece disponible para el análisis y también puede elegirse para el chat.

El valor predeterminado del chat es `qwen3:1.7b`. La configuración y los resultados de las pruebas, incluidos sus límites, están en [RENDIMIENTO_CHAT.md](RENDIMIENTO_CHAT.md).

Se mantiene la entrega progresiva de texto y la ocultación del razonamiento interno. El servidor precalienta el modelo de conversación real y conserva sus pesos en memoria según `OLLAMA_KEEP_ALIVE`. El contexto recupera ocho mensajes recientes y elimina consultas repetidas por cada semana pasada.

Compose y el inicio local comprueban ambos modelos y descargan únicamente los que falten; si coinciden, no duplican la descarga. Los binarios se guardan fuera de Git. Las pruebas locales de velocidad usan mensajes ficticios y no son una garantía de latencia o de calidad clínica en el VPS.

## Publicar estos cambios

1. Hacer **commit** incluyendo los archivos nuevos, especialmente las tres migraciones de `usuarios`, `chat` y `sesiones`.
2. Hacer **push** a la rama configurada en Dokploy.
3. Ejecutar **Deploy** conservando los volúmenes `datos`, `modelos` y `estaticos`.
4. Esperar a que termine `modelo` si necesita descargar el modelo de conversación. Backend aplica las migraciones con su arranque existente; no requiere recrear la base.
5. Comprobar registro/aceptación, conversación, análisis administrativo y que `worker` permanece activo.

No copiar `.env` al repositorio ni cambiar las contraseñas o claves existentes por este cambio. Para elegir otro modelo de conversación, establecer `OLLAMA_CHAT_MODEL` en Environment y redesplegar. Con Ollama externo, ese servidor también debe disponer de los modelos configurados.

Las comprobaciones se hicieron localmente; no se publicó ni se modificó el servidor desde esta tarea. Docker Compose se validó, pero el motor de Docker Desktop no estaba disponible para reconstruir imágenes en esta computadora.

## Validación realizada

- **137 pruebas de backend correctas** en SQLite temporal, incluyendo preservación de datos al migrar, cuentas, retención, conversación continua, reportes y streaming. Para la pasada completa se utilizó hashing rápido exclusivamente en el proceso de pruebas; también se ejecutaron pruebas de registro y aceptación con el hasher habitual.
- **21 pruebas API de frontend**, lint y compilación de producción correctos.
- **Cinco recorridos de Chrome con API simulada**: registro móvil, fallo de términos, chat abierto, cuenta antigua y administrador; se revisaron capturas sin desbordamientos.
- **Integración real local**: registro con CSRF y aceptación, respuesta progresiva de Ollama, guardado de los dos mensajes y vencimiento de 30 días, en una base temporal. La huella de la base original permaneció igual antes y después.
- Comprobación de migraciones pendientes de generar y configuración Compose CPU/GPU correctas. Las migraciones incluidas deben aplicarse al desplegar; no se ejecutaron sobre la base real durante esta tarea.

## Datos y escenario del 11 de septiembre

Los datos anteriores y la base habitual se conservan. Se preparó un paquete independiente para el **11 de septiembre de 2026, de 1:00 p. m. a 6:00 p. m., hora de Lima**, con 136 cuentas, 136 conversaciones, 7.420 mensajes y 1.144 citas verificadas. Contiene 4 perfiles sin dificultades expresadas, 32 con una, 36 con dos, 36 con tres y 28 con cuatro; el afrontamiento se distribuye como recursos independientes.

La carga se probó sobre una **base local aislada**. Su procedencia y su método de anotación estructurada se conservan internamente; no se atribuyen estos textos ni estas evidencias a participantes reales o a una ejecución de Ollama que no haya ocurrido. No se fabrican aceptaciones de términos ni se modifica la política de cuentas reales.

El ZIP portable, sus instrucciones operativas y los accesos privados están en `entregas_locales/actividad_20260911/`, excluida de Git. Los accesos legibles y la base local no se incluyen en el ZIP. Para revisar la web usar `ver_actividad_local.ps1`; para la operación del servidor consultar [la guía de carga](herramientas/carga_actividad/README.md). El VPS queda pendiente de la ejecución de su operador: no se publicó ni importó este lote desde aquí.

Validación de esta etapa: **160 pruebas de backend correctas**, carga completa e idempotente de las 136 cuentas, consulta de sus 136 análisis, acceso por CSRF, permisos, exportaciones de 100 y 36 cuentas, ciclo del worker sin pendientes ni eliminación de la muestra, y huella de la base habitual sin cambios. Se comprobaron además el cargador portable con configuración de producción y tres recorridos de Chrome con API real local (chat de escritorio, móvil y administración), sin errores de interfaz. No se ejecutó una prueba dentro del VPS.
