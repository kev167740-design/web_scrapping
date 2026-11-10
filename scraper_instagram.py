"""
Comentarios de publicaciones y reels de Instagram (actor apify/instagram-comment-scraper).

Uso:     python scraper_instagram.py banco_santander
Lee:     marcas/<marca>/input/instagram.txt
Guarda:  marcas/<marca>/output/instagram.json
Ajustes: sección [instagram] de config.cfg
"""

from __future__ import annotations

from nucleo.apify import ejecutar_actor, mostrar_estimacion
from nucleo.config import seccion
from nucleo.marcas import enlaces_o_salir, guardar_y_resumir, marca_desde_argumentos

RED = "instagram"


def main(marca: str) -> None:
    cfg = seccion(RED)
    enlaces = enlaces_o_salir(marca, RED)
    max_cost = cfg.decimal("max_gasto_usd")
    por_post = cfg.entero("comentarios_por_post")

    print(f"Instagram · {marca} · {len(enlaces)} publicaciones")
    mostrar_estimacion(len(enlaces) * por_post, cfg.decimal("precio_1000"), max_cost)

    run_input = {
        "directUrls": enlaces,
        "resultsLimit": por_post,                  # por publicación
        "includeNestedComments": cfg.si_no("incluir_respuestas"),
    }
    items, _ = ejecutar_actor(cfg.texto("actor"), run_input, max_cost)
    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_instagram.py <marca>"))
