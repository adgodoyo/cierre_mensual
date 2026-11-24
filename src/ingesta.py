#!/usr/bin/env python3
"""Ingesta: lee el reporte mensual de cada concesionario (un libro de Excel) y lo guarda ordenado en SQLite.

Uso:
  python src/ingesta.py --reconstruir     # carga los 24 meses, uno por uno
  python src/ingesta.py --mes 2026-10     # carga o recarga un mes
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import unicodedata
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from esquema import TABLAS, ddl

RAIZ = Path(__file__).resolve().parents[1]
INSUMOS = RAIZ / "01_insumos"
PROCESADOS = RAIZ / "02_procesados"
DB = PROCESADOS / "cierre.db"
MAPEO = RAIZ / "00_manuales" / "mapeo_puc_formato.xlsx"
CATALOGO = RAIZ / "04_pruebas" / "catalogo.json"
RE_LIBRO = re.compile(r"^reporte_mensual_([A-Z]{3})_(\d{4}-\d{2})\.xlsx$")
RE_CODIGO = re.compile(r"^\d{4,6}$")
RE_VIN = re.compile(r"^[A-Z0-9]{17}$")
TABLAS_MES = ["saldos", "ventas", "inventario", "gastos", "personal", "fi", "obligaciones"]
DEPTOS = {"livianos": "LIV", "usados": "USA", "electricos": "ELE", "pesados": "PES", "fi": "FYI", "servicio": "SER", "repuestos": "REP", "accesorios": "ACC", "administrativo": "ADM"}

# Qué trae cada hoja y qué tiene que resolver el agente. El tablero muestra esta tabla.
HOJAS = {
    "portada": ("Datos del concesionario y del periodo", "Confirma concesionario, sedes y mes", "—"),
    "balance": ("Balance general por sede, con secciones y subtotales", "Toma solo filas con código de cuenta; ignora títulos y subtotales", "saldos"),
    "resultados": ("Resultados por departamento de una sede", "Une código y columna: 4135 + Livianos = 4135-LIV", "saldos"),
    "ventas": ("Una fila por vehículo vendido", "Encuentra el encabezado aunque haya títulos arriba", "ventas"),
    "inventario": ("Vehículos en patio, sin encabezados", "Reconoce cada columna por lo que contiene", "inventario"),
    "librodegastos": ("Pagos del mes a proveedores", "Base para detectar duplicados, montos atípicos y fines de semana", "gastos"),
    "personal": ("Personas y costo por rol y sede", "Lee un encabezado combinado de dos filas", "personal"),
    "fi": ("Créditos, pólizas y comisiones por sede", "Convierte las columnas de sedes en filas", "fi"),
    "obligaciones": ("Cupos wholesale por entidad", "Convierte la tasa escrita como texto ('1,198 %') en número", "obligaciones"),
    "validador": ("Controles propios del concesionario (fórmulas)", "No se carga: el agente rehace los controles por su cuenta", "—"),
}


class ArchivoNoReconocido(Exception):
    """La hoja no se puede interpretar con certeza: se reporta, no se inventa."""


def normalizar(texto) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", t)


def rol_hoja(titulo: str) -> str | None:
    n = normalizar(titulo)
    return next((k for k in HOJAS if n.startswith(k)), None)


def numero(valor):
    """Convierte 1.234.567,89 / 1234567.89 / 1234567 a número. Devuelve None si no es número."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    t = str(valor).strip().replace("$", "").replace(" ", "").replace("%", "")
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


def fecha_iso(valor) -> str:
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%Y-%m-%d")
    return str(valor)[:10]


def matriz(ws):
    """Filas no vacías como listas de (valor, celda), sin suponer dónde está el encabezado."""
    return [f for f in ([(c.value, c.coordinate) for c in fila] for fila in ws.iter_rows()) if any(v not in (None, "") for v, _ in f)]


def leer_matriz(ruta: Path, hoja: str | None = None):
    wb = load_workbook(ruta, data_only=True)
    return matriz(wb[hoja] if hoja else wb.active)


def leer_cuentas(ws, columnas: dict[str, str]) -> list[dict]:
    """Tabla con códigos de cuenta en filas y sedes o departamentos en columnas. Los subtotales no tienen código."""
    m = matriz(ws)
    if not m:
        raise ArchivoNoReconocido("La hoja está vacía.")
    ancho = max(len(f) for f in m)
    es_codigo = lambda f, j: j < len(f) and bool(RE_CODIGO.match(str(f[j][0] or "").strip()))
    puntajes = [sum(1 for f in m if es_codigo(f, j)) for j in range(ancho)]
    col = max(range(ancho), key=lambda j: puntajes[j])
    if puntajes[col] < 3:
        raise ArchivoNoReconocido("No se encontró una columna con códigos de cuenta.")
    primera = next(i for i, f in enumerate(m) if es_codigo(f, col))
    encabezado = {}
    for f in m[:primera]:
        for j, (v, _) in enumerate(f):
            if normalizar(v) in columnas:
                encabezado[j] = columnas[normalizar(v)]
    if not encabezado:
        raise ArchivoNoReconocido("No se reconocieron las columnas de valores.")
    filas = []
    for f in m[primera:]:
        if not es_codigo(f, col):
            continue  # Títulos de sección y subtotales: no se suman dos veces.
        for j, clave in encabezado.items():
            v = numero(f[j][0]) if j < len(f) else None
            if v is not None:
                filas.append({"cuenta": str(f[col][0]).strip(), "clave": clave, "saldo": int(round(v)), "celda": f[j][1]})
    return filas


def leer_tabla(ws, campos: dict[str, str]) -> list[dict]:
    """Tabla con encabezado en cualquier fila: lo busca por los nombres de las columnas."""
    m = matriz(ws)
    for i, f in enumerate(m):
        mapa = {j: campos[normalizar(v)] for j, (v, _) in enumerate(f) if normalizar(v) in campos}
        if len(mapa) == len(campos):
            break
    else:
        raise ArchivoNoReconocido(f"No se encontró el encabezado con {', '.join(campos.values())}.")
    filas = []
    for f in m[i + 1:]:
        fila = {campo: (f[j][0] if j < len(f) else None) for j, campo in mapa.items()}
        if all(v in (None, "") for v in fila.values()) or normalizar(fila.get(next(iter(mapa.values())))) == "total":
            continue
        fila["celda"] = f[min(mapa)][1]
        filas.append(fila)
    return filas


def leer_inventario(ws, sedes: dict[str, str]) -> list[dict]:
    """La hoja llega sin encabezados: cada columna se reconoce por lo que contiene."""
    m = matriz(ws)
    if not m:
        raise ArchivoNoReconocido("La hoja de inventario está vacía.")
    ancho = max(len(f) for f in m)
    columnas = [[f[j][0] for f in m if j < len(f)] for j in range(ancho)]

    def col(condicion):
        hallada = [j for j, vals in enumerate(columnas) if sum(1 for v in vals if condicion(v)) >= .95 * len(m)]
        return hallada[0] if len(hallada) == 1 else None
    lineas = {"Livianos", "Usados", "Eléctricos", "Pesados"}
    pos = {"vin": col(lambda v: bool(RE_VIN.match(str(v)))), "sede": col(lambda v: normalizar(v) in sedes), "linea": col(lambda v: v in lineas),
           "ingreso": col(lambda v: isinstance(v, (datetime, date)) or bool(re.match(r"^\d{4}-\d{2}-\d{2}", str(v))))}
    numericas = [j for j, vals in enumerate(columnas) if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals)]
    if len(numericas) != 2 or any(v is None for v in pos.values()):
        raise ArchivoNoReconocido("No se pudieron identificar todas las columnas del inventario.")
    medias = {j: sum(columnas[j]) / len(columnas[j]) for j in numericas}
    pos["dias"], pos["costo"] = sorted(numericas, key=lambda j: medias[j])
    restantes = [j for j in range(ancho) if j not in pos.values()]
    if len(restantes) != 1:
        raise ArchivoNoReconocido("No se pudo identificar la columna de modelo.")
    pos["modelo"] = restantes[0]
    filas = []
    for f in m:
        d = int(f[pos["dias"]][0])
        filas.append({"vin": f[pos["vin"]][0], "sede_id": sedes[normalizar(f[pos["sede"]][0])], "linea": f[pos["linea"]][0], "modelo": f[pos["modelo"]][0], "dias": d,
                      "rango": "0-30" if d <= 30 else "31-60" if d <= 60 else ">60", "costo": int(f[pos["costo"]][0]), "fecha_ingreso": fecha_iso(f[pos["ingreso"]][0]),
                      "celda": f[pos["costo"]][1]})
    return filas


def leer_personal(ws, sedes: dict[str, str]) -> list[dict]:
    """Encabezado de dos filas: la sede (celda combinada) arriba y Personas/Costo abajo."""
    m = matriz(ws)
    i = next((k for k, f in enumerate(m) if normalizar(f[0][0]) == "rol"), None)
    if i is None or i == 0:
        raise ArchivoNoReconocido("No se encontró el encabezado de roles.")
    arriba = {j: sedes.get(normalizar(v)) for j, (v, _) in enumerate(m[i - 1]) if normalizar(v) in sedes}
    columnas, sede = {}, None
    for j, (v, _) in enumerate(m[i]):
        sede = arriba.get(j, sede)
        if normalizar(v) in ("personas", "costo") and sede:
            columnas.setdefault(sede, {})[normalizar(v)] = j
    if not columnas:
        raise ArchivoNoReconocido("No se reconocieron las sedes del encabezado combinado.")
    filas = []
    for f in m[i + 1:]:
        rol = f[0][0]
        if not rol or normalizar(rol) == "total":
            continue
        for s, c in columnas.items():
            filas.append({"sede_id": s, "rol": rol, "personas": int(numero(f[c["personas"]][0]) or 0), "costo": int(numero(f[c["costo"]][0]) or 0), "celda": f[c["costo"]][1]})
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


def libros_del_mes(mes: str) -> list[tuple[str, Path]]:
    carpeta = INSUMOS / mes
    return sorted((RE_LIBRO.match(p.name).group(1), p) for p in carpeta.glob("*.xlsx") if RE_LIBRO.match(p.name) and RE_LIBRO.match(p.name).group(2) == mes)


def cargar_mes(conn, mes: str, modo: str = "rutina") -> dict:
    """Carga un mes completo. Es repetible: primero retira lo que hubiera de ese mes."""
    if not (INSUMOS / mes).is_dir():
        raise FileNotFoundError(f"No existe la carpeta de insumos {INSUMOS / mes}")
    ts, version = hora_carga(mes, modo), commit_actual()
    for tabla in TABLAS_MES + ["cargas"]:
        conn.execute(f"DELETE FROM {tabla} WHERE periodo = ?", (mes,))
    validas = {r[0] for r in conn.execute("SELECT cuenta_codigo FROM cuentas")}
    sedes_por_conc: dict[str, dict[str, str]] = {}
    nombres_por_conc: dict[str, dict[str, str]] = {}
    for sid, cid, nombre in conn.execute("SELECT sede_id, concesionario_id, nombre FROM sedes"):
        nombres_por_conc.setdefault(cid, {})[normalizar(nombre)] = sid
        sedes_por_conc.setdefault(cid, {})[normalizar(nombre)] = sid
        sedes_por_conc[cid][normalizar(sid)] = sid
    resumen = {"archivos": 0, "hojas": 0, "filas": 0, "revisar": []}

    for cid, ruta in libros_del_mes(mes):
        if cid not in sedes_por_conc:
            resumen["revisar"].append(f"{ruta.name}: concesionario {cid} desconocido")
            continue
        resumen["archivos"] += 1
        rel = str(ruta.relative_to(INSUMOS))
        sedes = sedes_por_conc[cid]
        wb = load_workbook(ruta, data_only=True)

        def registrar(hoja, tabla, filas, estado="Correcto"):
            conn.execute("INSERT INTO cargas (periodo,concesionario_id,archivo,tabla,filas,estado,modo,commit_hash,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (mes, cid, f"{rel}!{hoja}", tabla, filas, estado, modo, version, "src/ingesta.py", ts))
            resumen["hojas"] += 1
            resumen["filas"] += filas

        def fuente(hoja, celda):
            return f"{rel}!{hoja}!{celda}"

        def guardar(tabla, hoja, filas):
            for f in filas:
                f.update(periodo=mes, fuente=fuente(hoja, f.pop("celda")), cargado_en=ts)
            insertar(conn, tabla, filas)
            return len(filas)

        def saldos(ws):
            if rol_hoja(ws.title) == "balance":
                filas = [{"sede_id": f["clave"], "cuenta_origen": f["cuenta"], "departamento": None, "saldo": f["saldo"], "celda": f["celda"]} for f in leer_cuentas(ws, sedes)]
            else:
                sede = next((s for n, s in sedes.items() if normalizar(ws.title).endswith(n)), None)
                if sede is None:
                    raise ArchivoNoReconocido("El nombre de la hoja no indica una sede conocida.")
                filas = [{"sede_id": sede, "cuenta_origen": f"{f['cuenta']}-{f['clave']}", "departamento": f["clave"], "saldo": f["saldo"], "celda": f["celda"]} for f in leer_cuentas(ws, DEPTOS)]
            for f in filas:
                base = f["cuenta_origen"].split("-")[0]
                f["cuenta_codigo"] = base if base in validas else None
            return guardar("saldos", ws.title, filas)

        def ventas(ws):
            filas = leer_tabla(ws, {"vin": "vin", "fecha": "fecha", "sede": "sede", "linea": "linea", "canal": "canal", "modelo": "modelo", "preciolista": "precio", "descuento": "descuento", "costo": "costo"})
            for f in filas:
                f.update(sede_id=sedes[normalizar(f.pop("sede"))], fecha=fecha_iso(f["fecha"]), precio=int(f["precio"]), descuento=int(f["descuento"]), costo=int(f["costo"]))
                f["margen"] = f["precio"] - f["descuento"] - f["costo"]
            return guardar("ventas", ws.title, filas)

        def gastos(ws):
            filas = leer_tabla(ws, {"fecha": "fecha", "sede": "sede", "cuenta": "cuenta_origen", "proveedor": "proveedor", "concepto": "concepto", "valor": "valor"})
            for f in filas:
                f.update(sede_id=sedes[normalizar(f.pop("sede"))], fecha=fecha_iso(f["fecha"]), cuenta_origen=str(f["cuenta_origen"]), valor=int(f["valor"]))
            return guardar("gastos", ws.title, filas)

        def fi(ws):
            conceptos = {"vehiculosvendidos": "unidades", "creditoscolocados": "creditos", "polizascolocadas": "polizas", "comisionesfi": "comisiones"}
            por_sede = {}
            for f in leer_tabla(ws, {"concepto": "concepto", **nombres_por_conc[cid]}):
                campo = conceptos.get(normalizar(f["concepto"]))
                for s in set(sedes.values()):
                    if campo and s in f:
                        por_sede.setdefault(s, {"sede_id": s, "celda": f["celda"]})[campo] = int(numero(f[s]) or 0)
            if any(len(v) < 6 for v in por_sede.values()) or not por_sede:
                raise ArchivoNoReconocido("Faltan conceptos de F&I.")
            return guardar("fi", ws.title, list(por_sede.values()))

        def obligaciones(ws):
            filas = leer_tabla(ws, {"entidad": "entidad", "sede": "sede", "tipo": "tipo", "saldo": "saldo", "tasamensual": "tasa_mensual", "interesdelmes": "interes_mes"})
            for f in filas:
                tasa = f["tasa_mensual"]
                tasa = numero(tasa) / 100 if isinstance(tasa, str) and "%" in tasa else numero(tasa)
                f.update(sede_id=sedes[normalizar(f.pop("sede"))], tasa_mensual=round(tasa, 6), saldo=int(f["saldo"]), interes_mes=int(f["interes_mes"]))
            return guardar("obligaciones", ws.title, filas)

        lectores = {"balance": saldos, "resultados": saldos, "ventas": ventas, "librodegastos": gastos, "fi": fi, "obligaciones": obligaciones,
                    "inventario": lambda ws: guardar("inventario", ws.title, leer_inventario(ws, sedes)),
                    "personal": lambda ws: guardar("personal", ws.title, leer_personal(ws, sedes))}
        vistos = set()
        for ws in wb.worksheets:
            rol = rol_hoja(ws.title)
            if rol not in lectores:
                continue
            vistos.add(rol)
            tabla = HOJAS[rol][2]
            try:
                registrar(ws.title, tabla, lectores[rol](ws))
            except (ArchivoNoReconocido, ValueError, KeyError, TypeError) as e:
                registrar(ws.title, tabla, 0, "Revisar")
                resumen["revisar"].append(f"{ruta.name} › {ws.title}: {e}")
        for faltante in set(lectores) - vistos:
            resumen["revisar"].append(f"{ruta.name}: falta la hoja «{faltante}»")

    estado = "Correcto" if not resumen["revisar"] else "Revisar"
    accion = f"Cargó {resumen['archivos']} libros, {resumen['hojas']} hojas y {resumen['filas']} filas"
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
        print(f"  {mes}: {r['archivos']} libros, {r['hojas']} hojas, {r['filas']} filas" + (f", {len(r['revisar'])} por revisar" if r["revisar"] else ""))
    exportar_csv(conn)
    conn.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Carga los reportes mensuales a la base de datos")
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
