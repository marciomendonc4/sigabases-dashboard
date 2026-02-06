import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(layout="wide")


@st.cache_data
def load_data():
    df = pd.read_parquet("tempo_atribuicao.parquet")

    datetime_cols = [
        "DATA_ABERTURA_OS",
        "DATA_ATRIBUICAO_OS",
        "DATA_LIMITE_OS",
    ]

    for col in datetime_cols:
        df[col] = pd.to_datetime(
            df[col],
            errors="coerce",
            dayfirst=True
        )

    return df

df = load_data()


df["dias_abertura_atribuicao"] = (
    df["DATA_ATRIBUICAO_OS"] - df["DATA_ABERTURA_OS"]
).dt.total_seconds() / 86400

df["horas_ate_prazo"] = (
    df["DATA_LIMITE_OS"] - df["DATA_ATRIBUICAO_OS"]
).dt.total_seconds() / 3600


def classificar_risco(row):
    if pd.isna(row["DATA_ATRIBUICAO_OS"]) or pd.isna(row["DATA_LIMITE_OS"]):
        return "SEM ATRIBUIÇÃO"

    if (
        row["DATA_ATRIBUICAO_OS"].date() == row["DATA_LIMITE_OS"].date()
        and row["DATA_ATRIBUICAO_OS"].hour >= 18
    ):
        return "FORA DO TURNO"

    h = row["horas_ate_prazo"]

    if h > 24:
        return "OK"
    elif h <= 1:
        return "EMERGÊNCIA"
    elif h < 6:
        return "VERMELHO"
    elif h < 12:
        return "AMARELO"
    else:
        return "OK"

df["nivel_risco"] = df.apply(classificar_risco, axis=1)


st.sidebar.header("Filtros")

estado = st.sidebar.multiselect(
    "Estado",
    options=sorted(df["estado"].dropna().unique()),
    default=sorted(df["estado"].dropna().unique())
)

df_f = df[df["estado"].isin(estado)]

regional = st.sidebar.multiselect(
    "Regional",
    options=sorted(df_f["regional"].dropna().unique()),
    default=sorted(df_f["regional"].dropna().unique())
)

df_f = df_f[df_f["regional"].isin(regional)]

base = st.sidebar.multiselect(
    "Base",
    options=sorted(df_f["base"].dropna().unique()),
    default=sorted(df_f["base"].dropna().unique())
)

df_f = df_f[df_f["base"].isin(base)]

sigla = st.sidebar.multiselect(
    "Sigla",
    options=sorted(df_f["sigla"].dropna().unique()),
    default=sorted(df_f["sigla"].dropna().unique())
)

df_f = df_f[df_f["sigla"].isin(sigla)]

grupo_os = st.sidebar.multiselect(
    "Grupo OS",
    options=sorted(df_f["grupo_os"].dropna().unique()),
    default=sorted(df_f["grupo_os"].dropna().unique())
)

df_f = df_f[df_f["grupo_os"].isin(grupo_os)]

tipo_os = st.sidebar.multiselect(
    "Tipo OS",
    options=sorted(df_f["tipo_os"].dropna().unique()),
    default=sorted(df_f["tipo_os"].dropna().unique())
)

df_f = df_f[df_f["tipo_os"].isin(tipo_os)]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "OS analisadas",
    f"{len(df_f):,}".replace(",", ".")
)

col2.metric(
    "Média dias criação → atribuição",
    round(df_f["dias_abertura_atribuicao"].mean(), 2)
)

col3.metric(
    "% FORA DO TURNO",
    round((df_f["nivel_risco"] == "FORA DO TURNO").mean() * 100, 2)
)

col4.metric(
    "% EMERGÊNCIA",
    round((df_f["nivel_risco"] == "EMERGÊNCIA").mean() * 100, 2)
)


bins = [-np.inf, 0, 1, 2, 3, 5, 7, 14, np.inf]
labels = [
    "Mesmo dia",
    "1 dia",
    "2 dias",
    "3 dias",
    "4–5 dias",
    "6–7 dias",
    "8–14 dias",
    ">14 dias"
]

df_f["bin_dias_atribuicao"] = pd.cut(
    df_f["dias_abertura_atribuicao"],
    bins=bins,
    labels=labels
)

bin_chart = (
    alt.Chart(df_f)
    .mark_bar()
    .encode(
        x=alt.X("bin_dias_atribuicao:N", sort=labels, title="Dias até atribuição"),
        y=alt.Y("count()", title="Quantidade de OS"),
        tooltip=["count()"]
    )
)

st.subheader("Distribuição — Tempo até atribuição")
st.altair_chart(bin_chart, use_container_width=True)


risk_chart = (
    alt.Chart(df_f)
    .mark_bar()
    .encode(
        x=alt.X("nivel_risco:N", title="Nível de risco"),
        y=alt.Y("count()", title="Quantidade"),
        tooltip=["count()"]
    )
)

st.subheader("Distribuição por nível de risco")
st.altair_chart(risk_chart, use_container_width=True)


st.subheader("Tabela resumida")

table = (
    df_f
    .groupby(["estado", "regional", "base", "grupo_os", "tipo_os", "nivel_risco"])
    .agg(
        os_qtd=("nivel_risco", "count"),
        media_dias_atribuicao=("dias_abertura_atribuicao", "mean"),
        media_horas_ate_prazo=("horas_ate_prazo", "mean")
    )
    .reset_index()
)

st.dataframe(
    table.sort_values("os_qtd", ascending=False),
    use_container_width=True
)