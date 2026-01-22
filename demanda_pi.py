import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Function to convert time strings to minutes
def time_to_minutes(t):
    if pd.isna(t) or ':' not in str(t):
        return 0
    try:
        parts = str(t).split(':')
        if len(parts) == 2:
            h, m = map(int, parts)
            return h * 60 + m
        else:
            return 0
    except:
        return 0

# Load and process data
@st.cache_data
def load_data(file_path='V_TEORIA_DAS_FILAS.xlsx'):
    df = pd.read_excel(file_path, sheet_name='TEORIA_DAS_FILAS')
    
    # Clean columns
    df['DURACAO_MIN'] = df['DURACAO'].apply(time_to_minutes)
    df['DESLOCAMENTO_MIN'] = df['DESLOCAMENTO'].apply(time_to_minutes)
    df['SERVICE_MIN'] = df['DURACAO_MIN'] + df['DESLOCAMENTO_MIN']
    df['SERVICE_H'] = df['SERVICE_MIN'] / 60.0
    
    df['PRECO_A_COBRAR'] = df['PRECO_A_COBRAR'].astype(str).str.replace(',', '.').astype(float)
    
    # Parse dates and times
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce', origin='1899-12-30', unit='D')  # Excel serial date
    df['ATRIBUICAO_DT'] = pd.to_datetime(df['ATRIBUICAO'], errors='coerce')
    df['INICIO_DT'] = df.apply(lambda row: row['DATA'].replace(hour=int(row['HORA_INICIO']), minute=0) if pd.notna(row['DATA']) else None, axis=1)
    df['WAIT_MIN'] = (df['INICIO_DT'] - df['ATRIBUICAO_DT']).dt.total_seconds() / 60 if 'INICIO_DT' in df else 0
    
    # Filter productive
    df['PRODUCTIVE'] = (df['STATUS'] == 'P') & (df['TIPO_OS'] != 'INDISP')
    
    return df

# Compute metrics
def compute_metrics(df, cost_per_hour):
    productive_df = df[df['PRODUCTIVE']]
    
    # Group by REGIAO
    agg = productive_df.groupby('REGIAO').agg(
        total_prod_hours=('SERVICE_H', 'sum'),
        total_revenue=('PRECO_A_COBRAR', 'sum'),
        total_activities=('TIPO_OS', 'count'),
        ct_activities=('TIPO_OS', lambda x: (x == 'CT').sum()),
        avg_wait_min=('WAIT_MIN', 'mean'),
        unique_days=('DATA', 'nunique'),
        unique_teams=('EQUIPE', 'nunique')
    ).reset_index()
    
    agg['avg_teams_per_day'] = agg['unique_teams'] / agg['unique_days']
    agg['avg_prod_h_per_team_day'] = agg['total_prod_hours'] / (agg['unique_teams'] * agg['unique_days'])
    agg['utilization'] = agg['avg_prod_h_per_team_day'] / 8.0  # Assume 8h day
    agg['rev_per_h'] = agg['total_revenue'] / agg['total_prod_hours']
    agg['profit_per_h'] = agg['rev_per_h'] - cost_per_hour
    agg['ct_share'] = agg['ct_activities'] / agg['total_activities']
    
    # Queue metrics (simplified)
    agg['arrival_rate'] = agg['total_activities'] / (agg['unique_days'] * 8 * agg['avg_teams_per_day'])  # lambda per hour per team
    agg['service_rate'] = 1 / agg['avg_prod_h_per_team_day'] if agg['avg_prod_h_per_team_day'] > 0 else 0  # mu
    agg['rho'] = agg['arrival_rate'] / (agg['service_rate'] * agg['avg_teams_per_day']) if agg['service_rate'] > 0 else 0
    
    # Overall
    overall = pd.DataFrame(agg.mean(numeric_only=True)).T
    overall['REGIAO'] = 'Overall'
    
    return pd.concat([agg, overall])

# Simulation function
def simulate_add_teams(metrics, extra_teams, capture_rate, cost_per_hour):
    sim = metrics.copy()
    sim['new_teams'] = sim['avg_teams_per_day'] + extra_teams
    sim['added_h_day'] = extra_teams * 6.0 * capture_rate  # Assume 6h productive per added team
    sim['inc_revenue_day'] = sim['added_h_day'] * sim['rev_per_h']
    sim['inc_cost_day'] = sim['added_h_day'] * cost_per_hour
    sim['inc_profit_day'] = sim['inc_revenue_day'] - sim['inc_cost_day']
    sim['new_util'] = (sim['avg_prod_h_per_team_day'] * sim['avg_teams_per_day'] + sim['added_h_day']) / (sim['new_teams'] * 8)
    sim['new_rho'] = sim['arrival_rate'] / (sim['service_rate'] * sim['new_teams']) if 'service_rate' in sim else 0
    return sim

# Streamlit Dashboard
st.title('Operational and Financial Dashboard for Equatorial Energia Teams')

df = load_data()

col1, col2 = st.columns(2)
cost_per_hour = col1.selectbox('Cost per Productive Hour', [200, 350], index=1)
extra_teams = col2.slider('Extra Teams to Simulate', 0, 5, 1)
capture_rate = st.slider('Capture Rate for Added Capacity (%)', 50, 100, 75) / 100.0

metrics = compute_metrics(df, cost_per_hour)

st.subheader('Key Metrics by Region')
st.dataframe(metrics[['REGIAO', 'utilization', 'rho', 'avg_wait_min', 'rev_per_h', 'profit_per_h', 'ct_share']])

st.subheader('Integrated View: Utilization vs Profit per Hour')
st.bar_chart(metrics.set_index('REGIAO')[['utilization', 'profit_per_h']])

st.subheader('Activity Mix (Overall)')
overall_ct = metrics[metrics['REGIAO'] == 'Overall']['ct_share'].values[0]
st.pie_chart(pd.Series({'CT': overall_ct, 'Other': 1 - overall_ct}))

st.subheader('Simulation: Adding Extra Teams')
sim_results = simulate_add_teams(metrics, extra_teams, capture_rate, cost_per_hour)
st.dataframe(sim_results[['REGIAO', 'inc_profit_day', 'new_util', 'new_rho']])

st.subheader('Annual Incremental Profit Projection (250 days)')
st.bar_chart(sim_results.set_index('REGIAO')['inc_profit_day'] * 250)