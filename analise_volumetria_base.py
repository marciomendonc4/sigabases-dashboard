import streamlit as st
import pandas as pd
import altair as alt
import pydeck as pdk

st.set_page_config(page_title="Dispersão Operacional", layout="wide")

ARQUIVO = "ANALISE_VOLUMETRIA_BASE.xlsx"
ARQUIVO_MAPA = "ANALISE_MAPA_VOLUMETRIA.parquet"



TMD_REFERENCIA = {
    (25, "PLANTÃO"): 25,
    (25, "LN"): 20,
    (25, "CORTE"): 9,

    (31, "PLANTÃO"): 25,
    (31, "LN"): 20,
    (31, "CORTE"): 9,

    (6, "CORTE"): 10,
    (6, "LN"): 23,
    (6, "PLANTÃO"): 29,

    (18, "CORTE"): 10,
    (18, "LN"): 25,
    (18, "PLANTÃO"): 29,
}

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
        "regional",
        "demanda_recebida_eqtl",
        "demanda_recebida_gere",
        "demanda_recebida_dpl",
        "ups",
        #"tme",
        "tmd",
        "ups_eqtl",
        "ups_gere",
        "ups_dpl"
    ]

    for col in colunas_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df
def carregar_mapa():
    df = pd.read_parquet(ARQUIVO_MAPA)

    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    for col in ["regional", "lat_grid", "lon_grid", "demanda", "ups", "tmd_total", "tmd_medio"]:
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

df_filtrado["tmd_esperado"] = df_filtrado.apply(
    lambda row: TMD_REFERENCIA.get(
        (int(row["regional"]), row["processo"]),
        pd.NA
    ),
    axis=1
)

df_tmd = (
    df_filtrado
    .groupby(["regional", "municipio_eqp", "processo"], as_index=False)
    .agg(
        demanda=("demanda_selecionada", "sum"),
        tmd_total=("tmd", "sum"),
        tmd_esperado=("tmd_esperado", "mean")
    )
)

df_tmd = df_tmd[df_tmd["demanda"] > 0].copy()

df_tmd["tmd_executado_medio"] = (
    df_tmd["tmd_total"] / df_tmd["demanda"]
)

df_tmd["gap_tmd"] = (
    df_tmd["tmd_executado_medio"] - df_tmd["tmd_esperado"]
)

tmd_exec_medio = (
    df_tmd["tmd_total"].sum() / df_tmd["demanda"].sum()
    if df_tmd["demanda"].sum() > 0 else 0
)

tmd_esp_medio = (
    (df_tmd["tmd_esperado"] * df_tmd["demanda"]).sum() / df_tmd["demanda"].sum()
    if df_tmd["demanda"].sum() > 0 else 0
)

gap_tmd = tmd_exec_medio - tmd_esp_medio


df_analise = (
    df_filtrado
    .groupby(["municipio_eqp", "processo", "municipio_vol"], as_index=False)
    .agg(
        demanda=("demanda_selecionada", "sum"),
        ups=("ups_selecionada", "sum"),
        tmd=("tmd", "sum")
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

st.subheader("Distribuição da demanda por cidades atendidas")

graf_demanda = (
    alt.Chart(df_analise)
    .mark_bar()
    .encode(
        y=alt.Y("municipio_eqp:N", title="Base / Sigla"),
        x=alt.X("sum(demanda):Q", stack="normalize", title="% da demanda"),
        color=alt.Color("municipio_vol:N", title="Cidades atendidas"),
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

st.subheader("Distribuição da UPS por Cidades atendidas")

graf_ups = (
    alt.Chart(df_analise)
    .mark_bar()
    .encode(
        y=alt.Y("municipio_eqp:N", title="Base / Sigla"),
        x=alt.X("sum(ups):Q", stack="normalize", title="% da UPS"),
        color=alt.Color("municipio_vol:N", title="Cidades atendidas"),
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

st.subheader("TMD")

col_tmd1, col_tmd2, col_tmd3 = st.columns(3)

col_tmd1.metric("TMD executado médio", f"{tmd_exec_medio:.1f}")
col_tmd2.metric("TMD esperado médio", f"{tmd_esp_medio:.1f}")
col_tmd3.metric("Gap TMD", f"{gap_tmd:+.1f}")

st.dataframe(
    df_tmd.sort_values("gap_tmd", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional": "Regional",
        "municipio_eqp": "Base / Sigla",
        "processo": "Processo",
        "demanda": st.column_config.NumberColumn("Demanda", format="%.0f"),
        "tmd_total": st.column_config.NumberColumn("TMD total", format="%.0f"),
        "tmd_executado_medio": st.column_config.NumberColumn("TMD executado médio", format="%.1f"),
        "tmd_esperado": st.column_config.NumberColumn("TMD esperado", format="%.1f"),
        "gap_tmd": st.column_config.NumberColumn("Gap TMD", format="%+.1f"),
    }
)

df_tmd_cidade = (
    df_tmd
    .groupby(["municipio_eqp"], as_index=False)
    .apply(
        lambda g: pd.Series({
            "demanda_total": g["demanda"].sum(),
            "tmd_executado_balanceado": (
                (g["tmd_executado_medio"] * g["demanda"]).sum() / g["demanda"].sum()
                if g["demanda"].sum() > 0 else pd.NA
            ),
            "tmd_esperado_balanceado": (
                (g["tmd_esperado"] * g["demanda"]).sum() / g["demanda"].sum()
                if g["demanda"].sum() > 0 else pd.NA
            )
        })
    )
    .reset_index(drop=True)
)

df_tmd_cidade["gap_tmd_balanceado"] = (
    df_tmd_cidade["tmd_executado_balanceado"] -
    df_tmd_cidade["tmd_esperado_balanceado"]
)

st.subheader("TMD balanceado por base")

st.dataframe(
    df_tmd_cidade.sort_values("gap_tmd_balanceado", ascending=False),
    use_container_width=True,
    hide_index=True,
    column_config={
        "municipio_eqp": "Base / Sigla",
        "demanda_total": st.column_config.NumberColumn("Demanda total", format="%.0f"),
        "tmd_executado_balanceado": st.column_config.NumberColumn("TMD executado balanceado", format="%.1f"),
        "tmd_esperado_balanceado": st.column_config.NumberColumn("TMD esperado balanceado", format="%.1f"),
        "gap_tmd_balanceado": st.column_config.NumberColumn("Gap TMD balanceado", format="%+.1f"),
    }
)

st.divider()
st.subheader("Mapa de calor operacional")

df_mapa = carregar_mapa()

df_mapa = df_mapa[
    (df_mapa["regional"].isin(regionais_sel)) &
    (df_mapa["municipio_eqp"].isin(bases_sel)) &
    (df_mapa["processo"].isin(processos_sel))
].copy()

df_mapa["tmd_esperado"] = df_mapa.apply(
    lambda row: TMD_REFERENCIA.get(
        (int(row["regional"]), row["processo"]),
        0
    ),
    axis=1
)

df_mapa["gap_tmd"] = df_mapa["tmd_medio"] - df_mapa["tmd_esperado"]
df_mapa["peso_gap_tmd"] = df_mapa["gap_tmd"].clip(lower=0)

tipo_mapa = st.selectbox(
    "Indicador do mapa",
    ["Demanda", "UPS", "TMD", "Variação TMD"]
)

coluna_peso = {
    "Demanda": "demanda",
    "UPS": "ups",
    "TMD médio": "tmd_medio",
    "Gap TMD": "peso_gap_tmd"
}[tipo_mapa]

df_mapa = df_mapa[
    (df_mapa["lat_grid"] != 0) &
    (df_mapa["lon_grid"] != 0) &
    (df_mapa[coluna_peso] > 0)
].copy()

if df_mapa.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    view_state = pdk.ViewState(
        latitude=df_mapa["lat_grid"].mean(),
        longitude=df_mapa["lon_grid"].mean(),
        zoom=7,
        pitch=0
    )

    layer = pdk.Layer(
        "HeatmapLayer",
        data=df_mapa,
        get_position="[lon_grid, lat_grid]",
        get_weight=coluna_peso,
        radiusPixels=45,
        intensity=1,
        threshold=0.05
    )

    deck =  pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "text": (
                "Cidade: {municipio_vol}\n"
                "Base: {municipio_eqp}\n"
                "Processo: {processo}\n"
                "Demanda: {demanda}\n"
                "UPS: {ups}\n"
                "TMD médio: {tmd_medio}\n"
                "Gap TMD: {gap_tmd}"
            )
        }
    )

    st.pydeck_chart(deck, use_container_width=True)