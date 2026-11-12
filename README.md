# SIATA Air Agent - Entrega Parte 1

Implementacion de la **Parte 1 (fundamentos clasicos)** del proyecto final de IA de EAFIT, usando datos reales del recurso publico:

- IDEAM, *Calidad del Aire en Colombia (Promedio Anual)*, Datos Abiertos Colombia (datos.gov.co), conjunto `kekd-7v7h`: https://www.datos.gov.co/d/kekd-7v7h
- CSV: https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- Copia local de respaldo en `data/` (ver `src/preparar_datos.py`).

## Cobertura de la Parte 1

Esta entrega cumple:

1. Fuente de datos reales identificada y documentada.
2. Modelo clasico implementado por el equipo (Gaussian Naive Bayes desde cero).
3. Linea base cuantitativa (clase mayoritaria).
4. Metricas comparativas (Accuracy, Macro F1, Balanced Accuracy).
5. Evidencia reproducible en archivo JSON de resultados.

## Requisitos

- Python 3.10+

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

Comando recomendado (genera evidencia de resultados):

```bash
python src/parte1_modelo_clasico.py --output-json resultados/parte1_resultados.json
```

Opcionalmente, se puede pasar otra URL CSV:

```bash
python src/parte1_modelo_clasico.py --url "https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv" --output-json resultados/parte1_resultados.json
```

## Entregables incluidos

- `src/parte1_modelo_clasico.py`: pipeline de datos, modelo clasico y evaluacion.
- `docs/ENTREGA_PARTE1.md`: informe tecnico de la Parte 1.
- `resultados/parte1_resultados.json`: metricas, features y matrices de confusion.
- `DECLARACION_USO_IA.md`: declaracion de uso de IA generativa.
- `requirements.txt`: dependencias minimas.
- `EAFIT_Proyecto_Final_IA.pdf`: enunciado original.
