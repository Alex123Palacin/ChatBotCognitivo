# Paquete de actividad

Herramientas para preparar, revisar y trasladar 136 historiales independientes.
No necesitan editar el frontend ni restaurar bases sobre el servidor.

## Preparación local

Desde la raíz, con Python del proyecto:

```powershell
.\backend\.venv\Scripts\python.exe -m herramientas.carga_actividad.preparar
.\backend\.venv\Scripts\python.exe -m herramientas.carga_actividad.verificar
.\backend\.venv\Scripts\python.exe -m herramientas.carga_actividad.verificar_local
.\backend\.venv\Scripts\python.exe -m herramientas.carga_actividad.empaquetar
```

La salida privada está en `entregas_locales/actividad_20260911/`, excluida de Git.
`--fecha AAAA-MM-DD` y `--salida CARPETA` permiten otra fecha y otra entrega.
Los UUID son estables; las credenciales se generan una vez y se reutilizan.
Una preparación que cambie el contenido exige otra carpeta: no pisa un paquete previo.

## Archivos

- `paquete_actividad_20260911.zip`: archivo portable que se entrega al operador.
- `PROMPT_AGENTE.txt` e `INSTRUCCIONES_VPS.md`: operación técnica, comandos y comprobaciones.
- `accesos.csv` y `accesos_privados.json`: accesos legibles solo para el propietario; fuera del ZIP.
- `actividad_local.sqlite3`: base aislada de revisión, nunca una copia de la base del servidor.
- `acceso_admin_local.json`: acceso administrativo exclusivo de esa base de revisión.
- `verificacion_paquete.json` y `verificacion_local.json`: comprobaciones de los datos y la integración.

Para revisar la web con esta base, ejecutar `ver_actividad_local.ps1` desde la raíz.
Abre `http://127.0.0.1:5192`, con backend en `8021`, sin cambiar el inicio habitual
ni su base. El administrador local se consulta en `acceso_admin_local.json`; las
cuentas de estudiantes, en `accesos.csv`. Cerrar con ENTER en la ventana del script.
El inicio de revisión no crea administradores predeterminados ni instala dependencias.

El paquete conserva `origen=demostracion` y `analisis_metodo=anotacion_estructurada_v1`.
Las conversaciones y evidencias se preparan de forma estructurada, con citas literales
verificadas. No se atribuyen a un procesamiento de Ollama que no haya ocurrido ni a
observaciones de participantes. Las identidades y correos de example.com no pertenecen
a alumnos reales. La procedencia de Perfil y la ficha Excel existente se conservan.
No se simula una aceptación humana de términos ni se desactiva la retención de cuentas reales.

Distribución: 4 cuentas sin dificultades expresadas, 32 con una, 36 con dos, 36 con tres
y 28 con cuatro. Planificación, automotivación y búsqueda de soporte se distribuyen como
recursos independientes, no se cuentan como dificultades. Cada historial tiene actividad
en las cinco horas de la ventana, con pausas, y de 40 a 60 mensajes totales. Una frase
semanal en un relato es un recuerdo del estudiante, no una división de la actividad en semanas.

Los análisis y frecuencias respetan las reglas actuales: las citas deben pertenecer a su
mensaje, los recursos deben estar expresados y la falta de frecuencia inequívoca conserva
`Sin información`. No se calculan diagnósticos ni eficacia a partir del lote.

## Operación

En el backend puede usarse el nuevo comando `cargar_actividad`. El ZIP contiene además
una entrada portable que permite usar el motor sin instalarlo permanentemente en la imagen.
Ambos validan primero, exigen SHA256 y código/migraciones compatibles, hacen un respaldo
SQLite consistente antes de aplicar y usan una transacción completa sin sobrescrituras.
No crean una base nueva cuando el operador tiene mal configurada la ruta de producción.

La web permite exportar hasta 100 alumnos por solicitud: usar grupos de 100 y 36.
El ZIP contiene hashes de contraseñas y debe trasladarse de forma privada.

## Conversión posterior a nombres de usuario

`python -m herramientas.carga_actividad.preparar_usuarios` prepara una segunda entrega
en `entregas_locales/cambio_usuarios_20260911/`. El mapa se genera una sola vez para
las 136 cuentas identificadas por sus mensajes y fechas de alta; se reutiliza al
repetir la preparación. El ZIP contiene el mapa, el script portable y el prompt
operativo. `accesos_usuarios.csv` permanece privado fuera del ZIP.

El script convierte username y nombre visible a identificadores aleatorios y vacía
el correo, conservando IDs, contraseñas, permisos, perfiles, mensajes y análisis.
Valida sin escribir por defecto; aplicar exige SHA256, respaldo SQLite previo y
una transacción completa. Rechaza colisiones, cuentas administrativas, identidades
modificadas, propietarios de conversaciones distintos y respuestas en curso.

El prompt pide al operador actualizar y publicar primero registro, login y vistas
para usar username. Esta herramienta no modifica esos formularios automáticamente.
Después de convertir no debe repetirse la carga del paquete inicial, que conserva
los identificadores anteriores. Los textos de conversaciones ya guardados tampoco
se reescriben para sustituir los nombres presentes en ellos.

Verificación: 166 pruebas de backend y conversión integral de las 136 cuentas en
una copia aislada, comprobando login, integridad de todos los mensajes/evidencias/
reportes, preservación de contraseñas y administradores, respaldo e idempotencia.
