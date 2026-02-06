import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.set_page_config(layout="wide")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_parquet("tempo_atribuicao.parquet")

    for col in [
        "DATA_ABERTURA_OS",
        "DATA_ATRIBUICAO_OS",
        "DATA_LIMITE_OS",
    ]:
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
        return "ATRIB. APÓS 18h (MESMO DIA)"

    h = row["horas_ate_prazo"]

    if h > 24:
        return ">24h"
    elif h <= 1:
        return "<=1h"
    elif h < 6:
        return "1–6h"
    elif h < 12:
        return "6–12h"
    else:
        return "12–24h"

df["nivel_risco"] = df.apply(classificar_risco, axis=1)


st.sidebar.header("Filtros")

estado = st.sidebar.multiselect(
    "Estado",
    sorted(df["estado"].dropna().unique()),
    default=sorted(df["estado"].dropna().unique())
)
df_f = df[df["estado"].isin(estado)]

regional = st.sidebar.multiselect(
    "Regional",
    sorted(df_f["regional"].dropna().unique()),
    default=sorted(df_f["regional"].dropna().unique())
)
df_f = df_f[df_f["regional"].isin(regional)]

base = st.sidebar.multiselect(
    "Base",
    sorted(df_f["base"].dropna().unique()),
    default=sorted(df_f["base"].dropna().unique())
)
df_f = df_f[df_f["base"].isin(base)]

sigla = st.sidebar.multiselect(
    "Sigla",
    sorted(df_f["sigla"].dropna().unique()),
    default=sorted(df_f["sigla"].dropna().unique())
)
df_f = df_f[df_f["sigla"].isin(sigla)]

grupo_os = st.sidebar.multiselect(
    "Grupo OS",
    sorted(df_f["grupo_os"].dropna().unique()),
    default=sorted(df_f["grupo_os"].dropna().unique())
)
df_f = df_f[df_f["grupo_os"].isin(grupo_os)]

tipo_os = st.sidebar.multiselect(
    "Tipo OS",
    sorted(df_f["tipo_os"].dropna().unique()),
    default=sorted(df_f["tipo_os"].dropna().unique())
)
df_f = df_f[df_f["tipo_os"].isin(tipo_os)]

"""
c1, c2, c3, c4 = st.columns(4)

c1.metric("OS analisadas", f"{len(df_f):,}".replace(",", "."))
c2.metric(
    "Média dias criação → atribuição",
    round(df_f["dias_abertura_atribuicao"].mean(), 2)
)
c3.metric(
    "% Atrib. após 18h",
    round((df_f["nivel_risco"] == "ATRIB. APÓS 18h (MESMO DIA)").mean() * 100, 2)
)
c4.metric(
    "% <=1h",
    round((df_f["nivel_risco"] == "<=1h").mean() * 100, 2)
)
"""

df_bins = df_f[df_f["dias_abertura_atribuicao"].notna()].copy()

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

df_bins["bin_dias_atribuicao"] = pd.cut(
    df_bins["dias_abertura_atribuicao"],
    bins=bins,
    labels=labels
)

hist_chart = (
    alt.Chart(df_bins)
    .mark_bar()
    .encode(
        x=alt.X("bin_dias_atribuicao:N", sort=labels, title="Dias até atribuição"),
        y=alt.Y("count()", title="Quantidade de OS"),
        tooltip=["count()"]
    )
)

st.subheader("Distribuição — Tempo até atribuição")
st.altair_chart(hist_chart, use_container_width=True)


df_risk = df_f[
    (df_f["nivel_risco"].notna())
    & (df_f["nivel_risco"] != "SEM ATRIBUIÇÃO")
].copy()

risk_order = [
    "<=1h",
    "1–6h",
    "6–12h",
    "12–24h",
    ">24h",
    "ATRIB. APÓS 18h (MESMO DIA)"
]

risk_chart = (
    alt.Chart(df_risk)
    .mark_bar()
    .encode(
        x=alt.X(
            "nivel_risco:N",
            sort=risk_order,
            title="Janela até o prazo"
        ),
        y=alt.Y("count()", title="Quantidade de OS"),
        tooltip=["count()"]
    )
)

st.subheader("Distribuição — Janela até o prazo")
st.altair_chart(risk_chart, use_container_width=True)

st.subheader("Tabela resumida")

table = (
    df_f
    .groupby(
        ["estado", "regional", "base", "grupo_os", "tipo_os", "nivel_risco"],
        dropna=True
    )
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