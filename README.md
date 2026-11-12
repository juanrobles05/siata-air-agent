# SIATA Air Agent - Parte 1

Implementacion de la **Parte 1 (fundamentos clasicos)** del proyecto final de IA de EAFIT, usando datos reales de calidad del aire desde:

- https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv

## Que resuelve esta parte

Se construye un modelo clasico de clasificacion para predecir la **categoria de PM2.5 del siguiente anio por estacion** (`buena`, `moderada`, `danina`) a partir de variables historicas agregadas.

Incluye lo exigido para Parte 1:

1. Datos reales de fuente abierta.
2. Modelo clasico implementado por el equipo (Gaussian Naive Bayes desde cero).
3. Comparacion contra linea base cuantitativa (clase mayoritaria).
4. Metricas: Accuracy, Macro-F1 y Balanced Accuracy.

## Requisitos

- Python 3.10+

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python src/parte1_modelo_clasico.py
```

Opcionalmente, con URL personalizada:

```bash
python src/parte1_modelo_clasico.py --url "https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv"
```

## Notas tecnicas

- Se filtran observaciones con exposicion de 24 horas para homogeneidad.
- Se transforma el dataset a formato ancho por `id_estacion` y `ano`.
- El objetivo se define como la categoria de PM2.5 del anio siguiente.
- El split es temporal (train con anios antiguos, test con anios recientes).

## Estructura

- `src/parte1_modelo_clasico.py`: pipeline completo de datos, entrenamiento y evaluacion.
- `requirements.txt`: dependencias minimas.
- `EAFIT_Proyecto_Final_IA.pdf`: enunciado original.
