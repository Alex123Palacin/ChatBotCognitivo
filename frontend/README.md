# Chatbot Cognitivo

Frontend con React, TypeScript, Vite, Tailwind CSS y React Router DOM.
Al enviar cualquier mensaje, el chatbot responde inmediatamente **hola**.

## Ejecutar

Desde la carpeta `frontend`:

```sh
npm install
npm run dev
```

La pantalla principal está en `/chat`. Las demás rutas redirigen a esa pantalla.

## Organización

- `src/main.tsx`: inicia React y BrowserRouter.
- `src/App.tsx`: define las rutas.
- `src/pages/ChatbotPage.tsx`: organiza los componentes de la pantalla y el menú móvil.
- `src/hooks/useChatbot.ts`: guarda el texto y los mensajes, agrega la respuesta `hola`, limpia el chat y desplaza la conversación.
- `src/types/chatbot.ts`: define los datos de un mensaje: id, contenido, remitente y fecha.
- `src/components/CabeceraChatComp.tsx`: muestra el nombre del chatbot.
- `src/components/BarraLateralComp.tsx`: contiene el menú y los botones para iniciar o limpiar la conversación.
- `src/components/InicioChatComp.tsx`: muestra la bienvenida y las sugerencias.
- `src/components/MensajeChatComp.tsx`: muestra el contenido y la hora de cada mensaje.
- `src/components/EntradaChatComp.tsx`: muestra el campo de texto y permite enviar con Enter o insertar un salto con Shift + Enter.
- `src/ui/BotonUI.tsx`: botón principal reutilizable.
- `src/ui/IconButtonUI.tsx`: botón reutilizable con icono.
- `src/index.css`: importa Tailwind y define los colores y estilos base.

## Funcionamiento

1. El usuario escribe y el texto se guarda en `texto`.
2. `enviarMensaje` comprueba que el texto no esté vacío.
3. Agrega el mensaje del usuario y la respuesta `hola` a `mensajes`.
4. Vacía el campo de texto.
5. La página muestra los mensajes con `MensajeChatComp`.

Las sugerencias también reciben la respuesta `hola`.
“Nuevo chat” y “Limpiar conversación” usan la misma función para vaciar el chat.
Los mensajes solo se guardan mientras la página está abierta; al recargar se borran.

## Comprobar el código

```sh
npm run build
npm run lint
```
