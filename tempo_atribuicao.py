import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

@st.cache_data
def load_data():
    df = pd.read_parquet("tempo_atribuicao.parquet")
    df['DATA_ATRIBUICAO'] = pd.to_datetime(df['DATA_ATRIBUICAO'], dayfirst=True)
    df['hour'] = df['DATA_ATRIBUICAO'].dt.hour
    df['date'] = df['DATA_ATRIBUICAO'].dt.date
    return df

df = load_data()

st.title("Distribuição de Atribuições – Análise de Gargalos")

# ── Cascading Filters ──────────────────────────────────────────────
# ── Cascading Filters (safe version) ──────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")

    # Estado
    estados = sorted(df['estado'].unique())
    sel_estado = st.multiselect("Estado", options=estados, default=estados)

    # Regional
    df_f = df[df['estado'].isin(sel_estado)] if sel_estado else df.copy()
    regionais = sorted(df_f['regional'].unique()) if not df_f.empty else []
    sel_regional = st.multiselect("Regional", options=regionais, default=regionais)

    # Base
    df_f = df_f[df_f['regional'].isin(sel_regional)] if sel_regional else df_f.copy()
    bases = sorted(df_f['base'].unique()) if not df_f.empty else []
    sel_base = st.multiselect("Base", options=bases, default=bases)

    # Sigla
    df_f = df_f[df_f['base'].isin(sel_base)] if sel_base else df_f.copy()
    siglas = sorted(df_f['sigla'].unique()) if not df_f.empty else []
    sel_sigla = st.multiselect("Sigla", options=siglas, default=siglas)

    # Tipo OS
    df_f = df_f[df_f['sigla'].isin(sel_sigla)] if sel_sigla else df_f.copy()
    tipos = sorted(df_f['tipo_os'].unique()) if not df_f.empty else []
    sel_tipo = st.multiselect("Tipo OS", options=tipos, default=tipos)

    # Grupo OS
    df_f = df_f[df_f['tipo_os'].isin(sel_tipo)] if sel_tipo else df_f.copy()
    grupos = sorted(df_f['grupo_os'].dropna().astype(str).unique()) if not df_f.empty else []
    sel_grupo = st.multiselect("Grupo OS", options=grupos, default=grupos)


# Apply filters
# Apply all filters
filtered = df
if sel_estado:   filtered = filtered[filtered['estado'].isin(sel_estado)]
if sel_regional: filtered = filtered[filtered['regional'].isin(sel_regional)]
if sel_base:     filtered = filtered[filtered['base'].isin(sel_base)]
if sel_sigla:    filtered = filtered[filtered['sigla'].isin(sel_sigla)]
if sel_tipo:     filtered = filtered[filtered['tipo_os'].isin(sel_tipo)]
if sel_grupo:    filtered = filtered[filtered['grupo_os'].isin(sel_grupo)]

if filtered.empty:
    st.warning("Nenhum dado corresponde à combinação de filtros selecionada.")
    st.stop()


if filtered.empty:
    st.warning("Nenhum dado após os filtros.")
    st.stop()

# ── Histogram: Hour of day ─────────────────────────────────────────
st.subheader("Distribuição por Hora do Dia")

fig_hist, ax_hist = plt.subplots(figsize=(9, 5))
counts, bins, _ = ax_hist.hist(
    filtered['hour'], 
    bins=np.arange(0, 25, 1), 
    edgecolor='black', 
    alpha=0.75
)
ax_hist.set_xlabel("Hora do dia (0–23)")
ax_hist.set_ylabel("Quantidade de atribuições")
ax_hist.set_title("Volume de atribuições por hora")
ax_hist.set_xticks(range(0, 24, 2))
ax_hist.grid(True, axis='y', alpha=0.3, linestyle='--')

for i in range(len(counts)):
    if counts[i] > 0:
        ax_hist.text(bins[i] + 0.4, counts[i] + max(counts)*0.01, 
                     str(int(counts[i])), ha='center', fontsize=9)

st.pyplot(fig_hist)

# ── Bottlenecks: Tipo OS ───────────────────────────────────────────
st.subheader("Gargalos por Tipo OS")

n_days = filtered['date'].nunique()
if n_days > 0:
    by_tipo = (
        filtered.groupby('tipo_os')
        .size()
        .reset_index(name='Total')
        .sort_values('Total', ascending=False)
    )
    by_tipo['Média Diária'] = (by_tipo['Total'] / n_days).round(1)
    by_tipo['% do Total'] = (by_tipo['Total'] / by_tipo['Total'].sum() * 100).round(1)

    # Bar chart - Top 10 or all if few
    top_tipo = by_tipo.head(12)  # adjust if you have many tipos
    fig_tipo, ax_tipo = plt.subplots(figsize=(9, 5.5))
    bars = ax_tipo.barh(top_tipo['tipo_os'], top_tipo['Média Diária'], color='cornflowerblue')
    ax_tipo.set_xlabel("Média diária de atribuições")
    ax_tipo.set_title(f"Média diária por Tipo OS ({n_days} dias)")
    ax_tipo.invert_yaxis()
    ax_tipo.grid(True, axis='x', alpha=0.3, linestyle='--')

    for bar in bars:
        width = bar.get_width()
        ax_tipo.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                     f'{width:.1f}', va='center', fontsize=10)

    st.pyplot(fig_tipo)

    st.caption("Tabela detalhada:")
    st.dataframe(by_tipo[['tipo_os', 'Média Diária', 'Total', '% do Total']], 
                 hide_index=True, use_container_width=True)

# ── Bottlenecks: Grupo OS ──────────────────────────────────────────
st.subheader("Gargalos por Grupo OS")

by_grupo = (
    filtered.groupby('grupo_os')
    .size()
    .reset_index(name='Total')
    .sort_values('Total', ascending=False)
)
by_grupo['Média Diária'] = (by_grupo['Total'] / n_days).round(1)
by_grupo['% do Total'] = (by_grupo['Total'] / by_grupo['Total'].sum() * 100).round(1)

top_grupo = by_grupo.head(10)
fig_grupo, ax_grupo = plt.subplots(figsize=(9, 5))
bars_g = ax_grupo.barh(top_grupo['grupo_os'], top_grupo['Média Diária'], color='lightcoral')
ax_grupo.set_xlabel("Média diária de atribuições")
ax_grupo.set_title(f"Média diária por Grupo OS ({n_days} dias)")
ax_grupo.invert_yaxis()
ax_grupo.grid(True, axis='x', alpha=0.3, linestyle='--')

for bar in bars_g:
    width = bar.get_width()
    ax_grupo.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                  f'{width:.1f}', va='center', fontsize=10)

st.pyplot(fig_grupo)

st.caption("Tabela detalhada:")
st.dataframe(by_grupo[['grupo_os', 'Média Diária', 'Total', '% do Total']], 
             hide_index=True, use_container_width=True)

# Footer info
st.caption(
    f"Período: {filtered['date'].min():%d/%m/%Y} – {filtered['date'].max():%d/%m/%Y} "
    f"• {n_days} dias • {len(filtered):,} atribuições"
)