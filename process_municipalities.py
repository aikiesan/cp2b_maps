#!/usr/bin/env python3
"""
Process SP Municipalities Shapefile for CP2B Maps
This script optimizes the shapefile for better performance in the web application
"""

import geopandas as gpd
import pandas as pd
import json
import pickle
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_municipalities_shapefile():
    """
    Process the municipalities shapefile to optimize it for the CP2B Maps application
    """
    
    # File paths
    input_shapefile = Path("shapefile/SP_Municipios_2024.shp")
    output_dir = Path("data/processed")
    output_dir.mkdir(exist_ok=True)
    
    logger.info(f"Loading shapefile: {input_shapefile}")
    
    # Load the shapefile
    try:
        gdf = gpd.read_file(input_shapefile)
        logger.info(f"Loaded {len(gdf)} municipalities")
        logger.info(f"Original CRS: {gdf.crs}")
        logger.info(f"Columns: {gdf.columns.tolist()}")
    except Exception as e:
        logger.error(f"Error loading shapefile: {e}")
        return None
    
    # Convert to WGS84 (EPSG:4326) for web mapping
    if gdf.crs != 'EPSG:4326':
        logger.info("Converting to WGS84 (EPSG:4326)")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Clean and standardize column names
    gdf = gdf.rename(columns={
        'CD_MUN': 'codigo_municipio',
        'NM_MUN': 'nome_municipio',
        'CD_RGI': 'codigo_rgi',
        'NM_RGI': 'nome_rgi',
        'CD_RGINT': 'codigo_regiao_imediata',
        'NM_RGINT': 'nome_regiao_imediata',
        'CD_UF': 'codigo_uf',
        'NM_UF': 'nome_uf',
        'SIGLA_UF': 'sigla_uf',
        'CD_REGIA': 'codigo_regiao',
        'NM_REGIA': 'nome_regiao',
        'SIGLA_RG': 'sigla_regiao',
        'CD_CONCU': 'codigo_concurb',
        'NM_CONCU': 'nome_concurb',
        'AREA_KM2': 'area_km2'
    })
    
    # Simplify geometries for better performance
    logger.info("Simplifying geometries...")
    tolerance_values = [0.001, 0.0005, 0.0001]  # Different levels of simplification
    
    for tolerance in tolerance_values:
        gdf_simplified = gdf.copy()
        gdf_simplified['geometry'] = gdf_simplified['geometry'].simplify(
            tolerance=tolerance, 
            preserve_topology=True
        )
        
        # Calculate file size reduction
        original_size = gdf.memory_usage(deep=True).sum()
        simplified_size = gdf_simplified.memory_usage(deep=True).sum()
        reduction = (1 - simplified_size/original_size) * 100
        
        # Save simplified versions
        output_file = output_dir / f"sp_municipios_simplified_{str(tolerance).replace('.', '_')}.geojson"
        gdf_simplified.to_file(output_file, driver='GeoJSON')
        logger.info(f"Saved simplified version (tolerance={tolerance}): {output_file}")
        logger.info(f"Memory reduction: {reduction:.1f}%")
    
    # Create a municipality lookup dictionary for fast access
    logger.info("Creating municipality lookup dictionary...")
    municipality_lookup = {}
    
    for idx, row in gdf.iterrows():
        codigo = row['codigo_municipio']
        nome = row['nome_municipio'].upper().strip()
        
        municipality_lookup[codigo] = {
            'codigo': codigo,
            'nome': row['nome_municipio'],
            'nome_upper': nome,
            'area_km2': row['area_km2'],
            'regiao_imediata': row['nome_regiao_imediata'],
            'regiao_intermediaria': row['nome_rgi'],
            'geometry_bounds': list(row['geometry'].bounds),
            'centroid': [row['geometry'].centroid.y, row['geometry'].centroid.x]
        }
        
        # Also add by name for lookup
        municipality_lookup[nome] = municipality_lookup[codigo]
    
    # Save lookup dictionary
    lookup_file = output_dir / "municipality_lookup.json"
    with open(lookup_file, 'w', encoding='utf-8') as f:
        json.dump(municipality_lookup, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Saved municipality lookup: {lookup_file}")
    
    # Create a compact version with only essential data for the web app
    logger.info("Creating compact version for web application...")
    
    # Keep only essential columns
    essential_columns = [
        'codigo_municipio', 'nome_municipio', 'area_km2', 
        'nome_regiao_imediata', 'nome_rgi', 'geometry'
    ]
    gdf_compact = gdf[essential_columns].copy()
    
    # Further simplify for web use
    gdf_compact['geometry'] = gdf_compact['geometry'].simplify(
        tolerance=0.0005, preserve_topology=True
    )
    
    # Save compact version
    compact_file = output_dir / "sp_municipios_compact.geojson"
    gdf_compact.to_file(compact_file, driver='GeoJSON')
    logger.info(f"Saved compact version: {compact_file}")
    
    # Create a version with centroids only for quick map markers
    logger.info("Creating centroids version...")
    gdf_centroids = gdf.copy()
    gdf_centroids['geometry'] = gdf_centroids['geometry'].centroid
    
    centroids_file = output_dir / "sp_municipios_centroids.geojson"
    gdf_centroids[essential_columns].to_file(centroids_file, driver='GeoJSON')
    logger.info(f"Saved centroids version: {centroids_file}")
    
    # Create a pickle file for fastest loading in Python
    logger.info("Creating pickle file for fastest loading...")
    pickle_file = output_dir / "sp_municipios_optimized.pkl"
    with open(pickle_file, 'wb') as f:
        pickle.dump(gdf_compact, f)
    logger.info(f"Saved pickle version: {pickle_file}")
    
    # Print summary statistics
    logger.info("\n=== PROCESSING SUMMARY ===")
    logger.info(f"Total municipalities processed: {len(gdf)}")
    logger.info(f"Output directory: {output_dir.absolute()}")
    logger.info(f"Files created:")
    for file in output_dir.glob("*"):
        size_mb = file.stat().st_size / (1024*1024)
        logger.info(f"  - {file.name}: {size_mb:.2f} MB")
    
    return gdf_compact

def create_integration_module():
    """
    Create a module to integrate the processed shapefiles with the existing application
    """
    
    integration_code = '''"""
CP2B Maps - Municipality Geometry Integration
Module to load and provide municipality geometries for the results page
"""

import geopandas as gpd
import pandas as pd
import json
import pickle
from pathlib import Path
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class MunicipalityGeometryLoader:
    """Efficiently loads and provides municipality geometries"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data" / "processed"
        self._gdf = None
        self._lookup = None
        
    @st.cache_data
    def load_geometries(_self):
        """Load municipality geometries with caching"""
        try:
            # Try to load the optimized pickle file first (fastest)
            pickle_file = _self.data_dir / "sp_municipios_optimized.pkl"
            if pickle_file.exists():
                with open(pickle_file, 'rb') as f:
                    _self._gdf = pickle.load(f)
                logger.info(f"Loaded {len(_self._gdf)} municipalities from pickle file")
                return _self._gdf
            
            # Fallback to GeoJSON
            geojson_file = _self.data_dir / "sp_municipios_compact.geojson"
            if geojson_file.exists():
                _self._gdf = gpd.read_file(geojson_file)
                logger.info(f"Loaded {len(_self._gdf)} municipalities from GeoJSON")
                return _self._gdf
            
            logger.warning("No processed municipality files found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading municipality geometries: {e}")
            return None
    
    @st.cache_data
    def load_lookup(_self):
        """Load municipality lookup dictionary"""
        try:
            lookup_file = _self.data_dir / "municipality_lookup.json"
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    _self._lookup = json.load(f)
                logger.info("Loaded municipality lookup dictionary")
                return _self._lookup
            
            logger.warning("Municipality lookup file not found")
            return {}
            
        except Exception as e:
            logger.error(f"Error loading municipality lookup: {e}")
            return {}
    
    def get_municipality_geometries(self, municipality_names):
        """
        Get geometries for a list of municipality names
        
        Args:
            municipality_names (list): List of municipality names
            
        Returns:
            list: List of geometry objects
        """
        if self._gdf is None:
            self._gdf = self.load_geometries()
        
        if self._gdf is None:
            return []
        
        geometries = []
        for name in municipality_names:
            # Try to find by name (case insensitive)
            mask = self._gdf['nome_municipio'].str.upper() == name.upper()
            matches = self._gdf[mask]
            
            if len(matches) > 0:
                geometries.append(matches.iloc[0]['geometry'])
            else:
                logger.warning(f"Municipality not found: {name}")
        
        return geometries
    
    def get_municipality_info(self, municipality_name):
        """Get detailed information about a municipality"""
        if self._lookup is None:
            self._lookup = self.load_lookup()
        
        name_upper = municipality_name.upper()
        return self._lookup.get(name_upper, {})
    
    def get_centroids(self, municipality_names):
        """Get centroids for municipality names"""
        centroids = []
        for name in municipality_names:
            info = self.get_municipality_info(name)
            if 'centroid' in info:
                centroids.append(info['centroid'])
        return centroids

# Global instance
municipality_loader = MunicipalityGeometryLoader()

def get_municipality_geometries(municipality_names):
    """Convenience function to get municipality geometries"""
    return municipality_loader.get_municipality_geometries(municipality_names)

def get_municipality_info(municipality_name):
    """Convenience function to get municipality info"""
    return municipality_loader.get_municipality_info(municipality_name)
'''
    
    # Create the integration module
    modules_dir = Path("src/streamlit/modules")
    integration_file = modules_dir / "municipality_loader.py"
    
    with open(integration_file, 'w', encoding='utf-8') as f:
        f.write(integration_code)
    
    logger.info(f"Created integration module: {integration_file}")

if __name__ == "__main__":
    print("CP2B Maps - Municipality Shapefile Processor")
    print("=" * 50)
    
    # Process the shapefile
    result = process_municipalities_shapefile()
    
    if result is not None:
        print("\nProcessing completed successfully!")
        
        # Create integration module
        create_integration_module()
        print("Integration module created!")
        
        print("\nNext steps:")
        print("1. The processed files are in 'data/processed/' directory")
        print("2. Integration module created at 'src/streamlit/modules/municipality_loader.py'")
        print("3. Update results_page.py to use the new municipality loader")
        print("4. Test the 'VER NO MAPA' functionality")
        
    else:
        print("Processing failed!")