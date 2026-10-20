import http.client
import json
import queue
import re
import socket
import threading
import time
from contextlib import closing
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


def _eventos_modelo(url, datos, timeout, cancelar=None):
    """Lee Ollama sin bloquear el plazo total ni la cancelación del consumidor."""
    cancelar = cancelar or (lambda: False)
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
            yield item
            if item.get("done"):
                return
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


def _contenido(item):
    # Ollama puede separar el razonamiento en thinking; solo se lee content.
    mensaje = item.get("message", {})
    contenido = item.get("response") if "response" in item else mensaje.get("content", "") if isinstance(mensaje, dict) else None
    if not isinstance(contenido, str):
        raise ErrorModelo("Ollama devolvió una respuesta no válida.")
    return contenido


def _generar_cancelable(url, datos, timeout, cancelar):
    partes = []
    with closing(_eventos_modelo(url, datos, timeout, cancelar)) as eventos:
        for item in eventos:
            partes.append(_contenido(item))
            if item.get("done"):
                return {"message": {"content": "".join(partes)}, "done_reason": item.get("done_reason")}


def _keep_alive():
    valor = str(getattr(settings, 'OLLAMA_KEEP_ALIVE', '-1')).strip()
    # La API distingue segundos numéricos de duraciones como "10m". "-1"
    # en Environment debe transmitirse como número, compatible con Ollama 0.18.
    return int(valor) if valor.lstrip('-').isdigit() else valor


def _solicitud(mensajes, formato, temperatura, limite, stream, directo):
    datos = {
        "model": settings.OLLAMA_MODEL,
        "messages": mensajes,
        "stream": stream,
        "think": False,
        "keep_alive": _keep_alive(),
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
    return settings.OLLAMA_URL.rstrip("/") + endpoint, datos


def generar(mensajes, formato=None, temperatura=0.4, limite=1800, cancelar=None, timeout=None, directo=False):
    """Una llamada local a Ollama; sirve para conversar y para extraer evidencias."""
    url, datos = _solicitud(mensajes, formato, temperatura, limite, cancelar is not None, directo)
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


class _TextoVisible:
    """Descarta bloques think incluso cuando sus etiquetas llegan partidas."""
    def __init__(self):
        self.pendiente = ''
        self.pensando = False
        self.entregado = False

    def recibir(self, texto, final=False):
        self.pendiente += texto
        salida = []
        while self.pendiente:
            etiqueta = re.search(r'</?think>', self.pendiente, flags=re.I)
            if etiqueta:
                if etiqueta.group().lower() == '<think>':
                    if not self.pensando:
                        salida.append(self.pendiente[:etiqueta.start()])
                    self.pensando = True
                else:
                    if not self.pensando and self.entregado:
                        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
                    # También descarta el prefijo de un cierre sin apertura.
                    self.pensando = False
                self.pendiente = self.pendiente[etiqueta.end():]
                continue
            if final:
                if self.pensando or any(
                    etiqueta.startswith(self.pendiente[pos:].lower())
                    for pos, caracter in enumerate(self.pendiente) if caracter == '<'
                    for etiqueta in ('<think>', '</think>')
                ):
                    raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
                salida.append(self.pendiente)
                self.pendiente = ''
                break
            if self.pensando:
                self.pendiente = self.pendiente[-7:]
                break
            # Reserva la palabra en curso y posibles etiquetas. Permite entregar
            # palabras completas sin mostrar media etiqueta <think>.
            coincidencia = re.search(r'\s+(?=\S*$)', self.pendiente)
            corte = coincidencia.end() if coincidencia else 0
            posible = self.pendiente.find('<')
            if posible >= 0:
                corte = min(corte, posible)
            if corte:
                salida.append(self.pendiente[:corte])
                self.pendiente = self.pendiente[corte:]
            break
        texto = ''.join(salida)
        self.entregado = self.entregado or bool(texto.strip())
        return texto


def generar_flujo(mensajes, temperatura=0.4, limite=192, directo=False, timeout=None):
    """Entrega palabras en cuanto Ollama las genera, con un plazo total acotado."""
    url, datos = _solicitud(mensajes, None, temperatura, limite, True, directo)
    filtro = _TextoVisible()
    hay_texto = False
    try:
        with closing(_eventos_modelo(url, datos, timeout or settings.OLLAMA_TIMEOUT)) as eventos:
            for item in eventos:
                if item.get('done') and item.get('done_reason') == 'length':
                    raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
                texto = filtro.recibir(_contenido(item))
                if texto:
                    hay_texto = hay_texto or bool(texto.strip())
                    yield texto
                if item.get('done'):
                    if filtro.pensando:
                        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
                    final = filtro.recibir('', final=True)
                    if final:
                        hay_texto = hay_texto or bool(final.strip())
                        yield final
                    if not hay_texto:
                        raise ErrorModelo('El modelo no completó su respuesta. Vuelve a intentarlo.')
    except HTTPError as exc:
        if exc.code == 404:
            raise ErrorModelo('Ollama no encuentra el modelo configurado. Compruébalo con ollama list.') from exc
        raise ErrorModelo('Ollama no pudo generar una respuesta. Revisa que tenga memoria disponible.') from exc
    except (URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        raise ErrorModelo('No se pudo obtener la respuesta de Ollama. Comprueba que esté abierto y vuelve a intentarlo.') from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise ErrorModelo('Ollama devolvió una respuesta no válida. Vuelve a intentarlo.') from exc


def precalentar_modelo():
    """Carga pesos y el prefijo escolar compartido antes de aceptar conversaciones."""
    datos = {
        'model': settings.OLLAMA_MODEL, 'prompt': '', 'stream': False,
        'keep_alive': _keep_alive(),
        'options': {'num_ctx': settings.OLLAMA_NUM_CTX, 'num_gpu': settings.OLLAMA_NUM_GPU},
    }
    if getattr(settings, 'OLLAMA_CHAT_DIRECT', True) and settings.OLLAMA_MODEL.startswith('deepseek-r1:8b'):
        from .conversacion import INSTRUCCIONES
        datos.update({'raw': True, 'prompt': _prompt_directo([{'role': 'system', 'content': INSTRUCCIONES}])})
        # Un solo token basta para dejar preparado el prefijo común del chat.
        # Su salida se descarta; no crea mensajes ni un estudiante de prueba.
        datos['options']['num_predict'] = 1
    solicitud = Request(settings.OLLAMA_URL.rstrip('/') + '/api/generate',
                        data=json.dumps(datos).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urlopen(solicitud, timeout=settings.OLLAMA_TIMEOUT) as respuesta:
            resultado = json.load(respuesta)
        if not isinstance(resultado, dict) or resultado.get('done') is not True:
            raise ErrorModelo('No se pudo precalentar el modelo de Ollama.')
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ErrorModelo('No se pudo precalentar el modelo de Ollama.') from exc
