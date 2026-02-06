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

# =========================
# METRICS
# =========================
df["dias_abertura_atribuicao"] = (
    df["DATA_ATRIBUICAO_OS"] - df["DATA_ABERTURA_OS"]
).dt.total_seconds() / 86400

df["horas_ate_prazo"] = (
    df["DATA_LIMITE_OS"] - df["DATA_ATRIBUICAO_OS"]
).dt.total_seconds() / 3600

# =========================
# RISK CLASSIFICATION
# =========================
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

# =========================
# SIDEBAR — CASCADING FILTERS
# estado → regional → base → sigla → grupo_os → tipo_os
# =========================
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

# =========================
# KPIs
# =========================
c1, c2, c3, c4 = st.columns(4)
"""
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

# =========================
# HISTOGRAM — DIAS ATÉ ATRIBUIÇÃO (NO NULLS + LABELS)
# =========================
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

df_hist = (
    df_bins
    .groupby("bin_dias_atribuicao", dropna=True)
    .size()
    .reset_index(name="qtd")
)

total_hist = df_hist["qtd"].sum()
df_hist["pct"] = df_hist["qtd"] / total_hist * 100
df_hist["label"] = (
    df_hist["qtd"].astype(int).astype(str)
    + " | "
    + df_hist["pct"].round(1).astype(str)
    + "%"
)

hist_bar = (
    alt.Chart(df_hist)
    .mark_bar()
    .encode(
        x=alt.X("bin_dias_atribuicao:N", sort=labels, title="Dias até atribuição"),
        y=alt.Y("qtd:Q", title="Quantidade de OS"),
        tooltip=["qtd", alt.Tooltip("pct:Q", format=".1f")]
    )
)

hist_text = (
    alt.Chart(df_hist)
    .mark_text(
        dy=-8,
        fontSize=11,
        color="white",
        align="center",
        baseline="bottom"
    )
    .encode(
        x=alt.X("bin_dias_atribuicao:N", sort=labels),
        y="qtd:Q",
        text="label:N"
    )
)

st.subheader("Distribuição — Tempo até atribuição")
st.altair_chart(
    (hist_bar + hist_text).configure_view(clip=False),
    use_container_width=True
)
# =========================
# RISK DISTRIBUTION (NO NULLS + LABELS)
# =========================
df_risk = df_f[
    (df_f["nivel_risco"].notna())
    & (df_f["nivel_risco"] != "SEM ATRIBUIÇÃO")
].copy()

df_risk_plot = (
    df_risk
    .groupby("nivel_risco", dropna=True)
    .size()
    .reset_index(name="qtd")
)

total_risk = df_risk_plot["qtd"].sum()
df_risk_plot["pct"] = df_risk_plot["qtd"] / total_risk * 100
df_risk_plot["label"] = (
    df_risk_plot["qtd"].astype(int).astype(str)
    + " | "
    + df_risk_plot["pct"].round(1).astype(str)
    + "%"
)

risk_order = [
    "<=1h",
    "1–6h",
    "6–12h",
    "12–24h",
    ">24h",
    "ATRIB. APÓS 18h (MESMO DIA)"
]

risk_bar = (
    alt.Chart(df_risk_plot)
    .mark_bar()
    .encode(
        x=alt.X("nivel_risco:N", sort=risk_order, title="Janela até o prazo"),
        y=alt.Y("qtd:Q", title="Quantidade de OS"),
        tooltip=["qtd", alt.Tooltip("pct:Q", format=".1f")]
    )
)

risk_text = (
    alt.Chart(df_risk_plot)
    .mark_text(
        dy=-10,
        fontSize=11,
        color="white",
        align="center",
        baseline="bottom"
    )
    .encode(
        x=alt.X("nivel_risco:N", sort=risk_order),
        y="qtd:Q",
        text="label:N"
    )
)

st.subheader("Distribuição — Janela até o prazo")
st.altair_chart(
    (risk_bar + risk_text).configure_view(clip=False),
    use_container_width=True
)
# =========================
# SUMMARY TABLE
# =========================
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