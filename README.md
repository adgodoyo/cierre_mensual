# Concesionario Andino: cierre mensual con agentes de IA

> **Datos simulados.** Ninguna cifra corresponde a una empresa real.

## Qué hace, en 5 líneas

1. Recibe archivos desordenados de las sedes Norte, Centro y Sur, y de tres concesionarios más.
2. Los ordena, los consolida y revisa que cuadren.
3. Explica cada alerta en español y dice en qué archivo y celda verificarla.
4. Proyecta el cierre del año con escenarios.
5. Entrega un reporte de una página, un audio y un tablero interactivo. Una persona aprueba antes de la versión final.

## Cómo ejecutarlo en 3 pasos

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_cierre.py --mes 2026-10
```

Para ver el tablero en su computador:

```bash
python -m http.server --directory docs 8000
```

Luego abra <http://localhost:8000>.

## Mapa de carpetas

| Carpeta | Qué contiene |
|---|---|
| `00_manuales/` | Instrucciones del agente, homologación PUC y diccionario de datos |
| `01_insumos/` | Archivos crudos de cada mes. Nunca se editan |
| `02_procesados/` | Base de datos SQLite y tablas en CSV |
| `03_salidas/` | Excel, reportes, gráficos y audios de cada mes |
| `04_pruebas/` | Generador de datos simulados y pruebas automáticas |
| `src/` | El código de los tres agentes |
| `docs/` | El tablero y el guion de la demostración |
| `.github/workflows/` | La rutina automática de cada mes |

## Los tres agentes

- **Procesamiento:** consolida, valida y explica.
- **Predictivo:** proyecta el año, con escenarios y sensibilidad.
- **Reporting:** redacta el reporte, el audio y alimenta el tablero.

## Cambiar el motor de IA

El sistema funciona completo **sin IA y sin costo**. Para probar un motor, defina la variable `MOTOR`:

```bash
MOTOR=ollama python run_cierre.py --mes 2026-10      # local y gratuito
MOTOR=anthropic python run_cierre.py --mes 2026-10   # requiere cuenta y clave
MOTOR=openai MOTOR_MODELO=<modelo> python run_cierre.py --mes 2026-10
```

Si el motor falla o cambia una cifra, el sistema conserva el texto de la plantilla.

## Si no tiene esta herramienta, use esta

| Función | Aquí usamos | Alternativas |
|---|---|---|
| Asistente que construye | Claude Code | GitHub Copilot en VS Code, ChatGPT/Codex |
| Base de datos | SQLite | Tablas de Excel, Supabase (plan gratuito), SharePoint Lists |
| Rutina automática | GitHub Actions | n8n (autoalojado, gratuito), Power Automate |
| Tablero | GitHub Pages | Power BI, Claude artifacts |
| Audio | edge-tts | NotebookLM, voz de Copilot |
| Motor | Ninguno u Ollama (gratis) | Claude, ChatGPT, Copilot, Gemini |

## Supuesto que debe conocer

Los supuestos de Flotas y tasa mueven el cierre apenas unos $0,3 mil millones. Para llegar al rango de la presentación ($145 a $152 mil millones), los escenarios incluyen un **ritmo de demanda** de +9 % y -14 %. Es ilustrativo y puede cambiarlo en el simulador del tablero.
