import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(page_title="Operational Time Analysis", layout="wide")

st.title("Operational Time & Demand Analysis")
st.caption("Exploratory analysis based on execution and travel times")

# --------------------------------------------------
# Data loading
# --------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

    def time_to_hours(val):
        if pd.isna(val):
            return 0.0
        h, m, *s = str(val).split(":")
        s = s[0] if s else 0
        return int(h) + int(m) / 60 + int(s) / 3600

    df["DURACAO_HORAS"] = df["DURACAO"].apply(time_to_hours)
    df["DESLOCAMENTO_HORAS"] = df["DESLOCAMENTO"].apply(time_to_hours)
    df["TMA_HORAS"] = df["DURACAO_HORAS"] + df["DESLOCAMENTO_HORAS"]

    df["DATA"] = pd.to_datetime(df["DATA"])
    df["ANO_MES"] = df["DATA"].dt.to_period("M").astype(str)

    return df


df = load_data()

# --------------------------------------------------
# Filters
# --------------------------------------------------
st.sidebar.header("Filters")

grupo_os = st.sidebar.multiselect(
    "Grupo OS",
    options=sorted(df["GRUPO_OS"].unique()),
    default=sorted(df["GRUPO_OS"].unique())
)

df_grupo = df[df["GRUPO_OS"].isin(grupo_os)]

tipo_os = st.sidebar.selectbox(
    "Tipo OS",
    options=["TODOS"] + sorted(df_grupo["TIPO_OS"].unique())
)

if tipo_os != "TODOS":
    df_f = df_grupo[df_grupo["TIPO_OS"] == tipo_os]
else:
    df_f = df_grupo.copy()

# --------------------------------------------------
# BOX PLOTS
# --------------------------------------------------
st.subheader("Time Distributions by Region")

def boxplot_por_regiao(df, coluna, titulo):
    dados = []
    labels = []

    for regiao, g in df.groupby("REGIAO"):
        dados.append(g[coluna].dropna().values)
        labels.append(regiao)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.boxplot(dados, labels=labels, showfliers=True)
    ax.set_title(titulo)
    ax.set_xlabel("Região")
    ax.set_ylabel("Horas")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    st.pyplot(fig)


c1, c2, c3 = st.columns(3)

with c1:
    boxplot_por_regiao(df_f, "DESLOCAMENTO_HORAS", "Deslocamento por Região")

with c2:
    boxplot_por_regiao(df_f, "DURACAO_HORAS", "Duração por Região")

with c3:
    boxplot_por_regiao(df_f, "TMA_HORAS", "TMA (Duração + Deslocamento) por Região")

# --------------------------------------------------
# LINE CHART (MONTHLY)
# --------------------------------------------------
st.subheader("Monthly Time Evolution")

metric = st.radio(
    "Metric",
    ["DESLOCAMENTO_HORAS", "DURACAO_HORAS", "TMA_HORAS"],
    horizontal=True
)

serie = (
    df_f.groupby("ANO_MES")[metric]
    .mean()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(serie["ANO_MES"], serie[metric], marker="o")
ax.set_title(f"Monthly Average – {metric}")
ax.set_xlabel("Month / Year")
ax.set_ylabel("Hours")
ax.tick_params(axis="x", rotation=45)
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)

# --------------------------------------------------
# DAILY DEMAND
# --------------------------------------------------
st.subheader("Daily Demand by Region")

demanda = (
    df_f.groupby(["REGIAO", "DATA"])
    .size()
    .reset_index(name="QTD_OS")
)

fig, ax = plt.subplots(figsize=(10, 4))

for regiao, g in demanda.groupby("REGIAO"):
    ax.plot(g["DATA"], g["QTD_OS"], label=regiao)

ax.set_title("Daily OS Demand")
ax.set_xlabel("Date")
ax.set_ylabel("OS per day")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)

# --------------------------------------------------
# PIE CHARTS
# --------------------------------------------------
st.subheader("OS Distribution by Region")

regioes = df_f["REGIAO"].unique()
cols = st.columns(len(regioes))

for col, regiao in zip(cols, regioes):
    with col:
        dist = (
            df_f[df_f["REGIAO"] == regiao]
            .groupby("GRUPO_OS")
            .size()
        )

        fig, ax = plt.subplots()
        ax.pie(
            dist.values,
            labels=dist.index,
            autopct="%1.1f%%",
            startangle=90
        )
        ax.set_title(regiao)

        st.pyplot(fig)
