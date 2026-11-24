#!/usr/bin/env python3
"""Prepara los datos del tablero: copia la base a docs/data y exporta meta.json.

Uso: python src/tablero.py --mes 2026-10
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime

from comun import DB, NOTA, RAIZ
from esquema import TABLAS, TRAZA
from openpyxl import load_workbook

from ingesta import HOJAS, conectar, libros_del_mes, rol_hoja

DESTINO = RAIZ / "docs" / "data"
DESCRIPCIONES = {
    "CLAUDE.md": "Manual del agente: rol, reglas y pasos del cierre.",
    "README.md": "Explicación del proyecto para personas no técnicas.",
    "run_cierre.py": "Un solo comando para ejecutar todo el cierre.",
    "requirements.txt": "Lista de librerías gratuitas que usa el proyecto.",
    "00_manuales": "Instrucciones del agente, homologación y diccionario.",
    "00_manuales/instrucciones_consolidacion.md": "Procedimiento para consolidar y validar.",
    "00_manuales/instrucciones_pronostico.md": "Procedimiento para proyectar el cierre del año.",
    "00_manuales/instrucciones_reporte.md": "Procedimiento para redactar los reportes.",
    "00_manuales/mapeo_puc_formato.xlsx": "Tabla que traduce cuentas PUC al formato.",
    "00_manuales/diccionario_de_datos.md": "Qué significa cada campo de cada tabla.",
    "01_insumos": "Un reporte mensual (libro de Excel) por concesionario. Nunca se editan.",
    "02_procesados": "Tablas ordenadas y base de datos SQLite.",
    "02_procesados/cierre.db": "La base de datos del cierre.",
    "02_procesados/csv": "Cada tabla en CSV, visible directamente en GitHub.",
    "03_salidas": "Reportes, gráficos, audios y Excel de cada mes.",
    "04_pruebas": "Generador de datos simulados y pruebas automáticas.",
    "04_pruebas/generar_datos.py": "Crea los 24 meses de archivos simulados.",
    "src": "El código de los agentes.",
    "src/ingesta.py": "Lee archivos desordenados y los carga a la base.",
    "src/procesamiento.py": "Agente de procesamiento: consolida y valida.",
    "src/pronostico.py": "Agente predictivo: escenarios y sensibilidad.",
    "src/reporte.py": "Agente de reporting: PDF, audio y guion.",
    "src/motor.py": "Adaptador para cambiar de motor de IA.",
    "src/tablero.py": "Prepara los datos de este tablero.",
    "src/esquema.py": "Definición de las tablas de la base.",
    "docs": "Este tablero, publicado con GitHub Pages.",
    "docs/guion_demo.md": "Guion paso a paso para la demostración.",
    "docs/data": "Base de datos y archivos que lee el tablero.",
    ".github/workflows/cierre_mensual.yml": "La rutina automática de cada mes.",
}


def git(*args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def repositorio() -> str | None:
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", git("remote", "get-url", "origin"))
    return m.group(1) if m else None


def esquema_json() -> dict:
    salida = {}
    for tabla, d in TABLAS.items():
        columnas = []
        for n, t, r, sig, ej in d["columnas"] + TRAZA:
            ref = re.search(r"REFERENCES (\w+)\((\w+)\)", r)
            columnas.append({"nombre": n, "tipo": t, "pk": "PRIMARY KEY" in r or n in (d.get("pk") or ""), "fk": ref.group(1) if ref else None, "significado": sig, "ejemplo": ej})
        salida[tabla] = {"descripcion": d["descripcion"], "script": d["script"], "columnas": columnas}
    return salida


def celda_texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str) and v.startswith("="):
        return "(fórmula)"
    texto = str(v)
    return texto if len(texto) <= 16 else texto[:15] + "…"  # Títulos largos no deben esconder las columnas de sedes.


def vistas_crudas(conn) -> dict:
    """Muestra real de cada libro: la hoja Balance (encabezado y filas 2205) y el mapa de sus hojas."""
    meses = [m[0] for m in conn.execute("SELECT DISTINCT periodo FROM saldos ORDER BY 1")]
    vistas = {}
    for mes in meses:
        vistas[mes] = {}
        for cid, ruta in libros_del_mes(mes):
            wb = load_workbook(ruta)  # Sin data_only: se ven las fórmulas tal como las dejó el concesionario.
            filas = [[(c.value, c.coordinate) for c in f] for f in wb["Balance"].iter_rows()]
            seleccion = []
            for i, f in enumerate(filas):
                es_2205 = any(str(v).strip() == "2205" for v, _ in f)
                if i < 8 or es_2205:
                    seleccion.append({"n": i + 1, "celdas": [celda_texto(v) for v, _ in f], "marca": es_2205})
            hojas = []
            for ws in wb.worksheets:
                rol = rol_hoja(ws.title)
                contenido, reto, tabla = HOJAS.get(rol, ("", "", "—"))
                hojas.append({"hoja": ws.title, "contenido": contenido, "reto": reto, "tabla": tabla, "filas": ws.max_row})
            vistas[mes][cid] = {"archivo": str(ruta.relative_to(RAIZ)), "hoja": "Balance", "total_filas": len(filas), "filas": seleccion, "hojas": hojas}
    return vistas


def arbol() -> list[dict]:
    excluir = {".git", ".venv", "__pycache__", ".pytest_cache", ".DS_Store"}
    def nodo(ruta, nivel):
        rel = ruta.relative_to(RAIZ).as_posix()
        item = {"nombre": ruta.name, "ruta": rel, "tipo": "carpeta" if ruta.is_dir() else "archivo", "descripcion": DESCRIPCIONES.get(rel, "")}
        if ruta.is_dir():
            hijos = sorted((h for h in ruta.iterdir() if h.name not in excluir), key=lambda h: (h.is_file(), h.name))
            if rel == "01_insumos" and hijos:
                item["nota"] = f"{len(hijos)} meses; se muestra el último"
                hijos = hijos[-1:]
            elif rel == "03_salidas" and hijos:
                hijos = hijos[-1:]
            elif rel == "docs/data/reportes" or rel == "02_procesados/csv":
                item["nota"] = f"{len(hijos)} archivos"
                hijos = []
            if nivel < 4:
                item["hijos"] = [nodo(h, nivel + 1) for h in hijos]
        return item
    return [nodo(h, 0) for h in sorted((h for h in RAIZ.iterdir() if h.name not in excluir), key=lambda h: (h.is_file(), h.name))]


def exportar(conn, mes: str) -> dict:
    DESTINO.mkdir(parents=True, exist_ok=True)
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    shutil.copy(DB, DESTINO / "cierre.db")
    commits = []
    for linea in git("log", "--date=iso-strict", "--pretty=format:%h|%ad|%s", "-n", "60").splitlines():
        h, f, s = linea.split("|", 2)
        commits.append({"hash": h, "fecha": f, "mensaje": s})
    meta = {"nota": NOTA, "mes": mes, "repo": repositorio(), "rama": git("rev-parse", "--abbrev-ref", "HEAD") or "main", "commit": git("rev-parse", "--short", "HEAD"),
            "generado": datetime.now().astimezone().isoformat(timespec="seconds"), "db_bytes": DB.stat().st_size, "db_ruta": "02_procesados/cierre.db",
            "esquema": esquema_json(), "vistas": vistas_crudas(conn), "arbol": arbol(), "commits": commits}
    (DESTINO / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def main() -> None:
    p = argparse.ArgumentParser(description="Prepara los datos del tablero")
    p.add_argument("--mes", default="2026-10")
    a = p.parse_args()
    conn = conectar()
    m = exportar(conn, a.mes)
    conn.close()
    print(f"Tablero listo: base de {m['db_bytes'] / 1e6:.1f} MB y {len(m['esquema'])} tablas. {NOTA}.")


if __name__ == "__main__":
    main()
