import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Operational & Financial Stress Analysis", layout="wide")

st.title("📊 Análise Operacional e Financeira – Teoria das Filas")
st.markdown(
    """
Este painel avalia **capacidade operacional**, **sobrecarga** e **viabilidade econômica**
com base em tempo real de execução + deslocamento e valores contratuais.
"""
)

# Parameters
JORNADA_HORAS = 8
CUSTO_HORA_EQUIPE = 350
CUSTO_DIA_EQUIPE = JORNADA_HORAS * CUSTO_HORA_EQUIPE

# Load data
@st.cache_data
def load_data():
    return pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

df = load_data()

# Basic preparation
df["DATA"] = pd.to_datetime(df["DATA"])

df["TEMPO_TOTAL_OS"] = df["DURACAO"] + df["DESLOCAMENTO"]

# Daily aggregation per equipe
base = (
    df
    .groupby(["REGIAO", "EQUIPE", "DATA"])
    .agg(
        DEMANDA_HORAS=("TEMPO_TOTAL_OS", "sum"),
        RECEITA_DIA=("PRECO_A_COBRAR", "sum")
    )
    .reset_index()
)

base["CAPACIDADE_HORAS"] = JORNADA_HORAS
base["SOBRECARGA_HORAS"] = base["DEMANDA_HORAS"] - base["CAPACIDADE_HORAS"]
base["DIA_SOBRECARREGADO"] = base["SOBRECARGA_HORAS"] > 0

# Financial layer
base["SALDO_ECONOMICO_DIA"] = base["RECEITA_DIA"] - CUSTO_DIA_EQUIPE
base["DIA_ECONOMICAMENTE_VIAVEL"] = base["SALDO_ECONOMICO_DIA"] > 0

# Regional aggregation
resultado = (
    base
    .groupby("REGIAO")
    .agg(
        MEDIA_DEMANDA_HORAS=("DEMANDA_HORAS", "mean"),
        MEDIA_CAPACIDADE_HORAS=("CAPACIDADE_HORAS", "mean"),
        TAXA_SOBRECARGA=("DIA_SOBRECARREGADO", "mean"),
        SALDO_OPERACIONAL_MEDIO=("SALDO_ECONOMICO_DIA", "mean"),
        TAXA_DIAS_VIAVEIS=("DIA_ECONOMICAMENTE_VIAVEL", "mean")
    )
    .reset_index()
)

# --------------------
# DASHBOARD
# --------------------

st.markdown("## ⏱️ Demanda Média vs Capacidade Média (horas/dia)")

fig1 = px.bar(
    resultado,
    x="REGIAO",
    y=["MEDIA_DEMANDA_HORAS", "MEDIA_CAPACIDADE_HORAS"],
    barmode="group",
    labels={
        "value": "Horas por dia",
        "variable": "Indicador"
    }
)
st.plotly_chart(fig1, use_container_width=True)

st.markdown(
    """
**Como interpretar**  
- Se a **demanda média** se aproxima ou ultrapassa a capacidade, o sistema está sob pressão.
- A capacidade é fixa (8h); a demanda reflete execução real + deslocamento.
"""
)

# --------------------

st.markdown("## 🚨 Taxa de Sobrecarga")

fig2 = px.bar(
    resultado,
    x="REGIAO",
    y="TAXA_SOBRECARGA",
    labels={"TAXA_SOBRECARGA": "Percentual de dias sobrecarregados"}
)
fig2.update_layout(yaxis_tickformat=".0%")
fig2.update_traces(texttemplate="%{y:.0%}", textposition="outside")

st.plotly_chart(fig2, use_container_width=True)

st.markdown(
    """
📌 **Como interpretar:**

- **0–10%** → operação muito confortável  
- **10–30%** → atenção  
- **30–50%** → risco estrutural  
- **>50%** → sistema subdimensionado  

👉 Este é o **termômetro de stress operacional**.
"""
)

# --------------------

st.markdown("## 💰 Saldo Operacional Médio (R$/dia)")

fig3 = px.bar(
    resultado,
    x="REGIAO",
    y="SALDO_OPERACIONAL_MEDIO",
    color="SALDO_OPERACIONAL_MEDIO",
    color_continuous_scale="RdYlGn",
    labels={"SALDO_OPERACIONAL_MEDIO": "R$ por dia"}
)
fig3.update_layout(coloraxis_showscale=False)
fig3.update_traces(texttemplate="R$ %{y:,.0f}", textposition="outside")

st.plotly_chart(fig3, use_container_width=True)

st.markdown(
    """
**O que significa o saldo operacional?**

- Representa a diferença entre **receita diária executada** e o **custo cheio de uma equipe (R$ 2.800/dia)**.
- Valor positivo indica que **a operação paga uma equipe adicional**.
- Valor negativo indica que **mobilização ampliaria prejuízo**, mesmo havendo demanda.
"""
)

# --------------------

st.markdown("## 📈 Taxa de Dias Economicamente Viáveis")

fig4 = px.bar(
    resultado,
    x="REGIAO",
    y="TAXA_DIAS_VIAVEIS",
    labels={"TAXA_DIAS_VIAVEIS": "Percentual de dias viáveis"}
)
fig4.update_layout(yaxis_tickformat=".0%")
fig4.update_traces(texttemplate="%{y:.0%}", textposition="outside")

st.plotly_chart(fig4, use_container_width=True)

st.markdown(
    """
**Leitura final**  
- Alta sobrecarga + baixa viabilidade → gargalo operacional sem densidade econômica  
- Alta sobrecarga + alta viabilidade → forte candidato à mobilização  
- Baixa sobrecarga → ajuste fino, não expansão
"""
)
