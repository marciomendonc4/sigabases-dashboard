import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="DPL SUL PI", layout="wide")

st.title("Tempos Operacionais")


@st.cache_data
def load_data():
    df = pd.read_excel("V_TEORIA_DAS_FILAS.xlsx")

    def time_to_hours(val):
        if pd.isna(val):
            return 0.0
        h, m, *s = str(val).split(":")
        s = s[0] if s else 0
        return int(h) + int(m) / 60 + int(s) / 3600

    df["DURACAO_HORAS"] = df["DURACAO"].apply(time_to_hours)
    df["DESLOCAMENTO_HORAS"] = df["DESLOCAMENTO"].apply(time_to_hours)
    df["TMA_HORAS"] = df["DURACAO_HORAS"] + df["DESLOCAMENTO_HORAS"]

    df["DATA"] = pd.to_datetime(df["DATA"])
    df["ANO_MES"] = df["DATA"].dt.to_period("M").astype(str)

    return df

df = load_data()

df["DATA"] = pd.to_datetime(df["DATA"])

df["MES_NUM"] = df["DATA"].dt.month

df["PERIODO"] = df["MES_NUM"].apply(
    lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
)

df["DATA"] = pd.to_datetime(df["DATA"])

df["MES_NUM"] = df["DATA"].dt.month

meses_pt = {
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
    12: "Dez"
}

df["MES"] = df["MES_NUM"].map(meses_pt)

ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
df["MES"] = pd.Categorical(df["MES"], categories=ordem_meses, ordered=True)

periodos = ["Todos", "Período Seco", "Período Úmido"]

periodo_selecionado = st.selectbox(
    "Selecione o período climático",
    periodos
)

if periodo_selecionado != "Todos":
    df = df[df["PERIODO"] == periodo_selecionado]


grupo_os = st.sidebar.multiselect(
    "Grupo OS",
    options=sorted(df["GRUPO_OS"].dropna().unique()),
    default=sorted(df["GRUPO_OS"].dropna().unique())
)

df_grupo = df[df["GRUPO_OS"].isin(grupo_os)]

tipo_os = st.sidebar.selectbox(
    "Tipo OS",
    options=["TODOS"] + sorted(df_grupo["TIPO_OS"].dropna().unique())
)

if tipo_os != "TODOS":
    df_f = df_grupo[df_grupo["TIPO_OS"] == tipo_os]
else:
    df_f = df_grupo.copy()


base = st.sidebar.multiselect(
    "Base",
    options=sorted(df_f["BASE"].dropna().unique()),
    default=sorted(df_f["BASE"].dropna().unique())
)

df_f = df_f[df_f["BASE"].isin(base)]

regioes = st.sidebar.multiselect(
    "Região",
    options=sorted(df["REGIAO"].dropna().unique()),
    default=sorted(df["REGIAO"].dropna().unique())
)

#df_f = df[df["REGIAO"].isin(regioes)]
df_f = df_f[df_f["REGIAO"].isin(regioes)]
st.subheader("Distribuição do Tempo Operacional")

def boxplot_por_regiao(df, coluna, titulo):
    dados = []
    labels = []
    medianas = []

    for regiao, g in df.groupby("REGIAO"):
        valores = g[coluna].dropna().values
        if len(valores) > 0:
            dados.append(valores)
            labels.append(regiao)
            medianas.append(np.median(valores))

    fig, ax = plt.subplots(figsize=(12, 5))
    bp = ax.boxplot(dados, labels=labels, showfliers=True)

    for i, med in enumerate(medianas):
        ax.text(
            i + 1,
            med,
            f"{med:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            bbox=dict(
                facecolor="white",
                edgecolor="black",
                boxstyle="round,pad=0.25",
                alpha=0.85
            )
        )

    ax.set_title(titulo)
    ax.set_xlabel("Região")
    ax.set_ylabel("Horas")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    st.pyplot(fig)

boxplot_por_regiao(df_f, "DESLOCAMENTO_HORAS", "Deslocamento por Região (horas)")
boxplot_por_regiao(df_f, "DURACAO_HORAS", "Duração por Região (horas)")
boxplot_por_regiao(df_f, "TMA_HORAS", "TMA – Duração + Deslocamento por Região (horas)")

st.subheader("Distribuição do Tempo Operacional")

metric = st.radio(
    "Métrica",
    ["DESLOCAMENTO_HORAS", "DURACAO_HORAS", "TMA_HORAS"],
    horizontal=True
)

serie = (
    df_f.groupby("ANO_MES")[metric]
    .mean()
    .reset_index()
)

fig, ax = plt.subplots(figsize=(16, 4))
ax.plot(serie["ANO_MES"], serie[metric], marker="o")
ax.set_title(f"Média Mensal – {metric}")
ax.set_xlabel("Mês/Ano")
ax.set_ylabel("Tempo")
ax.tick_params(axis="x", rotation=45)
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)



st.subheader("Demanda Diária por Região")

demanda = (
    df_f.groupby(["REGIAO", "DATA"])
    .size()
    .reset_index(name="QTD_OS")
)

fig, ax = plt.subplots(figsize=(16, 4))

for regiao, g in demanda.groupby("REGIAO"):
    ax.plot(g["DATA"], g["QTD_OS"], label=regiao)

ax.set_title("Demanda diária")
ax.set_xlabel("Data")
ax.set_ylabel("OS por dia")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)



st.subheader("Distribuição do Balde por Região")

regioes = sorted(df_f["REGIAO"].dropna().unique())

pies_por_linha = 3
linhas = range(0, len(regioes), pies_por_linha)

for i in linhas:
    cols = st.columns(pies_por_linha)

    for col, regiao in zip(cols, regioes[i:i + pies_por_linha]):
        with col:
            dist = (
                df_f[df_f["REGIAO"] == regiao]
                .groupby("GRUPO_OS")
                .size()
            )

            fig, ax = plt.subplots(figsize=(4, 4))
            ax.pie(
                dist.values,
                labels=dist.index,
                autopct="%1.1f%%",
                startangle=90
            )
            ax.set_title(regiao)

            st.pyplot(fig)

st.subheader("Comportamento Mensal do TMA")


df_f["MES_NUM"] = df_f["DATA"].dt.month
df_f["MES_NOME"] = df_f["DATA"].dt.strftime("%b")

df_f["MES_NUM"] = df_f["DATA"].dt.month

meses_pt = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}

df_f["MES_NOME"] = df_f["MES_NUM"].map(meses_pt)
ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
df_f["MES_NOME"] = pd.Categorical(df_f["MES_NOME"], categories=ordem_meses, ordered=True)

tma_mensal = (
    df_f.groupby(["MES_NUM", "MES_NOME"])["TMA_HORAS"]
    .mean()
    .reset_index()
    .sort_values("MES_NUM")
)

tma_mensal["PERIODO"] = tma_mensal["MES_NUM"].apply(
    lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
)



referencia_valor = 0.95
referencia_texto = f"Referência TMA: {referencia_valor:.2f} h"

fig, ax = plt.subplots(figsize=(12, 5))

cores = [
    "#d62728" if p == "Período Seco" else "#1f77b4"
    for p in tma_mensal["PERIODO"]
]

ax.bar(tma_mensal["MES_NOME"], tma_mensal["TMA_HORAS"], color=cores)


ax.axhline(
    y=referencia_valor,
    color="#1F1F1F",         
    linestyle="--",           
    linewidth=1.7,
    alpha=0.7,
    zorder=10
)

# Anotação da referência (mais limpa e profissional)

ax.text(0.98, referencia_valor + 0.02, referencia_texto, transform=ax.get_yaxis_transform(),
            fontsize=10, fontweight='bold', ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='#DDDDDD', alpha=0.9))
"""
ax.text(
    x=0.5,                    # um pouco à direita do início
    y=referencia_valor + 0.03,  # um pouco acima da linha
    s=referencia_texto,
    color="#4d4d4d",
    fontsize=10.5,
    fontweight="medium",
    va="bottom",
    ha="left",
    bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, pad=1.8)
)
"""
for spine in ['top']:
        ax.spines[spine].set_visible(False)
ax.set_title("Concentração do Tempo Médio de Atendimento por Mês")
ax.set_xlabel("Mês")
ax.set_ylabel("Média TMA (horas)")
ax.grid(True, linestyle="--", alpha=0.4)

# Opcional: limitar o eixo y para não cortar a anotação (ajuste conforme seus dados)
# ax.set_ylim(0, max(tma_mensal["TMA_HORAS"].max() * 1.15, referencia_valor * 1.4))

st.pyplot(fig)

st.caption(
    "Azul: Período Seco (maio a outubro) | Vermelho: Período Úmido (novembro a abril)\n"
    "Linha tracejada: meta de referência TMA"
)

st.subheader("Incidência de Improcedências")

if "NR_IMPROD" in df_f.columns:

    improd = df_f[df_f["NR_IMPROD"] == "NR IMPROCEDENTE"].copy()

    improd["MES_NUM"] = improd["DATA"].dt.month

    meses_pt = {
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
        12: "Dez"
    }

    improd["MES_NOME"] = improd["MES_NUM"].map(meses_pt)
    ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    improd["MES_NOME"] = pd.Categorical(improd["MES_NOME"], categories=ordem_meses, ordered=True)

    improd_mensal = (
        improd.groupby(["MES_NUM", "MES_NOME"])
        .size()
        .reset_index(name="QTD")
        .sort_values("MES_NUM")
    )

    improd_mensal["PERIODO"] = improd_mensal["MES_NUM"].apply(
        lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
    )

    fig, ax = plt.subplots(figsize=(12,5))

    cores = [
        "#d62728" if p == "Período Seco" else "#1f77b4"
        for p in improd_mensal["PERIODO"]
    ]

    ax.bar(improd_mensal["MES_NOME"], improd_mensal["QTD"], color=cores)

    ax.set_title("Incidência de Improcedências")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Quantidade")
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)

    st.caption(
        "Azul: Período Seco (maio a outubro) | Vermelho: Período Úmido (novembro a abril)"
    )

st.subheader("Incidência de Ligações Novas (LN)")

if "GRUPO_OS" in df_f.columns:

    ln = df_f[df_f["GRUPO_OS"] == "LN"].copy()

    ln["MES_NUM"] = ln["DATA"].dt.month

    meses_pt = {
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
        12: "Dez"
    }

    ln["MES_NOME"] = ln["MES_NUM"].map(meses_pt)

    ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

    ln["MES_NOME"] = pd.Categorical(
        ln["MES_NOME"],
        categories=ordem_meses,
        ordered=True
    )

    ln_mensal = (
        ln.groupby(["MES_NUM", "MES_NOME"])
        .size()
        .reset_index(name="QTD")
        .sort_values("MES_NUM")
    )

    ln_mensal["PERIODO"] = ln_mensal["MES_NUM"].apply(
        lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
    )

    fig, ax = plt.subplots(figsize=(12,5))

    cores = [
        "#d62728" if p == "Período Seco" else "#1f77b4"
        for p in ln_mensal["PERIODO"]
    ]

    ax.bar(ln_mensal["MES_NOME"], ln_mensal["QTD"], color=cores)

    ax.set_title("Incidência de Ligações Novas (LN)")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Quantidade")
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)

    
if "GRUPO_OS" in df_f.columns:

    ln = df_f[df_f["GRUPO_OS"] == "CORTE"].copy()

    ln["MES_NUM"] = ln["DATA"].dt.month

    meses_pt = {
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
        12: "Dez"
    }

    ln["MES_NOME"] = ln["MES_NUM"].map(meses_pt)

    ordem_meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

    ln["MES_NOME"] = pd.Categorical(
        ln["MES_NOME"],
        categories=ordem_meses,
        ordered=True
    )

    ln_mensal = (
        ln.groupby(["MES_NUM", "MES_NOME"])
        .size()
        .reset_index(name="QTD")
        .sort_values("MES_NUM")
    )

    ln_mensal["PERIODO"] = ln_mensal["MES_NUM"].apply(
        lambda x: "Período Seco" if 5 <= x <= 10 else "Período Úmido"
    )

    fig, ax = plt.subplots(figsize=(12,5))

    cores = [
        "#d62728" if p == "Período Seco" else "#1f77b4"
        for p in ln_mensal["PERIODO"]
    ]

    ax.bar(ln_mensal["MES_NOME"], ln_mensal["QTD"], color=cores)

    ax.set_title("Execuções de Suspensões de Fornecimento (CT)")
    ax.set_xlabel("Mês")
    ax.set_ylabel("Quantidade")
    ax.grid(True, linestyle="--", alpha=0.4)

    st.pyplot(fig)