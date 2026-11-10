"""Carpetas de cada marca, lectura de enlaces y guardado de resultados."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

try:  # evita errores al imprimir emojis en consolas de Windows
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parent.parent
MARCAS_DIR = RAIZ / "marcas"

# Red -> (nombre visible, instrucciones y ejemplos para su archivo de entrada)
REDES = {
    "tiktok": ("TikTok", """\
Enlaces de VÍDEOS de TikTok, uno por línea. También vale el enlace corto o el ID del vídeo.
  https://www.tiktok.com/@santander_es/video/7653069277586541846
  https://vm.tiktok.com/XXXXXXXX/"""),
    "facebook": ("Facebook", """\
Enlaces de PUBLICACIONES de Facebook (posts, reels, vídeos o fotos), uno por línea.
  https://www.facebook.com/BancoSantander/posts/pfbid0...
  https://www.facebook.com/reel/1234567890"""),
    "instagram": ("Instagram", """\
Enlaces de PUBLICACIONES o REELS de Instagram, uno por línea.
  https://www.instagram.com/p/DAbCdEfGhIj/
  https://www.instagram.com/reel/DAbCdEfGhIj/"""),
    "x": ("X (Twitter)", """\
Enlaces de TUITS (posts) de X, uno por línea. Se descargan las respuestas a cada tuit.
  https://x.com/usuario/status/1234567890123456789
No pongas enlaces de perfiles: el actor devolvería las respuestas que ESE usuario escribe."""),
    "youtube": ("YouTube", """\
Enlaces de VÍDEOS de YouTube (normales, Shorts o directos), uno por línea. También vale el ID.
  https://www.youtube.com/watch?v=dQw4w9WgXcQ
  https://youtu.be/dQw4w9WgXcQ
  https://www.youtube.com/shorts/abcdefghijk"""),
    "google_reviews": ("Google Reviews", """\
Enlaces de LUGARES de Google Maps (oficinas, sucursales…), uno por línea.
En Google Maps abre el lugar → Compartir → Copiar enlace.
  https://maps.app.goo.gl/XXXXXXXXXXXX
  https://www.google.com/maps/place/Banco+Santander/@40.41,-3.70,17z/..."""),
    "trustpilot": ("Trustpilot", """\
Dominio de la empresa o su página de Trustpilot, uno por línea.
  bancosantander.es
  https://es.trustpilot.com/review/www.bancosantander.es"""),
}


def fail(msg: str) -> None:
    print(f"\n❌ {msg}")
    sys.exit(1)


def validar_nombre(nombre: str) -> str:
    """'Banco Santander' -> 'banco_santander' (sin tildes ni espacios)."""
    nombre = unicodedata.normalize("NFKD", nombre.strip().lower())
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"\s+", "_", nombre)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_\-]*", nombre):
        fail(f"Nombre de marca no válido: '{nombre}'. Usa minúsculas, números, '_' o '-' "
             f"(p. ej. banco_santander).")
    return nombre


def marca_desde_argumentos(uso: str) -> str:
    if len(sys.argv) < 2:
        fail(f"Falta el nombre de la marca.\n   Uso: {uso}")
    marca = validar_nombre(sys.argv[1])
    if not (MARCAS_DIR / marca).exists():
        fail(f"La marca '{marca}' no existe. Créala primero con:  python inicio.py {marca}")
    return marca


def carpeta_input(marca: str) -> Path:
    return MARCAS_DIR / marca / "input"


def carpeta_output(marca: str, red: str | None = None) -> Path:
    base = MARCAS_DIR / marca / "output"
    return base / red if red else base


def archivo_enlaces(marca: str, red: str) -> Path:
    return carpeta_input(marca) / f"{red}.txt"


def plantilla_enlaces(marca: str, red: str) -> str:
    nombre, ayuda = REDES[red]
    lineas = [f"# {nombre} · marca: {marca}", "#"]
    lineas += [f"# {l}" if l else "#" for l in ayuda.splitlines()]
    lineas += ["#", "# Las líneas que empiezan por # se ignoran. Pega tus enlaces debajo:", ""]
    return "\n".join(lineas)


def leer_enlaces(marca: str, red: str) -> list[str]:
    ruta = archivo_enlaces(marca, red)
    if not ruta.exists():
        return []
    enlaces = []
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#"):
            enlaces.append(linea)
    return list(dict.fromkeys(enlaces))   # sin duplicados, mismo orden


def enlaces_o_salir(marca: str, red: str) -> list[str]:
    enlaces = leer_enlaces(marca, red)
    if not enlaces:
        ruta = archivo_enlaces(marca, red).relative_to(RAIZ)
        print(f"ℹ️  No hay enlaces en {ruta}. Añádelos y vuelve a ejecutar.")
        sys.exit(0)
    return enlaces


def archivo_resultado(marca: str, red: str) -> Path:
    return carpeta_output(marca) / f"{red}.json"


def leer_resultado(marca: str, red: str) -> list[dict]:
    ruta = archivo_resultado(marca, red)
    if not ruta.exists():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        fail(f"{relativa(ruta)} está dañado (no es un JSON válido). Revísalo o bórralo.")
    return datos if isinstance(datos, list) else []


def guardar_resultado(marca: str, red: str, items: list[dict]) -> tuple[Path, int, int]:
    """
    Guarda en output/<red>.json. Si [general] acumular = true, añade los nuevos a los
    que ya había, sin duplicados (si se repiten, se queda la versión nueva).
    Devuelve (ruta, nuevos, total).
    """
    from nucleo.config import seccion
    from nucleo.normalizar import clave_item

    ruta = archivo_resultado(marca, red)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    acumular = seccion("general").si_no("acumular")
    previos = leer_resultado(marca, red) if acumular else []

    combinados: dict[str, dict] = {}
    for item in previos:
        combinados[clave_item(red, item)] = item
    antes = len(combinados)
    for item in items:
        combinados[clave_item(red, item)] = item
    nuevos = len(combinados) - antes

    tmp = ruta.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(list(combinados.values()), ensure_ascii=False, indent=2, default=str),
                   encoding="utf-8")
    tmp.replace(ruta)   # escritura atómica: si se corta, no se pierde el json anterior
    return ruta, nuevos, len(combinados)


def relativa(ruta: Path) -> str:
    try:
        return str(ruta.relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def guardar_y_resumir(marca: str, red: str, items: list[dict]) -> None:
    ruta, nuevos, total = guardar_resultado(marca, red, items)
    print(f"\n✅ {REDES[red][0]}: {len(items):,} recibidos · {nuevos:,} nuevos · "
          f"{total:,} en total → {relativa(ruta)}")
