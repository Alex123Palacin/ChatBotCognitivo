# Entrega de actividad

La entrega está en `entregas_locales/actividad_20260911/` y no se sube a Git.

## Para el operador del VPS

Adjuntar únicamente `paquete_actividad_20260911.zip` y copiar el texto de `PROMPT_AGENTE.txt`.
Las instrucciones dentro del ZIP indican cómo validar, respaldar, aplicar y comprobar
la carga desde la consola del backend. El cargador portable no requiere instalar
herramientas permanentes ni modificar la imagen si el servicio ya tiene el código y
las tres migraciones compatibles. Rechaza versiones anteriores con un error claro.

No adjuntar `accesos.csv`, `accesos_privados.json`, `acceso_admin_local.json` ni una base
SQLite al repositorio o al frontend. El ZIP solo contiene el paquete, el motor de
importación, su entrada, instrucciones y huellas de integridad. Sus hashes de acceso
también son privados.

## Para revisar localmente

Ejecutar `ver_actividad_local.ps1` desde la raíz del proyecto. Abre la web en
`http://127.0.0.1:5192`, con backend en el puerto `8021` y la base aislada ya cargada.
Usar `/administrador` con el acceso de `acceso_admin_local.json`, o `/login` con una
cuenta de `accesos.csv`. Presionar ENTER en la ventana del script para cerrar sus
servicios. El inicio habitual `iniciar.ps1` y su base no se han modificado.

## Comprobaciones

- 136 estudiantes y conversaciones; cada historial contiene entre 50 y 58 mensajes.
- 7.420 mensajes, 1.144 evidencias literales y 136 reportes sin análisis pendientes.
- Actividad el 11/09/2026 entre las 13:00:00 y las 17:59:42, con zona de Lima.
- 4 perfiles sin dificultades expresadas, 32 con una, 36 con dos, 36 con tres y 28 con cuatro.
- Login, autorización, chat y los 136 detalles administrativos correctos.
- Exportación web comprobada en dos grupos de 100 y 36; 55 frecuencias explícitas
  reconocidas y los demás campos conservan `Sin información` según las reglas actuales.
- Carga repetida sin duplicados ni cambios a la actividad posterior.
- Respaldo y reversión transaccional verificados por pruebas del importador.
- Cargador portable verificado con configuración de producción, sin claves legibles en el ZIP.
- 160 pruebas del backend correctas y tres recorridos de Chrome con API real local.
- Base habitual sin cambios; ninguna operación en el VPS.

El método del lote es anotación estructurada con validación de citas y agregación
nativa de reportes. No se afirma que Ollama haya generado esas evidencias. La
procedencia y la ficha de exportación existentes se conservan; no se atribuye
aceptación de términos a las cuentas creadas administrativamente.

Fuentes y regeneración: [herramientas de carga](herramientas/carga_actividad/README.md).

## Segunda operación: nombres de usuario

Disponible `entregas_locales/cambio_usuarios_20260911/paquete_cambio_usuarios.zip`,
con su `PROMPT_AGENTE.txt` y el archivo privado `accesos_usuarios.csv` por separado.
El prompt establece actualizar primero la web para aceptar nombres de usuario y
después convertir las 136 identidades. La conversión fue probada en una copia
aislada: no se ejecutó en el VPS ni cambió la base habitual. No modifica los textos
ya guardados, las contraseñas ni los IDs de las cuentas o los reportes.
