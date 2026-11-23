"""Puntos de control del cierre. Si alguno falla, la rutina no publica."""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

import ingesta
import motor

RAIZ = Path(__file__).resolve().parents[1]
MES = "2026-10"
SALIDA = RAIZ / "03_salidas" / MES


def alertas(conn, regla):
    return conn.execute("SELECT sede_id, severidad, hallazgo, explicacion, impacto_cop, origen FROM alertas WHERE periodo=? AND concesionario_id='AND' AND regla=?", (MES, regla)).fetchall()


def test_suma_de_sedes_igual_consolidado():
    eri = pd.read_excel(SALIDA / f"formato_consolidado_{MES}.xlsx", sheet_name="ERI", header=1)
    for linea in ("Ventas netas", "Costo de ventas", "Utilidad operativa"):
        f = eri[eri["Línea"] == linea]
        assert f[f["Alcance"] != "Consolidado"]["Total"].sum() == f[f["Alcance"] == "Consolidado"]["Total"].iloc[0]


def test_ecuacion_contable(conn):
    filas = conn.execute("""SELECT periodo, sede_id, SUM(CASE WHEN substr(cuenta_origen,1,1)='1' THEN saldo ELSE -saldo END)
                            FROM saldos WHERE cuenta_origen NOT LIKE '%-%' GROUP BY 1,2""").fetchall()
    descuadres = {(p, s): d for p, s, d in filas if d != 0}
    assert descuadres == {(MES, "SUR"): -18_400_000}


def test_calibracion_con_las_diapositivas(conn):
    esperado = [11.2, 10.4, 12.1, 11.6, 12.8, 11.9, 12.4, 13.1, 12.2, 12.9]
    filas = conn.execute("""SELECT x.periodo, SUM(x.saldo) FROM saldos x JOIN sedes s USING(sede_id)
                            WHERE s.concesionario_id='AND' AND x.cuenta_codigo='4135' AND x.periodo LIKE '2026-%' GROUP BY 1 ORDER BY 1""").fetchall()
    assert [round(v / 1e9, 1) for _, v in filas] == esperado
    inv = dict(((l, r), v) for l, r, v in conn.execute("""SELECT i.linea, i.rango, SUM(i.costo) FROM inventario i JOIN sedes s USING(sede_id)
                                                          WHERE s.concesionario_id='AND' AND i.periodo=? GROUP BY 1,2""", (MES,)))
    objetivo = {"Livianos": (4200, 1900, 1100), "Eléctricos": (1300, 800, 900), "Usados": (700, 500, 1050), "Pesados": (900, 400, 350)}
    for linea, valores in objetivo.items():
        assert [inv[(linea, r)] for r in ("0-30", "31-60", ">60")] == [v * 1_000_000 for v in valores]


def test_error_1_proveedores_duplicado(conn):
    f = alertas(conn, "ecuacion_contable")
    assert len(f) == 1 and f[0][0] == "SUR" and f[0][1] == "Alta" and f[0][4] == 18_400_000 and "2205" in f[0][3]


def test_error_2_personal_norte(conn):
    f = alertas(conn, "personal_vs_promedio")
    assert len(f) == 1 and f[0][0] == "NOR" and "14,0 %" in f[0][2] and "3 personas" in f[0][3]


def test_error_3_usados_mas_de_60(conn):
    f = [x for x in alertas(conn, "antiguedad_inventario") if x[2].startswith("Usados")]
    assert len(f) == 1 and "31 %" in f[0][2] and "6 unidades" in f[0][3]


def test_error_4_cuenta_sin_mapear(conn):
    f = alertas(conn, "cuenta_sin_mapear")
    assert len(f) == 1 and "5195" in f[0][2] and "por confirmar" in f[0][3]


def test_error_5_anomalias_de_gasto(conn):
    textos = " | ".join(x[2] for x in alertas(conn, "anomalia_gasto"))
    for tipo in ("Pago duplicado", "Proveedor nuevo", "Monto atípico", "Registro en fin de semana"):
        assert tipo in textos


def test_archivo_sin_encabezados_se_lee_por_contenido():
    filas = ingesta.leer_inventario(RAIZ / "01_insumos" / MES / "AND" / "inventario_dias.xlsx", {"NOR", "CEN", "SUR"})
    assert len(filas) == 191 and all(f["costo"] > f["dias"] for f in filas)


def test_archivo_irreconocible_se_reporta_y_no_rompe(tmp_path, monkeypatch):
    insumos = tmp_path / "01_insumos"
    shutil.copytree(RAIZ / "01_insumos" / MES / "AND", insumos / MES / "AND")
    (insumos / MES / "AND" / "NOR_balance.xlsx").unlink()
    (insumos / MES / "AND" / "NOR_balance.csv").write_text("hola;mundo\nsin;cuentas\n", encoding="utf-8")
    base = tmp_path / "cierre.db"
    shutil.copy(RAIZ / "02_procesados" / "cierre.db", base)
    monkeypatch.setattr(ingesta, "INSUMOS", insumos)
    c = ingesta.conectar(base)
    r = ingesta.cargar_mes(c, MES)
    estado = c.execute("SELECT estado, filas FROM cargas WHERE periodo=? AND archivo LIKE '%NOR_balance%'", (MES,)).fetchone()
    inventadas = c.execute("SELECT COUNT(*) FROM saldos WHERE periodo=? AND sede_id='NOR'", (MES,)).fetchone()[0]
    c.close()
    assert estado == ("Revisar", 0) and inventadas == 0 and len(r["revisar"]) == 1


def test_pronostico_backtest_y_rango():
    x = json.loads((SALIDA / "pronostico.json").read_text(encoding="utf-8"))["concesionarios"]["AND"]
    assert x["backtest"]["mape_drivers"] < .05
    assert 145e9 <= x["escenarios"]["Pesimista"]["ingresos_anio"] < x["escenarios"]["Base"]["ingresos_anio"] < x["escenarios"]["Optimista"]["ingresos_anio"] <= 152e9


def test_costo_del_inventario_envejecido(conn):
    v = conn.execute("SELECT SUM(i.costo) FROM inventario i JOIN sedes s USING(sede_id) WHERE s.concesionario_id='AND' AND i.periodo=? AND i.rango='>60'", (MES,)).fetchone()[0]
    assert v * .012 == pytest.approx(40_800_000)


def test_motor_que_cambia_cifras_se_descarta(monkeypatch):
    monkeypatch.setenv("MOTOR", "ollama")
    monkeypatch.setattr(motor, "_ollama", lambda t: "Los ingresos fueron de $99,9 mil millones.")
    texto, estado = motor.reescribir("Los ingresos fueron de $12,9 mil millones.")
    assert texto == "Los ingresos fueron de $12,9 mil millones." and "alteró" in estado


def test_sin_motor_usa_plantilla(monkeypatch):
    monkeypatch.delenv("MOTOR", raising=False)
    assert motor.reescribir("Texto de prueba")[0] == "Texto de prueba"
