# Carga independiente de conversaciones

Este directorio agrega una herramienta externa. No modifica React, Django, las
migraciones, las reglas de medición ni el reloj del servidor.

Hay 20 personajes ficticios con nombres naturales, cuatro semanas por personaje
y dos visitas por semana: 160 mensajes de estudiantes. Las respuestas se generan
con el modelo configurado por la aplicación. Las evidencias y los reportes se
obtienen mediante el procesador existente, con su validación literal de citas.
No se rellenan resultados cuando Ollama falla. Estos relatos no corresponden a
participantes ni constituyen resultados empíricos de una tesis. Esa procedencia
queda en los archivos de carga; no se añaden etiquetas al nombre visible ni a los
mensajes del chat.

Los correos se generan como identificadores de acceso con un sufijo aleatorio
por lote. No se crean bandejas Gmail ni se verifica su propiedad ni se envían
correos. La herramienta verifica persistencia, conversación y análisis; no prueba
el formulario de registro ni el envío de correo.

## Archivos

- `historias.json`: nombres y relatos progresivos; no incluye respuestas ni
  conclusiones predeterminadas. Hay avances, retrocesos y falta de información.
- `cargar.py`: crea las cuentas, fija las semanas históricas, consulta Ollama,
  procesa evidencias, reanuda, exporta y permite preparar una limpieza delimitada.
- `test_carga.py`: comprobaciones con la base temporal del test runner de Django;
  sus dobles del modelo solo se usan en esas comprobaciones.
- `continuar.py`: ejecuta el lote reanudable con un máximo de diez reintentos;
  no instala servicios, cron ni tareas recurrentes.
- `ajustar_fechas.py`: modifica solo el calendario del lote identificado, preservando
  mensajes, respuestas y evidencias. Necesita que la carga esté pausada.
- `intercambio.py`: exporta exclusivamente las veinte cuentas del lote a una base
  aislada y permite incorporar mensajes/evidencias calculados en otro equipo.
  Al incorporar no importa usuarios, contraseñas ni sesiones: comprueba las
  identidades, el calendario, los UUID y las citas; conserva respuestas existentes.
- `acelerar_local.py`: ejecuta el modelo instalado en el equipo con GPU, usando
  el código de conversación y análisis de la aplicación sobre la base aislada.
- `test_intercambio.py`: comprueba la importación repetible y el rechazo de cambios
  en propietarios, mensajes existentes y citas no literales.
- `auditar.py`: comprueba el lote completo, sus credenciales, las fechas, los
  contadores de reportes y la conservación de las cuentas que había en el respaldo.
  Escribe `estado/auditoria-final.json` sin contraseñas.

## Aceleración con el equipo local

El 23 de octubre se pausó el supervisor del VPS después de 22 intercambios
completos. Se guardó un segundo respaldo consistente en el servidor y se exportó
solamente el lote ficticio. No se descargaron los datos de las cuentas previas.

La copia privada se procesa con `deepseek-r1:8b` de Ollama en la GPU local. Usa
los mismos prompts, funciones de respuesta, extracción y validación que el sitio.
No hay respuestas prefabricadas ni entrenamiento adicional. El cambio de hardware
puede producir salidas distintas en un modelo generativo; se conservan las
respuestas y los análisis que ya estaban terminados en el servidor.
Si el modelo rechaza varias generaciones consecutivas, se reintenta y puede usar
temporalmente el modo nativo ya soportado, con mayor margen para terminar. Nunca
se guarda una salida incompleta. El ejecutor da prioridad a cuentas con menos
mensajes, conservando el orden cronológico dentro de cada conversación.

La base separada es `secrets/cargas/colegio-20261023-20/local/aislada.sqlite3`.
Los scripts exigen que `DJANGO_DB_PATH` señale esa carpeta privada para sembrarla
o procesarla. Nunca se restaura esa base sobre producción. Se transfieren
mensajes y evidencias, se validan en una transacción y se recalculan los reportes
con las funciones existentes. El código de la aplicación no se modifica.

`resultados-modelo.json.gz` contiene una instantánea reanudable del cálculo;
`resultados.json` contiene las conversaciones y los reportes para su revisión.
Ambos contienen la procedencia ficticia y permanecen fuera de Git. Para ejecutar
esta ruta en otro equipo, primero migrar una base **nueva** en la carpeta privada,
sembrar la copia con `intercambio.py sembrar` y ejecutar `acelerar_local.py`.

## Calendario solicitado para este lote

El conjunto abarca del **10 de septiembre al 23 de octubre de 2026**. Cada persona
conserva cuatro sesiones consecutivas de siete días. Sus inicios se distribuyen
entre el 10 y el 25 de septiembre: las primeras cuatro semanas terminan el 8 de
octubre y las últimas el 23 de octubre. No son cuatro sesiones de duración irregular.

La primera visita ocurre al empezar el programa. En las semanas siguientes, la
primera visita se sitúa un día después del inicio y la última visita media hora
antes del cierre semanal. Así hay mensajes hasta el 23 de octubre, todos dentro
de sus sesiones, sin cambiar el reloj del servidor.

Para ajustar un lote existente: crear `estado/detener`, esperar a que el supervisor
indique `detenido` y ejecutar:

```sh
python /data/cargas/colegio-20261023-20/paquete/ajustar_fechas.py --carpeta /data/cargas/colegio-20261023-20/estado --desde 2026-09-10 --hasta 2026-10-23
```

La operación valida las identidades y los mensajes, usa una transacción y conserva
el manifiesto anterior. Repetirla con el mismo rango no duplica datos. Después de
verificar las fechas, renombrar el archivo de pausa y volver a iniciar el supervisor.

## Ejecución en el contenedor backend

Subir estos archivos a un directorio privado del volumen `/data`. Ejemplo de
paquete: `/data/cargas/colegio-20261023-20/paquete`. Mantener el estado en
`/data/cargas/colegio-20261023-20/estado`, fuera del contenido público del frontend.

```sh
python /data/cargas/colegio-20261023-20/paquete/cargar.py plan --carpeta /data/cargas/colegio-20261023-20/estado
python /data/cargas/colegio-20261023-20/paquete/cargar.py cargar --carpeta /data/cargas/colegio-20261023-20/estado
python /data/cargas/colegio-20261023-20/paquete/cargar.py procesar --max-pasos 1 --carpeta /data/cargas/colegio-20261023-20/estado
python /data/cargas/colegio-20261023-20/paquete/cargar.py procesar --carpeta /data/cargas/colegio-20261023-20/estado
```

El primer `cargar` crea un respaldo SQLite consistente antes de insertar cuentas.
No descargar ese respaldo como parte del paquete: contiene los datos previos del
sitio. Las contraseñas se generan individualmente, se guardan con hash en Django
y se conservan en el manifiesto privado para permitir el acceso a esas cuentas.
La carpeta se crea con permisos 700 y los archivos sensibles con permisos 600.

La primera ejecución fija el inicio 29 días antes de la fecha real, a las 09:00
de Lima y con pequeños desplazamientos entre personas. Las sesiones duran siete
días y las cuatro quedan cerradas. Se puede fijar otra fecha con `--inicio`
ISO con zona horaria al crear el lote. Al reanudar no se cambian sus fechas.
Las fechas visibles son una reconstrucción histórica de los relatos preparados;
no indican cuándo se generó realmente cada respuesta. La ejecución actual queda
registrada con la fecha real en el log. No hay logins ni presencia inventados.

Si se interrumpe, repetir `procesar`: conserva los UUID de los mensajes y la
relación respuesta-a. Si falla el modelo, no crea una respuesta de sustitución ni
marca su análisis como correcto. El worker normal puede completar evidencias;
la herramienta respeta sus reservas y espera cuando hay chats activos.

Para mantener la ejecución después de cerrar la consola, iniciar `continuar.py`
como proceso independiente con su salida redirigida a un log privado. Su comando
es `python /data/cargas/colegio-20261023-20/paquete/continuar.py --carpeta /data/cargas/colegio-20261023-20/estado`.
No ejecutar dos supervisores del mismo lote: un bloqueo impide esa duplicación.
`supervision/estado.json` distingue `procesando`, `completo`, `detenido` y
`requiere_revision`. Un contenedor recreado puede interrumpir el proceso; sus
datos y el punto de reanudación siguen en `/data`.

## Estado y exportación

```sh
python /data/cargas/colegio-20261023-20/paquete/cargar.py estado --carpeta /data/cargas/colegio-20261023-20/estado
python /data/cargas/colegio-20261023-20/paquete/cargar.py exportar --carpeta /data/cargas/colegio-20261023-20/estado
```

`completo: true` exige 20 cuentas, 80 sesiones, 160 mensajes de estudiantes, 160
respuestas, 160 mensajes analizados, 80 reportes listos y ninguna cita ajena a su
mensaje. Un reporte listo no implica cubrir los siete indicadores: la cobertura
depende de lo que efectivamente se relató. No se calcula una puntuación SISCO.

Archivos privados producidos: `manifiesto.json` (identidades, credenciales y fechas),
`estado.json` (avance), `credenciales.json` (accesos) y `resultados.json` (mensajes,
evidencias y reportes por persona). Guardarlos fuera de Git, por ejemplo bajo
`secrets/`, y no dentro de directorios publicados por Nginx.

Para una pausa ordenada, crear un archivo vacío llamado `detener` en la carpeta
de estado. Se revisa entre operaciones; una inferencia en curso puede tardar en
terminar. Renombrar ese archivo y reanudar cuando corresponda.

## Limpieza posterior

`limpiar` sin confirmación solo muestra los IDs y no elimina nada:

```sh
python /data/cargas/colegio-20261023-20/paquete/cargar.py limpiar --carpeta /data/cargas/colegio-20261023-20/estado
```

Después de detener cualquier carga, revisar esos IDs. La eliminación definitiva
requiere añadir `--confirmar-lote colegio-20261023-20`. Antes de borrar, comprueba
todas las identidades contra su manifiesto y rechaza cuentas administrativas o
cuyos datos de acceso cambiaron. El borrado abarca exclusivamente esas cuentas
y sus relaciones en cascada. No ejecutar hasta que el propietario lo autorice.

## Comprobación local aislada

Desde la raíz, en PowerShell:

```powershell
$env:PYTHONPATH = (Get-Location).Path
& .\backend\.venv\Scripts\python.exe backend/principal/manage.py test herramientas.carga_conversaciones.test_carga
```
