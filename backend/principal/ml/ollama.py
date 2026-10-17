import http.client
import json
import queue
import re
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings


class ErrorModelo(Exception):
    """Error comprensible sin exponer mensajes privados ni detalles internos."""


def historial_reciente(historial, presupuesto):
    """Limita contexto antiguo sin cortar frases ni el último mensaje del estudiante."""
    seleccion = []
    usados = 0
    for mensaje in reversed(historial[-16:]):
        if mensaje.get("role") not in ("user", "assistant") or not isinstance(mensaje.get("content"), str):
            continue
        longitud = len(mensaje["content"])
        if seleccion and usados + longitud > presupuesto:
            break
        seleccion.append({"role": mensaje["role"], "content": mensaje["content"]})
        usados += longitud
    return list(reversed(seleccion))


def presupuesto_contexto():
    # Estimación conservadora por caracteres: reserva espacio para generar respuesta.
    return max(2000, (getattr(settings, "OLLAMA_NUM_CTX", 4096) - 1200) * 3)


def _prompt_directo(mensajes):
    """Plantilla del modelo instalado, con el historial y sin razonamiento previo."""
    partes = ["<｜begin▁of▁sentence｜>"]
    ultimo_rol = None
    for mensaje in mensajes:
        rol = mensaje.get("role")
        if rol not in ("system", "user", "assistant"):
            continue
        # Un mensaje no puede introducir delimitadores de otro turno del modelo.
        contenido = mensaje["content"].replace("<｜", "< |").replace("｜>", "| >")
        if rol == "system":
            partes.append(contenido)
        elif rol == "user":
            partes.extend(["<｜User｜>", contenido, "<｜Assistant｜>"])
        else:
            if ultimo_rol != "user":
                partes.append("<｜Assistant｜>")
            partes.extend([contenido, "<｜end▁of▁sentence｜>"])
        ultimo_rol = rol
    if ultimo_rol != "user":
        partes.append("<｜Assistant｜>")
    partes.append("<think>\n</think>\n")
    return "".join(partes)


def _generar_cancelable(url, datos, timeout, cancelar):
    """Permite ceder Ollama al chat incluso mientras se esperan cabeceras HTTP."""
    if cancelar():
        raise ErrorModelo("El análisis continuará cuando no haya respuestas de chat pendientes.")
    destino = urlsplit(url)
    clase = http.client.HTTPSConnection if destino.scheme == "https" else http.client.HTTPConnection
    conexion = clase(destino.hostname, destino.port, timeout=timeout)
    eventos = queue.SimpleQueue()
    parar = threading.Event()
    socket_activo = []

    def leer():
        respuesta = None
        try:
            if parar.is_set():
                return
            conexion.connect()
            socket_activo.append(conexion.sock)
            if parar.is_set():
                return
            conexion.request("POST", destino.path, body=json.dumps(datos, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json"})
            if parar.is_set():
                return
            respuesta = conexion.getresponse()
            if respuesta.status != 200:
                raise HTTPError(url, respuesta.status, respuesta.reason, respuesta.headers, None)
            for linea in respuesta:
                if parar.is_set():
                    return
                if linea.strip():
                    eventos.put(("datos", json.loads(linea)))
            eventos.put(("fin", None))
        except Exception as error:
            eventos.put(("error", error))
        finally:
            if respuesta is not None:
                respuesta.close()
            conexion.close()

    # El hilo solo lee HTTP; la consulta a Django permanece en el hilo del worker.
    hilo = threading.Thread(target=leer, daemon=True, name="ollama-analisis")
    hilo.start()
    inicio = time.monotonic()
    revision = inicio
    partes = []
    try:
        while True:
            ahora = time.monotonic()
            if ahora - inicio >= timeout:
                raise TimeoutError("Se agotó el tiempo del análisis de Ollama.")
            if ahora >= revision:
                if cancelar():
                    raise ErrorModelo("El análisis continuará cuando no haya respuestas de chat pendientes.")
                revision = ahora + 1
            try:
                tipo, item = eventos.get(timeout=min(1, timeout - (ahora - inicio)))
            except queue.Empty:
                continue
            if tipo == "error":
                raise item
            if tipo == "fin":
                raise ErrorModelo("Ollama interrumpió el análisis antes de completarlo.")
            if not isinstance(item, dict):
                raise ErrorModelo("Ollama devolvió un análisis no válido.")
            mensaje = item.get("message", {})
            contenido = item.get("response") if "response" in item else mensaje.get("content", "") if isinstance(mensaje, dict) else None
            if not isinstance(contenido, str):
                raise ErrorModelo("Ollama devolvió un análisis no válido.")
            partes.append(contenido)
            # El campo thinking nunca se almacena ni se entrega a la aplicación.
            if item.get("done"):
                return {"message": {"content": "".join(partes)}, "done_reason": item.get("done_reason")}
    finally:
        parar.set()
        # shutdown despierta getresponse/readline; close por sí solo puede esperar.
        activo = socket_activo[0] if socket_activo else conexion.sock
        if activo is not None:
            try:
                activo.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        conexion.close()
        hilo.join(timeout=1)


def generar(mensajes, formato=None, temperatura=0.4, limite=1800, cancelar=None, timeout=None, directo=False):
    """Una llamada local a Ollama; sirve para conversar y para extraer evidencias."""
    datos = {
        "model": settings.OLLAMA_MODEL,
        "messages": mensajes,
        "stream": cancelar is not None,
        "think": False,
        "keep_alive": "10m",
        "options": {
            "temperature": temperatura,
            "num_ctx": getattr(settings, "OLLAMA_NUM_CTX", 4096),
            "num_predict": limite,
            "num_gpu": getattr(settings, "OLLAMA_NUM_GPU", 16),
        },
    }
    if formato is not None:
        # Ollama recibe directamente el esquema JSON en el campo format.
        datos["format"] = formato
    endpoint = "/api/chat"
    if directo and settings.OLLAMA_MODEL.startswith("deepseek-r1:8b"):
        # La plantilla verificada del DeepSeek instalado comienza en la respuesta
        # final. Conserva los pesos, las instrucciones y todos los turnos elegidos.
        datos.pop("messages")
        datos.update({"raw": True, "prompt": _prompt_directo(mensajes)})
        endpoint = "/api/generate"
    url = settings.OLLAMA_URL.rstrip("/") + endpoint
    solicitud = Request(
        url,
        data=json.dumps(datos, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        tiempo = timeout or settings.OLLAMA_TIMEOUT
        if cancelar is not None:
            resultado = _generar_cancelable(url, datos, tiempo, cancelar)
        else:
            with urlopen(solicitud, timeout=tiempo) as respuesta:
                resultado = json.load(respuesta)
        if not isinstance(resultado, dict):
            raise ErrorModelo("Ollama devolvió una respuesta no válida.")
        texto = resultado["response"] if "response" in resultado else resultado["message"]["content"]
        if not isinstance(texto, str):
            raise ErrorModelo("Ollama devolvió una respuesta no válida.")
        # Algunas versiones del modelo separan thinking, otras incluyen etiquetas.
        # Nunca entregamos ese razonamiento al estudiante ni lo usamos como evidencia.
        texto = re.sub(r"<think>.*?</think>", "", texto, flags=re.S)
        # También protege versiones que omiten la etiqueta de apertura.
        if "</think>" in texto:
            texto = texto.rsplit("</think>", 1)[-1]
        texto = re.sub(r"<think>.*$", "", texto, flags=re.S).strip()
        if not texto or resultado.get("done_reason") == "length":
            raise ErrorModelo("El modelo no completó su respuesta. Vuelve a intentarlo.")
        return texto
    except HTTPError as error:
        if error.code == 404:
            raise ErrorModelo("Ollama no encuentra el modelo configurado. Compruébalo con ollama list.") from error
        raise ErrorModelo("Ollama no pudo generar una respuesta. Revisa que tenga memoria disponible.") from error
    except (URLError, TimeoutError, OSError, http.client.HTTPException) as error:
        raise ErrorModelo("No se pudo obtener la respuesta de Ollama. Comprueba que esté abierto y vuelve a intentarlo.") from error
    except (ValueError, KeyError, TypeError) as error:
        raise ErrorModelo("Ollama devolvió una respuesta no válida. Vuelve a intentarlo.") from error
