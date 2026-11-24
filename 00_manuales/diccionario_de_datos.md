# Diccionario de datos

> Datos simulados. Cada tabla incluye `fuente` y `cargado_en` para rastrear cada fila.

## concesionarios

Concesionarios de la red (ficticios).

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `concesionario_id` | Código del concesionario | TEXT | AND |
| `nombre` | Nombre del concesionario | TEXT | Concesionario Andino |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## sedes

Sedes de cada concesionario.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `sede_id` | Código de la sede | TEXT | NOR |
| `concesionario_id` | Concesionario al que pertenece | TEXT | AND |
| `nombre` | Nombre de la sede | TEXT | Norte |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## cuentas

Homologación de cuentas PUC al formato mensual.

**Lo escribe:** `src/crear_mapeo.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `cuenta_codigo` | Cuenta PUC | TEXT | 2205 |
| `nombre` | Nombre de la cuenta | TEXT | Proveedores |
| `seccion` | Estado financiero: ESF o ERI | TEXT | ESF |
| `grupo` | Grupo dentro del estado | TEXT | Pasivo |
| `codigo_formato` | Código de la línea en el formato | TEXT | ESF.2.02 |
| `linea_formato` | Línea del formato | TEXT | Proveedores |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## saldos

Saldo por mes, sede, cuenta y departamento.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `saldo_id` | Identificador de la fila | INTEGER | 1024 |
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `sede_id` | Sede | TEXT | SUR |
| `cuenta_origen` | Cuenta tal como llegó en el archivo | TEXT | 4135-LIV |
| `cuenta_codigo` | Cuenta homologada; vacía si no está en el mapeo | TEXT | 4135 |
| `departamento` | Departamento del ERI; vacío en el ESF | TEXT | LIV |
| `saldo` | Valor en pesos (COP) | INTEGER | 18400000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## ventas

Una fila por vehículo vendido.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `venta_id` | Identificador de la venta | INTEGER | 311 |
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `vin` | Identificador del vehículo (simulado) | TEXT | SIMA4K2P9XT7LM3QR |
| `fecha` | Fecha de la venta | TEXT | 2026-10-15 |
| `sede_id` | Sede | TEXT | NOR |
| `canal` | Retail, Flotas, Plan de ahorro o Eléctricos | TEXT | Retail |
| `linea` | Línea del vehículo | TEXT | Livianos |
| `modelo` | Modelo ficticio | TEXT | Páramo SUV |
| `precio` | Precio de lista (COP) | INTEGER | 76000000 |
| `descuento` | Descuento (COP) | INTEGER | 2100000 |
| `costo` | Costo (COP) | INTEGER | 66500000 |
| `margen` | Margen (COP) | INTEGER | 7400000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## inventario

Una fila por vehículo en inventario al cierre.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `vin` | Identificador del vehículo | TEXT | SIMB7Q2R8KD4NW6TJ |
| `sede_id` | Sede | TEXT | CEN |
| `linea` | Línea del vehículo | TEXT | Usados |
| `modelo` | Modelo ficticio | TEXT | Usado SUV |
| `dias` | Días en inventario | INTEGER | 74 |
| `rango` | 0-30, 31-60 o >60 | TEXT | >60 |
| `costo` | Costo (COP) | INTEGER | 118000000 |
| `fecha_ingreso` | Fecha de ingreso | TEXT | 2026-08-18 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## gastos

Libro de gastos: una fila por pago.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `gasto_id` | Identificador del pago | INTEGER | 87 |
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `fecha` | Fecha del pago | TEXT | 2026-10-18 |
| `sede_id` | Sede | TEXT | CEN |
| `cuenta_origen` | Cuenta del gasto | TEXT | 5135 |
| `proveedor` | Proveedor ficticio | TEXT | Conecta Datos |
| `concepto` | Concepto | TEXT | Internet y software |
| `valor` | Valor (COP) | INTEGER | 4850000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## personal

Personas y costo por sede y rol.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `sede_id` | Sede | TEXT | NOR |
| `rol` | Rol | TEXT | Vendedores |
| `personas` | Número de personas | INTEGER | 12 |
| `costo` | Costo mensual (COP) | INTEGER | 98000000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## fi

Financiación y seguros por sede.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `sede_id` | Sede | TEXT | NOR |
| `unidades` | Vehículos vendidos | INTEGER | 58 |
| `creditos` | Créditos colocados | INTEGER | 27 |
| `polizas` | Pólizas colocadas | INTEGER | 22 |
| `comisiones` | Comisiones (COP) | INTEGER | 82000000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## obligaciones

Cupos wholesale por sede y entidad.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `sede_id` | Sede | TEXT | NOR |
| `entidad` | Entidad ficticia | TEXT | Banco Cordillera |
| `tipo` | Tipo de obligación | TEXT | Wholesale |
| `saldo` | Saldo (COP) | INTEGER | 2100000000 |
| `tasa_mensual` | Tasa mensual | REAL | 0.012 |
| `interes_mes` | Interés del mes (COP) | INTEGER | 25200000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## pronosticos

Proyecciones por escenario.

**Lo escribe:** `src/pronostico.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `pronostico_id` | Identificador | INTEGER | 5 |
| `periodo_base` | Último mes real usado | TEXT | 2026-10 |
| `periodo` | Mes proyectado | TEXT | 2026-12 |
| `concesionario_id` | Concesionario | TEXT | AND |
| `escenario` | Optimista, Base o Pesimista | TEXT | Base |
| `modelo` | Drivers o ETS | TEXT | Drivers |
| `metrica` | Variable proyectada | TEXT | ingresos |
| `valor` | Valor proyectado (COP) | REAL | 15200000000 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## alertas

Hallazgos del validador.

**Lo escribe:** `src/procesamiento.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `alerta_id` | Identificador | INTEGER | 12 |
| `periodo` | Mes AAAA-MM | TEXT | 2026-10 |
| `concesionario_id` | Concesionario | TEXT | AND |
| `sede_id` | Sede, si aplica | TEXT | SUR |
| `regla` | Control que la generó | TEXT | ecuacion_contable |
| `severidad` | Alta, Media o Baja | TEXT | Alta |
| `hallazgo` | Qué se encontró | TEXT | Activo no cuadra |
| `explicacion` | Explicación en una frase | TEXT | La cuenta 2205 aparece dos veces. |
| `impacto_cop` | Impacto estimado (COP) | INTEGER | 18400000 |
| `origen` | Archivo, hoja y celda | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## bitacora

Registro de cada paso ejecutado.

**Lo escribe:** `src/*.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `bitacora_id` | Identificador | INTEGER | 40 |
| `fecha` | Fecha y hora | TEXT | 2026-11-05T07:00:00-05:00 |
| `periodo` | Mes procesado | TEXT | 2026-10 |
| `paso` | Paso ejecutado | TEXT | ingesta |
| `resultado` | Resultado | TEXT | Correcto |
| `accion` | Qué hizo o qué falta | TEXT | Cargó 9 archivos |
| `responsable` | Agente o persona | TEXT | Agente de procesamiento |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |

## cargas

Una fila por hoja cargada cada mes.

**Lo escribe:** `src/ingesta.py`

| Campo | Significado | Tipo | Ejemplo |
|---|---|---|---|
| `carga_id` | Identificador | INTEGER | 100 |
| `periodo` | Mes cargado | TEXT | 2026-10 |
| `concesionario_id` | Concesionario | TEXT | AND |
| `archivo` | Libro y hoja | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance |
| `tabla` | Tabla destino | TEXT | saldos |
| `filas` | Filas agregadas | INTEGER | 118 |
| `estado` | Correcto o Revisar | TEXT | Correcto |
| `modo` | historico_simulado o rutina | TEXT | historico_simulado |
| `commit_hash` | Versión del código que hizo la carga | TEXT | a1b2c3d |
| `fuente` | De dónde salió la fila (archivo!hoja!celda o script) | TEXT | 2026-10/reporte_mensual_AND_2026-10.xlsx!Balance!E23 |
| `cargado_en` | Fecha y hora de carga | TEXT | 2026-11-05T07:00:00-05:00 |
