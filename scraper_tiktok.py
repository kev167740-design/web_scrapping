"""
Comentarios de vídeos de TikTok (actor thescrapelab/tiktok-comments-scraper).

Uso:     python scraper_tiktok.py banco_santander
Lee:     marcas/<marca>/input/tiktok.txt
Guarda:  marcas/<marca>/output/tiktok.json
Ajustes: sección [tiktok] de config.cfg
"""

from __future__ import annotations

from nucleo.apify import ejecutar_actor, mostrar_estimacion
from nucleo.config import seccion
from nucleo.marcas import enlaces_o_salir, guardar_y_resumir, marca_desde_argumentos

RED = "tiktok"
VIDEOS_POR_EJECUCION = 100   # límite del actor
PRECIO_VIDEO = 0.005


def main(marca: str) -> None:
    cfg = seccion(RED)
    enlaces = enlaces_o_salir(marca, RED)
    max_cost = cfg.decimal("max_gasto_usd")
    precio = cfg.decimal("precio_1000")
    respuestas = cfg.si_no("incluir_respuestas")
    por_video = cfg.entero("comentarios_por_video")
    por_comentario = cfg.entero("respuestas_por_comentario") if respuestas else 0
    filas_por_video = por_video * (1 + por_comentario)

    print(f"TikTok · {marca} · {len(enlaces)} vídeos")
    mostrar_estimacion(len(enlaces) * filas_por_video, precio, max_cost,
                       extra=len(enlaces) * PRECIO_VIDEO)

    items, gastado = [], 0.0
    lotes = [enlaces[i:i + VIDEOS_POR_EJECUCION] for i in range(0, len(enlaces), VIDEOS_POR_EJECUCION)]
    for n, lote in enumerate(lotes, start=1):
        restante = max_cost - gastado
        if restante < PRECIO_VIDEO:
            print(f"⚠️  Tope de gasto alcanzado: quedan {sum(map(len, lotes[n - 1:]))} vídeos sin procesar.")
            break
        if len(lotes) > 1:
            print(f"\nLote {n}/{len(lotes)} ({len(lote)} vídeos)")
        run_input = {
            "videoUrls": lote,
            "maxCommentsPerVideo": por_video,
            "includeReplies": respuestas,
            "maxRepliesPerComment": por_comentario,
            "maxSecondsPerVideo": cfg.entero("segundos_por_video"),
            "useResidentialProxy": cfg.si_no("proxy_residencial"),
        }
        resultado, _ = ejecutar_actor(cfg.texto("actor"), run_input, restante)

        estados = [i for i in resultado if i.get("record_type") == "video_status"]
        filas = [i for i in resultado if i.get("record_type") in ("comment", "reply")]
        for s in estados:
            motivo = f" · motivo: {s['stop_reason']}" if s.get("stop_reason") else ""
            print(f"  - {s.get('video_id') or s.get('video_url')}: {s.get('status')} · "
                  f"{s.get('top_level_comments', '?')} comentarios{motivo}")
            if s.get("stop_reason") == "time_limit":
                print("    ↳ se quedó sin tiempo: sube segundos_por_video en config.cfg")
        ok = sum(1 for s in estados if s.get("status") == "succeeded")
        gastado += len(filas) / 1000 * precio + ok * PRECIO_VIDEO
        items += filas

    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_tiktok.py <marca>"))
