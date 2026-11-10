"""
Une los resultados de todas las redes de una marca en un solo archivo con
estructura común.

Uso:     python union.py banco_santander
Lee:     marcas/<marca>/output/<red>.json   (los que existan)
Guarda:  marcas/<marca>/output/union.json

Campos de cada registro:
    brand, platform, record_type (comment / reply / review), id, parent_id,
    source_url, source_name, url, text, title, rating, author, created_at,
    likes, replies, language, owner_reply
"""

from __future__ import annotations

import json
from collections import Counter

from nucleo.marcas import (REDES, archivo_resultado, carpeta_output, leer_resultado,
                           marca_desde_argumentos, relativa)
from nucleo.normalizar import normalizar


def main(marca: str) -> None:
    registros: dict[tuple, dict] = {}
    print(f"Unión · {marca}\n")
    print(f"  {'Red':<16}{'crudos':>8}{'registros':>11}{'con texto':>11}   tipos")

    for red, (nombre, _) in REDES.items():
        if not archivo_resultado(marca, red).exists():
            continue
        crudos = leer_resultado(marca, red)
        filas = [r for item in crudos for r in normalizar(red, item, marca)]
        for r in filas:
            registros[(r["platform"], r["id"])] = r
        con_texto = sum(1 for r in filas if r["text"])
        tipos = ", ".join(f"{k} {v}" for k, v in Counter(r["record_type"] for r in filas).items())
        print(f"  {nombre:<16}{len(crudos):>8}{len(filas):>11}{con_texto:>11}   {tipos}")

        # Aviso si la estructura del actor no coincide con la esperada
        sin_texto = sum(1 for r in filas if not r["text"] and r["rating"] is None)
        if crudos and (not filas or sin_texto / len(filas) > 0.5):
            claves = sorted(crudos[0].keys())[:25] if isinstance(crudos[0], dict) else []
            print(f"    ⚠️  {nombre}: la mayoría de registros no tienen texto. Puede que el actor haya "
                  f"cambiado su estructura.\n       Campos del primer resultado: {', '.join(claves)}")

    if not registros:
        print("\nNo hay resultados todavía. Ejecuta antes algún scraper_<red>.py.")
        return

    union = sorted(registros.values(), key=lambda r: r["created_at"] or "", reverse=True)
    ruta = carpeta_output(marca) / "union.json"
    ruta.write_text(json.dumps(union, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ {len(union):,} registros → {relativa(ruta)}")


if __name__ == "__main__":
    main(marca_desde_argumentos("python union.py <marca>"))
