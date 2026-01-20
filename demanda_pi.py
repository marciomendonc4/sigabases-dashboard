import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Simulação operacional",
    layout="wide"
)

st.title("Diagnóstico Operacional")
st.subheader(
    "Premissas: Demanda, capacidade efetiva e indisponibilidade operacional"
)



modo_demanda = st.radio(
    "Selecione o nível de análise:",
    ["DEMANDA POR EQUIPES", "DEMANDA POR REGIÕES"],
    horizontal=True
)

if modo_demanda == "DEMANDA POR EQUIPES":
    arquivo_dados = "V_TEORIA_DAS_FILAS.xlsx"
    descricao_modo = (
        "🔍 **Demanda por Equipes**  \n"
        "Análise na capacidade operacional das equipes."
    )
else:
    arquivo_dados = "V_TEORIA_DAS_FILAS_REGIAO.xlsx"
    descricao_modo = (
        "🌍 **Demanda das Regiões**  \n"
        "Análise baseada na demanda agregada regional, com visão estratégica."
    )

st.info(descricao_modo)


st.sidebar.header("🎛️ Parâmetros do Modelo")

cenario = st.sidebar.selectbox(
    "Cenário operacional:",
    ["A – Conservador", "B – Moderado", "C – Agressivo"]
)

fator_cenario_padrao = {
    "A – Conservador": 1.00,
    "B – Moderado": 0.90,
    "C – Agressivo": 0.80
}

fator_capacidade = st.sidebar.slider(
    "Fator de capacidade do cenário",
    min_value=0.50,
    max_value=1.00,
    value=fator_cenario_padrao[cenario],
    step=0.05
)

margem_seguranca = st.sidebar.slider(
    "Margem de segurança (%)",
    min_value=0.70,
    max_value=0.95,
    value=0.90,
    step=0.05
)

limiar_sobrecarga = st.sidebar.slider(
    "Limiar de dias sobrecarregados para mobilização (%)",
    min_value=0.10,
    max_value=0.80,
    value=0.30,
    step=0.05
)

descricao_cenario = {
    "A – Conservador": (
        "🟢 **Cenário A – Conservador**  \n"
        "Capacidade real medida, considerando apenas indisponibilidades lançadas."
    ),
    "B – Moderado": (
        "🟡 **Cenário B – Moderado**  \n"
        "Inclui margem de atrasos, deslocamentos e variabilidade operacional."
    ),
    "C – Agressivo": (
        "🔴 **Cenário C – Agressivo**  \n"
        "Demanda contínua e redução de eficiência operacional."
    )
}

st.markdown("###Cenário em Análise")
st.info(descricao_cenario[cenario])


@st.cache_data
def carregar_dados(caminho):
    df = pd.read_excel(caminho)

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

df = carregar_dados(arquivo_dados)



df_dia = (
    df.groupby(["REGIAO", "DATA"])
      .agg(
          DEMANDA_DIA=("TIPO_OS", lambda x: (x != "INDISP").sum()),
          INDISP_HORAS=("DURACAO_HORAS", lambda x: x[df.loc[x.index, "TIPO_OS"] == "INDISP"].sum())
      )
      .reset_index()
)
JORNADA_DIARIA_PADRAO = 8.0

df_dia["CAPACIDADE_DIA"] = (
    JORNADA_DIARIA_PADRAO - df_dia["INDISP_HORAS"]
).clip(lower=0)

df_dia["CAPACIDADE_DIA"] *= fator_capacidade
df_dia["SALDO_DIA"] = df_dia["CAPACIDADE_DIA"] - df_dia["DEMANDA_DIA"]
df_dia["DIA_SOBRECARREGADO"] = df_dia["SALDO_DIA"] < 0



resultado = (
    df_dia.groupby("REGIAO")
    .agg(
        MEDIA_DEMANDA=("DEMANDA_DIA", "mean"),
        MEDIA_CAPACIDADE=("CAPACIDADE_DIA", "mean"),
        TAXA_SOBRECARGA=("DIA_SOBRECARREGADO", "mean"),
        SALDO_MEDIO=("SALDO_DIA", "mean"),
        DIAS_ANALISADOS=("DATA", "nunique")
    )
    .reset_index()
)

resultado["CAPACIDADE_SEGURA"] = resultado["MEDIA_CAPACIDADE"] * margem_seguranca

resultado["RECOMENDACAO"] = np.where(
    (resultado["SALDO_MEDIO"] < 0) &
    (resultado["TAXA_SOBRECARGA"] > limiar_sobrecarga),
    "MOBILIZAR",
    "NAO_MOBILIZAR"
)


st.sidebar.header("Regiões")
regioes = st.sidebar.multiselect(
    "Selecione as regiões:",
    resultado["REGIAO"].unique(),
    default=resultado["REGIAO"].unique()
)

resultado = resultado[resultado["REGIAO"].isin(regioes)]

#princip indicadores

st.markdown("## 📌 Indicadores Consolidados")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Demanda Média (OS/dia)", round(resultado["MEDIA_DEMANDA"].mean(), 2))
c2.metric("Capacidade Média (OS/dia)", round(resultado["MEDIA_CAPACIDADE"].mean(), 2))
c3.metric("Saldo Médio", round(resultado["SALDO_MEDIO"].mean(), 2))
c4.metric(
    "Taxa Média de Sobrecarga",
    f"{resultado['TAXA_SOBRECARGA'].mean()*100:.1f}%"
)

#resumo

st.markdown("## Diagnóstico por Região")

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



st.markdown("## Demanda x Capacidade")
fig1 = px.bar(
    resultado,
    x="REGIAO",
    y=["MEDIA_DEMANDA", "MEDIA_CAPACIDADE"],
    barmode="group",
    labels={"value": "OS por dia", "variable": "Indicador"}
)
fig1.update_traces(
    texttemplate="%{text:.2f}",
    textposition="outside"
)
st.plotly_chart(fig1, use_container_width=True)


st.markdown("## Saldo Operacional Médio")

fig2 = px.bar(
    resultado,
    x="REGIAO",
    y="SALDO_MEDIO",
    color="SALDO_MEDIO",
    color_continuous_scale="RdYlGn",
    text="SALDO_MEDIO"
)

fig2.update_layout(coloraxis_showscale=False)

fig2.update_traces(
    texttemplate="%{text:.2f}",
    textposition="outside"
)

st.plotly_chart(fig2, use_container_width=True)


st.markdown(
    """
📌 **Saldo operacional refere-se ao GAP entre a capacidade operacional e demanda efetiva.**

- **Saldo > 0** → capacidade média supera a demanda (ociosidade operacional)  
- **Saldo ≈ 0** → sistema rodando no limite da capacidade operacional 
- **Saldo < 0** → demanda média maior que a capacidade

*Esse indicador representa o “fôlego” diário da operação.*
""",
    unsafe_allow_html=False
)


st.markdown("## Taxa de Sobrecarga")
fig3 = px.bar(
    resultado,
    x="REGIAO",
    y="TAXA_SOBRECARGA",
    text="TAXA_SOBRECARGA"
)
fig3.update_layout(yaxis_tickformat=".0%")
fig3.update_traces(
    texttemplate="%{text:.2f}",
    textposition="outside"
)
st.plotly_chart(fig3, use_container_width=True)

st.markdown(
    """
📌 **Como interpretar:**

- **0–10%** → operação confortável  
- **10–30%** → atenção  
- **30–50%** → risco estrutural  
- **>50%** → sistema subdimensionado  

*Indicador do stress da operação - alta ou baixa demanda operacional.*
""",
    unsafe_allow_html=False
)



st.markdown("## Resultado")

for _, row in resultado.iterrows():
    if row["RECOMENDACAO"] == "MOBILIZAR":
        st.warning(
            f"🔴 **{row['REGIAO']}** apresenta sobrecarga estrutural. "
            f"Saldo médio de {row['SALDO_MEDIO']:.2f} OS/dia "
            f"e sobrecarga em {row['TAXA_SOBRECARGA']:.1%} dos dias."
        )
    else:
        st.success(
            f"🟢 **{row['REGIAO']}** opera com capacidade suficiente no cenário atual."
        )

st.markdown("---")
st.caption(
    "Modelo baseado em teoria das filas aplicada à operação real, "
    "com suporte a múltiplos níveis de demanda e simulação de cenários."
)
