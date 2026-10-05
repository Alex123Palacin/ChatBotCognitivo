# Chatbot Cognitivo · Frontend

React, TypeScript, Tailwind CSS y React Router DOM.

## Iniciar

Con Django en `http://127.0.0.1:8001` y Ollama abierto, desde `frontend/`:

```sh
npm install
npm run dev
```

Abre `http://localhost:5173/chat`. Vite envía las peticiones `/api/` al backend.
No se llama a Ollama desde el navegador.

## Flujo del código

`ChatbotPage.tsx` usa `useChatbot.ts`, que llama a `api/chatbotApi.ts`.
La API recibe el mensaje de Django y el hook actualiza los mensajes, la pregunta
pendiente y el estado de escritura. La página distribuye los componentes.

| Archivo | Responsabilidad |
| --- | --- |
| `src/main.tsx` / `src/App.tsx` | Inicio de React y rutas. |
| `src/pages/ChatbotPage.tsx` | Distribuye la pantalla del chat. |
| `src/hooks/useChatbot.ts` | Mensajes, sesión temporal, envío, espera, errores, opciones y limpieza. |
| `src/api/chatbotApi.ts` | Peticiones REST a Django y token CSRF. |
| `src/types/chatbot.ts` | Tipos de mensajes, preguntas, opciones y resultados. |
| `src/components/CabeceraChatComp.tsx` | Nombre del chatbot y menú móvil. |
| `src/components/BarraLateralComp.tsx` | Conversación actual, nuevo chat y limpieza. |
| `src/components/InicioChatComp.tsx` | Bienvenida y sugerencias. |
| `src/components/MensajeChatComp.tsx` | Contenido, hora y resultado de cada mensaje. |
| `src/components/EntradaChatComp.tsx` | Texto y envío con Enter; Shift + Enter inserta una línea. |
| `src/components/EstadoEscribiendoComp.tsx` | Tres puntos mientras el backend responde. |
| `src/components/OpcionesPreguntaComp.tsx` | Botones de respuesta y progreso del cuestionario. |
| `src/components/ResultadoCuestionarioComp.tsx` | Promedios por indicador/dimensión y detalle de respuestas. |
| `src/ui/` | Botones reutilizables. |
| `src/index.css` | Tailwind y colores. |
| `vite.config.ts` | Proxy local de `/api/` a Django. |

El envío se bloquea durante una respuesta. Si falla la conexión, se muestra un error
sin inventar respuestas; el usuario puede reintentar. Al limpiar el chat se cancela
la espera y se solicita al servidor borrar la conversación temporal.

Los resultados numéricos vienen del backend. El frontend no puntúa texto libre.
El cuestionario propio de 14 preguntas es orientativo, no es un diagnóstico ni
el inventario SISCO validado. Las preguntas, fórmulas y límites están documentados
con detalle en [el README del backend](../backend/README.md).

## Comprobar

```sh
npm run build
npm run lint
```

Las conversaciones no se conservan al recargar. El proxy de Vite es para desarrollo;
un despliegue necesita dirigir `/api/` a Django y las rutas de React a `index.html`.
