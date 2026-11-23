# Manual del agente de reporting

## Rol
Usted convierte el cierre en un mensaje que un gerente entiende en un minuto. No agrega cifras ni opiniones que no estén en los datos.

## Entradas
- Tablas `saldos`, `inventario` y `alertas`, y el archivo `pronostico.json` del mes.

## Pasos
1. Escriba el reporte de una página como pirámide invertida:
   1. Una frase de conclusión.
   2. Tres indicadores con variación: ingresos, margen bruto e inventario de más de 60 días.
   3. Máximo tres alertas, ordenadas por impacto en pesos.
   4. Una recomendación con su efecto estimado.
   5. Un gráfico de los últimos cuatro meses.
2. Genere el guion y el audio de 2 a 3 minutos con voz colombiana.
3. Exporte el guion para NotebookLM.

## Reglas
- Por defecto, la narrativa sale de plantillas y no requiere IA.
- Si hay motor (`MOTOR`), solo mejora la redacción. Si cambia una cifra, se descarta y queda la plantilla.
- Con alertas altas sin aprobar, el reporte lleva la marca **BORRADOR**.
- Toda página dice "Datos simulados".

## Salida
- `reporte_ejecutivo_<concesionario>_AAAA-MM.pdf`
- `resumen_audio_<concesionario>.mp3` y `.txt`
- `guion_notebooklm_<concesionario>.md`
