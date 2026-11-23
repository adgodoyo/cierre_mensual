# Guion de la demostración en vivo

**Duración:** unos 26 minutos, 2 minutos por paso. **Mensaje central:** el agente hace el trabajo repetitivo; la persona conserva el criterio y la firma.

## Antes de empezar

1. Abra una terminal en `cierre_mensual` y ejecute `python -m http.server --directory docs 8000`, o use la URL de GitHub Pages.
2. Abra el tablero con conexión a internet: los gráficos y el motor SQL se cargan desde un CDN.
3. Presione **Restablecer** para volver a Concesionario Andino, octubre de 2026.
4. Deje abiertos `SUR_balance.xlsx` y `formato_consolidado_2026-10.xlsx`.

## Paso a paso

| # | Dónde | Qué hacer | Qué decir |
|---|---|---|---|
| 1 | Excel: `01_insumos/2026-10/AND/` | Abra `NOR_balance.xlsx`, `SUR_balance.xlsx` y `CEN_balance.csv` | "Tres sedes, tres formatos. ¿Les suena conocido?" |
| 2 | Tablero: **Procesamiento** | Muestre Antes y Después, con las filas 2205 resaltadas | "El agente reconoce cada columna por su contenido." |
| 3 | **El recorrido del dato** | Clic en cada etapa, con la sede Sur | "Puedo llevar cualquier cifra hasta su celda de origen." |
| 4 | **Procesamiento**: Alertas | Lea la alerta de la cuenta 2205 y su origen | "No solo dice que no cuadra: dice por qué y dónde." |
| 5 | **Patrones**: Gastos con anomalías | Pase el cursor por los puntos marcados | "Duplicado, proveedor nuevo, monto atípico y un domingo." |
| 6 | **Base de datos** | Clic en una tabla del diagrama y en "Cuentas sin mapear" | "Esta es la base real, corriendo en su navegador." |
| 7 | **Base de datos**: Cómo se actualiza | Presione Reproducir | "Veinticuatro cierres, cada uno con su huella." |
| 8 | **Pronóstico** | Presione Pesimista, luego mueva Ritmo de demanda | "El rango depende de supuestos que ustedes controlan." |
| 9 | **Pronóstico**: tornado y matriz | Señale la barra más larga | "La demanda pesa mucho más que la tasa o las flotas." |
| 10 | **Inventario** | Muestre el costo de $40,8 M y las unidades lentas | "Esto cuesta tener carros quietos, cada mes." |
| 11 | **Reportes** | Muestre el PDF y reproduzca 20 segundos de audio | "De los datos a la gerencia, en una página y en audio." |
| 12 | **La rutina** y GitHub | Muestre el historial, la Action y el Issue | "Corre solo el día 5. Si hay alerta alta, espera a una persona." |
| 13 | **Cómo funciona** y **Dónde está cada cosa** | Clic en cada capa | "Cambie el motor y el sistema sigue funcionando." |

## Pantallazos para las diapositivas

| Tema | Qué capturar |
|---|---|
| Archivos desordenados | Los tres archivos crudos abiertos |
| Formato consolidado | Hojas ESF y Validador del Excel |
| Alertas | Tabla de alertas en Procesamiento |
| Anomalías | Gráfico de gastos con puntos marcados |
| Pronóstico con deslizadores | Simulador y gráfico de escenarios |
| Matriz de sensibilidad | Mapa de calor tasa × Flotas |
| Costo del inventario | Indicadores y gráfico de Inventario |
| Reporte de una página | PDF de Concesionario Andino |
| Reproductor de audio | Audio con el texto resaltado |
| Historial de GitHub | Lista de commits por fase |
| Ejecución de GitHub Action | Una ejecución en verde |
| Issue de aprobación | "Revisión requerida: 2026-10" |
| Arquitectura | Pestaña Cómo funciona |

## Si algo falla en vivo

- **Sin internet:** use los PDF, Excel y audios de `03_salidas/2026-10/`, que no dependen de la red.
- **Pregunta sobre un dato real:** recuerde que todo es simulado y que el método se traslada a sus archivos.
- **"¿Y si la IA se equivoca?":** muestre el borrador, el origen de cada alerta y la aprobación humana.
