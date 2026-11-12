# Entrega Parte 1 - SI3003 IA

## 1. Objetivo de la Parte 1

Implementar una tecnica clasica de IA sobre datos reales de Colombia y compararla contra una linea base cuantitativa.

## 2. Fuente de datos real

- Portal: datos.gov.co
- Recurso: https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- Tema: calidad del aire y meteorologia (AMVA/SIATA)

## 3. Problema formulado

Clasificar la categoria de calidad de aire para PM2.5 en registros de exposicion 24h:
- buena: PM2.5 <= 12.0
- moderada: 12.0 < PM2.5 <= 35.4
- danina: PM2.5 > 35.4

## 4. Modelo clasico implementado

Se implemento **Gaussian Naive Bayes desde cero** (sin usar clasificador de libreria), usando NumPy para:
- calculo de priori por clase,
- estimacion de media y varianza por feature y clase,
- log-verosimilitud gaussiana,
- decision por maximo a posteriori.

Archivo principal:
- src/parte1_modelo_clasico.py

## 5. Linea base

- Baseline: clasificador de clase mayoritaria del conjunto de entrenamiento.

## 6. Split y evaluacion

- Split temporal por anio (`train` anios antiguos, `test` anios recientes).
- Metricas reportadas:
  - Accuracy
  - Macro F1
  - Balanced Accuracy

## 7. Resultados obtenidos

Ejecucion validada el 2026-11-12.

Resumen:
- Filas crudas: 30,665
- Muestras finales: 2,133
- Train: 1,698
- Test: 435
- Features: mediana, percentil98, maximo, minimo, num_datos, representatividad

Baseline (clase mayoritaria):
- Accuracy: 0.6046
- Macro F1: 0.2512
- Balanced Accuracy: 0.3333

Gaussian Naive Bayes (from scratch):
- Accuracy: 0.9034
- Macro F1: 0.6021
- Balanced Accuracy: 0.6140

Mejora del modelo clasico vs baseline:
- Delta Accuracy: +0.2989
- Delta Macro F1: +0.3509
- Delta Balanced Accuracy: +0.2807

Evidencia reproducible en:
- resultados/parte1_resultados.json

## 8. Reproducibilidad

Instalacion:

```bash
pip install -r requirements.txt
```

Ejecucion:

```bash
python src/parte1_modelo_clasico.py --output-json resultados/parte1_resultados.json
```

## 9. Alcance

Esta entrega cubre completamente la **Parte 1** (fundamentos clasicos).
No incluye agente LLM, RAG ni dashboard, porque corresponden a Parte 2 o integracion final.
