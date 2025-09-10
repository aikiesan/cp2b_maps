#!/usr/bin/env python3
"""
Geometry Optimization Script for CP2B Maps
Converts shapefiles to optimized GeoParquet format with simplified geometries
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
import time

def optimize_municipalities():
    """Convert municipality shapefile to optimized GeoParquet"""
    print("Loading municipality shapefile...")
    start_time = time.time()
    
    # Load shapefile
    shapefile_path = Path("shapefile/Municipios_SP_shapefile.shp")
    gdf = gpd.read_file(shapefile_path)
    
    print(f"Loaded {len(gdf)} municipalities in {time.time() - start_time:.2f}s")
    print(f"Original file size: {shapefile_path.stat().st_size / (1024*1024):.1f} MB")
    
    # Ensure proper CRS
    if gdf.crs != 'EPSG:4326':
        print("Converting to EPSG:4326...")
        gdf = gdf.to_crs('EPSG:4326')
    
    # Standardize column names
    gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
    gdf['nome_municipio'] = gdf['NM_MUN']
    
    # Keep only essential columns for mapping
    essential_columns = [
        'cd_mun', 'nome_municipio', 'CD_MUN', 'NM_MUN', 
        'AREA_KM2', 'geometry'
    ]
    
    # Filter to existing columns
    available_columns = [col for col in essential_columns if col in gdf.columns]
    gdf_slim = gdf[available_columns].copy()
    
    print(f"Kept {len(available_columns)} essential columns")
    
    # Create different optimization levels
    optimizations = {
        'high_detail': 0.001,    # Very detailed for close zoom
        'medium_detail': 0.01,   # Good for state-wide view
        'low_detail': 0.02       # Fast loading for overview
    }
    
    for level, tolerance in optimizations.items():
        print(f"Creating {level} optimization (tolerance: {tolerance})...")
        start_opt = time.time()
        
        # Simplify geometry
        gdf_opt = gdf_slim.copy()
        gdf_opt['geometry'] = gdf_opt['geometry'].simplify(tolerance, preserve_topology=True)
        
        # Save as GeoParquet
        output_path = Path(f"shapefile/municipalities_{level}.parquet")
        gdf_opt.to_parquet(output_path)
        
        file_size = output_path.stat().st_size / (1024*1024)
        print(f"Success {level}: {file_size:.1f} MB in {time.time() - start_opt:.2f}s")
    
    print(f"Optimization complete! Total time: {time.time() - start_time:.2f}s")
    return True

def create_centroids():
    """Create municipality centroids for point-based visualization"""
    print("\nCreating municipality centroids...")
    
    shapefile_path = Path("shapefile/Municipios_SP_shapefile.shp")
    gdf = gpd.read_file(shapefile_path)
    
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')
    
    # Create centroids
    gdf['geometry'] = gdf['geometry'].centroid
    
    # Keep essential data
    centroids = gdf[['CD_MUN', 'NM_MUN']].copy()
    centroids['cd_mun'] = centroids['CD_MUN'].astype(str)
    centroids['nome_municipio'] = centroids['NM_MUN']
    centroids['lat'] = gdf.geometry.y
    centroids['lon'] = gdf.geometry.x
    
    # Save as regular parquet (no geometry needed)
    output_path = Path("shapefile/municipality_centroids.parquet")
    centroids.to_parquet(output_path)
    
    print(f"Created centroids: {output_path.stat().st_size / 1024:.1f} KB")
    return True

if __name__ == "__main__":
    print("Starting geometry optimization...")
    optimize_municipalities()
    create_centroids()
    print("All optimizations complete!")