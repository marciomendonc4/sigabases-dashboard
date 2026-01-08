import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import pyodbc

st.set_page_config(
    layout="wide",
    page_title="Distribuição do TMA"
)

@st.cache_data
def load_data():
    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={st.secrets['DB_SERVER']};"
        f"DATABASE={st.secrets['DB_DATABASE']};"
        f"UID={st.secrets['DB_USER']};"
        f"PWD={st.secrets['DB_PASSWORD']};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=50;"
    )
    df = pd.read_sql("SELECT * FROM v_desvio_padrao", conn)
    conn.close()
    return df

df = load_data()

st.title("Distribuição do Tempo Médio de Atendimento")

st.markdown("""
**Como interpretar o gráfico:**  
Cada caixa representa a distribuição do tempo médio de atendimento por regional.  
A linha central indica a mediana. Quanto maior a caixa, maior a variabilidade dos tempos.  
Valores extremos indicam maior dispersão entre as regionais.
""")

tipos = sorted(df['tipo_os'].dropna().unique().tolist())
tipos.insert(0, "NR's")

selected_tipo = st.selectbox(
    "Selecione o tipo de OS",
    tipos
)

if selected_tipo == "NR's":
    df_plot = df[df['tipo_os'].isin(['NR IMPROD', 'NR IND', 'NR COL'])].copy()
else:
    df_plot = df[df['tipo_os'] == selected_tipo].copy()

grouped = (
    df_plot
    .groupby('regional_nome')['media']
    .apply(list)
    .sort_index()
)

fig1, ax1 = plt.subplots(figsize=(12, 6))

bp = ax1.boxplot(
    grouped.values,
    labels=grouped.index.tolist(),
    patch_artist=True,
    boxprops=dict(facecolor="#1f77b4", alpha=0.5),
    medianprops=dict(color='black', linewidth=2)
)

for median in bp['medians']:
    x, y = median.get_xydata()[1]
    ax1.text(x, y, f"{y:.2f}", ha='center', va='bottom', fontsize=9)

ax1.set_title(f"Distribuição do tempo de atendimento - {selected_tipo}")
ax1.set_xlabel("Regional")
ax1.set_ylabel("Média (h)")
ax1.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig1)

st.markdown("---")

df_plot['mes'] = pd.to_datetime(df_plot['data']).dt.to_period('M').astype(str)

df_linha = (
    df_plot
    .groupby(['mes', 'regional_nome'], as_index=False)['media']
    .mean()
)

fig2, ax2 = plt.subplots(figsize=(12, 5))

for regional, grp in df_linha.groupby('regional_nome'):
    ax2.plot(grp['mes'], grp['media'], marker='o', label=regional)

ax2.set_title(f"Evolução mensal do tempo médio de atendimento - {selected_tipo}")
ax2.set_xlabel("Mês")
ax2.set_ylabel("Média (h)")
ax2.legend(title="Regional", bbox_to_anchor=(1.05, 1), loc='upper left')
ax2.grid(True, linestyle="--", alpha=0.4)

st.pyplot(fig2)
