"""Lee config.cfg (claves y parámetros de cada red)."""

from __future__ import annotations

import configparser
import os
import shutil

from nucleo.marcas import RAIZ, fail

CFG = RAIZ / "config.cfg"
EJEMPLO = RAIZ / "config.ejemplo.cfg"
_parser: configparser.ConfigParser | None = None


def _cargar() -> configparser.ConfigParser:
    global _parser
    if _parser is None:
        if not CFG.exists():
            if not EJEMPLO.exists():
                fail("No encuentro config.cfg ni config.ejemplo.cfg.")
            shutil.copy(EJEMPLO, CFG)
            print("ℹ️  Se creó config.cfg a partir de config.ejemplo.cfg. Pon ahí tus claves.")
        parser = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=(";",))
        try:
            parser.read(CFG, encoding="utf-8-sig")
        except configparser.Error as e:
            fail(f"config.cfg tiene un error de formato: {e}")
        _parser = parser
    return _parser


class Seccion:
    """Acceso con tipo a una sección de config.cfg, con mensajes de error claros."""

    def __init__(self, nombre: str):
        parser = _cargar()
        if not parser.has_section(nombre):
            fail(f"Falta la sección [{nombre}] en config.cfg (cópiala de config.ejemplo.cfg).")
        self.nombre = nombre
        self._s = parser[nombre]

    def _valor(self, clave: str) -> str:
        if clave not in self._s:
            fail(f"Falta '{clave}' en la sección [{self.nombre}] de config.cfg.")
        return self._s[clave].strip()

    def texto(self, clave: str) -> str:
        return self._valor(clave)

    def entero(self, clave: str, opcional: bool = False) -> int | None:
        v = self._valor(clave)
        if v == "" and opcional:
            return None
        try:
            return int(v)
        except ValueError:
            fail(f"[{self.nombre}] {clave} debe ser un número entero (ahora: '{v}').")

    def decimal(self, clave: str) -> float:
        v = self._valor(clave).replace(",", ".")
        try:
            return float(v)
        except ValueError:
            fail(f"[{self.nombre}] {clave} debe ser un número (ahora: '{v}').")

    def si_no(self, clave: str) -> bool:
        v = self._valor(clave).lower()
        if v in ("true", "sí", "si", "yes", "1"):
            return True
        if v in ("false", "no", "0"):
            return False
        fail(f"[{self.nombre}] {clave} debe ser true o false (ahora: '{v}').")

    def lista(self, clave: str) -> list[str]:
        return [x.strip() for x in self._valor(clave).split(",") if x.strip()]


def seccion(nombre: str) -> Seccion:
    return Seccion(nombre)


def clave(nombre: str, variable_entorno: str, obligatoria: bool = True) -> str:
    """Lee una clave de [claves]; si está vacía, usa la variable de entorno."""
    parser = _cargar()
    valor = parser.get("claves", nombre, fallback="").strip() or os.environ.get(variable_entorno, "").strip()
    if not valor and obligatoria:
        fail(f"Falta '{nombre}' en la sección [claves] de config.cfg "
             f"(o la variable de entorno {variable_entorno}).")
    return valor
