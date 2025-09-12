"""
Data Loading Module for CP2B Maps
Handles all data loading, caching, and preprocessing functions
"""

import os
import sqlite3
import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
import streamlit as st

# Configure logging
logger = logging.getLogger(__name__)

@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_shapefile_cached(shapefile_path, simplify_tolerance=0.001):
    """Carrega shapefile com cache e simplificação opcional"""
    try:
        if not os.path.exists(shapefile_path):
            return None
            
        gdf = gpd.read_file(shapefile_path)
        
        # Converter para WGS84 se necessário
        if gdf.crs and gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        
        # CORREÇÃO: Converter colunas problemáticas para string para evitar erro de serialização
        for col in gdf.columns:
            if col != 'geometry':
                if gdf[col].dtype == 'datetime64[ns]' or str(gdf[col].dtype).startswith('datetime'):
                    gdf[col] = gdf[col].astype(str)
                elif gdf[col].dtype == 'object':
                    # Converter objetos complexos para string também
                    gdf[col] = gdf[col].astype(str)
        
        # Simplificar geometrias complexas para melhor performance
        if simplify_tolerance > 0:
            gdf['geometry'] = gdf['geometry'].simplify(simplify_tolerance, preserve_topology=True)
        
        return gdf
    except Exception as e:
        logger.error(f"Erro ao carregar {shapefile_path}: {e}")
        return None

@st.cache_data(ttl=3600)
def prepare_layer_data():
    """Pré-carrega todos os dados das camadas uma vez"""
    base_path = Path(__file__).parent.parent.parent.parent / "shapefile"
    geoparquet_path = Path(__file__).parent.parent.parent.parent / "geoparquet"
    
    layers = {}
    
    # Plantas de Biogás (pontos - sem simplificação)
    plantas_path = base_path / "Plantas_Biogas_SP.shp" 
    layers['plantas'] = load_shapefile_cached(str(plantas_path), simplify_tolerance=0)
    
    # Gasodutos (linhas - simplificação leve)
    gasodutos_dist = base_path / "Gasodutos_Distribuicao_SP.shp"
    gasodutos_transp = base_path / "Gasodutos_Transporte_SP.shp"
    layers['gasodutos_dist'] = load_shapefile_cached(str(gasodutos_dist), simplify_tolerance=0.0001)
    layers['gasodutos_transp'] = load_shapefile_cached(str(gasodutos_transp), simplify_tolerance=0.0001)
    
    # Rodovias (linhas - simplificação leve)
    rodovias_path = base_path / "Rodovias_Estaduais_SP.shp"
    layers['rodovias'] = load_shapefile_cached(str(rodovias_path), simplify_tolerance=0.0001)
    
    # Rios (linhas - simplificação média)
    rios_path = base_path / "Rios_SP.shp" 
    layers['rios'] = load_shapefile_cached(str(rios_path), simplify_tolerance=0.001)
    
    # Áreas Urbanas (polígonos otimizados via GeoParquet) - LIMITADO para evitar problemas
    areas_path = geoparquet_path / "Areas_Urbanas_SP.parquet"
    if areas_path.exists():
        try:
            areas_gdf = gpd.read_parquet(areas_path)
            if areas_gdf.crs and areas_gdf.crs != 'EPSG:4326':
                areas_gdf = areas_gdf.to_crs('EPSG:4326')
            
            # LIMITAR drasticamente para evitar travamento - apenas 1000 polígonos máximo
            if len(areas_gdf) > 1000:
                areas_gdf = areas_gdf.sample(n=1000, random_state=42)
            
            # Simplificação muito agressiva para polígonos complexos
            areas_gdf['geometry'] = areas_gdf['geometry'].simplify(0.005, preserve_topology=True)
            layers['areas_urbanas'] = areas_gdf
        except Exception as e:
            logger.error(f"Erro ao carregar áreas urbanas: {e}")
            layers['areas_urbanas'] = None
    else:
        layers['areas_urbanas'] = None
    
    # Regiões Administrativas (polígonos - simplificação leve)
    regioes_path = base_path / "Regiao_Adm_SP.shp"
    layers['regioes_admin'] = load_shapefile_cached(str(regioes_path), simplify_tolerance=0.001)
    
    return layers

def get_database_path():
    """Get database path"""
    return Path(__file__).parent.parent.parent.parent / "data" / "cp2b_maps.db"

@st.cache_data
def load_municipalities():
    """Load municipality data from database with error handling"""
    try:
        db_path = get_database_path()
        
        if not db_path.exists():
            logger.warning("Database not found")
            return pd.DataFrame()
        
        with sqlite3.connect(db_path) as conn:
            query = "SELECT * FROM municipalities ORDER BY total_final_nm_ano DESC"
            df = pd.read_sql_query(query, conn)
            
            # Convert per capita values to total values by multiplying by population
            if 'rsu_potencial_nm_habitante_ano' in df.columns and 'populacao_2022' in df.columns:
                df['rsu_potencial_nm_ano'] = df['rsu_potencial_nm_habitante_ano'] * df['populacao_2022']
                df['rsu_potencial_nm_ano'] = df['rsu_potencial_nm_ano'].fillna(0)
            
            if 'rpo_potencial_nm_habitante_ano' in df.columns and 'populacao_2022' in df.columns:
                df['rpo_potencial_nm_ano'] = df['rpo_potencial_nm_habitante_ano'] * df['populacao_2022']
                df['rpo_potencial_nm_ano'] = df['rpo_potencial_nm_ano'].fillna(0)
            
            logger.info(f"Loaded {len(df)} municipalities")
            return df
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data
def load_optimized_geometries(detail_level="medium_detail"):
    """Load optimized municipality geometries from GeoParquet"""
    try:
        parquet_path = Path(__file__).parent.parent.parent.parent / "shapefile" / f"municipalities_{detail_level}.parquet"
        
        if parquet_path.exists():
            return gpd.read_parquet(parquet_path)
        else:
            # Fallback to original shapefile
            shapefile_path = Path(__file__).parent.parent.parent.parent / "shapefile" / "Municipios_SP_shapefile.shp"
            if shapefile_path.exists():
                gdf = gpd.read_file(shapefile_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
                return gdf
    except Exception as e:
        logger.error(f"Error loading geometries: {e}")
    
    return None

def safe_divide(numerator, denominator, default=0):
    """Safe division with default value"""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default

@st.cache_data
def format_number(value, unit="Nm³/ano", scale=1):
    """Format numbers with proper scaling"""
    try:
        if pd.isna(value) or value == 0:
            return f"0 {unit}"
        
        scaled_value = value / scale
        if scale >= 1_000_000:
            return f"{scaled_value:.1f}M {unit}"
        elif scale >= 1_000:
            return f"{scaled_value:.0f}K {unit}"
        else:
            return f"{value:,.0f} {unit}"
    except:
        return f"0 {unit}"

def apply_filters(df, filters):
    """Apply filters to dataframe"""
    if not filters:
        return df
    
    filtered_df = df.copy()
    
    for filter_type, filter_value in filters.items():
        if filter_type == 'min_potential':
            filtered_df = filtered_df[filtered_df['total_final_nm_ano'] >= filter_value]
        elif filter_type == 'max_potential':
            filtered_df = filtered_df[filtered_df['total_final_nm_ano'] <= filter_value]
        elif filter_type == 'region':
            if filter_value != 'All':
                filtered_df = filtered_df[filtered_df['region'] == filter_value]
        elif filter_type == 'residue_type':
            if filter_value in ['Agrícola', 'Pecuária']:
                col_name = f"total_{filter_value.lower()}_nm_ano"
                if col_name in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[col_name] > 0]
    
    return filtered_df

def get_residue_label(column_name):
    """Get friendly label for residue column names"""
    labels = {
        'total_final_nm_ano': 'Potencial Total',
        'total_agricola_nm_ano': 'Potencial Agrícola',
        'total_pecuaria_nm_ano': 'Potencial Pecuário',
        'biogas_cana_nm_ano': 'Biogás de Cana',
        'biogas_soja_nm_ano': 'Biogás de Soja', 
        'biogas_milho_nm_ano': 'Biogás de Milho',
        'biogas_cafe_nm_ano': 'Biogás de Café',
        'biogas_citros_nm_ano': 'Biogás de Citros',
        'biogas_bovinos_nm_ano': 'Biogás de Bovinos',
        'biogas_suino_nm_ano': 'Biogás de Suínos',
        'biogas_aves_nm_ano': 'Biogás de Aves',
        'biogas_piscicultura_nm_ano': 'Biogás de Piscicultura'
    }
    return labels.get(column_name, column_name.replace('_', ' ').title())