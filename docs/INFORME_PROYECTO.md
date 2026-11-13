# Informe del proyecto — Agente de calidad del aire del Valle de Aburrá

SI3003 Inteligencia Artificial · EAFIT · 2026-1 · Entrega: 13 de noviembre de 2026

## 1. Problema

Los ciudadanos del Valle de Aburrá no cuentan con una forma sencilla de interpretar los datos
históricos de PM2.5 de su estación más cercana, ni de saber qué dicen la normativa y las guías de
salud al respecto. El proyecto construye un agente conversacional que combina un modelo
estadístico propio con un sistema de recuperación de documentos (RAG) para responder, con datos
y fuentes verificables, preguntas sobre calidad del aire en la región.

## 2. Datos

- **Fuente:** IDEAM, *Calidad del Aire en Colombia (Promedio Anual)*, Datos Abiertos Colombia
  (datos.gov.co), conjunto `kekd-7v7h`: https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- **Alcance usado:** promedios anuales de PM2.5 (exposición de 24 h) de 60 estaciones en 10
  municipios del Valle de Aburrá, 2011-2025, con huecos (298 filas tras limpieza).
- **Plan B:** copia local versionada en `data/calidad_aire_ideam.csv` (crudo) y
  `data/valle_aburra_pm25.csv` (subconjunto filtrado), generada por `src/preparar_datos.py`. El
  proyecto corre sin conexión a internet usando estos archivos.
- **Limitación de origen:** el dataset es anual, no diario ni en tiempo real; esto condiciona todo
  el diseño posterior (no se puede responder "cómo está el aire hoy").

## 3. Parte 1 — Técnica clásica (ML propio)

**Problema formulado:** predecir la categoría de PM2.5 (`baja` ≤ 15, `media` ≤ 25, `alta` > 25 µg/m³,
promedio anual) de una estación en el año siguiente, a partir de sus indicadores del año actual.
Los cortes usan la meta intermedia 3 de la OMS (2021) y el límite anual de la Resolución 2254 de
2017.

**Modelo implementado por el equipo:** Gaussian Naive Bayes desde cero en NumPy (prior por
clase, media/varianza por feature y clase, log-verosimilitud gaussiana, decisión MAP), sin usar un
clasificador de librería. Features principales: `promedio` y `percentil98` del año t.

**Líneas base:** (1) clase mayoritaria, (2) persistencia (el año siguiente repite la categoría
actual). Persistencia es una línea base fuerte y esperable en series anuales cortas.

**Evaluación:** walk-forward por año de origen (se entrena solo con años anteriores al año
evaluado), 213 pares estación-año, 143 predicciones desde 2020.

| Modelo | Accuracy | Macro F1 | Balanced Acc. |
|---|---|---|---|
| Mayoritaria | 0.636 | 0.259 | 0.333 |
| Persistencia | 0.713 | 0.663 | 0.680 |
| Gaussian NB (propio) | 0.664 | 0.521 | 0.487 |

El modelo propio supera claramente a la línea base mayoritaria, pero no a la de persistencia; esto
se documenta y explica en `docs/ENTREGA_PARTE1.md` (ablación de features, matriz de confusión,
lectura honesta de resultados).

## 4. Parte 2 — Agente LLM con RAG y herramientas

**Modelo de lenguaje:** API de Groq (compatible con OpenAI), modelo configurable por `.env`
(por defecto `openai/gpt-oss-120b`, con *fallback* automático si no está disponible).

**Loop agéntico** (`src/agente.py`): system prompt con reglas explícitas (usar herramientas para
cualquier dato numérico, no inventar cifras, citar siempre la fuente, aclarar que los datos son
anuales). El loop ejecuta hasta `T_MAX = 6` rondas de modelo → herramienta → observación;
maneja límites de tasa de Groq (reintentos respetando `retry-after`), *fallback* de modelo si el
configurado deja de existir, y errores de herramienta (se devuelven como observación al modelo en
vez de romper el ciclo).

**Herramientas (8, superan el mínimo de 2 exigido):**

| Herramienta | Qué hace |
|---|---|
| `list_stations` | Estaciones, municipio, coordenadas y años con datos |
| `get_pm25` | PM2.5 anual de una estación (promedio, mediana, p98, máximo, categoría) |
| `predict_next_period` | Categoría esperada del año siguiente (modelo de la Parte 1) |
| `compare_stations` | Compara dos estaciones en un año |
| `exceedance_days` | Días de excedencia reportados por el IDEAM |
| `trend` | Pendiente del PM2.5 anual a lo largo de los años |
| `get_recommendation` | Recomendaciones de salud de la EPA por nivel de AQI |
| `search_docs` | Búsqueda RAG (BM25) en el corpus normativo, con fuente y URL |

**RAG** (`src/rag.py`, corpus en `docs_rag/`): recuperador BM25 implementado desde cero
(sin librerías de embeddings/FAISS, para no depender de descargar modelos grandes ni de GPU).
El corpus incluye la Resolución 2254 de 2017, el AQI y la guía de salud de la EPA, las guías de la
OMS 2021, el protocolo POECA del AMVA sobre episodios de contaminación, contexto del Valle de
Aburrá y un FAQ propio sobre cómo interpretar los datos. Cada documento se trocea por sección y
cada fragmento recuperado conserva `fuente` y `url` para que el agente las cite textualmente.

**Dashboard** (`src/app.py`, Streamlit): filtros de municipio, estación y año; cinco vistas (serie
de tiempo con bandas de categoría y límites normativos, mapa de estaciones, mapa de calor
estación-año, ranking del año, predicción con probabilidades) y un panel de chat con el agente que
puede incluir el contexto de los filtros seleccionados. El panel funciona sin clave de Groq; solo el
chat se deshabilita.

## 5. Resultados

- Parte 1: ver tabla de la sección 3 y detalle en `docs/ENTREGA_PARTE1.md` /
  `resultados/parte1_resultados.json`.
- Parte 2: evaluación cualitativa del agente (10-15 preguntas, corrección de herramienta llamada y
  citación de fuente) en `docs/EVALUACION_AGENTE.md` y `resultados/evaluacion_agente.json`
  (generados con `src/evaluar_agente.py`, requiere una clave de Groq gratuita).

## 6. Limitaciones

- Datos anuales con huecos: pocas observaciones por estación; las métricas de la Parte 1 tienen
  alta varianza y la clase "alta" está subrepresentada en el conjunto de prueba.
- No hay datos diarios ni pronóstico para "mañana"; `predict_next_period` es una estimación
  anual y, según la propia evaluación, menos precisa que suponer persistencia.
- Las categorías baja/media/alta son una definición propia del proyecto, no equivalen al AQI de la
  EPA ni a los colores del ICA colombiano.
- El corpus RAG usa BM25 (recuperación léxica); preguntas formuladas con sinónimos muy distintos
  al texto fuente pueden no recuperar el fragmento correcto.
- El LLM puede cometer errores de razonamiento pese a las reglas del *system prompt*; las
  respuestas deben contrastarse con las fuentes citadas.
- Es una herramienta informativa y académica: no sustituye consejo médico, legal ni de seguridad.

## 7. Declaración de uso de IA generativa

Ver `DECLARACION_USO_IA.md`.
