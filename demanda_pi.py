import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Simulação operacional",
    layout="wide"
)

st.title("Diagnóstico Operacional e Financeiro")
st.subheader(
    "Premissas: demanda em tempo real, capacidade efetiva e viabilidade econômica"
)

modo_demanda = st.radio(
    "Selecione o nível de análise:",
    ["DEMANDA POR EQUIPES", "DEMANDA POR REGIÕES"],
    horizontal=True
)

if modo_demanda == "DEMANDA POR EQUIPES":
    arquivo_dados = "V_TEORIA_DAS_FILAS.xlsx"
    descricao_modo = "🔍 **Demanda por Equipes**"
else:
    arquivo_dados = "V_TEORIA_DAS_FILAS.xlsx"
    descricao_modo = "🌍 **Demanda por Regiões**"

st.info(descricao_modo)

st.sidebar.header("🎛️ Parâmetros do Modelo")

cenario = st.sidebar.selectbox(
    "Cenário operacional:",
    ["A – Conservador", "B – Moderado", "C – Agressivo"]
)

fator_cenario = {
    "A – Conservador": 1.00,
    "B – Moderado": 0.90,
    "C – Agressivo": 0.80
}[cenario]

margem_seguranca = st.sidebar.slider(
    "Margem de segurança (%)",
    0.70, 0.95, 0.90, 0.05
)

limiar_sobrecarga = st.sidebar.slider(
    "Limiar de sobrecarga (%)",
    0.10, 0.80, 0.30, 0.05
)

CUSTO_HORA_EQUIPE = 350.0
JORNADA_DIARIA_PADRAO = 8.0

@st.cache_data
def carregar_dados(caminho):
    df = pd.read_excel(caminho)

    def hhmm_para_horas(valor):
        if pd.isna(valor):
            return 0.0
        partes = str(valor).split(":")
        partes = [int(p) for p in partes]
        if len(partes) == 2:
            h, m = partes
            s = 0
        else:
            h, m, s = partes
        return h + m/60 + s/3600

    df["DURACAO_HORAS"] = df["DURACAO"].apply(hhmm_para_horas)
    df["DESLOCAMENTO_HORAS"] = df["DESLOCAMENTO"].apply(hhmm_para_horas)

    return df

df = carregar_dados(arquivo_dados)

# ======================
# OPERATIONAL LAYER
# ======================

df_dia = (
    df.groupby(["REGIAO", "DATA"])
      .agg(
          DEMANDA_HORAS_DIA=(
              "DURACAO_HORAS",
              lambda x: (
                  x[df.loc[x.index, "TIPO_OS"] != "INDISP"].sum() +
                  df.loc[x.index, "DESLOCAMENTO_HORAS"][df.loc[x.index, "TIPO_OS"] != "INDISP"].sum()
              )
          ),
          INDISP_HORAS=("DURACAO_HORAS",
                        lambda x: x[df.loc[x.index, "TIPO_OS"] == "INDISP"].sum())
      )
      .reset_index()
)

df_dia["CAPACIDADE_DIA_HORAS"] = (
    JORNADA_DIARIA_PADRAO - df_dia["INDISP_HORAS"]
).clip(lower=0) * fator_cenario

df_dia["SALDO_HORAS"] = df_dia["CAPACIDADE_DIA_HORAS"] - df_dia["DEMANDA_HORAS_DIA"]
df_dia["DIA_SOBRECARREGADO"] = df_dia["SALDO_HORAS"] < 0

# ======================
# FINANCIAL LAYER
# ======================

df_exec = df[df["TIPO_OS"] != "INDISP"].copy()
df_exec["TEMPO_TOTAL_HORAS"] = df_exec["DURACAO_HORAS"] + df_exec["DESLOCAMENTO_HORAS"]

financeiro = (
    df_exec.groupby("REGIAO")
    .agg(
        RECEITA_TOTAL=("PRECO_A_COBRAR", "sum"),
        HORAS_EXECUTADAS=("TEMPO_TOTAL_HORAS", "sum")
    )
    .reset_index()
)

financeiro["RECEITA_HORA_REAL"] = (
    financeiro["RECEITA_TOTAL"] / financeiro["HORAS_EXECUTADAS"]
)

financeiro["MARGEM_HORA"] = (
    financeiro["RECEITA_HORA_REAL"] - CUSTO_HORA_EQUIPE
)

# ======================
# CONSOLIDATION
# ======================

resultado = (
    df_dia.groupby("REGIAO")
    .agg(
        MEDIA_DEMANDA_HORAS=("DEMANDA_HORAS_DIA", "mean"),
        MEDIA_CAPACIDADE_HORAS=("CAPACIDADE_DIA_HORAS", "mean"),
        TAXA_SOBRECARGA=("DIA_SOBRECARREGADO", "mean"),
        SALDO_MEDIO_HORAS=("SALDO_HORAS", "mean")
    )
    .reset_index()
)

resultado = resultado.merge(financeiro, on="REGIAO", how="left")

resultado["RECOMENDACAO"] = np.where(
    (resultado["SALDO_MEDIO_HORAS"] < 0) &
    (resultado["TAXA_SOBRECARGA"] > limiar_sobrecarga) &
    (resultado["MARGEM_HORA"] > 0),
    "MOBILIZAR",
    "NAO_MOBILIZAR"
)

# ======================
# OUTPUT
# ======================

st.markdown("## Diagnóstico Integrado")

st.dataframe(
    resultado.style.format({
        "MEDIA_DEMANDA_HORAS": "{:.2f}",
        "MEDIA_CAPACIDADE_HORAS": "{:.2f}",
        "SALDO_MEDIO_HORAS": "{:.2f}",
        "TAXA_SOBRECARGA": "{:.1%}",
        "RECEITA_HORA_REAL": "R$ {:.2f}",
        "MARGEM_HORA": "R$ {:.2f}"
    }),
    use_container_width=True
)
