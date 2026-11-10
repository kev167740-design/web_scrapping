"""
Crea las carpetas de una marca, con un archivo de entrada por cada red social.

Uso:  python inicio.py banco_santander

Resultado:
    marcas/banco_santander/
        input/   tiktok.txt, facebook.txt, instagram.txt, x.txt, youtube.txt,
                 google_reviews.txt, trustpilot.txt   ← pega aquí los enlaces
        output/  tiktok.json, facebook.json… (uno por red) y union.json

Si la marca ya existe, no se borra nada: solo se crean los archivos que falten.
"""

import shutil
import sys

from nucleo.config import CFG, EJEMPLO
from nucleo.marcas import (REDES, archivo_enlaces, carpeta_input, carpeta_output, fail,
                           leer_enlaces, plantilla_enlaces, relativa, validar_nombre)


def main() -> None:
    if len(sys.argv) < 2:
        fail("Falta el nombre de la marca.\n   Uso: python inicio.py banco_santander")
    marca = validar_nombre(sys.argv[1])

    carpeta_input(marca).mkdir(parents=True, exist_ok=True)
    carpeta_output(marca).mkdir(parents=True, exist_ok=True)

    if not CFG.exists() and EJEMPLO.exists():
        shutil.copy(EJEMPLO, CFG)
        print("Creado config.cfg: pon ahí tus claves (Apify, OpenAI, YouTube).\n")

    print(f"Marca: {marca}\n")
    for red, (nombre, _) in REDES.items():
        ruta = archivo_enlaces(marca, red)
        if ruta.exists():
            estado = f"ya existía · {len(leer_enlaces(marca, red))} enlaces"
        else:
            ruta.write_text(plantilla_enlaces(marca, red), encoding="utf-8")
            estado = "creado"
        print(f"  {nombre:<16} {relativa(ruta):<45} {estado}")

    print(f"""
✅ Listo. Siguientes pasos:
  1. Pega los enlaces en los archivos de {relativa(carpeta_input(marca))}/
  2. Ejecuta el scraper de cada red, por ejemplo:
       python scraper_tiktok.py {marca}
     o todos los que tengan enlaces:
       python scraper_todos.py {marca}
  3. Une los resultados:
       python union.py {marca}""")


if __name__ == "__main__":
    main()
