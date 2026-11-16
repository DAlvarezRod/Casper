# Capa de red de Casper (Fase 4): un solo lugar para hablar con internet.
# Todos los comandos web pasan por get_json. Así el manejo de errores
# (sin internet, servicio caído, respuesta rara) vive en un solo sitio
# en vez de repetirse en cada comando.
import requests


class WebError(Exception):
    # Un fallo de red traducido a lenguaje humano. Los comandos devuelven
    # este mensaje al usuario en vez de un traceback incomprensible.
    pass


TIMEOUT = 10  # segundos; sin timeout, una API caída congelaría a Casper para siempre


def _error_http(r):
    # El código HTTP solo dice "429"; el cuerpo dice CUÁL límite se agotó
    # (por minuto o por día). Sin ese detalle, Casper no puede decirle al
    # usuario si debe esperar un minuto o hasta mañana.
    mensaje = f"El servicio devolvió un error (HTTP {r.status_code})."
    if getattr(r, "text", None):
        mensaje += f" Detalle: {r.text[:400]}"
    return mensaje


def get_json(url, params=None, headers=None):
    # requests.get devuelve una respuesta; .json() la convierte en dict/list.
    # raise_for_status() lanza HTTPError si el código no es 2xx (404, 500...).
    try:
        r = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        raise WebError("El servicio tardó demasiado en responder.")
    except requests.exceptions.ConnectionError:
        raise WebError("No hay conexión a internet o el servicio no responde.")
    except requests.exceptions.HTTPError:
        raise WebError(_error_http(r))
    except ValueError:
        raise WebError("El servicio respondió algo que no entiendo (no era JSON).")


def post_json(url, payload, headers=None, timeout=60):
    # Igual que get_json pero con POST y un cuerpo JSON. Lo usa el cerebro
    # (Fase 6): un modelo local puede tardar un minuto en responder, por
    # eso el timeout es mayor que en las APIs rápidas de la Fase 4.
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        raise WebError("El servicio tardó demasiado en responder.")
    except requests.exceptions.ConnectionError:
        raise WebError("No hay conexión a internet o el servicio no responde.")
    except requests.exceptions.HTTPError:
        raise WebError(_error_http(r))
    except ValueError:
        raise WebError("El servicio respondió algo que no entiendo (no era JSON).")
