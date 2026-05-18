import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dispersão Operacional", layout="wide")

ARQUIVO = "ANALISE_VOLUMETRIA_BASE.xlsx"

REGIONAIS = {
    6: "SUL MA",
    18: "LESTE MA",
    25: "NORTE MA",
    31: "NOROESTE MA"
}

@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO)

    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    colunas_num = [
        "demanda_recebida_eqtl",
        "demanda_recebida_gere",
        "demanda_recebida_dpl",
        "ups",
        "tme",
        "ups_eqtl",
        "ups_gere",
        "ups_dpl"
    ]

    for col in colunas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


df = carregar_dados()

st.title("Dispersão Operacional por Base")
st.caption("Análise de onde a demanda e o esforço operacional das bases estão sendo consumidos.")

with st.sidebar:
    st.header("Filtros")

    regionais_sel = st.multiselect(
        "Regional",
        options=sorted(df["regional"].dropna().unique()),
        default=sorted(df["regional"].dropna().unique()),
        format_func=lambda x: REGIONAIS.get(x, str(x))
    )

    df_regional = df[
        df["regional"].isin(regionais_sel)
    ]

    bases_sel = st.multiselect(
        "Base / Sigla",
        options=sorted(df_regional["municipio_eqp"].dropna().unique()),
        default=sorted(df_regional["municipio_eqp"].dropna().unique())
    )

    df_base = df_regional[
        df_regional["municipio_eqp"].isin(bases_sel)
    ]

    processos_sel = st.multiselect(
        "Processo",
        options=sorted(df_base["processo"].dropna().unique()),
        default=sorted(df_base["processo"].dropna().unique())
    )

    fontes_sel = st.multiselect(
        "Fonte",
        ["DPL", "EQTL", "GERE"],
        default=["DPL"]
    )

df_filtrado = df[
    (df["regional"].isin(regionais_sel)) &
    (df["municipio_eqp"].isin(bases_sel)) &
    (df["processo"].isin(processos_sel))
].copy()

df_filtrado["demanda_selecionada"] = 0
df_filtrado["ups_selecionada"] = 0

if "DPL" in fontes_sel:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_dpl"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_dpl"]

if "EQTL" in fontes_sel:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_eqtl"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_eqtl"]

if "GERE" in fontes_sel:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_gere"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_gere"]


df_analise = (
    df_filtrado
    .groupby(["municipio_eqp", "processo", "municipio_vol"], as_index=False)
    .agg(
        demanda=("demanda_selecionada", "sum"),
        ups=("ups_selecionada", "sum"),
        tme=("tme", "sum")
    )
)

df_analise["cidade_base"] = df_analise["municipio_eqp"]
df_analise["fora_base"] = df_analise["municipio_eqp"] != df_analise["municipio_vol"]

df_analise["demanda_total_base"] = (
    df_analise
    .groupby(["municipio_eqp", "processo"])["demanda"]
    .transform("sum")
)

df_analise["ups_total_base"] = (
    df_analise
    .groupby(["municipio_eqp", "processo"])["ups"]
    .transform("sum")
)

df_analise["pct_demanda"] = (
    df_analise["demanda"] /
    df_analise["demanda_total_base"].replace(0, pd.NA)
)

df_analise["pct_ups"] = (
    df_analise["ups"] /
    df_analise["ups_total_base"].replace(0, pd.NA)
)

demanda_total = df_analise["demanda"].sum()
ups_total = df_analise["ups"].sum()

demanda_fora = df_analise.loc[df_analise["fora_base"], "demanda"].sum()
ups_fora = df_analise.loc[df_analise["fora_base"], "ups"].sum()

pct_demanda_fora = demanda_fora / demanda_total if demanda_total else 0
pct_ups_fora = ups_fora / ups_total if ups_total else 0

qtd_cidades = df_analise["municipio_vol"].nunique()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Demanda total", f"{demanda_total:,.0f}".replace(",", "."))
col2.metric("% demanda fora da base", f"{pct_demanda_fora:.1%}")
col3.metric("% UPS fora da base", f"{pct_ups_fora:.1%}")
col4.metric("Cidades atendidas", qtd_cidades)

st.divider()

st.subheader("Distribuição da demanda por cidade executada")

graf_demanda = (
    alt.Chart(df_analise)
    .mark_bar()
    .encode(
        y=alt.Y("municipio_eqp:N", title="Base / Sigla"),
        x=alt.X("sum(demanda):Q", stack="normalize", title="% da demanda"),
        color=alt.Color("municipio_vol:N", title="Cidade executada"),
        tooltip=[
            "municipio_eqp",
            "processo",
            "municipio_vol",
            alt.Tooltip("demanda:Q", format=",.0f"),
            alt.Tooltip("pct_demanda:Q", format=".1%")
        ]
    )
    .properties(height=420)
)

st.altair_chart(graf_demanda, use_container_width=True)

st.subheader("Distribuição do UPS por cidade executada")

graf_ups = (
    alt.Chart(df_analise)
    .mark_bar()
    .encode(
        y=alt.Y("municipio_eqp:N", title="Base / Sigla"),
        x=alt.X("sum(ups):Q", stack="normalize", title="% do UPS"),
        color=alt.Color("municipio_vol:N", title="Cidade executada"),
        tooltip=[
            "municipio_eqp",
            "processo",
            "municipio_vol",
            alt.Tooltip("ups:Q", format=",.0f"),
            alt.Tooltip("pct_ups:Q", format=".1%")
        ]
    )
    .properties(height=420)
)

st.altair_chart(graf_ups, use_container_width=True)

st.subheader("Tabela de dispersão")

df_tabela = df_analise.copy()
df_tabela["pct_demanda"] = df_tabela["pct_demanda"] * 100
df_tabela["pct_ups"] = df_tabela["pct_ups"] * 100

df_tabela = df_tabela.sort_values(
    ["municipio_eqp", "processo", "ups"],
    ascending=[True, True, False]
)

st.dataframe(
    df_tabela,
    use_container_width=True,
    hide_index=True,
    column_config={
        "municipio_eqp": "Base / Sigla",
        "processo": "Processo",
        "municipio_vol": "Cidade executada",
        "demanda": st.column_config.NumberColumn("Demanda", format="%.0f"),
        "ups": st.column_config.NumberColumn("UPS", format="%.1f"),
        "tme": st.column_config.NumberColumn("TME", format="%.1f"),
        "pct_demanda": st.column_config.NumberColumn("% Demanda", format="%.1f%%"),
        "pct_ups": st.column_config.NumberColumn("% UPS", format="%.1f%%"),
        "fora_base": "Fora da base"
    },
    column_order=[
        "municipio_eqp",
        "processo",
        "municipio_vol",
        "demanda",
        "pct_demanda",
        "ups",
        "pct_ups",
        "tme",
        "fora_base"
    ]
)