#!/usr/bin/env python3
"""Ingesta: lee los archivos crudos de un mes y los guarda ordenados en SQLite.

Uso:
  python src/ingesta.py --reconstruir     # carga los 24 meses, uno por uno
  python src/ingesta.py --mes 2026-10     # carga o recarga un mes
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import subprocess
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from esquema import TABLAS, ddl

RAIZ = Path(__file__).resolve().parents[1]
INSUMOS = RAIZ / "01_insumos"
PROCESADOS = RAIZ / "02_procesados"
DB = PROCESADOS / "cierre.db"
MAPEO = RAIZ / "00_manuales" / "mapeo_puc_formato.xlsx"
CATALOGO = RAIZ / "04_pruebas" / "catalogo.json"
RE_CUENTA = re.compile(r"^\d{4,6}(-[A-Z]{3})?$")
RE_VIN = re.compile(r"^[A-Z0-9]{17}$")
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}")
TABLAS_MES = ["saldos", "ventas", "inventario", "gastos", "personal", "fi", "obligaciones"]


class ArchivoNoReconocido(Exception):
    """El archivo no se puede interpretar con certeza: se reporta, no se inventa."""


def normalizar(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", t)


def numero(valor):
    """Convierte 1.234.567,89 / 1234567.89 / 1234567 a número. Devuelve None si no es número."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    t = str(valor).strip().replace("$", "").replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    try:
        return float(t)
    except ValueError:
        return None


def leer_matriz(ruta: Path):
    """Devuelve filas como listas de (valor, celda), sin suponer dónde está el encabezado."""
    if ruta.suffix.lower() == ".xlsx":
        hoja = load_workbook(ruta, data_only=True).active
        return [[(c.value, c.coordinate) for c in fila] for fila in hoja.iter_rows()]
    texto = ruta.read_text(encoding="utf-8-sig")
    primera = texto.splitlines()[0] if texto else ""
    separador = ";" if primera.count(";") >= primera.count(",") else ","
    return [[(v, f"{get_column_letter(j + 1)}{i + 1}") for j, v in enumerate(fila)]
            for i, fila in enumerate(csv.reader(texto.splitlines(), delimiter=separador))]


def leer_balance(ruta: Path) -> list[dict]:
    """Detecta por contenido la columna de cuenta y la de valor (saldo o débito/crédito)."""
    matriz = [f for f in leer_matriz(ruta) if any(v not in (None, "") for v, _ in f)]
    if not matriz:
        raise ArchivoNoReconocido("El archivo está vacío.")
    ancho = max(len(f) for f in matriz)
    puntajes = [sum(1 for f in matriz if j < len(f) and RE_CUENTA.match(str(f[j][0]).strip())) for j in range(ancho)]
    col_cuenta = max(range(ancho), key=lambda j: puntajes[j])
    if puntajes[col_cuenta] < 3:
        raise ArchivoNoReconocido("No se encontró una columna con códigos de cuenta.")
    primera = next(i for i, f in enumerate(matriz) if col_cuenta < len(f) and RE_CUENTA.match(str(f[col_cuenta][0]).strip()))
    titulos = {}
    for fila in matriz[:primera]:
        for j, (v, _) in enumerate(fila):
            n = normalizar(v)
            if n.startswith("debito"):
                titulos["debito"] = j
            elif n.startswith("credito"):
                titulos["credito"] = j
            elif n.startswith("saldo"):
                titulos["saldo"] = j
    datos = [f for f in matriz[primera:] if col_cuenta < len(f) and RE_CUENTA.match(str(f[col_cuenta][0]).strip())]
    if not ({"debito", "credito"} <= titulos.keys() or "saldo" in titulos):
        numericas = [j for j in range(ancho) if j != col_cuenta and sum(1 for f in datos if j < len(f) and numero(f[j][0]) is not None) >= .9 * len(datos)]
        if len(numericas) != 1:
            raise ArchivoNoReconocido("No se pudo determinar con certeza cuál columna contiene el saldo.")
        titulos["saldo"] = numericas[0]
    filas = []
    for f in datos:
        cuenta = str(f[col_cuenta][0]).strip()
        if "saldo" in titulos:
            valor, celda = numero(f[titulos["saldo"]][0]), f[titulos["saldo"]][1]
        else:
            deb, cre = numero(f[titulos["debito"]][0]) or 0, numero(f[titulos["credito"]][0]) or 0
            valor = deb - cre if cuenta[0] in "156" else cre - deb
            celda = f[titulos["debito"] if deb else titulos["credito"]][1]
        if valor is None:
            raise ArchivoNoReconocido(f"La cuenta {cuenta} no tiene un valor numérico ({celda}).")
        filas.append({"cuenta_origen": cuenta, "saldo": int(round(valor)), "celda": celda})
    return filas


def leer_inventario(ruta: Path, sedes: set[str]) -> list[dict]:
    """El archivo llega sin encabezados: cada columna se reconoce por lo que contiene."""
    matriz = [f for f in leer_matriz(ruta) if any(v not in (None, "") for v, _ in f)]
    if not matriz:
        raise ArchivoNoReconocido("El archivo de inventario está vacío.")
    ancho = max(len(f) for f in matriz)
    columnas = [[f[j][0] for f in matriz if j < len(f)] for j in range(ancho)]
    def col(condicion):
        hallada = [j for j, vals in enumerate(columnas) if sum(1 for v in vals if condicion(v)) >= .95 * len(matriz)]
        return hallada[0] if len(hallada) == 1 else None
    lineas = {"Livianos", "Usados", "Eléctricos", "Pesados"}
    pos = {"vin": col(lambda v: bool(RE_VIN.match(str(v)))), "sede": col(lambda v: v in sedes), "linea": col(lambda v: v in lineas),
           "ingreso": col(lambda v: bool(RE_FECHA.match(str(v))))}
    numericas = [j for j, vals in enumerate(columnas) if all(isinstance(v, (int, float)) for v in vals)]
    if len(numericas) != 2 or any(v is None for v in pos.values()):
        raise ArchivoNoReconocido("No se pudieron identificar todas las columnas del inventario.")
    medias = {j: sum(columnas[j]) / len(columnas[j]) for j in numericas}
    pos["dias"], pos["costo"] = sorted(numericas, key=lambda j: medias[j])
    restantes = [j for j in range(ancho) if j not in pos.values()]
    if len(restantes) != 1:
        raise ArchivoNoReconocido("No se pudo identificar la columna de modelo.")
    pos["modelo"] = restantes[0]
    filas = []
    for f in matriz:
        d = int(f[pos["dias"]][0])
        filas.append({"vin": f[pos["vin"]][0], "sede_id": f[pos["sede"]][0], "linea": f[pos["linea"]][0], "modelo": f[pos["modelo"]][0], "dias": d,
                      "rango": "0-30" if d <= 30 else "31-60" if d <= 60 else ">60", "costo": int(f[pos["costo"]][0]), "fecha_ingreso": str(f[pos["ingreso"]][0])[:10],
                      "celda": f[pos["costo"]][1]})
    return filas


def commit_actual() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "sin-commit"


def hora_carga(mes: str, modo: str) -> str:
    if modo != "historico_simulado":
        return datetime.now().astimezone().isoformat(timespec="seconds")
    a, m = map(int, mes.split("-"))
    a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    return f"{date(a, m, 5).isoformat()}T07:00:00-05:00"


def insertar(conn, tabla: str, filas: list[dict]) -> None:
    if filas:
        cols = list(filas[0])
        conn.executemany(f"INSERT INTO {tabla} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [[f[c] for c in cols] for f in filas])


def conectar(ruta: Path = DB) -> sqlite3.Connection:
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def crear_base(conn) -> None:
    for sentencia in ddl():
        conn.execute(sentencia)
    ahora = "2024-12-05T07:00:00-05:00"
    catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
    for cid, c in catalogo["concesionarios"].items():
        conn.execute("INSERT INTO concesionarios VALUES (?,?,?,?)", (cid, c["nombre"], "04_pruebas/catalogo.json", ahora))
        for sid, nombre in c["sedes"].items():
            conn.execute("INSERT INTO sedes VALUES (?,?,?,?,?)", (sid, cid, nombre, "04_pruebas/catalogo.json", ahora))
    hoja = load_workbook(MAPEO, data_only=True).active
    for i, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
        conn.execute("INSERT INTO cuentas VALUES (?,?,?,?,?,?,?,?)", (str(fila[0]), *fila[1:6], f"00_manuales/mapeo_puc_formato.xlsx!A{i}", ahora))
    conn.commit()


def cargar_mes(conn, mes: str, modo: str = "rutina") -> dict:
    """Carga un mes completo. Es repetible: primero retira lo que hubiera de ese mes."""
    carpeta_mes = INSUMOS / mes
    if not carpeta_mes.is_dir():
        raise FileNotFoundError(f"No existe la carpeta de insumos {carpeta_mes}")
    ts, version = hora_carga(mes, modo), commit_actual()
    for tabla in TABLAS_MES + ["cargas"]:
        conn.execute(f"DELETE FROM {tabla} WHERE periodo = ?", (mes,))
    validas = {r[0] for r in conn.execute("SELECT cuenta_codigo FROM cuentas")}
    sedes_por_conc: dict[str, set[str]] = {}
    for sid, cid in conn.execute("SELECT sede_id, concesionario_id FROM sedes"):
        sedes_por_conc.setdefault(cid, set()).add(sid)
    resumen = {"archivos": 0, "filas": 0, "revisar": []}

    def registrar(cid, ruta, tabla, filas, estado="Correcto"):
        conn.execute("INSERT INTO cargas (periodo,concesionario_id,archivo,tabla,filas,estado,modo,commit_hash,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (mes, cid, str(ruta.relative_to(INSUMOS)), tabla, filas, estado, modo, version, "src/ingesta.py", ts))
        resumen["archivos"] += 1
        resumen["filas"] += filas

    def intentar(cid, ruta, tabla, funcion):
        try:
            registrar(cid, ruta, tabla, funcion())
        except (ArchivoNoReconocido, ValueError, KeyError) as e:
            registrar(cid, ruta, tabla, 0, "Revisar")
            resumen["revisar"].append(f"{ruta.relative_to(INSUMOS)}: {e}")

    for cid in sorted(sedes_por_conc):
        carpeta = carpeta_mes / cid
        if not carpeta.is_dir():
            continue
        rel = lambda r: str(r.relative_to(INSUMOS))
        for sede in sorted(sedes_por_conc[cid]):
            ruta = next((carpeta / f"{sede}_balance{e}" for e in (".xlsx", ".csv") if (carpeta / f"{sede}_balance{e}").exists()), None)
            if ruta is None:
                continue
            def balance(ruta=ruta, sede=sede):
                filas = []
                for f in leer_balance(ruta):
                    base, _, depto = f["cuenta_origen"].partition("-")
                    filas.append({"periodo": mes, "sede_id": sede, "cuenta_origen": f["cuenta_origen"], "cuenta_codigo": base if base in validas else None,
                                  "departamento": depto or None, "saldo": f["saldo"], "fuente": f"{rel(ruta)}!{f['celda']}", "cargado_en": ts})
                insertar(conn, "saldos", filas)
                return len(filas)
            intentar(cid, ruta, "saldos", balance)

        def tabla_csv(ruta, tabla, renombrar=None, extra=None):
            df = pd.read_csv(ruta) if ruta.suffix == ".csv" else pd.read_excel(ruta)
            df = df.rename(columns=renombrar or {})
            if extra:
                df = extra(df)
            prefijo = "L" if ruta.suffix == ".csv" else "A"
            df["periodo"], df["cargado_en"] = mes, ts
            df["fuente"] = [f"{rel(ruta)}!{prefijo}{i + 2}" for i in range(len(df))]
            insertar(conn, tabla, df.astype(object).where(df.notna(), None).to_dict("records"))
            return len(df)

        r = carpeta / f"ventas_vin_{mes}.csv"
        intentar(cid, r, "ventas", lambda: tabla_csv(r, "ventas", {"sede": "sede_id"}))
        r2 = carpeta / f"gastos_{mes}.csv"
        intentar(cid, r2, "gastos", lambda: tabla_csv(r2, "gastos", {"sede": "sede_id", "cuenta": "cuenta_origen"}, lambda d: d.assign(cuenta_origen=d["cuenta_origen"].astype(str))))
        r3 = carpeta / f"personal_{mes}.xlsx"
        intentar(cid, r3, "personal", lambda: tabla_csv(r3, "personal", {"sede": "sede_id"}))
        r4 = carpeta / f"fi_{mes}.csv"
        intentar(cid, r4, "fi", lambda: tabla_csv(r4, "fi", {"sede": "sede_id"}))
        r5 = carpeta / f"obligaciones_{mes}.csv"
        intentar(cid, r5, "obligaciones", lambda: tabla_csv(r5, "obligaciones", {"sede": "sede_id"}))
        r6 = carpeta / "inventario_dias.xlsx"
        def inventario():
            filas = leer_inventario(r6, sedes_por_conc[cid])
            for f in filas:
                f.update(periodo=mes, fuente=f"{rel(r6)}!{f.pop('celda')}", cargado_en=ts)
            insertar(conn, "inventario", filas)
            return len(filas)
        intentar(cid, r6, "inventario", inventario)

    estado = "Correcto" if not resumen["revisar"] else "Revisar"
    accion = f"Cargó {resumen['archivos']} archivos y {resumen['filas']} filas"
    if resumen["revisar"]:
        accion += ". Por revisar: " + " | ".join(resumen["revisar"])
    conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                 (ts, mes, "ingesta", estado, accion, "Agente de procesamiento", "src/ingesta.py", ts))
    conn.commit()
    return resumen


def exportar_csv(conn) -> None:
    carpeta = PROCESADOS / "csv"
    carpeta.mkdir(parents=True, exist_ok=True)
    for tabla in TABLAS:
        pd.read_sql_query(f"SELECT * FROM {tabla}", conn).to_csv(carpeta / f"{tabla}.csv", index=False)


def reconstruir() -> None:
    PROCESADOS.mkdir(exist_ok=True)
    DB.unlink(missing_ok=True)
    conn = conectar()
    crear_base(conn)
    meses = sorted(p.name for p in INSUMOS.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name))
    for mes in meses:
        r = cargar_mes(conn, mes, "historico_simulado")
        print(f"  {mes}: {r['archivos']} archivos, {r['filas']} filas" + (f", {len(r['revisar'])} por revisar" if r["revisar"] else ""))
    exportar_csv(conn)
    conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Carga los archivos crudos a la base de datos")
    p.add_argument("--mes")
    p.add_argument("--reconstruir", action="store_true")
    a = p.parse_args()
    if a.reconstruir or not DB.exists():
        reconstruir()
    if a.mes:
        conn = conectar()
        print(cargar_mes(conn, a.mes))
        exportar_csv(conn)
        conn.close()


if __name__ == "__main__":
    main()
