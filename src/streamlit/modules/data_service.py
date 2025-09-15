"""
Centralized Data Service for CP2B Maps
Optimized data loading with lazy loading, efficient caching, and memory management
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import pandas as pd
import geopandas as gpd
import streamlit as st
from functools import lru_cache

logger = logging.getLogger(__name__)

class DataService:
    """Centralized data service with lazy loading and optimized caching"""

    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent.parent
        self.shapefile_path = self.base_path / "shapefile"
        self.geoparquet_path = self.base_path / "geoparquet"
        self.db_path = self.base_path / "data" / "cp2b_maps.db"
        self._cache = {}

    @st.cache_data(ttl=3600, show_spinner=False)
    def _load_shapefile_optimized(_self, shapefile_path: str, simplify_tolerance: float = 0.001) -> Optional[gpd.GeoDataFrame]:
        """Load shapefile with optimizations - static method for caching"""
        try:
            if not os.path.exists(shapefile_path):
                logger.warning(f"Shapefile not found: {shapefile_path}")
                return None

            gdf = gpd.read_file(shapefile_path)

            # Convert to WGS84 if needed
            if gdf.crs and gdf.crs != 'EPSG:4326':
                gdf = gdf.to_crs('EPSG:4326')

            # Convert problematic columns to string for serialization
            for col in gdf.columns:
                if col != 'geometry':
                    if gdf[col].dtype == 'datetime64[ns]' or str(gdf[col].dtype).startswith('datetime'):
                        gdf[col] = gdf[col].astype(str)
                    elif gdf[col].dtype == 'object':
                        gdf[col] = gdf[col].astype(str)

            # Simplify geometries for better performance
            if simplify_tolerance > 0:
                gdf['geometry'] = gdf['geometry'].simplify(simplify_tolerance, preserve_topology=True)

            logger.info(f"Loaded {len(gdf)} features from {Path(shapefile_path).name}")
            return gdf

        except Exception as e:
            logger.error(f"Error loading {shapefile_path}: {e}")
            return None

    def get_layer_data(self, layer_name: str, force_reload: bool = False) -> Optional[gpd.GeoDataFrame]:
        """Get layer data with lazy loading"""
        if not force_reload and layer_name in self._cache:
            return self._cache[layer_name]

        layer_config = {
            'plantas': {'file': 'Plantas_Biogas_SP.shp', 'simplify': 0},
            'gasodutos_dist': {'file': 'Gasodutos_Distribuicao_SP.shp', 'simplify': 0.0001},
            'gasodutos_transp': {'file': 'Gasodutos_Transporte_SP.shp', 'simplify': 0.0001},
            'rodovias': {'file': 'Rodovias_Estaduais_SP.shp', 'simplify': 0.0001},
            'rios': {'file': 'Rios_SP.shp', 'simplify': 0.001},
            'regioes_admin': {'file': 'Regiao_Adm_SP.shp', 'simplify': 0.001},
            'sp_border': {'file': 'Limite_SP.shp', 'simplify': 0.001}
        }

        if layer_name not in layer_config:
            logger.warning(f"Unknown layer: {layer_name}")
            return None

        config = layer_config[layer_name]
        file_path = self.shapefile_path / config['file']

        data = self._load_shapefile_optimized(str(file_path), config['simplify'])
        if data is not None:
            self._cache[layer_name] = data

        return data

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_municipalities(_self) -> pd.DataFrame:
        """Load municipality data from database"""
        try:
            if not _self.db_path.exists():
                logger.warning("Database not found")
                return pd.DataFrame()

            with sqlite3.connect(_self.db_path) as conn:
                query = "SELECT * FROM municipalities ORDER BY total_final_nm_ano DESC"
                df = pd.read_sql_query(query, conn)

                # Convert per capita values to total values
                if 'rsu_potencial_nm_habitante_ano' in df.columns and 'populacao_2022' in df.columns:
                    df['rsu_potencial_nm_ano'] = df['rsu_potencial_nm_habitante_ano'] * df['populacao_2022']
                    df['rsu_potencial_nm_ano'] = df['rsu_potencial_nm_ano'].fillna(0)

                if 'rpo_potencial_nm_habitante_ano' in df.columns and 'populacao_2022' in df.columns:
                    df['rpo_potencial_nm_ano'] = df['rpo_potencial_nm_habitante_ano'] * df['populacao_2022']
                    df['rpo_potencial_nm_ano'] = df['rpo_potencial_nm_ano'].fillna(0)

                logger.info(f"Loaded {len(df)} municipalities")
                return df

        except Exception as e:
            logger.error(f"Error loading municipality data: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=3600, show_spinner=False)
    def load_municipality_geometries(_self, detail_level: str = "medium_detail") -> Optional[gpd.GeoDataFrame]:
        """Load optimized municipality geometries"""
        try:
            # Try GeoParquet first (much faster)
            parquet_path = _self.shapefile_path / f"municipalities_{detail_level}.parquet"
            if parquet_path.exists():
                gdf = gpd.read_parquet(parquet_path)
                logger.info(f"Loaded {len(gdf)} municipality geometries from parquet")
                return gdf

            # Fallback to shapefile
            shapefile_path = _self.shapefile_path / "Municipios_SP_shapefile.shp"
            if shapefile_path.exists():
                gdf = gpd.read_file(shapefile_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
                logger.info(f"Loaded {len(gdf)} municipality geometries from shapefile")
                return gdf

        except Exception as e:
            logger.error(f"Error loading municipality geometries: {e}")

        return None

    def clear_cache(self, layer_name: str = None):
        """Clear cache for specific layer or all layers"""
        if layer_name:
            self._cache.pop(layer_name, None)
            logger.info(f"Cleared cache for {layer_name}")
        else:
            self._cache.clear()
            logger.info("Cleared all layer cache")

    def get_cache_status(self) -> Dict[str, int]:
        """Get current cache status"""
        return {
            'cached_layers': len(self._cache),
            'layer_names': list(self._cache.keys()),
            'total_memory_mb': sum(gdf.memory_usage(deep=True).sum() / 1024 / 1024
                                 for gdf in self._cache.values() if gdf is not None)
        }

# Global data service instance
@st.cache_resource
def get_data_service() -> DataService:
    """Get singleton data service instance"""
    return DataService()

# Convenience functions for backward compatibility
def load_municipalities() -> pd.DataFrame:
    """Load municipality data"""
    service = get_data_service()
    return service.load_municipalities()

def load_optimized_geometries(detail_level: str = "medium_detail") -> Optional[gpd.GeoDataFrame]:
    """Load optimized municipality geometries"""
    service = get_data_service()
    return service.load_municipality_geometries(detail_level)

def get_layer_data(layer_name: str) -> Optional[gpd.GeoDataFrame]:
    """Get specific layer data"""
    service = get_data_service()
    return service.get_layer_data(layer_name)

# Utility functions
def safe_divide(numerator, denominator, default=0):
    """Safe division with default value"""
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default

@st.cache_data
def format_number(value, unit="m³/ano", scale=1):
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

def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
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

def get_residue_label(column_name: str) -> str:
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