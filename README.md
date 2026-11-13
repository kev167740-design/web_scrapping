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

- **`[claves]`:** claves de Apify, OpenAI y YouTube (Google).
- **`[general]`:** el tiempo máximo de cada ejecución y si los resultados se acumulan.
- **Una sección por red** con todos los parámetros de su actor: comentarios por vídeo o publicación, respuestas, orden, idioma, fechas, tiempo por vídeo, filtros y **tope de gasto**.

`config.cfg` está en `.gitignore`, así que las claves no se suben a GitHub.

## Estructura de cada marca

```
marcas/banco_santander/
├── input/
│   ├── tiktok.txt            ← enlaces de vídeos
│   ├── facebook.txt          ← enlaces de publicaciones
│   ├── instagram.txt         ← enlaces de posts o reels
│   ├── x.txt                 ← enlaces de tweets (/status/…)
│   ├── youtube.txt           ← enlaces de vídeos
│   ├── google_reviews.txt    ← enlaces de lugares de Google Maps
│   └── trustpilot.txt        ← página de Trustpilot
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
| `scraper_x.py <marca>` | Respuestas a tweets de X |
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


