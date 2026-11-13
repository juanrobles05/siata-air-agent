# Preguntas frecuentes sobre cómo interpretar los datos del proyecto
Fuente: documento escrito por el equipo del proyecto (no es una fuente oficial). Resume cómo se leen los datos del IDEAM usados aquí; las normas y guías citadas están en los demás documentos del corpus.
URL: https://www.datos.gov.co/d/kekd-7v7h

## ¿Los datos del proyecto son diarios o anuales?
Son promedios anuales de PM2.5 por estación, del conjunto del IDEAM en datos.gov.co. No hay datos diarios ni horarios, así que el proyecto no puede decir cómo está el aire hoy ni predecir el día de mañana.

## ¿Qué significa que una estación tenga categoría anual baja, media o alta?
Es una clasificación propia del proyecto sobre el promedio anual de PM2.5: baja hasta 15 µg/m³, media entre 15 y 25 µg/m³ y alta por encima de 25 µg/m³. El valor de 25 es el límite anual de la norma colombiana y el de 15 es una meta intermedia de la OMS. No equivale a los colores del ICA ni a las categorías del AQI de la EPA, que se definen para promedios de 24 horas.

## ¿Por qué un promedio anual puede estar bajo y aun así haber días malos?
Un promedio anual mezcla días buenos y días de episodios. Una estación puede tener un promedio anual de 20 µg/m³ y aun así superar el límite diario de 37 µg/m³ durante varios días. Los días de excedencia reportados por el IDEAM sirven para ver eso.

## ¿Por qué las estaciones de tráfico suelen tener valores más altos?
Están junto a vías con mucho flujo vehicular, y los vehículos son la principal fuente de PM2.5 en el Valle. En los documentos del AMVA se espera que estaciones como Tráfico Centro y Fiscalía General tengan concentraciones más altas que las estaciones de representatividad poblacional.

## ¿Qué tan confiable es la predicción de la categoría del año siguiente?
Es una estimación estadística hecha con un clasificador Naive Bayes y pocos datos (alrededor de 200 pares estación-año). En la evaluación fue menos acertada que suponer que el año siguiente repite la categoría del actual, así que debe leerse como una referencia y no como un pronóstico.

## ¿Esto es un consejo médico?
No. El sistema entrega información general y de normas. Las recomendaciones de salud provienen de guías de la EPA; ante síntomas o dudas se debe consultar a un profesional de la salud.

## ¿Qué cobertura tienen las estaciones y los años?
Cubre estaciones de 10 municipios del Valle de Aburrá entre 2011 y 2025, con huecos: no todas las estaciones tienen todos los años, y algunas tienen representatividad temporal baja en ciertos años, lo que puede subestimar el promedio.
