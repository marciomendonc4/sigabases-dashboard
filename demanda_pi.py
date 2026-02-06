import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="DPL SUL PI", layout="wide")

st.title("Tempos Operacionais")


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



grupo_os = st.sidebar.multiselect(
    "Grupo OS",
    options=sorted(df["GRUPO_OS"].dropna().unique()),
    default=sorted(df["GRUPO_OS"].dropna().unique())
)

df_grupo = df[df["GRUPO_OS"].isin(grupo_os)]

tipo_os = st.sidebar.selectbox(
    "Tipo OS",
    options=["TODOS"] + sorted(df_grupo["TIPO_OS"].dropna().unique())
)

if tipo_os != "TODOS":
    df_f = df_grupo[df_grupo["TIPO_OS"] == tipo_os]
else:
    df_f = df_grupo.copy()


regioes = st.sidebar.multiselect(
    "Região",
    options=sorted(df["REGIAO"].dropna().unique()),
    default=sorted(df["REGIAO"].dropna().unique())
)

#df_f = df[df["REGIAO"].isin(regioes)]
df_f = df_f[df_f["REGIAO"].isin(regioes)]
st.subheader("Distribuição do Tempo Operacional")

def boxplot_por_regiao(df, coluna, titulo):
    dados = []
    labels = []
    medianas = []

    for regiao, g in df.groupby("REGIAO"):
        valores = g[coluna].dropna().values
        if len(valores) > 0:
            dados.append(valores)
            labels.append(regiao)
            medianas.append(np.median(valores))

    fig, ax = plt.subplots(figsize=(12, 5))
    bp = ax.boxplot(dados, labels=labels, showfliers=True)

    for i, med in enumerate(medianas):
        ax.text(
            i + 1,
            med,
            f"{med:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            bbox=dict(
                facecolor="white",
                edgecolor="black",
                boxstyle="round,pad=0.25",
                alpha=0.85
            )
        )

    ax.set_title(titulo)
    ax.set_xlabel("Região")
    ax.set_ylabel("Horas")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    st.pyplot(fig)

boxplot_por_regiao(df_f, "DESLOCAMENTO_HORAS", "Deslocamento por Região (horas)")
boxplot_por_regiao(df_f, "DURACAO_HORAS", "Duração por Região (horas)")
boxplot_por_regiao(df_f, "TMA_HORAS", "TMA – Duração + Deslocamento por Região (horas)")

st.subheader("Distribuição do Tempo Operacional")

metric = st.radio(
    "Métrica",
    ["DESLOCAMENTO_HORAS", "DURACAO_HORAS", "TMA_HORAS"],
    horizontal=True
)

serie = (
    df_f.groupby("ANO_MES")[metric]
    .mean()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(16, 4))
ax.plot(serie["ANO_MES"], serie[metric], marker="o")
ax.set_title(f"Média Mensal – {metric}")
ax.set_xlabel("Mês/Ano")
ax.set_ylabel("Tempo")
ax.tick_params(axis="x", rotation=45)
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)

st.subheader("Demanda Diária por Região")

demanda = (
    df_f.groupby(["REGIAO", "DATA"])
    .size()
    .reset_index(name="QTD_OS")
)

fig, ax = plt.subplots(figsize=(16, 4))

for regiao, g in demanda.groupby("REGIAO"):
    ax.plot(g["DATA"], g["QTD_OS"], label=regiao)

ax.set_title("Demanda diária")
ax.set_xlabel("Data")
ax.set_ylabel("OS por dia")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)



st.subheader("Distribuição do Balde por Região")

regioes = sorted(df_f["REGIAO"].dropna().unique())

pies_por_linha = 3
linhas = range(0, len(regioes), pies_por_linha)

for i in linhas:
    cols = st.columns(pies_por_linha)

    for col, regiao in zip(cols, regioes[i:i + pies_por_linha]):
        with col:
            dist = (
                df_f[df_f["REGIAO"] == regiao]
                .groupby("GRUPO_OS")
                .size()
            )

            fig, ax = plt.subplots(figsize=(4, 4))
            ax.pie(
                dist.values,
                labels=dist.index,
                autopct="%1.1f%%",
                startangle=90
            )
            ax.set_title(regiao)

            st.pyplot(fig)
