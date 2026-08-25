import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Comparativo de Execução",
    page_icon="📊",
    layout="wide",
)

st.title("Comparativo de Execução — 2025 × 2026")
st.caption("Período comparável: 01/01 a 24/08 de cada ano")


# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data
def carregar_dados():
    df = pd.read_excel("deterioracao_demanda.xlsx")

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
    )

    df["ANO"] = pd.to_numeric(df["ANO"], errors="coerce")
    df["MES"] = pd.to_numeric(df["MES"], errors="coerce")
    df["QTD"] = pd.to_numeric(df["QTD"], errors="coerce").fillna(0)

    colunas_texto = [
        "EQUIPE",
        "SIGLA",
        "BASE",
        "TIPO_EQUIPE",
        "SEGMENTO",
        "TIPO_OS",
        "GRUPO_OS",
        "PROD_IMPROD",
    ]

    for coluna in colunas_texto:
        if coluna in df.columns:
            df[coluna] = (
                df[coluna]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.strip()
                .str.upper()
            )

    df = df[df["ANO"].isin([2025, 2026])]
    df = df[df["MES"].between(1, 8)]
    df = df.dropna(subset=["ANO", "MES", "EQUIPE"])

    df["ANO"] = df["ANO"].astype(int)
    df["MES"] = df["MES"].astype(int)

    return df


df_original = carregar_dados()


# =========================================================
# AUXILIARY FUNCTIONS
# =========================================================

MESES = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
}


def filtro_multiselect(df, coluna, titulo):
    opcoes = sorted(df[coluna].dropna().unique())

    selecionados = st.sidebar.multiselect(
        titulo,
        options=opcoes,
        default=[],
        placeholder="Todos",
    )

    if selecionados:
        return df[df[coluna].isin(selecionados)]

    return df


def valor_ano(df, ano, coluna):
    resultado = df.loc[df["ANO"] == ano, coluna]

    if resultado.empty:
        return 0

    return resultado.iloc[0]


def calcular_variacao(valor_2025, valor_2026):
    if valor_2025 == 0:
        return None

    return ((valor_2026 / valor_2025) - 1) * 100


def formatar_numero(valor, casas=0):
    formato = f"{{:,.{casas}f}}"
    return (
        formato.format(valor)
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_variacao(valor):
    if valor is None:
        return "N/A"

    return f"{valor:+.1f}%".replace(".", ",")


# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.header("Filtros")

df_filtrado = df_original.copy()

df_filtrado = filtro_multiselect(
    df_filtrado, "BASE", "Base"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "SIGLA", "Sigla"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "TIPO_EQUIPE", "Tipo de equipe"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "SEGMENTO", "Segmento"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "EQUIPE", "Equipe"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "GRUPO_OS", "Grupo OS"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "TIPO_OS", "Tipo OS"
)

df_filtrado = filtro_multiselect(
    df_filtrado, "PROD_IMPROD", "Produtivo / Improdutivo"
)

if df_filtrado.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()


# =========================================================
# MONTHLY CONSOLIDATION
# =========================================================

# Each team is counted only once within each year/month.
resumo_mensal = (
    df_filtrado
    .groupby(["ANO", "MES"], as_index=False)
    .agg(
        EXECUCAO=("QTD", "sum"),
        EQUIPES_ATIVAS=("EQUIPE", "nunique"),
    )
)

resumo_mensal["EXECUCAO_POR_EQUIPE"] = (
    resumo_mensal["EXECUCAO"]
    / resumo_mensal["EQUIPES_ATIVAS"]
)

resumo_mensal["MES_NOME"] = resumo_mensal["MES"].map(MESES)

resumo_mensal = resumo_mensal.sort_values(
    ["ANO", "MES"]
)

resumo_mensal["EXECUCAO_ACUMULADA"] = (
    resumo_mensal
    .groupby("ANO")["EXECUCAO"]
    .cumsum()
)

resumo_mensal["ANO_TEXTO"] = resumo_mensal["ANO"].astype(str)


# =========================================================
# PERIOD SUMMARY
# =========================================================

# A team-month identifies one available team in one month.
equipes_mes = (
    df_filtrado[["ANO", "MES", "EQUIPE"]]
    .drop_duplicates()
    .groupby("ANO", as_index=False)
    .size()
    .rename(columns={"size": "EQUIPE_MES"})
)

resumo_periodo = (
    df_filtrado
    .groupby("ANO", as_index=False)
    .agg(
        EXECUCAO=("QTD", "sum"),
        EQUIPES_DISTINTAS=("EQUIPE", "nunique"),
    )
    .merge(equipes_mes, on="ANO", how="left")
)

resumo_periodo["EXECUCAO_POR_EQUIPE_MES"] = (
    resumo_periodo["EXECUCAO"]
    / resumo_periodo["EQUIPE_MES"]
)


# =========================================================
# KPI CARDS
# =========================================================

execucao_2025 = valor_ano(
    resumo_periodo, 2025, "EXECUCAO"
)

execucao_2026 = valor_ano(
    resumo_periodo, 2026, "EXECUCAO"
)

equipe_mes_2025 = valor_ano(
    resumo_periodo, 2025, "EQUIPE_MES"
)

equipe_mes_2026 = valor_ano(
    resumo_periodo, 2026, "EQUIPE_MES"
)

media_2025 = valor_ano(
    resumo_periodo, 2025, "EXECUCAO_POR_EQUIPE_MES"
)

media_2026 = valor_ano(
    resumo_periodo, 2026, "EXECUCAO_POR_EQUIPE_MES"
)

variacao_execucao = calcular_variacao(
    execucao_2025,
    execucao_2026,
)

variacao_estrutura = calcular_variacao(
    equipe_mes_2025,
    equipe_mes_2026,
)

variacao_media = calcular_variacao(
    media_2025,
    media_2026,
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Execução em 2025",
    formatar_numero(execucao_2025),
)

col2.metric(
    "Execução em 2026",
    formatar_numero(execucao_2026),
    delta=formatar_variacao(variacao_execucao),
)

col3.metric(
    "Variação da estrutura",
    formatar_numero(equipe_mes_2026) + " equipes-mês",
    delta=formatar_variacao(variacao_estrutura),
)

col4.metric(
    "Execução por equipe-mês",
    formatar_numero(media_2026, 1),
    delta=formatar_variacao(variacao_media),
)


# =========================================================
# MONTHLY LINE CHARTS
# =========================================================

col_esquerda, col_direita = st.columns(2)

with col_esquerda:
    st.subheader("Execução mensal")

    fig_execucao = px.line(
        resumo_mensal,
        x="MES",
        y="EXECUCAO",
        color="ANO_TEXTO",
        markers=True,
        labels={
            "MES": "Mês",
            "EXECUCAO": "Quantidade executada",
            "ANO_TEXTO": "Ano",
        },
        color_discrete_map={
            "2025": "#7F8C8D",
            "2026": "#1565C0",
        },
    )

    fig_execucao.update_xaxes(
        tickmode="array",
        tickvals=list(MESES.keys()),
        ticktext=list(MESES.values()),
    )

    fig_execucao.update_layout(
        hovermode="x unified",
        legend_title_text="Ano",
    )

    st.plotly_chart(
        fig_execucao,
        use_container_width=True,
    )

with col_direita:
    st.subheader("Execução mensal por equipe ativa")

    fig_media = px.line(
        resumo_mensal,
        x="MES",
        y="EXECUCAO_POR_EQUIPE",
        color="ANO_TEXTO",
        markers=True,
        labels={
            "MES": "Mês",
            "EXECUCAO_POR_EQUIPE": "Execução por equipe",
            "ANO_TEXTO": "Ano",
        },
        color_discrete_map={
            "2025": "#7F8C8D",
            "2026": "#D84315",
        },
    )

    fig_media.update_xaxes(
        tickmode="array",
        tickvals=list(MESES.keys()),
        ticktext=list(MESES.values()),
    )

    fig_media.update_layout(
        hovermode="x unified",
        legend_title_text="Ano",
    )

    st.plotly_chart(
        fig_media,
        use_container_width=True,
    )


# =========================================================
# CUMULATIVE EXECUTION
# =========================================================

st.subheader("Execução acumulada")

fig_acumulado = px.line(
    resumo_mensal,
    x="MES",
    y="EXECUCAO_ACUMULADA",
    color="ANO_TEXTO",
    markers=True,
    labels={
        "MES": "Mês",
        "EXECUCAO_ACUMULADA": "Execução acumulada",
        "ANO_TEXTO": "Ano",
    },
    color_discrete_map={
        "2025": "#7F8C8D",
        "2026": "#2E7D32",
    },
)

fig_acumulado.update_xaxes(
    tickmode="array",
    tickvals=list(MESES.keys()),
    ticktext=list(MESES.values()),
)

fig_acumulado.update_layout(
    hovermode="x unified",
    legend_title_text="Ano",
)

st.plotly_chart(
    fig_acumulado,
    use_container_width=True,
)


# =========================================================
# COMPARISON BY GRUPO_OS
# =========================================================

st.subheader("Comparativo por grupo de OS")

grupo_os = (
    df_filtrado
    .groupby(["GRUPO_OS", "ANO"], as_index=False)
    .agg(
        EXECUCAO=("QTD", "sum"),
        EQUIPES=("EQUIPE", "nunique"),
    )
)

grupo_os["EXECUCAO_POR_EQUIPE"] = (
    grupo_os["EXECUCAO"]
    / grupo_os["EQUIPES"]
)

grupo_os["ANO_TEXTO"] = grupo_os["ANO"].astype(str)

ordem_grupos = (
    grupo_os
    .groupby("GRUPO_OS")["EXECUCAO"]
    .sum()
    .sort_values(ascending=True)
    .index
)

fig_grupo = px.bar(
    grupo_os,
    x="EXECUCAO",
    y="GRUPO_OS",
    color="ANO_TEXTO",
    barmode="group",
    orientation="h",
    category_orders={
        "GRUPO_OS": ordem_grupos.tolist()
    },
    labels={
        "EXECUCAO": "Quantidade executada",
        "GRUPO_OS": "Grupo OS",
        "ANO_TEXTO": "Ano",
    },
    color_discrete_map={
        "2025": "#7F8C8D",
        "2026": "#1565C0",
    },
)

fig_grupo.update_layout(
    height=max(450, len(ordem_grupos) * 42),
    legend_title_text="Ano",
)

st.plotly_chart(
    fig_grupo,
    use_container_width=True,
)


# =========================================================
# VARIATION BY GRUPO_OS
# =========================================================

comparativo_grupo = (
    grupo_os
    .pivot_table(
        index="GRUPO_OS",
        columns="ANO",
        values="EXECUCAO",
        aggfunc="sum",
        fill_value=0,
    )
    .reset_index()
)

for ano in [2025, 2026]:
    if ano not in comparativo_grupo.columns:
        comparativo_grupo[ano] = 0

comparativo_grupo["DIFERENCA"] = (
    comparativo_grupo[2026]
    - comparativo_grupo[2025]
)

comparativo_grupo["VARIACAO_PCT"] = (
    comparativo_grupo["DIFERENCA"]
    .div(comparativo_grupo[2025].replace(0, pd.NA))
    .mul(100)
)

comparativo_grupo = comparativo_grupo.sort_values(
    "DIFERENCA"
)

st.subheader("Variação por grupo de OS")

fig_variacao = px.bar(
    comparativo_grupo,
    x="DIFERENCA",
    y="GRUPO_OS",
    orientation="h",
    color="DIFERENCA",
    color_continuous_scale=[
        [0.0, "#B71C1C"],
        [0.5, "#EEEEEE"],
        [1.0, "#1B5E20"],
    ],
    labels={
        "DIFERENCA": "Diferença absoluta: 2026 − 2025",
        "GRUPO_OS": "Grupo OS",
    },
)

fig_variacao.update_layout(
    height=max(450, len(comparativo_grupo) * 42),
    coloraxis_showscale=False,
)

st.plotly_chart(
    fig_variacao,
    use_container_width=True,
)


# =========================================================
# PRODUCTIVE / UNPRODUCTIVE COMPOSITION
# =========================================================

st.subheader("Composição produtiva e improdutiva")

produtividade = (
    df_filtrado
    .groupby(["ANO", "PROD_IMPROD"], as_index=False)
    .agg(EXECUCAO=("QTD", "sum"))
)

produtividade["ANO_TEXTO"] = produtividade["ANO"].astype(str)

fig_produtividade = px.bar(
    produtividade,
    x="ANO_TEXTO",
    y="EXECUCAO",
    color="PROD_IMPROD",
    barmode="stack",
    text_auto=".3s",
    labels={
        "ANO_TEXTO": "Ano",
        "EXECUCAO": "Quantidade executada",
        "PROD_IMPROD": "Classificação",
    },
    color_discrete_map={
        "P": "#2E7D32",
        "I": "#C62828",
    },
)

fig_produtividade.update_layout(
    legend_title_text="Produtividade",
)

st.plotly_chart(
    fig_produtividade,
    use_container_width=True,
)


# =========================================================
# DETAILED TABLE
# =========================================================

with st.expander("Ver dados consolidados"):
    tabela_exibicao = resumo_mensal[
        [
            "ANO",
            "MES_NOME",
            "EXECUCAO",
            "EQUIPES_ATIVAS",
            "EXECUCAO_POR_EQUIPE",
            "EXECUCAO_ACUMULADA",
        ]
    ].copy()

    tabela_exibicao.columns = [
        "Ano",
        "Mês",
        "Execução",
        "Equipes ativas",
        "Execução por equipe",
        "Execução acumulada",
    ]

    st.dataframe(
        tabela_exibicao,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Execução": st.column_config.NumberColumn(
                format="%d"
            ),
            "Equipes ativas": st.column_config.NumberColumn(
                format="%d"
            ),
            "Execução por equipe": st.column_config.NumberColumn(
                format="%.1f"
            ),
            "Execução acumulada": st.column_config.NumberColumn(
                format="%d"
            ),
        },
    )