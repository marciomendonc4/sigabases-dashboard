import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Distribuição do Balde",
    layout="wide"
)

st.title("Distribuição do Balde de Serviços")

arquivo = st.file_uploader(
    "Carregue o arquivo XLSX",
    type=["xlsx"]
)

if arquivo is None:
    st.stop()

df = pd.read_excel(arquivo)

df.columns = df.columns.str.strip()

df["QTD"] = pd.to_numeric(df["QTD"], errors="coerce").fillna(0)

def filtro_cascata(df_base, coluna, label):
    opcoes = sorted(df_base[coluna].dropna().unique())

    selecionados = st.sidebar.multiselect(
        label,
        opcoes,
        default=opcoes
    )

    if selecionados:
        return df_base[df_base[coluna].isin(selecionados)]

    return df_base.iloc[0:0]

st.sidebar.header("Filtros")

df_filtro = df.copy()

df_filtro = filtro_cascata(df_filtro, "base", "Base")
df_filtro = filtro_cascata(df_filtro, "MUNICIPIO", "Município")
df_filtro = filtro_cascata(df_filtro, "SEGMENTO", "Segmento")
df_filtro = filtro_cascata(df_filtro, "Tipo_Equipe", "Tipo de Equipe")
df_filtro = filtro_cascata(df_filtro, "equipe", "Equipe")
df_filtro = filtro_cascata(df_filtro, "GRUPO_OS", "Grupo OS")
df_filtro = filtro_cascata(df_filtro, "TIPO_OS", "Tipo OS")

df_filtrado = df_filtro.copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado.")
    st.stop()

total_servicos = int(df_filtrado["QTD"].sum())
total_equipes = df_filtrado["equipe"].nunique()
total_bases = df_filtrado["base"].nunique()

c1, c2, c3 = st.columns(3)

c1.metric("Serviços", f"{total_servicos:,}".replace(",", "."))
c2.metric("Equipes", total_equipes)
c3.metric("Bases", total_bases)

st.divider()

dist_segmento = (
    df_filtrado
    .groupby(["SEGMENTO", "GRUPO_OS"], as_index=False)["QTD"]
    .sum()
)

dist_segmento["TOTAL"] = (
    dist_segmento
    .groupby("SEGMENTO")["QTD"]
    .transform("sum")
)

dist_segmento["PERC"] = (
    dist_segmento["QTD"] /
    dist_segmento["TOTAL"]
)

fig_segmento = px.bar(
    dist_segmento,
    x="SEGMENTO",
    y="PERC",
    color="GRUPO_OS",
    text=dist_segmento["PERC"].map(lambda x: f"{x:.1%}")
)

fig_segmento.update_layout(
    barmode="stack",
    yaxis_tickformat=".0%",
    xaxis_title=None,
    yaxis_title="% do Balde",
    legend_title="Grupo OS",
    height=500
)

fig_segmento.update_traces(
    textposition="inside"
)

st.subheader("Distribuição por Segmento")

st.plotly_chart(
    fig_segmento,
    use_container_width=True
)

dist_tipo = (
    df_filtrado
    .groupby(["Tipo_Equipe", "GRUPO_OS"], as_index=False)["QTD"]
    .sum()
)

dist_tipo["TOTAL"] = (
    dist_tipo
    .groupby("Tipo_Equipe")["QTD"]
    .transform("sum")
)

dist_tipo["PERC"] = (
    dist_tipo["QTD"] /
    dist_tipo["TOTAL"]
)

fig_tipo = px.bar(
    dist_tipo,
    x="Tipo_Equipe",
    y="PERC",
    color="GRUPO_OS",
    text=dist_tipo["PERC"].map(lambda x: f"{x:.1%}")
)

fig_tipo.update_layout(
    barmode="stack",
    yaxis_tickformat=".0%",
    xaxis_title=None,
    yaxis_title="% do Balde",
    legend_title="Grupo OS",
    height=600
)

fig_tipo.update_traces(
    textposition="inside"
)

st.subheader("Distribuição por Tipo de Equipe")

st.plotly_chart(
    fig_tipo,
    use_container_width=True
)

heatmap = (
    df_filtrado
    .pivot_table(
        index="Tipo_Equipe",
        columns="GRUPO_OS",
        values="QTD",
        aggfunc="sum",
        fill_value=0
    )
)

heatmap = heatmap.div(
    heatmap.sum(axis=1),
    axis=0
)

fig_heatmap = px.imshow(
    heatmap,
    text_auto=".0%",
    aspect="auto"
)

fig_heatmap.update_layout(
    height=700,
    xaxis_title="Grupo OS",
    yaxis_title="Tipo de Equipe"
)

st.subheader("Heatmap de Distribuição")

st.plotly_chart(
    fig_heatmap,
    use_container_width=True
)

tabela = (
    df_filtrado
    .groupby(
        [
            "SEGMENTO",
            "Tipo_Equipe",
            "GRUPO_OS"
        ],
        as_index=False
    )["QTD"]
    .sum()
)

tabela["TOTAL"] = (
    tabela
    .groupby(
        [
            "SEGMENTO",
            "Tipo_Equipe"
        ]
    )["QTD"]
    .transform("sum")
)

tabela["PERC"] = (
    tabela["QTD"] /
    tabela["TOTAL"]
)

tabela["PERC"] = tabela["PERC"].map(
    lambda x: f"{x:.1%}"
)

tabela = tabela.sort_values(
    ["SEGMENTO", "Tipo_Equipe", "QTD"],
    ascending=[True, True, False]
)

st.subheader("Tabela Detalhada")

st.dataframe(
    tabela,
    use_container_width=True,
    hide_index=True
)