"""Crea la tabla de homologación PUC -> formato y el diccionario de datos.

La cuenta 5195 Diversos queda por fuera a propósito: el validador debe detectarla.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from esquema import diccionario_md

RAIZ = Path(__file__).resolve().parents[1]
MAPEO = RAIZ / "00_manuales" / "mapeo_puc_formato.xlsx"

FILAS = [
    ("1105", "Caja", "ESF", "Activo", "ESF.1.01", "Efectivo"),
    ("1110", "Bancos", "ESF", "Activo", "ESF.1.01", "Efectivo"),
    ("1305", "Clientes", "ESF", "Activo", "ESF.1.02", "Cuentas por cobrar"),
    ("143501", "Inventario Livianos", "ESF", "Activo", "ESF.1.03", "Inventario Livianos"),
    ("143502", "Inventario Eléctricos", "ESF", "Activo", "ESF.1.04", "Inventario Eléctricos"),
    ("143503", "Inventario Usados", "ESF", "Activo", "ESF.1.05", "Inventario Usados"),
    ("143504", "Inventario Pesados", "ESF", "Activo", "ESF.1.06", "Inventario Pesados"),
    ("143505", "Inventario Repuestos", "ESF", "Activo", "ESF.1.07", "Inventario Repuestos"),
    ("1516", "Construcciones", "ESF", "Activo", "ESF.1.08", "Activos fijos"),
    ("1524", "Equipo de oficina", "ESF", "Activo", "ESF.1.08", "Activos fijos"),
    ("1592", "Depreciación acumulada", "ESF", "Activo", "ESF.1.08", "Activos fijos"),
    ("2105", "Obligaciones wholesale", "ESF", "Pasivo", "ESF.2.01", "Obligaciones wholesale"),
    ("2205", "Proveedores", "ESF", "Pasivo", "ESF.2.02", "Proveedores"),
    ("2404", "Impuesto de renta", "ESF", "Pasivo", "ESF.2.03", "Impuestos"),
    ("2408", "IVA por pagar", "ESF", "Pasivo", "ESF.2.03", "Impuestos"),
    ("2505", "Salarios por pagar", "ESF", "Pasivo", "ESF.2.04", "Obligaciones laborales"),
    ("3105", "Capital social", "ESF", "Patrimonio", "ESF.3.01", "Capital"),
    ("3605", "Utilidad del ejercicio", "ESF", "Patrimonio", "ESF.3.02", "Resultados"),
    ("3705", "Utilidades acumuladas", "ESF", "Patrimonio", "ESF.3.02", "Resultados"),
    ("4135", "Ventas netas", "ERI", "Ingresos", "ERI.01", "Ventas netas"),
    ("6135", "Costo de ventas", "ERI", "Costos", "ERI.02", "Costo de ventas"),
    ("5205", "Gastos variables", "ERI", "Gastos", "ERI.04", "Gastos variables"),
    ("5105", "Gastos de personal", "ERI", "Gastos", "ERI.05", "Gastos de personal"),
    ("5135", "Gastos semifijos", "ERI", "Gastos", "ERI.06", "Gastos semifijos"),
    ("5120", "Gastos fijos", "ERI", "Gastos", "ERI.07", "Gastos fijos"),
    ("5305", "Gasto financiero", "ERI", "Gastos", "ERI.08", "Gasto financiero"),
]
ENCABEZADOS = ["cuenta_codigo", "nombre", "seccion", "grupo", "codigo_formato", "linea_formato"]


def crear() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Mapeo"
    ws.append(ENCABEZADOS)
    for celda in ws[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="1F4E79")
    for fila in FILAS:
        ws.append(list(fila))
    for col, ancho in zip("ABCDEF", [15, 28, 10, 13, 16, 28]):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = "A2"
    wb.save(MAPEO)
    (RAIZ / "00_manuales" / "diccionario_de_datos.md").write_text(diccionario_md(), encoding="utf-8")


if __name__ == "__main__":
    crear()
    print(f"Mapeo creado con {len(FILAS)} cuentas. Datos simulados.")
