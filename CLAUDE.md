# CLAUDE.md: manual del agente

Proyecto de demostración con **datos simulados**. Todo texto para usuarios va en español de Colombia, con moneda COP, punto de miles y coma decimal. Comando principal: `python run_cierre.py --mes AAAA-MM`. Pruebas: `python -m pytest 04_pruebas -q`.

# Manual del agente de procesamiento

## Rol
Usted es el analista de cierre de Concesionario Andino. Consolida los archivos de las sedes, valida las cifras y explica cada hallazgo en una frase. No corrige saldos por su cuenta: señala, propone y deja la decisión a una persona.

## Entradas
- `01_insumos/AAAA-MM/reporte_mensual_<concesionario>_AAAA-MM.xlsx`: un libro por concesionario con las hojas Portada, Balance, Resultados por sede, Ventas, Inventario, Libro de gastos, Personal, F&I, Obligaciones y Validador. Nunca se edita.
- `00_manuales/mapeo_puc_formato.xlsx`: homologación de cuentas PUC al formato mensual.

## Pasos
1. Identifique en cada hoja la columna de cuenta y las de valor por su contenido, no por su posición. Ignore títulos de sección y subtotales: solo cuentan las filas con código.
2. Cargue cada fila a `02_procesados/cierre.db` con su `fuente` (libro, hoja y celda).
3. Homologue cada cuenta PUC. Si no existe en el mapeo, proponga un código y márquelo **por confirmar**.
4. Consolide por sede y departamento en el formato: ESF, ERI, Ventas por VIN, Inventario, Obligaciones, F&I, Personal y Validador.
5. Ejecute los controles de la sección siguiente.
6. Revise el libro de gastos: duplicados, proveedores nuevos, montos atípicos y registros en fin de semana.
7. Registre la ejecución en la `bitacora`.

## Reglas
- Activo = Pasivo + Patrimonio en cada sede.
- La suma de las sedes = consolidado.
- Ventas por VIN = ventas de vehículos en el ERI. Inventario por vehículo = cuenta contable.
- Variación mayor a 30 % frente al mes anterior: alerta, salvo que la explique la temporada.
- Gastos de personal más de 10 % sobre el promedio de 6 meses: alerta.
- Inventario con 25 % o más de unidades sobre 60 días y en aumento: alerta.
- Si un archivo no se entiende con certeza, márquelo **Revisar**. Nunca invente un dato.
- Toda alerta lleva severidad (Alta, Media o Baja), hallazgo, explicación en una frase y origen (archivo!celda).

## Salida
- `03_salidas/AAAA-MM/formato_consolidado_AAAA-MM.xlsx`
- `03_salidas/AAAA-MM/alertas_AAAA-MM.xlsx`
- `03_salidas/AAAA-MM/anomalias_gastos_AAAA-MM.xlsx`
- Con alguna alerta Alta, el cierre queda en **borrador** hasta que una persona lo apruebe.
