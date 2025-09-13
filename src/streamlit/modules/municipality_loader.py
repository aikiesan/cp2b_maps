"""
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
        # Get the absolute path to the project root and data directory
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent  # Go up from modules/streamlit/src/CP2B_Maps
        self.data_dir = project_root / "data" / "processed"
        self._gdf = None
        self._lookup = None
        
        # Debug path information
        logger.info(f"Municipality loader initialized")
        logger.info(f"Current file: {current_file}")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Data directory exists: {self.data_dir.exists()}")
        
    def load_geometries(self):
        """Load municipality geometries with caching"""
        try:
            # Try to load the optimized pickle file first (fastest)
            pickle_file = self.data_dir / "sp_municipios_optimized.pkl"
            if pickle_file.exists():
                with open(pickle_file, 'rb') as f:
                    self._gdf = pickle.load(f)
                logger.info(f"Loaded {len(self._gdf)} municipalities from pickle file")
                return self._gdf
            
            # Fallback to GeoJSON
            geojson_file = self.data_dir / "sp_municipios_compact.geojson"
            if geojson_file.exists():
                self._gdf = gpd.read_file(geojson_file)
                logger.info(f"Loaded {len(self._gdf)} municipalities from GeoJSON")
                return self._gdf
            
            logger.warning("No processed municipality files found")
            return None
            
        except Exception as e:
            logger.error(f"Error loading municipality geometries: {e}")
            return None
    
    def load_lookup(self):
        """Load municipality lookup dictionary"""
        try:
            lookup_file = self.data_dir / "municipality_lookup.json"
            if lookup_file.exists():
                with open(lookup_file, 'r', encoding='utf-8') as f:
                    self._lookup = json.load(f)
                logger.info("Loaded municipality lookup dictionary")
                return self._lookup
            
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
