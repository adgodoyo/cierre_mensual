"""Esquema de la base de datos: una sola definición para las tablas y el diccionario de datos."""
from __future__ import annotations

ING = "src/ingesta.py"
SEDE = "REFERENCES sedes(sede_id)"
CONC = "REFERENCES concesionarios(concesionario_id)"
TRAZA = [
    ("fuente", "TEXT", "NOT NULL", "De dónde salió la fila (archivo!celda o script)", "2026-10/AND/SUR_balance.xlsx!C12"),
    ("cargado_en", "TEXT", "NOT NULL", "Fecha y hora de carga", "2026-11-05T07:00:00-05:00"),
]

TABLAS = {
    "concesionarios": {"descripcion": "Concesionarios de la red (ficticios).", "script": ING, "columnas": [
        ("concesionario_id", "TEXT", "PRIMARY KEY", "Código del concesionario", "AND"),
        ("nombre", "TEXT", "NOT NULL", "Nombre del concesionario", "Concesionario Andino")]},
    "sedes": {"descripcion": "Sedes de cada concesionario.", "script": ING, "columnas": [
        ("sede_id", "TEXT", "PRIMARY KEY", "Código de la sede", "NOR"),
        ("concesionario_id", "TEXT", f"NOT NULL {CONC}", "Concesionario al que pertenece", "AND"),
        ("nombre", "TEXT", "NOT NULL", "Nombre de la sede", "Norte")]},
    "cuentas": {"descripcion": "Homologación de cuentas PUC al formato mensual.", "script": "src/crear_mapeo.py", "columnas": [
        ("cuenta_codigo", "TEXT", "PRIMARY KEY", "Cuenta PUC", "2205"),
        ("nombre", "TEXT", "NOT NULL", "Nombre de la cuenta", "Proveedores"),
        ("seccion", "TEXT", "NOT NULL", "Estado financiero: ESF o ERI", "ESF"),
        ("grupo", "TEXT", "NOT NULL", "Grupo dentro del estado", "Pasivo"),
        ("codigo_formato", "TEXT", "NOT NULL", "Código de la línea en el formato", "ESF.2.02"),
        ("linea_formato", "TEXT", "NOT NULL", "Línea del formato", "Proveedores")]},
    "saldos": {"descripcion": "Saldo por mes, sede, cuenta y departamento.", "script": ING, "columnas": [
        ("saldo_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador de la fila", "1024"),
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "SUR"),
        ("cuenta_origen", "TEXT", "NOT NULL", "Cuenta tal como llegó en el archivo", "4135-LIV"),
        ("cuenta_codigo", "TEXT", "REFERENCES cuentas(cuenta_codigo)", "Cuenta homologada; vacía si no está en el mapeo", "4135"),
        ("departamento", "TEXT", "", "Departamento del ERI; vacío en el ESF", "LIV"),
        ("saldo", "INTEGER", "NOT NULL", "Valor en pesos (COP)", "18400000")]},
    "ventas": {"descripcion": "Una fila por vehículo vendido.", "script": ING, "columnas": [
        ("venta_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador de la venta", "311"),
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("vin", "TEXT", "NOT NULL", "Identificador del vehículo (simulado)", "SIMA4K2P9XT7LM3QR"),
        ("fecha", "TEXT", "NOT NULL", "Fecha de la venta", "2026-10-15"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "NOR"),
        ("canal", "TEXT", "NOT NULL", "Retail, Flotas, Plan de ahorro o Eléctricos", "Retail"),
        ("linea", "TEXT", "NOT NULL", "Línea del vehículo", "Livianos"),
        ("modelo", "TEXT", "NOT NULL", "Modelo ficticio", "Páramo SUV"),
        ("precio", "INTEGER", "NOT NULL", "Precio de lista (COP)", "76000000"),
        ("descuento", "INTEGER", "NOT NULL", "Descuento (COP)", "2100000"),
        ("costo", "INTEGER", "NOT NULL", "Costo (COP)", "66500000"),
        ("margen", "INTEGER", "NOT NULL", "Margen (COP)", "7400000")]},
    "inventario": {"descripcion": "Una fila por vehículo en inventario al cierre.", "script": ING, "columnas": [
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("vin", "TEXT", "NOT NULL", "Identificador del vehículo", "SIMB7Q2R8KD4NW6TJ"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "CEN"),
        ("linea", "TEXT", "NOT NULL", "Línea del vehículo", "Usados"),
        ("modelo", "TEXT", "NOT NULL", "Modelo ficticio", "Usado SUV"),
        ("dias", "INTEGER", "NOT NULL", "Días en inventario", "74"),
        ("rango", "TEXT", "NOT NULL", "0-30, 31-60 o >60", ">60"),
        ("costo", "INTEGER", "NOT NULL", "Costo (COP)", "118000000"),
        ("fecha_ingreso", "TEXT", "NOT NULL", "Fecha de ingreso", "2026-08-18")], "pk": "PRIMARY KEY (periodo, vin)"},
    "gastos": {"descripcion": "Libro de gastos: una fila por pago.", "script": ING, "columnas": [
        ("gasto_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador del pago", "87"),
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("fecha", "TEXT", "NOT NULL", "Fecha del pago", "2026-10-18"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "CEN"),
        ("cuenta_origen", "TEXT", "NOT NULL", "Cuenta del gasto", "5135"),
        ("proveedor", "TEXT", "NOT NULL", "Proveedor ficticio", "Conecta Datos"),
        ("concepto", "TEXT", "NOT NULL", "Concepto", "Internet y software"),
        ("valor", "INTEGER", "NOT NULL", "Valor (COP)", "4850000")]},
    "personal": {"descripcion": "Personas y costo por sede y rol.", "script": ING, "columnas": [
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "NOR"),
        ("rol", "TEXT", "NOT NULL", "Rol", "Vendedores"),
        ("personas", "INTEGER", "NOT NULL", "Número de personas", "12"),
        ("costo", "INTEGER", "NOT NULL", "Costo mensual (COP)", "98000000")], "pk": "PRIMARY KEY (periodo, sede_id, rol)"},
    "fi": {"descripcion": "Financiación y seguros por sede.", "script": ING, "columnas": [
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "NOR"),
        ("unidades", "INTEGER", "NOT NULL", "Vehículos vendidos", "58"),
        ("creditos", "INTEGER", "NOT NULL", "Créditos colocados", "27"),
        ("polizas", "INTEGER", "NOT NULL", "Pólizas colocadas", "22"),
        ("comisiones", "INTEGER", "NOT NULL", "Comisiones (COP)", "82000000")], "pk": "PRIMARY KEY (periodo, sede_id)"},
    "obligaciones": {"descripcion": "Cupos wholesale por sede y entidad.", "script": ING, "columnas": [
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("sede_id", "TEXT", f"NOT NULL {SEDE}", "Sede", "NOR"),
        ("entidad", "TEXT", "NOT NULL", "Entidad ficticia", "Banco Cordillera"),
        ("tipo", "TEXT", "NOT NULL", "Tipo de obligación", "Wholesale"),
        ("saldo", "INTEGER", "NOT NULL", "Saldo (COP)", "2100000000"),
        ("tasa_mensual", "REAL", "NOT NULL", "Tasa mensual", "0.012"),
        ("interes_mes", "INTEGER", "NOT NULL", "Interés del mes (COP)", "25200000")], "pk": "PRIMARY KEY (periodo, sede_id, entidad)"},
    "pronosticos": {"descripcion": "Proyecciones por escenario.", "script": "src/pronostico.py", "columnas": [
        ("pronostico_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador", "5"),
        ("periodo_base", "TEXT", "NOT NULL", "Último mes real usado", "2026-10"),
        ("periodo", "TEXT", "NOT NULL", "Mes proyectado", "2026-12"),
        ("concesionario_id", "TEXT", f"NOT NULL {CONC}", "Concesionario", "AND"),
        ("escenario", "TEXT", "NOT NULL", "Optimista, Base o Pesimista", "Base"),
        ("modelo", "TEXT", "NOT NULL", "Drivers o ETS", "Drivers"),
        ("metrica", "TEXT", "NOT NULL", "Variable proyectada", "ingresos"),
        ("valor", "REAL", "NOT NULL", "Valor proyectado (COP)", "15200000000")]},
    "alertas": {"descripcion": "Hallazgos del validador.", "script": "src/procesamiento.py", "columnas": [
        ("alerta_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador", "12"),
        ("periodo", "TEXT", "NOT NULL", "Mes AAAA-MM", "2026-10"),
        ("concesionario_id", "TEXT", f"NOT NULL {CONC}", "Concesionario", "AND"),
        ("sede_id", "TEXT", SEDE, "Sede, si aplica", "SUR"),
        ("regla", "TEXT", "NOT NULL", "Control que la generó", "ecuacion_contable"),
        ("severidad", "TEXT", "NOT NULL", "Alta, Media o Baja", "Alta"),
        ("hallazgo", "TEXT", "NOT NULL", "Qué se encontró", "Activo no cuadra"),
        ("explicacion", "TEXT", "NOT NULL", "Explicación en una frase", "La cuenta 2205 aparece dos veces."),
        ("impacto_cop", "INTEGER", "", "Impacto estimado (COP)", "18400000"),
        ("origen", "TEXT", "NOT NULL", "Archivo y celda", "2026-10/AND/SUR_balance.xlsx!A20")]},
    "bitacora": {"descripcion": "Registro de cada paso ejecutado.", "script": "src/*.py", "columnas": [
        ("bitacora_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador", "40"),
        ("fecha", "TEXT", "NOT NULL", "Fecha y hora", "2026-11-05T07:00:00-05:00"),
        ("periodo", "TEXT", "NOT NULL", "Mes procesado", "2026-10"),
        ("paso", "TEXT", "NOT NULL", "Paso ejecutado", "ingesta"),
        ("resultado", "TEXT", "NOT NULL", "Resultado", "Correcto"),
        ("accion", "TEXT", "NOT NULL", "Qué hizo o qué falta", "Cargó 9 archivos"),
        ("responsable", "TEXT", "NOT NULL", "Agente o persona", "Agente de procesamiento")]},
    "cargas": {"descripcion": "Una fila por archivo cargado cada mes.", "script": ING, "columnas": [
        ("carga_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT", "Identificador", "100"),
        ("periodo", "TEXT", "NOT NULL", "Mes cargado", "2026-10"),
        ("concesionario_id", "TEXT", f"NOT NULL {CONC}", "Concesionario", "AND"),
        ("archivo", "TEXT", "NOT NULL", "Archivo", "2026-10/AND/SUR_balance.xlsx"),
        ("tabla", "TEXT", "NOT NULL", "Tabla destino", "saldos"),
        ("filas", "INTEGER", "NOT NULL", "Filas agregadas", "118"),
        ("estado", "TEXT", "NOT NULL", "Correcto o Revisar", "Correcto"),
        ("modo", "TEXT", "NOT NULL", "historico_simulado o rutina", "historico_simulado"),
        ("commit_hash", "TEXT", "NOT NULL", "Versión del código que hizo la carga", "a1b2c3d")]},
}

SIN_TRAZA_EXTRA: set[str] = set()


def ddl() -> list[str]:
    sentencias = []
    for tabla, d in TABLAS.items():
        columnas = [" ".join(x for x in (n, t, r) if x) for n, t, r, _, _ in d["columnas"] + TRAZA]
        if d.get("pk"):
            columnas.append(d["pk"])
        sentencias.append(f"CREATE TABLE {tabla} (\n  " + ",\n  ".join(columnas) + "\n);")
    sentencias += [
        "CREATE INDEX idx_saldos_periodo ON saldos(periodo, sede_id);",
        "CREATE INDEX idx_ventas_periodo ON ventas(periodo, sede_id);",
        "CREATE INDEX idx_inventario_sede ON inventario(sede_id, periodo);",
        "CREATE INDEX idx_gastos_periodo ON gastos(periodo, sede_id);",
        "CREATE INDEX idx_alertas_periodo ON alertas(periodo, concesionario_id);",
    ]
    return sentencias


def diccionario_md() -> str:
    partes = ["# Diccionario de datos", "", "> Datos simulados. Cada tabla incluye `fuente` y `cargado_en` para rastrear cada fila.", ""]
    for tabla, d in TABLAS.items():
        partes += [f"## {tabla}", "", d["descripcion"], "", f"**Lo escribe:** `{d['script']}`", "",
                   "| Campo | Significado | Tipo | Ejemplo |", "|---|---|---|---|"]
        for n, t, _, sig, ej in d["columnas"] + TRAZA:
            partes.append(f"| `{n}` | {sig} | {t} | {ej} |")
        partes.append("")
    return "\n".join(partes)
