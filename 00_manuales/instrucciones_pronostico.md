# Manual del agente predictivo

## Rol
Usted proyecta el cierre del año y explica qué supuestos lo mueven. Un pronóstico es un rango con supuestos visibles, no una cifra exacta.

## Entradas
- Tablas `ventas`, `saldos`, `obligaciones`, `inventario` y `fi` de `02_procesados/cierre.db`, ya validadas.

## Pasos
1. Calcule por canal: **unidades × precio × margen**. Use estacionalidad del mismo mes del año anterior y la tendencia reciente.
2. Trate Flotas aparte, con promedio de 12 meses, porque llega por oleadas.
3. Compare con un modelo estadístico (Holt-Winters).
4. Calcule tres escenarios para noviembre y diciembre:
   - **Optimista:** Flotas +10 %, tasa estable, ritmo de demanda +9 %.
   - **Base:** tendencia y estacionalidad de diciembre.
   - **Pesimista:** tasa wholesale +200 bp, Flotas -15 %, ritmo de demanda -14 %.
5. Haga el backtest: con datos hasta junio, pronostique julio a septiembre y reporte el MAPE.
6. Construya la matriz de sensibilidad tasa × Flotas y el gráfico de tornado.
7. Calcule el costo del inventario de más de 60 días con la tasa ilustrativa de 1,2 % mensual.

## Reglas
- El **ritmo de demanda** es un supuesto ilustrativo, calibrado al rango de la presentación. Siempre se declara como tal.
- Los bp son anuales: +200 bp equivalen a +0,167 puntos en la tasa mensual.
- Solo use información disponible hasta el mes de corte.
- Si el MAPE del backtest supera 5 %, la prueba automática falla y no se publica.

## Salida
- Tabla `pronosticos`, `03_salidas/AAAA-MM/pronostico.json` y gráficos en `03_salidas/AAAA-MM/graficos/`.
