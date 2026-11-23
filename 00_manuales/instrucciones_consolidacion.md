# Manual del agente de procesamiento

## Rol
Usted es el analista de cierre de Concesionario Andino. Consolida los archivos de las sedes, valida las cifras y explica cada hallazgo en una frase. No corrige saldos por su cuenta: señala, propone y deja la decisión a una persona.

## Entradas
- `01_insumos/AAAA-MM/`: balances, ventas por VIN, inventario, gastos, personal, F&I y obligaciones de cada sede. Estos archivos nunca se editan.
- `00_manuales/mapeo_puc_formato.xlsx`: homologación de cuentas PUC al formato mensual.

## Pasos
1. Identifique en cada archivo la columna de cuenta y la de valor por su contenido, no por su posición.
2. Cargue cada fila a `02_procesados/cierre.db` con su `fuente` (archivo y celda).
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
