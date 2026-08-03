import pandas as pd
import numpy as np
from datetime import datetime, time

ARQUIVO = "ANALISE_NORTE.xlsx"


def converter_hora(valor):
    if pd.isna(valor):
        return pd.NaT

    if isinstance(valor, time):
        return pd.Timedelta(
            hours=valor.hour,
            minutes=valor.minute,
            seconds=valor.second,
            microseconds=valor.microsecond
        )

    if isinstance(valor, (datetime, pd.Timestamp)):
        return pd.Timedelta(
            hours=valor.hour,
            minutes=valor.minute,
            seconds=valor.second,
            microseconds=valor.microsecond
        )

    if isinstance(valor, (int, float)):
        return pd.to_timedelta(valor, unit="D")

    texto = str(valor).replace(",", ".")
    return pd.to_timedelta(texto)


def preparar_dados(caminho):
    df = pd.read_excel(caminho)

    df.columns = (
        df.columns
          .str.strip()
          .str.lower()
    )

    df["data_turno"] = pd.to_datetime(
        df["data_turno"],
        dayfirst=True,
        errors="coerce"
    ).dt.normalize()

    for coluna in ["inicio_turno", "fim_turno", "data_atribuicao"]:
        df[coluna] = pd.to_datetime(
            df[coluna].astype(str).str.replace(",", ".", regex=False),
            dayfirst=True,
            errors="coerce"
        )

    df["inicio_td"] = df["inicio"].apply(converter_hora)
    df["fim_td"] = df["fim"].apply(converter_hora)

    df["turno_cruza_meia_noite"] = (
        df["fim_turno"].dt.date >
        df["inicio_turno"].dt.date
    )

    atividade_apos_meia_noite = (
        df["turno_cruza_meia_noite"]
        & (df["inicio_td"] < (df["inicio_turno"] - df["inicio_turno"].dt.normalize()))
    )

    df["inicio_atividade"] = (
        df["data_turno"]
        + df["inicio_td"]
        + pd.to_timedelta(atividade_apos_meia_noite.astype(int), unit="D")
    )

    atividade_termina_dia_seguinte = (
        df["fim_td"] < df["inicio_td"]
    )

    df["fim_atividade"] = (
        df["inicio_atividade"].dt.normalize()
        + df["fim_td"]
        + pd.to_timedelta(
            atividade_termina_dia_seguinte.astype(int),
            unit="D"
        )
    )

    df["duracao_atividade_min"] = (
        df["fim_atividade"] - df["inicio_atividade"]
    ).dt.total_seconds().div(60)

    df["fim_turno_cenario"] = df["fim_turno"]

    df.loc[df["12h"].eq(1), "fim_turno_cenario"] = (
        df.loc[df["12h"].eq(1), "fim_turno"]
        + pd.Timedelta(hours=2)
    )

    df["cidade_equipe"] = (
        df["equipe"]
          .astype("string")
          .str.slice(3, 6)
          .str.upper()
    )

    df["preco_a_cobrar"] = pd.to_numeric(
        df["preco_a_cobrar"]
          .astype(str)
          .str.replace(".", "", regex=False)
          .str.replace(",", ".", regex=False),
        errors="coerce"
    ).fillna(0)

    df["desmobilizar"] = pd.to_numeric(
        df["desmobilizar"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["12h"] = pd.to_numeric(
        df["12h"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["duracao_zero"] = df["duracao_atividade_min"].eq(0)

    df["duracao_invalida"] = (
        df["duracao_atividade_min"].isna()
        | df["duracao_atividade_min"].lt(0)
        | df["duracao_atividade_min"].gt(12 * 60)
    )

    return df


df = preparar_dados(ARQUIVO)

print(df[[
    "os",
    "equipe",
    "cidade_equipe",
    "inicio_atividade",
    "fim_atividade",
    "duracao_atividade_min",
    "inicio_turno",
    "fim_turno",
    "fim_turno_cenario",
    "desmobilizar",
    "12h"
]].head())