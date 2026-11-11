from html import escape
from pathlib import Path
from math import asin, cos, radians, sin, sqrt

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
    dados_mapa["COR_MAPA"] = dados_mapa["PACOTE"].apply(
        lambda pacote: (
            [46, 125, 50, 200]
            if pacote == "COM PROJETO"
            else [198, 40, 40, 200]
        )
    )

    for coluna in colunas_tooltip:
        dados_mapa[coluna] = dados_mapa[coluna].map(
            lambda valor: escape(str(valor)) if pd.notna(valor) else "NÃO INFORMADO"
        )

    latitude_central = dados_mapa["LATITUDE"].mean()
    longitude_central = dados_mapa["LONGITUDE"].mean()
    zoom = 7
    camadas = []

    centro = st.selectbox(
        "Instalação de referência",
        options=dados_mapa.index.tolist(),
        index=None,
        placeholder="Selecione uma instalação para analisar o entorno",
        format_func=lambda linha: (
            f"{dados_mapa.at[linha, 'INSTALACAO']} · "
            f"{df_filtrado.at[linha, 'CIDADE']} · "
            f"{df_filtrado.at[linha, 'BAIRRO']} (linha {linha + 2})"
        ),
    )

    if centro is not None:
        raio = st.slider("Raio de análise (m)", 50, 5000, 200, step=50)
        latitude_central = dados_mapa.at[centro, "LATITUDE"]
        longitude_central = dados_mapa.at[centro, "LONGITUDE"]
        latitude_origem = radians(latitude_central)
        zoom = 14 if raio <= 1000 else 11

        def dentro_do_raio(ponto):
            latitude, longitude = ponto
            delta_lat = radians(latitude - latitude_central)
            delta_lon = radians(longitude - longitude_central)
            haversine = (
                sin(delta_lat / 2) ** 2
                + cos(latitude_origem) * cos(radians(latitude))
                * sin(delta_lon / 2) ** 2
            )
            distancia = 2 * 6_371_008.8 * asin(min(1, sqrt(haversine)))
            return distancia <= raio

        no_raio = [
            dentro_do_raio(ponto)
            for ponto in dados_mapa[["LATITUDE", "LONGITUDE"]].itertuples(
                index=False, name=None
            )
        ]
        st.metric("Ligações novas no raio (inclui a referência)", sum(no_raio))
        dados_mapa.loc[[not dentro for dentro in no_raio], "COR_MAPA"] = (
            dados_mapa.loc[[not dentro for dentro in no_raio], "COR_MAPA"]
            .map(lambda cor: [*cor[:3], 45])
        )
        camadas.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[{"posicao": [longitude_central, latitude_central]}],
                get_position="posicao",
                get_radius=raio,
                radius_units="meters",
                get_fill_color=[33, 100, 200, 35],
                get_line_color=[33, 100, 200, 210],
                stroked=True,
                line_width_min_pixels=2,
            )
        )

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
        zoom=zoom,
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

    st.markdown(
        "🟢 **Com Projeto** &nbsp;&nbsp;&nbsp;&nbsp; 🔴 **Sem Projeto**"
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[*camadas, camada_pontos],
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
