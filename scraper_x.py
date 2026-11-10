"""
Respuestas a tuits de X / Twitter (actor xquik/x-reply-scraper).

Uso:     python scraper_x.py banco_santander
Lee:     marcas/<marca>/input/x.txt
Guarda:  marcas/<marca>/output/x.json
Ajustes: sección [x] de config.cfg
"""

from __future__ import annotations

from nucleo.apify import ejecutar_actor, mostrar_estimacion
from nucleo.config import seccion
from nucleo.marcas import enlaces_o_salir, guardar_y_resumir, marca_desde_argumentos

RED = "x"


def main(marca: str) -> None:
    cfg = seccion(RED)
    enlaces = enlaces_o_salir(marca, RED)
    raros = [u for u in enlaces if "/status/" not in u and not u.isdigit()]
    if raros:
        print(f"⚠️  Estos enlaces no parecen tuits (les falta '/status/'): "
              f"{', '.join(raros[:3])}{'…' if len(raros) > 3 else ''}")
    max_cost = cfg.decimal("max_gasto_usd")
    por_tuit = cfg.entero("respuestas_por_tuit")
    total = len(enlaces) * por_tuit

    print(f"X · {marca} · {len(enlaces)} tuits")
    mostrar_estimacion(total, cfg.decimal("precio_1000"), max_cost)

    run_input = {
        "startUrls": enlaces,
        "maxItemsPerTarget": por_tuit,
        "maxItems": total,
        "scope": cfg.texto("alcance"),
        "maxDepth": cfg.entero("profundidad"),
        "sort": cfg.texto("orden"),
        "includeOriginalPost": False,
        "excludeOriginalAuthor": cfg.si_no("excluir_autor_original"),
        "includeHiddenReplies": cfg.si_no("incluir_ocultas"),
    }
    opcionales = {"lang": cfg.texto("idioma"), "since": cfg.texto("desde"),
                  "until": cfg.texto("hasta"), "minLikes": cfg.entero("min_likes", opcional=True)}
    run_input.update({k: v for k, v in opcionales.items() if v not in ("", None)})

    items, _ = ejecutar_actor(cfg.texto("actor"), run_input, max_cost)
    items = [i for i in items if i.get("id") or i.get("text")]   # quita registros de control del actor
    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_x.py <marca>"))
