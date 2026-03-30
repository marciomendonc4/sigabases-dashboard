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

# =========================
# DATA CLEANING (IMPORTANT)
# =========================
cols_numericas = [
    "media", "media_duracao", "media_deslocamento",
    "ups_efetiva", "ups_realizada", "ups_bid"
]

for col in cols_numericas:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# FILTRO TIPO OS
# =========================
lista_tipo_os = sorted(df['tipo_os'].dropna().unique().tolist())
lista_tipo_os.insert(0, "NR's")

tipo_os_selecionado = st.selectbox(
    "Selecione o tipo de OS",
    lista_tipo_os
)

if tipo_os_selecionado == "NR's":
    df_filtrado = df[df['tipo_os'].isin(['NR IMPROD', 'NR IND', 'NR COL'])].copy()
else:
    df_filtrado = df[df['tipo_os'] == tipo_os_selecionado].copy()

# =========================
# FILTRO REGIONAL
# =========================
lista_regional = sorted(df_filtrado['regional_nome'].dropna().unique().tolist())

regional_selecionada = st.multiselect(
    "Selecione a Regional (opcional)",
    lista_regional
)

# =========================
# EIXO DINÂMICO
# =========================
if regional_selecionada:
    df_filtrado = df_filtrado[df_filtrado['regional_nome'].isin(regional_selecionada)]
    eixo_x = "BASE"
    label_x = "Base"
else:
    eixo_x = "regional_nome"
    label_x = "Regional"

# =========================
# FUNÇÃO BOXPLOT ROBUSTA
# =========================
def boxplot_dinamico(df, coluna, titulo, ylabel):
    df_plot = df.copy()

    # remove nulls
    df_plot = df_plot.dropna(subset=[coluna])

    dados = (
        df_plot.groupby(eixo_x)[coluna]
        .apply(list)
        .loc[lambda x: x.map(len) > 0]
        .sort_index()
    )

    if dados.empty:
        st.warning(f"Sem dados para {titulo}")
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    boxplot = ax.boxplot(
        dados.values,
        labels=dados.index.tolist(),
        patch_artist=True,
        boxprops=dict(alpha=0.5),
        medianprops=dict(linewidth=2)
    )

    # median labels
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

boxplot_dinamico(df_filtrado, "media", f"TMA ({tipo_os_selecionado})", "Horas")
boxplot_dinamico(df_filtrado, "media_duracao", f"Duração ({tipo_os_selecionado})", "Horas")
boxplot_dinamico(df_filtrado, "media_deslocamento", f"Deslocamento ({tipo_os_selecionado})", "Horas")

# =========================
# UPS BOXPLOTS
# =========================
st.markdown("---")
st.subheader("Distribuição de Produtividade (UPS)")

boxplot_dinamico(df_filtrado, "ups_realizada", f"UPS Realizada ({tipo_os_selecionado})", "UPS")
boxplot_dinamico(df_filtrado, "ups_efetiva", f"UPS Efetiva ({tipo_os_selecionado})", "UPS")
boxplot_dinamico(df_filtrado, "ups_bid", f"UPS BID ({tipo_os_selecionado})", "UPS")

# =========================
# SCATTER PLOT (FIXED)
# =========================
st.markdown("---")
st.subheader("Desvio do Modelo de Produtividade")

df_scatter = df_filtrado.dropna(subset=["ups_realizada", "ups_efetiva"]).copy()

if df_scatter.empty:
    st.warning("Sem dados suficientes para o scatter plot")
else:
    df_scatter["desvio"] = df_scatter["ups_efetiva"] - df_scatter["ups_realizada"]

    fig, ax = plt.subplots(figsize=(8, 6))

    scatter = ax.scatter(
        df_scatter["ups_realizada"],
        df_scatter["ups_efetiva"],
        c=df_scatter["desvio"],
        cmap="coolwarm",
        alpha=0.6,
        s=40
    )

    # colorbar
    cbar = plt.colorbar(scatter)
    cbar.set_label("Desvio (Efetiva - Realizada)")

    # diagonal reference
    max_val = max(
        df_scatter["ups_realizada"].max(),
        df_scatter["ups_efetiva"].max()
    )

    ax.plot([0, max_val], [0, max_val], linestyle="--")

    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)

    ax.set_xlabel("UPS Realizada")
    ax.set_ylabel("UPS Efetiva")
    ax.set_title("Desvio do Modelo de Produtividade")
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)