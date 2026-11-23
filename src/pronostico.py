#!/usr/bin/env python3
"""Agente predictivo: proyecta el cierre del año con drivers y lo compara con un modelo estadístico.

Fórmula central: unidades x precio x margen, por canal.
Uso: python src/pronostico.py --mes 2026-10
"""
from __future__ import annotations

import argparse
import json
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

from comun import NOTA, PALETA, RAIZ, SALIDAS, miles_millones, nombre_mes, pct
from ingesta import conectar, exportar_csv, hora_carga

CANALES = ["Retail", "Flotas", "Plan de ahorro", "Eléctricos"]
ESCENARIOS = {
    # "demanda" es un supuesto explícito, calibrado para que el rango coincida con la presentación ($145-152 mil millones).
    # Flotas y tasa por sí solas mueven el cierre apenas unos $0,3 mil millones.
    "Optimista": {"flotas": .10, "retail": 0.0, "tasa_bp": 0, "dic": 0.0, "demanda": .09},
    "Base": {"flotas": 0.0, "retail": 0.0, "tasa_bp": 0, "dic": 0.0, "demanda": 0.0},
    "Pesimista": {"flotas": -.15, "retail": 0.0, "tasa_bp": 200, "dic": 0.0, "demanda": -.14},
}
TASA_ILUSTRATIVA = .012
Z_80 = 1.2816
Z_95 = 1.96


def cargar_series(conn):
    ventas = pd.read_sql_query("""SELECT s.concesionario_id cid, v.periodo, v.canal, COUNT(*) unidades, SUM(v.precio - v.descuento) ingresos, SUM(v.margen) margen
                                  FROM ventas v JOIN sedes s USING(sede_id) GROUP BY 1,2,3""", conn)
    saldos = pd.read_sql_query("""SELECT s.concesionario_id cid, x.periodo, substr(x.cuenta_origen,1,4) cuenta, SUM(x.saldo) valor
                                  FROM saldos x JOIN sedes s USING(sede_id) WHERE x.cuenta_origen LIKE '%-%' GROUP BY 1,2,3""", conn)
    deuda = pd.read_sql_query("""SELECT s.concesionario_id cid, o.periodo, SUM(o.saldo) saldo, SUM(o.interes_mes) interes
                                 FROM obligaciones o JOIN sedes s USING(sede_id) GROUP BY 1,2""", conn)
    eri = saldos.pivot_table(index=["cid", "periodo"], columns="cuenta", values="valor", aggfunc="sum", fill_value=0).reset_index()
    if "5195" not in eri:
        eri["5195"] = 0
    eri["ingresos"] = eri["4135"]
    eri["bruto"] = eri["4135"] - eri["6135"]
    eri["semifijo"] = eri["5135"] + eri["5195"]
    eri["utilidad"] = eri.bruto - eri["5205"] - eri["5105"] - eri.semifijo - eri["5120"] - eri["5305"]
    eri = eri.rename(columns={"5205": "variable", "5105": "personal", "5120": "fijo", "5305": "financiero"})
    veh = ventas.groupby(["cid", "periodo"])[["ingresos", "margen"]].sum().rename(columns={"ingresos": "ing_veh", "margen": "mar_veh"}).reset_index()
    eri = eri.merge(veh, on=["cid", "periodo"]).merge(deuda, on=["cid", "periodo"])
    eri["ing_otros"], eri["mar_otros"] = eri.ingresos - eri.ing_veh, eri.bruto - eri.mar_veh
    return ventas, eri[["cid", "periodo", "ingresos", "bruto", "variable", "personal", "semifijo", "fijo", "financiero", "utilidad", "ing_otros", "mar_otros", "saldo", "interes"]]


def _periodos(corte, n):
    return [str(pd.Period(corte) + i) for i in range(1, n + 1)]


def _atras(periodo, n):
    return str(pd.Period(periodo) - n)


def _ventana(corte, n):
    return [_atras(corte, i) for i in range(n - 1, -1, -1)]


def preparar_base(ventas, eri, cid, corte, n):
    """Calcula los drivers con información disponible hasta el mes de corte."""
    v = ventas[(ventas.cid == cid) & (ventas.periodo <= corte)]
    e = eri[(eri.cid == cid) & (eri.periodo <= corte)].set_index("periodo")
    ult6, previo6, ult12 = _ventana(corte, 6), [_atras(p, 12) for p in _ventana(corte, 6)], _ventana(corte, 12)
    total_unidades = v.groupby("periodo").unidades.sum()

    def indice_estacional(periodo):
        """Peso del mismo mes del año anterior frente a los 12 meses que lo rodean (todas las líneas)."""
        q = pd.Period(periodo) - 12
        ventana = [str(q + k) for k in range(-5, 7)]
        media = total_unidades.reindex(ventana).dropna().mean()
        return float(total_unidades.get(str(q), media) / media)

    meses = []
    for destino in _periodos(corte, n):
        ly, canales = _atras(destino, 12), {}
        for canal in CANALES:
            h = v[v.canal == canal].set_index("periodo")
            suma = lambda col, ps: float(h[col].reindex(ps).fillna(0).sum())
            u_act, u_prev = suma("unidades", ult6), suma("unidades", previo6)
            i_act, i_prev = suma("ingresos", ult6), suma("ingresos", previo6)
            precio_act = i_act / u_act if u_act else 0
            precio_prev = i_prev / u_prev if u_prev else precio_act
            if canal == "Flotas":  # Flotas es irregular: se usa el promedio de 12 meses.
                unidades = suma("unidades", ult12) / 12
                precio = suma("ingresos", ult12) / max(suma("unidades", ult12), 1)
            else:
                g_u = np.clip(u_act / u_prev, .80, 1.35) if u_prev else 1.0
                g_p = np.clip(precio_act / precio_prev, .90, 1.15) if precio_prev else 1.0
                p_ly = float(h.ingresos.get(ly, 0) / h.unidades.get(ly, 1)) if ly in h.index else precio_act
                # Nivel reciente sin estacionalidad x estacionalidad del mes x tendencia desde la mitad de la ventana.
                nivel = u_act / sum(indice_estacional(p) for p in ult6)
                rezago = (pd.Period(destino) - pd.Period(corte)).n + 2.5
                unidades, precio = nivel * indice_estacional(destino) * g_u ** (rezago / 12), p_ly * g_p
            margen = suma("margen", ult6) / i_act if i_act else 0
            canales[canal] = {"unidades": float(unidades), "precio": float(precio), "margen": float(margen)}
        crec_otros = np.clip(e.ing_otros.reindex(ult6).sum() / e.ing_otros.reindex(previo6).sum(), .85, 1.25)
        meses.append({"periodo": destino, "canales": canales, "ing_otros": float(e.ing_otros.get(ly, e.ing_otros.tail(6).mean()) * crec_otros),
                      "margen_otros": float(e.mar_otros.reindex(ult6).sum() / e.ing_otros.reindex(ult6).sum()),
                      "variable_pct": float(e.variable.reindex(ult6).sum() / e.ingresos.reindex(ult6).sum()),
                      "personal": float(e.personal.loc[corte]), "semifijo": float(e.semifijo.reindex(ult6).mean()), "fijo": float(e.fijo.reindex(ult6).mean()),
                      "saldo": float(e.saldo.loc[corte]), "tasa": float(e.interes.loc[corte] / e.saldo.loc[corte])})
    return meses


def aplicar(base, p):
    """Recalcula ingresos y utilidad con los supuestos. El tablero usa exactamente esta fórmula."""
    salida = []
    for m in base:
        estacional = (1 + p["dic"] if m["periodo"].endswith("-12") else 1) * (1 + p.get("demanda", 0))
        ingreso_v = bruto_v = 0.0
        for canal, d in m["canales"].items():
            factor = (1 + p["flotas"]) if canal == "Flotas" else ((1 + p["retail"]) * estacional if canal == "Retail" else estacional)
            ingreso = d["unidades"] * factor * d["precio"]
            ingreso_v += ingreso
            bruto_v += ingreso * d["margen"]
        otros = m["ing_otros"] * estacional
        ingresos = ingreso_v + otros
        bruto = bruto_v + otros * m["margen_otros"]
        financiero = m["saldo"] * (m["tasa"] + p["tasa_bp"] / 10000 / 12)
        utilidad = bruto - ingresos * m["variable_pct"] - m["personal"] - m["semifijo"] - m["fijo"] - financiero
        salida.append({"periodo": m["periodo"], "ingresos": ingresos, "bruto": bruto, "financiero": financiero, "utilidad": utilidad})
    return salida


def modelo_ets(serie: pd.Series, n: int) -> list[float]:
    """Holt-Winters con 24 meses o más; con menos, Holt amortiguado sobre la serie sin estacionalidad."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if len(serie) >= 24:
            ajuste = ExponentialSmoothing(serie.values, trend="add", damped_trend=True, seasonal="mul", seasonal_periods=12, initialization_method="estimated").fit()
            return [float(x) for x in ajuste.forecast(n)]
        indice = pd.PeriodIndex(serie.index, freq="M")
        primeros = serie.iloc[:12]
        factores = (primeros / primeros.mean()).groupby(pd.PeriodIndex(primeros.index, freq="M").month).mean()
        sin_est = serie.values / np.array([factores.get(p.month, 1) for p in indice])
        ajuste = ExponentialSmoothing(sin_est, trend="add", damped_trend=True, initialization_method="estimated").fit()
        destinos = [indice[-1] + i for i in range(1, n + 1)]
        return [float(x * factores.get(p.month, 1)) for x, p in zip(ajuste.forecast(n), destinos)]


def backtest(ventas, eri, cid, corte="2026-06", n=3):
    e = eri[eri.cid == cid].set_index("periodo")
    drivers = aplicar(preparar_base(ventas, eri, cid, corte, n), ESCENARIOS["Base"])
    ets = modelo_ets(e.ingresos[e.index <= corte].astype(float), n)
    filas = []
    for d, valor_ets in zip(drivers, ets):
        real = float(e.ingresos.loc[d["periodo"]])
        filas.append({"periodo": d["periodo"], "real": real, "drivers": d["ingresos"], "ets": valor_ets, "error_drivers": d["ingresos"] / real - 1, "error_ets": valor_ets / real - 1})
    return {"corte": corte, "meses": filas, "mape_drivers": float(np.mean([abs(f["error_drivers"]) for f in filas])), "mape_ets": float(np.mean([abs(f["error_ets"]) for f in filas]))}


def error_historico(ventas, eri, cid, corte):
    """Error porcentual de pronósticos pasados a 1 y 2 meses: define el ancho de las bandas."""
    e = eri[eri.cid == cid].set_index("periodo")
    errores = []
    for c in sorted(e.index):
        if c < "2026-04" or c >= corte:
            continue
        for d in aplicar(preparar_base(ventas, eri, cid, c, 2), ESCENARIOS["Base"]):
            if d["periodo"] in e.index and d["periodo"] <= corte:
                errores.append(d["ingresos"] / float(e.ingresos.loc[d["periodo"]]) - 1)
    return float(np.sqrt(np.mean(np.square(errores)))) if errores else .04


def resultado_anual(base, p, ytd_i, ytd_u):
    r = aplicar(base, p)
    return ytd_i + sum(x["ingresos"] for x in r), ytd_u + sum(x["utilidad"] for x in r), r


def patrones(conn, mes):
    ventas = pd.read_sql_query("SELECT v.*, s.concesionario_id cid FROM ventas v JOIN sedes s USING(sede_id)", conn)
    ventas["neto"] = ventas.precio - ventas.descuento
    anual = ventas[ventas.periodo.between(str(pd.Period(mes) - 11), mes)]
    canal = anual.groupby("canal").agg(unidades=("vin", "count"), ingresos=("neto", "sum"), margen=("margen", "sum"), descuento=("descuento", "sum"), precio=("precio", "sum")).reset_index()
    canal["margen_pct"], canal["descuento_pct"] = canal.margen / canal.ingresos, canal.descuento / canal.precio
    modelos = anual.groupby("modelo").agg(unidades=("vin", "count"), ingresos=("neto", "sum"), margen=("margen", "sum")).reset_index()
    modelos["margen_pct"] = modelos.margen / modelos.ingresos
    modelos = modelos.sort_values("margen", ascending=False)
    ranking = pd.read_sql_query("""
      WITH r AS (SELECT s.concesionario_id cid, SUM(CASE WHEN substr(x.cuenta_origen,1,4)='4135' THEN x.saldo END) ing, SUM(CASE WHEN substr(x.cuenta_origen,1,4)='6135' THEN x.saldo END) cos
                 FROM saldos x JOIN sedes s USING(sede_id) WHERE x.periodo=? GROUP BY 1),
           i AS (SELECT s.concesionario_id cid, 1.0*SUM(CASE WHEN rango='>60' THEN costo ELSE 0 END)/SUM(costo) viejo FROM inventario x JOIN sedes s USING(sede_id) WHERE periodo=? GROUP BY 1),
           f AS (SELECT s.concesionario_id cid, 1.0*SUM(creditos)/SUM(unidades) pen FROM fi x JOIN sedes s USING(sede_id) WHERE periodo=? GROUP BY 1)
      SELECT c.concesionario_id cid, c.nombre, r.ing ingresos, 1.0*(r.ing-r.cos)/r.ing margen, i.viejo inventario_60, f.pen penetracion_fi
      FROM concesionarios c JOIN r ON r.cid=c.concesionario_id JOIN i ON i.cid=c.concesionario_id JOIN f ON f.cid=c.concesionario_id""", conn, params=(mes, mes, mes))
    ranking["puesto_margen"] = ranking.margen.rank(ascending=False).astype(int)
    ranking["puesto_inventario"] = ranking.inventario_60.rank().astype(int)
    ranking["puesto_fi"] = ranking.penetracion_fi.rank(ascending=False).astype(int)
    ranking["puntaje"] = ranking.puesto_margen + ranking.puesto_inventario + ranking.puesto_fi
    costo = pd.read_sql_query("""SELECT s.concesionario_id cid, i.periodo, SUM(i.costo) saldo_60 FROM inventario i JOIN sedes s USING(sede_id)
                                 WHERE i.rango='>60' GROUP BY 1,2""", conn)
    costo["costo_financiero"] = costo.saldo_60 * TASA_ILUSTRATIVA
    return {"canales": canal.to_dict("records"), "modelos_top": modelos.head(5).to_dict("records"), "modelos_bottom": modelos.tail(5).to_dict("records"),
            "ranking": ranking.sort_values("puntaje").to_dict("records"), "costo_inventario": costo.to_dict("records"), "tasa_ilustrativa": TASA_ILUSTRATIVA}


def estilo(ax, titulo):
    ax.set_facecolor(PALETA["crema"])
    ax.figure.set_facecolor(PALETA["crema"])
    ax.set_title(titulo, loc="left", fontsize=13, fontfamily="serif", color=PALETA["navy"], fontweight="bold")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    ax.grid(axis="y", color="#D9CFBE", linewidth=.6)
    ax.figure.text(.99, .01, NOTA, ha="right", fontsize=8, color="#6F6658")


def graficos(res, mes):
    carpeta = SALIDAS / mes / "graficos"
    carpeta.mkdir(parents=True, exist_ok=True)
    a = res["concesionarios"]["AND"]
    hist = a["historia"][-12:]
    x = [h["periodo"] for h in hist]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.plot(x, [h["ingresos"] / 1e9 for h in hist], color=PALETA["navy"], lw=2.2, label="Real")
    for nombre, color in [("Optimista", PALETA["teal"]), ("Base", PALETA["ciruela"]), ("Pesimista", PALETA["terracota"])]:
        e = a["escenarios"][nombre]
        xs = [x[-1]] + [m["periodo"] for m in e["meses"]]
        ys = [hist[-1]["ingresos"] / 1e9] + [m["ingresos"] / 1e9 for m in e["meses"]]
        ax.plot(xs, ys, "--o", color=color, ms=3.5, label=nombre)
    b = a["escenarios"]["Base"]["meses"]
    ax.fill_between([m["periodo"] for m in b], [m["banda95_inf"] / 1e9 for m in b], [m["banda95_sup"] / 1e9 for m in b], color=PALETA["ciruela"], alpha=.10, label="Banda 95 %")
    ax.fill_between([m["periodo"] for m in b], [m["banda_inf"] / 1e9 for m in b], [m["banda_sup"] / 1e9 for m in b], color=PALETA["ciruela"], alpha=.18, label="Banda 80 %")
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("COP miles de millones")
    ax.legend(frameon=False, ncol=5, fontsize=8)
    estilo(ax, "Ingresos: real y escenarios")
    fig.tight_layout()
    fig.savefig(carpeta / "pronostico_escenarios.png", dpi=150)
    plt.close(fig)
    t = sorted(a["tornado"], key=lambda f: abs(f["alto"] - f["bajo"]))
    fig, ax = plt.subplots(figsize=(8, 3.8))
    for i, f in enumerate(t):
        ax.barh(i, f["bajo"] / 1e6, color=PALETA["terracota"])
        ax.barh(i, f["alto"] / 1e6, color=PALETA["teal"])
    ax.set_yticks(range(len(t)), [f["supuesto"] for f in t])
    ax.axvline(0, color="#333", lw=.8)
    ax.set_xlabel("Cambio en utilidad operativa 2026 (COP millones)")
    estilo(ax, "Sensibilidad de la utilidad operativa")
    ax.grid(axis="x", color="#D9CFBE", linewidth=.6)
    fig.tight_layout()
    fig.savefig(carpeta / "tornado.png", dpi=150)
    plt.close(fig)
    s = a["sensibilidad"]
    fig, ax = plt.subplots(figsize=(6.4, 4))
    matriz = np.array(s["utilidad"]) / 1e9
    ax.imshow(matriz, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(3), s["flotas_etiquetas"])
    ax.set_yticks(range(3), s["tasa_etiquetas"])
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{matriz[i, j]:.2f}".replace(".", ","), ha="center", va="center", color="#111")
    estilo(ax, "Utilidad operativa 2026 (COP miles de millones)")
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(carpeta / "sensibilidad.png", dpi=150)
    plt.close(fig)
    bt = a["backtest"]["meses"]
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    p = [m["periodo"] for m in bt]
    ax.plot(p, [m["real"] / 1e9 for m in bt], "-o", color=PALETA["navy"], label="Real")
    ax.plot(p, [m["drivers"] / 1e9 for m in bt], "--o", color=PALETA["teal"], label="Drivers")
    ax.plot(p, [m["ets"] / 1e9 for m in bt], ":o", color=PALETA["terracota"], label="ETS")
    ax.set_ylabel("COP miles de millones")
    ax.legend(frameon=False)
    estilo(ax, "Backtest julio a septiembre de 2026")
    fig.tight_layout()
    fig.savefig(carpeta / "backtest.png", dpi=150)
    plt.close(fig)


def pronosticar(conn, mes: str) -> dict:
    ventas, eri = cargar_series(conn)
    anio = mes[:4]
    n = 12 - int(mes[5:])
    ts = hora_carga(mes, "rutina")
    conn.execute("DELETE FROM pronosticos WHERE periodo_base=?", (mes,))
    salida = {"nota": NOTA, "periodo_base": mes, "tasa_interpretacion": "Los puntos básicos (bp) son anuales: +200 bp equivalen a +0,167 puntos en la tasa mensual.",
              "supuesto_demanda": "Ritmo de demanda de noviembre y diciembre: +9 % (Optimista) y -14 % (Pesimista). Es un supuesto ilustrativo calibrado al rango de la presentación, no un resultado del modelo.", "concesionarios": {}}
    filas_db = []
    for cid, nombre in conn.execute("SELECT concesionario_id, nombre FROM concesionarios ORDER BY 1").fetchall():
        e = eri[(eri.cid == cid) & (eri.periodo <= mes)].sort_values("periodo")
        ytd = e[e.periodo.str.startswith(anio)]
        ytd_i, ytd_u = float(ytd.ingresos.sum()), float(ytd.utilidad.sum())
        base = preparar_base(ventas, eri, cid, mes, n)
        sigma = error_historico(ventas, eri, cid, mes)
        escenarios = {}
        for nombre_e, p in ESCENARIOS.items():
            ing, uti, meses = resultado_anual(base, p, ytd_i, ytd_u)
            for h, m in enumerate(meses, start=1):
                ancho = Z_80 * sigma * np.sqrt(h)
                ancho95 = Z_95 * sigma * np.sqrt(h)
                m["banda_inf"], m["banda_sup"] = m["ingresos"] * (1 - ancho), m["ingresos"] * (1 + ancho)
                m["banda95_inf"], m["banda95_sup"] = m["ingresos"] * (1 - ancho95), m["ingresos"] * (1 + ancho95)
                for metrica in ("ingresos", "utilidad"):
                    filas_db.append((mes, m["periodo"], cid, nombre_e, "Drivers", metrica, float(m[metrica]), "src/pronostico.py", ts))
            resto = sum(m["ingresos"] for m in meses)
            # Prudente: supone que si un mes se desvía, el siguiente se desvía en la misma dirección.
            escenarios[nombre_e] = {"supuestos": p, "meses": meses, "ingresos_anio": ing, "utilidad_anio": uti,
                                    "banda_inf_anio": ytd_i + resto * (1 - Z_80 * sigma), "banda_sup_anio": ytd_i + resto * (1 + Z_80 * sigma),
                                    "banda95_inf_anio": ytd_i + resto * (1 - Z_95 * sigma), "banda95_sup_anio": ytd_i + resto * (1 + Z_95 * sigma)}
        serie = e.set_index("periodo").ingresos.astype(float)
        ets = modelo_ets(serie, n)
        for destino, v in zip(_periodos(mes, n), ets):
            filas_db.append((mes, destino, cid, "Base", "ETS", "ingresos", float(v), "src/pronostico.py", ts))
        descomp = seasonal_decompose(serie.values, model="additive", period=12)
        tasas, flotas = [0, 100, 200], [.10, 0.0, -.15]
        matriz = [[resultado_anual(base, {"flotas": f, "retail": 0.0, "tasa_bp": t, "dic": 0.0}, ytd_i, ytd_u)[1] for f in flotas] for t in tasas]
        u0 = escenarios["Base"]["utilidad_anio"]
        pruebas = [("Ritmo de demanda (-14 % / +9 %)", {"demanda": -.14}, {"demanda": .09}), ("Tasa wholesale (±200 bp)", {"tasa_bp": 200}, {"tasa_bp": -200}), ("Flotas (-15 % / +10 %)", {"flotas": -.15}, {"flotas": .10}),
                   ("Retail (±5 %)", {"retail": -.05}, {"retail": .05}), ("Estacionalidad diciembre (±10 %)", {"dic": -.10}, {"dic": .10})]
        tornado = []
        for etiqueta, bajo, alto in pruebas:
            ub = resultado_anual(base, {**ESCENARIOS["Base"], **bajo}, ytd_i, ytd_u)[1]
            ua = resultado_anual(base, {**ESCENARIOS["Base"], **alto}, ytd_i, ytd_u)[1]
            tornado.append({"supuesto": etiqueta, "bajo": ub - u0, "alto": ua - u0})
        tornado.sort(key=lambda f: -abs(f["alto"] - f["bajo"]))
        salida["concesionarios"][cid] = {
            "nombre": nombre, "ytd_ingresos": ytd_i, "ytd_utilidad": ytd_u, "sigma": sigma, "motor": base, "escenarios": escenarios,
            "historia": e[["periodo", "ingresos", "bruto", "utilidad"]].to_dict("records"),
            "ets": [{"periodo": p, "ingresos": v} for p, v in zip(_periodos(mes, n), ets)], "ets_anio": ytd_i + sum(ets),
            "backtest": backtest(ventas, eri, cid),
            "sensibilidad": {"tasas": tasas, "flotas": flotas, "tasa_etiquetas": ["+0 bp", "+100 bp", "+200 bp"], "flotas_etiquetas": ["Flotas +10 %", "Flotas 0 %", "Flotas -15 %"], "utilidad": matriz},
            "tornado": tornado,
            "descomposicion": {"periodos": serie.index.tolist(), "observado": serie.tolist(), "tendencia": [None if np.isnan(x) else float(x) for x in descomp.trend],
                               "estacional": [float(x) for x in descomp.seasonal], "residuo": [None if np.isnan(x) else float(x) for x in descomp.resid]},
        }
    conn.executemany("INSERT INTO pronosticos (periodo_base,periodo,concesionario_id,escenario,modelo,metrica,valor,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?,?)", filas_db)
    salida["patrones"] = patrones(conn, mes)
    a = salida["concesionarios"]["AND"]["escenarios"]
    conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                 (ts, mes, "pronostico", "Correcto", f"Cierre {anio} Andino: {miles_millones(a['Pesimista']['ingresos_anio'])} a {miles_millones(a['Optimista']['ingresos_anio'])}", "Agente predictivo", "src/pronostico.py", ts))
    conn.commit()
    texto = json.dumps(salida, ensure_ascii=False, default=float)
    for carpeta in (SALIDAS / mes, RAIZ / "docs" / "data"):
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "pronostico.json").write_text(texto, encoding="utf-8")
    graficos(json.loads(texto), mes)
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description="Agente predictivo")
    p.add_argument("--mes", default="2026-10")
    a = p.parse_args()
    conn = conectar()
    r = pronosticar(conn, a.mes)
    exportar_csv(conn)
    conn.close()
    x = r["concesionarios"]["AND"]
    print(f"Pronóstico desde {nombre_mes(a.mes)} para Concesionario Andino ({NOTA}):")
    for n, e in x["escenarios"].items():
        print(f"  {n}: ingresos {miles_millones(e['ingresos_anio'], 2)} · utilidad {miles_millones(e['utilidad_anio'], 2)}")
    print(f"  Backtest MAPE: drivers {pct(x['backtest']['mape_drivers'])}, ETS {pct(x['backtest']['mape_ets'])}")


if __name__ == "__main__":
    main()
