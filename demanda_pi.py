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
    
    # Converter 'DATA' para numérico antes da conversão para datetime
    df['DATA'] = pd.to_numeric(df['DATA'], errors='coerce')
    
    # Limpeza e criação de colunas
    df['DURACAO_MIN'] = df['DURACAO'].apply(tempo_para_minutos)
    df['DESLOCAMENTO_MIN'] = df['DESLOCAMENTO'].apply(tempo_para_minutos)
    df['TEMPO_SERVICO_MIN'] = df['DURACAO_MIN'] + df['DESLOCAMENTO_MIN']
    df['TEMPO_SERVICO_H'] = df['TEMPO_SERVICO_MIN'] / 60.0
    
    df['PRECO_A_COBRAR'] = df['PRECO_A_COBRAR'].astype(str).str.replace(',', '.').astype(float)
    
    df = pd.read_excel(caminho_arquivo, sheet_name='TEORIA_DAS_FILAS')
    
    df['DATA'] = pd.to_numeric(df['DATA'], errors='coerce')
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', origin='1899-12-30', unit='D')
    
    df['ATRIBUICAO_DT'] = pd.to_datetime(df['ATRIBUICAO'], errors='coerce')
    
    # Cria INICIO_DT com cuidado
    def criar_inicio_dt(row):
        if pd.isna(row['DATA']) or pd.isna(row['HORA_INICIO']):
            return pd.NaT
        try:
            hora = int(row['HORA_INICIO'])
            return row['DATA'].replace(hour=hora, minute=0, second=0, microsecond=0)
        except:
            return pd.NaT
    
    df['INICIO_DT'] = df.apply(criar_inicio_dt, axis=1)
    
    # Cálculo de espera com tratamento de NaT
    mask = df['INICIO_DT'].notna() & df['ATRIBUICAO_DT'].notna()
    df['TEMPO_ESPERA_MIN'] = 0.0
    df.loc[mask, 'TEMPO_ESPERA_MIN'] = (
        (df.loc[mask, 'INICIO_DT'] - df.loc[mask, 'ATRIBUICAO_DT'])
        .dt.total_seconds() / 60
    )
    # Filtrar atividades produtivas
    df['PRODUTIVA'] = (df['STATUS'] == 'P') & (df['TIPO_OS'] != 'INDISP')
    
    return df

# Calcular métricas
def calcular_metricas(df, custo_por_hora):
    df_produtivo = df[df['PRODUTIVA']]
    
    # Agrupamento por REGIÃO
    agrupado = df_produtivo.groupby('REGIAO').agg(
        total_horas_produtivas=('TEMPO_SERVICO_H', 'sum'),
        receita_total=('PRECO_A_COBRAR', 'sum'),
        total_atividades=('TIPO_OS', 'count'),
        atividades_ct=('TIPO_OS', lambda x: (x == 'CT').sum()),
        espera_media_min=('TEMPO_ESPERA_MIN', 'mean'),
        dias_unicos=('DATA', 'nunique'),
        equipes_unicas=('EQUIPE', 'nunique')
    ).reset_index()
    
    agrupado['equipes_media_por_dia'] = agrupado['equipes_unicas'] / agrupado['dias_unicos']
    agrupado['horas_produtivas_media_por_equipe_dia'] = agrupado['total_horas_produtivas'] / (agrupado['equipes_unicas'] * agrupado['dias_unicos'])
    agrupado['utilizacao'] = agrupado['horas_produtivas_media_por_equipe_dia'] / 8.0  # Assume 8h/dia
    agrupado['receita_por_hora'] = agrupado['receita_total'] / agrupado['total_horas_produtivas']
    agrupado['lucro_por_hora'] = agrupado['receita_por_hora'] - custo_por_hora
    agrupado['participacao_ct'] = agrupado['atividades_ct'] / agrupado['total_atividades']
    
    # Métricas simplificadas de fila
    agrupado['taxa_chegada'] = agrupado['total_atividades'] / (agrupado['dias_unicos'] * 8 * agrupado['equipes_media_por_dia'])
    agrupado['taxa_servico'] = 1 / agrupado['horas_produtivas_media_por_equipe_dia'].replace(0, np.nan)
    agrupado['rho'] = agrupado['taxa_chegada'] / (agrupado['taxa_servico'] * agrupado['equipes_media_por_dia'])
    
    # Linha geral (média)
    geral = pd.DataFrame(agrupado.mean(numeric_only=True)).T
    geral['REGIAO'] = 'Geral'
    
    return pd.concat([agrupado, geral])

# Simulação de adição de equipes
def simular_adicao_equipes(metricas, equipes_extras, taxa_captura, custo_por_hora):
    simulacao = metricas.copy()
    simulacao['novas_equipes'] = simulacao['equipes_media_por_dia'] + equipes_extras
    simulacao['horas_adicionais_dia'] = equipes_extras * 6.0 * taxa_captura  # 6h produtivas por equipe adicionada
    simulacao['receita_adicional_dia'] = simulacao['horas_adicionais_dia'] * simulacao['receita_por_hora']
    simulacao['custo_adicional_dia'] = simulacao['horas_adicionais_dia'] * custo_por_hora
    simulacao['lucro_adicional_dia'] = simulacao['receita_adicional_dia'] - simulacao['custo_adicional_dia']
    simulacao['nova_utilizacao'] = (simulacao['horas_produtivas_media_por_equipe_dia'] * simulacao['equipes_media_por_dia'] + simulacao['horas_adicionais_dia']) / (simulacao['novas_equipes'] * 8)
    simulacao['novo_rho'] = simulacao['taxa_chegada'] / (simulacao['taxa_servico'] * simulacao['novas_equipes'])
    return simulacao

# Interface Streamlit
st.title('Dashboard Operacional e Financeiro - Equipes Equatorial Energia')

df = carregar_dados()

col1, col2 = st.columns(2)
custo_por_hora = col1.selectbox('Custo por Hora Produtiva (R$)', [200, 350], index=1)
equipes_extras = col2.slider('Quantidade de Equipes Extras para Simular', 0, 5, 1)
taxa_captura = st.slider('Taxa de Captura da Capacidade Adicional (%)', 50, 100, 75) / 100.0

metricas = calcular_metricas(df, custo_por_hora)

st.subheader('Principais Indicadores por Região')
st.dataframe(metricas[['REGIAO', 'utilizacao', 'rho', 'espera_media_min', 'receita_por_hora', 'lucro_por_hora', 'participacao_ct']])

st.subheader('Visão Integrada: Utilização × Lucro por Hora')
st.bar_chart(metricas.set_index('REGIAO')[['utilizacao', 'lucro_por_hora']])

st.subheader('Composição de Atividades (Geral)')
participacao_ct_geral = metricas[metricas['REGIAO'] == 'Geral']['participacao_ct'].values[0]
st.pie_chart(pd.Series({'CT': participacao_ct_geral, 'Outras': 1 - participacao_ct_geral}))

st.subheader('Simulação: Adição de Equipes Extras')
resultados_simulacao = simular_adicao_equipes(metricas, equipes_extras, taxa_captura, custo_por_hora)
st.dataframe(resultados_simulacao[['REGIAO', 'lucro_adicional_dia', 'nova_utilizacao', 'novo_rho']])

st.subheader('Projeção Anual de Lucro Adicional (250 dias úteis)')
st.bar_chart(resultados_simulacao.set_index('REGIAO')['lucro_adicional_dia'] * 250)