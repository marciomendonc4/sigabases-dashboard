import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

st.set_page_config(page_title="Demanda Operacional", layout="wide")

st.title("Mapa Operacional de Execuções")

# -----------------------------
# LOAD DATA
# -----------------------------

@st.cache_data
def load_data():

    df = pd.read_excel("demanda_pab.xlsx")

    df["DATA"] = pd.to_datetime(df["DATA"])

    df["MES_NUM"] = df["DATA"].dt.month

    df["PERIODO"] = df["MES_NUM"].apply(
        lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
    )

    # convert price if needed
    if df["PRECO_A_COBRAR"].dtype == object:
        df["PRECO_A_COBRAR"] = (
            df["PRECO_A_COBRAR"]
            .astype(str)
            .str.replace(",", ".")
            .astype(float)
        )

    return df


@st.cache_data
def load_equipes():

    eq = pd.read_excel("equipes_pab.xlsx", sheet_name="equipe")

    eq["qtd"] = (
        eq["qtd"]
        .astype(str)
        .str.replace(",", ".")
        .astype(float)
    )

    return eq


df = load_data()
equipes = load_equipes()

# -----------------------------
# PERIOD FILTER (TOP)
# -----------------------------

periodos = ["Todos", "Período Seco", "Período Úmido"]

periodo_selecionado = st.selectbox(
    "Selecione o período climático",
    periodos
)

if periodo_selecionado != "Todos":
    df = df[df["PERIODO"] == periodo_selecionado]

# -----------------------------
# SIDEBAR FILTERS (CASCADE)
# -----------------------------

sigla = st.sidebar.selectbox(
    "SIGLA",
    ["TODOS"] + sorted(df["SIGLA"].dropna().unique())
)

if sigla != "TODOS":
    df = df[df["SIGLA"] == sigla]

grupo = st.sidebar.selectbox(
    "GRUPO_OS",
    ["TODOS"] + sorted(df["GRUPO_OS"].dropna().unique())
)

if grupo != "TODOS":
    df = df[df["GRUPO_OS"] == grupo]

tipo = st.sidebar.selectbox(
    "TIPO_OS",
    ["TODOS"] + sorted(df["TIPO_OS"].dropna().unique())
)

if tipo != "TODOS":
    df = df[df["TIPO_OS"] == tipo]

atividade = st.sidebar.selectbox(
    "ATIVIDADE",
    ["TODOS"] + sorted(df["ATIVIDADE"].dropna().unique())
)

if atividade != "TODOS":
    df = df[df["ATIVIDADE"] == atividade]

equipe = st.sidebar.selectbox(
    "EQUIPE",
    ["TODOS"] + sorted(df["EQUIPE"].dropna().unique())
)

if equipe != "TODOS":
    df = df[df["EQUIPE"] == equipe]

# -----------------------------
# FILTER EQUIPES FILE
# -----------------------------

eq_filtrado = equipes.copy()

if sigla != "TODOS":
    eq_filtrado = eq_filtrado[eq_filtrado["sigla"] == sigla]

# -----------------------------
# TEAM METRICS
# -----------------------------

col1, col2 = st.columns([1,1])

total_equipes = eq_filtrado["qtd"].sum()

with col1:
    st.metric("Total de Equipes", f"{total_equipes:.1f}")

with col2:

    segmento_counts = (
        eq_filtrado
        .groupby("segmento")["qtd"]
        .sum()
        .reset_index()
    )

    st.write("Equipes por Segmento")
    st.dataframe(segmento_counts, use_container_width=True)

# -----------------------------
# MAP
# -----------------------------

st.subheader("Mapa de Execuções")

if df.empty:
    st.warning("Nenhum dado encontrado com os filtros atuais.")
else:

    center_lat = df["LATITUDE"].mean()
    center_lon = df["LONGITUDE"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11
    )

    # -----------------------------
    # HEATMAP
    # -----------------------------

    heat_data = df[["LATITUDE", "LONGITUDE"]].values.tolist()

    HeatMap(
        heat_data,
        radius=10,
        blur=15
    ).add_to(m)

    # -----------------------------
    # TEAM COLORED POINTS
    # -----------------------------

    cores = [
        "red","blue","green","purple","orange",
        "darkred","lightred","beige","darkblue",
        "darkgreen","cadetblue","darkpurple"
    ]

    equipes_lista = df["EQUIPE"].unique()

    color_map = {
        equipe: cores[i % len(cores)]
        for i, equipe in enumerate(equipes_lista)
    }

    for _, row in df.iterrows():

        folium.CircleMarker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            radius=3,
            color=color_map[row["EQUIPE"]],
            fill=True,
            fill_opacity=0.8,
            popup=f"""
            Equipe: {row['EQUIPE']}<br>
            Atividade: {row['ATIVIDADE']}<br>
            Grupo: {row['GRUPO_OS']}<br>
            Data: {row['DATA'].date()}
            """
        ).add_to(m)

    # -----------------------------
    # TEAM BASE MARKERS
    # -----------------------------

    for _, row in eq_filtrado.iterrows():

        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"""
            Município: {row['MUNICIPIO']}<br>
            Segmento: {row['segmento']}<br>
            Equipe: {row['equipe']}
            """,
            icon=folium.Icon(color="black", icon="home")
        ).add_to(m)

    # -----------------------------
    # DISPLAY MAP
    # -----------------------------

    st_folium(m, width=1400, height=700)