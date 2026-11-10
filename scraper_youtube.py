"""
Comentarios de vídeos de YouTube con la API oficial de Google (YouTube Data API v3).
No usa Apify ni cuesta dinero: gasta cuota gratuita (10.000 unidades al día;
cada página de hasta 100 comentarios = 1 unidad).

Uso:     python scraper_youtube.py banco_santander
Lee:     marcas/<marca>/input/youtube.txt
Guarda:  marcas/<marca>/output/youtube.json
Ajustes: sección [youtube] de config.cfg
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from nucleo.config import clave, seccion
from nucleo.marcas import enlaces_o_salir, fail, guardar_y_resumir, marca_desde_argumentos

RED = "youtube"
API = "https://www.googleapis.com/youtube/v3/"


class VideoNoDisponible(Exception):
    pass


class Cliente:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.unidades = 0

    def get(self, recurso: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v not in (None, "")}
        url = f"{API}{recurso}?{urllib.parse.urlencode({**params, 'key': self.api_key})}"
        for intento in range(4):
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    self.unidades += 1
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                self.unidades += 1
                try:
                    error = json.loads(e.read().decode("utf-8")).get("error", {})
                except Exception:
                    error = {}
                razon = ((error.get("errors") or [{}])[0].get("reason")
                         or (error.get("details") or [{}])[0].get("reason") or "")
                mensaje = error.get("message", str(e))
                if razon in ("quotaExceeded", "dailyLimitExceeded"):
                    raise RuntimeError("cuota")
                if razon in ("keyInvalid", "API_KEY_INVALID", "badRequest") and "key" in mensaje.lower():
                    fail("La clave de YouTube no es válida. Revisa youtube_api_key en config.cfg.")
                if razon in ("accessNotConfigured", "SERVICE_DISABLED"):
                    fail("La API de YouTube no está activada en tu proyecto de Google Cloud. "
                         "Actívala en: https://console.cloud.google.com/apis/library/youtube.googleapis.com")
                if razon in ("commentsDisabled", "videoNotFound", "forbidden") or e.code == 404:
                    raise VideoNoDisponible(razon or mensaje)
                if e.code >= 500 and intento < 3:
                    time.sleep(2 ** intento)
                    continue
                fail(f"Error de la API de YouTube ({e.code}): {mensaje}")
            except urllib.error.URLError as e:
                if intento < 3:
                    time.sleep(2 ** intento)
                    continue
                fail(f"No se pudo conectar con YouTube: {e.reason}")
        fail("La API de YouTube no respondió tras varios intentos.")


def video_id(enlace: str) -> str | None:
    enlace = enlace.strip()
    if re.fullmatch(r"[\w-]{11}", enlace):
        return enlace
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([\w-]{11})", enlace)
    return m.group(1) if m else None


def fila(c: dict, vid: str, titulo: str, padre: str | None, respuestas: int | None) -> dict:
    s = c.get("snippet", {})
    return {
        "comment_id": c.get("id"),
        "parent_id": padre,
        "is_reply": padre is not None,
        "video_id": vid,
        "video_url": f"https://www.youtube.com/watch?v={vid}",
        "video_title": titulo,
        "comment_url": f"https://www.youtube.com/watch?v={vid}&lc={c.get('id')}",
        "text": s.get("textOriginal") or s.get("textDisplay"),
        "author": s.get("authorDisplayName"),
        "published_at": s.get("publishedAt"),
        "like_count": s.get("likeCount"),
        "reply_count": respuestas,
    }


def comentarios_video(cli: Cliente, vid: str, maximo: int, con_respuestas: bool, orden: str,
                      filas: list) -> None:
    """Añade a `filas` los comentarios del vídeo (así no se pierde nada si se agota la cuota)."""
    info = cli.get("videos", part="snippet,statistics", id=vid).get("items") or []
    if not info:
        raise VideoNoDisponible("videoNotFound")
    titulo = info[0]["snippet"].get("title")
    total = info[0].get("statistics", {}).get("commentCount", "?")
    print(f"  {vid} · {(titulo or '')[:60]} · {total} comentarios en YouTube")

    principales, token = 0, None
    while principales < maximo:
        datos = cli.get("commentThreads", part="snippet,replies", videoId=vid, maxResults=100,
                        order=orden, textFormat="plainText", pageToken=token)
        for hilo in datos.get("items", []):
            if principales >= maximo:
                break
            top = hilo["snippet"]["topLevelComment"]
            n_resp = hilo["snippet"].get("totalReplyCount", 0)
            filas.append(fila(top, vid, titulo, None, n_resp))
            principales += 1
            if con_respuestas and n_resp:
                incluidas = (hilo.get("replies") or {}).get("comments", [])
                if len(incluidas) >= n_resp:
                    filas += [fila(r, vid, titulo, top["id"], None) for r in incluidas]
                else:   # la API solo trae 5 respuestas por hilo: se piden todas
                    t = None
                    while True:
                        r = cli.get("comments", part="snippet", parentId=top["id"], maxResults=100,
                                    textFormat="plainText", pageToken=t)
                        filas += [fila(x, vid, titulo, top["id"], None) for x in r.get("items", [])]
                        t = r.get("nextPageToken")
                        if not t:
                            break
        token = datos.get("nextPageToken")
        if not token:
            break


def main(marca: str) -> None:
    cfg = seccion(RED)
    api_key = clave("youtube_api_key", "YOUTUBE_API_KEY")
    enlaces = enlaces_o_salir(marca, RED)
    maximo = cfg.entero("comentarios_por_video")
    con_respuestas = cfg.si_no("incluir_respuestas")
    orden = cfg.texto("orden")

    ids = []
    for e in enlaces:
        vid = video_id(e)
        if vid:
            ids.append(vid)
        else:
            print(f"⚠️  No reconozco este enlace de YouTube: {e}")
    ids = list(dict.fromkeys(ids))
    print(f"YouTube · {marca} · {len(ids)} vídeos")

    cli, items = Cliente(api_key), []
    for vid in ids:
        antes = len(items)
        try:
            comentarios_video(cli, vid, maximo, con_respuestas, orden, items)
            print(f"    → {len(items) - antes} comentarios y respuestas")
        except VideoNoDisponible as e:
            motivo = {"commentsDisabled": "comentarios desactivados",
                      "videoNotFound": "vídeo no encontrado o privado"}.get(str(e), str(e))
            print(f"  ⚠️  {vid}: {motivo}")
        except RuntimeError as e:
            if str(e) != "cuota":
                raise
            print("\n⚠️  Cuota diaria de YouTube agotada (se renueva a medianoche, hora del Pacífico). "
                  "Se guarda lo descargado hasta ahora.")
            break

    print(f"Cuota usada: ~{cli.unidades} unidades de 10.000 diarias")
    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_youtube.py <marca>"))
