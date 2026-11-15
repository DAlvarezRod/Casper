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

## Cómo correr las pruebas

```bash
pip install -r requirements.txt
python -m pytest
```
