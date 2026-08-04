from pathlib import Path
from datetime import datetime, time

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Análise de Estrutura Operacional",
    page_icon="📊",
    layout="wide",
)

PASTA_APP = Path(__file__).resolve().parent
ARQUIVO = PASTA_APP / "ANALISE_NORTE.xlsx"


def converter_hora(valor):
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, time):
        return pd.Timedelta(
            hours=valor.hour,
            minutes=valor.minute,
            seconds=valor.second,
            microseconds=valor.microsecond,
        )
    if isinstance(valor, (datetime, pd.Timestamp)):
        return pd.Timedelta(
            hours=valor.hour,
            minutes=valor.minute,
            seconds=valor.second,
            microseconds=valor.microsecond,
        )
    if isinstance(valor, (int, float)):
        return pd.to_timedelta(valor, unit="D")
    return pd.to_timedelta(str(valor).replace(",", "."), errors="coerce")


def converter_preco(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return float(valor)
    texto = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return pd.to_numeric(texto, errors="coerce")


def minutos_fora_turno(inicio, fim, inicio_turno, fim_turno):
    if pd.isna(inicio) or pd.isna(fim) or pd.isna(inicio_turno) or pd.isna(fim_turno):
        return np.nan
    duracao = max((fim - inicio).total_seconds() / 60, 0)
    sobreposicao = max(
        (min(fim, fim_turno) - max(inicio, inicio_turno)).total_seconds() / 60,
        0,
    )
    return max(duracao - sobreposicao, 0)


@st.cache_data(show_spinner=False)
def carregar_e_preparar(caminho):
    df = pd.read_excel(caminho, engine="openpyxl")
    df.columns = df.columns.astype(str).str.strip().str.lower()

    obrigatorias = {
        "os", "equipe", "data_turno", "inicio", "fim", "inicio_turno",
        "fim_turno", "data_atribuicao", "preco_a_cobrar", "grupo_os",
        "tipo_os", "desmobilizar", "12h",
    }
    faltantes = sorted(obrigatorias.difference(df.columns))
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(faltantes))

    df["data_turno"] = pd.to_datetime(
        df["data_turno"], dayfirst=True, errors="coerce"
    ).dt.normalize()

    for coluna in ["inicio_turno", "fim_turno", "data_atribuicao"]:
        serie = df[coluna]
        if not pd.api.types.is_datetime64_any_dtype(serie):
            serie = serie.astype(str).str.replace(",", ".", regex=False)
        df[coluna] = pd.to_datetime(serie, dayfirst=True, errors="coerce")

    df["desmobilizar"] = pd.to_numeric(
        df["desmobilizar"], errors="coerce"
    ).fillna(0).astype(int)
    df["12h"] = pd.to_numeric(df["12h"], errors="coerce").fillna(0).astype(int)
    df["preco_a_cobrar"] = df["preco_a_cobrar"].apply(converter_preco).fillna(0.0)

    df["inicio_td"] = df["inicio"].apply(converter_hora)
    df["fim_td"] = df["fim"].apply(converter_hora)

    inicio_turno_td = df["inicio_turno"] - df["inicio_turno"].dt.normalize()
    turno_cruza_meia_noite = (
        df["fim_turno"].dt.normalize() > df["inicio_turno"].dt.normalize()
    )
    atividade_apos_meia_noite = turno_cruza_meia_noite & (
        df["inicio_td"] < inicio_turno_td
    )

    df["inicio_atividade"] = (
        df["data_turno"]
        + df["inicio_td"]
        + pd.to_timedelta(atividade_apos_meia_noite.astype(int), unit="D")
    )

    termina_dia_seguinte = df["fim_td"] < df["inicio_td"]
    df["fim_atividade"] = (
        df["inicio_atividade"].dt.normalize()
        + df["fim_td"]
        + pd.to_timedelta(termina_dia_seguinte.astype(int), unit="D")
    )

    df["duracao_original_min"] = (
        df["fim_atividade"] - df["inicio_atividade"]
    ).dt.total_seconds().div(60)

    duracao_valida = df["duracao_original_min"].where(
        df["duracao_original_min"].between(1, 720)
    )
    mediana_detalhada = duracao_valida.groupby(
        [df["cidade_equipe"]] if "cidade_equipe" in df else [df["equipe"].astype(str).str.slice(3, 6), df["grupo_os"], df["tipo_os"]]
    ).transform("median")
    mediana_tipo = duracao_valida.groupby(df["tipo_os"]).transform("median")
    mediana_global = duracao_valida.median()
    if pd.isna(mediana_global):
        mediana_global = 30.0

    df["duracao_modelo_min"] = (
        duracao_valida
        .fillna(mediana_detalhada)
        .fillna(mediana_tipo)
        .fillna(mediana_global)
        .clip(lower=1, upper=720)
    )

    df["cidade_equipe"] = (
        df["equipe"].astype("string").str.slice(3, 6).str.upper()
    )
    df["fim_turno_proposto"] = df["fim_turno"] + pd.to_timedelta(
        df["12h"].eq(1).astype(int) * 2, unit="h"
    )

    df = df.sort_values(["equipe", "data_turno", "inicio_atividade", "os"])
    chaves = ["equipe", "data_turno"]
    df["ordem_execucao"] = df.groupby(chaves).cumcount() + 1
    df["fim_anterior"] = df.groupby(chaves)["fim_atividade"].shift(1)
    df["intervalo_entre_atividades_min"] = (
        df["inicio_atividade"] - df["fim_anterior"]
    ).dt.total_seconds().div(60)
    df["sobreposicao"] = df["intervalo_entre_atividades_min"].lt(0)
    df["intervalo_entre_atividades_min"] = df[
        "intervalo_entre_atividades_min"
    ].clip(lower=0)

    df["primeira_atividade"] = df["ordem_execucao"].eq(1)
    df["tempo_primeiro_servico_min"] = np.where(
        df["primeira_atividade"],
        (df["inicio_atividade"] - df["inicio_turno"]).dt.total_seconds() / 60,
        np.nan,
    )
    df["tempo_primeiro_servico_min"] = df[
        "tempo_primeiro_servico_min"
    ].clip(lower=0)

    df["hora_extra_atual_min"] = df.apply(
        lambda r: minutos_fora_turno(
            r["inicio_atividade"], r["fim_atividade"],
            r["inicio_turno"], r["fim_turno"]
        ),
        axis=1,
    ).fillna(0)

    return df


def criar_base_equipe_dia(df):
    base = (
        df.groupby(
            ["cidade_equipe", "data_turno", "equipe", "desmobilizar", "12h"],
            as_index=False,
        )
        .agg(
            atividades=("os", "count"),
            carga_min=("duracao_modelo_min", "sum"),
            receita=("preco_a_cobrar", "sum"),
            hora_extra_min=("hora_extra_atual_min", "sum"),
            primeiro_servico_min=("tempo_primeiro_servico_min", "max"),
            intervalo_medio_min=("intervalo_entre_atividades_min", "mean"),
        )
    )
    base["capacidade_atual_min"] = 480.0
    base["capacidade_proposta_min"] = np.where(base["12h"].eq(1), 720.0, 480.0)
    base["utilizacao_atual"] = base["carga_min"] / base["capacidade_atual_min"]
    base["tempo_sem_execucao_atual_min"] = (
        base["capacidade_atual_min"] - base["carga_min"]
    ).clip(lower=0)
    return base


@st.cache_data(show_spinner=False)
def simular_redistribuicao(df):
    base = criar_base_equipe_dia(df)
    mantidas = base[base["desmobilizar"].eq(0)].copy()
    removidas = df[df["desmobilizar"].eq(1)].copy()

    cargas = {
        (r.cidade_equipe, r.data_turno, r.equipe): float(r.carga_min)
        for r in mantidas.itertuples()
    }
    capacidades = {
        (r.cidade_equipe, r.data_turno, r.equipe): float(r.capacidade_proposta_min)
        for r in mantidas.itertuples()
    }

    resultados = []
    removidas = removidas.sort_values(
        ["data_turno", "cidade_equipe", "data_atribuicao", "inicio_atividade"]
    )

    for r in removidas.itertuples():
        chaves = [
            chave for chave in cargas
            if chave[0] == r.cidade_equipe and chave[1] == r.data_turno
        ]
        duracao = float(r.duracao_modelo_min)
        elegiveis = [
            chave for chave in chaves
            if cargas[chave] + duracao <= capacidades[chave]
        ]

        if elegiveis:
            destino = min(
                elegiveis,
                key=lambda chave: (
                    cargas[chave] / capacidades[chave],
                    cargas[chave],
                    chave[2],
                ),
            )
            cargas[destino] += duracao
            status = "Absorvida"
            equipe_destino = destino[2]
        else:
            status = "Não absorvida"
            equipe_destino = None

        resultados.append({
            "os": r.os,
            "cidade_equipe": r.cidade_equipe,
            "data_turno": r.data_turno,
            "equipe_origem": r.equipe,
            "equipe_destino": equipe_destino,
            "duracao_min": duracao,
            "receita": float(r.preco_a_cobrar),
            "status": status,
        })

    redistribuicao = pd.DataFrame(resultados)
    carga_final = pd.DataFrame([
        {
            "cidade_equipe": chave[0],
            "data_turno": chave[1],
            "equipe": chave[2],
            "carga_proposta_min": carga,
            "capacidade_proposta_min": capacidades[chave],
        }
        for chave, carga in cargas.items()
    ])
    if not carga_final.empty:
        carga_final["utilizacao_proposta"] = (
            carga_final["carga_proposta_min"] /
            carga_final["capacidade_proposta_min"]
        )
        carga_final["tempo_sem_execucao_proposto_min"] = (
            carga_final["capacidade_proposta_min"] -
            carga_final["carga_proposta_min"]
        ).clip(lower=0)

    return base, redistribuicao, carga_final


def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def percentual(valor):
    return f"{valor:.1%}" if pd.notna(valor) else "–"


def classificar_risco(utilizacao, nao_absorvida):
    if nao_absorvida > 0 or utilizacao > 0.95:
        return "Alto"
    if utilizacao > 0.85:
        return "Moderado"
    return "Baixo"


st.title("Análise de Estrutura Operacional")
st.caption("Comparação entre a estrutura atual e o cenário com desmobilizações e turnos de 12 horas")

if not ARQUIVO.exists():
    st.error(f"Arquivo não encontrado: {ARQUIVO}")
    st.stop()

try:
    with st.spinner("Processando a operação e simulando a redistribuição..."):
        dados = carregar_e_preparar(ARQUIVO)
except Exception as erro:
    st.error("Não foi possível carregar ou preparar o arquivo.")
    st.exception(erro)
    st.stop()

cidades = sorted(dados["cidade_equipe"].dropna().unique().tolist())
datas_validas = dados["data_turno"].dropna()

with st.sidebar:
    st.header("Filtros")
    cidades_selecionadas = st.multiselect(
        "Cidades", cidades, default=cidades
    )
    data_inicial = st.date_input("Data inicial", datas_validas.min().date())
    data_final = st.date_input("Data final", datas_validas.max().date())

if data_inicial > data_final:
    st.error("A data inicial não pode ser posterior à data final.")
    st.stop()

filtro = (
    dados["cidade_equipe"].isin(cidades_selecionadas)
    & dados["data_turno"].between(pd.Timestamp(data_inicial), pd.Timestamp(data_final))
)
df = dados.loc[filtro].copy()

if df.empty:
    st.warning("Não existem dados para os filtros selecionados.")
    st.stop()

base, redistribuicao, carga_proposta = simular_redistribuicao(df)

cap_atual = base["capacidade_atual_min"].sum()
carga_atual = base["carga_min"].sum()
util_atual = carga_atual / cap_atual if cap_atual else np.nan
he_atual = base["hora_extra_min"].sum()

cap_proposta = carga_proposta["capacidade_proposta_min"].sum() if not carga_proposta.empty else 0
carga_prop = carga_proposta["carga_proposta_min"].sum() if not carga_proposta.empty else 0
util_prop = carga_prop / cap_proposta if cap_proposta else np.nan

absorvidas = redistribuicao["status"].eq("Absorvida").sum() if not redistribuicao.empty else 0
nao_absorvidas = redistribuicao["status"].eq("Não absorvida").sum() if not redistribuicao.empty else 0
min_nao_absorvidos = (
    redistribuicao.loc[redistribuicao["status"].eq("Não absorvida"), "duracao_min"].sum()
    if not redistribuicao.empty else 0
)
receita_nao_absorvida = (
    redistribuicao.loc[redistribuicao["status"].eq("Não absorvida"), "receita"].sum()
    if not redistribuicao.empty else 0
)

st.subheader("Resultado executivo")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Utilização atual", percentual(util_atual))
c2.metric("Utilização proposta", percentual(util_prop), percentual(util_prop - util_atual))
c3.metric("OS redistribuídas", f"{absorvidas:,}".replace(",", "."))
c4.metric("OS não absorvidas", f"{nao_absorvidas:,}".replace(",", "."))
c5.metric("HE para zerar excedente", f"{min_nao_absorvidos / 60:,.1f} h".replace(",", "X").replace(".", ",").replace("X", "."))

comparacao = pd.DataFrame({
    "Indicador": [
        "Equipes-dia disponíveis",
        "Capacidade produtiva (h)",
        "Carga executada/absorvida (h)",
        "Utilização",
        "Tempo sem execução estimado (h)",
    ],
    "Estrutura atual": [
        len(base),
        cap_atual / 60,
        carga_atual / 60,
        util_atual,
        base["tempo_sem_execucao_atual_min"].sum() / 60,
    ],
    "Estrutura proposta": [
        len(carga_proposta),
        cap_proposta / 60,
        carga_prop / 60,
        util_prop,
        carga_proposta["tempo_sem_execucao_proposto_min"].sum() / 60 if not carga_proposta.empty else 0,
    ],
})

st.dataframe(
    comparacao.style.format({
        "Estrutura atual": "{:,.2f}",
        "Estrutura proposta": "{:,.2f}",
    }),
    hide_index=True,
    use_container_width=True,
)

st.subheader("Impacto por cidade")
atual_cidade = base.groupby("cidade_equipe", as_index=False).agg(
    capacidade_atual_min=("capacidade_atual_min", "sum"),
    carga_atual_min=("carga_min", "sum"),
    hora_extra_atual_min=("hora_extra_min", "sum"),
    primeiro_servico_medio_min=("primeiro_servico_min", "mean"),
    intervalo_medio_min=("intervalo_medio_min", "mean"),
    receita_atual=("receita", "sum"),
)
atual_cidade["utilizacao_atual"] = (
    atual_cidade["carga_atual_min"] / atual_cidade["capacidade_atual_min"]
)

if not carga_proposta.empty:
    proposta_cidade = carga_proposta.groupby("cidade_equipe", as_index=False).agg(
        capacidade_proposta_min=("capacidade_proposta_min", "sum"),
        carga_proposta_min=("carga_proposta_min", "sum"),
    )
    proposta_cidade["utilizacao_proposta"] = (
        proposta_cidade["carga_proposta_min"] /
        proposta_cidade["capacidade_proposta_min"]
    )
else:
    proposta_cidade = pd.DataFrame(columns=[
        "cidade_equipe", "capacidade_proposta_min", "carga_proposta_min",
        "utilizacao_proposta"
    ])

1if not redistribuicao.empty:
    red_cidade = redistribuicao.groupby("cidade_equipe", as_index=False).agg(
        os_redistribuidas=("status", lambda s: s.eq("Absorvida").sum()),
        os_nao_absorvidas=("status", lambda s: s.eq("Não absorvida").sum()),
        receita_em_risco=("receita", lambda s: s[redistribuicao.loc[s.index, "status"].eq("Não absorvida")].sum()),
        minutos_nao_absorvidos=("duracao_min", lambda s: s[redistribuicao.loc[s.index, "status"].eq("Não absorvida")].sum()),
    )
else:
    red_cidade = pd.DataFrame(columns=[
        "cidade_equipe", "os_redistribuidas", "os_nao_absorvidas",
        "receita_em_risco", "minutos_nao_absorvidos"
    ])

impacto = (
    atual_cidade
    .merge(proposta_cidade, on="cidade_equipe", how="outer")
    .merge(red_cidade, on="cidade_equipe", how="left")
    .fillna(0)
)
impacto["risco"] = impacto.apply(
    lambda r: classificar_risco(r["utilizacao_proposta"], r["os_nao_absorvidas"]),
    axis=1,
)

exibicao = impacto[[
    "cidade_equipe", "utilizacao_atual", "utilizacao_proposta",
    "os_redistribuidas", "os_nao_absorvidas", "hora_extra_atual_min",
    "primeiro_servico_medio_min", "intervalo_medio_min", "receita_em_risco", "risco"
]].rename(columns={
    "cidade_equipe": "Cidade",
    "utilizacao_atual": "Utilização atual",
    "utilizacao_proposta": "Utilização proposta",
    "os_redistribuidas": "OS redistribuídas",
    "os_nao_absorvidas": "OS não absorvidas",
    "hora_extra_atual_min": "HE atual (min)",
    "primeiro_servico_medio_min": "Primeiro serviço (min)",
    "intervalo_medio_min": "Intervalo médio (min)",
    "receita_em_risco": "Receita em risco",
    "risco": "Risco",
})

st.dataframe(
    exibicao.style.format({
        "Utilização atual": "{:.1%}",
        "Utilização proposta": "{:.1%}",
        "OS redistribuídas": "{:,.0f}",
        "OS não absorvidas": "{:,.0f}",
        "HE atual (min)": "{:,.0f}",
        "Primeiro serviço (min)": "{:,.1f}",
        "Intervalo médio (min)": "{:,.1f}",
        "Receita em risco": lambda v: moeda(v),
    }),
    hide_index=True,
    use_container_width=True,
)

grafico_utilizacao = impacto.set_index("cidade_equipe")[[
    "utilizacao_atual", "utilizacao_proposta"
]].rename(columns={
    "utilizacao_atual": "Atual",
    "utilizacao_proposta": "Proposta",
})
st.bar_chart(grafico_utilizacao, y_label="Utilização", x_label="Cidade")

st.subheader("Demanda das equipes desmobilizadas")
g1, g2, g3 = st.columns(3)
total_removidas = len(redistribuicao)
taxa_absorcao = absorvidas / total_removidas if total_removidas else 1.0
g1.metric("Taxa de absorção", percentual(taxa_absorcao))
g2.metric("Carga não absorvida", f"{min_nao_absorvidos / 60:,.1f} h".replace(",", "X").replace(".", ",").replace("X", "."))
g3.metric("Receita em risco", moeda(receita_nao_absorvida))

st.caption(
    "Premissas: equipes da mesma cidade são intercambiáveis; turnos regulares possuem "
    "8 horas produtivas e turnos marcados como 12h possuem 12 horas produtivas. "
    "Deslocamento não é estimado por falta de coordenadas. Equipes-dia sem qualquer "
    "atividade não aparecem na fonte e, portanto, não entram na capacidade observada."
)
