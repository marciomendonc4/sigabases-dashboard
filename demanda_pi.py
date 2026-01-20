import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Diagnóstico Operacional - Teoria das Filas",
    layout="wide"
)

st.title("📊 Diagnóstico Operacional por Região")
st.subheader(
    "Análise de demanda, capacidade real das equipes e indisponibilidade operacional"
)

# ======================
# Sidebar — Cenários
# ======================

st.sidebar.header("🎛️ Configurações de Análise")

cenario = st.sidebar.selectbox(
    "Selecione o cenário:",
    ["A – Conservador", "B – Moderado", "C – Agressivo"]
)

if cenario.startswith("A"):
    fator_capacidade = 1.00
    descricao_cenario = (
        "🟢 **Cenário A – Conservador**  \n"
        "Considera apenas a indisponibilidade registrada (INDISP). "
        "Representa a capacidade operacional real observada."
    )

elif cenario.startswith("B"):
    fator_capacidade = 0.90
    descricao_cenario = (
        "🟡 **Cenário B – Moderado**  \n"
        "Além da indisponibilidade registrada, aplica uma margem adicional "
        "para atrasos, deslocamentos e variabilidade operacional."
    )

else:
    fator_capacidade = 0.80
    descricao_cenario = (
        "🔴 **Cenário C – Agressivo**  \n"
        "Assume pressão operacional contínua, com redução de eficiência "
        "devido a sobrecarga, fadiga e retrabalho."
    )

st.markdown("### 🧭 Cenário em Análise")
st.info(descricao_cenario)

# ======================
# Carregamento dos dados
# ======================

@st.cache_data
def carregar_dados():
    df = pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

    def duracao_para_horas(valor):
        if pd.isna(valor):
            return 0.0
        partes = str(valor).split(":")
        if len(partes) == 2:
            h, m = partes
            s = 0
        elif len(partes) == 3:
            h, m, s = partes
        else:
            return 0.0
        return int(h) + int(m)/60 + int(s)/3600

    df["DURACAO_HORAS"] = df["DURACAO"].apply(duracao_para_horas)

    return df

df = carregar_dados()

# ======================
# Agregações principais
# ======================

df_regional = (
    df.groupby(["REGIAO", "DATA"])
      .agg(
          DEMANDA_DIA=("TIPO_OS", lambda x: (x != "INDISP").sum()),
          INDISP_HORAS=("DURACAO_HORAS", lambda x: x[df.loc[x.index, "TIPO_OS"] == "INDISP"].sum())
      )
      .reset_index()
)

JORNADA_DIARIA_PADRAO = 8.0

df_regional["CAPACIDADE_DIA"] = JORNADA_DIARIA_PADRAO - df_regional["INDISP_HORAS"]
df_regional["CAPACIDADE_DIA"] = df_regional["CAPACIDADE_DIA"].clip(lower=0)
df_regional["CAPACIDADE_DIA"] *= fator_capacidade

df_regional["SALDO_DIA"] = df_regional["CAPACIDADE_DIA"] - df_regional["DEMANDA_DIA"]
df_regional["DIA_SOBRECARREGADO"] = df_regional["SALDO_DIA"] < 0

# ======================
# Diagnóstico regional
# ======================

resultado = (
    df_regional.groupby("REGIAO")
    .agg(
        MEDIA_DEMANDA=("DEMANDA_DIA", "mean"),
        MEDIA_CAPACIDADE=("CAPACIDADE_DIA", "mean"),
        TAXA_SOBRECARGA=("DIA_SOBRECARREGADO", "mean"),
        SALDO_MEDIO=("SALDO_DIA", "mean"),
        DIAS_ANALISADOS=("DATA", "nunique")
    )
    .reset_index()
)

resultado["CAPACIDADE_SEGURA"] = resultado["MEDIA_CAPACIDADE"] * 0.9
resultado["RECOMENDACAO"] = np.where(
    resultado["SALDO_MEDIO"] < 0, "MOBILIZAR", "NAO_MOBILIZAR"
)

# ======================
# Filtro por região
# ======================

st.sidebar.header("📍 Filtro Regional")
regioes = st.sidebar.multiselect(
    "Selecione as regiões:",
    resultado["REGIAO"].unique(),
    default=resultado["REGIAO"].unique()
)

resultado = resultado[resultado["REGIAO"].isin(regioes)]

# ======================
# Indicadores gerais
# ======================

st.markdown("## 📌 Indicadores Consolidados")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Demanda Média (OS/dia)", round(resultado["MEDIA_DEMANDA"].mean(), 2))
c2.metric("Capacidade Média (OS/dia)", round(resultado["MEDIA_CAPACIDADE"].mean(), 2))
c3.metric("Saldo Médio", round(resultado["SALDO_MEDIO"].mean(), 2))
c4.metric(
    "Taxa Média de Sobrecarga",
    f"{resultado['TAXA_SOBRECARGA'].mean()*100:.1f}%"
)

# ======================
# Tabela resumo
# ======================

st.markdown("## 📋 Diagnóstico por Região")

st.dataframe(
    resultado.style.format({
        "MEDIA_DEMANDA": "{:.2f}",
        "MEDIA_CAPACIDADE": "{:.2f}",
        "CAPACIDADE_SEGURA": "{:.2f}",
        "SALDO_MEDIO": "{:.2f}",
        "TAXA_SOBRECARGA": "{:.1%}"
    }),
    use_container_width=True
)

# ======================
# Gráficos
# ======================

st.markdown("## ⚖️ Demanda x Capacidade Média")
st.caption("Comparação entre volume médio diário de OS e capacidade operacional efetiva.")

fig1 = px.bar(
    resultado,
    x="REGIAO",
    y=["MEDIA_DEMANDA", "MEDIA_CAPACIDADE"],
    barmode="group",
    labels={"value": "OS por dia", "variable": "Indicador"}
)
fig1.update_layout(title="Demanda Média vs Capacidade Média por Região")
st.plotly_chart(fig1, use_container_width=True)

st.markdown("## 📉 Saldo Operacional Médio")
st.caption("Valores negativos indicam déficit estrutural de capacidade.")

fig2 = px.bar(
    resultado,
    x="REGIAO",
    y="SALDO_MEDIO",
    color="SALDO_MEDIO",
    color_continuous_scale="RdYlGn"
)
fig2.update_layout(title="Saldo Médio por Região", coloraxis_showscale=False)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("## 🚨 Frequência de Sobrecarga")
st.caption("Percentual de dias em que a demanda superou a capacidade disponível.")

fig3 = px.bar(
    resultado,
    x="REGIAO",
    y="TAXA_SOBRECARGA"
)
fig3.update_layout(
    title="Taxa de Sobrecarga por Região",
    yaxis_tickformat=".0%"
)
st.plotly_chart(fig3, use_container_width=True)

# ======================
# Interpretação automática
# ======================

st.markdown("## 🧠 Interpretação Automática")

for _, row in resultado.iterrows():
    if row["RECOMENDACAO"] == "MOBILIZAR":
        st.warning(
            f"🔴 **{row['REGIAO']}** apresenta sobrecarga estrutural. "
            f"Saldo médio de {row['SALDO_MEDIO']:.2f} OS/dia "
            f"e sobrecarga em {row['TAXA_SOBRECARGA']:.1%} dos dias."
        )
    else:
        st.success(
            f"🟢 **{row['REGIAO']}** opera com folga operacional consistente."
        )

st.markdown("---")
st.caption(
    "Modelo baseado em teoria das filas aplicada à operação real, "
    "considerando indisponibilidades e cenários de risco operacional."
)
