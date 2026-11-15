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
        raise WebError(f"El servicio devolvió un error (HTTP {r.status_code}).")
    except ValueError:
        raise WebError("El servicio respondió algo que no entiendo (no era JSON).")
