import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    layout="wide",
    page_title="Distribuição do TMA e UPS"
)

@st.cache_data
def importar_excel():
    return pd.read_excel("v_desvio_padrao_2025.xlsx")

df = importar_excel()

st.title("Distribuição do Tempo Médio de Atendimento e Produtividade (UPS)")

st.markdown("""
**Como interpretar os gráficos:**  
- Boxplots mostram a distribuição dos indicadores  
- A linha central representa a mediana  
- Maior dispersão indica maior variabilidade operacional  
- UPS Efetiva reflete o esforço real (tempo)  
- UPS BID reflete a complexidade real dos serviços executados  
""")

# =========================
# FILTRO TIPO OS
# =========================
lista_tipo_os = sorted(df['tipo_os'].dropna().unique().tolist())
lista_tipo_os.insert(0, "NR's")

tipo_os_selecionado = st.selectbox(
    "Selecione o tipo de OS",
    lista_tipo_os
)

st.caption(
    "**NR's** refere-se aos tipos **COL**, **IND** e **IMPROD**.\n"
    "**RC** refere-se à reativação sem instalação de medidor e ramal."
)

if tipo_os_selecionado == "NR's":
    df_filtrado = df[df['tipo_os'].isin(['NR IMPROD', 'NR IND', 'NR COL'])].copy()
else:
    df_filtrado = df[df['tipo_os'] == tipo_os_selecionado].copy()

# =========================
# FILTRO REGIONAL (NOVO)
# =========================
lista_regional = sorted(df_filtrado['regional_nome'].dropna().unique().tolist())

regional_selecionada = st.multiselect(
    "Selecione a Regional (opcional)",
    lista_regional
)

# =========================
# DEFINIÇÃO DINÂMICA DO EIXO X
# =========================
if regional_selecionada:
    df_filtrado = df_filtrado[df_filtrado['regional_nome'].isin(regional_selecionada)]
    eixo_x = "BASE"
    label_x = "Base"
else:
    eixo_x = "regional_nome"
    label_x = "Regional"

# =========================
# FUNÇÃO DE BOXPLOT DINÂMICO
# =========================
def boxplot_dinamico(df, coluna, titulo, ylabel):
    dados = (
        df.groupby(eixo_x)[coluna]
        .apply(list)
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    boxplot = ax.boxplot(
        dados.values,
        labels=dados.index.tolist(),
        patch_artist=True,
        boxprops=dict(alpha=0.5),
        medianprops=dict(linewidth=2)
    )

    for mediana in boxplot['medians']:
        x, y = mediana.get_xydata()[1]
        ax.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=9)

    ax.set_title(titulo)
    ax.set_xlabel(label_x)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.xticks(rotation=45)

    st.pyplot(fig)

# =========================
# TMA BOXPLOTS
# =========================
st.subheader("Distribuição dos Tempos")

boxplot_dinamico(
    df_filtrado,
    "media",
    f"TMA – Tempo Médio de Atendimento ({tipo_os_selecionado})",
    "Horas"
)

boxplot_dinamico(
    df_filtrado,
    "media_duracao",
    f"Duração do Atendimento ({tipo_os_selecionado})",
    "Horas"
)

boxplot_dinamico(
    df_filtrado,
    "media_deslocamento",
    f"Tempo de Deslocamento ({tipo_os_selecionado})",
    "Horas"
)

# =========================
# UPS BOXPLOTS (NOVO)
# =========================
st.markdown("---")
st.subheader("Distribuição de Produtividade (UPS)")

boxplot_dinamico(
    df_filtrado,
    "ups_realizada",
    f"UPS Realizada ({tipo_os_selecionado})",
    "UPS"
)

boxplot_dinamico(
    df_filtrado,
    "ups_efetiva",
    f"UPS Efetiva (baseado em TMA) ({tipo_os_selecionado})",
    "UPS"
)

boxplot_dinamico(
    df_filtrado,
    "ups_bid",
    f"UPS BID (complexidade real) ({tipo_os_selecionado})",
    "UPS"
)

# =========================
# SCATTER PLOT (🔥 PRINCIPAL)
# =========================
st.markdown("---")
st.subheader("Relação entre UPS Realizada vs UPS Efetiva")

fig, ax = plt.subplots(figsize=(8, 6))

ax.scatter(
    df_filtrado["ups_realizada"],
    df_filtrado["ups_efetiva"],
    alpha=0.6
)

# Linha de referência (perfeita calibração)
max_val = max(
    df_filtrado["ups_realizada"].max(),
    df_filtrado["ups_efetiva"].max()
)

ax.plot([0, max_val], [0, max_val], linestyle="--")

ax.set_xlabel("UPS Realizada")
ax.set_ylabel("UPS Efetiva")
ax.set_title("Desvio do Modelo de Produtividade")
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)