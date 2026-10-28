# Rendimiento de las respuestas

El chat usa por defecto **`qwen3:1.7b`** para entregar respuestas breves con menos trabajo de CPU. **`deepseek-r1:8b`** sigue procesando las evidencias en segundo plano. No se eliminó el modelo anterior ni se modificaron los datos de conversación.

`OLLAMA_CHAT_MODEL` elige el modelo de conversación y `OLLAMA_MODEL` el de análisis. Para utilizar DeepSeek en ambos:

```text
OLLAMA_CHAT_MODEL=deepseek-r1:8b
OLLAMA_MODEL=deepseek-r1:8b
```

Estas variables se configuran en Environment y requieren nuevo despliegue. El servicio `modelo` comprueba ambos y descarga lo que falte. Con Ollama externo, su servidor debe tenerlos disponibles. Mantener dos modelos puede requerir más memoria; Ollama puede descargar pesos de memoria y volverlos a cargar según sus recursos.

## Cambios aplicados

- El precalentamiento prepara el modelo de chat real antes de abrir el backend.
- La entrega continúa siendo progresiva: no se espera toda la respuesta para mostrar texto.
- Se conserva la ocultación de `thinking` y de etiquetas de razonamiento, la cancelación al cerrar el flujo y el rechazo de una respuesta incompleta.
- El contexto recupera ocho mensajes recientes y evita consultas adicionales por semanas anteriores.
- No se rebajó el límite de generación a los 48 tokens utilizados en una comparación breve: producción conserva hasta 192 para evitar truncamientos.
- Las instrucciones mantienen contexto de colegio, límites de apoyo, privacidad y seguridad. El modelo rápido tiene menor capacidad y puede seguir peor algunas preferencias de estilo; las instrucciones no garantizan una salida exacta en cada generación. Se conserva la elección de DeepSeek para quien priorice ese comportamiento sobre velocidad.

## Prueba local orientativa

Con CPU explícita, contexto 4096, las mismas instrucciones y un mensaje escolar ficticio, con máximo de 48 tokens:

| Modelo | Primer texto, frío | Total, frío | Primer texto, caliente | Total, caliente |
| --- | --- | --- | --- | --- |
| DeepSeek 8B | 26,898 s | 36,344 s | 0,884 s | 10,101 s |
| Qwen3 1.7B | 7,431 s | 9,160 s | 0,202 s | 1,932 s |

Una respuesta de DeepSeek se truncó con ese límite de prueba; no se adoptó tal límite. Pruebas posteriores con el límite normal dieron respuestas del modelo rápido en aproximadamente 2–3 segundos una vez cargado. Son observaciones de esta computadora, **no una garantía para el VPS ni una certificación de calidad clínica**.

También se evaluó Qwen3 4B localmente, pero no se seleccionó: en este entorno mostró razonamiento como contenido y agotó el límite de respuesta. No se incorporó una plantilla experimental de ese modelo al código de producción.

Antes de habilitar otra variante, comprobar idioma, calidad, respuestas completas, tratamiento de razonamiento y recursos reales; los controles de [thinking de Ollama](https://docs.ollama.com/capabilities/thinking) varían entre modelos. Consultar la [familia oficial Qwen3](https://ollama.com/library/qwen3) y mantener las pruebas de selección de modelo y streaming.
