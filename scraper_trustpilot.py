"""
Reseñas de Trustpilot (actor sourabhbgp/trustpilot-review-scraper).

Uso:     python scraper_trustpilot.py banco_santander
Lee:     marcas/<marca>/input/trustpilot.txt
Guarda:  marcas/<marca>/output/trustpilot.json
Ajustes: sección [trustpilot] de config.cfg

Con dividir_por_estrellas = true hace una ejecución por cada nivel de estrellas
(1★…5★). Sirve para sacar más reseñas cuando una empresa tiene más de las que el
actor devuelve en una sola pasada.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from nucleo.apify import ejecutar_actor, mostrar_estimacion
from nucleo.config import seccion
from nucleo.marcas import enlaces_o_salir, guardar_y_resumir, marca_desde_argumentos

RED = "trustpilot"
PRECIO_EJECUCION = 0.007


def dominio(enlace: str) -> str:
    """'https://es.trustpilot.com/review/www.banco.es?page=2' -> 'www.banco.es'."""
    m = re.search(r"trustpilot\.[a-z.]+/review/([^/?#]+)", enlace)
    if m:
        return m.group(1)
    if enlace.startswith("http"):
        return urlparse(enlace).netloc
    return enlace.strip("/")


def main(marca: str) -> None:
    cfg = seccion(RED)
    empresas = list(dict.fromkeys(dominio(e) for e in enlaces_o_salir(marca, RED)))
    max_cost = cfg.decimal("max_gasto_usd")
    por_empresa = cfg.entero("resenas_por_empresa")
    estrellas = [int(s) for s in cfg.lista("estrellas")]

    pasadas = [[s] for s in (estrellas or [1, 2, 3, 4, 5])] if cfg.si_no("dividir_por_estrellas") \
        else [estrellas]
    print(f"Trustpilot · {marca} · {', '.join(empresas)}"
          + (f" · {len(pasadas)} pasadas por estrellas" if len(pasadas) > 1 else ""))
    mostrar_estimacion(len(empresas) * por_empresa * len(pasadas), cfg.decimal("precio_1000"),
                       max_cost, extra=len(pasadas) * PRECIO_EJECUCION)

    base = {
        "urls": empresas,
        "maxReviewsPerCompany": por_empresa,
        "languages": cfg.lista("idiomas"),
        "dateRange": "all",
        "sort": cfg.texto("orden"),
        "verifiedOnly": cfg.si_no("solo_verificadas"),
        "repliesOnly": cfg.si_no("solo_con_respuesta"),
        "keyword": cfg.texto("palabra_clave"),
        "topics": [],
    }
    if cfg.texto("desde"):
        base["startDate"] = cfg.texto("desde")

    items, gastado, precio = [], 0.0, cfg.decimal("precio_1000")
    for n, filtro in enumerate(pasadas, start=1):
        restante = max_cost - gastado
        if restante <= PRECIO_EJECUCION:
            print("⚠️  Tope de gasto alcanzado; se omiten las pasadas restantes.")
            break
        if len(pasadas) > 1:
            print(f"\nPasada {n}/{len(pasadas)}: {filtro[0]}★")
        resultado, _ = ejecutar_actor(cfg.texto("actor"), {**base, "stars": filtro}, restante)
        print(f"  {len(resultado)} reseñas")
        items += resultado
        gastado += len(resultado) / 1000 * precio + PRECIO_EJECUCION

    guardar_y_resumir(marca, RED, items)


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_trustpilot.py <marca>"))
