"""
Reseñas de Google Maps (actor compass/google-maps-reviews-scraper).

Uso:     python scraper_google_reviews.py banco_santander
Lee:     marcas/<marca>/input/google_reviews.txt
Guarda:  marcas/<marca>/output/google_reviews.json
Ajustes: sección [google_reviews] de config.cfg
"""

from __future__ import annotations

from nucleo.apify import ejecutar_actor, mostrar_estimacion
from nucleo.config import seccion
from nucleo.marcas import enlaces_o_salir, guardar_y_resumir, marca_desde_argumentos

RED = "google_reviews"


def main(marca: str) -> None:
    cfg = seccion(RED)
    enlaces = enlaces_o_salir(marca, RED)
    max_cost = cfg.decimal("max_gasto_usd")
    por_lugar = cfg.entero("resenas_por_lugar")
    orden = cfg.texto("orden")

    print(f"Google Reviews · {marca} · {len(enlaces)} lugares")
    mostrar_estimacion(len(enlaces) * por_lugar, cfg.decimal("precio_1000"), max_cost)

    run_input = {
        "startUrls": [{"url": u} for u in enlaces],
        "maxReviews": por_lugar,
        "reviewsSort": orden,
        "language": cfg.texto("idioma"),
        "reviewsOrigin": cfg.texto("origen"),
        "personalData": cfg.si_no("datos_personales"),
    }
    desde = cfg.texto("desde")
    if desde:
        if orden != "newest":
            print("⚠️  'desde' solo funciona con orden = newest; se ignora.")
        else:
            run_input["reviewsStartDate"] = desde
    if cfg.texto("filtro_texto"):
        run_input["reviewsFilterString"] = cfg.texto("filtro_texto")

    items, _ = ejecutar_actor(cfg.texto("actor"), run_input, max_cost)
    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_google_reviews.py <marca>"))
