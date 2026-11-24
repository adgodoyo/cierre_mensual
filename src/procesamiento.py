#!/usr/bin/env python3
"""Agente de procesamiento: consolida, valida y explica los hallazgos del mes.

Uso:
  python src/procesamiento.py --mes 2026-10    # valida y escribe los Excel del mes
  python src/procesamiento.py --historial      # recalcula las alertas de todos los meses
"""
from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from comun import NOTA, SALIDAS, cop, millones, nombre_mes, pct
from ingesta import cargar_mes, conectar, exportar_csv, hora_carga

UMBRAL_VARIACION = .30
UMBRAL_PERSONAL = .10
UMBRAL_ANTIGUEDAD = .25
UMBRAL_ANTIGUEDAD_ALTA = .30
LINEAS_ERI = [("4135", "Ventas netas"), ("6135", "Costo de ventas"), ("5205", "Gastos variables"), ("5105", "Gastos de personal"),
              ("5135", "Gastos semifijos"), ("5120", "Gastos fijos"), ("5305", "Gasto financiero")]
DEPTOS = {"LIV": "Livianos", "USA": "Usados", "ELE": "Eléctricos", "PES": "Pesados", "FYI": "F&I", "SER": "Servicio", "REP": "Repuestos", "ACC": "Accesorios", "ADM": "Administrativo"}
CUENTA_INV = {"Livianos": "143501", "Eléctricos": "143502", "Usados": "143503", "Pesados": "143504"}
ORDEN_SEV = {"Alta": 0, "Media": 1, "Baja": 2}


def leer(conn, consulta, parametros=()):
    return pd.read_sql_query(consulta, conn, params=parametros)


def alerta(mes, cid, sede, regla, severidad, hallazgo, explicacion, impacto, origen):
    return {"periodo": mes, "concesionario_id": cid, "sede_id": sede, "regla": regla, "severidad": severidad, "hallazgo": hallazgo,
            "explicacion": explicacion, "impacto_cop": None if impacto is None else int(abs(impacto)), "origen": origen}


def es_esf(cuentas: pd.Series) -> pd.Series:
    return ~cuentas.str.contains("-", regex=False)


def proponer_codigo(cuenta: str, catalogo: pd.DataFrame):
    """Sugiere la cuenta homologada más cercana del mismo grupo PUC. Siempre queda por confirmar."""
    base = cuenta.split("-")[0]
    candidatas = catalogo[catalogo.cuenta_codigo.str[:2] == base[:2]].copy()
    if candidatas.empty:
        candidatas = catalogo[catalogo.cuenta_codigo.str[0] == base[0]].copy()
    if candidatas.empty:
        return None
    candidatas["distancia"] = (candidatas.cuenta_codigo.str[:4].astype(int) - int(base[:4])).abs()
    return candidatas.sort_values("distancia").iloc[0]


def construir_esf(saldos: pd.DataFrame, catalogo: pd.DataFrame, sedes: list[str]) -> pd.DataFrame:
    esf = saldos[es_esf(saldos.cuenta_origen)].merge(catalogo, on="cuenta_codigo", how="left")
    esf["codigo_formato"] = esf.codigo_formato.fillna("ESF.9.99")
    esf["linea_formato"] = esf.linea_formato.fillna("Sin homologar (por confirmar)")
    esf["grupo"] = esf.grupo.fillna(esf.cuenta_origen.str[0].map({"1": "Activo", "2": "Pasivo", "3": "Patrimonio"}))
    tabla = esf.pivot_table(index=["grupo", "codigo_formato", "linea_formato"], columns="sede_id", values="saldo", aggfunc="sum", fill_value=0).reindex(columns=sedes, fill_value=0)
    tabla["Consolidado"] = tabla.sum(axis=1)
    return tabla.reset_index().sort_values("codigo_formato")


def construir_eri(saldos: pd.DataFrame, sedes: list[str]) -> pd.DataFrame:
    eri = saldos[~es_esf(saldos.cuenta_origen)].copy()
    eri["base"] = eri.cuenta_origen.str[:4]
    filas = []
    for alcance in ["Consolidado"] + sedes:
        datos = eri if alcance == "Consolidado" else eri[eri.sede_id == alcance]
        por_cuenta = datos.pivot_table(index="base", columns="departamento", values="saldo", aggfunc="sum", fill_value=0).reindex(columns=list(DEPTOS), fill_value=0)
        valor = lambda c: por_cuenta.loc[c] if c in por_cuenta.index else pd.Series(0, index=list(DEPTOS))
        otras = [c for c in por_cuenta.index if c not in {x for x, _ in LINEAS_ERI}]
        sin_homologar = sum((por_cuenta.loc[c] for c in otras), pd.Series(0, index=list(DEPTOS)))
        bruta = valor("4135") - valor("6135")
        gastos = sum((valor(c) for c in ["5205", "5105", "5135", "5120", "5305"]), pd.Series(0, index=list(DEPTOS)))
        lineas = [("Ventas netas", valor("4135")), ("Costo de ventas", valor("6135")), ("Utilidad bruta", bruta), ("Gastos variables", valor("5205")),
                  ("Gastos de personal", valor("5105")), ("Gastos semifijos", valor("5135")), ("Gastos fijos", valor("5120")), ("Gasto financiero", valor("5305")),
                  ("Sin homologar (por confirmar)", sin_homologar), ("Utilidad operativa", bruta - gastos - sin_homologar)]
        for nombre, serie in lineas:
            filas.append({"Alcance": alcance, "Línea": nombre, **{DEPTOS[d]: int(serie[d]) for d in DEPTOS}, "Total": int(serie.sum())})
    return pd.DataFrame(filas)


def validar_concesionario(conn, mes, cid, catalogo, anterior, historia_personal):
    sedes_df = leer(conn, "SELECT sede_id, nombre FROM sedes WHERE concesionario_id=? ORDER BY sede_id", (cid,))
    sedes, nombres = sedes_df.sede_id.tolist(), dict(zip(sedes_df.sede_id, sedes_df.nombre))
    marcas = ",".join("?" * len(sedes))
    saldos = leer(conn, f"SELECT * FROM saldos WHERE periodo=? AND sede_id IN ({marcas})", (mes, *sedes))
    ventas = leer(conn, f"SELECT * FROM ventas WHERE periodo=? AND sede_id IN ({marcas})", (mes, *sedes))
    inv = leer(conn, f"SELECT * FROM inventario WHERE periodo=? AND sede_id IN ({marcas})", (mes, *sedes))
    alertas, controles = [], []

    def control(nombre, alcance, esperado, obtenido, tolerancia=1):
        dif = int(obtenido) - int(esperado)
        controles.append({"Control": nombre, "Alcance": alcance, "Esperado": int(esperado), "Obtenido": int(obtenido), "Diferencia": dif, "Estado": "Cumple" if abs(dif) <= tolerancia else "No cumple"})
        return abs(dif) <= tolerancia

    # 1. Ecuación contable por sede
    for s in sedes:
        esf = saldos[(saldos.sede_id == s) & es_esf(saldos.cuenta_origen)]
        activo = esf[esf.cuenta_origen.str[0] == "1"].saldo.sum()
        pas_pat = esf[esf.cuenta_origen.str[0].isin(["2", "3"])].saldo.sum()
        if not control("Activo = Pasivo + Patrimonio", nombres[s], activo, pas_pat):
            dif = pas_pat - activo
            repetidas = esf[esf.duplicated(["cuenta_origen", "saldo"], keep="first")]
            causa = repetidas[repetidas.saldo == abs(dif)]
            if len(causa):
                f = causa.iloc[0]
                nombre_c = catalogo.set_index("cuenta_codigo").nombre.get(f.cuenta_origen, f.cuenta_origen)
                texto, origen = f"La cuenta {f.cuenta_origen} {nombre_c} está repetida en {nombres[s]} por {millones(f.saldo)}; al retirar la fila repetida el balance cuadra.", f.fuente
            else:
                texto, origen = f"El balance de {nombres[s]} no cuadra por {millones(dif)} y no se identificó una fila repetida.", esf.iloc[0].fuente.split("!")[0]
            alertas.append(alerta(mes, cid, s, "ecuacion_contable", "Alta", f"Activo ≠ Pasivo + Patrimonio en {nombres[s]} por {millones(abs(dif))}", texto, dif, origen))

    # 2. Suma de sedes = consolidado, y cruces entre fuentes
    esf_c, eri_c = construir_esf(saldos, catalogo, sedes), construir_eri(saldos, sedes)
    for columna, nombre in [("Consolidado", "ESF")]:
        control(f"Suma de sedes = consolidado ({nombre})", "Consolidado", esf_c[sedes].to_numpy().sum(), esf_c[columna].sum())
    consolidado = eri_c[eri_c["Alcance"] == "Consolidado"].set_index("Línea")["Total"]
    for linea in ["Ventas netas", "Utilidad operativa"]:
        por_sedes = eri_c[(eri_c["Alcance"] != "Consolidado") & (eri_c["Línea"] == linea)]["Total"].sum()
        if not control(f"Suma de sedes = consolidado ({linea})", "Consolidado", por_sedes, consolidado[linea]):
            alertas.append(alerta(mes, cid, None, "suma_sedes", "Alta", f"La suma de sedes no coincide en {linea}", "El consolidado no es igual a la suma de las sedes.", por_sedes - consolidado[linea], f"formato_consolidado_{mes}.xlsx!ERI"))
    vehiculos = saldos[saldos.cuenta_origen.isin([f"4135-{d}" for d in ("LIV", "USA", "ELE", "PES")])].saldo.sum()
    if not control("Ventas por VIN = ventas de vehículos en ERI", "Consolidado", vehiculos, (ventas.precio - ventas.descuento).sum()):
        alertas.append(alerta(mes, cid, None, "cruce_ventas", "Alta", "Ventas por VIN no coinciden con el ERI", "El detalle de vehículos vendidos no suma lo mismo que el estado de resultados.", vehiculos - (ventas.precio - ventas.descuento).sum(), f"{mes}/reporte_mensual_{cid}_{mes}.xlsx!Ventas"))
    for linea, cuenta in CUENTA_INV.items():
        contable, detalle = saldos[saldos.cuenta_origen == cuenta].saldo.sum(), inv[inv.linea == linea].costo.sum()
        if not control(f"Inventario {linea}: detalle = balance", "Consolidado", contable, detalle):
            alertas.append(alerta(mes, cid, None, "cruce_inventario", "Alta", f"Inventario {linea} no coincide con el balance", "El detalle por vehículo no suma lo mismo que la cuenta contable.", contable - detalle, f"{mes}/reporte_mensual_{cid}_{mes}.xlsx!Inventario"))
    utilidad_3605 = saldos[saldos.cuenta_origen == "3605"].saldo.sum()
    if not control("Utilidad del ERI = cuenta 3605", "Consolidado", utilidad_3605, consolidado["Utilidad operativa"]):
        alertas.append(alerta(mes, cid, None, "cruce_utilidad", "Alta", "La utilidad del ERI no coincide con el balance", "La utilidad calculada difiere de la cuenta 3605.", utilidad_3605 - consolidado["Utilidad operativa"], f"formato_consolidado_{mes}.xlsx!ERI"))

    # 3. Variación frente al mes anterior
    if anterior is not None:
        previo = anterior[anterior.sede_id.isin(sedes)]
        temporada = mes[-2:] in ("12", "01")
        for cuenta, nombre in LINEAS_ERI:
            hoy = saldos[saldos.cuenta_origen.str.startswith(cuenta + "-")].saldo.sum()
            antes = previo[previo.cuenta_origen.str.startswith(cuenta + "-")].saldo.sum()
            if antes and abs(hoy / antes - 1) > UMBRAL_VARIACION and not (temporada and cuenta in ("4135", "6135", "5205")):
                f = saldos[saldos.cuenta_origen.str.startswith(cuenta + "-")].iloc[0]
                alertas.append(alerta(mes, cid, None, "variacion_mensual", "Media", f"{nombre} varía {pct(hoy / antes - 1)} frente al mes anterior",
                                      f"{nombre} pasó de {millones(antes)} a {millones(hoy)} y no hay un motivo estacional que lo explique.", hoy - antes, f.fuente))

    # 4. Cuentas sin homologar
    for _, f in saldos[saldos.cuenta_codigo.isna()].iterrows():
        p = proponer_codigo(f.cuenta_origen, catalogo)
        propuesta = f"{p.codigo_formato} {p.linea_formato}" if p is not None else "sin propuesta"
        alertas.append(alerta(mes, cid, f.sede_id, "cuenta_sin_mapear", "Media", f"Cuenta {f.cuenta_origen.split('-')[0]} no está en la tabla de homologación",
                              f"Se propone clasificarla en {propuesta}, marcada como por confirmar hasta que una persona la apruebe.", f.saldo, f.fuente))

    # 5. Gastos de personal frente al promedio de 6 meses
    actual_p = leer(conn, f"SELECT * FROM personal WHERE periodo=? AND sede_id IN ({marcas})", (mes, *sedes))
    for s in sedes:
        previos = historia_personal[(historia_personal.sede_id == s) & (historia_personal.periodo < mes)].groupby("periodo").costo.sum().tail(6)
        if len(previos) < 6:
            continue
        hoy, media = actual_p[actual_p.sede_id == s].costo.sum(), previos.mean()
        if hoy / media - 1 > UMBRAL_PERSONAL:
            ultimo = previos.index[-1]
            antes = historia_personal[(historia_personal.sede_id == s) & (historia_personal.periodo == ultimo)].set_index("rol").personas
            ahora = actual_p[actual_p.sede_id == s].set_index("rol")
            cambio = (ahora.personas - antes).sort_values(ascending=False)
            rol, nuevos = cambio.index[0], int(cambio.iloc[0])
            motivo = f"ingresaron {nuevos} personas en {rol}" if nuevos > 0 else "no hay cambio de planta que lo explique"
            alertas.append(alerta(mes, cid, s, "personal_vs_promedio", "Media", f"Gastos de personal de {nombres[s]} +{pct(hoy / media - 1)} frente al promedio de 6 meses",
                                  f"El gasto subió {millones(hoy - media)} porque {motivo}.", hoy - media, ahora.loc[rol, "fuente"]))

    # 6. Antigüedad del inventario (en unidades)
    previo_inv = leer(conn, f"SELECT linea, rango FROM inventario WHERE periodo=(SELECT MAX(periodo) FROM inventario WHERE periodo<?) AND sede_id IN ({marcas})", (mes, *sedes))
    for linea, g in inv.groupby("linea"):
        if len(g) < 10:
            continue
        cuota = (g.rango == ">60").mean()
        antes = (previo_inv[previo_inv.linea == linea].rango == ">60").mean() if len(previo_inv) else cuota
        if cuota >= UMBRAL_ANTIGUEDAD and cuota - antes >= .05:
            viejos = g[g.rango == ">60"]
            severidad = "Alta" if cuota >= UMBRAL_ANTIGUEDAD_ALTA and cuota - antes >= .10 else "Media"
            sin_mov = viejos[viejos.fecha_ingreso.str[:7] == (pd.Period(mes) - 2).strftime("%Y-%m")]
            detalle = f"; {len(sin_mov)} unidades no se mueven desde {nombre_mes((pd.Period(mes) - 2).strftime('%Y-%m')).split(' de ')[0]}" if len(sin_mov) else ""
            alertas.append(alerta(mes, cid, None, "antiguedad_inventario", severidad, f"{linea} con más de 60 días llega a {pct(cuota, 0)} de las unidades",
                                  f"{len(viejos)} de {len(g)} unidades superan 60 días y suman {millones(viejos.costo.sum())}{detalle}.", viejos.costo.sum(), viejos.sort_values("dias").iloc[-1].fuente))
    return alertas, controles, esf_c, eri_c, {"sedes": sedes, "nombres": nombres, "ventas": ventas, "inventario": inv}


def detectar_anomalias(gastos: pd.DataFrame, mes: str) -> pd.DataFrame:
    """Marca pagos duplicados, proveedores nuevos, montos atípicos y registros en fin de semana."""
    hoy = gastos[gastos.periodo == mes].copy()
    previo = gastos[gastos.periodo < mes]
    hallazgos = []
    claves = ["fecha", "sede_id", "cuenta_origen", "proveedor", "concepto", "valor"]
    for _, f in hoy[hoy.duplicated(claves, keep="first")].iterrows():
        hallazgos.append((f, "Pago duplicado", "Alta", f"{f.proveedor} tiene dos pagos iguales de {millones(f.valor)} el mismo día.", f.valor))
    conocidos = set(zip(previo.concesionario_id, previo.proveedor))
    if previo.periodo.nunique() >= 3:
        for _, f in hoy.iterrows():
            if (f.concesionario_id, f.proveedor) not in conocidos:
                hallazgos.append((f, "Proveedor nuevo", "Media", f"{f.proveedor} no aparece en ningún mes anterior; conviene verificar su registro antes de pagar.", f.valor))
    for _, f in hoy.iterrows():
        h = previo[(previo.sede_id == f.sede_id) & (previo.proveedor == f.proveedor) & (previo.cuenta_origen == f.cuenta_origen)].sort_values("periodo").tail(12)
        if len(h) >= 6 and h.valor.std() > 0:
            z, razon = (f.valor - h.valor.mean()) / h.valor.std(), f.valor / h.valor.mean()
            if z > 3 and razon >= 1.5:
                texto = f"El pago a {f.proveedor} es {str(round(razon, 1)).replace('.', ',')} veces su promedio mensual de {millones(h.valor.mean())}."
                hallazgos.append((f, "Monto atípico", "Media", texto, f.valor - h.valor.mean()))
    for _, f in hoy.iterrows():
        dia = pd.Timestamp(f.fecha).day_of_week
        if dia >= 5:
            nombre = "domingo" if dia == 6 else "sábado"
            hallazgos.append((f, "Registro en fin de semana", "Baja", f"El pago a {f.proveedor} se registró un {nombre} ({f.fecha}), fuera del calendario habitual.", f.valor))
    filas = [{"periodo": mes, "concesionario_id": f.concesionario_id, "sede_id": f.sede_id, "fecha": f.fecha, "proveedor": f.proveedor, "cuenta": f.cuenta_origen, "valor": int(f.valor),
              "tipo": tipo, "severidad": sev, "explicacion": txt, "impacto_cop": int(imp), "origen": f.fuente} for f, tipo, sev, txt, imp in hallazgos]
    columnas = ["periodo", "concesionario_id", "sede_id", "fecha", "proveedor", "cuenta", "valor", "tipo", "severidad", "explicacion", "impacto_cop", "origen"]
    return pd.DataFrame(filas, columns=columnas)


def dar_formato(ruta) -> None:
    from openpyxl import load_workbook
    wb = load_workbook(ruta)
    for ws in wb.worksheets:
        ws.insert_rows(1)
        ws["A1"] = f"{ws.title} · {NOTA}"
        ws["A1"].font = Font(bold=True, size=12, color="1F4E79")
        for celda in ws[2]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor="1F4E79")
            celda.alignment = Alignment(wrap_text=True, vertical="center")
        for j, columna in enumerate(ws.iter_cols(min_row=2), start=1):
            ancho = min(46, max(len(str(c.value)) if c.value is not None else 0 for c in columna) + 2)
            ws.column_dimensions[get_column_letter(j)].width = max(10, ancho)
            for c in columna[1:]:
                if isinstance(c.value, int) and abs(c.value) >= 1000:
                    c.number_format = "#,##0"
                elif isinstance(c.value, float):
                    c.number_format = "0.00%" if abs(c.value) < 1 else "#,##0.00"
                elif c.value in ("Alta", "No cumple"):
                    c.fill = PatternFill("solid", fgColor="F2D5C8")
                elif c.value == "Media":
                    c.fill = PatternFill("solid", fgColor="F6E7C1")
                elif c.value in ("Baja", "Cumple"):
                    c.fill = PatternFill("solid", fgColor="D4E6E2")
        ws.freeze_panes = "A3"
    wb.save(ruta)


def escribir_formato(conn, mes, cid, nombre, r, controles, alertas_c) -> str:
    carpeta = SALIDAS / mes
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / (f"formato_consolidado_{mes}.xlsx" if cid == "AND" else f"formato_consolidado_{mes}_{nombre.replace(' ', '_')}.xlsx")
    sedes, inv, ventas = r["sedes"], r["inventario"], r["ventas"]
    marcas = ",".join("?" * len(sedes))
    envejecido = inv.pivot_table(index=["linea", "sede_id"], columns="rango", values="costo", aggfunc="sum", fill_value=0).reindex(columns=["0-30", "31-60", ">60"], fill_value=0).reset_index()
    with pd.ExcelWriter(archivo, engine="openpyxl") as x:
        r["esf"].rename(columns={"grupo": "Grupo", "codigo_formato": "Código", "linea_formato": "Línea"}).to_excel(x, sheet_name="ESF", index=False)
        r["eri"].to_excel(x, sheet_name="ERI", index=False)
        ventas[["vin", "fecha", "sede_id", "canal", "linea", "modelo", "precio", "descuento", "costo", "margen", "fuente"]].to_excel(x, sheet_name="Ventas por VIN", index=False)
        envejecido.to_excel(x, sheet_name="Inventario por antigüedad", index=False)
        for hoja, tabla in [("Obligaciones financieras", "obligaciones"), ("F&I", "fi"), ("Personal", "personal")]:
            leer(conn, f"SELECT * FROM {tabla} WHERE periodo=? AND sede_id IN ({marcas})", (mes, *sedes)).drop(columns=["cargado_en"]).to_excel(x, sheet_name=hoja, index=False)
        pd.DataFrame(controles).to_excel(x, sheet_name="Validador", index=False)
    dar_formato(archivo)
    return str(archivo)


def procesar_mes(conn, mes: str, escribir=True, simulado=False) -> dict:
    catalogo = leer(conn, "SELECT cuenta_codigo, nombre, grupo, codigo_formato, linea_formato FROM cuentas")
    meses = [m[0] for m in conn.execute("SELECT DISTINCT periodo FROM saldos ORDER BY 1")]
    anterior = leer(conn, "SELECT * FROM saldos WHERE periodo=?", (meses[meses.index(mes) - 1],)) if meses.index(mes) else None
    historia = leer(conn, "SELECT periodo, sede_id, rol, personas, costo, fuente FROM personal WHERE periodo<=?", (mes,))
    gastos = leer(conn, "SELECT g.*, s.concesionario_id FROM gastos g JOIN sedes s USING(sede_id) WHERE periodo<=?", (mes,))
    conn.execute("DELETE FROM alertas WHERE periodo=?", (mes,))
    ts = hora_carga(mes, "historico_simulado" if simulado else "rutina")
    todas, anomalias_mes, archivos = [], detectar_anomalias(gastos, mes), []
    for cid, nombre in conn.execute("SELECT concesionario_id, nombre FROM concesionarios ORDER BY 1").fetchall():
        alertas, controles, esf, eri, r = validar_concesionario(conn, mes, cid, catalogo, anterior, historia)
        for _, a in anomalias_mes[anomalias_mes.concesionario_id == cid].iterrows():
            alertas.append(alerta(mes, cid, a.sede_id, "anomalia_gasto", a.severidad, f"{a.tipo}: {a.proveedor}", a.explicacion, a.impacto_cop, a.origen))
        todas += alertas
        if escribir:
            r.update(esf=esf, eri=eri)
            archivos.append(escribir_formato(conn, mes, cid, nombre, r, controles, alertas))
    todas.sort(key=lambda a: (a["concesionario_id"] != "AND", a["concesionario_id"], ORDEN_SEV[a["severidad"]], -(a["impacto_cop"] or 0)))
    conn.executemany("INSERT INTO alertas (periodo,concesionario_id,sede_id,regla,severidad,hallazgo,explicacion,impacto_cop,origen,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     [(a["periodo"], a["concesionario_id"], a["sede_id"], a["regla"], a["severidad"], a["hallazgo"], a["explicacion"], a["impacto_cop"], a["origen"], "src/procesamiento.py", ts) for a in todas])
    if escribir:
        carpeta = SALIDAS / mes
        vista = pd.DataFrame(todas).rename(columns={"concesionario_id": "concesionario", "sede_id": "sede", "severidad": "Severidad", "hallazgo": "Hallazgo", "explicacion": "Explicación", "impacto_cop": "Impacto (COP)", "origen": "Origen (archivo!celda)"})
        with pd.ExcelWriter(carpeta / f"alertas_{mes}.xlsx", engine="openpyxl") as x:
            vista.to_excel(x, sheet_name="Alertas", index=False)
        dar_formato(carpeta / f"alertas_{mes}.xlsx")
        with pd.ExcelWriter(carpeta / f"anomalias_gastos_{mes}.xlsx", engine="openpyxl") as x:
            anomalias_mes.to_excel(x, sheet_name="Anomalías", index=False)
        dar_formato(carpeta / f"anomalias_gastos_{mes}.xlsx")
    altas = sum(a["severidad"] == "Alta" for a in todas)
    if simulado:
        conn.execute("DELETE FROM bitacora WHERE periodo=? AND paso IN ('validacion','aprobacion')", (mes,))
    conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                 (ts, mes, "validacion", "Requiere revisión" if altas else "Correcto", f"{len(todas)} alertas ({altas} altas) y {len(anomalias_mes)} anomalías de gasto", "Agente de procesamiento", "src/procesamiento.py", ts))
    if simulado:
        conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                     (ts, mes, "aprobacion", "Aprobado", "Cierre revisado y aprobado (historia simulada)", "Analista de cierre (simulado)", "src/procesamiento.py", ts))
    conn.commit()
    return {"alertas": len(todas), "altas": altas, "anomalias": len(anomalias_mes), "archivos": archivos}


def main() -> None:
    p = argparse.ArgumentParser(description="Agente de procesamiento")
    p.add_argument("--mes", default="2026-10")
    p.add_argument("--historial", action="store_true")
    a = p.parse_args()
    conn = conectar()
    if a.historial:
        meses = [m[0] for m in conn.execute("SELECT DISTINCT periodo FROM saldos ORDER BY 1")]
        for m in meses:
            if m != a.mes:
                r = procesar_mes(conn, m, escribir=False, simulado=True)
                print(f"  {m}: {r['alertas']} alertas ({r['altas']} altas)")
    r = procesar_mes(conn, a.mes, simulado=a.historial)
    if a.historial:
        conn.execute("DELETE FROM bitacora WHERE periodo=? AND paso='aprobacion'", (a.mes,))
        conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                     (hora_carga(a.mes, "historico_simulado"), a.mes, "aprobacion", "Pendiente", "Esperando revisión humana de las alertas altas", "Analista de cierre (simulado)", "src/procesamiento.py", hora_carga(a.mes, "historico_simulado")))
        conn.commit()
    exportar_csv(conn)
    conn.close()
    print(f"Procesamiento de {nombre_mes(a.mes)}: {r['alertas']} alertas, {r['altas']} altas, {r['anomalias']} anomalías. {NOTA}.")


if __name__ == "__main__":
    main()
