import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Análise de Volumetria", layout="wide")

ARQUIVO = "ANALISE_VOLUMETRIA_SUL_PI.xlsx"

REGIONAIS = {
    6: "SUL MA",
    18: "LESTE MA",
    25: "NORTE MA",
    31: "NOROESTE MA",
    30: "SUL PI",
    28: "METROP. PI",
    29: "NORTE PI"
}

MESES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr",
    5: "Mai", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

DIAS_UTEIS_MES = {
    1: 25,
    2: 23,
    3: 25,
    4: 24,
    5: 25,
    6: 24,
    7: 27,
    8: 25,
    9: 24,
    10: 26,
    11: 23,
    12: 25
}

@st.cache_data
@st.cache_data
def carregar_dados():
    df = pd.read_excel(ARQUIVO)

    df.columns = (
        df.columns
        .str.lower()
        .str.strip()
        .str.replace(" ", "_", regex=False)
    )

    df["mes"] = df["mes"].astype(int)
    df["mes_label"] = df["mes"].map(MESES)
    df["regional_nome"] = df["regional_id"].map(REGIONAIS).fillna(df["regional"].astype(str))

    df["periodo_climatico"] = df["mes"].apply(
        lambda x: "Período Chuvoso" if x in [11, 12, 1, 2, 3, 4] else "Período Seco"
    )

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
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0

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
    "qtd_equipe",
    "ups_dpl",
    "ups_gere",
    "ups_eqtl",
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

    meses_sel = st.multiselect(
        "Mês",
        options=sorted(df["mes"].dropna().unique()),
        default=sorted(df["mes"].dropna().unique()),
        format_func=lambda x: MESES.get(int(x), str(x))
    )

    df_filtro_mes = df_filtro_regional[
    df_filtro_regional["mes"].isin(meses_sel)
    ]

    bases_sel = st.multiselect(
        "Base",
        options=sorted(df_filtro_mes["base"].dropna().unique()),
        default=sorted(df_filtro_mes["base"].dropna().unique())
    )

    df_filtro_base = df_filtro_mes[
        df_filtro_mes["base"].isin(bases_sel)
    ]

    cidades_sel = st.multiselect(
        "Cidade",
        options=sorted(df_filtro_base["cidade"].dropna().unique()),
        default=sorted(df_filtro_base["cidade"].dropna().unique())
    )

    df_filtro_cidade = df_filtro_regional[
        df_filtro_regional["cidade"].isin(cidades_sel)
    ]

    

    processos_sel = st.multiselect(
        "Processo",
        options=sorted(df_filtro_cidade["processo"].dropna().unique()),
        default=sorted(df_filtro_cidade["processo"].dropna().unique())
    )

    df_filtro_processo = df_filtro_cidade[
        df_filtro_cidade["processo"].isin(processos_sel)
    ]

    servicos_sel = st.multiselect(
        "Serviço",
        options=sorted(df_filtro_processo["servico2"].dropna().unique()),
        default=sorted(df_filtro_processo["servico2"].dropna().unique())
    )

    fontes_demanda = st.multiselect(
        "Fonte da demanda",
        ["DPL", "EQTL", "GERE"],
        default=["DPL"]
    )

df_filtrado = df[
    (df["regional_id"].isin(regionais_sel)) &
    (df["mes"].isin(meses_sel)) &
    (df["base"].isin(bases_sel)) &
    (df["cidade"].isin(cidades_sel)) &
    (df["processo"].isin(processos_sel)) &
    (df["servico2"].isin(servicos_sel))
].copy()

df_filtrado["demanda_selecionada"] = 0
df_filtrado["ups_selecionada"] = 0

if "DPL" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_dpl"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_dpl"]

if "EQTL" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_eqtl"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_eqtl"]

if "GERE" in fontes_demanda:
    df_filtrado["demanda_selecionada"] += df_filtrado["demanda_recebida_gere"]
    df_filtrado["ups_selecionada"] += df_filtrado["ups_gere"]


df_mes = (
    df_filtrado
    .groupby(["mes", "mes_label", "periodo_climatico"], as_index=False)
    .agg(
        vol_mensal=("vol_mensal", "sum"),
        demanda_mensal=("demanda_selecionada", "sum"),
    )
    .sort_values("mes")
)

df_mes["vol_acumulada"] = df_mes["vol_mensal"].cumsum()
df_mes["demanda_acumulada"] = df_mes["demanda_mensal"].cumsum()
df_mes["limite_80"] = df_mes["vol_acumulada"] * 0.8
df_mes["limite_120"] = df_mes["vol_acumulada"] * 1.2
df_mes["aderencia_acumulada"] = df_mes["demanda_acumulada"] / df_mes["vol_acumulada"].replace(0, pd.NA)

#financeiro

df_filtrado["valor_vol_mensal"] = (
    df_filtrado["vol_mensal"] * df_filtrado["preco"]
)

df_filtrado["valor_demanda"] = (
    df_filtrado["demanda_selecionada"] * df_filtrado["preco"]
)

df_fin_mes = (
    df_filtrado
    .groupby(["mes", "mes_label", "periodo_climatico"], as_index=False)
    .agg(
        financeiro_esperado=("valor_vol_mensal", "sum"),
        financeiro_recebido=("valor_demanda", "sum")
    )
    .sort_values("mes")
)

df_fin_mes["financeiro_esperado_acum"] = df_fin_mes["financeiro_esperado"].cumsum()
df_fin_mes["financeiro_recebido_acum"] = df_fin_mes["financeiro_recebido"].cumsum()
df_fin_mes["limite_80_fin"] = df_fin_mes["financeiro_esperado_acum"] * 0.8
df_fin_mes["limite_120_fin"] = df_fin_mes["financeiro_esperado_acum"] * 1.2

fin_esperado_total = df_fin_mes["financeiro_esperado"].sum()
fin_recebido_total = df_fin_mes["financeiro_recebido"].sum()
aderencia_fin = fin_recebido_total / fin_esperado_total if fin_esperado_total else 0
gap_fin = fin_recebido_total - fin_esperado_total

st.subheader("Análise financeira")

colf1, colf2, colf3, colf4 = st.columns(4)

colf1.metric("Financeiro esperado", f"R$ {fin_esperado_total:,.0f}".replace(",", "."))
colf2.metric("Financeiro recebido", f"R$ {fin_recebido_total:,.0f}".replace(",", "."))
colf3.metric("Aderência financeira", f"{aderencia_fin:.1%}")
colf4.metric("Gap financeiro", f"R$ {gap_fin:,.0f}".replace(",", "."))


vol_total = df_mes["vol_mensal"].sum()
demanda_total = df_mes["demanda_mensal"].sum()
aderencia = demanda_total / vol_total if vol_total else 0
gap = demanda_total - vol_total

st.subheader("Análise volumetria")

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

linha_principal = (
    alt.Chart(
        df_acum_plot[
            df_acum_plot["indicador"].isin([
                "Volumetria acumulada",
                "Demanda acumulada"
            ])
        ]
    )
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="Quantidade"),
        color=alt.Color("indicador:N", title="Indicador"),
        tooltip=[
            "mes_label",
            "indicador",
            alt.Tooltip("valor:Q", format=",.0f")
        ]
    )
)

linha_limites = (
    alt.Chart(
        df_acum_plot[
            df_acum_plot["indicador"].isin([
                "Limite 80%",
                "Limite 120%"
            ])
        ]
    )
    .mark_line(point=False, strokeDash=[6,4])
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values())),
        y="valor:Q",
        color="indicador:N"
    )
)

graf_acum = (
    linha_principal +
    linha_limites
).properties(height=420)

st.altair_chart(graf_acum, use_container_width=True)

st.subheader("Demanda mensal vs Volumetria mensal")
df_mensal_plot = df_mes.melt(
    id_vars=["mes", "mes_label", "periodo_climatico"],
    value_vars=["vol_mensal", "demanda_mensal"],
    var_name="indicador",
    value_name="valor"
)

df_tmd_cidade = (
    df_filtrado
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(
        demanda=("demanda_selecionada", "sum"),
        tmd_total=("tmd", "sum"),
        tma_total=("tma", "sum"),
        tme_total=("tme", "sum")
    )
)

df_tmd_cidade["tmd_por_demanda"] = (
    df_tmd_cidade["tmd_total"] /
    df_tmd_cidade["demanda"].replace(0, pd.NA)
)

df_tmd_cidade["pct_tmd_tma"] = (
    df_tmd_cidade["tmd_total"] /
    df_tmd_cidade["tma_total"].replace(0, pd.NA)
)

df_mensal_plot["indicador"] = df_mensal_plot["indicador"].map({
    "vol_mensal": "Volumetria mensal",
    "demanda_mensal": "Demanda mensal"
})

df_mensal_plot["cor"] = df_mensal_plot.apply(
    lambda row:
        "Chuvoso"
        if row["indicador"] == "Volumetria mensal"
        and row["periodo_climatico"] == "Período Chuvoso"
        else "Seco"
        if row["indicador"] == "Volumetria mensal"
        and row["periodo_climatico"] == "Período Seco"
        else "Demanda",
    axis=1
)

graf_mensal = (
    alt.Chart(df_mensal_plot)
    .mark_bar()
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="Quantidade"),
        color=alt.Color(
            "cor:N",
            title="Legenda",
            scale=alt.Scale(
                domain=["Demanda", "Chuvoso", "Seco"],
                range=["#6BAED6", "#1F77B4", "#D62728"]
            )
        ),
        xOffset="indicador:N",
        tooltip=[
            "mes_label",
            "periodo_climatico",
            "indicador",
            alt.Tooltip("valor:Q", format=",.0f")
        ]
    )
    .properties(height=420)
)

st.altair_chart(graf_mensal, use_container_width=True)



st.subheader("Financeiro acumulado esperado vs recebido")

df_fin_acum_plot = df_fin_mes.melt(
    id_vars=["mes", "mes_label"],
    value_vars=[
        "financeiro_esperado_acum",
        "financeiro_recebido_acum",
        "limite_80_fin",
        "limite_120_fin"
    ],
    var_name="indicador",
    value_name="valor"
)

df_fin_acum_plot["indicador"] = df_fin_acum_plot["indicador"].map({
    "financeiro_esperado_acum": "Financeiro esperado acumulado",
    "financeiro_recebido_acum": "Financeiro recebido acumulado",
    "limite_80_fin": "Limite 80%",
    "limite_120_fin": "Limite 120%"
})

linha_fin_principal = (
    alt.Chart(
        df_fin_acum_plot[
            df_fin_acum_plot["indicador"].isin([
                "Financeiro esperado acumulado",
                "Financeiro recebido acumulado"
            ])
        ]
    )
    .mark_line(point=True, strokeWidth=3)
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="R$"),
        color=alt.Color("indicador:N", title="Indicador"),
        tooltip=[
            "mes_label",
            "indicador",
            alt.Tooltip("valor:Q", format=",.0f")
        ]
    )
)

linha_fin_limites = (
    alt.Chart(
        df_fin_acum_plot[
            df_fin_acum_plot["indicador"].isin([
                "Limite 80%",
                "Limite 120%"
            ])
        ]
    )
    .mark_line(point=False, strokeDash=[6, 4])
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values())),
        y="valor:Q",
        color="indicador:N"
    )
)

graf_fin_acum = (
    linha_fin_principal + linha_fin_limites
).properties(height=420)

st.altair_chart(graf_fin_acum, use_container_width=True)


st.subheader("Financeiro mensal esperado vs recebido")

df_fin_mensal_plot = df_fin_mes.melt(
    id_vars=["mes", "mes_label", "periodo_climatico"],
    value_vars=["financeiro_esperado", "financeiro_recebido"],
    var_name="indicador",
    value_name="valor"
)

df_fin_mensal_plot["indicador"] = df_fin_mensal_plot["indicador"].map({
    "financeiro_esperado": "Financeiro esperado",
    "financeiro_recebido": "Financeiro recebido"
})

graf_fin_mensal = (
    alt.Chart(df_fin_mensal_plot)
    .mark_bar()
    .encode(
        x=alt.X("mes_label:N", sort=list(MESES.values()), title="Mês"),
        y=alt.Y("valor:Q", title="R$"),
        color=alt.Color("indicador:N", title="Indicador"),
        xOffset="indicador:N",
        tooltip=[
            "mes_label",
            "periodo_climatico",
            "indicador",
            alt.Tooltip("valor:Q", format=",.0f")
        ]
    )
    .properties(height=420)
)

st.altair_chart(graf_fin_mensal, use_container_width=True)




st.subheader("Resumo por período")

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
        "🔴 Alta demanda",
        "🟢 Demanda adequada",
        "🟡 Baixa demanda",
        "⚪ Sem volumetria"
    ],
    default=[
        "🔴 Alta demanda",
        "🟢 Demanda adequada",
        "🟡 Baixa demanda"
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
        return "🔴 Alta demanda"

    if x >= 0.8:
        return "🟢 Demanda adequada"

    return "🟡 Baixa demanda"


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

    periodos_ups_sel = st.multiselect(
        "Período UPS",
        ["Período Chuvoso", "Período Seco"],
        default=["Período Chuvoso", "Período Seco"]
    )

    faixa_aceitacao = st.slider(
        "Faixa de aceitação (%)",
        min_value=50,
        max_value=120,
        value=90
    )

limite_ups = meta_ups * (faixa_aceitacao / 100)

df_ups_base = df_filtrado[
    df_filtrado["periodo_climatico"].isin(periodos_ups_sel)
].copy()

df_ups_base["dias_uteis"] = df_ups_base["mes"].map(DIAS_UTEIS_MES)

qtd_meses_periodo = max(df_ups_base["mes"].nunique(), 1)

df_equipes_atual = (
    df_filtrado[df_filtrado["mes"] == 4]
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(qtd_equipe_atual=("qtd_equipe", "mean"))
)

df_ups_cidade = (
    df_ups_base
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(
        ups_total=("ups_selecionada", "sum"),
        dias_uteis_medio=("dias_uteis", "mean")
    )
)

df_ups_cidade = df_ups_cidade.merge(
    df_equipes_atual,
    on=["regional_nome", "cidade"],
    how="left"
)

df_ups_cidade["ups_medio_mes"] = (
    df_ups_cidade["ups_total"] / qtd_meses_periodo
)

df_ups_cidade["ups_medio_dia"] = (
    df_ups_cidade["ups_medio_mes"] /
    df_ups_cidade["dias_uteis_medio"].replace(0, pd.NA)
)

df_ups_cidade["equipes_sustentadas"] = (
    df_ups_cidade["ups_medio_dia"] / limite_ups
)

df_ups_cidade["ups_equipe_dia"] = (
    df_ups_cidade["ups_medio_dia"] /
    df_ups_cidade["qtd_equipe_atual"].replace(0, pd.NA)
)

df_ups_cidade["saldo_equipes"] = (
    df_ups_cidade["equipes_sustentadas"] -
    df_ups_cidade["qtd_equipe_atual"]
)

df_ups_cidade["pct_meta"] = (
    df_ups_cidade["ups_equipe_dia"] / meta_ups
)

df_ups_cidade["pct_meta"] = pd.to_numeric(
    df_ups_cidade["pct_meta"],
    errors="coerce"
).fillna(0)



def classificar_nota_ups(x):
    if pd.isna(x):
        return "Sem dados"
    if x >= 0.90:
        return "A"
    if x >= 0.80:
        return "B"
    if x >= 0.70:
        return "C"
    return "D"

def classificar_situacao_ups(x):
    if pd.isna(x):
        return "⚪ Sem dados"
    if x >= limite_ups:
        return "🟢 Saudável"
    return "🔴 Abaixo do aceitável"

df_ups_cidade["nota_ups"] = df_ups_cidade["pct_meta"].apply(classificar_nota_ups)
df_ups_cidade["pct_meta"] = (
    df_ups_cidade["pct_meta"] * 100
).round(2)
df_ups_cidade["situacao_ups"] = df_ups_cidade["ups_equipe_dia"].apply(classificar_situacao_ups)

df_ups_cidade = df_ups_cidade.sort_values("saldo_equipes", ascending=False)

nota_geral = classificar_nota_ups(
    df_ups_cidade["ups_equipe_dia"].mean() / meta_ups
)

col_ups1, col_ups2, col_ups3, col_ups4 = st.columns(4)

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

col_ups4.metric(
    "Rank geral",
    nota_geral
)

st.dataframe(
    df_ups_cidade,
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional_nome": "Regional",
        "cidade": "Cidade",
        "qtd_equipe_atual": st.column_config.NumberColumn("Equipes atuais", format="%.1f"),
        "dias_uteis_medio": st.column_config.NumberColumn("Dias úteis médios", format="%.1f"),
        "ups_equipe_dia": st.column_config.NumberColumn("UPS/equipe/dia", format="%.1f"),
        "equipes_sustentadas": st.column_config.NumberColumn("Equipes sustentadas", format="%.1f"),
        "saldo_equipes": st.column_config.NumberColumn("Saldo equipes", format="%.1f"),
        "pct_meta": st.column_config.NumberColumn("% da meta", format="%.2f%%"),
        "nota_ups": "Nota UPS",
        "situacao_ups": "Situação UPS"
    },
    column_order=[
        "regional_nome",
        "cidade",
        "qtd_equipe_atual",
        "dias_uteis_medio",
        "ups_equipe_dia",
        "equipes_sustentadas",
        "saldo_equipes",
        "pct_meta",
        "nota_ups",
        "situacao_ups"
    ]
)

st.subheader("Saldo de equipes por regional")

df_ups_regional = (
    df_ups_cidade
    .groupby("regional_nome", as_index=False)
    .agg(
        equipes_atuais=("qtd_equipe_atual", "sum"),
        equipes_sustentadas=("equipes_sustentadas", "sum"),
        saldo_equipes=("saldo_equipes", "sum")
    )
)

df_ups_regional = df_ups_regional.sort_values("saldo_equipes", ascending=False)

st.dataframe(
    df_ups_regional,
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional_nome": "Regional",
        "equipes_atuais": st.column_config.NumberColumn("Equipes atuais", format="%.1f"),
        "equipes_sustentadas": st.column_config.NumberColumn("Equipes sustentadas", format="%.1f"),
        "saldo_equipes": st.column_config.NumberColumn("Saldo de equipes", format="%.1f")
    }
)

st.subheader("tmd por cidade")

df_tmd_cidade = (
    df_filtrado
    .groupby(["regional_nome", "cidade"], as_index=False)
    .agg(
        demanda=("demanda_selecionada", "sum"),
        tmd_total=("tmd", "sum"),
        tma_total=("tma", "sum"),
        tme_total=("tme", "sum")
    )
)

df_tmd_cidade["tmd_por_demanda"] = (
    df_tmd_cidade["tmd_total"] /
    df_tmd_cidade["demanda"].replace(0, pd.NA)
)

df_tmd_cidade["pct_tmd_tma"] = (
    df_tmd_cidade["tmd_total"] /
    df_tmd_cidade["tma_total"].replace(0, pd.NA)
)

df_tmd_cidade = df_tmd_cidade.sort_values(
    "pct_tmd_tma",
    ascending=False
)

st.dataframe(
    df_tmd_cidade,
    use_container_width=True,
    hide_index=True,
    column_config={
        "regional_nome": "Regional",
        "cidade": "Cidade",
        "demanda": st.column_config.NumberColumn("Demanda", format="%.0f"),
        "tmd_total": st.column_config.NumberColumn("TMD total", format="%.0f"),
        "tma_total": st.column_config.NumberColumn("TMA total", format="%.0f"),
        "tme_total": st.column_config.NumberColumn("TME total", format="%.0f"),
        "tmd_por_demanda": st.column_config.NumberColumn("TMD por demanda", format="%.1f"),
        "pct_tmd_tma": st.column_config.NumberColumn("% TMD/TMA", format="%.1%")
    }
)