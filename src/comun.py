"""Utilidades compartidas: rutas y formato colombiano de cifras."""
from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "02_procesados" / "cierre.db"
SALIDAS = RAIZ / "03_salidas"
NOTA = "Datos simulados"
PALETA = {"crema": "#F3EDE2", "navy": "#1F4E79", "teal": "#1D6B67", "terracota": "#B4532A", "ciruela": "#6B3A63"}
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _co(texto: str) -> str:
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def numero(valor, decimales: int = 0) -> str:
    return _co(f"{valor:,.{decimales}f}")


def cop(valor) -> str:
    return f"{'-' if valor < 0 else ''}${numero(abs(valor))}"


def millones(valor, decimales: int = 1) -> str:
    return f"{'-' if valor < 0 else ''}${numero(abs(valor) / 1e6, decimales)} M"


def miles_millones(valor, decimales: int = 1) -> str:
    return f"{'-' if valor < 0 else ''}${numero(abs(valor) / 1e9, decimales)} mil millones"


def pct(valor, decimales: int = 1) -> str:
    return f"{numero(valor * 100, decimales)} %"


def nombre_mes(periodo: str) -> str:
    anio, mes = periodo.split("-")
    return f"{MESES_ES[int(mes) - 1]} de {anio}"
