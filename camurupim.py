import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Análise Operacional — Camurupim",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp {
        background-color: #f7f9fb;
        color: #243447;
    }
    .block-container { max-width: 1450px; padding-top: 2rem; }
    h1, h2, h3, h4, h5, h6,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"],
    .stCaption {
        color: #243447 !important;
    }
    h1 { color: #17324d !important; }
    h2, h3 { color: #294861 !important; }
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #dbe4ec;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 5px 18px rgba(31, 50, 65, 0.08);
    }
    [data-testid="stMetricLabel"] p {
        color: #536779 !important;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #17324d !important;
    }
    [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border-color: #cbd6e1 !important;
        color: #243447 !important;
    }
    [data-baseweb="select"] span,
    [data-baseweb="select"] input,
    [data-baseweb="tag"] span {
        color: #243447 !important;
    }
    .stMultiSelect label p {
        color: #40566b !important;
        font-weight: 600;
    }
    .section-divider {
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 2.8rem 0 1.7rem 0;
        color: #60758a;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .section-divider::before,
    .section-divider::after {
        content: "";
        height: 1px;
        flex: 1;
        background: linear-gradient(90deg, transparent, #cfd8e3);
    }
    .section-divider::after {
        background: linear-gradient(90deg, #cfd8e3, transparent);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def carregar_log():
    df = pd.read_excel("camurupim_log.xlsx")

    df["data"] = pd.to_datetime(df["data"]).dt.normalize()
    df["atribuicao"] = pd.to_datetime(
        df["Tempo_de_Atribuicao_da_Atividade"]
    )
    df["inicio_turno"] = pd.to_datetime(df["inicio_turno"])
    df["inicio_deslocamento_dt"] = (
        df["data"]
        + pd.to_timedelta(df["inicio_deslocamento"].astype(str))
    )

    atribuida_antes = df["atribuicao"] < df["inicio_turno"]

    df["atribuida_antes_turno"] = atribuida_antes.map(
        {True: "Sim", False: "Não"}
    )

    df["tempo_ocioso_coi_min"] = (
        (df["atribuicao"] - df["inicio_turno"])
        .dt.total_seconds()
        .div(60)
        .clip(lower=0)
    )

    df["inicio_contagem_equipe"] = df[
        ["atribuicao", "inicio_turno"]
    ].max(axis=1)

    df["tempo_inicio_primeira_atividade_min"] = (
        (
            df["inicio_deslocamento_dt"]
            - df["inicio_contagem_equipe"]
        )
        .dt.total_seconds()
        .div(60)
    )

    df["status_atribuicao"] = "ATRIBUIÇÃO NO INÍCIO DO TURNO"
    df.loc[
        df["atribuicao"] > df["inicio_turno"],
        "status_atribuicao",
    ] = "ATRIBUIÇÃO APÓS INÍCIO DO TURNO"
    df.loc[
        df["atribuicao"] < df["inicio_turno"],
        "status_atribuicao",
    ] = "ATRIBUIÇÃO ANTES DO INÍCIO DO TURNO"

    return df[
        [
            "data",
            "equipe",
            "inicio_turno",
            "atribuicao",
            "inicio_deslocamento_dt",
            "atribuida_antes_turno",
            "tempo_ocioso_coi_min",
            "tempo_inicio_primeira_atividade_min",
            "status_atribuicao",
        ]
    ].copy()


@st.cache_data
def carregar_atividades():
    df = pd.read_excel("camurupim.xlsx")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    for coluna in ["tipos_os", "grupo_os", "sigla_base"]:
        df[coluna] = (
            df[coluna]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.strip()
        )

    return df


def formatar_minutos(valor):
    if pd.isna(valor):
        return "—"

    minutos = int(round(valor))
    horas, minutos_restantes = divmod(minutos, 60)

    if horas:
        return f"{horas}h {minutos_restantes:02d}min"

    return f"{minutos_restantes} min"


def preparar_distribuicao(df, coluna):
    distribuicao = (
        df.groupby(coluna, as_index=False)
        .size()
        .rename(columns={"size": "quantidade"})
    )

    total = distribuicao["quantidade"].sum()
    distribuicao["percentual"] = (
        distribuicao["quantidade"].div(total).mul(100)
        if total
        else 0
    )
    distribuicao["rotulo"] = (
        distribuicao["quantidade"].astype(str)
        + "  •  "
        + distribuicao["percentual"].map(lambda x: f"{x:.1f}%")
    )

    return distribuicao.sort_values("quantidade", ascending=True)


def criar_grafico(df, coluna, titulo, cor):
    distribuicao = preparar_distribuicao(df, coluna)

    fig = px.bar(
        distribuicao,
        x="quantidade",
        y=coluna,
        orientation="h",
        text="rotulo",
        custom_data=["percentual"],
        color_discrete_sequence=[cor],
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(color="#243447", size=14),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Serviços: %{x}<br>"
            "Participação: %{customdata[0]:.1f}%"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        title=dict(
            text=titulo,
            x=0.02,
            font=dict(size=18, color="#17324d", family="Arial"),
        ),
        height=max(380, len(distribuicao) * 42),
        margin=dict(l=115, r=115, t=65, b=55),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        xaxis=dict(
            title="Quantidade de serviços",
            automargin=True,
            title_font=dict(color="#40566b", size=14),
            tickfont=dict(color="#536779", size=12),
            showgrid=True,
            gridcolor="#dde5ec",
            zeroline=False,
        ),
        yaxis=dict(
            title=None,
            automargin=True,
            tickfont=dict(color="#40566b", size=13),
        ),
        font=dict(family="Arial", color="#243447"),
    )

    return fig


st.title("Análise Operacional — Camurupim")
st.caption("Primeira atividade do turno e distribuição dos serviços executados")

try:
    log = carregar_log()
except FileNotFoundError:
    st.error("Arquivo camurupim_log.xlsx não encontrado.")
    st.stop()

st.subheader("Início da primeira atividade")

media_ocioso = log["tempo_ocioso_coi_min"].mean()
media_inicio = log["tempo_inicio_primeira_atividade_min"].mean()
percentual_atribuicao_apos_turno = (
    log["status_atribuicao"]
    .eq("ATRIBUIÇÃO APÓS INÍCIO DO TURNO")
    .mean()
    * 100
)

card1, card2, card3 = st.columns([1, 1, 1])

with card1:
    st.metric(
        "Tempo ocioso COI — média",
        formatar_minutos(media_ocioso),
        help="Tempo médio entre o início do turno e a atribuição da primeira atividade.",
    )

with card2:
    st.metric(
        "Início da primeira atividade — média",
        formatar_minutos(media_inicio),
        help="Tempo médio entre a disponibilidade da equipe e o início do deslocamento.",
    )

with card3:
    st.metric(
        "Atribuições após início do turno",
        f"{percentual_atribuicao_apos_turno:.1f}%".replace(".", ","),
        help="Percentual das primeiras atividades atribuídas após o início do turno da equipe.",
    )

tabela_log = log.copy()
tabela_log["data"] = tabela_log["data"].dt.strftime("%d/%m/%Y")

for coluna in [
    "inicio_turno",
    "atribuicao",
    "inicio_deslocamento_dt",
]:
    tabela_log[coluna] = tabela_log[coluna].dt.strftime("%H:%M")

tabela_log = tabela_log.rename(
    columns={
        "data": "Data",
        "equipe": "Equipe",
        "inicio_turno": "Início do turno",
        "atribuicao": "Atribuição",
        "inicio_deslocamento_dt": "Início do deslocamento",
        "atribuida_antes_turno": "Atribuída antes do turno",
        "tempo_ocioso_coi_min": "Tempo ocioso COI (min)",
        "tempo_inicio_primeira_atividade_min": "Tempo para início (min)",
        "status_atribuicao": "Status da atribuição",
    }
)

st.dataframe(
    tabela_log,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Tempo ocioso COI (min)": st.column_config.NumberColumn(format="%.0f"),
        "Tempo para início (min)": st.column_config.NumberColumn(format="%.0f"),
    },
)

st.markdown(
    '<div class="section-divider">Distribuição das atividades executadas</div>',
    unsafe_allow_html=True,
)

try:
    atividades = carregar_atividades()
except FileNotFoundError:
    st.error("Arquivo camurupim.xlsx não encontrado.")
    st.stop()

filtro1, filtro2 = st.columns(2)

with filtro1:
    bases = st.multiselect(
        "Sigla da base",
        options=sorted(atividades["sigla_base"].unique()),
        placeholder="Todas as bases",
    )

with filtro2:
    grupos = st.multiselect(
        "Grupo de OS",
        options=sorted(atividades["grupo_os"].unique()),
        placeholder="Todos os grupos",
    )

atividades_filtradas = atividades.copy()

if bases:
    atividades_filtradas = atividades_filtradas[
        atividades_filtradas["sigla_base"].isin(bases)
    ]

if grupos:
    atividades_filtradas = atividades_filtradas[
        atividades_filtradas["grupo_os"].isin(grupos)
    ]

st.caption(
    f"{len(atividades_filtradas):,} serviços selecionados"
    .replace(",", ".")
)

if atividades_filtradas.empty:
    st.warning("Nenhum serviço encontrado para os filtros selecionados.")
else:
    grafico_tipo = criar_grafico(
        atividades_filtradas,
        "tipos_os",
        "Distribuição por tipo de OS",
        "#4f81bd",
    )

    grafico_grupo = criar_grafico(
        atividades_filtradas,
        "grupo_os",
        "Distribuição por grupo de OS",
        "#5a9a8b",
    )

    grafico_base = criar_grafico(
        atividades_filtradas,
        "sigla_base",
        "Distribuição por base",
        "#8a78a8",
    )

    coluna1, coluna2 = st.columns(2)

    with coluna1:
        st.plotly_chart(
            grafico_tipo,
            use_container_width=True,
            theme=None,
        )

    with coluna2:
        st.plotly_chart(
            grafico_grupo,
            use_container_width=True,
            theme=None,
        )

    st.plotly_chart(
        grafico_base,
        use_container_width=True,
        theme=None,
    )
