# Abrir Chatbot Cognitivo en Windows

## 1. Instalar estos programas una sola vez

- [Python para Windows](https://www.python.org/downloads/windows/): se recomienda **Python 3.14**, probado en este proyecto. Durante la instalación, activa **Add Python to PATH** si aparece. El proyecto necesita Python 3.12 o superior.
- [Node.js](https://nodejs.org/en/download/): instala **Node.js 24 LTS** con las opciones predeterminadas; incluye npm.
- [Ollama para Windows](https://ollama.com/download/windows): instala la aplicación. El modelo se ejecuta en tu computadora.

Después de instalarlos, cierra y vuelve a abrir la carpeta del proyecto. No necesitas configurar Docker, PostgreSQL, claves del VPS ni cuentas de servicios de IA para este inicio local.

## 2. Abrir el programa

1. Descarga o clona **el proyecto completo**. Si es un ZIP, extrae su contenido en una carpeta; no ejecutes archivos desde dentro del ZIP.
2. Abre la carpeta principal `ChatBotCognitivo`.
3. Haz **doble clic en `iniciar.bat`**. No abras directamente `iniciar.ps1` con doble clic, porque Windows puede mostrarlo en un editor.
4. Espera mientras la ventana prepara el programa. El navegador se abrirá automáticamente en **http://localhost:5173** cuando la interfaz pueda comunicarse con el backend.

La primera vez el inicio crea el entorno Python, instala las dependencias, inicia Ollama si hace falta y descarga `deepseek-r1:8b` si todavía no está instalado. **La descarga del modelo ocupa aproximadamente 5 GB y necesita Internet.** Puede tardar varios minutos. Las siguientes veces se reutilizan el modelo y las dependencias.

También se prepara automáticamente la base SQLite local y se inicia el procesador de análisis y cierres semanales. La velocidad de respuesta de la IA depende del equipo.

## 3. Entrar y cerrar

- Estudiantes: crear una cuenta o iniciar sesión desde la pantalla del programa.
- Administración: **http://localhost:5173/administrador**. En una instalación nueva, usuario **admin** y contraseña **admin**. Si esa cuenta local ya existía, se conserva su contraseña.
- Mientras uses el programa, **deja abierta la ventana de inicio**.
- Para apagarlo, vuelve a esa ventana y **presiona ENTER**. Se cierran los procesos que abrió esta ejecución. Si Ollama ya estaba abierto antes, se conserva.

Los datos quedan en `backend/principal/db.sqlite3` y permanecen al cerrar. Una copia nueva del repositorio comienza sin los alumnos, conversaciones ni reportes del sitio desplegado.

## Si aparece un error

La ventana conserva el mensaje para leerlo. Revisa que estén instalados los tres programas y que no haya otra ventana del proyecto abierta. Los detalles están en `logs/backend-error.log`, `logs/frontend-error.log` y, cuando el iniciador abrió Ollama, `logs/ollama-error.log`.

Si Windows bloquea el script por provenir de un ZIP descargado, revisa **Propiedades → Desbloquear** en el ZIP de confianza antes de extraerlo de nuevo. El iniciador usa `RemoteSigned` solo para su proceso; no cambia permanentemente la política de PowerShell del equipo.

## Para quien entrega el proyecto

Sube a Git `iniciar.bat`, `iniciar.ps1`, este archivo, los requisitos de Python, `package.json`, `package-lock.json` y el resto del código y migraciones. Los archivos de inicio están permitidos expresamente en `.gitignore`.

No copies `.venv`, `node_modules`, `.env`, `secrets`, bases de datos ni registros: el inicio crea las dependencias locales y esos archivos privados siguen excluidos de Git.

Para comprobar el arranque sin abrir el navegador, desde PowerShell puedes ejecutar `./iniciar.ps1 -Verificar`. Esta opción prepara y arranca los servicios reales, comprueba la API a través de React y los apaga al terminar. También funciona `iniciar.bat -Verificar`.
