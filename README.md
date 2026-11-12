# SIATA Air Agent - Entrega Parte 1

Implementacion de la **Parte 1 (fundamentos clasicos)** del proyecto final de IA de EAFIT, usando datos reales del recurso publico:

- IDEAM, *Calidad del Aire en Colombia (Promedio Anual)*, Datos Abiertos Colombia (datos.gov.co), conjunto `kekd-7v7h`: https://www.datos.gov.co/d/kekd-7v7h
- CSV: https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- Copia local de respaldo en `data/` (ver `src/preparar_datos.py`).

## Cobertura de la Parte 1

1. Fuente de datos reales identificada y documentada.
2. Modelo clasico implementado por el equipo (Gaussian Naive Bayes desde cero).
3. Dos lineas base: clase mayoritaria y persistencia.
4. Evaluacion walk-forward con Accuracy, Macro F1, Balanced Accuracy y matriz de confusion.
5. Evidencia reproducible en archivo JSON de resultados.

## Requisitos

- Python 3.10+

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecucion

```bash
python src/preparar_datos.py
python src/parte1_modelo_clasico.py --output-json resultados/parte1_resultados.json
```

`preparar_datos.py` usa `data/calidad_aire_ideam.csv` si existe; con `--descargar` vuelve a bajarlo de datos.gov.co.

## Entregables incluidos

- `src/preparar_datos.py`: limpia y filtra el Valle de Aburra.
- `src/parte1_modelo_clasico.py`: modelo clasico, lineas base y evaluacion.
- `docs/ENTREGA_PARTE1.md`: informe tecnico de la Parte 1.
- `resultados/parte1_resultados.json`: metricas, ablacion de features y matrices de confusion.
- `DECLARACION_USO_IA.md`: declaracion de uso de IA generativa.
- `requirements.txt`: dependencias minimas.
- `EAFIT_Proyecto_Final_IA.pdf`: enunciado original.
