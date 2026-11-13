"""Agente de calidad del aire: loop agentico con tool calling sobre Groq (API compatible con OpenAI)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import (APIConnectionError, APIStatusError, APITimeoutError, BadRequestError, NotFoundError,
                    OpenAI, RateLimitError)

from tools import TOOL_SPECS, ejecutar_herramienta

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

T_MAX = 6                 # maximo de vueltas modelo -> herramientas por pregunta
MAX_CHARS_OBS = 4000      # recorte de la observacion que se devuelve al modelo
REINTENTOS_API = 3
ESPERA_MAX = 30           # segundos maximos de espera ante un limite de tasa
MAX_BUSQUEDAS = 2         # search_docs maximo por pregunta (cuida los tokens por minuto de Groq)
MODELO_POR_DEFECTO = "openai/gpt-oss-120b"
# si el modelo configurado ya no existe en Groq, se usa el primero disponible de esta lista
MODELOS_ALTERNATIVOS = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
_modelo_activo: str | None = None

SYSTEM_PROMPT = """Eres un asistente de calidad del aire (PM2.5) para el Valle de Aburra, Colombia. Respondes en español, de forma breve y clara.

REGLAS
1. Para cualquier dato numerico (PM2.5 de una estacion, comparaciones, tendencia, dias de excedencia, prediccion) DEBES llamar a una herramienta. Nunca inventes cifras ni estaciones.
2. Para normas, limites, guias de la OMS, categorias del AQI, episodios de contaminacion, medidas o recomendaciones de salud, usa search_docs o get_recommendation y apoyate SOLO en lo que devuelvan: no agregues medidas, cifras ni detalles que no aparezcan en los fragmentos; si el documento no da un detalle, di que el documento no lo especifica. Con una busqueda suele bastar: no repitas search_docs con consultas casi iguales.
3. Cita siempre la fuente al final de la respuesta, en texto plano, con este formato: "Fuente: <nombre del documento> - <URL>" (para datos: "Fuente: IDEAM, datos.gov.co (kekd-7v7h)"). Usa el nombre y la URL tal como los devolvio search_docs. NUNCA uses marcas como 【...】 ni referencias numericas tipo "id" o "cursor".
4. Si no sabes el nombre exacto de una estacion, usa list_stations. Si una herramienta devuelve un error, lee el mensaje y corrige la llamada (por ejemplo usando el id de la estacion); si no se puede resolver, dilo.
5. Los datos del proyecto son PROMEDIOS ANUALES. No tienes datos diarios ni en tiempo real: no digas como esta el aire hoy ni pronostiques mañana. predict_next_period estima la categoria anual del año siguiente y es incierta (explica que es una estimacion).
6. Las categorias anuales baja/media/alta (cortes 15 y 25 ug/m3) son propias del proyecto y no son las categorias del AQI ni los colores del ICA. No afirmes rangos numericos del ICA: no los tienes.
7. Si algo no esta en las herramientas ni en los documentos, di que no lo sabes.
8. No des consejo medico: las recomendaciones de salud son informacion general de la EPA; ante sintomas, sugiere consultar a un profesional.
9. Si la pregunta no es sobre calidad del aire, responde amablemente que solo puedes ayudar con ese tema."""


def _cliente() -> OpenAI:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Falta GROQ_API_KEY. Copia .env.example a .env y pon tu clave de Groq.")
    return OpenAI(
        api_key=key,
        base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        timeout=60.0,
        max_retries=0,  # los reintentos los controla _llamar_llm
    )


def _elegir_modelo_alternativo(client: OpenAI, no_disponible: str) -> str:
    disponibles = {m.id for m in client.models.list().data}
    for m in MODELOS_ALTERNATIVOS:
        if m in disponibles and m != no_disponible:
            return m
    raise RuntimeError(f"El modelo '{no_disponible}' no existe en Groq y no hay alternativa conocida. Disponibles: {sorted(disponibles)}")


def _llamar_llm(client: OpenAI, mensajes: List[Dict[str, Any]], con_herramientas: bool = True):
    global _modelo_activo
    if _modelo_activo is None:
        _modelo_activo = os.getenv("GROQ_MODEL", "").strip() or MODELO_POR_DEFECTO
    ultimo: Exception | None = None
    for intento in range(REINTENTOS_API + 1):
        kwargs: Dict[str, Any] = dict(model=_modelo_activo, messages=mensajes, temperature=0.2)
        if con_herramientas:
            kwargs.update(tools=TOOL_SPECS, tool_choice="auto")
        try:
            return client.chat.completions.create(**kwargs)
        except NotFoundError:
            _modelo_activo = _elegir_modelo_alternativo(client, _modelo_activo)
            print(f"[aviso] modelo no disponible; usando {_modelo_activo}. Actualiza GROQ_MODEL en .env.", file=sys.stderr)
            continue
        except RateLimitError as e:
            ultimo = e
            espera = _espera_reintento(e, intento)
            time.sleep(espera)
            continue
        except (APITimeoutError, APIConnectionError) as e:
            ultimo = e
        except APIStatusError as e:
            if e.status_code < 500:
                raise
            ultimo = e
        time.sleep(2 * (intento + 1))
    raise ultimo  # type: ignore[misc]


def _espera_reintento(e: RateLimitError, intento: int) -> float:
    """Usa el encabezado retry-after de Groq si existe; si no, espera creciente."""
    try:
        ra = float(e.response.headers.get("retry-after", ""))
    except (ValueError, AttributeError, TypeError):
        ra = 4.0 * (intento + 1)
    return min(ra + 1.0, ESPERA_MAX)


def _limpiar(texto: str) -> str:
    """Quita marcas de cita propias del modelo (【...】) que no corresponden a ninguna fuente real."""
    texto = re.sub(r"\s*【[^】]*】", "", texto)
    return re.sub(r"[ 	]+([.,;:])", r"\1", texto).strip()


def _recortar(texto: str) -> str:
    if len(texto) <= MAX_CHARS_OBS:
        return texto
    return texto[:MAX_CHARS_OBS] + '... [observacion recortada]'


class Agente:
    def __init__(self) -> None:
        self.client = _cliente()
        self.historial: List[Dict[str, Any]] = []  # solo turnos usuario/asistente (texto)

    def reiniciar(self) -> None:
        self.historial = []

    def preguntar(self, pregunta: str, t_max: int = T_MAX) -> Dict[str, Any]:
        """Ejecuta el loop. Devuelve {respuesta, pasos, herramientas, fuentes, terminado}."""
        mensajes: List[Dict[str, Any]] = (
            [{"role": "system", "content": SYSTEM_PROMPT}] + self.historial
            + [{"role": "user", "content": pregunta}]
        )
        pasos: List[Dict[str, Any]] = []
        respuesta = ""
        terminado = False
        busquedas = 0
        tokens = {"prompt": 0, "completion": 0}

        for vuelta in range(t_max):
            try:
                resp = _llamar_llm(self.client, mensajes)
            except BadRequestError as e:
                # Groq a veces rechaza una llamada a herramienta mal formada; se le avisa y se reintenta una vez
                if pasos and pasos[-1].get("reintento_formato"):
                    respuesta = "No pude completar la consulta por un error del modelo. Intenta reformular la pregunta."
                    break
                mensajes.append({"role": "user", "content":
                                 "Tu llamada a la herramienta tenia un formato invalido. Vuelve a intentarlo con argumentos JSON validos."})
                pasos.append({"vuelta": vuelta + 1, "error_modelo": str(e)[:200], "reintento_formato": True})
                continue
            except Exception as e:
                respuesta = f"No pude contactar al modelo ({type(e).__name__}). Intenta de nuevo en unos segundos."
                pasos.append({"vuelta": vuelta + 1, "error_api": str(e)[:200]})
                break

            if getattr(resp, "usage", None):
                tokens["prompt"] += resp.usage.prompt_tokens or 0
                tokens["completion"] += resp.usage.completion_tokens or 0
            msg = resp.choices[0].message
            if not msg.tool_calls:
                respuesta = _limpiar(msg.content or "")
                terminado = True
                break

            mensajes.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                if tc.function.name == "search_docs" and busquedas >= MAX_BUSQUEDAS:
                    resultado = {"error": "Ya hiciste el maximo de busquedas permitido para esta pregunta. Responde con lo que obtuviste y di que falta."}
                else:
                    if tc.function.name == "search_docs":
                        busquedas += 1
                    resultado = ejecutar_herramienta(tc.function.name, tc.function.arguments)
                texto = _recortar(json.dumps(resultado, ensure_ascii=False))
                mensajes.append({"role": "tool", "tool_call_id": tc.id, "content": texto})
                pasos.append({
                    "vuelta": vuelta + 1,
                    "herramienta": tc.function.name,
                    "argumentos": tc.function.arguments,
                    "error": resultado.get("error") if isinstance(resultado, dict) else None,
                    "resultado": resultado,
                })

        if not terminado and not respuesta:
            # se agotaron las vueltas: una ultima llamada sin herramientas para que resuma lo obtenido
            try:
                mensajes.append({"role": "user", "content":
                                 "Ya no puedes llamar mas herramientas. Responde con la informacion obtenida; si falta algo, dilo."})
                resp = _llamar_llm(self.client, mensajes, con_herramientas=False)
                respuesta = _limpiar(resp.choices[0].message.content or "")
            except Exception:
                respuesta = "No alcance a completar la consulta en el maximo de pasos permitido."

        self.historial += [{"role": "user", "content": pregunta}, {"role": "assistant", "content": respuesta}]
        self.historial = self.historial[-12:]  # memoria corta: ultimos 6 intercambios

        herramientas = [p["herramienta"] for p in pasos if "herramienta" in p]
        return {
            "respuesta": respuesta,
            "pasos": pasos,
            "herramientas": herramientas,
            "fuentes": _fuentes(pasos),
            "terminado": terminado,
            "tokens": tokens,
        }


def _fuentes(pasos: List[Dict[str, Any]]) -> List[str]:
    """URLs/fuentes que devolvieron las herramientas (para mostrar o evaluar citas)."""
    vistas: List[str] = []
    for p in pasos:
        r = p.get("resultado")
        if not isinstance(r, dict):
            continue
        for item in r.get("resultados", []) if isinstance(r.get("resultados"), list) else []:
            if item.get("url") and item["url"] not in vistas:
                vistas.append(item["url"])
        if r.get("url") and r["url"] not in vistas:
            vistas.append(r["url"])
        if r.get("fuente") and "IDEAM" in str(r["fuente"]) and "IDEAM, datos.gov.co kekd-7v7h" not in vistas:
            vistas.append("IDEAM, datos.gov.co kekd-7v7h")
    return vistas


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente de calidad del aire del Valle de Aburra")
    parser.add_argument("pregunta", nargs="*", help="Pregunta; si se omite, abre un chat interactivo")
    parser.add_argument("--trazas", action="store_true", help="Muestra las herramientas llamadas")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    agente = Agente()

    def responder(q: str) -> None:
        r = agente.preguntar(q)
        if args.trazas:
            for p in r["pasos"]:
                if "herramienta" in p:
                    estado = f"ERROR: {p['error']}" if p["error"] else "ok"
                    print(f"  [herramienta] {p['herramienta']}({p['argumentos']}) -> {estado}")
        print(r["respuesta"], "\n")

    if args.pregunta:
        responder(" ".join(args.pregunta))
        return
    print("Agente de calidad del aire. Escribe tu pregunta (vacio o 'salir' para terminar).\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() == "salir":
            break
        responder(q)


if __name__ == "__main__":
    main()
