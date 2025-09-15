"""
Analysis and Charts Module for CP2B Maps
Handles all data visualization and analysis functions
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

def create_top_chart(df, display_col, title, limit=15):
    """Create top municipalities chart"""
    if df.empty or display_col not in df.columns:
        return None
    
    top_data = df.nlargest(limit, display_col)
    
    fig = px.bar(
        top_data,
        x='nome_municipio',
        y=display_col,
        title=f'Top {limit} Municípios - {title}',
        labels={display_col: 'Potencial (m³/ano)', 'nome_municipio': 'Município'},
        color=display_col,
        color_continuous_scale='Viridis'
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=False,
        xaxis_title="Município",
        yaxis_title="Potencial (m³/ano)"
    )
    
    return fig

def create_distribution_chart(df, display_col, title):
    """Create distribution chart"""
    if df.empty or display_col not in df.columns:
        return None
    
    fig = px.histogram(
        df,
        x=display_col,
        title=f'Distribuição - {title}',
        nbins=20,
        labels={display_col: 'Potencial (m³/ano)'},
        color_discrete_sequence=['#2E8B57']
    )
    fig.update_layout(
        height=400,
        xaxis_title="Potencial (m³/ano)",
        yaxis_title="Número de Municípios"
    )
    
    return fig

def create_correlation_chart(df, display_col, title):
    """Create a scatter plot to show correlation"""
    if df.empty or 'populacao_2022' not in df.columns or display_col not in df.columns:
        return None
    
    fig = px.scatter(
        df,
        x='populacao_2022',
        y=display_col,
        size=display_col,
        color=display_col,
        hover_name='nome_municipio',
        title=f'População vs Potencial - {title}',
        labels={'populacao_2022': 'População (2022)', display_col: 'Potencial (m³/ano)'},
        color_continuous_scale='Viridis',
        size_max=60
    )
    fig.update_layout(height=400)
    return fig

def create_regional_comparison_chart(df, display_col):
    """Create regional comparison chart if region data exists"""
    if df.empty or display_col not in df.columns:
        return None
    
    # Check if we have region data
    if 'region' not in df.columns:
        return None
    
    regional_data = df.groupby('region')[display_col].sum().reset_index()
    
    fig = px.pie(
        regional_data,
        values=display_col,
        names='region',
        title='Distribuição Regional do Potencial',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_layout(height=400)
    
    return fig

def create_multi_source_comparison(df, municipality_name=None):
    """Create comparison chart for different biogas sources"""
    if df.empty:
        return None
    
    # Define biogas source columns
    source_columns = {
        'biogas_cana_nm_ano': 'Cana-de-açúcar',
        'biogas_soja_nm_ano': 'Soja',
        'biogas_milho_nm_ano': 'Milho',
        'biogas_bovinos_nm_ano': 'Bovinos',
        'biogas_suino_nm_ano': 'Suínos',
        'biogas_aves_nm_ano': 'Aves'
    }
    
    # Filter data for municipality if specified
    if municipality_name:
        df_filtered = df[df['nome_municipio'] == municipality_name]
        title = f'Composição do Biogás - {municipality_name}'
    else:
        df_filtered = df
        title = 'Composição Total do Biogás - Estado de SP'
    
    if df_filtered.empty:
        return None
    
    # Calculate totals for each source
    source_totals = {}
    for col, label in source_columns.items():
        if col in df_filtered.columns:
            total = df_filtered[col].sum()
            if total > 0:
                source_totals[label] = total
    
    if not source_totals:
        return None
    
    # Create pie chart
    fig = px.pie(
        values=list(source_totals.values()),
        names=list(source_totals.keys()),
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(height=400)
    
    return fig

def create_trend_analysis_chart(df, display_col):
    """Create a trend analysis showing potential vs population density"""
    if df.empty or display_col not in df.columns:
        return None
    
    if 'area_km2' not in df.columns or 'populacao_2022' not in df.columns:
        return None
    
    # Calculate population density
    df_analysis = df.copy()
    df_analysis['densidade_pop'] = df_analysis['populacao_2022'] / df_analysis['area_km2']
    df_analysis['potencial_per_capita'] = df_analysis[display_col] / df_analysis['populacao_2022']
    
    # Remove outliers for better visualization
    df_analysis = df_analysis[
        (df_analysis['densidade_pop'] > 0) & 
        (df_analysis['potencial_per_capita'] > 0)
    ]
    
    fig = px.scatter(
        df_analysis,
        x='densidade_pop',
        y='potencial_per_capita',
        size='populacao_2022',
        color=display_col,
        hover_name='nome_municipio',
        title='Densidade Populacional vs Potencial Per Capita',
        labels={
            'densidade_pop': 'Densidade Populacional (hab/km²)',
            'potencial_per_capita': 'Potencial Per Capita (m³/hab/ano)'
        },
        color_continuous_scale='Viridis'
    )
    fig.update_layout(height=400)
    
    return fig

def create_comparative_metrics_table(df, selected_municipalities):
    """Create comparative metrics table for selected municipalities"""
    if df.empty or not selected_municipalities:
        return None
    
    selected_df = df[df['cd_mun'].isin(selected_municipalities)].copy()
    
    if selected_df.empty:
        return None
    
    # Calculate key metrics
    metrics_cols = [
        'nome_municipio', 'populacao_2022', 'total_final_nm_ano',
        'total_agricola_nm_ano', 'total_pecuaria_nm_ano'
    ]
    
    # Add per capita calculations
    selected_df['potencial_per_capita'] = (
        selected_df['total_final_nm_ano'] / selected_df['populacao_2022']
    )
    
    # Select and rename columns for display
    display_cols = metrics_cols + ['potencial_per_capita']
    result_df = selected_df[display_cols].copy()
    
    result_df.columns = [
        'Município', 'População', 'Potencial Total', 'Potencial Agrícola',
        'Potencial Pecuário', 'Potencial Per Capita'
    ]
    
    return result_df

def create_summary_statistics(df, display_col):
    """Create summary statistics for the selected data column"""
    if df.empty or display_col not in df.columns:
        return None
    
    data = df[display_col].dropna()
    
    if len(data) == 0:
        return None
    
    stats = {
        'Contagem': len(data),
        'Média': data.mean(),
        'Mediana': data.median(),
        'Desvio Padrão': data.std(),
        'Mínimo': data.min(),
        'Máximo': data.max(),
        'Quartil 25%': data.quantile(0.25),
        'Quartil 75%': data.quantile(0.75)
    }
    
    return pd.DataFrame(list(stats.items()), columns=['Estatística', 'Valor'])

def create_municipality_ranking(df, display_col, limit=50):
    """Create municipality ranking table"""
    if df.empty or display_col not in df.columns:
        return None
    
    ranking_df = df.nlargest(limit, display_col)[
        ['nome_municipio', display_col, 'populacao_2022']
    ].copy()
    
    ranking_df['ranking'] = range(1, len(ranking_df) + 1)
    ranking_df['potencial_per_capita'] = (
        ranking_df[display_col] / ranking_df['populacao_2022']
    )
    
    # Reorder columns
    ranking_df = ranking_df[[
        'ranking', 'nome_municipio', display_col, 
        'populacao_2022', 'potencial_per_capita'
    ]]
    
    ranking_df.columns = [
        'Posição', 'Município', 'Potencial Total', 
        'População', 'Potencial Per Capita'
    ]
    
    return ranking_df

def analyze_catchment_area_data(df, catchment_results, display_col):
    """Analyze and visualize catchment area results"""
    if not catchment_results or df.empty:
        return None, None
    
    # Create charts for catchment analysis
    municipality_chart = None
    raster_chart = None
    
    try:
        # Municipality analysis chart
        if 'municipalities' in catchment_results and catchment_results['municipalities']:
            mun_data = catchment_results['municipalities']
            mun_df = pd.DataFrame(mun_data)
            
            if not mun_df.empty and display_col in mun_df.columns:
                municipality_chart = px.bar(
                    mun_df.head(10),
                    x='nome_municipio',
                    y=display_col,
                    title='Top 10 Municípios na Área de Captação',
                    labels={display_col: 'Potencial (m³/ano)', 'nome_municipio': 'Município'}
                )
                municipality_chart.update_layout(xaxis_tickangle=-45, height=400)
        
        # Raster analysis chart (land use)
        if 'raster_analysis' in catchment_results and catchment_results['raster_analysis']:
            raster_data = catchment_results['raster_analysis']
            
            if isinstance(raster_data, dict) and raster_data:
                raster_df = pd.DataFrame(
                    list(raster_data.items()),
                    columns=['Uso do Solo', 'Área (hectares)']
                )
                
                raster_chart = px.pie(
                    raster_df,
                    values='Área (hectares)',
                    names='Uso do Solo',
                    title='Distribuição de Uso do Solo na Área de Captação'
                )
                raster_chart.update_layout(height=400)
    
    except Exception as e:
        st.error(f"Erro na análise da área de captação: {e}")
    
    return municipality_chart, raster_chart