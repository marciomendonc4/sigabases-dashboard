import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Operational Diagnostics", layout="wide")
st.title("Operational Diagnostics – Time & Demand")


@st.cache_data
def load_data():
    df = pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

    def to_hours(val):
        if pd.isna(val):
            return 0.0
        h, m, *s = str(val).split(":")
        s = s[0] if s else 0
        return int(h) + int(m)/60 + int(s)/3600

    df["DURACAO_HORAS"] = df["DURACAO"].apply(to_hours)
    df["DESLOCAMENTO_HORAS"] = df["DESLOCAMENTO"].apply(to_hours)
    df["TMA_HORAS"] = df["DURACAO_HORAS"] + df["DESLOCAMENTO_HORAS"]

    df["DATA"] = pd.to_datetime(df["DATA"])
    df["MES"] = df["DATA"].dt.to_period("M").astype(str)

    return df

df = load_data()

df = df[df["TIPO_OS"] != "INDISP"]


st.sidebar.header("Filters")

grupo_os_opcoes = ["LN", "CORTE", "PLANTAO"]
grupo_selecionado = st.sidebar.radio("GRUPO_OS", grupo_os_opcoes, horizontal=True)

df_filtro_grupo = df[df["GRUPO_OS"] == grupo_selecionado]

tipo_os_opcoes = sorted(df_filtro_grupo["TIPO_OS"].unique())
tipo_os_selecionado = st.sidebar.selectbox("TIPO_OS", ["ALL"] + tipo_os_opcoes)

if tipo_os_selecionado != "ALL":
    df_filtrado = df_filtro_grupo[df_filtro_grupo["TIPO_OS"] == tipo_os_selecionado]
else:
    df_filtrado = df_filtro_grupo.copy()


st.markdown("## Distribution of Time Metrics")

c1, c2, c3 = st.columns(3)

with c1:
    fig = px.box(
        df_filtrado,
        y="DESLOCAMENTO_HORAS",
        points="outliers",
        title="Deslocamento (hours)",
        labels={"DESLOCAMENTO_HORAS": "Hours"}
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.box(
        df_filtrado,
        y="DURACAO_HORAS",
        points="outliers",
        title="Duração (hours)",
        labels={"DURACAO_HORAS": "Hours"}
    )
    st.plotly_chart(fig, use_container_width=True)

with c3:
    fig = px.box(
        df_filtrado,
        y="TMA_HORAS",
        points="outliers",
        title="TMA – Duração + Deslocamento (hours)",
        labels={"TMA_HORAS": "Hours"}
    )
    st.plotly_chart(fig, use_container_width=True)


st.markdown("## Monthly Evolution")

metric = st.radio(
    "Metric",
    ["DESLOCAMENTO_HORAS", "DURACAO_HORAS", "TMA_HORAS"],
    horizontal=True
)

df_mes = (
    df_filtrado
    .groupby("MES")[metric]
    .mean()
    .reset_index()
)

fig = px.line(
    df_mes,
    x="MES",
    y=metric,
    markers=True,
    labels={metric: "Average hours", "MES": "Month"},
    title=f"Monthly Average – {metric.replace('_HORAS','')}"
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("## Daily Demand (OS/day)")

df_demanda = (
    df_filtrado
    .groupby(["DATA", "REGIAO"])
    .size()
    .reset_index(name="DEMANDA_DIA")
)

fig = px.line(
    df_demanda,
    x="DATA",
    y="DEMANDA_DIA",
    color="REGIAO",
    labels={"DEMANDA_DIA": "OS/day", "DATA": "Date"},
    title="Daily Demand per Region"
)
st.plotly_chart(fig, use_container_width=True)


st.markdown("## Distribution of GRUPO_OS by Region")

regioes = sorted(df["REGIAO"].unique())
cols = st.columns(3)

for i, regiao in enumerate(regioes):
    df_pie = (
        df[df["REGIAO"] == regiao]
        .groupby("GRUPO_OS")
        .size()
        .reset_index(name="QTD")
    )

    fig = px.pie(
        df_pie,
        values="QTD",
        names="GRUPO_OS",
        title=regiao,
        hole=0.4
    )
    fig.update_traces(textinfo="percent+label")

    cols[i % 3].plotly_chart(fig, use_container_width=True)
