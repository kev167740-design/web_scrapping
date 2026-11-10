"""
Ejecuta, una tras otra, todas las redes que tengan enlaces en input/.

Uso:  python scraper_todos.py banco_santander
"""

from __future__ import annotations

import importlib
import traceback

from nucleo.marcas import REDES, leer_enlaces, marca_desde_argumentos


def main(marca: str) -> None:
    resultados = {}
    for red, (nombre, _) in REDES.items():
        if not leer_enlaces(marca, red):
            resultados[nombre] = "sin enlaces"
            continue
        print(f"\n{'=' * 64}\n{nombre.upper()}\n{'=' * 64}")
        try:
            importlib.import_module(f"scraper_{red}").main(marca)
            resultados[nombre] = "ok"
        except SystemExit as e:   # los scrapers usan sys.exit al fallar
            resultados[nombre] = "ok" if e.code in (0, None) else "error (ver arriba)"
        except Exception:
            traceback.print_exc()
            resultados[nombre] = "error inesperado (ver arriba)"

    print(f"\n{'=' * 64}\nRESUMEN\n{'=' * 64}")
    for nombre, estado in resultados.items():
        print(f"  {nombre:<16} {estado}")
    print(f"\nSiguiente paso:  python union.py {marca}")


if __name__ == "__main__":
    main(marca_desde_argumentos("python scraper_todos.py <marca>"))
