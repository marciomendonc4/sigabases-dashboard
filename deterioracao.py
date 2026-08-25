import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Comparativo de Execução",
    page_icon="📊",
    layout="wide",
)

st.title("Comparativo de Execução — 2025 × 2026")
st.caption("Período: 01/01 a 24/08")


@st.cache_data
def carregar_dados():
    df = pd.read_excel("deterioracao_demanda.xlsx")

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
    )

    colunas_numericas = [
        "ANO",
        "MES",
        "QTD",
        "PRODUCAO",
        "QTD_DIAS",
    ]

    for coluna in colunas_numericas:
        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

    df["QTD"] = df["QTD"].fillna(0)
    df["PRODUCAO"] = df["PRODUCAO"].fillna(0)
    df["QTD_DIAS"] = df["QTD_DIAS"].fillna(0)

    colunas_texto = [
        "REGIONAL",
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
        df[coluna] = (
            df[coluna]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    regionais = {
    30: "SUL PI",
    28: "METROP. PI",
    29: "NORTE PI",
    }

    df["REGIONAL"] = (
        pd.to_numeric(
            df["REGIONAL"],
            errors="coerce",
        )
        .map(regionais)
        .fillna("NÃO INFORMADO")
    )

    df = df[
        df["ANO"].isin([2025, 2026])
    ]

    df = df[
        df["MES"].between(1, 8)
    ]

    df = df.dropna(
        subset=["ANO", "MES", "EQUIPE"]
    )

    df["ANO"] = df["ANO"].astype(int)
    df["MES"] = df["MES"].astype(int)

    return df


def aplicar_filtro(df, coluna, titulo):
    opcoes = sorted(
        df[coluna]
        .dropna()
        .unique()
        .tolist()
    )

    selecionados = st.sidebar.multiselect(
        titulo,
        options=opcoes,
        placeholder="Todos",
    )

    if selecionados:
        return df[df[coluna].isin(selecionados)]

    return df


def formatar_numero(valor, casas=0):
    formato = f"{{:,.{casas}f}}"

    return (
        formato.format(valor)
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def formatar_variacao(valor):
    if valor is None or pd.isna(valor):
        return None

    return f"{valor:+.1f}%".replace(".", ",")


def calcular_variacao(valor_2025, valor_2026):
    if valor_2025 == 0:
        return None

    return (
        (valor_2026 / valor_2025) - 1
    ) * 100


def obter_valor_ano(df, ano, coluna):
    resultado = df.loc[
        df["ANO"] == ano,
        coluna,
    ]

    if resultado.empty:
        return 0

    return resultado.iloc[0]


def calcular_resumo_mensal(df):
    execucao = (
        df.groupby(
            ["ANO", "MES"],
            as_index=False,
        )
        .agg(
            EXECUCAO=("QTD", "sum"),
            PRODUCAO=("PRODUCAO", "sum"),
            EQUIPES_ATIVAS=("EQUIPE", "nunique"),
        )
    )

    dias = (
        df[
            [
                "ANO",
                "MES",
                "EQUIPE",
                "QTD_DIAS",
            ]
        ]
        .drop_duplicates(
            subset=[
                "ANO",
                "MES",
                "EQUIPE",
            ]
        )
        .groupby(
            ["ANO", "MES"],
            as_index=False,
        )
        .agg(
            TOTAL_DIAS=("QTD_DIAS", "sum")
        )
    )

    resumo = execucao.merge(
        dias,
        on=["ANO", "MES"],
        how="left",
    )

    resumo["MEDIA_QTD_DIARIA"] = (
        resumo["EXECUCAO"]
        .div(
            resumo["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    resumo["MEDIA_PRODUCAO_DIARIA"] = (
        resumo["PRODUCAO"]
        .div(
            resumo["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    resumo = resumo.sort_values(
        ["ANO", "MES"]
    )

    resumo["EXECUCAO_ACUMULADA"] = (
        resumo
        .groupby("ANO")["EXECUCAO"]
        .cumsum()
    )

    resumo["ANO_TEXTO"] = resumo["ANO"].astype(str)

    return resumo


def calcular_resumo_periodo(df):
    execucao = (
        df.groupby(
            "ANO",
            as_index=False,
        )
        .agg(
            EXECUCAO=("QTD", "sum"),
            PRODUCAO=("PRODUCAO", "sum"),
        )
    )

    dias = (
        df[
            [
                "ANO",
                "MES",
                "EQUIPE",
                "QTD_DIAS",
            ]
        ]
        .drop_duplicates(
            subset=[
                "ANO",
                "MES",
                "EQUIPE",
            ]
        )
        .groupby(
            "ANO",
            as_index=False,
        )
        .agg(
            TOTAL_DIAS=("QTD_DIAS", "sum")
        )
    )

    resumo = execucao.merge(
        dias,
        on="ANO",
        how="left",
    )

    resumo["MEDIA_QTD_DIARIA"] = (
        resumo["EXECUCAO"]
        .div(
            resumo["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    resumo["MEDIA_PRODUCAO_DIARIA"] = (
        resumo["PRODUCAO"]
        .div(
            resumo["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    return resumo


def calcular_medias_tipo_os(df):
    volumes = (
        df.groupby(
            ["ANO", "TIPO_OS"],
            as_index=False,
        )
        .agg(
            QTD=("QTD", "sum"),
            PRODUCAO=("PRODUCAO", "sum"),
        )
    )

    dias = (
        df[
            [
                "ANO",
                "MES",
                "EQUIPE",
                "TIPO_OS",
                "QTD_DIAS",
            ]
        ]
        .drop_duplicates(
            subset=[
                "ANO",
                "MES",
                "EQUIPE",
                "TIPO_OS",
            ]
        )
        .groupby(
            ["ANO", "TIPO_OS"],
            as_index=False,
        )
        .agg(
            TOTAL_DIAS=("QTD_DIAS", "sum")
        )
    )

    medias = volumes.merge(
        dias,
        on=["ANO", "TIPO_OS"],
        how="left",
    )

    medias["QTDE_MEDIA"] = (
        medias["QTD"]
        .div(
            medias["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    medias["VALOR_MEDIO"] = (
        medias["PRODUCAO"]
        .div(
            medias["TOTAL_DIAS"].replace(0, pd.NA)
        )
    )

    medias["TICKET_MEDIO"] = (
        medias["PRODUCAO"]
        .div(
            medias["QTD"].replace(0, pd.NA)
        )
    )

    return medias


def criar_tabela_tipo_os(df):
    medias = calcular_medias_tipo_os(df)

    tabela = (
        medias
        .pivot(
            index="TIPO_OS",
            columns="ANO",
            values=[
            "QTDE_MEDIA",
            "VALOR_MEDIO",
            "TICKET_MEDIO",
        ],
        )
    )

    tabela.columns = [
        f"{indicador}_{ano}"
        for indicador, ano in tabela.columns
    ]

    tabela = tabela.reset_index()

    colunas_esperadas = [
        "QTDE_MEDIA_2025",
        "VALOR_MEDIO_2025",
        "TICKET_MEDIO_2025",
        "QTDE_MEDIA_2026",
        "VALOR_MEDIO_2026",
        "TICKET_MEDIO_2026",
    ]

    for coluna in colunas_esperadas:
        if coluna not in tabela.columns:
            tabela[coluna] = 0

    tabela["VAR_QTDE"] = (
        tabela["QTDE_MEDIA_2026"]
        .div(
            tabela[
                "QTDE_MEDIA_2025"
            ].replace(0, pd.NA)
        )
        .sub(1)
        .mul(100)
    )

    tabela["VAR_VALOR"] = (
        tabela["VALOR_MEDIO_2026"]
        .div(
            tabela[
                "VALOR_MEDIO_2025"
            ].replace(0, pd.NA)
        )
        .sub(1)
        .mul(100)
    )

    tabela["VAR_TICKET"] = (
        tabela["TICKET_MEDIO_2026"]
        .div(
            tabela[
                "TICKET_MEDIO_2025"
            ].replace(0, pd.NA)
        )
        .sub(1)
        .mul(100)
    )

    resumo_total = calcular_resumo_periodo(df)

    total_2025 = resumo_total[
        resumo_total["ANO"] == 2025
    ]

    total_2026 = resumo_total[
        resumo_total["ANO"] == 2026
    ]

    qtd_2025 = (
        total_2025["MEDIA_QTD_DIARIA"].iloc[0]
        if not total_2025.empty
        else 0
    )

    valor_2025 = (
        total_2025["MEDIA_PRODUCAO_DIARIA"].iloc[0]
        if not total_2025.empty
        else 0
    )

    qtd_2026 = (
        total_2026["MEDIA_QTD_DIARIA"].iloc[0]
        if not total_2026.empty
        else 0
    )

    valor_2026 = (
        total_2026["MEDIA_PRODUCAO_DIARIA"].iloc[0]
        if not total_2026.empty
        else 0
    )

    ticket_2025 = (
        total_2025["PRODUCAO"].iloc[0]
        / total_2025["EXECUCAO"].iloc[0]
        if (
            not total_2025.empty
            and total_2025["EXECUCAO"].iloc[0] != 0
        )
        else 0
    )

    ticket_2026 = (
        total_2026["PRODUCAO"].iloc[0]
        / total_2026["EXECUCAO"].iloc[0]
        if (
            not total_2026.empty
            and total_2026["EXECUCAO"].iloc[0] != 0
        )
        else 0
    )

    linha_total = pd.DataFrame(
        {
            "TIPO_OS": ["TOTAL"],
            "QTDE_MEDIA_2025": [qtd_2025],
            "VALOR_MEDIO_2025": [valor_2025],
            "TICKET_MEDIO_2025": [ticket_2025],
            "QTDE_MEDIA_2026": [qtd_2026],
            "VALOR_MEDIO_2026": [valor_2026],
            "TICKET_MEDIO_2026": [ticket_2026],
            "VAR_QTDE": [
                calcular_variacao(
                    qtd_2025,
                    qtd_2026,
                )
            ],
            "VAR_VALOR": [
                calcular_variacao(
                    valor_2025,
                    valor_2026,
                )
            ],
            "VAR_TICKET": [
                calcular_variacao(
                    ticket_2025,
                    ticket_2026,
                )
            ],
        }
    )

    tabela = tabela[
        [
            "TIPO_OS",
            "QTDE_MEDIA_2025",
            "VALOR_MEDIO_2025",
            "TICKET_MEDIO_2025",
            "QTDE_MEDIA_2026",
            "VALOR_MEDIO_2026",
            "TICKET_MEDIO_2026",
            "VAR_QTDE",
            "VAR_VALOR",
            "VAR_TICKET",
        ]
    ]

    tabela = tabela.sort_values(
        "TIPO_OS"
    )

    tabela = pd.concat(
        [tabela, linha_total],
        ignore_index=True,
    )

    return tabela


df_original = carregar_dados()

st.sidebar.header("Filtros")

df_filtrado = df_original.copy()

df_filtrado = aplicar_filtro(
    df_filtrado,
    "REGIONAL",
    "Regional",
)

meses = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

meses_disponiveis = sorted(
    df_filtrado["MES"]
    .dropna()
    .astype(int)
    .unique()
    .tolist()
)

meses_selecionados = st.sidebar.multiselect(
    "Mês",
    options=meses_disponiveis,
    format_func=lambda mes: meses[mes],
    placeholder="Todos",
)

if meses_selecionados:
    df_filtrado = df_filtrado[
        df_filtrado["MES"].isin(meses_selecionados)
    ]

df_filtrado = aplicar_filtro(
    df_filtrado,
    "BASE",
    "Base",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "SIGLA",
    "Sigla",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "TIPO_EQUIPE",
    "Tipo de equipe",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "SEGMENTO",
    "Segmento",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "EQUIPE",
    "Equipe",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "GRUPO_OS",
    "Grupo OS",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "TIPO_OS",
    "Tipo OS",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "PROD_IMPROD",
    "Produtivo / Improdutivo",
)

if df_filtrado.empty:
    st.warning(
        "Nenhum registro encontrado para os filtros selecionados."
    )
    st.stop()

resumo_mensal = calcular_resumo_mensal(
    df_filtrado
)

resumo_periodo = calcular_resumo_periodo(
    df_filtrado
)

execucao_2025 = obter_valor_ano(
    resumo_periodo,
    2025,
    "EXECUCAO",
)

execucao_2026 = obter_valor_ano(
    resumo_periodo,
    2026,
    "EXECUCAO",
)

media_2025 = obter_valor_ano(
    resumo_periodo,
    2025,
    "MEDIA_QTD_DIARIA",
)

media_2026 = obter_valor_ano(
    resumo_periodo,
    2026,
    "MEDIA_QTD_DIARIA",
)

variacao_execucao = calcular_variacao(
    execucao_2025,
    execucao_2026,
)

variacao_media = calcular_variacao(
    media_2025,
    media_2026,
)

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Demanda em 2025",
    formatar_numero(execucao_2025),
)

col2.metric(
    "Demanda em 2026",
    formatar_numero(execucao_2026),
    delta=formatar_variacao(
        variacao_execucao
    ),
)

col3.metric(
    "Média diária por equipe — 2025",
    formatar_numero(media_2025, 2),
)

col4.metric(
    "Média diária por equipe — 2026",
    formatar_numero(media_2026, 2),
    delta=formatar_variacao(
        variacao_media
    ),
)

st.subheader("Comparativo de execução mensal")

tipo_comparacao = st.radio(
    "Forma de comparação",
    options=[
        "Absoluta",
        "Proporcional",
    ],
    horizontal=True,
    label_visibility="collapsed",
)

if tipo_comparacao == "Absoluta":
    coluna_grafico = "EXECUCAO"
    titulo_eixo_y = "Quantidade executada"
    formato_hover = ":,.0f"
else:
    coluna_grafico = "MEDIA_QTD_DIARIA"
    titulo_eixo_y = "Atividades por equipe/dia"
    formato_hover = ":.2f"

fig_execucao = px.line(
    resumo_mensal,
    x="MES",
    y=coluna_grafico,
    color="ANO_TEXTO",
    markers=True,
    labels={
        "MES": "Mês",
        coluna_grafico: titulo_eixo_y,
        "ANO_TEXTO": "Ano",
    },
    color_discrete_map={
        "2025": "#7F8C8D",
        "2026": "#1565C0",
    },
)

fig_execucao.update_traces(
    hovertemplate=(
        "<b>%{fullData.name}</b><br>"
        "Mês: %{x}<br>"
        f"{titulo_eixo_y}: %{{y{formato_hover}}}"
        "<extra></extra>"
    )
)

fig_execucao.update_xaxes(
    tickmode="array",
    tickvals=list(range(1, 9)),
    ticktext=[
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
    ],
)

fig_execucao.update_yaxes(
    title=titulo_eixo_y,
)

fig_execucao.update_layout(
    hovermode="x unified",
    legend_title_text="Ano",
)

st.plotly_chart(
    fig_execucao,
    use_container_width=True,
)

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
    tickvals=list(range(1, 9)),
    ticktext=[
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
    ],
)

fig_acumulado.update_layout(
    hovermode="x unified",
    legend_title_text="Ano",
)

st.plotly_chart(
    fig_acumulado,
    use_container_width=True,
)

st.subheader("Comparativo por grupo de OS")

grupo_os = (
    df_filtrado
    .groupby(
        ["GRUPO_OS", "ANO"],
        as_index=False,
    )
    .agg(
        EXECUCAO=("QTD", "sum"),
    )
)

grupo_os["ANO_TEXTO"] = (
    grupo_os["ANO"].astype(str)
)

ordem_grupos = (
    grupo_os
    .groupby("GRUPO_OS")["EXECUCAO"]
    .sum()
    .sort_values(ascending=True)
    .index
    .tolist()
)

fig_grupo = px.bar(
    grupo_os,
    x="EXECUCAO",
    y="GRUPO_OS",
    color="ANO_TEXTO",
    barmode="group",
    orientation="h",
    category_orders={
        "GRUPO_OS": ordem_grupos
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
    height=max(
        400,
        len(ordem_grupos) * 60,
    ),
    legend_title_text="Ano",
)

st.plotly_chart(
    fig_grupo,
    use_container_width=True,
)

st.subheader("Execução média diária por tipo de OS")

tabela_tipo_os = criar_tabela_tipo_os(
    df_filtrado
)

st.dataframe(
    tabela_tipo_os,
    use_container_width=True,
    hide_index=True,
    column_config={
        "TIPO_OS": st.column_config.TextColumn(
            "Tipo de OS",
        ),
        "QTDE_MEDIA_2025": st.column_config.NumberColumn(
            "Qtde 2025",
            format="%.2f",
        ),
        "VALOR_MEDIO_2025": st.column_config.NumberColumn(
            "Valor 2025",
            format="R$ %.2f",
        ),
        "TICKET_MEDIO_2025": st.column_config.NumberColumn(
            "Ticket Médio 2025",
            format="R$ %.2f",
        ),
        "QTDE_MEDIA_2026": st.column_config.NumberColumn(
            "Qtde 2026",
            format="%.2f",
        ),
        "VALOR_MEDIO_2026": st.column_config.NumberColumn(
            "Valor 2026",
            format="R$ %.2f",
        ),
        "TICKET_MEDIO_2026": st.column_config.NumberColumn(
            "Ticket Médio 2026",
            format="R$ %.2f",
        ),
        "VAR_QTDE": st.column_config.NumberColumn(
            "Var. Qtde",
            format="%.1f%%",
        ),
        "VAR_VALOR": st.column_config.NumberColumn(
            "Var. Valor",
            format="%.1f%%",
        ),
        "VAR_TICKET": st.column_config.NumberColumn(
            "Var. Ticket",
            format="%.1f%%",
        ),
    },
)

with st.expander("Ver consolidação mensal"):
    tabela_mensal = resumo_mensal[
        [
            "ANO",
            "MES",
            "EXECUCAO",
            "PRODUCAO",
            "EQUIPES_ATIVAS",
            "TOTAL_DIAS",
            "MEDIA_QTD_DIARIA",
            "MEDIA_PRODUCAO_DIARIA",
            "EXECUCAO_ACUMULADA",
        ]
    ].copy()

    tabela_mensal.columns = [
        "Ano",
        "Mês",
        "Execução",
        "Produção",
        "Equipes ativas",
        "Equipe-dias",
        "Média diária por equipe",
        "Produção diária por equipe",
        "Execução acumulada",
    ]

    st.dataframe(
        tabela_mensal,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Execução": st.column_config.NumberColumn(
                format="%d",
            ),
            "Produção": st.column_config.NumberColumn(
                format="R$ %.2f",
            ),
            "Equipes ativas": st.column_config.NumberColumn(
                format="%d",
            ),
            "Equipe-dias": st.column_config.NumberColumn(
                format="%d",
            ),
            "Média diária por equipe": st.column_config.NumberColumn(
                format="%.2f",
            ),
            "Produção diária por equipe": st.column_config.NumberColumn(
                format="R$ %.2f",
            ),
            "Execução acumulada": st.column_config.NumberColumn(
                format="%d",
            ),
        },
    )