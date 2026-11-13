# Declaracion de uso de IA generativa

Este proyecto distingue dos usos distintos de IA generativa, para evitar confusiones:

1. **Herramientas de asistencia usadas por el equipo para construir el proyecto** (lo que cubre esta declaracion).
2. **El modelo de lenguaje (LLM) de Groq**, que no es una ayuda externa sino el componente central de la Parte 2: el agente con *tool calling* definido en `src/agente.py` es, en si mismo, el entregable que combina IA moderna con la Parte 1 (Naive Bayes) y el RAG. Su uso esta documentado en el README (seccion "Como funciona el agente"), no como asistencia de desarrollo.

## 1. Herramienta de asistencia de desarrollo

- GitHub Copilot (agente de codigo en VS Code; modelo Claude Sonnet 5 en las sesiones mas recientes).

Uso dado a lo largo del proyecto:
- Parte 1: redaccion inicial del pipeline de datos, del Naive Bayes desde cero, de las lineas base (mayoritaria y persistencia) y de la evaluacion walk-forward.
- Parte 2: apoyo en la redaccion del loop agentico (manejo de *tool calling*, reintentos ante limites de tasa de Groq, *fallback* de modelo), del recuperador BM25 propio (`src/rag.py`), de las 8 herramientas del agente (`src/tools.py`) y del dashboard de Streamlit (`src/app.py`).
- Redaccion y actualizacion de documentacion tecnica (README, `docs/ENTREGA_PARTE1.md`, esta declaracion).
- Revision de consistencia entre documentacion y codigo tras cada cambio relevante (por ejemplo, verificar que las metricas reportadas en el README coincidan con `resultados/parte1_resultados.json`).

## 2. Control academico aplicado por el equipo

- Revision manual de todo el codigo generado antes de incorporarlo.
- Decisiones propias sobre el modelado (eleccion de features, cortes de categoria, metricas, diseno del corpus RAG y de las reglas del `SYSTEM_PROMPT` del agente).
- Verificacion de ejecucion de extremo a extremo con datos reales de la API (`preparar_datos.py` -> `parte1_modelo_clasico.py` -> `agente.py`/`app.py`).
- El corpus de `docs_rag/` fue redactado citando fuentes oficiales (Resolucion 2254 de 2017, OMS, EPA, AMVA/POECA); su contenido fue verificado por el equipo, no solo generado.

## 3. Alcance y responsabilidad

- La implementacion final (Parte 1, agente con RAG y herramientas, y dashboard) fue validada y ejecutada por el equipo.
- La responsabilidad del contenido tecnico, de los resultados reportados y de las afirmaciones del corpus RAG recae en el equipo, conforme al pacto pedagogico del curso.
