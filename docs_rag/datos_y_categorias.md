# Datos del proyecto y categorías anuales usadas
Fuente: documentación del propio proyecto sobre el conjunto del IDEAM.
URL: https://www.datos.gov.co/d/kekd-7v7h

## Los datos
Los datos son promedios anuales de PM2.5 por estación publicados por el IDEAM en el conjunto "Calidad del Aire en Colombia (Promedio Anual)" de datos.gov.co, filtrados a 10 municipios del Valle de Aburrá (años 2011 a 2025, con huecos). Las estaciones del Valle las opera la autoridad ambiental AMVA. No hay datos diarios ni horarios en este proyecto.

## Categorías anuales del proyecto
Para clasificar un promedio anual el proyecto usa tres categorías: baja (hasta 15 µg/m³, meta intermedia 3 de la OMS), media (más de 15 y hasta 25 µg/m³) y alta (más de 25 µg/m³, por encima del límite anual de la Resolución 2254 de 2017). Son categorías propias del proyecto para promedios anuales y no equivalen a las categorías del AQI, que son para promedios de 24 horas.

## Predicción
La herramienta de predicción estima la categoría anual del año siguiente con un clasificador Naive Bayes entrenado con datos anuales. Es una estimación estadística con pocos datos (alrededor de 200 pares estación-año): no es un pronóstico diario ni una guía médica, y en la evaluación fue menos exacta que suponer que el año siguiente repite la categoría del actual.
