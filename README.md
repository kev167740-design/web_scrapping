# web_scrapping

Extrae comentarios y reseñas de una marca en **TikTok, Facebook, Instagram, X, YouTube, Google Reviews y Trustpilot**, y los une en un solo archivo con estructura común.

```
python inicio.py banco_santander            # 1. crea las carpetas de la marca
                                            # 2. pega los enlaces en marcas/banco_santander/input/
python scraper_tiktok.py banco_santander    # 3. extrae una red (o todas con scraper_todos.py)
python union.py banco_santander             # 4. une todo en output/union.json
```

## Instalación

```bash
pip install -r requirements.txt
```

YouTube usa la librería estándar de Python, así que no necesita nada más.

## Configuración: `config.cfg`

Todo se configura en `config.cfg`. Si no existe, `inicio.py` lo crea copiando `config.ejemplo.cfg`.

- **`[claves]`:** tus claves de Apify, OpenAI y YouTube (Google).
- **`[general]`:** el tiempo máximo de cada ejecución y si los resultados se acumulan.
- **Una sección por red** con todos los parámetros de su actor: comentarios por vídeo o publicación, respuestas, orden, idioma, fechas, tiempo por vídeo, filtros y **tope de gasto**.

`config.cfg` está en `.gitignore`, así que tus claves no se suben a GitHub.

## Estructura de cada marca

```
marcas/banco_santander/
├── input/
│   ├── tiktok.txt            ← enlaces de vídeos
│   ├── facebook.txt          ← enlaces de publicaciones
│   ├── instagram.txt         ← enlaces de posts o reels
│   ├── x.txt                 ← enlaces de tuits (/status/…)
│   ├── youtube.txt           ← enlaces de vídeos
│   ├── google_reviews.txt    ← enlaces de lugares de Google Maps
│   └── trustpilot.txt        ← dominio o página de Trustpilot
└── output/
    ├── tiktok.json  facebook.json  instagram.json  x.json
    ├── youtube.json  google_reviews.json  trustpilot.json
    └── union.json
```

- **Cada archivo de `input/`** explica qué poner y trae ejemplos. Pon un enlace por línea; las líneas que empiezan por `#` se ignoran.
- **Cada red tiene un solo JSON en `output/`.** Si ejecutas otra vez y `acumular = true`, lo nuevo se **añade** sin duplicados; si un comentario ya estaba, se actualiza (likes, etc.). Con `acumular = false` se reemplaza.

## Scripts

| Script | Qué hace |
|---|---|
| `inicio.py <marca>` | Crea las carpetas y los archivos de enlaces (no borra nada si ya existen) |
| `scraper_tiktok.py <marca>` | Comentarios de TikTok |
| `scraper_facebook.py <marca>` | Comentarios de Facebook |
| `scraper_instagram.py <marca>` | Comentarios de Instagram |
| `scraper_x.py <marca>` | Respuestas a tuits de X |
| `scraper_youtube.py <marca>` | Comentarios de YouTube (API oficial, gratis) |
| `scraper_google_reviews.py <marca>` | Reseñas de Google Maps |
| `scraper_trustpilot.py <marca>` | Reseñas de Trustpilot |
| `scraper_todos.py <marca>` | Ejecuta todas las redes que tengan enlaces |
| `union.py <marca>` | Une todos los JSON en `output/union.json` |

## `union.json`

Cada registro tiene los mismos campos, venga de la red que venga:

| Campo | Contenido |
|---|---|
| `brand`, `platform` | Marca y red (`tiktok`, `facebook`, `instagram`, `x`, `youtube`, `google_reviews`, `trustpilot`) |
| `record_type` | `comment`, `reply` o `review` |
| `id`, `parent_id` | Id del comentario y, si es una respuesta, id del comentario al que responde |
| `source_url`, `source_name` | Vídeo, post, lugar o empresa de donde sale |
| `url` | Enlace directo al comentario o reseña (si la red lo da) |
| `text`, `title` | Texto y título (el título solo existe en Trustpilot) |
| `rating` | Estrellas (solo en reseñas) |
| `author`, `created_at`, `likes`, `replies` | Autor, fecha (ISO, UTC), likes y número de respuestas |
| `language`, `owner_reply` | Idioma y respuesta de la empresa (en reseñas) |

Si un actor cambia su estructura y `union.py` no encuentra el texto, te avisa y muestra los campos que sí llegaron.

## Cómo sacar el máximo del plan gratuito de Apify ($5/mes)

Los topes de gasto de `config.cfg` suman exactamente $5. Con esos valores, el volumen aproximado es:

| Red | Precio | Tope | Volumen aprox. |
|---|---|---|---|
| YouTube | **gratis** (API de Google) | — | miles al día (10.000 unidades = hasta ~1M comentarios) |
| X | $0.15 / 1.000 | $0.50 | ~3.300 respuestas |
| TikTok | $0.25 / 1.000 + $0.005/vídeo + plataforma | $1.00 | ~3.000 comentarios |
| Trustpilot | $0.50 / 1.000 + $0.007/ejecución | $0.75 | ~1.450 reseñas |
| Google Reviews | $0.60 / 1.000 | $0.75 | ~1.250 reseñas |
| Facebook | ~$0.50–1.50 / 1.000 | $1.00 | ~700–2.000 comentarios |
| Instagram | $2.30 / 1.000 | $1.00 | ~430 comentarios |

**Consejos:**

1. **Reparte el presupuesto según lo que más te importe.** Cambia los `max_gasto_usd`: si Instagram no es clave, quítale presupuesto y dáselo a X o a TikTok, que rinden 10–15 veces más por dólar.
2. **No pidas respuestas** (`incluir_respuestas = false`) salvo que las necesites, porque cada respuesta cuesta lo mismo que un comentario.
3. **Junta todos los enlaces de una red en una sola ejecución.** Así pagas una sola tarifa de inicio; los scripts ya lo hacen.
4. **No pagues dos veces lo mismo.** `acumular` evita duplicados en el JSON, pero Apify cobra lo que descarga. Al mes siguiente usa `desde` (Google, Trustpilot, X) para traer solo lo nuevo, y quita de `input/` los vídeos o posts que ya extrajiste.
5. **Prueba primero con poco**, por ejemplo `comentarios_por_video = 50`, y comprueba el coste real en [Billing](https://console.apify.com/billing).
6. **`dividir_por_estrellas` en Trustpilot** hace una pasada por cada nivel de estrellas. Solo merece la pena si una empresa tiene más reseñas de las que el actor saca de una vez (~5.000), porque cada pasada suma una tarifa de inicio.
7. **Cuidado con los datos falsos.** Algunos actores devuelven datos de demostración a las cuentas gratuitas. Los scripts los detectan (`"demo": true`), te avisan y los descartan.

## Cambiar de actor

El actor de cada red se elige en `config.cfg` (`actor = …`). Si pones otro, revisa que acepte los mismos parámetros de entrada. Si no los acepta, hay que adaptar su `scraper_<red>.py` y el conversor en `nucleo/normalizar.py`.
