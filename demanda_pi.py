import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Operational & Economic Analysis", layout="wide")

JORNADA_DIARIA_PADRAO = 8.0
CUSTO_HORA_EQUIPE = 350.0

@st.cache_data
def load_data():
    return pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

def hhmm_to_hours(col):
    return (
        pd.to_timedelta(col, errors="coerce")
        .dt.total_seconds()
        .div(3600)
        .fillna(0)
    )

df = load_data()

df["DURACAO_HORAS"] = hhmm_to_hours(df["DURACAO"])
df["DESLOCAMENTO_HORAS"] = hhmm_to_hours(df["DESLOCAMENTO"])
df["DEMANDA_HORAS"] = df["DURACAO_HORAS"] + df["DESLOCAMENTO_HORAS"]

df = df[df["DEMANDA_HORAS"] > 0]

df["RECEITA_HORA"] = df["PRECO_A_COBRAR"] / df["DEMANDA_HORAS"]

base_dia = (
    df.groupby(["REGIAO", "DATA", "EQUIPE"])
      .agg(
          DEMANDA_HORAS=("DEMANDA_HORAS", "sum"),
          RECEITA_TOTAL=("PRECO_A_COBRAR", "sum"),
          RECEITA_HORA_MEDIA=("RECEITA_HORA", "mean")
      )
      .reset_index()
)

base_dia["CAPACIDADE_HORAS"] = JORNADA_DIARIA_PADRAO
base_dia["SOBRECARGA_HORAS"] = base_dia["DEMANDA_HORAS"] - base_dia["CAPACIDADE_HORAS"]
base_dia["SOBRECARGA_FLAG"] = base_dia["SOBRECARGA_HORAS"] > 0

resultado = (
    base_dia.groupby("REGIAO")
    .agg(
        MEDIA_DEMANDA_HORAS=("DEMANDA_HORAS", "mean"),
        MEDIA_CAPACIDADE_HORAS=("CAPACIDADE_HORAS", "mean"),
        TAXA_SOBRECARGA=("SOBRECARGA_FLAG", "mean"),
        SALDO_OPERACIONAL_MEDIO=("SOBRECARGA_HORAS", "mean"),
        RECEITA_HORA_MEDIA=("RECEITA_HORA_MEDIA", "mean")
    )
    .reset_index()
)

resultado["CUSTO_HORA"] = CUSTO_HORA_EQUIPE
resultado["MARGEM_HORA"] = resultado["RECEITA_HORA_MEDIA"] - resultado["CUSTO_HORA"]
resultado["VIAVEL_ECONOMICAMENTE"] = resultado["MARGEM_HORA"] > 0

st.title("📊 Operational & Economic Stress Analysis")
st.caption("Time-based demand, contractual capacity, economic realism")

col1, col2 = st.columns(2)

with col1:
    fig1 = px.bar(
        resultado,
        x="REGIAO",
        y="TAXA_SOBRECARGA",
        text="TAXA_SOBRECARGA",
        title="Taxa de Sobrecarga"
    )
    fig1.update_layout(yaxis_tickformat=".0%")
    fig1.update_traces(texttemplate="%{text:.1%}", textposition="outside")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.bar(
        resultado,
        x="REGIAO",
        y=["MEDIA_DEMANDA_HORAS", "MEDIA_CAPACIDADE_HORAS"],
        barmode="group",
        title="Demanda vs Capacidade (horas/dia)"
    )
    st.plotly_chart(fig2, use_container_width=True)

fig3 = px.bar(
    resultado,
    x="REGIAO",
    y="SALDO_OPERACIONAL_MEDIO",
    color="SALDO_OPERACIONAL_MEDIO",
    title="Saldo Operacional Médio (horas)",
    color_continuous_scale="RdYlGn"
)
fig3.update_layout(coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

fig4 = px.bar(
    resultado,
    x="REGIAO",
    y="MARGEM_HORA",
    color="VIAVEL_ECONOMICAMENTE",
    title="Margem Econômica por Hora",
    text="MARGEM_HORA"
)
fig4.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
st.plotly_chart(fig4, use_container_width=True)

st.dataframe(resultado, use_container_width=True)
