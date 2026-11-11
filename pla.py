from html import escape
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st


st.set_page_config(
    page_title="Distribuição de Ligações Novas",
    page_icon="📍",
    layout="wide",
)

st.title("Distribuição de Ligações Novas")


@st.cache_data
def carregar_dados():
    df = pd.read_excel(Path(__file__).with_name("pla.xlsx"))

    df.columns = (
        df.columns
        .str.strip()
        .str.upper()
    )

    colunas_texto = [
        "REGIONAL",
        "SECCIONAL",
        "MUNICIPIO",
        "CIDADE",
        "BAIRRO",
        "PACOTE",
        "SANEADO",
        "NOTA_PROJ",
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

    for coluna in ["LATITUDE", "LONGITUDE"]:
        df[coluna] = (
            df[coluna]
            .astype(str)
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df[coluna] = pd.to_numeric(
            df[coluna],
            errors="coerce",
        )

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


df = carregar_dados()

st.sidebar.header("Filtros")

df_filtrado = df.copy()

df_filtrado = aplicar_filtro(
    df_filtrado,
    "REGIONAL",
    "Regional",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "NOTA_PROJ",
    "Nota de Projeto",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "SECCIONAL",
    "Seccional",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "MUNICIPIO",
    "Município",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "CIDADE",
    "Cidade",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "BAIRRO",
    "Bairro",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "PACOTE",
    "Pacote",
)

df_filtrado = aplicar_filtro(
    df_filtrado,
    "SANEADO",
    "Saneado",
)

if df_filtrado.empty:
    st.warning(
        "Nenhuma Ligação Nova encontrada para os filtros selecionados."
    )
    st.stop()

quantidade_ligacoes = len(df_filtrado)

col1, col2, col3 = st.columns([1, 1, 2])

col1.metric(
    "Ligações Novas",
    f"{quantidade_ligacoes:,.0f}".replace(",", "."),
)

col2.metric(
    "Municípios",
    df_filtrado["MUNICIPIO"].nunique(),
)

maior_concentracao = (
    df_filtrado["CIDADE"]
    .value_counts()
    .index[0]
)

quantidade_maior_concentracao = (
    df_filtrado["CIDADE"]
    .value_counts()
    .iloc[0]
)

col3.metric(
    "Cidade com maior demanda",
    maior_concentracao,
    f"{quantidade_maior_concentracao} ligações",
    delta_color="off",
)

coordenadas_validas = (
    df_filtrado["LATITUDE"].between(-35, 6)
    & df_filtrado["LONGITUDE"].between(-75, -30)
    & df_filtrado["LATITUDE"].ne(0)
    & df_filtrado["LONGITUDE"].ne(0)
)
sem_coordenadas = df_filtrado.loc[~coordenadas_validas]

colunas_tooltip = [
    "REGIONAL", "SECCIONAL", "MUNICIPIO", "CIDADE",
    "BAIRRO", "PACOTE", "SANEADO", "INSTALACAO", "ULTIMA_OBS_VISITA",
]
dados_mapa = df_filtrado.loc[coordenadas_validas].reindex(
    columns=["LATITUDE", "LONGITUDE", *colunas_tooltip]
).copy()

st.subheader("Distribuição geográfica")

if dados_mapa.empty:
    st.info("Nenhuma instalação com coordenadas válidas para os filtros selecionados.")
else:
    cores_saneado = {
        "SEM AÇÃO MAPEADA": (107, 114, 128),
        "PENDENTE LEVANTAMENTO": (37, 99, 235),
        "PENDENTE VIABILIDADE": (217, 119, 6),
        "RESTRIÇÃO OBRA GRANDE PORTE": (190, 24, 93),
    }
    cores_visiveis = {
        status: cores_saneado.get(status, (13, 148, 136))
        for status in sorted(dados_mapa["SANEADO"].unique())
    }
    dados_mapa["COR_MAPA"] = dados_mapa["SANEADO"].map(
        lambda status: [*cores_visiveis[status], 200]
    )

    for coluna in colunas_tooltip:
        dados_mapa[coluna] = dados_mapa[coluna].map(
            lambda valor: escape(str(valor)) if pd.notna(valor) else "NÃO INFORMADO"
        )

    latitude_central = dados_mapa["LATITUDE"].mean()
    longitude_central = dados_mapa["LONGITUDE"].mean()

    camada_pontos = pdk.Layer(
        "ScatterplotLayer",
        data=dados_mapa,
        get_position="[LONGITUDE, LATITUDE]",
        get_fill_color="COR_MAPA",
        get_line_color=[255, 255, 255, 220],
        get_radius=350,
        radius_min_pixels=6,
        radius_max_pixels=22,
        line_width_min_pixels=1,
        pickable=True,
        auto_highlight=True,
    )

    visualizacao_inicial = pdk.ViewState(
        latitude=latitude_central,
        longitude=longitude_central,
        zoom=7,
        pitch=0,
    )

    tooltip = {
        "html": """
            <b>Regional:</b> {REGIONAL}<br>
            <b>Seccional:</b> {SECCIONAL}<br>
            <b>Município:</b> {MUNICIPIO}<br>
            <b>Cidade:</b> {CIDADE}<br>
            <b>Bairro:</b> {BAIRRO}<br>
            <b>Pacote:</b> {PACOTE}<br>
            <b>Saneado:</b> {SANEADO}<br>
            <b>Instalação:</b> {INSTALACAO}<br>
            <b>Última observação de visita:</b> {ULTIMA_OBS_VISITA}
        """,
        "style": {
            "backgroundColor": "#202124",
            "color": "white",
            "whiteSpace": "pre-wrap",
            "maxWidth": "420px",
        },
    }

    legenda = " &nbsp;&nbsp; ".join(
        f'<span style="color: rgb({r}, {g}, {b})">●</span> '
        f'<strong>{escape(status)}</strong>'
        for status, (r, g, b) in cores_visiveis.items()
    )
    st.markdown(legenda, unsafe_allow_html=True)

    st.pydeck_chart(
        pdk.Deck(
            layers=[camada_pontos],
            initial_view_state=visualizacao_inicial,
            tooltip=tooltip,
            map_style=(
                "https://basemaps.cartocdn.com/gl/"
                "positron-gl-style/style.json"
            ),
        ),
        use_container_width=True,
        height=650,
    )

st.subheader("Demanda por localização")

tabela_localizacao = (
    df_filtrado
    .groupby(
        [
            "REGIONAL",
            "SECCIONAL",
            "MUNICIPIO",
            "CIDADE",
            "BAIRRO",
        ],
        dropna=False,
        as_index=False,
    )
    .size()
    .rename(
        columns={
            "size": "LIGAÇÕES"
        }
    )
)

tabela_localizacao["% DO TOTAL"] = (
    tabela_localizacao["LIGAÇÕES"]
    .div(tabela_localizacao["LIGAÇÕES"].sum())
    .mul(100)
)

tabela_localizacao = tabela_localizacao.sort_values(
    "LIGAÇÕES",
    ascending=False,
)

st.dataframe(
    tabela_localizacao,
    use_container_width=True,
    hide_index=True,
    column_config={
        "LIGAÇÕES": st.column_config.NumberColumn(
            "Ligações",
            format="%d",
        ),
        "% DO TOTAL": st.column_config.ProgressColumn(
            "% do total",
            format="%.1f%%",
            min_value=0,
            max_value=100,
        ),
    },
)

st.subheader("Instalações sem coordenadas válidas")

if sem_coordenadas.empty:
    st.info("Nenhuma instalação sem coordenadas válidas para os filtros selecionados.")
else:
    st.dataframe(
        sem_coordenadas,
        use_container_width=True,
        hide_index=True,
    )
