import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Análise de Volumetria", layout="wide")

ARQUIVO = "ANALISE_VOLUMETRIA.xlsx"

REGIONAIS = {
    6: "SUL MA",
    18: "LESTE MA",
    25: "NORTE MA",
    31: "NOROESTE MA"
}

MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}


@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO)
    df.columns = df.columns.str.lower().str.strip()

    df["mes"] = df["mes"].astype(int)
    df["mes_label"] = df["mes"].map(MESES)
    df["regional_nome"] = df["regional_id"].map(REGIONAIS).fillna(df["regional"].astype(str))

    df["periodo_climatico"] = df["mes"].apply(
        lambda x: "Período Chuvoso" if x in [11, 12, 1, 2, 3, 4] else "Período Seco"
    )

    for col in [
        "vol_mensal",
        "demanda_recebida_dpl",
        "demanda_recebida_eqtl",
        "demanda_recebida_gere",
        "preco"
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


df = carregar_dados()

colunas_numericas = [
    "vol_mensal",
    "demanda_recebida_dpl",
    "demanda_recebida_eqtl",
    "demanda_recebida_gere",
    "preco",
    "ups",
    "tma",
    "tmd",
    "tme",
    "dias_ativos",
    "qtd_equipe"
]

for col in colunas_numericas:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

st.title("Análise de Volumetria")
st.caption("Comparativo entre volumetria contratual esperada e demanda recebida para execução.")

with st.sidebar:
    st.header("Filtros")

    regionais_sel = st.multiselect(
        "Regional",
        options=sorted(df["regional_id"].dropna().unique()),
        default=sorted(df["regional_id"].dropna().unique()),
        format_func=lambda x: REGIONAIS.get(x, str(x))
    )

    df_filtro_regional = df[df["regional_id"].isin(regionais_sel)]

    cidades_sel = st.multiselect(
        "Cidade",
        options=sorted(df_filtro_regional["cidade"].dropna().unique()),
        default=sorted(df_filtro_regional["cidade"].dropna().unique())
    )

    processos_sel = st.multiselect(
        "Processo",
        options=sorted(df_filtro_regional["processo"].dropna().unique()),
        default=sorted(df_filtro_regional["processo"].dropna().unique())
    )

    fontes_demanda = st.multiselect(
        "Fonte da demanda",
        ["DPL", "EQTL", "GERE"],
        default=["DPL"]
    )

df_filtrado = df[
    (df["regional_id"].isin(regionais_sel)) &
    (df["cidade"].isin(cidades_sel)) &
    (df["processo"].isin(processos_sel))
].copy()

df_filtrado["demanda_selecionada"] = 0

if "DPL" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_dpl"]

if "EQTL" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_eqtl"]

if "GERE" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_gere"]


df_mes = (
    df_filtrado
    .groupby(["mes", "mes_label"], as_index=False)
    .agg(
        vol_mensal=("vol_mensal", "sum"),
        demanda_mensal=("demanda_selecionada", "sum"),
        valor_volumetria=("vol_mensal", lambda x: 0),
    )
    .sort_values("mes")
)

df_mes["vol_acumulada"] = df_mes["vol_mensal"].cumsum()
df_mes["demanda_acumulada"] = df_mes["demanda_mensal"].cumsum()
df_mes["limite_80"] = df_mes["vol_acumulada"] * 0.8
df_mes["limite_120"] = df_mes["vol_acumulada"] * 1.2
df_mes["aderencia_acumulada"] = df_mes["demanda_acumulada"] / df_mes["vol_acumulada"].replace(0, pd.NA)

vol_total = df_mes["vol_mensal"].sum()
demanda_total = df_mes["demanda_mensal"].sum()
aderencia = demanda_total / vol_total if vol_total else 0
gap = demanda_total - vol_total

col1, col2, col3, col4 = st.columns(4)

col1.metric("Volumetria esperada", f"{vol_total:,.0f}".replace(",", "."))
col2.metric("Demanda recebida", f"{demanda_total:,.0f}".replace(",", "."))
col3.metric("Aderência", f"{aderencia:.1%}")
col4.metric("Gap", f"{gap:,.0f}".replace(",", "."))

st.divider()

st.subheader("Demanda acumulada vs Volumetria acumulada")

df_acum_plot = df_mes.melt(
    id_vars=["mes", "mes_label"],
    value_vars=["vol_acumulada", "demanda_acumulada", "limite_80", "limite_120"],
    var_name="indicador",
    value_name="valor"
)

nomes_indicadores = {
    "vol_acumulada": "Volumetria acumulada",
    "demanda_acumulada": "Demanda acumulada",
    "limite_80": "Limite 80%",
    "limite_120": "Limite 120%"
}

df_acum_plot["indicador"] = df_acum_plot["indicador"].map(nomes_indicadores)

graf_acum = (
    alt.Chart(df_acum_plot)
    .mark_line(point=True, strokeDash=[6,4])
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="Quantidade"),
        color=alt.Color("indicador:N", title="Indicador"),
        tooltip=["mes_label", "indicador", alt.Tooltip("valor:Q", format=",.0f")]
    )
    .properties(height=420)
)

st.altair_chart(graf_acum, use_container_width=True)

st.subheader("Demanda mensal vs Volumetria mensal")

df_mensal_plot = df_mes.melt(
    id_vars=["mes", "mes_label"],
    value_vars=["vol_mensal", "demanda_mensal"],
    var_name="indicador",
    value_name="valor"
)

df_mensal_plot["indicador"] = df_mensal_plot["indicador"].map({
    "vol_mensal": "Volumetria mensal",
    "demanda_mensal": "Demanda mensal"
})

graf_mensal = (
    alt.Chart(df_mensal_plot)
    .mark_bar()
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="Quantidade"),
        color=alt.Color("indicador:N", title="Indicador"),
        xOffset="indicador:N",
        tooltip=["mes_label", "indicador", alt.Tooltip("valor:Q", format=",.0f")]
    )
    .properties(height=420)
)

st.altair_chart(graf_mensal, use_container_width=True)

st.subheader("Resumo por período climático")

df_periodo = (
    df_filtrado
    .groupby("periodo_climatico", as_index=False)
    .agg(
        volumetria=("vol_mensal", "sum"),
        demanda=("demanda_selecionada", "sum")
    )
)

df_periodo["aderencia"] = df_periodo["demanda"] / df_periodo["volumetria"].replace(0, pd.NA)

st.dataframe(
    df_periodo,
    use_container_width=True,
    hide_index=True
)

st.subheader("Diagnóstico por cidade")

situacoes_sel = st.multiselect(
    "Situação",
    [
        "🔴 Subdimensionado",
        "🟢 Adequado",
        "🟡 Ociosidade",
        "⚪ Sem volumetria"
    ],
    default=[
        "🔴 Subdimensionado",
        "🟢 Adequado",
        "🟡 Ociosidade"
    ]
)

df_cidade = (
    df_filtrado
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(
        volumetria=("vol_mensal", "sum"),
        demanda=("demanda_selecionada", "sum")
    )
)



df_cidade = df_cidade[
    (df_cidade["volumetria"] > 0) |
    (df_cidade["demanda"] > 0)
]

df_cidade["limite_80"] = df_cidade["volumetria"] * 0.8
df_cidade["limite_120"] = df_cidade["volumetria"] * 1.2

df_cidade["aderencia"] = (
    df_cidade["demanda"] /
    df_cidade["volumetria"].replace(0, pd.NA)
)

df_cidade["aderencia_pct"] = df_cidade["aderencia"] * 100

df_cidade["gap"] = (
    df_cidade["demanda"] -
    df_cidade["volumetria"]
)

df_cidade["diagnostico"] = df_cidade.apply(
    lambda row:
        "Demanda insuficiente"
        if row["demanda"] < row["limite_80"]
        else "Dentro da faixa contratual"
        if row["demanda"] <= row["limite_120"]
        else "Demanda acima da volumetria",
    axis=1
)



def classificar_situacao(x):
    if pd.isna(x):
        return "⚪ Sem volumetria"

    if x > 1.2:
        return "🔴 Subdimensionado"

    if x >= 0.8:
        return "🟢 Adequado"

    return "🟡 Ociosidade"


df_cidade["situacao"] = df_cidade["aderencia"].apply(classificar_situacao)

df_cidade = df_cidade[
    df_cidade["situacao"].isin(situacoes_sel)
]

df_cidade = df_cidade.sort_values(
    "aderencia",
    ascending=False
)

st.dataframe(
    df_cidade,
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional_nome": "Regional",

        "cidade": "Cidade",

        "volumetria": st.column_config.NumberColumn(
            "Volumetria",
            format="%.0f"
        ),

        "demanda": st.column_config.NumberColumn(
            "Demanda",
            format="%.0f"
        ),

        "limite_80": st.column_config.NumberColumn(
            "Limite 80%",
            format="%.0f"
        ),

        "limite_120": st.column_config.NumberColumn(
            "Limite 120%",
            format="%.0f"
        ),

        "aderencia_pct": st.column_config.NumberColumn(
            "Aderência %",
            format="%.1f"
        ),

        "gap": st.column_config.NumberColumn(
            "Gap",
            format="%.0f"
        ),

        "situacao": "Situação",

        "diagnostico": "Diagnóstico"
    }
)

st.subheader("Análise de UPS por cidade")

with st.sidebar:
    st.divider()
    st.header("Parâmetros UPS")

    meta_ups = st.number_input(
        "Meta UPS/equipe/dia",
        min_value=1.0,
        value=42.0,
        step=1.0
    )

    faixa_aceitacao = st.slider(
        "Faixa de aceitação (%)",
        min_value=50,
        max_value=120,
        value=90
    )

    min_dias_ativos = st.slider(
        "Mínimo de dias ativos",
        min_value=1,
        max_value=31,
        value=10
    )

limite_ups = meta_ups * (faixa_aceitacao / 100)

df_ups_base = df_filtrado[
    df_filtrado["dias_ativos"] >= min_dias_ativos
].copy()

df_ups_cidade = (
    df_ups_base
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(
        ups_total=("ups", "sum"),
        dias_ativos_medio=("dias_ativos", "mean"),
        qtd_equipe=("qtd_equipe", "mean")
    )
)

df_ups_cidade["ups_medio_dia"] = (
    df_ups_cidade["ups_total"] /
    df_ups_cidade["dias_ativos_medio"].replace(0, pd.NA)
)

df_ups_cidade["ups_equipe_dia"] = (
    df_ups_cidade["ups_medio_dia"] /
    df_ups_cidade["qtd_equipe"].replace(0, pd.NA)
)

df_ups_cidade["equipes_sustentadas"] = (
    df_ups_cidade["ups_medio_dia"] /
    limite_ups
)

df_ups_cidade["pct_meta"] = (
    df_ups_cidade["ups_equipe_dia"] /
    meta_ups
)

df_ups_cidade["nota_ups"] = df_ups_cidade["pct_meta"].apply(
    lambda x:
        "A" if x >= 0.90 else
        "B" if x >= 0.80 else
        "C" if x >= 0.70 else
        "D"
)

df_ups_cidade["situacao_ups"] = df_ups_cidade["ups_equipe_dia"].apply(
    lambda x:
        "🟢 Saudável" if x >= limite_ups else
        "🔴 Abaixo do aceitável"
)

df_ups_cidade = df_ups_cidade.sort_values(
    "ups_equipe_dia",
    ascending=False
)

col_ups1, col_ups2, col_ups3 = st.columns(3)

col_ups1.metric(
    "UPS médio/equipe/dia",
    f"{df_ups_cidade['ups_equipe_dia'].mean():.1f}"
)

col_ups2.metric(
    "Meta considerada",
    f"{meta_ups:.0f}"
)

col_ups3.metric(
    "Limite aceitável",
    f"{limite_ups:.1f}"
)

st.dataframe(
    df_ups_cidade,
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional_nome": "Regional",
        "cidade": "Cidade",

        "ups_total": st.column_config.NumberColumn(
            "UPS Total",
            format="%.0f"
        ),

        "dias_ativos_medio": st.column_config.NumberColumn(
            "Dias ativos médios",
            format="%.1f"
        ),

        "qtd_equipe": st.column_config.NumberColumn(
            "Qtd. equipes",
            format="%.1f"
        ),

        "ups_medio_dia": st.column_config.NumberColumn(
            "UPS médio/dia",
            format="%.1f"
        ),

        "ups_equipe_dia": st.column_config.NumberColumn(
            "UPS/equipe/dia",
            format="%.1f"
        ),

        "equipes_sustentadas": st.column_config.NumberColumn(
            "Equipes sustentadas",
            format="%.1f"
        ),

        "pct_meta": st.column_config.NumberColumn(
            "% da meta",
            format="%.1%"
        ),

        "nota_ups": "Nota UPS",
        "situacao_ups": "Situação UPS"
    }
)