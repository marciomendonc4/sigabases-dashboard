import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="Análise de Filas")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("TEORIA_FILAS_ITZ.xlsx")
    return df

df = load_data()

# =========================
# DATETIME + FEATURES
# =========================
df["CRIACAO_TS"] = pd.to_datetime(df["CRIACAO_TS"], errors="coerce")
df["ATRIBUICAO_TS"] = pd.to_datetime(df["ATRIBUICAO_TS"], errors="coerce")
df["INICIO_TS"] = pd.to_datetime(df["INICIO_TS"], errors="coerce")

st.write(df[["ATRIBUICAO_TS"]].dtypes)

# Drop broken rows (important)
df = df.dropna(subset=["ATRIBUICAO_TS", "INICIO_TS"])

# Hour buckets
df["hora_atr"] = df["ATRIBUICAO_TS"].dt.floor("h")
df["hora_ini"] = df["INICIO_TS"].dt.floor("h")

# Waiting time (minutes)
df["fila_min"] = (df["INICIO_TS"] - df["ATRIBUICAO_TS"]).dt.total_seconds() / 60

# COI vs Field delay
df["coi_min"] = (df["ATRIBUICAO_TS"] - df["CRIACAO_TS"]).dt.total_seconds() / 60
df["field_min"] = df["fila_min"]

# =========================
# FILTERS
# =========================
st.title("Análise de Filas Operacionais")

col1, col2 = st.columns(2)

with col1:
    cidades = sorted(df["CIDADE"].dropna().unique())
    cidade_sel = st.selectbox("Cidade", cidades)

with col2:
    data_min = df["ATRIBUICAO_TS"].min().date()
    data_max = df["ATRIBUICAO_TS"].max().date()
    periodo = st.date_input("Período", [data_min, data_max])

df = df[df["CIDADE"] == cidade_sel]

if len(periodo) == 2:
    df = df[
        (df["ATRIBUICAO_TS"].dt.date >= periodo[0]) &
        (df["ATRIBUICAO_TS"].dt.date <= periodo[1])
    ]

# =========================
# DEMAND vs CAPACITY
# =========================
demanda = df.groupby("hora_atr").size()
capacidade = df.groupby("hora_ini").size()

fluxo = pd.concat([demanda, capacidade], axis=1).fillna(0)
fluxo.columns = ["atribuicoes", "inicios"]
fluxo = fluxo.sort_index()

# =========================
# BACKLOG
# =========================
fluxo["backlog"] = fluxo["atribuicoes"].cumsum() - fluxo["inicios"].cumsum()

# =========================
# WAITING TIME
# =========================
fila = df.groupby("hora_atr")["fila_min"].mean()

# =========================
# COI vs FIELD DELAY
# =========================
delay = df.groupby("hora_atr")[["coi_min", "field_min"]].mean()

# =========================
# PLOTS
# =========================

# ---- 1. Demand vs Capacity
st.subheader("Demanda vs Capacidade")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(fluxo.index, fluxo["atribuicoes"], label="Atribuições")
ax.plot(fluxo.index, fluxo["inicios"], label="Inícios")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)
st.pyplot(fig)

# ---- 2. Backlog
st.subheader("Backlog (Fila Acumulada)")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(fluxo.index, fluxo["backlog"])
ax.grid(True, linestyle="--", alpha=0.4)
st.pyplot(fig)

# ---- 3. Waiting Time
st.subheader("Tempo Médio de Espera")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(fila.index, fila.values)
ax.grid(True, linestyle="--", alpha=0.4)
st.pyplot(fig)

# ---- 4. COI vs Field Delay
st.subheader("Decomposição do Tempo de Espera (COI vs Campo)")

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(delay.index, delay["coi_min"], label="COI")
ax.plot(delay.index, delay["field_min"], label="Campo")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)
st.pyplot(fig)