# Conservación de las conversaciones nuevas

La creación de cuenta exige aceptar expresamente la política `conversaciones-30-dias-v1`. El servidor registra su versión y la fecha de aceptación, y rechaza registros sin aceptación booleana o con otra versión.

Cada mensaje nuevo de esas cuentas recibe una fecha de eliminación a **30 días desde el envío de ese mensaje**. El plazo no empieza en el registro de la cuenta ni se reinicia al volver a entrar. La cuenta se conserva.

## Datos anteriores

Las migraciones añaden columnas vacías y un índice. No rellenan fechas de eliminación ni aceptaciones anteriores, no cambian las fechas del historial y no borran registros. Las cuentas y mensajes sin aceptación/fecha de eliminación están excluidos de la limpieza. Los scripts de demostración y la preparación del lote del 11 de septiembre quedan fuera de este cambio.

## Ejecución automática

El servicio `worker` ya configurado en Compose ejecuta la limpieza en sus ciclos, aunque nadie abra el chat. Se procesan lotes acotados de mensajes vencidos. Una respuesta que se está generando se deja para un ciclo posterior.

Se retiran también las evidencias asociadas y el reporte/resumen de las sesiones afectadas, para no conservar las citas vencidas en otro lugar. Los mensajes y evidencias todavía vigentes permanecen disponibles. No se borran cuentas ni sesiones históricas.

El nombre interno del comando del worker sigue siendo `procesar_semanas` para que la configuración de despliegue existente sea compatible; eso no obliga a mostrar semanas en la web.

## Comprobación manual

Desde `backend/principal`, una simulación sin borrado:

```sh
python manage.py limpiar_conversaciones
python manage.py limpiar_conversaciones --dry-run
```

Aplicar explícitamente un lote, únicamente cuando corresponda a la operación normal:

```sh
python manage.py limpiar_conversaciones --aplicar --limite 1000
```

La salida contiene conteos, no conversaciones ni identificadores personales. **Durante el desarrollo de este cambio no se ejecutó la aplicación del borrado sobre la base real.**

## Despliegue

Guardar los cambios en Git no los publica. Después de push y Deploy, el backend aplica sus migraciones con el arranque existente. Conservar el volumen `datos` y mantener el worker activo para la limpieza automática. No ejecutar `down -v`, recrear la base ni cargar datos nuevos como parte de esta actualización.

La eliminación del sistema activo no borra automáticamente respaldos externos, archivos ya descargados o copias hechas por otros operadores. Su acceso y conservación requieren una gestión aparte; el aviso de registro lo indica expresamente. No se promete eliminación física de cualquier copia ni confidencialidad absoluta.
