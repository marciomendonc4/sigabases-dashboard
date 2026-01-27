import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(
    layout="wide",
    page_title="Distribuição do TMA"
)

@st.cache_data
def importar_excel():
    return pd.read_excel("v_desvio_padrao_2025.xlsx")

df = importar_excel()

st.title("Distribuição do Tempo Médio de Atendimento")
st.markdown("""
**Como interpretar os gráficos:**  
Cada caixa representa a distribuição do tempo médio por regional.  
A linha central indica a mediana.  
Caixas maiores indicam maior variabilidade operacional.
""")

lista_tipo_os = sorted(df['tipo_os'].dropna().unique().tolist())
lista_tipo_os.insert(0, "NR's")

tipo_os_selecionado = st.selectbox(
    "Selecione o tipo de OS",
    lista_tipo_os
)

st.caption(
    "**NR's** refere-se aos tipos **COL**, **IND** e **IMPROD**.\n"
    "**RC** refere-se à **reativação sem instalação de medidor e ramal**."
)

if tipo_os_selecionado == "NR's":
    df_filtrado = df[df['tipo_os'].isin(['NR IMPROD', 'NR IND', 'NR COL'])].copy()
else:
    df_filtrado = df[df['tipo_os'] == tipo_os_selecionado].copy()

st.subheader("Distribuição dos Tempos por Regional")

def boxplot_por_regional(df, coluna, titulo, ylabel):
    dados = (
        df.groupby('regional_nome')[coluna]
        .apply(list)
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    boxplot = ax.boxplot(
        dados.values,
        labels=dados.index.tolist(),
        patch_artist=True,
        boxprops=dict(facecolor="#1f77b4", alpha=0.5),
        medianprops=dict(color="black", linewidth=2)
    )

    for mediana in boxplot['medians']:
        x, y = mediana.get_xydata()[1]
        ax.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=9)

    ax.set_title(titulo)
    ax.set_xlabel("Regional")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.xticks(rotation=45)

    st.pyplot(fig)

boxplot_por_regional(
    df_filtrado,
    "media",
    f"TMA – Tempo Médio de Atendimento ({tipo_os_selecionado})",
    "Horas"
)

boxplot_por_regional(
    df_filtrado,
    "media_duracao",
    f"Duração do Atendimento ({tipo_os_selecionado})",
    "Horas"
)

boxplot_por_regional(
    df_filtrado,
    "media_deslocamento",
    f"Tempo de Deslocamento ({tipo_os_selecionado})",
    "Horas"
)

st.markdown("---")

df_filtrado['mes'] = (
    pd.to_datetime(df_filtrado['data'])
    .dt.to_period('M')
    .astype(str)
)

df_evolucao_mensal = (
    df_filtrado
    .groupby(['mes', 'regional_nome'], as_index=False)['media']
    .mean()
    .sort_values('mes')
)

figura_linha, eixo_linha = plt.subplots(figsize=(12, 5))

for regional, grupo in df_evolucao_mensal.groupby('regional_nome'):
    eixo_linha.plot(
        grupo['mes'],
        grupo['media'],
        marker='o',
        label=regional
    )

eixo_linha.set_title(
    f"Evolução mensal do TMA – {tipo_os_selecionado}"
)
eixo_linha.set_xlabel("Mês")
eixo_linha.set_ylabel("Horas")
eixo_linha.legend(title="Regional", bbox_to_anchor=(1.05, 1), loc='upper left')
eixo_linha.grid(True, linestyle="--", alpha=0.4)
plt.xticks(rotation=45)

st.pyplot(figura_linha)
