from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parte1_modelo_clasico import (  # noqa: E402
    DATA_PATH,
    LIMITE_ALTO,
    LIMITE_BAJO,
    categoria_pm25,
    predecir_siguiente_anio,
)

st.set_page_config(page_title="Calidad del aire - Valle de Aburrá", page_icon="🌫️", layout="wide")

COLORES = {"baja": "#2a9d8f", "media": "#e9a820", "alta": "#c1121f"}
LIMITE_COLOMBIA = 25.0
GUIA_OMS = 5.0
PREGUNTAS_EJEMPLO = [
    "¿Cuál es el límite anual de PM2.5 en Colombia y cómo se compara con la guía de la OMS?",
    "¿Qué estaciones tiene Itagüí?",
    "¿Cuáles son las medidas en nivel de alerta por contaminación?",
    "Tengo asma, ¿qué hago si el AQI está dañino para grupos sensibles?",
]


@st.cache_data
def cargar_datos() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["categoria"] = df["promedio"].map(categoria_pm25)
    return df


@st.cache_data(show_spinner=False)
def predecir(id_estacion: int) -> dict:
    return predecir_siguiente_anio(id_estacion)


def get_agente():
    """Un agente por sesion; si falta la clave de Groq devuelve None y el resto del panel sigue funcionando."""
    if "agente" not in st.session_state:
        try:
            from agente import Agente
            st.session_state.agente = Agente()
            st.session_state.agente_error = None
        except Exception as e:  # falta la clave, paquete no instalado, etc.
            st.session_state.agente = None
            st.session_state.agente_error = str(e)
    return st.session_state.agente


# ------------------------------------------------------------------ datos y filtros

try:
    datos = cargar_datos()
except FileNotFoundError:
    st.error("No se encontró data/valle_aburra_pm25.csv. Ejecuta primero: python src/preparar_datos.py")
    st.stop()

estaciones = (
    datos.sort_values("anio").groupby("id_estacion")
    .agg(estacion=("estacion", "last"), municipio=("municipio", "last"),
         latitud=("latitud", "last"), longitud=("longitud", "last"),
         anio_min=("anio", "min"), anio_max=("anio", "max"), n=("anio", "count"))
    .reset_index()
)

with st.sidebar:
    st.header("Filtros")
    municipios = ["Todos"] + sorted(estaciones["municipio"].unique())
    municipio = st.selectbox("Municipio", municipios, index=municipios.index("Medellín") if "Medellín" in municipios else 0)
    est_filtradas = estaciones if municipio == "Todos" else estaciones[estaciones["municipio"] == municipio]
    est_filtradas = est_filtradas.sort_values(["municipio", "estacion"])
    etiquetas = {int(r.id_estacion): f"{r.estacion} ({r.municipio}, {int(r.n)} años)" for r in est_filtradas.itertuples()}
    ids = list(etiquetas)
    por_defecto = ids.index(29509) if 29509 in ids else 0
    id_sel = st.selectbox("Estación", ids, index=por_defecto, format_func=lambda i: etiquetas[i])
    anios = sorted(datos["anio"].unique(), reverse=True)
    anio_sel = st.selectbox("Año del mapa", anios, index=0)
    comparar = st.checkbox("Comparar con otras estaciones del municipio", value=False)
    st.divider()
    st.caption(
        "Datos: IDEAM, *Calidad del Aire en Colombia (Promedio Anual)*, datos.gov.co (kekd-7v7h). "
        "Son promedios anuales: no hay datos diarios ni en tiempo real. "
        "Herramienta informativa; no es consejo médico."
    )

est = estaciones[estaciones["id_estacion"] == id_sel].iloc[0]
serie = datos[datos["id_estacion"] == id_sel].sort_values("anio")

st.title("Calidad del aire (PM2.5) en el Valle de Aburrá")
col_panel, col_chat = st.columns([3, 2], gap="large")

# ------------------------------------------------------------------ panel izquierdo

with col_panel:
    st.subheader(f"{est.estacion} · {est.municipio}")

    fila = serie[serie["anio"] == anio_sel]
    if fila.empty:
        st.info(f"Esta estación no tiene dato en {anio_sel}. Años disponibles: {', '.join(str(a) for a in serie['anio'])}.")
        ref = serie.iloc[-1]
    else:
        ref = fila.iloc[0]
    m1, m2, m3 = st.columns(3)
    m1.metric(f"PM2.5 promedio {int(ref.anio)}", f"{ref.promedio:.1f} µg/m³")
    m2.metric("Categoría anual", ref.categoria.capitalize())
    m3.metric("Vs. límite colombiano (25)", f"{ref.promedio - LIMITE_COLOMBIA:+.1f} µg/m³",
              help="Resolución 2254 de 2017: 25 µg/m³ como promedio anual. La guía anual de la OMS 2021 es 5 µg/m³.")

    # se usa un selector y no st.tabs: los graficos dentro de pestañas ocultas se dibujan con tamaño cero
    vista = st.radio("Vista", ["Serie de tiempo", "Mapa de estaciones", "Mapa de calor", "Ranking del año", "Predicción"], horizontal=True,
                     label_visibility="collapsed")

    if vista == "Serie de tiempo":
        fig = go.Figure()
        top = max(serie["promedio"].max(), datos["promedio"].quantile(0.99), 30) * 1.1
        fig.add_hrect(y0=0, y1=LIMITE_BAJO, fillcolor=COLORES["baja"], opacity=0.10, line_width=0)
        fig.add_hrect(y0=LIMITE_BAJO, y1=LIMITE_ALTO, fillcolor=COLORES["media"], opacity=0.12, line_width=0)
        fig.add_hrect(y0=LIMITE_ALTO, y1=top, fillcolor=COLORES["alta"], opacity=0.10, line_width=0)
        if comparar:
            otras = datos[(datos["municipio"] == est.municipio) & (datos["id_estacion"] != id_sel)]
            for _, g in otras.groupby("id_estacion"):
                g = g.sort_values("anio")
                fig.add_trace(go.Scatter(x=g["anio"], y=g["promedio"], mode="lines", name=g["estacion"].iloc[-1],
                                         line=dict(width=1), opacity=0.5, hovertemplate="%{y:.1f} µg/m³ (%{x})"))
        fig.add_trace(go.Scatter(
            x=serie["anio"], y=serie["promedio"], mode="lines+markers", name=est.estacion,
            line=dict(color="#1d3557", width=3),
            marker=dict(size=10, color=[COLORES[c] for c in serie["categoria"]], line=dict(width=1.5, color="#1d3557")),
            hovertemplate="%{y:.1f} µg/m³ (%{x})<extra></extra>"))
        fig.add_hline(y=LIMITE_COLOMBIA, line_dash="dash", line_color="#6d6875",
                      annotation_text="Límite Colombia (25)", annotation_position="top left")
        fig.add_hline(y=GUIA_OMS, line_dash="dot", line_color="#6d6875",
                      annotation_text="Guía OMS 2021 (5)", annotation_position="bottom left")
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="PM2.5 promedio anual (µg/m³)",
                          xaxis_title="Año", yaxis_range=[0, top], legend=dict(orientation="h", y=-0.2),
                          xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")
        st.caption("Fondo: categorías anuales del proyecto (baja ≤ 15, media ≤ 25, alta > 25 µg/m³). "
                   "Los huecos son años sin dato para la estación.")

        exc = serie.dropna(subset=["dias_excedencia"])
        if not exc.empty:
            fig2 = px.bar(exc, x="anio", y="dias_excedencia",
                          labels={"anio": "Año", "dias_excedencia": "Días de excedencia"},
                          title="Días de excedencia reportados por el IDEAM")
            fig2.update_traces(marker_color="#457b9d", hovertemplate="%{y} días (%{x})<extra></extra>")
            fig2.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), xaxis=dict(dtick=1))
            st.plotly_chart(fig2, width="stretch")

    elif vista == "Mapa de estaciones":
        mapa = estaciones.merge(datos[datos["anio"] == anio_sel][["id_estacion", "promedio", "categoria"]],
                                on="id_estacion", how="inner")
        if mapa.empty:
            st.info(f"No hay estaciones con dato en {anio_sel}.")
        else:
            mapa["seleccionada"] = mapa["id_estacion"] == id_sel
            mapa["tam"] = mapa["seleccionada"].map({True: 22, False: 12})
            mapa["etiqueta"] = mapa["estacion"] + " · " + mapa["municipio"]
            args = dict(lat="latitud", lon="longitud", color="categoria", size="tam", size_max=22,
                        color_discrete_map=COLORES, category_orders={"categoria": ["baja", "media", "alta"]},
                        hover_name="etiqueta", hover_data={"promedio": ":.1f", "tam": False, "latitud": False,
                                                           "longitud": False, "categoria": False},
                        center=dict(lat=float(est.latitud), lon=float(est.longitud)), zoom=11, height=460)
            try:
                fm = px.scatter_map(mapa, map_style="open-street-map", **args)
            except AttributeError:  # plotly < 5.24
                fm = px.scatter_mapbox(mapa, mapbox_style="open-street-map", **args)
            fm.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend_title_text=f"Categoría {anio_sel}")
            st.plotly_chart(fm, width="stretch")
            st.caption(f"Cada punto es una estación con dato en {anio_sel}; la seleccionada se ve más grande y el mapa se centra en ella.")

    elif vista == "Mapa de calor":
        base = datos if municipio == "Todos" else datos[datos["municipio"] == municipio]
        # con un solo municipio basta el nombre de la estacion (etiquetas cortas dejan mas espacio al grafico)
        nombre = base["estacion"].str.slice(0, 26) if municipio != "Todos" else (
            base["estacion"].str.slice(0, 18) + " · " + base["municipio"].str.slice(0, 6))
        base = base.assign(fila=nombre)
        mat = base.pivot_table(index="fila", columns="anio", values="promedio", aggfunc="mean")
        mat = mat.reindex(columns=range(int(mat.columns.min()), int(mat.columns.max()) + 1))  # los huecos quedan vacios
        orden = base.sort_values(["municipio", "estacion"])["fila"].drop_duplicates()
        mat = mat.loc[[f for f in orden if f in mat.index]]
        fh = px.imshow(mat, aspect="auto", color_continuous_scale="YlOrRd", zmin=5, zmax=45, text_auto=".0f",
                       labels=dict(x="Año", y="", color="µg/m³"))
        fh.update_traces(hovertemplate="%{y}<br>%{x}: %{z:.1f} µg/m³<extra></extra>", xgap=1, ygap=1)
        fh.update_xaxes(side="top", dtick=1)
        fh.update_yaxes(tickfont=dict(size=10), automargin=True)
        fh.update_xaxes(tickfont=dict(size=10))
        fh.update_layout(height=max(360, 24 * len(mat) + 130), margin=dict(l=10, r=10, t=10, b=10),
                         plot_bgcolor="#d9d9d9",
                         coloraxis_colorbar=dict(orientation="h", y=-0.12, thickness=10, len=0.7, title_side="right"))
        st.plotly_chart(fh, width="stretch")
        st.caption("PM2.5 promedio anual por estación y año (µg/m³); gris = sin dato. "
                   "Más oscuro = más contaminación. Se filtra con el municipio de la barra lateral.")

    elif vista == "Ranking del año":
        base = datos[datos["anio"] == anio_sel]
        if municipio != "Todos":
            base = base[base["municipio"] == municipio]
        if base.empty:
            st.info(f"No hay estaciones con dato en {anio_sel} para este filtro.")
        else:
            top_n = base.sort_values("promedio", ascending=False).head(20).sort_values("promedio")
            top_n = top_n.assign(etiqueta=top_n["estacion"].str.slice(0, 26) if municipio != "Todos" else
                                 top_n["estacion"].str.slice(0, 18) + " · " + top_n["municipio"].str.slice(0, 6))
            fr = px.bar(top_n, x="promedio", y="etiqueta", orientation="h", color="categoria",
                        color_discrete_map=COLORES, category_orders={"categoria": ["baja", "media", "alta"]},
                        labels={"promedio": "PM2.5 promedio anual (µg/m³)", "etiqueta": "", "categoria": "Categoría"},
                        text=top_n["promedio"].map(lambda v: f"{v:.1f}"))
            fr.add_vline(x=LIMITE_COLOMBIA, line_dash="dash", line_color="#6d6875",
                         annotation_text="Colombia 25", annotation_position="top right")
            fr.add_vline(x=GUIA_OMS, line_dash="dot", line_color="#6d6875",
                         annotation_text="OMS 5", annotation_position="top left")
            fr.update_traces(hovertemplate="%{y}: %{x:.1f} µg/m³<extra></extra>")
            fr.update_yaxes(tickfont=dict(size=10), automargin=True)
            fr.update_xaxes(range=[0, max(top_n["promedio"].max(), LIMITE_COLOMBIA) * 1.15])
            fr.update_layout(height=max(320, 28 * len(top_n) + 130), margin=dict(l=10, r=10, t=30, b=10),
                             legend=dict(orientation="h", y=-0.12))
            st.plotly_chart(fr, width="stretch")
            n_sup = int((base["promedio"] > LIMITE_COLOMBIA).sum())
            st.caption(f"{anio_sel}: {len(base)} estaciones con dato; {n_sup} superan el límite colombiano anual de 25 µg/m³. "
                       "Se muestran hasta 20, de mayor a menor.")

    else:
        st.markdown(f"Categoría anual esperada del año siguiente para **{est.estacion}**.")
        try:
            pred = predecir(int(id_sel))
            c1, c2 = st.columns(2)
            c1.metric(f"Base: {pred['anio_base']}", f"{pred['pm25_promedio_base']:.1f} µg/m³",
                      pred["categoria_base"].capitalize(), delta_color="off")
            c2.metric(f"Estimada {pred['anio_predicho']}", pred["categoria_predicha"].capitalize())
            pr = pd.DataFrame({"categoria": list(pred["probabilidades"]), "prob": list(pred["probabilidades"].values())})
            pr["categoria"] = pd.Categorical(pr["categoria"], ["baja", "media", "alta"], ordered=True)
            pr = pr.sort_values("categoria")
            fig3 = px.bar(pr, x="prob", y="categoria", orientation="h", color="categoria", color_discrete_map=COLORES,
                          category_orders={"categoria": ["baja", "media", "alta"]},
                          labels={"prob": "Probabilidad", "categoria": ""}, text=pr["prob"].map(lambda p: f"{p:.0%}"))
            fig3.update_layout(height=220, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
                               xaxis=dict(range=[0, 1], tickformat=".0%"), yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig3, width="stretch")
        except ValueError as e:
            st.info(f"No se puede estimar para esta estación: {e}")
        st.warning(
            "Es un Naive Bayes entrenado con pocos datos anuales (Macro F1 0.52 en la evaluación). "
            "En las pruebas fue menos exacto que suponer que el año siguiente repite la categoría actual (Macro F1 0.66). "
            "Tómalo como una referencia, no como un pronóstico."
        )

# ------------------------------------------------------------------ chat con el agente

with col_chat:
    st.subheader("Pregunta al agente")
    agente = get_agente()
    if agente is None:
        st.warning(f"El chat no está disponible: {st.session_state.agente_error}. "
                   "Copia `.env.example` a `.env`, pon tu clave de Groq y reinicia la app. El resto del panel funciona sin ella.")

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []
    usar_contexto = st.checkbox("Incluir en la pregunta la estación y el año seleccionados", value=True)

    st.caption("Ejemplos:")
    pendiente = None
    for i, ej in enumerate(PREGUNTAS_EJEMPLO):
        if st.button(ej, key=f"ej{i}", width="stretch", disabled=agente is None):
            pendiente = ej

    caja = st.container(height=430)
    with caja:
        for m in st.session_state.mensajes:
            with st.chat_message(m["rol"]):
                st.markdown(m["texto"])
                if m.get("herramientas"):
                    with st.expander("Herramientas usadas y fuentes"):
                        st.write(", ".join(m["herramientas"]))
                        for f in m.get("fuentes", []):
                            st.markdown(f"- {f}")

    entrada = st.chat_input("Escribe tu pregunta sobre la calidad del aire", disabled=agente is None)
    pregunta = pendiente or entrada
    if pregunta and agente is not None:
        st.session_state.mensajes.append({"rol": "user", "texto": pregunta})
        enviada = pregunta
        if usar_contexto:
            enviada = (f"(Contexto de la interfaz: estación seleccionada {est.estacion}, municipio {est.municipio}, "
                       f"id {int(id_sel)}, año {int(anio_sel)}.) {pregunta}")
        with caja:
            with st.chat_message("user"):
                st.markdown(pregunta)
            with st.chat_message("assistant"):
                with st.spinner("Consultando herramientas…"):
                    r = agente.preguntar(enviada)
                st.markdown(r["respuesta"])
        st.session_state.mensajes.append({
            "rol": "assistant", "texto": r["respuesta"],
            "herramientas": r["herramientas"], "fuentes": r["fuentes"],
        })
        st.rerun()

    if st.session_state.mensajes and st.button("Borrar conversación"):
        st.session_state.mensajes = []
        if agente is not None:
            agente.reiniciar()
        st.rerun()
