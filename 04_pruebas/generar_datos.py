#!/usr/bin/env python3
"""Genera el reporte mensual SIMULADO de cada concesionario, 24 meses (nov-2024 a oct-2026).

Un solo libro de Excel por concesionario y mes: 01_insumos/AAAA-MM/reporte_mensual_<COD>_AAAA-MM.xlsx
Datos simulados: ninguna cifra corresponde a una empresa real.
Uso:  python 04_pruebas/generar_datos.py
"""
from __future__ import annotations

import calendar
import json
import shutil
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
INSUMOS = RAIZ / "01_insumos"
SEMILLA = 20261031
MILLON = 1_000_000
MIL_MILLONES = 1_000_000_000

MESES = [str(p) for p in pd.period_range("2024-11", "2026-10", freq="M")]
MES_CIERRE = "2026-10"

CONCESIONARIOS = {
    "AND": {"nombre": "Concesionario Andino", "factor": 1.00, "margen": 0.0, "sedes": {"NOR": ("Norte", .40), "CEN": ("Centro", .35), "SUR": ("Sur", .25)}},
    "VAL": {"nombre": "Autos del Valle", "factor": .72, "margen": .006, "sedes": {"CAL": ("Cali", .55), "PAL": ("Palmira", .27), "TUL": ("Tuluá", .18)}},
    "CAR": {"nombre": "Motores Caribe", "factor": .58, "margen": -.007, "sedes": {"BAQ": ("Barranquilla", .50), "CTG": ("Cartagena", .32), "SMR": ("Santa Marta", .18)}},
    "LLA": {"nombre": "Llanos Motor", "factor": .39, "margen": .002, "sedes": {"VIL": ("Villavicencio", .62), "YOP": ("Yopal", .26), "ACA": ("Acacías", .12)}},
}

# Ingresos de Andino en miles de millones. Ene-oct 2026 coinciden con las diapositivas.
INGRESOS_ANDINO = [10.1, 13.2, 10.2, 9.5, 11.0, 10.6, 11.6, 10.9, 11.3, 11.9, 11.1, 11.7,
                   11.4, 14.6, 11.2, 10.4, 12.1, 11.6, 12.8, 11.9, 12.4, 13.1, 12.2, 12.9]
MARGEN_ANDINO = [.148, .153, .149, .147, .150, .149, .151, .150, .149, .152, .150, .151,
                 .150, .154, .151, .149, .152, .150, .153, .151, .152, .153, .150, .142]

DEPARTAMENTOS = {"LIV": "Livianos", "USA": "Usados", "ELE": "Eléctricos", "PES": "Pesados", "FYI": "F&I",
                 "SER": "Servicio", "REP": "Repuestos", "ACC": "Accesorios", "ADM": "Administrativo"}
VEHICULOS = ["LIV", "USA", "ELE", "PES"]
MARGEN_DEPTO = {"LIV": .095, "USA": .12, "ELE": .11, "PES": .085, "FYI": .90, "SER": .48, "REP": .27, "ACC": .33}
PESO_GASTO = {"LIV": .25, "USA": .07, "ELE": .07, "PES": .07, "FYI": .03, "SER": .13, "REP": .08, "ACC": .03, "ADM": .27}

MODELOS = {
    "LIV": [("Ceiba Hatch", 49), ("Cóndor Sedán", 58), ("Páramo SUV", 76), ("Tayrona Pickup", 92), ("Quindío Van", 69)],
    "USA": [("Usado Hatch", 34), ("Usado Sedán", 41), ("Usado SUV", 58), ("Usado Pickup", 67)],
    "ELE": [("Colibrí EV", 112), ("Frailejón EV", 146), ("Guadua EV", 188)],
    "PES": [("Titán 5T", 205), ("Magdalena 10T", 298), ("Cordillera 17T", 420)],
}
COSTO_INV = {"LIV": 58, "ELE": 105, "USA": 52, "PES": 190}
INV_OCT = {"LIV": (4200, 1900, 1100), "ELE": (1300, 800, 900), "USA": (700, 500, 1050), "PES": (900, 400, 350)}
ENTIDADES = [("Banco Cordillera", .50, .0115), ("Financiera Altiplano", .30, .0120), ("Crédito Rutas", .20, .0130)]
ROLES = [("Vendedores", 1.0), ("Asesores F&I", 1.1), ("Técnicos", .95), ("Repuestos", .8), ("Administrativos", .9), ("Gerencia", 2.8)]
PROVEEDORES = {
    "5205": [("Publicidad Mirador", "Pauta comercial", .34), ("Fletes La Sabana", "Transporte de vehículos", .28), ("Alistamiento Exprés", "Alistamiento", .22), ("Comisiones Red Aliada", "Comisiones externas", .16)],
    "5135": [("Energía Cordillera", "Servicios públicos", .24), ("Aseo Integral", "Aseo y cafetería", .10), ("Vigilancia Centinela", "Vigilancia", .30), ("Conecta Datos", "Internet y software", .16), ("Mantenimientos Roble", "Mantenimiento", .20)],
    "5120": [("Inmuebles del Parque", "Arrendamiento", .72), ("Seguros Horizonte", "Seguros de sede", .28)],
}
NOMBRES_CUENTA = {
    "1105": "Caja", "1110": "Bancos", "1305": "Clientes", "143501": "Inventario Livianos", "143502": "Inventario Eléctricos",
    "143503": "Inventario Usados", "143504": "Inventario Pesados", "143505": "Inventario Repuestos", "1516": "Construcciones",
    "1524": "Equipo de oficina", "1592": "Depreciación acumulada", "2105": "Obligaciones wholesale", "2205": "Proveedores",
    "2404": "Impuesto de renta", "2408": "IVA por pagar", "2505": "Salarios por pagar", "3105": "Capital social",
    "3605": "Utilidad del ejercicio", "3705": "Utilidades acumuladas", "4135": "Ventas netas", "6135": "Costo de ventas",
    "5105": "Gastos de personal", "5120": "Gastos fijos", "5135": "Gastos semifijos", "5195": "Diversos",
    "5205": "Gastos variables", "5305": "Gasto financiero",
}


def repartir(total: int, pesos) -> list[int]:
    """Reparte un entero exacto según pesos: la suma siempre cuadra al peso."""
    pesos = np.asarray(pesos, dtype=float)
    pesos = pesos / pesos.sum()
    crudo = pesos * int(total)
    base = np.floor(crudo).astype(np.int64)
    faltan = int(total) - int(base.sum())
    for i in np.argsort(-(crudo - base))[:faltan]:
        base[i] += 1
    return [int(x) for x in base]


def fin_mes(mes: str) -> date:
    a, m = map(int, mes.split("-"))
    return date(a, m, calendar.monthrange(a, m)[1])


def dias_habiles(mes: str) -> list[date]:
    fin = fin_mes(mes)
    return [date(fin.year, fin.month, d) for d in range(1, fin.day + 1) if date(fin.year, fin.month, d).weekday() < 5]


def vin(rng) -> str:
    alfabeto = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return "SIM" + "".join(rng.choice(list(alfabeto), 14))


def generar_ventas(rng, cod, sede, mes, depto, ingreso, costo, p_flota):
    modelos = MODELOS[depto]
    precio_medio = np.mean([p for _, p in modelos]) * MILLON
    # En meses fuertes sube también el precio medio (mezcla), así las unidades varían menos que los ingresos.
    indice_mes = INGRESOS_ANDINO[MESES.index(mes)] / 11.8
    n = max(1, int(round(ingreso / precio_medio * 1.15 * indice_mes ** -.32)))
    idx = rng.integers(0, len(modelos), n)
    lista = np.array([modelos[i][1] * MILLON * rng.uniform(.95, 1.07) for i in idx])
    canales = []
    for _ in range(n):
        if depto == "ELE":
            canales.append("Eléctricos")
        elif depto == "USA":
            canales.append("Retail")
        elif rng.random() < p_flota:
            canales.append("Flotas")
        elif depto == "LIV" and rng.random() < .18:
            canales.append("Plan de ahorro")
        else:
            canales.append("Retail")
    pct = {"Retail": (.015, .05), "Flotas": (.05, .10), "Plan de ahorro": (.005, .025), "Eléctricos": (.01, .04)}
    desc = np.array([rng.uniform(*pct[c]) for c in canales])
    netos = repartir(ingreso, lista * (1 - desc))
    ajuste_margen = {"Retail": 1.0, "Flotas": .72, "Plan de ahorro": .9, "Eléctricos": 1.05}
    pesos_margen = np.array([max(1.0, netos[i] * ajuste_margen[canales[i]] * rng.uniform(.75, 1.25)) for i in range(n)])
    margen_total = ingreso - costo
    margenes = repartir(margen_total, pesos_margen) if margen_total > 0 else [0] * n
    dias = [d for d in (date(fin_mes(mes).year, fin_mes(mes).month, x) for x in range(1, fin_mes(mes).day + 1)) if d.weekday() != 6]
    p_dia = np.array([1 + 1.4 * (d.day / len(dias)) ** 3 for d in dias])
    p_dia /= p_dia.sum()
    filas = []
    for i in range(n):
        descuento = int(round(netos[i] * desc[i] / (1 - desc[i])))
        filas.append({"vin": vin(rng), "fecha": dias[int(rng.choice(len(dias), p=p_dia))].isoformat(), "sede": sede, "canal": canales[i],
                      "linea": DEPARTAMENTOS[depto], "modelo": modelos[idx[i]][0], "precio": netos[i] + descuento, "descuento": descuento,
                      "costo": netos[i] - margenes[i], "margen": margenes[i]})
    return filas


def generar_inventario(rng, cod, conf, mes, t, ingreso, atascados):
    filas = []
    sedes = list(conf["sedes"])
    pesos = [conf["sedes"][s][1] for s in sedes]
    escala = ingreso / (12.9 * MIL_MILLONES)
    envejecimiento = .72 + .28 * t / 23
    fin = fin_mes(mes)
    rangos = [(1, 30), (31, 60), (61, 150)]
    for depto, valores in INV_OCT.items():
        for b, valor_m in enumerate(valores):
            if cod == "AND" and mes == MES_CIERRE:
                valor = valor_m * MILLON
                n = {"USA": (10, 10, 3)[b]}.get(depto, max(1, round(valor_m / COSTO_INV[depto])))
                if depto == "USA" and b == 2:
                    valor -= sum(a["costo"] for a in atascados)
            elif cod == "AND" and depto == "USA":
                n = (12, 10, 3)[b] if mes not in ("2026-08", "2026-09") else ((10, 10, 3)[b])
                valor = int(n * COSTO_INV["USA"] * MILLON * rng.uniform(.92, 1.08))
            else:
                ruido = rng.uniform(.93, 1.07)
                factor = envejecimiento if b == 2 else 1.0
                valor = int(valor_m * MILLON * escala * factor * ruido)
                n = max(1, round(valor / (COSTO_INV[depto] * MILLON)))
            costos = repartir(valor, rng.uniform(.82, 1.18, n))
            for c in costos:
                d = int(rng.integers(*rangos[b]) if rangos[b][0] != rangos[b][1] else rangos[b][0])
                if cod == "AND" and mes == MES_CIERRE and depto == "USA" and b == 2:
                    d = int(rng.integers(93, 151))  # Ingresaron antes de agosto: solo las 6 sembradas son de agosto.
                modelo = MODELOS[depto][int(rng.integers(len(MODELOS[depto])))][0]
                filas.append({"vin": vin(rng), "sede": sedes[int(rng.choice(len(sedes), p=pesos))], "linea": DEPARTAMENTOS[depto], "modelo": modelo,
                              "dias": d, "costo": c, "ingreso": (fin - timedelta(days=d)).isoformat()})
    if cod == "AND" and mes in ("2026-08", "2026-09", "2026-10"):
        for a in atascados:
            filas.append({"vin": a["vin"], "sede": a["sede"], "linea": "Usados", "modelo": a["modelo"], "dias": (fin - date.fromisoformat(a["ingreso"])).days,
                          "costo": a["costo"], "ingreso": a["ingreso"]})
    return filas


def construir():
    rng = np.random.default_rng(SEMILLA)
    datos = {m: {} for m in MESES}
    atascados = []
    for i, c in enumerate([118, 124, 121, 119, 123, 117]):
        atascados.append({"vin": vin(rng), "sede": ["CEN", "SUR", "NOR"][i % 3], "modelo": ["Usado SUV", "Usado Pickup"][i % 2],
                          "costo": c * MILLON + (8 * MILLON if i == 0 else 0), "ingreso": date(2026, 8, 3 + i * 4).isoformat()})
    historial_personal = {}
    for t, mes in enumerate(MESES):
        p_flota = float(rng.choice([.03, .05, .07, .10, .24, .30], p=[.25, .25, .2, .12, .1, .08]))
        for cod, conf in CONCESIONARIOS.items():
            ruido = 1.0 if cod == "AND" else float(rng.uniform(.96, 1.04))
            ingreso = int(round(INGRESOS_ANDINO[t] * MIL_MILLONES * conf["factor"] * ruido))
            margen = MARGEN_ANDINO[t] + conf["margen"] + (0 if cod == "AND" else float(rng.normal(0, .002)))
            ele = .065 + .06 * t / 23
            part = {"LIV": .50 - ele * .55, "USA": .105, "ELE": ele, "PES": .095, "FYI": .016, "SER": .062, "REP": .082, "ACC": .022}
            ingresos_d = dict(zip(part, repartir(ingreso, list(part.values()))))
            no_veh = sum(ingresos_d[d] * MARGEN_DEPTO[d] for d in part if d not in VEHICULOS)
            bruto_veh = int(round(ingreso * margen - no_veh))
            base_veh = {d: ingresos_d[d] * MARGEN_DEPTO[d] for d in VEHICULOS}
            bruto_d = dict(zip(VEHICULOS, repartir(bruto_veh, list(base_veh.values()))))
            for d in part:
                if d not in VEHICULOS:
                    bruto_d[d] = int(round(ingresos_d[d] * MARGEN_DEPTO[d]))
            sedes = list(conf["sedes"])
            pesos = [conf["sedes"][s][1] for s in sedes]
            rev_sede = {d: dict(zip(sedes, repartir(v, pesos))) for d, v in ingresos_d.items()}
            bruto_sede = {d: dict(zip(sedes, repartir(v, pesos))) for d, v in bruto_d.items()}
            ventas, balances, gastos, personal, fi, obligaciones = [], {}, [], [], [], []
            inventario = generar_inventario(rng, cod, conf, mes, t, ingreso, atascados if cod == "AND" else [])
            base_mensual = np.mean(INGRESOS_ANDINO) * MIL_MILLONES * conf["factor"]
            for s_i, sede in enumerate(sedes):
                peso = pesos[s_i]
                filas_v = []
                for d in VEHICULOS:
                    filas_v += generar_ventas(rng, cod, sede, mes, d, rev_sede[d][sede], rev_sede[d][sede] - bruto_sede[d][sede], p_flota)
                ventas += filas_v
                unidades = len(filas_v)
                inv_linea = {d: sum(x["costo"] for x in inventario if x["sede"] == sede and x["linea"] == DEPARTAMENTOS[d]) for d in VEHICULOS}
                piso = int(sum(inv_linea.values()) * .78)
                interes = 0
                for (entidad, part_e, tasa), saldo in zip(ENTIDADES, repartir(piso, [e[1] for e in ENTIDADES])):
                    tasa_mes = round(tasa + .0002 * np.sin(t / 4), 5)
                    costo_int = int(round(saldo * tasa_mes))
                    interes += costo_int
                    obligaciones.append({"sede": sede, "entidad": entidad, "tipo": "Wholesale", "saldo": saldo, "tasa_mensual": tasa_mes, "interes_mes": costo_int})
                clave = (cod, sede)
                pers = int(base_mensual * peso * .046 * (1 + .004 * t) * rng.uniform(.988, 1.012))
                if cod == "AND" and sede == "NOR" and mes == MES_CIERRE:
                    pers = int(round(np.mean(historial_personal[clave][-6:]) * 1.14))
                historial_personal.setdefault(clave, []).append(pers)
                vend = max(3, round(base_mensual * peso / (68 * MILLON) / 7))
                plantilla = {"Vendedores": vend + (3 if cod == "AND" and sede == "NOR" and mes == MES_CIERRE else 0), "Asesores F&I": max(1, round(vend * .25)),
                             "Técnicos": max(3, round(vend * .9)), "Repuestos": max(2, round(vend * .4)), "Administrativos": max(2, round(vend * .55)), "Gerencia": 1}
                costo_rol = repartir(pers, [plantilla[r] * w for r, w in ROLES])
                personal += [{"sede": sede, "rol": r, "personas": plantilla[r], "costo": c} for (r, _), c in zip(ROLES, costo_rol)]
                pen_cred, pen_seg = {"AND": (.46, .38), "VAL": (.52, .44), "CAR": (.39, .30), "LLA": (.43, .35)}[cod]
                creditos = int(round(unidades * (pen_cred + rng.normal(0, .025))))
                polizas = int(round(unidades * (pen_seg + rng.normal(0, .025))))
                fi.append({"sede": sede, "unidades": unidades, "creditos": creditos, "polizas": polizas, "comisiones": rev_sede["FYI"][sede]})
                ing = sum(rev_sede[d][sede] for d in rev_sede)
                variable, semifijo, fijo = int(ing * .026), int(base_mensual * peso * .014 * rng.uniform(.985, 1.015)), int(base_mensual * peso * .012)
                filas_b = []
                for d in rev_sede:
                    filas_b += [(f"4135-{d}", rev_sede[d][sede]), (f"6135-{d}", rev_sede[d][sede] - bruto_sede[d][sede])]
                for cuenta, total in [("5105", pers), ("5205", variable), ("5135", semifijo), ("5120", fijo), ("5305", interes)]:
                    filas_b += [(f"{cuenta}-{d}", v) for d, v in zip(PESO_GASTO, repartir(total, list(PESO_GASTO.values())))]
                for cuenta, total in [("5205", variable), ("5135", semifijo), ("5120", fijo)]:
                    provs = PROVEEDORES[cuenta]
                    habiles = dias_habiles(mes)
                    for (prov, concepto, w), valor in zip(provs, repartir(total, [p[2] * rng.uniform(.985, 1.015) for p in provs])):
                        gastos.append({"fecha": habiles[int(rng.integers(len(habiles)))].isoformat(), "sede": sede, "cuenta": cuenta,
                                       "proveedor": prov, "concepto": concepto, "valor": valor})
                utilidad = ing - sum(rev_sede[d][sede] - bruto_sede[d][sede] for d in rev_sede) - pers - variable - semifijo - fijo - interes
                base_s = base_mensual * peso
                activos = {"1105": int(ing * .01), "1110": int(ing * .10), "1305": int(ing * .55), "143501": inv_linea["LIV"], "143502": inv_linea["ELE"],
                           "143503": inv_linea["USA"], "143504": inv_linea["PES"], "143505": int(ing * .09), "1516": int(base_s * .18), "1524": int(base_s * .07),
                           "1592": -int(base_s * (.05 + .0005 * t))}
                pasivos = {"2105": piso, "2205": int(ing * .24), "2404": int(ing * .012), "2408": int(ing * .03), "2505": int(pers * .8)}
                capital = int(base_s * .20)
                acumuladas = sum(activos.values()) - sum(pasivos.values()) - capital - utilidad
                balances[sede] = [(k, v) for k, v in activos.items()] + [(k, v) for k, v in pasivos.items()] + [("3105", capital), ("3605", utilidad), ("3705", acumuladas)] + filas_b
            datos[mes][cod] = {"ventas": ventas, "balances": balances, "gastos": gastos, "personal": personal, "fi": fi, "obligaciones": obligaciones, "inventario": inventario}
    return datos, atascados


def sembrar_errores(datos, atascados):
    oct_and = datos[MES_CIERRE]["AND"]
    # 1. Proveedores duplicado en Sur: la línea de lote aparece dos veces.
    sur = oct_and["balances"]["SUR"]
    pos = next(i for i, (c, _) in enumerate(sur) if c == "2205")
    lote = int(18.4 * MILLON)
    sur[pos] = ("2205", sur[pos][1] - lote)
    sur[pos + 1:pos + 1] = [("2205", lote), ("2205", lote)]
    # 4. Cuenta 5195 sin homologar en Centro (sale de semifijos para no alterar la utilidad).
    cen = oct_and["balances"]["CEN"]
    diversos = int(7.35 * MILLON)
    pos = next(i for i, (c, _) in enumerate(cen) if c == "5135-ADM")
    cen[pos] = ("5135-ADM", cen[pos][1] - diversos)
    cen.insert(pos + 1, ("5195-ADM", diversos))
    gastos = oct_and["gastos"]
    fila_cen = max((g for g in gastos if g["sede"] == "CEN" and g["cuenta"] == "5135"), key=lambda g: g["valor"])
    fila_cen["valor"] -= diversos
    gastos.append({"fecha": "2026-10-14", "sede": "CEN", "cuenta": "5195", "proveedor": "Mantenimientos Roble", "concepto": "Gastos diversos sin clasificar", "valor": diversos})
    # 5a. Pago duplicado.
    original = next(g for g in gastos if g["sede"] == "NOR" and g["proveedor"] == "Fletes La Sabana")
    gastos.append(dict(original))
    # 5b. Proveedor nuevo (se toma de un pago existente para conservar el total).
    nuevo = next(g for g in gastos if g["sede"] == "SUR" and g["proveedor"] == "Alistamiento Exprés")
    valor_nuevo = int(4.85 * MILLON)
    nuevo["valor"] -= valor_nuevo
    gastos.append({"fecha": "2026-10-21", "sede": "SUR", "cuenta": nuevo["cuenta"], "proveedor": "Soluciones Nébula SAS", "concepto": "Alistamiento", "valor": valor_nuevo})
    # 5c. Monto 3,4 veces su promedio mensual.
    hist = [next(g["valor"] for g in datos[m]["AND"]["gastos"] if g["sede"] == "NOR" and g["proveedor"] == "Aseo Integral") for m in MESES[-7:-1]]
    atipico = next(g for g in gastos if g["sede"] == "NOR" and g["proveedor"] == "Aseo Integral")
    nuevo_valor = int(round(np.mean(hist) * 3.4))
    delta = nuevo_valor - atipico["valor"]
    atipico["valor"] = nuevo_valor
    compensa = next(g for g in gastos if g["sede"] == "NOR" and g["proveedor"] == "Vigilancia Centinela")
    compensa["valor"] -= delta
    # 5d. Asiento en domingo.
    domingo = next(g for g in gastos if g["sede"] == "CEN" and g["proveedor"] == "Conecta Datos")
    domingo["fecha"] = "2026-10-18"
    return {
        "mes": MES_CIERRE, "concesionario": "AND",
        "proveedores_duplicado": {"sede": "SUR", "cuenta": "2205", "diferencia": lote},
        "personal_norte": {"sede": "NOR", "variacion": .14, "vendedores_nuevos": 3},
        "usados_mas_60": {"unidades": 9, "total_unidades": 29, "porcentaje_unidades": round(9 / 29, 4), "sin_movimiento_desde_agosto": [a["vin"] for a in atascados]},
        "cuenta_sin_mapear": {"sede": "CEN", "cuenta": "5195", "valor": diversos},
        "gastos": {"duplicado": original["proveedor"], "proveedor_nuevo": "Soluciones Nébula SAS", "monto_atipico": "Aseo Integral", "factor": 3.4, "domingo": "2026-10-18"},
    }


# ---------- Libro mensual: un archivo por concesionario y mes ----------
AZUL, CREMA, TINTA = "1F4E79", "F3EDE2", "2A2A2A"
FINO = Side(style="thin", color="D9CFBE")
CONTENIDO = [
    ("Portada", "Datos del concesionario, del periodo y contenido del libro."),
    ("Balance", "Balance general por sede, con secciones y subtotales."),
    ("Resultados <sede>", "Una hoja por sede: resultados por departamento."),
    ("Ventas", "Una fila por vehículo vendido en el mes."),
    ("Inventario", "Vehículos en patio al cierre (exportado sin encabezados)."),
    ("Libro de gastos", "Pagos del mes a proveedores."),
    ("Personal", "Personas y costo por rol y sede."),
    ("F&I", "Créditos, pólizas y comisiones por sede."),
    ("Obligaciones", "Cupos wholesale por entidad y sede."),
    ("Validador", "Controles propios del concesionario (fórmulas)."),
]


def _nombre(codigo: str) -> str:
    return NOMBRES_CUENTA.get(codigo, codigo)


def _titulo(ws, texto: str, sub: str) -> None:
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=14, color=AZUL)
    ws["A2"] = sub
    ws["A2"].font = Font(italic=True, size=9, color="7A7265")


def _encabezado(ws, fila: int, valores: list, inicio: int = 1) -> None:
    for j, v in enumerate(valores, start=inicio):
        c = ws.cell(fila, j, v)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _anchos(ws, anchos: dict) -> None:
    for col, w in anchos.items():
        ws.column_dimensions[col].width = w


def _formato_numeros(ws, fila_ini: int, col_ini: int, col_fin: int) -> None:
    for fila in ws.iter_rows(min_row=fila_ini, min_col=col_ini, max_col=col_fin):
        for c in fila:
            c.number_format = '#,##0;[Red]-#,##0'
            c.border = Border(bottom=FINO)


def _fila_total(ws, fila: int, ultima_col: int) -> None:
    for j in range(1, ultima_col + 1):
        c = ws.cell(fila, j)
        c.font = Font(bold=True, color=AZUL)
        c.fill = PatternFill("solid", fgColor="EDE5D7")


def hoja_portada(wb, cid, mes, conf):
    ws = wb.active
    ws.title = "Portada"
    _titulo(ws, "Reporte mensual de cierre", "Datos simulados para formación. No corresponden a ninguna empresa real.")
    filas = [("Concesionario", conf["nombre"]), ("Código", cid), ("Periodo", mes), ("Moneda", "COP (pesos colombianos)"),
             ("Sedes", ", ".join(n for n, _ in conf["sedes"].values())), ("Elaborado por", "Contabilidad del concesionario")]
    for i, (k, v) in enumerate(filas, start=4):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    ws.cell(11, 1, "Contenido del libro").font = Font(bold=True, size=12, color=AZUL)
    _encabezado(ws, 12, ["Hoja", "Qué contiene"])
    for i, (h, d) in enumerate(CONTENIDO, start=13):
        ws.cell(i, 1, h)
        ws.cell(i, 2, d)
    _anchos(ws, {"A": 22, "B": 64})


def hoja_balance(wb, mes, conf, balances):
    ws = wb.create_sheet("Balance")
    sedes = list(conf["sedes"])
    nombres = [conf["sedes"][s][0] for s in sedes]
    _titulo(ws, f"Balance general por sede · {mes}", "Cifras en pesos. Las filas sin código son títulos o subtotales.")
    _encabezado(ws, 4, ["Código", "Cuenta", *nombres, "Total"])
    valores, orden = {}, []
    for s in sedes:
        vistos = Counter()
        for codigo, v in balances[s]:
            if "-" in codigo:
                continue
            clave = (codigo, vistos[codigo])
            vistos[codigo] += 1
            if clave not in valores:
                valores[clave] = {}
                orden.append(clave)
            valores[clave][s] = v
    primera = {}
    for i, (c, _) in enumerate(orden):
        primera.setdefault(c, i)
    orden.sort(key=lambda x: (primera[x[0]], x[1]))
    ultima = 2 + len(sedes) + 1
    letra = lambda j: get_column_letter(j)
    totales = {}
    for digito, seccion, total in [("1", "ACTIVO", "Total activo"), ("2", "PASIVO", "Total pasivo"), ("3", "PATRIMONIO", "Total patrimonio")]:
        ws.append(["", seccion])
        ws.cell(ws.max_row, 2).font = Font(bold=True, color=AZUL)
        inicio = ws.max_row + 1
        for clave in [k for k in orden if k[0][0] == digito]:
            r = ws.max_row + 1
            ws.append([clave[0], _nombre(clave[0]), *[valores[clave].get(s) for s in sedes], f"=SUM(C{r}:{letra(ultima - 1)}{r})"])
        fin = ws.max_row
        r = fin + 1
        ws.append(["", total, *[f"=SUM({letra(j)}{inicio}:{letra(j)}{fin})" for j in range(3, ultima + 1)]])
        _fila_total(ws, r, ultima)
        totales[digito] = r
        ws.append([])
    _formato_numeros(ws, 5, 3, ultima)
    _anchos(ws, {"A": 10, "B": 30, **{letra(j): 17 for j in range(3, ultima + 1)}})
    ws.freeze_panes = "C5"
    return totales


def hoja_resultados(wb, mes, sede, nombre, filas):
    ws = wb.create_sheet(f"Resultados {nombre}")
    _titulo(ws, f"Estado de resultados por departamento · Sede {nombre} · {mes}", "Cifras en pesos. Gastos en positivo.")
    deptos = list(DEPARTAMENTOS)
    _encabezado(ws, 4, ["Código", "Concepto", *[DEPARTAMENTOS[d] for d in deptos], "Total"])
    valores = {}
    for codigo, v in filas:
        base, _, d = codigo.partition("-")
        if d:
            valores.setdefault(base, {})[d] = v
    ultima = 2 + len(deptos) + 1
    letra = get_column_letter
    fila = {}

    def cuenta(c):
        r = ws.max_row + 1
        ws.append([c, _nombre(c), *[valores.get(c, {}).get(d) for d in deptos], f"=SUM(C{r}:{letra(ultima - 1)}{r})"])
        fila[c] = r

    def calculo(etiqueta, formula):
        r = ws.max_row + 1
        ws.append(["", etiqueta, *[formula(letra(j)) for j in range(3, ultima + 1)]])
        _fila_total(ws, r, ultima)
        return r

    cuenta("4135")
    cuenta("6135")
    ub = calculo("Utilidad bruta", lambda c: f"={c}{fila['4135']}-{c}{fila['6135']}")
    gastos = [c for c in ["5205", "5105", "5135", "5195", "5120", "5305"] if c in valores]
    for c in gastos:
        cuenta(c)
    tg = calculo("Total gastos", lambda c: f"=SUM({c}{fila[gastos[0]]}:{c}{fila[gastos[-1]]})")
    calculo("Utilidad operativa", lambda c: f"={c}{ub}-{c}{tg}")
    _formato_numeros(ws, 5, 3, ultima)
    _anchos(ws, {"A": 10, "B": 24, **{letra(j): 15 for j in range(3, ultima + 1)}})
    ws.freeze_panes = "C5"


def hoja_tabla(wb, titulo_hoja, titulo, sub, encabezado, filas, fila_encabezado=4, anchos=None):
    ws = wb.create_sheet(titulo_hoja)
    if titulo:
        _titulo(ws, titulo, sub)
    _encabezado(ws, fila_encabezado, encabezado)
    for f in filas:
        ws.append(f)
    _anchos(ws, anchos or {})
    ws.freeze_panes = ws.cell(fila_encabezado + 1, 1)
    return ws


def escribir_libro(mes: str, cid: str, d: dict) -> Path:
    conf = CONCESIONARIOS[cid]
    sedes = list(conf["sedes"])
    nombre = {s: conf["sedes"][s][0] for s in sedes}
    wb = Workbook()
    wb.properties.creator = "Datos simulados"
    wb.properties.title = f"Reporte mensual de cierre {cid} {mes}"
    wb.calculation.fullCalcOnLoad = True  # Excel calcula subtotales y el Validador al abrir el libro.
    hoja_portada(wb, cid, mes, conf)
    totales = hoja_balance(wb, mes, conf, d["balances"])
    for s in sedes:
        hoja_resultados(wb, mes, s, nombre[s], d["balances"][s])
    ventas = sorted(d["ventas"], key=lambda v: (v["fecha"], v["vin"]))
    ws = hoja_tabla(wb, "Ventas", f"Ventas por vehículo · {mes}", "Una fila por vehículo facturado.",
                    ["VIN", "Fecha", "Sede", "Línea", "Canal", "Modelo", "Precio lista", "Descuento", "Costo"],
                    [[v["vin"], date.fromisoformat(v["fecha"]), nombre[v["sede"]], v["linea"], v["canal"], v["modelo"], v["precio"], v["descuento"], v["costo"]] for v in ventas],
                    anchos={"A": 21, "B": 12, "C": 14, "D": 12, "E": 15, "F": 16, "G": 15, "H": 13, "I": 15})
    for fila in ws.iter_rows(min_row=5):
        fila[1].number_format = "DD/MM/YYYY"
        for c in fila[6:9]:
            c.number_format = "#,##0"
    ws = wb.create_sheet("Inventario")  # Exportado del sistema de patio: sin encabezados.
    for v in d["inventario"]:
        ws.append([v["vin"], nombre[v["sede"]], v["linea"], v["modelo"], v["dias"], v["costo"], date.fromisoformat(v["ingreso"])])
    for fila in ws.iter_rows():
        fila[5].number_format = "#,##0"
        fila[6].number_format = "DD/MM/YYYY"
    _anchos(ws, {"A": 21, "B": 14, "C": 12, "D": 16, "E": 7, "F": 14, "G": 12})
    gastos = sorted(d["gastos"], key=lambda g: (g["fecha"], g["sede"], g["proveedor"]))
    ws = hoja_tabla(wb, "Libro de gastos", None, None, ["Fecha", "Sede", "Cuenta", "Proveedor", "Concepto", "Valor"],
                    [[date.fromisoformat(g["fecha"]), nombre[g["sede"]], g["cuenta"], g["proveedor"], g["concepto"], g["valor"]] for g in gastos],
                    fila_encabezado=1, anchos={"A": 12, "B": 14, "C": 9, "D": 24, "E": 30, "F": 15})
    for fila in ws.iter_rows(min_row=2):
        fila[0].number_format = "DD/MM/YYYY"
        fila[5].number_format = "#,##0"
    # Personal: encabezado de dos filas con la sede combinada sobre Personas y Costo.
    ws = wb.create_sheet("Personal")
    _titulo(ws, f"Personal por rol y sede · {mes}", "Costo mensual total en pesos.")
    for i, s in enumerate(sedes):
        col = 2 + i * 2
        ws.merge_cells(start_row=4, start_column=col, end_row=4, end_column=col + 1)
        _encabezado(ws, 4, [nombre[s]], inicio=col)
        _encabezado(ws, 5, ["Personas", "Costo"], inicio=col)
    _encabezado(ws, 5, ["Rol"])
    por = {(p["sede"], p["rol"]): p for p in d["personal"]}
    for rol, _ in ROLES:
        fila = [rol]
        for s in sedes:
            fila += [por[(s, rol)]["personas"], por[(s, rol)]["costo"]]
        ws.append(fila)
    r = ws.max_row + 1
    ws.append(["Total", *[f"=SUM({get_column_letter(j)}6:{get_column_letter(j)}{r - 1})" for j in range(2, 2 + 2 * len(sedes))]])
    _fila_total(ws, r, 1 + 2 * len(sedes))
    _formato_numeros(ws, 6, 2, 1 + 2 * len(sedes))
    _anchos(ws, {"A": 18, **{get_column_letter(j): 14 for j in range(2, 2 + 2 * len(sedes))}})
    # F&I: conceptos en filas y sedes en columnas.
    fi = {f["sede"]: f for f in d["fi"]}
    conceptos = [("Vehículos vendidos", "unidades"), ("Créditos colocados", "creditos"), ("Pólizas colocadas", "polizas"), ("Comisiones F&I", "comisiones")]
    ws = hoja_tabla(wb, "F&I", f"Financiación y seguros · {mes}", "Comisiones en pesos.", ["Concepto", *[nombre[s] for s in sedes]],
                    [[c, *[fi[s][k] for s in sedes]] for c, k in conceptos], anchos={"A": 22, **{get_column_letter(j): 16 for j in range(2, 2 + len(sedes))}})
    _formato_numeros(ws, 5, 2, 1 + len(sedes))
    # Obligaciones: la tasa llega escrita como texto.
    ws = hoja_tabla(wb, "Obligaciones", f"Obligaciones financieras · {mes}", "Cupos de financiación de inventario (wholesale).",
                    ["Entidad", "Sede", "Tipo", "Saldo", "Tasa mensual", "Interés del mes"],
                    [[o["entidad"], nombre[o["sede"]], o["tipo"], o["saldo"], f"{o['tasa_mensual'] * 100:.3f} %".replace(".", ","), o["interes_mes"]] for o in d["obligaciones"]],
                    anchos={"A": 22, "B": 14, "C": 12, "D": 16, "E": 13, "F": 15})
    for fila in ws.iter_rows(min_row=5):
        fila[3].number_format = fila[5].number_format = "#,##0"
    # Validador propio del concesionario: Excel lo calcula al abrir el archivo.
    ws = wb.create_sheet("Validador")
    _titulo(ws, "Validador del concesionario", "Fórmulas que Excel calcula al abrir el libro.")
    _encabezado(ws, 4, ["Sede", "Total activo", "Pasivo + patrimonio", "Diferencia", "Estado"])
    for i, s in enumerate(sedes):
        c, r = get_column_letter(3 + i), 5 + i
        ws.append([nombre[s], f"=Balance!{c}{totales['1']}", f"=Balance!{c}{totales['2']}+Balance!{c}{totales['3']}", f"=B{r}-C{r}", f'=IF(ABS(D{r})<1,"Cuadra","Revisar")'])
    _formato_numeros(ws, 5, 2, 4)
    _anchos(ws, {"A": 16, "B": 18, "C": 20, "D": 15, "E": 12})
    for ws in wb.worksheets:
        ws.sheet_properties.tabColor = AZUL if ws.title in ("Portada", "Validador") else "B4532A" if ws.title == "Inventario" else "1D6B67"
    ruta = INSUMOS / mes / f"reporte_mensual_{cid}_{mes}.xlsx"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    wb.save(ruta)
    return ruta


def main():
    if INSUMOS.exists():
        for hijo in INSUMOS.iterdir():
            if hijo.is_dir() and len(hijo.name) == 7 and hijo.name[4] == "-":
                shutil.rmtree(hijo)
    INSUMOS.mkdir(exist_ok=True)
    datos, atascados = construir()
    errores = sembrar_errores(datos, atascados)
    for mes in MESES:
        for cid, d in datos[mes].items():
            escribir_libro(mes, cid, d)
    (RAIZ / "04_pruebas" / "errores_sembrados.json").write_text(json.dumps(errores, ensure_ascii=False, indent=2), encoding="utf-8")
    catalogo = {"concesionarios": {k: {"nombre": v["nombre"], "sedes": {s: n for s, (n, _) in v["sedes"].items()}} for k, v in CONCESIONARIOS.items()},
                "departamentos": DEPARTAMENTOS, "cuentas": NOMBRES_CUENTA}
    (RAIZ / "04_pruebas" / "catalogo.json").write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {len(MESES)} meses × {len(CONCESIONARIOS)} concesionarios = {len(MESES) * len(CONCESIONARIOS)} libros en 01_insumos/ (datos simulados).")


if __name__ == "__main__":
    main()
