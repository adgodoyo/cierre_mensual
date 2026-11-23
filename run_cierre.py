#!/usr/bin/env python3
"""Ejecuta el cierre completo: procesamiento -> pronóstico -> reporte -> tablero.

Uso:
  python run_cierre.py --mes 2026-10       # cierra un mes
  python run_cierre.py --reconstruir       # regenera todo desde los datos simulados
  python run_cierre.py --mes 2026-10 --aprobado   # publica sin marca de borrador
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

from comun import NOTA, SALIDAS, millones, nombre_mes, pct  # noqa: E402
from ingesta import INSUMOS, cargar_mes, conectar, exportar_csv, hora_carga  # noqa: E402
from procesamiento import procesar_mes  # noqa: E402
from pronostico import pronosticar  # noqa: E402
from reporte import generar  # noqa: E402
from tablero import exportar  # noqa: E402


def paso(numero: int, texto: str) -> None:
    print(f"\nPaso {numero} de 5. {texto}", flush=True)


def ultimo_mes() -> str:
    meses = sorted(p.name for p in INSUMOS.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}", p.name))
    if not meses:
        raise SystemExit("No hay meses en 01_insumos. Ejecute: python run_cierre.py --reconstruir")
    return meses[-1]


def reconstruir_base(mes: str) -> None:
    for comando in (["04_pruebas/generar_datos.py"], ["src/crear_mapeo.py"], ["src/ingesta.py", "--reconstruir"], ["src/procesamiento.py", "--mes", mes, "--historial"]):
        subprocess.run([sys.executable, *comando], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL)


def registrar_aprobacion(conn, mes: str, altas: int, aprobado: bool) -> None:
    ts = hora_carga(mes, "rutina")
    resultado, accion = ("Aprobado", "Una persona aprobó el cierre") if aprobado else ("Pendiente", "Esperando revisión humana de las alertas altas") if altas else ("Aprobado", "Sin alertas altas: no requiere revisión")
    conn.execute("DELETE FROM bitacora WHERE periodo=? AND paso='aprobacion'", (mes,))
    conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                 (ts, mes, "aprobacion", resultado, accion, "Supervisión humana" if aprobado or altas else "Regla automática", "run_cierre.py", ts))
    conn.commit()


def escribir_estado(conn, mes: str, aprobado: bool) -> dict:
    filas = conn.execute("""SELECT c.nombre, a.severidad, a.hallazgo, a.explicacion, a.impacto_cop, a.origen FROM alertas a JOIN concesionarios c USING(concesionario_id)
                            WHERE a.periodo=? AND a.severidad='Alta' ORDER BY a.impacto_cop DESC""", (mes,)).fetchall()
    estado = {"mes": mes, "altas": len(filas), "aprobado": aprobado, "requiere_revision": bool(filas) and not aprobado}
    cuerpo = [f"# Revisión del cierre de {nombre_mes(mes)}", "", f"> {NOTA}. Los reportes quedan como **borrador** hasta aprobar.", "", "| Concesionario | Hallazgo | Explicación | Impacto | Origen |", "|---|---|---|---|---|"]
    cuerpo += [f"| {n} | {h} | {e} | {millones(i or 0)} | `{o}` |" for n, _, h, e, i, o in filas]
    cuerpo += ["", "**Para aprobar:** revise cada fila y cierre este Issue. La rutina volverá a generar los reportes sin la marca de borrador."]
    carpeta = SALIDAS / mes
    (carpeta / "revision_requerida.md").write_text("\n".join(cuerpo) + "\n", encoding="utf-8")
    (carpeta / "estado_cierre.json").write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    return estado


def main() -> None:
    p = argparse.ArgumentParser(description="Cierre mensual con agentes")
    p.add_argument("--mes", help="Mes AAAA-MM. Si se omite, usa el último disponible")
    p.add_argument("--aprobado", action="store_true", help="Una persona ya revisó las alertas")
    p.add_argument("--sin-audio", action="store_true", help="No genera audio nuevo")
    p.add_argument("--reconstruir", action="store_true", help="Regenera datos y base desde cero")
    a = p.parse_args()
    if a.mes and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", a.mes):
        raise SystemExit("El mes debe tener formato AAAA-MM, por ejemplo 2026-10")
    inicio = time.time()
    if a.reconstruir:
        print("Regenerando los 24 meses de datos simulados y la base de datos…", flush=True)
        reconstruir_base(a.mes or "2026-10")
    mes = a.mes or ultimo_mes()
    if not (INSUMOS / mes).is_dir():
        raise SystemExit(f"No hay archivos para {mes} en 01_insumos/{mes}")
    previo = SALIDAS / mes / "estado_cierre.json"
    aprobado = a.aprobado or (not a.reconstruir and previo.exists() and json.loads(previo.read_text(encoding="utf-8")).get("aprobado", False))
    print(f"Cierre de {nombre_mes(mes)} · {NOTA}")
    conn = conectar()
    paso(1, "Leyendo los archivos de las sedes")
    if a.reconstruir:
        print("  Ya cargados en la reconstrucción.")
    else:
        r = cargar_mes(conn, mes)
        print(f"  {r['archivos']} archivos y {r['filas']} filas." + (f" Por revisar: {len(r['revisar'])}." if r["revisar"] else ""))
    paso(2, "Consolidando y validando")
    if a.reconstruir:  # La reconstrucción ya validó el mes: se deja una sola fila en la bitácora.
        conn.execute("DELETE FROM bitacora WHERE periodo=? AND paso='validacion'", (mes,))
    v = procesar_mes(conn, mes)
    print(f"  {v['alertas']} alertas, {v['altas']} altas y {v['anomalias']} anomalías de gasto.")
    registrar_aprobacion(conn, mes, v["altas"], aprobado)
    paso(3, "Proyectando el cierre del año")
    x = pronosticar(conn, mes)["concesionarios"]["AND"]
    print(f"  Backtest con error medio de {pct(x['backtest']['mape_drivers'])}.")
    paso(4, "Redactando reportes y audio")
    generar(conn, mes, aprobado, not a.sin_audio)
    estado = escribir_estado(conn, mes, aprobado)
    exportar_csv(conn)
    paso(5, "Actualizando el tablero")
    exportar(conn, mes)
    conn.close()
    print(f"\nListo en {time.time() - inicio:.0f} segundos.")
    print("Requiere revisión humana: las versiones quedan en borrador." if estado["requiere_revision"] else "Cierre sin revisiones pendientes.")
    print("Ver el tablero: python -m http.server --directory docs 8000  y abrir http://localhost:8000")


if __name__ == "__main__":
    main()
