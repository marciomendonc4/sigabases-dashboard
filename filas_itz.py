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
# DATETIME (ROBUST)
# =========================
df["CRIACAO_TS"] = pd.to_datetime(df["CRIACAO_TS"], errors="coerce")
df["ATRIBUICAO_TS"] = pd.to_datetime(df["ATRIBUICAO_TS"], errors="coerce")
df["INICIO_TS"] = pd.to_datetime(df["INICIO_TS"], errors="coerce")

# remove broken rows
df = df.dropna(subset=["ATRIBUICAO_TS", "INICIO_TS"])

# =========================
# FEATURES
# =========================
df["hora_atr"] = df["ATRIBUICAO_TS"].dt.floor("h")
df["hora_ini"] = df["INICIO_TS"].dt.floor("h")

df["hora_dia"] = df["ATRIBUICAO_TS"].dt.hour
df["hora_ini_dia"] = df["INICIO_TS"].dt.hour

# waiting time (minutes)
df["fila_min"] = (df["INICIO_TS"] - df["ATRIBUICAO_TS"]).dt.total_seconds() / 60

# COI delay (minutes)
df["coi_min"] = (df["ATRIBUICAO_TS"] - df["CRIACAO_TS"]).dt.total_seconds() / 60

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
# AGGREGATIONS (AVERAGE DAY)
# =========================

# Demand vs capacity
demanda_hora = df.groupby("hora_dia").size()
capacidade_hora = df.groupby("hora_ini_dia").size()

# Waiting time
fila_hora = df.groupby("hora_dia")["fila_min"].mean()

# COI vs Field
coi_hora = df.groupby("hora_dia")["coi_min"].mean()
field_hora = df.groupby("hora_dia")["fila_min"].mean()

# =========================
# PLOTS
# =========================

# ---- 1. Demand vs Capacity
st.subheader("Demanda vs Capacidade (Perfil Médio Diário)")

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(demanda_hora.index, demanda_hora.values, label="Atribuições")
ax.plot(capacidade_hora.index, capacidade_hora.values, label="Inícios")

ax.set_xticks(range(24))
ax.set_xlabel("Hora do dia")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)

# ---- 2. Waiting Time
st.subheader("Tempo Médio de Espera por Hora")

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(fila_hora.index, fila_hora.values)

ax.set_xticks(range(24))
ax.set_xlabel("Hora do dia")
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)

# ---- 3. COI vs Field Delay
st.subheader("Decomposição do Tempo de Espera (COI vs Campo)")

fig, ax = plt.subplots(figsize=(10, 5))

ax.plot(coi_hora.index, coi_hora.values, label="COI")
ax.plot(field_hora.index, field_hora.values, label="Campo")

ax.set_xticks(range(24))
ax.set_xlabel("Hora do dia")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig)