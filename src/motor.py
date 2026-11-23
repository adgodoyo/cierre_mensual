"""Motor de lenguaje intercambiable. Se elige con la variable de entorno MOTOR.

  ninguno    (predeterminado) usa solo plantillas; gratis y sin conexión
  ollama     modelo local y gratuito (MOTOR_MODELO, por defecto llama3.2)
  anthropic  requiere `pip install anthropic` y ANTHROPIC_API_KEY
  openai     requiere `pip install openai`, OPENAI_API_KEY y MOTOR_MODELO

Regla de seguridad: si el motor falla o cambia una cifra, se conserva la plantilla.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

INSTRUCCION = ("Eres analista financiero en Colombia. Reescribe el texto en español claro y profesional. "
               "Conserva exactamente todas las cifras, unidades, nombres y hechos. No agregues datos ni opiniones. "
               "Devuelve solo el texto reescrito.")


def motor_activo() -> str:
    return os.getenv("MOTOR", "ninguno").strip().lower() or "ninguno"


def _ollama(texto: str) -> str:
    cuerpo = json.dumps({"model": os.getenv("MOTOR_MODELO", "llama3.2"), "system": INSTRUCCION, "prompt": texto, "stream": False}).encode()
    url = os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/generate"
    pedido = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return json.load(r)["response"].strip()


def _anthropic(texto: str) -> str:
    import anthropic
    r = anthropic.Anthropic().beta.messages.create(
        model=os.getenv("MOTOR_MODELO", "claude-opus-5-5"), max_tokens=4000, system=INSTRUCCION,
        output_config={"effort": "low"}, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        messages=[{"role": "user", "content": texto}])
    if r.stop_reason != "end_turn":
        raise RuntimeError(f"Respuesta incompleta: {r.stop_reason}")
    return "".join(b.text for b in r.content if b.type == "text").strip()


def _openai(texto: str) -> str:
    import openai
    modelo = os.getenv("MOTOR_MODELO")
    if not modelo:
        raise RuntimeError("Defina MOTOR_MODELO para usar openai")
    r = openai.OpenAI().chat.completions.create(model=modelo, messages=[{"role": "system", "content": INSTRUCCION}, {"role": "user", "content": texto}])
    return r.choices[0].message.content.strip()


def cifras(texto: str) -> list[str]:
    return sorted(re.findall(r"\d+(?:[.,]\d+)*", texto))


def reescribir(texto: str) -> tuple[str, str]:
    """Devuelve (texto, estado). Nunca detiene el cierre por un problema del motor."""
    motor = motor_activo()
    if motor == "ninguno":
        return texto, "Plantilla (sin motor)"
    funciones = {"ollama": _ollama, "anthropic": _anthropic, "openai": _openai}
    if motor not in funciones:
        return texto, f"Motor desconocido: {motor}; se usó la plantilla"
    try:
        nuevo = funciones[motor](texto)
    except Exception as e:  # El cierre debe continuar aunque el motor no esté disponible.
        return texto, f"{motor} no disponible ({type(e).__name__}); se usó la plantilla"
    if not nuevo or cifras(nuevo) != cifras(texto):
        return texto, f"{motor} alteró las cifras; se conservó la plantilla"
    return nuevo, f"Reescrito con {motor}"
