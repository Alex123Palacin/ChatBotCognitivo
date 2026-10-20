# Frontend del Chatbot Cognitivo

React, TypeScript, Vite, Tailwind y React Router DOM. Conserva el diseño del chat, sin logo, y añade acceso de estudiantes y un panel administrativo para consultar reportes.

## Ejecutar

```powershell
npm install
npm run dev
```

Abre `http://localhost:5173`. Django debe estar en `127.0.0.1:8000`; Vite reenvía `/api/` hacia él. Con `iniciar.ps1` en la raíz puedes arrancar frontend, backend y procesamiento semanal juntos.

## Rutas

| Ruta | Pantalla |
| --- | --- |
| `/registro` | Crear una cuenta con Gmail y contraseña propia. |
| `/login` | Acceder; el rol determina la pantalla de destino. |
| `/chat` | Chat personal del estudiante. |
| `/administrador` | Login administrativo con usuario y contraseña; muestra el panel cuando la sesión es administrativa. |
| `/administrador/alumnos` | Estudiantes registrados y filtro de actividad reciente. |
| `/administrador/alumnos/:id` | Tiempo desde el inicio, días con conversación, reporte provisional, cuatro semanas y reportes acumulados. |
| `/administrador/alumnos/:id/reportes` | Acceso alternativo al mismo detalle. |
| `/administrador/reportes/:id` | Reporte semanal con dimensiones, indicadores, citas y conclusiones. |
| `/admin/...` | Redirecciones compatibles hacia las rutas `/administrador/...`. |

Las rutas se protegen en React para organizar la navegación. Django también comprueba el rol y el dueño de la conversación: ocultar una pantalla no es la única protección.

## Organización

| Ruta | Responsabilidad |
| --- | --- |
| `src/main.tsx` | Monta React con BrowserRouter y estilos. |
| `src/App.tsx` | Envuelve las rutas en el proveedor de autenticación. |
| `src/routes/AppRoutes.tsx` | Rutas públicas, privadas y redirecciones por rol. |
| `src/pages/` | Arma las pantallas con componentes y hooks. |
| `src/pages/admin/` | Listado, alumno y reporte semanal. |
| `src/pages/admin/LoginAdminPage.tsx` | Acceso administrativo con usuario textual y contraseña. |
| `src/components/auth/` | Marco visual del acceso y proveedor de la sesión actual. |
| `src/components/admin/` | Estructura del panel, alumnos, semanas y evidencia de cada indicador. |
| `src/components/admin/TablaAlumnosComp.tsx` | Tabla de estudiantes con filas y enlaces para abrir su reporte. |
| `src/components/admin/InformacionAlumnoComp.tsx` | Primer/último mensaje, tiempo desde el inicio y días con conversación. |
| `src/components/admin/ReporteActualComp.tsx` | Aviso de cobertura y reporte provisional con citas por indicador. |
| `src/components/BarraLateralComp.tsx` | Cuenta actual, cuatro semanas y cierre de sesión. |
| `src/components/CabeceraChatComp.tsx` | Nombre del chatbot y sesión semanal en curso. |
| `src/components/InicioChatComp.tsx` | Bienvenida de conversación libre y explicación del seguimiento. |
| `src/components/MensajeChatComp.tsx` | Mensaje, autor y hora de Lima. |
| `src/components/EntradaChatComp.tsx` | Redacción, límite de texto y envío con Enter. |
| `src/components/EstadoEscribiendoComp.tsx` | Puntos animados mientras se espera la respuesta. |
| `src/hooks/useAuth.ts` | Acceso al estado y acciones de autenticación. |
| `src/hooks/useChatbot.ts` | Recupera historial, envía, espera, reintenta y sincroniza las semanas. |
| `src/hooks/useDatosAdmin.ts` | Carga y actualización periódica de las consultas del panel. |
| `src/hooks/useAlumnos.ts`, `useAlumno.ts`, `useReportes.ts` | Consultas específicas de alumnos/reportes. |
| `src/api/http.ts` | Fetch con cookie, CSRF, tiempos de espera y errores. |
| `src/api/authApi.ts` | Registro, login, logout y usuario actual. |
| `src/api/chatbotApi.ts` | Historial y envío a Django; valida la estructura de respuesta. |
| `src/api/alumnosApi.ts`, `reportesApi.ts` | Peticiones administrativas. |
| `src/types/` | Estructuras TypeScript de usuario, chat, alumno y reporte. |
| `src/ui/` | Botones y campos reutilizables. |
| `src/utils/fechas.ts` | Presentación de fechas y periodos en Lima. |
| `src/index.css` | Tailwind, colores y estilos base. |
| `vite.config.ts` | Configuración del frontend y proxy local a Django. |

## Comportamiento

El historial pertenece a la cuenta y se recupera al recargar o iniciar sesión otra vez. Ya no hay nuevo chat, limpiar conversación, cuestionario, opciones de respuesta ni resultados numéricos. Las semanas se separan visualmente dentro del mismo historial.

El frontend muestra tres puntos hasta recibir el primer texto y después presenta la respuesta progresivamente en la misma burbuja mediante `/api/chat/flujo/`. El historial definitivo sustituye el texto parcial al terminar. Si una petición falla, recupera lo guardado y permite reintentar la misma clave sin duplicar mensajes. Las lecturas periódicas no sobrescriben el envío en curso.

El panel se actualiza cada 30 segundos. Al seleccionar un estudiante muestra su reporte provisional de la semana vigente, con avisos sobre análisis pendiente y cobertura de los siete indicadores; conserva debajo los reportes semanales acumulados. Separa citas del estudiante de interpretaciones de IA y no convierte duración, mensajes ni conteos de evidencias en niveles de estrés. La actividad reciente refleja los últimos cinco minutos, no una conexión permanente comprobada. El acceso local del administrador usa `admin/admin`; los estudiantes conservan su pantalla de Gmail.

No se guardan contraseñas ni tokens de autenticación en localStorage. Una notificación local sin credenciales sincroniza cambios de cuenta entre pestañas, y el historial anterior se desmonta al cambiar de usuario.

## Comprobar

```powershell
npm run build
npm run lint
npm run test:api
```

Las pruebas API comprueban lectura de historial, CSRF, clave de reintento, errores de conexión/Ollama y respuestas inválidas. El proxy de Vite es para desarrollo; el servidor definitivo debe dirigir `/api/` a Django y las rutas de React a `index.html`.

Para creación del administrador, funcionamiento semanal y relación con la tesis, consulta [el README de la raíz](../README.md).
