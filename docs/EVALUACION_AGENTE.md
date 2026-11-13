# Evaluacion del agente

Generado automaticamente por `src/evaluar_agente.py`. 15 preguntas de prueba; 15/15 llamaron la(s) herramienta(s) esperada(s); 10/13 citaron explicitamente la fuente en el texto cuando aplicaba (2 preguntas no requerian cita, p. ej. fuera de dominio o estacion inexistente). en 4 de 15 respuestas una herramienta devolvio una fuente/URL pero el texto final del agente no la cito explicitamente (incumple la regla 3 del system prompt). Revisar en el detalle de abajo.

| # | Pregunta | Tipo | Herramienta(s) esperada(s) | Herramienta(s) llamada(s) | ¿Correcta? | ¿Citó fuente en el texto? |
|---|---|---|---|---|---|---|
| 1 | ¿Qué estaciones de calidad del aire hay en Itagüí? | consulta_datos | list_stations | list_stations | Sí | Sí |
| 2 | ¿Cuál fue el PM2.5 promedio en Tráfico Centro en 2023? | consulta_datos | get_pm25 | get_pm25 | Sí | Sí |
| 3 | Dame el historial completo de PM2.5 de la estación I.E. Concejo Municipal. | consulta_datos | get_pm25 | get_pm25 | Sí | Sí |
| 4 | Compara el PM2.5 de Tráfico Centro y Tráfico Sur en 2021. | consulta_datos | compare_stations | compare_stations | Sí | Sí |
| 5 | ¿Cuántos días de excedencia tuvo la estación Casa Justicia en 2020? | consulta_datos | exceedance_days | exceedance_days | Sí | Sí |
| 6 | ¿Cuál es la tendencia del PM2.5 en Hospital Manuel Uribe a lo largo de los años? | consulta_datos | trend | trend | Sí | Sí |
| 7 | ¿Qué categoría de PM2.5 se espera para Tráfico Centro el próximo año? | prediccion | predict_next_period | predict_next_period | Sí | Sí |
| 8 | Tengo asma y el AQI de hoy está dañino para grupos sensibles, ¿qué debo hacer? | recomendacion_salud | get_recommendation | get_recommendation | Sí | Sí |
| 9 | ¿Cuál es el límite anual de PM2.5 en Colombia según la Resolución 2254 de 2017? | rag_normativa | search_docs | search_docs | Sí | No |
| 10 | ¿Qué medidas aplican en el nivel de alerta por contaminación según el protocolo POECA? | rag_protocolo | search_docs | search_docs | Sí | Sí |
| 11 | ¿Cuál es la guía anual de calidad del aire de la OMS para PM2.5? | rag_salud | search_docs | search_docs | Sí | No |
| 12 | ¿Cuál es el PM2.5 de la estación Altavista? | manejo_error_ambiguedad | get_pm25 | get_pm25, get_pm25 | Sí | Sí |
| 13 | ¿Cuál es el PM2.5 de la estación Marte 2030? | manejo_error_inexistente | get_pm25 | get_pm25, list_stations, list_stations | Sí | N/A |
| 14 | Dame el PM2.5 de I.E. Ciro Mendia en 2022 y dime qué debo hacer si la categoría es alta. | encadenamiento_multiherramienta | get_pm25, get_recommendation | get_pm25, get_recommendation | Sí | No |
| 15 | ¿Cuál es la capital de Francia? | fuera_de_dominio | (ninguna) | (ninguna) | Sí | N/A |

## Respuestas completas

### 1. ¿Qué estaciones de calidad del aire hay en Itagüí?
- Herramientas llamadas: list_stations
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `list_stations({"municipio":"Itagüí"})` -> ok
- Respuesta: En Itagüí hay 5 estaciones de calidad del aire:

1. **CASA JUSTICIA** (id 29493) – datos 2013‑2025  
2. **I.E. CONCEJO MUNICIPAL** (id 29511) – datos 2012‑2025  
3. **ITA‑COL. EL ROSARIO** (id 9021) – datos 2012‑2012  
4. **ITA‑DITAIRES** (id 9002) – datos 2011‑2012  
5. **ITA‑POGO** (id 99999) – datos 2013‑2019  

Fuente: IDEAM, Calidad del Aire en Colombia (Promedio Anual), datos.gov.co – kekd-7v7h

### 2. ¿Cuál fue el PM2.5 promedio en Tráfico Centro en 2023?
- Herramientas llamadas: get_pm25
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_pm25({"anio":2023,"estacion":"Tráfico Centro"})` -> ok
- Respuesta: El promedio anual de PM2.5 en la estación **Tráfico Centro** (Medellín) en 2023 fue **23.4 µg/m³**, correspondiente a la categoría **media** del proyecto.  

Fuente: IDEAM, datos.gov.co - kekd-7v7h

### 3. Dame el historial completo de PM2.5 de la estación I.E. Concejo Municipal.
- Herramientas llamadas: get_pm25
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_pm25({"estacion":"I.E. Concejo Municipal"})` -> ok
- Respuesta: **Historial anual de PM2.5 – Estación I.E. CONCEJO MUNICIPAL (Itagüí)**  

| Año | Promedio (µg/m³) | Mediana | Percentil 98 | Máximo | Categoría anual* |
|-----|------------------|---------|--------------|--------|-------------------|
| 2012 | 25.4 | 25.3 | 38.4 | 49.1 | alta |
| 2013 | 25.7 | 24.7 | 42.9 | 47.2 | alta |
| 2014 | 25.1 | 23.8 | 47.3 | 63.2 | alta |
| 2015 | 24.0 | 22.6 | 48.1 | 57.2 | media |
| 2016 | 25.8 | 22.6 | 75.9 | 87.5 | alta |
| 2017 | 22.1 | 21.5 | 37.7 | 64.9 | media |
| 2018 | 19.4 | 18.2 | 40.5 | 60.1 | media |
| 2020 | 20.1 | 17.3 | 51.8 | 65.8 | media |
| 2021 | 16.9 | 16.6 | 28.1 | 38.0 | media |
| 2022 | 16.2 | 15.3 | 31.6 | 37.4 | media |
| 2023 | 18.3 | 18.0 | 31.3 | 38.4 | media |
| 2024 | 16.13 | 14.58 | 35.24 | 39.75 | media |
| 2025 | 16.64 | 16.35 | 26.24 | 33.75 | media |

\*Categorías anuales del proyecto: **baja** ≤ 15 µg/m³, **media** ≤ 25 µg/m³, **alta** > 25 µg/m³ (no son las categorías del AQI diario).

Fuente: IDEAM, datos.gov.co (kekd-7v7h)

### 4. Compara el PM2.5 de Tráfico Centro y Tráfico Sur en 2021.
- Herramientas llamadas: compare_stations
- Fuentes devueltas por las herramientas: (ninguna)
- Pasos (herramienta, argumentos, error si lo hubo):
  - `compare_stations({"anio":2021,"estacion_a":"Tráfico Centro","estacion_b":"Tráfico Sur"})` -> ok
- Respuesta: En 2021 el promedio anual de PM2.5 fue:

- **Tráfico Centro (Medellín)**: 25.3 µg/m³ → categoría **alta**.  
- **Tráfico Sur (Sabaneta)**: 25.4 µg/m³ → categoría **alta**.

La diferencia entre ambas estaciones es de **0.1 µg/m³**, siendo ligeramente mayor en Tráfico Sur.  

Fuente: IDEAM, datos.gov.co.

### 5. ¿Cuántos días de excedencia tuvo la estación Casa Justicia en 2020?
- Herramientas llamadas: exceedance_days
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `exceedance_days({"anio":2020,"estacion":"Casa Justicia"})` -> ok
- Respuesta: La estación Casa Justicia registró **42 días de excedencia** en 2020.  
Fuente: IDEAM, datos.gov.co – kekd-7v7h

### 6. ¿Cuál es la tendencia del PM2.5 en Hospital Manuel Uribe a lo largo de los años?
- Herramientas llamadas: trend
- Fuentes devueltas por las herramientas: (ninguna)
- Pasos (herramienta, argumentos, error si lo hubo):
  - `trend({"estacion":"Hospital Manuel Uribe"})` -> ok
- Respuesta: La tendencia del PM2.5 en la estación **Hospital Manuel Uribe (Envigado)** es **baja**. La regresión lineal muestra una pendiente de **‑0.35 µg/m³ por año**, pasando de un promedio anual de **16.6 µg/m³** (primer año con datos) a **13.47 µg/m³** (último año con datos).  

Fuente: IDEAM, datos.gov.co (trend)

### 7. ¿Qué categoría de PM2.5 se espera para Tráfico Centro el próximo año?
- Herramientas llamadas: predict_next_period
- Fuentes devueltas por las herramientas: (ninguna)
- Pasos (herramienta, argumentos, error si lo hubo):
  - `predict_next_period({"estacion":"Tráfico Centro"})` -> ok
- Respuesta: Se estima que la categoría anual de PM2.5 para la estación **Tráfico Centro** en el próximo año será **media** (promedio anual ≤ 25 µg/m³). Esta es una estimación basada en el modelo Naive Bayes del proyecto y no constituye un pronóstico diario.  

Fuente: datos del proyecto – predicción 2026.

### 8. Tengo asma y el AQI de hoy está dañino para grupos sensibles, ¿qué debo hacer?
- Herramientas llamadas: get_recommendation
- Fuentes devueltas por las herramientas: https://document.airnow.gov/air-quality-guide-for-particle-pollution.pdf
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_recommendation({"nivel":"danina para grupos sensibles"})` -> ok
- Respuesta: Para proteger tu salud cuando el AQI está en nivel **dañino para grupos sensibles**:

- Reduce al máximo el tiempo al aire libre y evita actividades físicas intensas.  
- Si necesitas salir, hazlo en períodos cortos y toma descansos frecuentes.  
- Sigue tu plan de acción para el asma y ten a mano la medicación de alivio rápido (por ejemplo, inhalador de rescate).  
- Si notas síntomas como dificultad para respirar, sibilancias intensas o empeoramiento del asma, **consulta a un profesional de salud** de inmediato.  

*Fuente: U.S. EPA / AirNow, Air Quality Guide for Particle Pollution (EPA-452/F-23-002, 2023) - https://document.airnow.gov/air-quality-guide-for-particle-pollution.pdf*

### 9. ¿Cuál es el límite anual de PM2.5 en Colombia según la Resolución 2254 de 2017?
*Atencion: hubo fuente disponible y no se cito explicitamente en el texto.*

- Herramientas llamadas: search_docs
- Fuentes devueltas por las herramientas: https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=82634, https://www.datos.gov.co/d/kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `search_docs({"k":3,"query":"Resolución 2254 de 2017 límite anual PM2.5 Colombia"})` -> ok
- Respuesta: El límite máximo permisible de PM2.5 en Colombia, según la Resolución 2254 de 2017, es **25 µg/m³ como promedio anual**.

### 10. ¿Qué medidas aplican en el nivel de alerta por contaminación según el protocolo POECA?
- Herramientas llamadas: search_docs
- Fuentes devueltas por las herramientas: https://2024.laestrella.gov.co/uploads/entidad/control/6f9eb-plan-de-accion-poeca.pdf, https://www.colmayor.edu.co/wp-content/uploads/2023/09/resolucion-metropolitana-2356-_33fsj.pdf
- Pasos (herramienta, argumentos, error si lo hubo):
  - `search_docs({"k":5,"query":"POECA nivel de alerta medidas protocolo POECA contaminación Valle de Aburra"})` -> ok
- Respuesta: En el nivel de **alerta** el protocolo POECA amplía la restricción vehicular a los **seis dígitos de la placa** y extiende los horarios de restricción, por ejemplo de **05:00 a 10:00 y de 16:00 a 20:00** para vehículos particulares. En este nivel **no hay vías exentas**. Las mismas excepciones que en prevención se mantienen: vehículos de emergencia, exequiales, de orden público, a gas natural o eléctricos, y el transporte público colectivo.  

Fuente: Protocolo POECA: declaración de episodios y medidas por nivel (Valle de Aburrá) – https://2024.laestrella.gov.co/uploads/entidad/control/6f9eb-plan-de-accion-poeca.pdf

### 11. ¿Cuál es la guía anual de calidad del aire de la OMS para PM2.5?
*Atencion: hubo fuente disponible y no se cito explicitamente en el texto.*

- Herramientas llamadas: search_docs
- Fuentes devueltas por las herramientas: https://www.ncbi.nlm.nih.gov/books/NBK574591/table/ch3.tab24/, https://www.datos.gov.co/d/kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `search_docs({"k":3,"query":"guía anual OMS PM2.5 límite anual microgramos por metro cúbico"})` -> ok
- Respuesta: La Guía 2021 de la Organización Mundial de la Salud (OMS) establece como límite anual para PM2.5 **5 µg/m³** (promedio anual). En la versión anterior de 2005 el límite era de **10 µg/m³** al año.

### 12. ¿Cuál es el PM2.5 de la estación Altavista?
*Nota del evaluador: Hay dos estaciones 'Altavista' en Medellín; se espera que el agente pida aclarar o liste candidatos, sin inventar un valor.*

- Herramientas llamadas: get_pm25, get_pm25
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_pm25({"estacion":"Altavista"})` -> ERROR: 'Altavista' es ambiguo; usa el id de una de estas: 31371: ALTAVISTA (Medellín); 20383: ALTAVISTA (Medellín)
  - `get_pm25({"estacion":"31371"})` -> ok
- Respuesta: El promedio anual de PM2.5 registrado en la estación **ALTAVISTA (Medellín)** para el último año disponible (2025) es **19.27 µg/m³**, con categoría anual “media”.  

Fuente: IDEAM, datos.gov.co (kekd-7v7h)

### 13. ¿Cuál es el PM2.5 de la estación Marte 2030?
*Nota del evaluador: La estación no existe; se espera que el agente lo informe (posiblemente tras usar list_stations) y no invente datos.*

*Atencion: hubo fuente disponible y no se cito explicitamente en el texto.*

- Herramientas llamadas: get_pm25, list_stations, list_stations
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_pm25({"estacion":"Marte 2030"})` -> ERROR: No encontre ninguna estacion que coincida con 'Marte 2030'. Usa list_stations para ver las disponibles.
  - `list_stations({})` -> ok
  - `list_stations({"municipio":""})` -> ok
- Respuesta: No se encontró ninguna estación con el nombre **Marte 2030** en la base de datos del proyecto. Por lo tanto, no dispongo de datos de PM2.5 para esa estación.

### 14. Dame el PM2.5 de I.E. Ciro Mendia en 2022 y dime qué debo hacer si la categoría es alta.
*Atencion: hubo fuente disponible y no se cito explicitamente en el texto.*

- Herramientas llamadas: get_pm25, get_recommendation
- Fuentes devueltas por las herramientas: IDEAM, datos.gov.co kekd-7v7h, https://document.airnow.gov/air-quality-guide-for-particle-pollution.pdf
- Pasos (herramienta, argumentos, error si lo hubo):
  - `get_pm25({"anio":2022,"estacion":"I.E. Ciro Mendia"})` -> ok
  - `get_recommendation({"nivel":"danina"})` -> ok
- Respuesta: En 2022 la estación **I.E. Ciro Mendia** (Medellín) registró un promedio anual de **PM2.5 de 19.6 µg/m³**, con categoría anual **media** (el proyecto define “alta” como > 25 µg/m³).

Aunque la categoría no es alta, si en alguna estación la categoría fuera **alta**, la EPA recomienda:

- **Grupos sensibles** (personas con enfermedades cardíacas o pulmonares, asma, EPOC, adultos mayores, niños, embarazadas, trabajadores al aire libre): evitar actividades largas o intensas al aire libre y, de ser posible, realizarlas en interiores.  
- **Resto de la población**: reducir el tiempo de exposición al aire libre, hacer pausas frecuentes y buscar lugares con mejor ventilación.

Estas son recomendaciones generales; ante cualquier síntoma, consulte a un profesional de salud.

### 15. ¿Cuál es la capital de Francia?
*Nota del evaluador: Pregunta ajena al proyecto; se espera que el agente decline sin llamar herramientas.*

- Herramientas llamadas: (ninguna)
- Fuentes devueltas por las herramientas: (ninguna)
- Respuesta: Lo siento, solo puedo ayudar con preguntas relacionadas con la calidad del aire (PM2.5) en el Valle de Aburrá.