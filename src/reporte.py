#!/usr/bin/env python3
"""Agente de reporting: una página por concesionario, audio y guion.

Uso: python src/reporte.py --mes 2026-10 [--aprobado] [--sin-audio]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pymupdf
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from comun import NOTA, PALETA, RAIZ, SALIDAS, miles_millones, millones, nombre_mes, numero, pct
from ingesta import conectar, exportar_csv, hora_carga
from motor import motor_activo, reescribir
from pronostico import TASA_ILUSTRATIVA, cargar_series

VOZ = "es-CO-SalomeNeural"
DOCS_REPORTES = RAIZ / "docs" / "data" / "reportes"


def slug(nombre: str) -> str:
    return nombre.replace(" ", "_")


def limpiar_pdf(texto: str) -> str:
    return texto.replace("≠", "distinto de").replace("&", "&amp;")


def signo(valor: float, decimales: int = 1) -> str:
    return f"{'+' if valor >= 0 else '-'}{numero(abs(valor), decimales)}"


def hechos(conn, mes: str, cid: str, nombre: str, eri: pd.DataFrame, pron: dict) -> dict:
    e = eri[(eri.cid == cid) & (eri.periodo <= mes)].sort_values("periodo").set_index("periodo")
    previo = str(pd.Period(mes) - 1)
    hoy, antes = e.loc[mes], e.loc[previo]
    viejo = pd.read_sql_query("""SELECT i.periodo, SUM(i.costo) valor FROM inventario i JOIN sedes s USING(sede_id)
                                 WHERE s.concesionario_id=? AND i.rango='>60' GROUP BY 1""", conn, params=(cid,)).set_index("periodo").valor
    lineas = pd.read_sql_query("""SELECT i.linea, SUM(CASE WHEN i.rango='>60' THEN i.costo ELSE 0 END) viejo, SUM(i.costo) total
                                  FROM inventario i JOIN sedes s USING(sede_id) WHERE s.concesionario_id=? AND i.periodo=? GROUP BY 1""", conn, params=(cid, mes))
    lineas["cuota"] = lineas.viejo / lineas.total
    critica = lineas.sort_values("cuota", ascending=False).iloc[0]
    alertas = pd.read_sql_query("SELECT severidad, hallazgo, explicacion, impacto_cop, origen FROM alertas WHERE periodo=? AND concesionario_id=? ORDER BY COALESCE(impacto_cop,0) DESC", conn, params=(mes, cid))
    p = pron["concesionarios"][cid]["escenarios"]
    margen, margen_ant = hoy.bruto / hoy.ingresos, antes.bruto / antes.ingresos
    return {
        "cid": cid, "nombre": nombre, "mes": mes, "ingresos": float(hoy.ingresos), "var_ingresos": float(hoy.ingresos / antes.ingresos - 1),
        "margen": float(margen), "var_margen_pp": float((margen - margen_ant) * 100), "utilidad": float(hoy.utilidad),
        "viejo": float(viejo[mes]), "var_viejo": float(viejo[mes] / viejo[previo] - 1), "costo_viejo": float(viejo[mes] * TASA_ILUSTRATIVA),
        "linea_critica": critica.linea, "valor_critico": float(critica.viejo), "cuota_critica": float(critica.cuota), "ahorro": float(critica.viejo * TASA_ILUSTRATIVA),
        "alertas_total": len(alertas), "altas": int((alertas.severidad == "Alta").sum()), "alertas": alertas.head(3).to_dict("records"),
        "base": p["Base"]["ingresos_anio"], "pesimista": p["Pesimista"]["ingresos_anio"], "optimista": p["Optimista"]["ingresos_anio"],
        "serie": [{"periodo": k, "ingresos": float(v.ingresos), "margen": float(v.bruto / v.ingresos)} for k, v in e.tail(4).iterrows()],
    }


def narrativa(h: dict) -> dict:
    direccion = "crecieron" if h["var_ingresos"] >= 0 else "cayeron"
    conclusion = (f"{h['nombre']} cerró {nombre_mes(h['mes'])} con ingresos de {miles_millones(h['ingresos'])}, que {direccion} {pct(abs(h['var_ingresos']))} frente al mes anterior, "
                  f"con margen bruto de {pct(h['margen'])} y {h['altas']} alertas altas por revisar.")
    recomendacion = (f"Priorizar la salida de {h['linea_critica']} con más de 60 días ({millones(h['valor_critico'], 0)}): "
                     f"cada mes evitado ahorra cerca de {millones(h['ahorro'])} en costo financiero.")
    return {"conclusion": conclusion, "recomendacion": recomendacion}


def grafico(h: dict, ruta) -> None:
    s = h["serie"]
    x = [f"{nombre_mes(f['periodo']).split(' de ')[0][:3].capitalize()} {f['periodo'][2:4]}" for f in s]
    fig, ax = plt.subplots(figsize=(6.9, 3.5))
    fig.set_facecolor(PALETA["crema"])
    ax.set_facecolor(PALETA["crema"])
    barras = ax.bar(x, [f["ingresos"] / 1e9 for f in s], color=PALETA["navy"], width=.52)
    for b, f in zip(barras, s):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * .5, numero(f["ingresos"] / 1e9, 1), ha="center", color="white", fontsize=9)
    ax.set_ylabel("Ingresos (COP miles de millones)", fontsize=7)
    ax2 = ax.twinx()
    ax2.plot(x, [f["margen"] * 100 for f in s], "-o", color=PALETA["terracota"], lw=2)
    for i, f in enumerate(s):
        ax2.annotate(pct(f["margen"]), (i, f["margen"] * 100), textcoords="offset points", xytext=(0, 6), ha="center", color=PALETA["terracota"], fontsize=8)
    # La línea de margen va por encima de las barras para que sus etiquetas se lean.
    ax.set_ylim(0, max(f["ingresos"] / 1e9 for f in s) * 1.8)
    bajo, alto = min(f["margen"] * 100 for f in s), max(f["margen"] * 100 for f in s)
    rango = max(alto - bajo, .5)
    ax2.set_ylim(bajo - rango * 3.2, alto + rango * .8)
    ax2.set_ylabel("Margen bruto (%)", fontsize=7)
    for eje in (ax, ax2):
        eje.spines["top"].set_visible(False)
        eje.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(ruta, dpi=170)
    plt.close(fig)


def crear_pdf(h: dict, n: dict, ruta, ruta_grafico, borrador: bool) -> None:
    c = canvas.Canvas(str(ruta), pagesize=A4)
    c.setTitle(f"Reporte ejecutivo {h['nombre']} {h['mes']}")
    c.setAuthor(NOTA)
    W, H = A4
    M = 40
    ancho = W - 2 * M
    c.setFillColor(HexColor(PALETA["crema"]))
    c.rect(0, 0, W, H, stroke=0, fill=1)

    def parrafo(texto, y, tam=10, color="#2A2A2A", fuente="Helvetica", interlinea=None, x=M, w=ancho):
        p = Paragraph(limpiar_pdf(texto), ParagraphStyle("p", fontName=fuente, fontSize=tam, leading=interlinea or tam * 1.32, textColor=HexColor(color), alignment=TA_LEFT))
        _, alto = p.wrap(w, 400)
        p.drawOn(c, x, y - alto)
        return y - alto

    def seccion(texto, y):
        c.setFillColor(HexColor(PALETA["teal"]))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(M, y, texto.upper())
        return y - 7

    c.setFillColor(HexColor(PALETA["navy"]))
    c.setFont("Times-Bold", 21)
    c.drawString(M, H - 52, h["nombre"])
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#5F584C"))
    c.drawString(M, H - 68, f"Reporte ejecutivo · {nombre_mes(h['mes'])} · {NOTA}")
    if borrador:
        c.setFillColor(HexColor(PALETA["terracota"]))
        c.roundRect(W - M - 142, H - 66, 142, 22, 4, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W - M - 71, H - 59, "BORRADOR · por aprobar")
    y = parrafo(n["conclusion"], H - 84, 13.5, PALETA["navy"], "Times-Bold", 17.5) - 14

    y = seccion("Indicadores clave", y)
    kpis = [("Ingresos", millones(h["ingresos"], 0),f"{signo(h['var_ingresos'] * 100)} % vs. mes anterior", "saldos · cuenta 4135"),
            ("Margen bruto", pct(h["margen"]), f"{signo(h['var_margen_pp'])} pp vs. mes anterior", "saldos · 4135 y 6135"),
            ("Inventario >60 días", millones(h["viejo"], 0), f"{signo(h['var_viejo'] * 100)} % vs. mes anterior", "inventario · rango >60")]
    caja = (ancho - 16) / 3
    for i, (t, v, d, f) in enumerate(kpis):
        x = M + i * (caja + 8)
        c.setFillColor(HexColor("#FBF8F2"))
        c.setStrokeColor(HexColor("#DCD2C0"))
        c.roundRect(x, y - 76, caja, 76, 5, stroke=1, fill=1)
        c.setFillColor(HexColor("#5F584C"))
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 9, y - 15, t)
        c.setFillColor(HexColor(PALETA["navy"]))
        c.setFont("Times-Bold", 19)
        c.drawString(x + 9, y - 38, v)
        c.setFillColor(HexColor("#2A2A2A"))
        c.setFont("Helvetica", 7.8)
        c.drawString(x + 9, y - 53, d)
        c.setFillColor(HexColor("#7A7265"))
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 9, y - 67, f"Fuente: {f}")
    y -= 96

    y = seccion(f"Alertas principales por impacto en pesos ({len(h['alertas'])} de {h['alertas_total']})", y) - 3
    if not h["alertas"]:
        y = parrafo("El validador no encontró alertas este mes.", y, 9.5) - 6
    colores = {"Alta": PALETA["terracota"], "Media": "#B98A22", "Baja": PALETA["teal"]}
    for a in h["alertas"]:
        c.setFillColor(HexColor(colores[a["severidad"]]))
        c.roundRect(M, y - 13, 40, 13, 3, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(M + 20, y - 9.5, a["severidad"])
        impacto = f" · {millones(a['impacto_cop'])}" if a["impacto_cop"] else ""
        y2 = parrafo(f"<b>{a['hallazgo']}{impacto}</b>", y, 9, x=M + 48, w=ancho - 48)
        y2 = parrafo(a["explicacion"], y2 - 1, 8.4, "#3A3A3A", x=M + 48, w=ancho - 48)
        y = parrafo(f"Origen: {a['origen']}", y2 - 1, 6.6, "#7A7265", x=M + 48, w=ancho - 48) - 6
    y -= 5

    y = seccion("Recomendación", y) - 2
    y = parrafo(n["recomendacion"], y, 10.5, PALETA["navy"], "Helvetica-Bold") - 3
    y = parrafo(f"Efecto estimado con tasa ilustrativa de {pct(TASA_ILUSTRATIVA)} mensual. Cierre proyectado del año: {miles_millones(h['pesimista'])} a {miles_millones(h['optimista'])}.", y, 8, "#5F584C") - 12

    y = seccion("Ingresos y margen bruto, últimos 4 meses", y)
    alto_g = min(y - 48, ancho * 3.5 / 6.9)
    c.drawImage(str(ruta_grafico), M, y - alto_g, width=ancho, height=alto_g, preserveAspectRatio=True, anchor="c")
    c.setFillColor(HexColor("#7A7265"))
    c.setFont("Helvetica", 6.6)
    c.drawString(M, 30, f"Trazabilidad: 02_procesados/cierre.db (saldos, inventario, alertas) · src/reporte.py · 03_salidas/{h['mes']}/")
    c.drawRightString(W - M, 30, f"{NOTA}: no corresponde a ninguna empresa real")
    c.save()


def hablar_valor(valor: float) -> str:
    if abs(valor) >= 1e9:
        return f"{numero(abs(valor) / 1e9, 1)} mil millones de pesos"
    return f"{numero(abs(valor) / 1e6, 0)} millones de pesos"


def guion_audio(h: dict) -> str:
    sube = "subieron" if h["var_ingresos"] >= 0 else "bajaron"
    margen = "mejoró" if h["var_margen_pp"] >= 0 else "se redujo"
    viejo = "aumentó" if h["var_viejo"] >= 0 else "disminuyó"
    partes = [
        f"Hola. Este es el resumen del cierre de {nombre_mes(h['mes'])} de {h['nombre']}. Todas las cifras de este audio son datos simulados, creados para una demostración.",
        f"Empecemos por lo más importante. Los ingresos del mes fueron {hablar_valor(h['ingresos'])}. Frente al mes anterior {sube} {numero(abs(h['var_ingresos']) * 100, 1)} por ciento.",
        f"El margen bruto quedó en {numero(h['margen'] * 100, 1)} por ciento, es decir, {margen} {numero(abs(h['var_margen_pp']), 1)} puntos porcentuales. En palabras sencillas: de cada cien pesos vendidos, quedaron cerca de {numero(h['margen'] * 100, 0)} pesos después de pagar el costo de lo vendido.",
        f"La utilidad operativa del mes fue de {hablar_valor(h['utilidad'])}, ya descontados los gastos de personal, los gastos variables, los gastos fijos y el costo financiero.",
        f"Ahora miremos el inventario, porque ahí está guardada buena parte del dinero. El inventario con más de sesenta días suma {hablar_valor(h['viejo'])} y {viejo} {numero(abs(h['var_viejo']) * 100, 1)} por ciento frente al mes pasado. Mantener esos vehículos cuesta cerca de {hablar_valor(h['costo_viejo'])} cada mes, con una tasa ilustrativa de uno coma dos por ciento mensual.",
        f"La línea que más preocupa es {h['linea_critica']}: el {numero(h['cuota_critica'] * 100, 0)} por ciento de su valor lleva más de sesenta días en inventario.",
    ]
    if h["alertas"]:
        partes.append(f"Pasemos a los controles. El sistema revisó los archivos de todas las sedes y dejó {h['alertas_total']} alertas, de las cuales {h['altas']} son de severidad alta. Estas son las de mayor impacto en pesos.")
        ordinales = ["La primera", "La segunda", "La tercera"]
        for o, a in zip(ordinales, h["alertas"]):
            partes.append(f"{o}: {texto_hablado(a['explicacion'])}")
        partes.append("Cada alerta indica su archivo y su celda. El sistema señala el problema, pero la decisión sigue siendo del equipo financiero.")
    else:
        partes.append("Pasemos a los controles. El sistema revisó los archivos de todas las sedes y este mes no encontró alertas. Aun así, una persona debe dar el visto bueno antes de publicar el cierre.")
    partes += [
        f"Miremos hacia adelante. Con la información hasta este mes, el escenario base proyecta ingresos de {hablar_valor(h['base'])} para todo el año. El escenario pesimista llega a {hablar_valor(h['pesimista'])} y el optimista a {hablar_valor(h['optimista'])}. Estos rangos dependen de supuestos sobre demanda, flotas y tasa de interés, así que conviene revisarlos cada mes.",
        f"La recomendación de este cierre es concreta: priorizar la salida de {h['linea_critica']} con más de sesenta días, que hoy suman {hablar_valor(h['valor_critico'])}. Cada mes que se evite ahorra cerca de {hablar_valor(h['ahorro'])} en costo financiero.",
        "Para terminar, tres pasos: revisar las alertas, confirmar las cuentas pendientes y aprobar el cierre. Gracias por escuchar.",
    ]
    return "\n\n".join(partes)


def texto_hablado(texto: str) -> str:
    import re
    t = texto.replace("≠", "distinto de").replace(" %", " por ciento")
    t = re.sub(r"\$([\d.,]+) M\b", lambda m: f"{m.group(1).removesuffix(',0')} millones de pesos", t)
    t = re.sub(r"\((\d{4})-(\d{2})-(\d{2})\)", lambda m: f"del {int(m.group(3))} de {nombre_mes(m.group(1) + '-' + m.group(2)).split(' de ')[0]}", t)
    return t.replace("ERI.06 ", "la línea de ")


async def _edge(texto: str, ruta) -> None:
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate="+4%").save(str(ruta))


def crear_audio(texto: str, ruta) -> str:
    try:
        asyncio.run(_edge(texto, ruta))
        if ruta.exists() and ruta.stat().st_size > 10000:
            return f"edge-tts ({VOZ})"
    except Exception as e:
        print(f"  edge-tts no disponible ({type(e).__name__}); se intenta gTTS")
    try:
        from gtts import gTTS
        gTTS(texto, lang="es", tld="com.co").save(str(ruta))
        return "gTTS"
    except Exception as e:
        ruta.unlink(missing_ok=True)
        print(f"  Audio no generado ({type(e).__name__}). El guion quedó en .txt")
        return "no generado"


def generar(conn, mes: str, aprobado=False, con_audio=True) -> dict:
    carpeta = SALIDAS / mes
    carpeta.mkdir(parents=True, exist_ok=True)
    DOCS_REPORTES.mkdir(parents=True, exist_ok=True)
    pron = json.loads((carpeta / "pronostico.json").read_text(encoding="utf-8"))
    _, eri = cargar_series(conn)
    salida = {"nota": NOTA, "mes": mes, "motor": motor_activo(), "aprobado": aprobado, "reportes": {}}
    for cid, nombre in conn.execute("SELECT concesionario_id, nombre FROM concesionarios ORDER BY 1").fetchall():
        h = hechos(conn, mes, cid, nombre, eri, pron)
        plantilla = narrativa(h)
        conclusion, estado = reescribir(plantilla["conclusion"])
        recomendacion, _ = reescribir(plantilla["recomendacion"])
        final = {"conclusion": conclusion, "recomendacion": recomendacion}
        s = slug(nombre)
        png_g = carpeta / "graficos" / f"reporte_{s}.png"
        png_g.parent.mkdir(exist_ok=True)
        grafico(h, png_g)
        borrador = h["altas"] > 0 and not aprobado
        pdf = carpeta / f"reporte_ejecutivo_{s}_{mes}.pdf"
        crear_pdf(h, final, pdf, png_g, borrador)
        with pymupdf.open(pdf) as d:
            paginas = len(d)
            d[0].get_pixmap(dpi=120).save(DOCS_REPORTES / f"reporte_{cid}.png")
        shutil.copy(pdf, DOCS_REPORTES / f"reporte_{cid}.pdf")
        guion = guion_audio(h)
        (carpeta / f"resumen_audio_{s}.txt").write_text(guion + "\n", encoding="utf-8")
        (carpeta / f"guion_notebooklm_{s}.md").write_text(
            f"# Guion para NotebookLM: {nombre}, {nombre_mes(mes)}\n\n> {NOTA}. Pegue este texto como fuente en NotebookLM y genere el resumen de audio.\n\n"
            "**Instrucción sugerida:** conversación breve en español de Colombia para contadores y analistas; no agregar cifras.\n\n" + guion + "\n", encoding="utf-8")
        mp3 = carpeta / f"resumen_audio_{s}.mp3"
        voz = "omitido"
        if con_audio:
            voz = crear_audio(guion, mp3)
            if mp3.exists():
                shutil.copy(mp3, DOCS_REPORTES / f"audio_{cid}.mp3")
        elif mp3.exists():
            voz = "existente"
        salida["reportes"][cid] = {"nombre": nombre, "borrador": borrador, "paginas": paginas, "hechos": h, "plantilla": plantilla, "final": final, "estado_motor": estado,
                                   "guion": guion, "parrafos": guion.split("\n\n"), "palabras": len(guion.split()), "voz": voz,
                                   "pdf": f"data/reportes/reporte_{cid}.pdf", "png": f"data/reportes/reporte_{cid}.png", "audio": f"data/reportes/audio_{cid}.mp3" if mp3.exists() else None,
                                   "bytes_audio": mp3.stat().st_size if mp3.exists() else 0}
        print(f"  {nombre}: {paginas} página(s), {len(guion.split())} palabras, voz {voz}" + (" · BORRADOR" if borrador else ""))
    texto = json.dumps(salida, ensure_ascii=False, default=float)
    (carpeta / "reportes.json").write_text(texto, encoding="utf-8")
    (RAIZ / "docs" / "data" / "reportes.json").write_text(texto, encoding="utf-8")
    ts = hora_carga(mes, "rutina")
    conn.execute("INSERT INTO bitacora (fecha,periodo,paso,resultado,accion,responsable,fuente,cargado_en) VALUES (?,?,?,?,?,?,?,?)",
                 (ts, mes, "reporte", "Borrador" if any(r["borrador"] for r in salida["reportes"].values()) else "Correcto", f"Generó {len(salida['reportes'])} reportes y sus guiones", "Agente de reporting", "src/reporte.py", ts))
    conn.commit()
    return salida


def main() -> None:
    p = argparse.ArgumentParser(description="Agente de reporting")
    p.add_argument("--mes", default="2026-10")
    p.add_argument("--aprobado", action="store_true")
    p.add_argument("--sin-audio", action="store_true")
    a = p.parse_args()
    conn = conectar()
    generar(conn, a.mes, a.aprobado, not a.sin_audio)
    exportar_csv(conn)
    conn.close()


if __name__ == "__main__":
    main()
