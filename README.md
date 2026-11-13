# Agente de calidad del aire del Valle de Aburrá

Proyecto final de SI3003 Inteligencia Artificial (EAFIT, 2026-1). Un agente basado en un LLM que responde preguntas sobre PM2.5 en el Valle de Aburrá. Combina:

- **Parte 1 (IA clásica):** un Gaussian Naive Bayes implementado desde cero que estima la categoría anual de PM2.5 del año siguiente para cada estación.
- **Parte 2 (IA moderna):** un agente con loop agéntico y *tool calling* (Groq, API compatible con OpenAI) que usa 8 herramientas, entre ellas una búsqueda RAG sobre normas y guías de salud.

> Es una herramienta informativa y académica. No es consejo médico, legal ni de seguridad.

## Datos

- **Fuente:** IDEAM, *Calidad del Aire en Colombia (Promedio Anual)*, Datos Abiertos Colombia (datos.gov.co), conjunto `kekd-7v7h`: https://www.datos.gov.co/d/kekd-7v7h
- **CSV:** https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- Se usan los promedios anuales de PM2.5 (exposición de 24 h) de 10 municipios del Valle de Aburrá: 298 filas, 60 estaciones, 2011-2025, con huecos.
- Plan B sin internet: la copia cruda está en `data/calidad_aire_ideam.csv` y el subconjunto ya filtrado en `data/valle_aburra_pm25.csv`.
- No hay datos diarios ni en tiempo real.

## Estructura

```
data/                          CSV crudo (IDEAM) y subconjunto del Valle de Aburrá
docs_rag/                      corpus del RAG: documentos .md, cada uno con su fuente y URL
src/preparar_datos.py          limpia y filtra el CSV del IDEAM
src/parte1_modelo_clasico.py   Naive Bayes propio, líneas base y evaluación
src/rag.py                     recuperador BM25 sobre docs_rag/
src/tools.py                   las 8 herramientas del agente y sus esquemas
src/agente.py                  loop agéntico (LLM + tool calling)
resultados/                    métricas de la Parte 1 (JSON)
docs/ENTREGA_PARTE1.md         informe técnico de la Parte 1
DECLARACION_USO_IA.md          declaración de uso de IA generativa
```

## Instalación

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
```

## Configurar el LLM (Groq)

1. Crea una clave gratuita en https://console.groq.com/keys.
2. Copia `.env.example` a `.env` y pega la clave:

```
GROQ_API_KEY=tu_clave
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-120b
```

`.env` está en `.gitignore`; nunca lo subas al repositorio. Si el modelo de `GROQ_MODEL` deja de existir en Groq, el agente elige automáticamente otro modelo disponible y avisa por consola.

## Uso

**1. Preparar los datos** (usa la copia local de `data/`; con `--descargar` baja de nuevo el CSV):

```bash
python src/preparar_datos.py
```

**2. Entrenar y evaluar la Parte 1:**

```bash
python src/parte1_modelo_clasico.py --output-json resultados/parte1_resultados.json
```

**3. Hablar con el agente por consola:**

```bash
python src/agente.py "¿Cuál fue el PM2.5 promedio de Tráfico Centro en 2024 y supera el límite colombiano?"
python src/agente.py --trazas
```

Sin pregunta abre un chat interactivo; `--trazas` muestra las herramientas que el agente llama.

## Cómo funciona el agente

1. El usuario hace una pregunta; el modelo decide si llama herramientas.
2. `src/agente.py` ejecuta cada llamada con `ejecutar_herramienta()` y devuelve el resultado al modelo como observación.
3. El ciclo se repite hasta que el modelo responde o se alcanza `T_MAX = 6` vueltas; en ese caso se pide una respuesta final sin herramientas.
4. Los errores (estación inexistente o ambigua, argumentos inválidos, fallo de la API) vuelven al modelo como observación o como mensaje claro y no rompen el loop. Los límites de tasa de Groq se reintentan respetando `retry-after`.

| Herramienta | Qué hace |
|---|---|
| `list_stations` | Estaciones, municipios, coordenadas y años con datos |
| `get_pm25` | PM2.5 anual de una estación (promedio, mediana, p98, máximo, categoría) |
| `predict_next_period` | Categoría anual esperada del año siguiente (Naive Bayes de la Parte 1) |
| `compare_stations` | Compara dos estaciones en un año |
| `exceedance_days` | Días de excedencia reportados por el IDEAM |
| `trend` | Pendiente del PM2.5 anual a lo largo de los años |
| `get_recommendation` | Recomendaciones de salud de la EPA por nivel del AQI |
| `search_docs` | Búsqueda RAG (BM25) en el corpus, con fuente y URL |

### Corpus del RAG (`docs_rag/`)

Resolución 2254 de 2017 (Colombia), AQI de la EPA 2024, guía de salud de la EPA para partículas, guías de la OMS 2021, resolución del AMVA sobre episodios (POECA), plan de acción POECA 2019 de La Estrella, contexto del Valle de Aburrá, descripción de los datos y un FAQ del equipo. Cada documento indica su fuente y URL en las primeras líneas. Para ampliarlo basta con añadir un `.md` con ese formato y secciones `##`; el índice se construye al iniciar.

Se usa BM25 propio en lugar de embeddings para que el proyecto no dependa de descargar un modelo grande ni de GPU.

## Resultados de la Parte 1

Predicción de la categoría anual (baja ≤ 15, media ≤ 25, alta > 25 µg/m³) del año siguiente, con evaluación *walk-forward* sobre 143 predicciones:

| Modelo | Accuracy | Macro F1 |
|---|---|---|
| Clase mayoritaria | 0.636 | 0.259 |
| Persistencia (misma categoría del año actual) | 0.713 | 0.663 |
| Naive Bayes propio | 0.664 | 0.521 |

El Naive Bayes supera a la clase mayoritaria pero **no a la persistencia**. Detalle, ablación de features y limitaciones en `docs/ENTREGA_PARTE1.md`.

## Limitaciones

- Datos anuales con huecos: pocas observaciones por estación (213 pares año a año) y métricas con alta varianza.
- No hay datos diarios ni pronóstico para mañana.
- Las categorías baja/media/alta son propias del proyecto y no equivalen al AQI ni a los colores del ICA.
- Las medidas por nivel de episodio del corpus corresponden a la versión de 2019 del protocolo, modificado en 2022.
- Los modelos de lenguaje pueden equivocarse: las respuestas deben contrastarse con las fuentes citadas.
- La capa gratuita de Groq tiene límites de tokens por minuto; si se supera, el agente espera y reintenta, y la respuesta puede tardar.

## Uso de IA generativa

Ver `DECLARACION_USO_IA.md`.
