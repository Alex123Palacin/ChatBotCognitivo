# Revisión de la carga del 23 de octubre de 2026

## Alcance

20 personajes, cuatro sesiones por personaje y dos mensajes del estudiante por
sesión. Se esperan 160 respuestas del chatbot y 80 reportes semanales. La generación
y extracción de evidencias se ejecutan en Ollama con el código existente. Los
primeros 22 intercambios se procesaron en el VPS; los pendientes se trasladaron
a una base privada separada para aprovechar la GPU local con el mismo modelo.
El contenido es ficticio y no constituye una muestra de estudiantes reales.

## Comprobaciones realizadas

- Trece comprobaciones automatizadas en una base temporal: fechas, cuatro semanas,
  acceso por contraseña, colisiones, idempotencia, recuperación de una interrupción,
  validación de citas, exportación, limpieza delimitada y reintento del supervisor.
- Calendario solicitado: conjunto del 10 de septiembre al 23 de octubre de 2026,
  con inicios escalonados y cuatro semanas exactas por persona. También se comprueba
  la recalendariación de mensajes ya existentes y su posterior reanudación.
- Paquete transferido a `/data/cargas/colegio-20261023-20/paquete`.
- Respaldo SQLite anterior a la creación de las veinte cuentas, en el directorio
  privado de estado del lote. No se modifica ni sustituye la base existente.
- Las cuentas aparecen en el panel con sus nombres y cuatro sesiones.
- Ocho comprobaciones específicas de incorporación y auditoría: preservación de cuentas,
  repetición sin duplicados y rechazo de propietarios ajenos, citas inventadas,
  cambios de respuestas, omisión de mensajes, fechas ajenas y análisis pendientes;
  verificación de accesos y conservación del administrador.
- Primer reporte observado: Mateo Quispe Salazar, semana 1; dos mensajes y tres
  citas. Las citas observadas pertenecen literalmente a sus mensajes.

## Hallazgo para revisar la clasificación

En el reporte de Mateo, semana 1, el modelo asignó el fragmento «No sé cómo decidir
qué estudiar primero.» a **Búsqueda de soporte / ausencia expresada**. El fragmento
describe una dificultad para priorizar y no declara expresamente que no pida o no
tenga apoyo. Conviene revisar esa asignación frente a **Planificación**.

Esto muestra por qué verificar la literalidad de una cita no basta para comprobar
que su indicador y su señal sean correctos. El resultado original se conserva en
la aplicación. Este archivo no introduce correcciones manuales en los reportes.

En Gabriel, semana 1, apareció «termino tarde la tarea.» como cita de síntomas
psicológicos. Ese fragmento aislado describe un resultado temporal y no un síntoma
psicológico explícito; el mensaje completo sí menciona vergüenza. Conviene revisar
tanto la categoría como la selección del fragmento, sin considerar suficiente
que la cita sea literal.

## Otras observaciones durante la ejecución

- Adrián menciona un golpe en la pierna durante fútbol, expresamente ajeno a los
  estudios. En la salida observada no se clasificó ese golpe como síntoma físico
  académico. La evidencia física registrada en su semana 4 fue la negación literal
  «No estoy teniendo problemas para dormir por los estudios.».
- Un intento de respuesta para Daniela, semana 1, alcanzó el límite de generación
  y fue rechazado por el filtro existente. No se guardó el texto incompleto.
  El reintento produjo una respuesta válida. El ejecutor local permite reintentar
  errores del modelo; ante tres fallos consecutivos usa temporalmente el modo
  nativo ya soportado por la aplicación, sin cambiar su configuración en el VPS.
- Hasta esta revisión no se encontraron fechas de mensajes fuera de su sesión ni
  sesiones con duración distinta de siete días. La comprobación final debe volver
  a ejecutarse sobre el conjunto completo incorporado en el servidor.

## Cómo revisar los resultados cuando termine

1. Revisar `estado.json`: `completo` debe ser verdadero y `citas_invalidas` cero.
2. Abrir `resultados.json`, que incluye conversación y reportes por persona.
3. Comparar cada cita con su mensaje de origen y revisar también su categoría.
4. Distinguir información ausente de una negación explícita. El personaje con
   mensajes breves o temas ajenos al colegio no debería recibir conclusiones
   completas por el solo hecho de haber transcurrido cuatro semanas.
5. Revisar especialmente las molestias atribuidas a un resfrío o a un golpe
   deportivo, y la preocupación por un familiar: no deben convertirse
   automáticamente en síntomas de estrés académico.
6. Comparar las semanas sin asumir que todos mejoran. Los relatos incluyen
   retrocesos y dificultades que persisten.

Las contraseñas se conservan en `secrets/cargas/colegio-20261023-20/credenciales.json`,
que está excluido de Git. No incluir ese archivo ni el respaldo del sitio en una
publicación o en un documento de resultados.

## Resultado final verificado en el VPS

El 23 de octubre de 2026, a las 12:38 de Lima, la auditoría confirmó:

- 20 cuentas del lote y sus 20 accesos por contraseña verificados.
- 80 sesiones de siete días y 80 reportes completos.
- 160 mensajes de estudiantes y 160 respuestas del chatbot.
- Los 160 mensajes analizados, sin análisis pendientes ni citas no literales.
- Las tres cuentas anteriores conservan sus identidades y credenciales.
- Las veinte filas del panel muestran ocho mensajes y cuatro reportes cada una.
- Se revisaron también los cuatro reportes del último estudiante, cuya última
  sesión cierra el 23 de octubre a las 09:00 de Lima.

La copia de `auditoria-final.json` del servidor está en la carpeta privada del
lote, junto con `resultados.json`, que incorpora los enlaces a los ochenta
reportes del VPS. El código de frontend y backend permaneció sin cambios.
La literalidad verificada no corrige los posibles errores de clasificación
descritos arriba: este conjunto sirve para comprobar y revisar el sistema.
