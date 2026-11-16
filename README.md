# Casper

Casper es un asistente personal desarrollado en Python.

Su objetivo es evolucionar progresivamente hasta convertirse en un asistente capaz de interactuar de forma cercana con el entorno tecnológico de su usario.

## Casperv1

La primera versión de Casper se centra en la interacción mediante chat de texto.

### Capacidades

- Resolución de problemas matemáticos.
- Ayuda con programación.
- C y C++.
- Java.
- Python.
- Oracle SQL.
- Bash.
- Git.
- GitHub.
- Bash en Windows y Linux.

### Restricciones actuales

Casper v1 no:

- Manipula archivos del computador.
- Crea programas automáticamente en el computador.
- Ejecuta comandos automáticamente.
- Controla dispositivos externos.
- Utiliza interacción por voz.

## Tecnologías

- Python
- Git
- GitHub

## Cómo ejecutar

```bash
python -m pip install -r requirements.txt
python src/main.py
```

## Fase 4 — Poderes web

Casper consulta APIs reales por internet:

- `clima <ciudad>` — clima actual (Open-Meteo, gratis y sin clave).
- `dolar` — precio del dólar en pesos (ExchangeRate-API, gratis y sin clave).
- `convertir <cantidad> <moneda> a <moneda>` — ej. `convertir 100 usd a cop`.
- `noticias` — titulares de tecnología (Hacker News). Con una clave gratis de
  [NewsAPI](https://newsapi.org) guardada como variable de entorno
  `NEWS_API_KEY` (o en un archivo `.env`, ver `.env.example`), muestra
  titulares generales de Colombia. Las claves nunca van en el código.

## Fase 5 — Voz

Casper habla y escucha (todo opcional: sin micrófono o sin las librerías,
los comandos avisan en vez de romperse):

- `decir <texto>` — Casper lo dice en voz alta (pyttsx3, offline, voces SAPI).
- `escuchar` — graba 5 segundos del micrófono, lo transcribe con Google
  (gratis, sin clave) y procesa lo que dijiste como si lo hubieras escrito.
- `voz on` / `voz off` — activa o desactiva que Casper hable sus respuestas.

En Windows, si no hay voz en español instalada, Windows la descarga en
Configuración → Hora e idioma → Voz. El micrófono necesita permiso de la app.

## Fase 6 — Cerebro (LLM)

Cuando ningún comando coincide, Casper le pregunta a un modelo de lenguaje,
que puede responder con texto o llamar a uno de sus comandos como herramienta.
Así entiende paráfrasis ("deshazte de la primera nota"), conversación
("¿cómo estás?") y preguntas de conocimiento ("¿cuál es la fórmula de
la velocidad?"). Si el cerebro no está disponible, Casper contesta como antes.

**Opción A — Ollama (local, gratis, sin clave, recomendado):**

1. Instala Ollama desde https://ollama.com
2. Descarga el modelo: `ollama pull qwen2.5:3b`
3. Listo: `CASPER_LLM=ollama` es el valor por defecto.

**Opción B — Gemini (nube, gratis con clave):**

1. Crea una clave gratis en https://aistudio.google.com/app/apikey
2. Copia `.env.example` a `.env` y pon `CASPER_LLM=gemini` y tu
   `GEMINI_API_KEY`.

El modelo NO puede usar: apagar, reiniciar, bloquear, decir, voz, escuchar
ni salir. Las acciones destructivas y el control de voz los inicia solo
el humano. Las claves viven en variables de entorno o en `.env`, nunca en
el código.

## Cómo correr las pruebas

```bash
pip install -r requirements.txt
python -m pytest
```
