"""Herramientas que usa el agente. Todas devuelven diccionarios serializables a JSON.

Si algo falla (estacion inexistente, sin datos, etc.) se devuelve {"error": ...}
para que el agente lo reciba como observacion y pueda corregir la llamada.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

import rag
from parte1_modelo_clasico import (
    DATA_PATH,
    LIMITE_ALTO,
    LIMITE_BAJO,
    categoria_pm25,
    predecir_siguiente_anio,
)

LIMITE_COLOMBIA_ANUAL = 25.0  # Res. 2254 de 2017
GUIA_OMS_ANUAL = 5.0          # OMS 2021
NOTA_CATEGORIAS = (
    f"Categorias anuales del proyecto: baja <= {LIMITE_BAJO:g}, media <= {LIMITE_ALTO:g}, "
    f"alta > {LIMITE_ALTO:g} ug/m3 (no son las categorias del AQI diario)."
)


class ToolError(Exception):
    pass


_df: pd.DataFrame | None = None


def _datos() -> pd.DataFrame:
    global _df
    if _df is None:
        if not Path(DATA_PATH).exists():
            raise ToolError("No existe data/valle_aburra_pm25.csv. Ejecuta: python src/preparar_datos.py")
        _df = pd.read_csv(DATA_PATH)
    return _df


def _norm(texto: Any) -> str:
    n = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in n if not unicodedata.combining(c)).lower().strip()


def _resolver_estacion(estacion: Any) -> int:
    """Acepta id numerico o parte del nombre. Si hay ambiguedad, lista candidatos."""
    df = _datos()
    est = df.drop_duplicates("id_estacion")[["id_estacion", "estacion", "municipio"]]

    if str(estacion).strip().isdigit():
        i = int(str(estacion).strip())
        if i in set(est["id_estacion"]):
            return i
        raise ToolError(f"No existe la estacion con id {i}. Usa list_stations.")

    q = _norm(estacion)
    if not q:
        raise ToolError("Falta el nombre o id de la estacion.")
    coincide = est[est["estacion"].map(_norm).str.contains(q, regex=False)]
    if len(coincide) == 1:
        return int(coincide.iloc[0]["id_estacion"])
    if len(coincide) == 0:
        raise ToolError(f"No encontre ninguna estacion que coincida con '{estacion}'. Usa list_stations para ver las disponibles.")
    cand = [f"{r.id_estacion}: {r.estacion} ({r.municipio})" for r in coincide.head(8).itertuples()]
    raise ToolError(f"'{estacion}' es ambiguo; usa el id de una de estas: " + "; ".join(cand))


def _serie(id_estacion: int) -> pd.DataFrame:
    return _datos()[_datos()["id_estacion"] == id_estacion].sort_values("anio")


def _info(id_estacion: int) -> Dict[str, Any]:
    f = _serie(id_estacion).iloc[-1]
    return {"id_estacion": int(id_estacion), "estacion": f["estacion"], "municipio": f["municipio"]}


# ------------------------------------------------------------------ herramientas

def list_stations(municipio: str | None = None) -> Dict[str, Any]:
    df = _datos()
    if municipio:
        df = df[df["municipio"].map(_norm) == _norm(municipio)]
        if df.empty:
            munis = sorted(_datos()["municipio"].unique())
            raise ToolError(f"Municipio '{municipio}' no encontrado. Disponibles: {', '.join(munis)}")
    g = df.groupby(["id_estacion", "estacion", "municipio", "latitud", "longitud"]).agg(
        anio_min=("anio", "min"), anio_max=("anio", "max"), n_anios=("anio", "count")
    ).reset_index()
    # sin filtro de municipio la lista es larga (60 estaciones): se omiten las coordenadas para ahorrar tokens
    estaciones = []
    for r in g.sort_values(["municipio", "estacion"]).itertuples():
        fila = {"id_estacion": int(r.id_estacion), "estacion": r.estacion, "municipio": r.municipio,
                "anios": f"{int(r.anio_min)}-{int(r.anio_max)}"}
        if municipio:
            fila["latitud"] = round(float(r.latitud), 5)
            fila["longitud"] = round(float(r.longitud), 5)
        estaciones.append(fila)
    return {"total": len(estaciones), "estaciones": estaciones,
            "fuente": "IDEAM, Calidad del Aire en Colombia (Promedio Anual), datos.gov.co kekd-7v7h"}


def get_pm25(estacion: Any, anio: int | None = None) -> Dict[str, Any]:
    i = _resolver_estacion(estacion)
    s = _serie(i)
    if anio is not None:
        s = s[s["anio"] == int(anio)]
        if s.empty:
            anios = sorted(_serie(i)["anio"].astype(int).tolist())
            raise ToolError(f"La estacion {i} no tiene dato del anio {anio}. Anios disponibles: {anios}")
    registros = [
        {
            "anio": int(r.anio), "promedio_ug_m3": round(float(r.promedio), 2),
            "mediana": None if pd.isna(r.mediana) else round(float(r.mediana), 2),
            "percentil98": None if pd.isna(r.percentil98) else round(float(r.percentil98), 2),
            "maximo": None if pd.isna(r.maximo) else round(float(r.maximo), 2),
            "categoria_anual": categoria_pm25(float(r.promedio)),
            "supera_limite_colombia_25": bool(r.promedio > LIMITE_COLOMBIA_ANUAL),
            "supera_guia_oms_5": bool(r.promedio > GUIA_OMS_ANUAL),
        }
        for r in s.itertuples()
    ]
    return {**_info(i), "registros": registros, "nota": NOTA_CATEGORIAS,
            "fuente": "IDEAM, datos.gov.co kekd-7v7h"}


def predict_next_period(estacion: Any) -> Dict[str, Any]:
    i = _resolver_estacion(estacion)
    try:
        r = predecir_siguiente_anio(i)
    except ValueError as e:
        raise ToolError(str(e))
    r["advertencia"] = (
        "Naive Bayes entrenado con datos anuales (Macro F1 0.52 en walk-forward); en la evaluacion fue "
        "menos exacto que asumir que el anio siguiente repite la categoria actual (Macro F1 0.66). "
        "Es una estimacion, no un pronostico diario."
    )
    r["nota"] = NOTA_CATEGORIAS
    return r


def compare_stations(estacion_a: Any, estacion_b: Any, anio: int | None = None) -> Dict[str, Any]:
    a, b = _resolver_estacion(estacion_a), _resolver_estacion(estacion_b)
    if a == b:
        raise ToolError("Las dos estaciones son la misma.")
    sa, sb = _serie(a).set_index("anio"), _serie(b).set_index("anio")
    comunes = sorted(set(sa.index) & set(sb.index))
    if anio is None:
        if not comunes:
            raise ToolError("Las estaciones no tienen ningun anio en comun para comparar.")
        anio = int(comunes[-1])
    elif int(anio) not in comunes:
        raise ToolError(f"No hay dato de ambas estaciones en {anio}. Anios en comun: {[int(x) for x in comunes]}")
    pa, pb = float(sa.loc[int(anio), "promedio"]), float(sb.loc[int(anio), "promedio"])
    peor = _info(a) if pa > pb else _info(b)
    return {
        "anio": int(anio),
        "estacion_a": {**_info(a), "promedio_ug_m3": round(pa, 2), "categoria_anual": categoria_pm25(pa)},
        "estacion_b": {**_info(b), "promedio_ug_m3": round(pb, 2), "categoria_anual": categoria_pm25(pb)},
        "diferencia_ug_m3": round(abs(pa - pb), 2),
        "mayor_pm25": peor["estacion"] if pa != pb else "iguales",
        "nota": NOTA_CATEGORIAS,
    }


def exceedance_days(estacion: Any, anio: int | None = None) -> Dict[str, Any]:
    i = _resolver_estacion(estacion)
    s = _serie(i)
    if anio is not None:
        s = s[s["anio"] == int(anio)]
        if s.empty:
            raise ToolError(f"La estacion {i} no tiene dato del anio {anio}.")
    s = s.dropna(subset=["dias_excedencia"])
    if s.empty:
        raise ToolError("No hay datos de dias de excedencia para esa estacion y anio.")
    return {
        **_info(i),
        "dias_excedencia": [
            {"anio": int(r.anio), "dias": int(r.dias_excedencia), "dias_con_datos": int(r.num_datos),
             "representatividad_pct": None if pd.isna(r.representatividad) else float(r.representatividad)}
            for r in s.itertuples()
        ],
        "nota": "Dias de excedencia segun el IDEAM; el limite de 24 h de referencia puede variar entre anios. "
                "Con baja representatividad temporal la cifra subestima el total anual.",
        "fuente": "IDEAM, datos.gov.co kekd-7v7h",
    }


def trend(estacion: Any) -> Dict[str, Any]:
    i = _resolver_estacion(estacion)
    s = _serie(i)
    if len(s) < 3:
        raise ToolError(f"La estacion {i} tiene solo {len(s)} anios de datos; se necesitan al menos 3 para estimar tendencia.")
    x, y = s["anio"].to_numpy(float), s["promedio"].to_numpy(float)
    pendiente = float(np.polyfit(x, y, 1)[0])
    direccion = "estable" if abs(pendiente) < 0.2 else ("sube" if pendiente > 0 else "baja")
    return {
        **_info(i),
        "anios": f"{int(x.min())}-{int(x.max())}", "n_datos": int(len(s)),
        "pendiente_ug_m3_por_anio": round(pendiente, 3), "tendencia": direccion,
        "primer_promedio": round(float(y[0]), 2), "ultimo_promedio": round(float(y[-1]), 2),
        "nota": "Regresion lineal simple sobre pocos anios, con huecos; es orientativa.",
    }


_RECOMENDACIONES = {
    "buena": ("Buena (AQI 0-50)", "Buen dia para estar activo al aire libre."),
    "moderada": ("Moderada (AQI 51-100)",
                 "Personas inusualmente sensibles: considerar actividades al aire libre mas cortas y menos intensas y vigilar sintomas como tos o falta de aire. El resto: actividad normal."),
    "danina para grupos sensibles": ("Danina para grupos sensibles (AQI 101-150)",
                 "Grupos sensibles: actividades mas cortas y menos intensas, mas pausas y vigilar sintomas. Asma: seguir el plan de accion y tener a mano la medicacion de alivio rapido. Enfermedad cardiaca con palpitaciones, falta de aire o fatiga inusual: contactar al proveedor de salud."),
    "danina": ("Danina (AQI 151-200)",
               "Grupos sensibles: evitar actividades largas o intensas al aire libre y considerar reprogramarlas o hacerlas en interiores. Resto: reducir actividades largas o intensas y hacer mas pausas."),
    "muy danina": ("Muy danina (AQI 201-300)",
                   "Grupos sensibles: evitar toda actividad fisica al aire libre. Resto: evitar actividades largas o intensas."),
    "peligrosa": ("Peligrosa (AQI 301-500)",
                  "Todos: evitar la actividad fisica al aire libre. Grupos sensibles: permanecer en interiores con poca actividad."),
}
_ALIAS_NIVEL = {
    "good": "buena", "moderate": "moderada",
    "unhealthy for sensitive groups": "danina para grupos sensibles",
    "danina grupos sensibles": "danina para grupos sensibles", "danina a grupos sensibles": "danina para grupos sensibles",
    "sensibles": "danina para grupos sensibles", "naranja": "danina para grupos sensibles",
    "very unhealthy": "muy danina", "unhealthy": "danina", "hazardous": "peligrosa", "rojo": "danina",
    "danino": "danina", "muy danino": "muy danina",
}
_GRUPOS_SENSIBLES = ("personas con enfermedad cardiaca o pulmonar (incluidos asma y EPOC), adultos mayores, "
                     "ninos y adolescentes, mujeres embarazadas y trabajadores al aire libre")


def get_recommendation(nivel: str, grupo: str | None = None) -> Dict[str, Any]:
    k = _norm(nivel).replace("_", " ").replace("-", " ")
    if k not in _RECOMENDACIONES:
        # tolera variantes ("Dañina para grupos sensibles (101-150)", nombres en ingles, etc.)
        k = (
            next((clave for clave in sorted(_RECOMENDACIONES, key=len, reverse=True) if clave in k), None)
            or next((_ALIAS_NIVEL[a] for a in sorted(_ALIAS_NIVEL, key=len, reverse=True) if a in k), None)
        )
    if k not in _RECOMENDACIONES:
        raise ToolError("Nivel no valido. Usa uno de: " + ", ".join(_RECOMENDACIONES))
    categoria, texto = _RECOMENDACIONES[k]
    return {
        "categoria_aqi": categoria,
        "recomendacion": texto,
        "grupo_consultado": grupo,
        "grupos_sensibles": _GRUPOS_SENSIBLES,
        "fuente": "U.S. EPA / AirNow, Air Quality Guide for Particle Pollution (EPA-452/F-23-002, 2023)",
        "url": "https://document.airnow.gov/air-quality-guide-for-particle-pollution.pdf",
        "aviso": "Informacion general, no es consejo medico. Ante sintomas consulte a un profesional de salud.",
    }


def search_docs(query: str, k: int = 3) -> Dict[str, Any]:
    if not str(query).strip():
        raise ToolError("La consulta esta vacia.")
    k = max(1, min(int(k), 5))
    res = rag.buscar(query, k)
    if not res:
        return {"resultados": [], "nota": "No se encontraron fragmentos relevantes en el corpus."}
    return {"resultados": [
        {"documento": r["titulo"], "seccion": r["seccion"], "url": r["url"], "texto": _recorte(r["texto"])}
        for r in res
    ]}


def _recorte(texto: str, limite: int = 800) -> str:
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + " [...]"


# ------------------------------------------------------------------ registro para el LLM

FUNCIONES = {
    "list_stations": list_stations,
    "get_pm25": get_pm25,
    "predict_next_period": predict_next_period,
    "compare_stations": compare_stations,
    "exceedance_days": exceedance_days,
    "trend": trend,
    "get_recommendation": get_recommendation,
    "search_docs": search_docs,
}


def _spec(nombre: str, descripcion: str, props: Dict[str, Any], requeridos: list) -> Dict[str, Any]:
    return {"type": "function", "function": {
        "name": nombre, "description": descripcion,
        "parameters": {"type": "object", "properties": props, "required": requeridos}}}


_EST = {"type": "string", "description": "Nombre (o parte del nombre) o id numerico de la estacion."}
_ANIO = {"type": "integer", "description": "Año del dato (opcional)."}

TOOL_SPECS = [
    _spec("list_stations", "Lista las estaciones de calidad del aire del Valle de Aburra con municipio, coordenadas y años con datos. Usala para resolver nombres de estaciones.",
          {"municipio": {"type": "string", "description": "Filtrar por municipio (opcional)."}}, []),
    _spec("get_pm25", "Devuelve el PM2.5 promedio anual (ug/m3) de una estacion, con mediana, percentil 98, maximo y categoria anual. Sin 'anio' devuelve todos los años.",
          {"estacion": _EST, "anio": _ANIO}, ["estacion"]),
    _spec("predict_next_period", "Estima la categoria anual de PM2.5 del año siguiente para una estacion con el modelo Naive Bayes del proyecto. Es un dato anual, no un pronostico para mañana.",
          {"estacion": _EST}, ["estacion"]),
    _spec("compare_stations", "Compara el PM2.5 promedio anual de dos estaciones en un año (por defecto el ultimo año en comun).",
          {"estacion_a": _EST, "estacion_b": _EST, "anio": _ANIO}, ["estacion_a", "estacion_b"]),
    _spec("exceedance_days", "Dias de excedencia del limite reportados por el IDEAM para una estacion.",
          {"estacion": _EST, "anio": _ANIO}, ["estacion"]),
    _spec("trend", "Tendencia del PM2.5 anual de una estacion a lo largo de los años (pendiente en ug/m3 por año).",
          {"estacion": _EST}, ["estacion"]),
    _spec("get_recommendation", "Recomendaciones de salud de la EPA segun el nivel del AQI diario de PM2.5 (buena, moderada, danina para grupos sensibles, danina, muy danina, peligrosa).",
          {"nivel": {"type": "string", "enum": list(_RECOMENDACIONES), "description": "Nivel del AQI diario."},
           "grupo": {"type": "string", "description": "Grupo de la persona, p. ej. asma, ninos, adultos mayores (opcional)."}}, ["nivel"]),
    _spec("search_docs", "Busca en los documentos de referencia (normativa colombiana Res. 2254/2017, guias de la OMS, AQI y guia de salud de la EPA, episodios del Valle de Aburra). Devuelve fragmentos con su fuente y URL; citalos.",
          {"query": {"type": "string", "description": "Pregunta o palabras clave."},
           "k": {"type": "integer", "description": "Numero de fragmentos (1-5, por defecto 3)."}}, ["query"]),
]


def ejecutar_herramienta(nombre: str, argumentos: Any) -> Dict[str, Any]:
    """Ejecuta una herramienta; los errores se devuelven como {"error": ...}."""
    if nombre not in FUNCIONES:
        return {"error": f"Herramienta desconocida: {nombre}. Disponibles: {', '.join(FUNCIONES)}"}
    try:
        args = json.loads(argumentos) if isinstance(argumentos, str) and argumentos.strip() else (argumentos or {})
        if not isinstance(args, dict):
            return {"error": "Los argumentos deben ser un objeto JSON."}
        return FUNCIONES[nombre](**args)
    except ToolError as e:
        return {"error": str(e)}
    except TypeError as e:
        return {"error": f"Argumentos invalidos para {nombre}: {e}"}
    except json.JSONDecodeError:
        return {"error": "Los argumentos no son JSON valido."}
    except Exception as e:  # el agente recibe el fallo como observacion y no se cae el loop
        return {"error": f"Fallo inesperado en {nombre}: {type(e).__name__}: {e}"}
