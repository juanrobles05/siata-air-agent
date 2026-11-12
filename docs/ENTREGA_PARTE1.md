# Entrega Parte 1 - SI3003 IA

## 1. Objetivo

Predecir la categoria de PM2.5 de una estacion del Valle de Aburra en el **año siguiente**,
a partir de los indicadores del año actual, con un modelo clasico implementado desde cero
y comparado contra lineas base.

## 2. Fuente de datos

- Publicado por: IDEAM (Instituto de Hidrologia, Meteorologia y Estudios Ambientales)
- Conjunto: "Calidad del Aire en Colombia (Promedio Anual)", id `kekd-7v7h`
- Portal: Datos Abiertos Colombia (datos.gov.co) - https://www.datos.gov.co/d/kekd-7v7h
- CSV: https://www.datos.gov.co/api/v3/views/kekd-7v7h/query.csv
- Copia local (plan B): `data/calidad_aire_ideam.csv`. Subconjunto del Valle de Aburra
  (PM2.5, 24 h, 10 municipios) en `data/valle_aburra_pm25.csv`, generado con
  `python src/preparar_datos.py`.
- Las estaciones del Valle de Aburra del conjunto las opera la autoridad ambiental AMVA.

Limpieza: se eliminan filas exactamente repetidas, se normalizan los nombres de municipio
(MEDELLIN / Medellin / MEDELLIN con tilde) y se quita el `*` de algunos nombres de estacion.
Resultado: 298 filas, 60 estaciones, 2011-2025.

## 3. Problema formulado

Cada ejemplo es un par (estacion, año t) con la categoria real de la misma estacion en t+1.
Solo se usan años consecutivos; si falta t+1 no hay par. Salen **213 pares de 49 estaciones**.

Categorias sobre el **promedio anual** de PM2.5 (ug/m3):

| Clase | Rango | Referencia |
|---|---|---|
| baja | <= 15 | Meta intermedia 3 de la OMS (guia 2021) |
| media | 15 - 25 | |
| alta | > 25 | Limite anual de la norma colombiana (Res. 2254 de 2017) |

Se descartaron los cortes 12 y 35.4 de la tabla AQI de la EPA porque son para promedios de 24 h:
aplicados a promedios anuales dejaban ~90 % de los datos en una sola clase. Los valores de la
norma colombiana y de la OMS deben verificarse contra el documento original antes de la entrega final.

## 4. Modelo y lineas base

- **Gaussian Naive Bayes desde cero** (NumPy): priores, media y varianza por clase y feature,
  log-verosimilitud gaussiana, decision por maximo a posteriori y `predict_proba`.
- Features del modelo principal: `promedio` y `percentil98` del año t.
- **Linea base 1, mayoritaria**: siempre la clase mas frecuente del entrenamiento.
- **Linea base 2, persistencia**: el año siguiente tendra la misma categoria que el actual.

## 5. Evaluacion

Walk-forward por año de origen: para cada año Y >= 2020 se entrena con los pares de años < Y
y se predice Y. En total 143 predicciones (44 baja, 91 media, 8 alta).

| Modelo | Accuracy | Macro F1 | Balanced Acc. |
|---|---|---|---|
| Mayoritaria | 0.636 | 0.259 | 0.333 |
| Persistencia | 0.713 | 0.663 | 0.680 |
| Gaussian NB (propio) | 0.664 | 0.521 | 0.487 |

Matriz de confusion del Naive Bayes (filas = real, columnas = predicho):

| | baja | media | alta |
|---|---|---|---|
| baja | 16 | 28 | 0 |
| media | 13 | 77 | 1 |
| alta | 0 | 6 | 2 |

Ablacion de features (mismo walk-forward):

| Features | Accuracy | Macro F1 |
|---|---|---|
| promedio | 0.671 | 0.518 |
| promedio + percentil98 (principal) | 0.664 | 0.521 |
| promedio + maximo | 0.664 | 0.521 |
| promedio + mediana | 0.622 | 0.483 |
| las 7 features | 0.524 | 0.427 |

## 6. Lectura de los resultados y limitaciones

- El Naive Bayes **supera a la linea base mayoritaria** (Macro F1 0.52 vs 0.26) pero
  **no supera a la persistencia** (0.52 vs 0.66). Con datos anuales, lo mejor que se sabe
  del proximo año es la categoria del actual.
- El Naive Bayes tiende a predecir "media": detecta pocas estaciones "baja" (recall 16/44)
  y casi no detecta "alta" (2/8). La clase "alta" tiene muy pocos ejemplos en test.
- Con las 7 features el modelo empeora: son muy correlacionadas, y Naive Bayes asume
  independencia, asi que cuenta la misma informacion varias veces.
- El conjunto principal se escogio mirando la ablacion sobre el mismo walk-forward,
  asi que su metrica es algo optimista. No se hizo mas busqueda de hiperparametros.
- Pocos datos: 213 pares, 49 estaciones, años con huecos (2018 y 2019 casi sin pares).
  Las metricas tienen alta varianza; una sola estacion puede mover un punto porcentual.
- El dataset es anual: no hay prediccion diaria. La herramienta del agente se llama
  `predict_next_period`.
- Los resultados son informativos, no un consejo medico ni de seguridad.

## 7. Uso desde el agente

```python
from parte1_modelo_clasico import predecir_siguiente_anio
predecir_siguiente_anio(29509)   # id_estacion; opcional anio=...
```

Devuelve categoria base, categoria predicha y probabilidades por clase. Entrena solo con
pares anteriores al año consultado.

## 8. Reproducibilidad

```bash
pip install -r requirements.txt
python src/preparar_datos.py
python src/parte1_modelo_clasico.py --output-json resultados/parte1_resultados.json
```

Evidencia: `resultados/parte1_resultados.json`.
