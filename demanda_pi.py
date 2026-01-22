import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Função para converter strings de tempo em minutos
def tempo_para_minutos(t):
    if pd.isna(t) or ':' not in str(t):
        return 0
    try:
        partes = str(t).split(':')
        if len(partes) == 2:
            h, m = map(int, partes)
            return h * 60 + m
        else:
            return 0
    except:
        return 0

# Carregar e processar os dados
@st.cache_data
def carregar_dados(caminho_arquivo='V_TEORIA_DAS_FILAS.xlsx'):
    df = pd.read_excel(caminho_arquivo, sheet_name='TEORIA_DAS_FILAS')
    
    # Converter DATA para numérico e depois para datetime (Excel serial date)
    df['DATA'] = pd.to_numeric(df['DATA'], errors='coerce')
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', origin='1899-12-30', unit='D')
    
    # Converter ATRIBUICAO
    df['ATRIBUICAO_DT'] = pd.to_datetime(df['ATRIBUICAO'], errors='coerce')
    
    # Criar INICIO_DT com cuidado
    def criar_inicio_dt(row):
        if pd.isna(row['DATA']) or pd.isna(row['HORA_INICIO']):
            return pd.NaT
        try:
            hora = int(float(row['HORA_INICIO']))  # aceita float também
            return row['DATA'].replace(hour=hora, minute=0, second=0, microsecond=0)
        except:
            return pd.NaT
    
    df['INICIO_DT'] = df.apply(criar_inicio_dt, axis=1)
    
    # Cálculo de tempo de espera com proteção
    df['TEMPO_ESPERA_MIN'] = 0.0
    mask = df['INICIO_DT'].notna() & df['ATRIBUICAO_DT'].notna()
    df.loc[mask, 'TEMPO_ESPERA_MIN'] = (
        (df.loc[mask, 'INICIO_DT'] - df.loc[mask, 'ATRIBUICAO_DT'])
        .dt.total_seconds() / 60
    )
    
    # Colunas de tempo de serviço
    df['DURACAO_MIN'] = df['DURACAO'].apply(tempo_para_minutos)
    df['DESLOCAMENTO_MIN'] = df['DESLOCAMENTO'].apply(tempo_para_minutos)
    df['TEMPO_SERVICO_MIN'] = df['DURACAO_MIN'] + df['DESLOCAMENTO_MIN']
    df['TEMPO_SERVICO_H'] = df['TEMPO_SERVICO_MIN'] / 60.0
    
    # Preço
    df['PRECO_A_COBRAR'] = df['PRECO_A_COBRAR'].astype(str).str.replace(',', '.').astype(float)
    
    # Flag produtiva
    df['PRODUTIVA'] = (df['STATUS'] == 'P') & (df['TIPO_OS'] != 'INDISP')
    
    return df

# Calcular métricas
def calcular_metricas(df, custo_por_hora):
    df_produtivo = df[df['PRODUTIVA']].copy()
    
    if df_produtivo.empty:
        st.warning("Nenhuma atividade produtiva encontrada após filtro.")
        return pd.DataFrame(columns=['REGIAO'])
    
    colunas_necessarias = ['TEMPO_SERVICO_H', 'PRECO_A_COBRAR', 'TIPO_OS', 'TEMPO_ESPERA_MIN', 'DATA', 'EQUIPE', 'REGIAO']
    faltantes = [col for col in colunas_necessarias if col not in df_produtivo.columns]
    if faltantes:
        st.error(f"Colunas faltando para cálculo: {faltantes}")
        return pd.DataFrame(columns=['REGIAO'])
    
    # Agrupamento
    agrupado = df_produtivo.groupby('REGIAO').agg(
        total_horas_produtivas=('TEMPO_SERVICO_H', 'sum'),
        receita_total=('PRECO_A_COBRAR', 'sum'),
        total_atividades=('TIPO_OS', 'count'),
        atividades_ct=('TIPO_OS', lambda x: (x == 'CT').sum()),
        espera_media_min=('TEMPO_ESPERA_MIN', 'mean'),
        dias_unicos=('DATA', 'nunique'),
        equipes_unicas=('EQUIPE', 'nunique')
    ).reset_index()
    
    # Evitar divisão por zero
    agrupado['equipes_media_por_dia'] = agrupado['equipes_unicas'] / agrupado['dias_unicos'].replace(0, np.nan)
    agrupado['horas_produtivas_media_por_equipe_dia'] = (
        agrupado['total_horas_produtivas'] / (agrupado['equipes_unicas'] * agrupado['dias_unicos'])
    ).replace([np.inf, -np.inf], 0).fillna(0)
    
    agrupado['utilizacao'] = agrupado['horas_produtivas_media_por_equipe_dia'] / 8.0
    agrupado['receita_por_hora'] = agrupado['receita_total'] / agrupado['total_horas_produtivas'].replace(0, np.nan)
    agrupado['receita_por_hora'] = agrupado['receita_por_hora'].fillna(0)
    agrupado['lucro_por_hora'] = agrupado['receita_por_hora'] - custo_por_hora
    agrupado['participacao_ct'] = agrupado['atividades_ct'] / agrupado['total_atividades'].replace(0, np.nan)
    agrupado['participacao_ct'] = agrupado['participacao_ct'].fillna(0)
    
    # Métricas de fila com proteção
    agrupado['taxa_chegada'] = agrupado['total_atividades'] / (
        agrupado['dias_unicos'] * 8 * agrupado['equipes_media_por_dia']
    ).replace(0, np.nan).fillna(0)
    
    agrupado['taxa_servico'] = np.where(
        agrupado['horas_produtivas_media_por_equipe_dia'] > 0,
        1 / agrupado['horas_produtivas_media_por_equipe_dia'],
        0
    )
    
    agrupado['rho'] = np.where(
        agrupado['taxa_servico'] > 0,
        agrupado['taxa_chegada'] / (agrupado['taxa_servico'] * agrupado['equipes_media_por_dia']),
        0
    )
    
    # Geral
    geral = pd.DataFrame(agrupado.mean(numeric_only=True)).T
    geral['REGIAO'] = 'Geral'
    
    return pd.concat([agrupado, geral], ignore_index=True)

# Simulação
def simular_adicao_equipes(metricas, equipes_extras, taxa_captura, custo_por_hora):
    if metricas.empty:
        return pd.DataFrame()
    
    simulacao = metricas.copy()
    simulacao['novas_equipes'] = simulacao['equipes_media_por_dia'] + equipes_extras
    simulacao['horas_adicionais_dia'] = equipes_extras * 6.0 * taxa_captura
    simulacao['receita_adicional_dia'] = simulacao['horas_adicionais_dia'] * simulacao['receita_por_hora']
    simulacao['custo_adicional_dia'] = simulacao['horas_adicionais_dia'] * custo_por_hora
    simulacao['lucro_adicional_dia'] = simulacao['receita_adicional_dia'] - simulacao['custo_adicional_dia']
    
    simulacao['nova_utilizacao'] = (
        (simulacao['horas_produtivas_media_por_equipe_dia'] * simulacao['equipes_media_por_dia'] + 
         simulacao['horas_adicionais_dia']) / (simulacao['novas_equipes'] * 8)
    ).replace([np.inf, -np.inf], 0).fillna(0)
    
    simulacao['novo_rho'] = np.where(
        simulacao['taxa_servico'] > 0,
        simulacao['taxa_chegada'] / (simulacao['taxa_servico'] * simulacao['novas_equipes']),
        0
    )
    
    return simulacao

# ────────────────────────────────────────────────
# Interface
# ────────────────────────────────────────────────

st.title('Dashboard Operacional e Financeiro - Equipes Equatorial Energia')

df = carregar_dados()

col1, col2 = st.columns(2)
custo_por_hora = col1.selectbox('Custo por Hora Produtiva (R$)', [200, 350], index=1)
equipes_extras = col2.slider('Quantidade de Equipes Extras para Simular', 0, 5, 1)
taxa_captura = st.slider('Taxa de Captura da Capacidade Adicional (%)', 50, 100, 75) / 100.0

metricas = calcular_metricas(df, custo_por_hora)

if metricas.empty:
    st.warning("Não foi possível calcular métricas. Verifique se há dados produtivos no arquivo.")
else:
    st.subheader('Principais Indicadores por Região')
    st.dataframe(metricas[['REGIAO', 'utilizacao', 'rho', 'espera_media_min', 'receita_por_hora', 'lucro_por_hora', 'participacao_ct']])

    st.subheader('Visão Integrada: Utilização × Lucro por Hora')
    st.bar_chart(metricas.set_index('REGIAO')[['utilizacao', 'lucro_por_hora']])

    st.subheader('Composição de Atividades (Geral)')
    if 'Geral' in metricas['REGIAO'].values:
        participacao_ct_geral = metricas[metricas['REGIAO'] == 'Geral']['participacao_ct'].values[0]
        st.pie_chart(pd.Series({'CT': participacao_ct_geral, 'Outras': 1 - participacao_ct_geral}))

    st.subheader('Simulação: Adição de Equipes Extras')
    resultados_simulacao = simular_adicao_equipes(metricas, equipes_extras, taxa_captura, custo_por_hora)
    if not resultados_simulacao.empty:
        st.dataframe(resultados_simulacao[['REGIAO', 'lucro_adicional_dia', 'nova_utilizacao', 'novo_rho']])

        st.subheader('Projeção Anual de Lucro Adicional (250 dias úteis)')
        st.bar_chart(resultados_simulacao.set_index('REGIAO')['lucro_adicional_dia'] * 250)
    else:
        st.info("Simulação não gerada (métricas vazias).")