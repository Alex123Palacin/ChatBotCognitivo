# Chatbot Cognitivo

Conversación académica libre con cuentas propias, un mismo historial y cuatro sesiones semanales. React muestra el chat y el panel administrativo; Django guarda los datos y controla las fechas; Ollama responde y analiza mensajes usando el modelo local `deepseek-r1:8b`.

## Dominio previsto

El dominio principal del proyecto es **https://chatcognitivo.tech**, con acceso administrativo en **https://chatcognitivo.tech/administrador**. Django admite `chatcognitivo.tech` y `www.chatcognitivo.tech`, y confía en sus orígenes HTTPS para las operaciones con CSRF. El desarrollo local sigue funcionando con las direcciones habituales.

El frontend utiliza rutas relativas `/api/`. Al publicar, el servidor debe servir la compilación `frontend/dist`, enviar `/api/` al backend y devolver `index.html` para las rutas de React, como `/chat` y `/administrador`. El proxy de Vite solo corresponde al desarrollo.

Esta configuración prepara el código; no registra el dominio ni modifica DNS. Para publicarlo falta elegir el hosting, apuntar los registros DNS a ese servicio y activar HTTPS. Si se utiliza `www`, también debe configurarse en DNS y conviene redirigirlo al dominio principal. El servidor debe poder acceder a Ollama y mantener ejecutándose el procesador semanal.

El despliegue ya está definido en `docker-compose.yml`: frontend con Nginx, backend con Gunicorn, procesador semanal y Ollama. Compose utiliza `DEBUG=False`, claves privadas y almacenamiento persistente. Consulta [DESPLIEGUE.md](DESPLIEGUE.md) para publicarlo en Dokploy; `iniciar.ps1` conserva su funcionamiento local.

Ejecuta `py preparar_despliegue.py` para generar `.env`. Ese archivo contiene las claves que debes copiar en **Environment** de Dokploy y está excluido de Git. El administrador utiliza `DJANGO_ADMIN_PASSWORD`. La plantilla genera una contraseña privada; en este despliegue el propietario solicitó expresamente `admin/admin`, mediante la excepción documentada en [DESPLIEGUE.md](DESPLIEGUE.md).

## Iniciar en Windows

Con Ollama abierto y las dependencias ya instaladas, desde la raíz:

```powershell
.\iniciar.ps1
```

Abre **http://localhost:5173**. El script aplica las migraciones, inicia Django junto al procesador de semanas y ejecuta Vite. Conserva esa terminal abierta. `Ctrl+C` detiene los procesos que inició. Los registros del backend están en `logs/` y no se suben a Git.

También puedes usar dos terminales:

```powershell
# Terminal 1, desde backend/principal
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py iniciar_backend
```

```powershell
# Terminal 2, desde frontend
npm run dev
```

`iniciar_backend` inicia el servidor en `127.0.0.1:8000` y el procesador automático. `runserver` por sí solo sirve la API, pero necesita que ejecutes aparte `manage.py procesar_semanas --continuo` para analizar y cerrar semanas. El cierre no depende de que el estudiante vuelva a entrar.

Si faltan dependencias, desde `backend`: `py -m venv .venv` y `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`; desde `frontend`: `npm install`. No necesitas descargar otro modelo.

## Estudiantes y administrador

Los estudiantes se registran en `/registro` con nombre o apodo, una dirección `@gmail.com` y una contraseña propia. No es la contraseña de Gmail: esta cuenta pertenece al proyecto. Todavía no existe verificación de propiedad del correo ni acceso OAuth de Google.

El panel está en **http://localhost:5173/administrador**. Sin sesión muestra su propia pantalla de acceso: **usuario `admin`, contraseña `admin`**, como se solicitó para desarrollo local. Django prepara esta cuenta al iniciar con `iniciar_backend` o `runserver`; no vuelve a cambiar la contraseña de una cuenta existente. La contraseña se guarda mediante hash y el usuario tiene permisos del panel, sin permisos de superusuario. Las rutas anteriores `/admin/...` redirigen a `/administrador/...`.

Los estudiantes siguen entrando por `/login` con su Gmail. El panel comprueba el rol administrativo en el servidor, además de proteger las rutas de React.

Al seleccionar un estudiante aparecen el primer y último mensaje, tiempo transcurrido desde el inicio, días con conversación, cantidad de mensajes y análisis pendientes. **No se interpreta el tiempo transcurrido como tiempo de conversación continua.** También se puede filtrar el listado por actividad reciente.

El detalle muestra un **reporte provisional de la semana en curso**, con citas y cobertura de los siete indicadores, sin esperar al cierre. Un aviso distingue falta de mensajes, análisis pendiente, falta de evidencia y cobertura parcial/completa. Tener una cita permite describir ese indicador; cubrir los siete no convierte el reporte en una medición validada de estrés. Los reportes semanales acumulados siguen disponibles en el mismo detalle.

## Las cuatro semanas

La primera semana empieza con el primer mensaje guardado. Cada semana dura exactamente siete días; las siguientes mantienen esas fechas aunque el estudiante no converse. Por ejemplo, un primer mensaje el 8 de octubre a las 10:00 inicia la semana 1 hasta el 15 a las 10:00; en ese instante empieza la semana 2. Al cumplir 28 días termina el programa y el historial queda disponible para lectura. Las fechas se muestran con la hora de Lima.

El estudiante puede hablar uno o varios días. Todos sus mensajes de ese periodo se analizan; no tiene que completar preguntas ni conversar todos los días. Las semanas sin mensajes también generan un reporte, indicando falta de información.

El procesador revisa los vencimientos periódicamente, guarda un único reporte por semana y reintenta análisis que fallaron. Mientras falte analizar un mensaje, el reporte aparece **en proceso**. Si el equipo o el backend estaban apagados, procesa los vencimientos al iniciar nuevamente, conservando las fechas originales. Para funcionamiento permanente, el backend y este procesador necesitan permanecer encendidos en un servidor.

## Relación con la tesis

Se usan las tres dimensiones y siete indicadores de la tabla proporcionada:

| Dimensión | Indicadores |
| --- | --- |
| Estímulos estresores | Sobrecarga académica; presión del tiempo |
| Síntomas | Síntomas físicos; síntomas psicológicos |
| Estrategias de afrontamiento | Planificación; automotivación; búsqueda de soporte |

La IA conversa con empatía y puede hacer una pregunta breve si el contexto lo permite. El análisis se ejecuta por separado: identifica afirmaciones del estudiante, las vincula a un indicador y extrae una cita literal. El código redacta una observación conservadora a partir de esa cita y comprueba que realmente esté en el mensaje de origen antes de guardarla. Las sugerencias del asistente no se toman como experiencias del estudiante.

Los reportes muestran evidencia de dificultades, recursos de afrontamiento o negaciones explícitas, con su fecha y mensaje de origen. Las conclusiones conservan distintas señales de la semana y no suponen que una mención posterior significa mejoría o empeoramiento. Sin respaldo, el indicador figura como **sin información suficiente**.

**Esto es una descripción cualitativa orientativa de conversaciones.** Eliminar el cuestionario cambia el procedimiento de la tabla: no se aplica el inventario SISCO ni su escala ordinal 1–5, y no se genera un nivel clínico de estrés. El número de mensajes o evidencias tampoco mide intensidad. Para usarlo como instrumento de investigación se debe definir y validar este procedimiento conversacional con el asesor de la tesis.

No se entrenaron los pesos del modelo, no se hizo fine-tuning y no hay un conjunto de entrenamiento nuevo. Se usa tu modelo descargado con instrucciones para conversar y un esquema JSON para extraer evidencia. La salida estructurada facilita validar el formato, pero no garantiza que todas las interpretaciones sean correctas. También puede omitir menciones: en una prueba no extrajo dos negaciones explícitas de síntomas; esos indicadores quedaron sin información, sin atribuirles estrés bajo.

El chat usa un modo directo del mismo modelo para evitar la demora del razonamiento previo, manteniendo las instrucciones y los turnos recientes. En una comparación local, el mismo mensaje académico pasó de 63,23 a 8,26 segundos; las otras pruebas tardaron entre 2,41 y 10,03 segundos. Son tiempos observados, no una garantía: cambian según la carga del equipo y el contexto. El análisis de evidencia sigue ejecutándose por separado. `OLLAMA_CHAT_DIRECT=false` restaura la conversación nativa.

## Organización y comprobaciones

Consulta [backend/README.md](backend/README.md) y [frontend/README.md](frontend/README.md) para conocer los archivos, endpoints y responsabilidades.

```powershell
# Desde backend/principal, pruebas con Ollama sustituido por mocks
..\.venv\Scripts\python.exe manage.py test usuarios chat reportes ml
..\.venv\Scripts\python.exe manage.py check

# Desde frontend
npm run build
npm run lint
npm run test:api
```

Las contraseñas se guardan mediante el sistema de hash de Django. La autenticación usa cookies de sesión y CSRF; la API verifica permisos aunque alguien intente saltarse las rutas de React. Los datos locales están en `backend/principal/db.sqlite3`, excluido de Git. Esta configuración es para desarrollo local; las opciones del despliegue deben configurarse para el servidor definitivo.
