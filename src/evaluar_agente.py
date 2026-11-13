"""Evaluacion del agente: ejecuta un banco de 10-15 preguntas de prueba y registra que
herramienta llamo y si cito una fuente, para el entregable "Evaluacion del agente" del proyecto.

Requiere una clave de Groq valida en .env (ver .env.example). No inventa resultados: si falta la
clave o la API falla, el script lo reporta en vez de simular una respuesta.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from agente import Agente

ROOT = Path(__file__).resolve().parent.parent

# Cada caso indica la(s) herramienta(s) esperada(s) y que tipo de comportamiento se evalua.
# Los nombres de estacion son reales (ver data/valle_aburra_pm25.csv).
CASOS: List[Dict[str, Any]] = [
    {"pregunta": "¿Qué estaciones de calidad del aire hay en Itagüí?",
     "herramientas_esperadas": ["list_stations"], "tipo": "consulta_datos"},
    {"pregunta": "¿Cuál fue el PM2.5 promedio en Tráfico Centro en 2023?",
     "herramientas_esperadas": ["get_pm25"], "tipo": "consulta_datos"},
    {"pregunta": "Dame el historial completo de PM2.5 de la estación I.E. Concejo Municipal.",
     "herramientas_esperadas": ["get_pm25"], "tipo": "consulta_datos"},
    {"pregunta": "Compara el PM2.5 de Tráfico Centro y Tráfico Sur en 2021.",
     "herramientas_esperadas": ["compare_stations"], "tipo": "consulta_datos"},
    {"pregunta": "¿Cuántos días de excedencia tuvo la estación Casa Justicia en 2020?",
     "herramientas_esperadas": ["exceedance_days"], "tipo": "consulta_datos"},
    {"pregunta": "¿Cuál es la tendencia del PM2.5 en Hospital Manuel Uribe a lo largo de los años?",
     "herramientas_esperadas": ["trend"], "tipo": "consulta_datos"},
    {"pregunta": "¿Qué categoría de PM2.5 se espera para Tráfico Centro el próximo año?",
     "herramientas_esperadas": ["predict_next_period"], "tipo": "prediccion"},
    {"pregunta": "Tengo asma y el AQI de hoy está dañino para grupos sensibles, ¿qué debo hacer?",
     "herramientas_esperadas": ["get_recommendation"], "tipo": "recomendacion_salud"},
    {"pregunta": "¿Cuál es el límite anual de PM2.5 en Colombia según la Resolución 2254 de 2017?",
     "herramientas_esperadas": ["search_docs"], "tipo": "rag_normativa"},
    {"pregunta": "¿Qué medidas aplican en el nivel de alerta por contaminación según el protocolo POECA?",
     "herramientas_esperadas": ["search_docs"], "tipo": "rag_protocolo"},
    {"pregunta": "¿Cuál es la guía anual de calidad del aire de la OMS para PM2.5?",
     "herramientas_esperadas": ["search_docs"], "tipo": "rag_salud"},
    {"pregunta": "¿Cuál es el PM2.5 de la estación Altavista?",
     "herramientas_esperadas": ["get_pm25"], "tipo": "manejo_error_ambiguedad",
     "nota_evaluador": "Hay dos estaciones 'Altavista' en Medellín; se espera que el agente pida aclarar o liste candidatos, sin inventar un valor."},
    {"pregunta": "¿Cuál es el PM2.5 de la estación Marte 2030?",
     "herramientas_esperadas": ["get_pm25"], "tipo": "manejo_error_inexistente",
     "nota_evaluador": "La estación no existe; se espera que el agente lo informe (posiblemente tras usar list_stations) y no invente datos."},
    {"pregunta": "Dame el PM2.5 de I.E. Ciro Mendia en 2022 y dime qué debo hacer si la categoría es alta.",
     "herramientas_esperadas": ["get_pm25", "get_recommendation"], "tipo": "encadenamiento_multiherramienta"},
    {"pregunta": "¿Cuál es la capital de Francia?",
     "herramientas_esperadas": [], "tipo": "fuera_de_dominio",
     "nota_evaluador": "Pregunta ajena al proyecto; se espera que el agente decline sin llamar herramientas."},
]


def _cito_fuente(resultado: Dict[str, Any]) -> bool:
    """Solo cuenta si el TEXTO final del agente cita la fuente (regla 3 del system prompt).

    No basta con que alguna herramienta haya devuelto una fuente/URL: el agente debe
    escribirla en su respuesta. Contar lo contrario produce falsos positivos.
    """
    return "fuente:" in resultado["respuesta"].lower()


def ejecutar(casos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agente = Agente()
    filas = []
    for i, caso in enumerate(casos, start=1):
        agente.reiniciar()
        print(f"[{i}/{len(casos)}] {caso['pregunta']}")
        r = agente.preguntar(caso["pregunta"])
        llamadas = r["herramientas"]
        esperadas = caso["herramientas_esperadas"]
        correcto = (not esperadas and not llamadas) or any(h in llamadas for h in esperadas)
        pasos_detalle = [
            {"herramienta": p["herramienta"], "argumentos": p["argumentos"], "error": p["error"]}
            for p in r["pasos"] if "herramienta" in p
        ]
        fila = {
            "num": i,
            "pregunta": caso["pregunta"],
            "tipo": caso["tipo"],
            "herramientas_esperadas": esperadas,
            "herramientas_llamadas": llamadas,
            "herramienta_correcta": correcto,
            "cito_fuente": _cito_fuente(r),
            "fuentes_disponibles_no_citadas": bool(r["fuentes"]) and "fuente:" not in r["respuesta"].lower(),
            "terminado": r["terminado"],
            "respuesta": r["respuesta"],
            "fuentes": r["fuentes"],
            "pasos": pasos_detalle,
            "nota_evaluador": caso.get("nota_evaluador", ""),
        }
        filas.append(fila)
    return filas


# tipos de caso donde legitimamente no hay nada que citar (declinar o decir "no hay datos" es lo correcto)
TIPOS_SIN_CITA_ESPERADA = {"fuera_de_dominio", "manejo_error_inexistente"}


def a_markdown(filas: List[Dict[str, Any]]) -> str:
    n = len(filas)
    n_tool_ok = sum(1 for f in filas if f["herramienta_correcta"])
    con_cita_esperada = [f for f in filas if f["tipo"] not in TIPOS_SIN_CITA_ESPERADA]
    n_cita_ok = sum(1 for f in con_cita_esperada if f["cito_fuente"])
    n_fuente_perdida = sum(1 for f in filas if f["fuentes_disponibles_no_citadas"])
    lineas = [
        "# Evaluacion del agente",
        "",
        f"Generado automaticamente por `src/evaluar_agente.py`. {n} preguntas de prueba; "
        f"{n_tool_ok}/{n} llamaron la(s) herramienta(s) esperada(s); "
        f"{n_cita_ok}/{len(con_cita_esperada)} citaron explicitamente la fuente en el texto cuando aplicaba "
        f"({n - len(con_cita_esperada)} preguntas no requerian cita, p. ej. fuera de dominio o estacion inexistente).",
    ]
    if n_fuente_perdida:
        lineas.append(
            f"\n**Atencion:** en {n_fuente_perdida} de {n} respuestas una herramienta devolvio una fuente/URL "
            "pero el texto final del agente no la cito explicitamente (incumple la regla 3 del system prompt). "
            "Revisar en el detalle de abajo."
        )
    lineas += [
        "",
        "| # | Pregunta | Tipo | Herramienta(s) esperada(s) | Herramienta(s) llamada(s) | ¿Correcta? | ¿Citó fuente en el texto? |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in filas:
        cita_txt = "N/A" if f["tipo"] in TIPOS_SIN_CITA_ESPERADA else ("Sí" if f["cito_fuente"] else "No")
        lineas.append(
            f"| {f['num']} | {f['pregunta']} | {f['tipo']} | "
            f"{', '.join(f['herramientas_esperadas']) or '(ninguna)'} | "
            f"{', '.join(f['herramientas_llamadas']) or '(ninguna)'} | "
            f"{'Sí' if f['herramienta_correcta'] else 'No'} | "
            f"{cita_txt} |"
        )
    lineas.append("")
    lineas.append("## Respuestas completas")
    for f in filas:
        lineas.append(f"\n### {f['num']}. {f['pregunta']}")
        if f["nota_evaluador"]:
            lineas.append(f"*Nota del evaluador: {f['nota_evaluador']}*\n")
        if f["fuentes_disponibles_no_citadas"]:
            lineas.append("*Atencion: hubo fuente disponible y no se cito explicitamente en el texto.*\n")
        lineas.append(f"- Herramientas llamadas: {', '.join(f['herramientas_llamadas']) or '(ninguna)'}")
        lineas.append(f"- Fuentes devueltas por las herramientas: {', '.join(f['fuentes']) or '(ninguna)'}")
        if f["pasos"]:
            lineas.append("- Pasos (herramienta, argumentos, error si lo hubo):")
            for p in f["pasos"]:
                estado = f"ERROR: {p['error']}" if p["error"] else "ok"
                lineas.append(f"  - `{p['herramienta']}({p['argumentos']})` -> {estado}")
        lineas.append(f"- Respuesta: {f['respuesta']}")
    return "\n".join(lineas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalua el agente con un banco de preguntas de prueba")
    parser.add_argument("--output-json", default=str(ROOT / "resultados" / "evaluacion_agente.json"))
    parser.add_argument("--output-md", default=str(ROOT / "docs" / "EVALUACION_AGENTE.md"))
    args = parser.parse_args()

    filas = ejecutar(CASOS)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(filas, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(a_markdown(filas), encoding="utf-8")

    print(f"\nGuardado: {out_json}")
    print(f"Guardado: {out_md}")


if __name__ == "__main__":
    main()
