"""
Data Loading Module for CP2B Maps
Handles all data loading, caching, and preprocessing functions
Updated to use centralized data service for better performance
"""

import os
import sqlite3
import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
import streamlit as st

# Import the new centralized data service
from .data_service import get_data_service, DataService

# Configure logging
logger = logging.getLogger(__name__)

# Keep original function for backward compatibility, but mark as deprecated
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
    """
    Pré-carrega todos os dados das camadas uma vez
    OPTIMIZED: Now uses centralized data service with lazy loading
    """
    service = get_data_service()

    layers = {
        'plantas': service.get_layer_data('plantas'),
        'gasodutos_dist': service.get_layer_data('gasodutos_dist'),
        'gasodutos_transp': service.get_layer_data('gasodutos_transp'),
        'rodovias': service.get_layer_data('rodovias'),
        'rios': service.get_layer_data('rios'),
        'areas_urbanas': None,  # Kept disabled for performance
        'regioes_admin': service.get_layer_data('regioes_admin'),
        'sp_border': service.get_layer_data('sp_border')
    }

    return layers

def get_database_path():
    """Get database path"""
    return Path(__file__).parent.parent.parent.parent / "data" / "cp2b_maps.db"

# OPTIMIZED: Use centralized data service
def load_municipalities():
    """Load municipality data from database with error handling - OPTIMIZED"""
    service = get_data_service()
    return service.load_municipalities()

def load_optimized_geometries(detail_level="medium_detail"):
    """Load optimized municipality geometries - OPTIMIZED"""
    service = get_data_service()
    return service.load_municipality_geometries(detail_level)

# Import utility functions from centralized data service
from .data_service import safe_divide, format_number, apply_filters, get_residue_label

# Keep these functions here for backward compatibility but they now delegate to data_service