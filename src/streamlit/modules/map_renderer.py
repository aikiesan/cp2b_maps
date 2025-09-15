"""
Map Rendering Module for CP2B Maps
Handles all map creation and layer rendering functions
"""

import os
import logging
from pathlib import Path
import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
from folium.plugins import MarkerCluster, MiniMap, HeatMap
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Import dependencies
from .data_loader import prepare_layer_data

# Check for raster system availability
try:
    from ..raster.raster_loader import RasterLoader
    from ..raster.raster_loader import create_mapbiomas_legend
    HAS_RASTER_SYSTEM = True
except ImportError:
    HAS_RASTER_SYSTEM = False
    logger.warning("Raster system not available")

def add_plantas_layer_fast(m, plantas_gdf):
    """Adiciona camada de plantas de forma otimizada"""
    if plantas_gdf is None or len(plantas_gdf) == 0:
        return
    
    # Usar MarkerCluster para performance com muitos pontos
    marker_cluster = MarkerCluster(name="🏭 Plantas de Biogás").add_to(m)
    
    color_map = {
        'Biogás': '#32CD32',
        'Aterro': '#8B4513', 
        'Tratamento': '#4169E1',
        'Outros': '#9370DB'
    }
    
    for _, row in plantas_gdf.iterrows():
        tipo = row.get('TIPO_PLANT', 'Outros')
        color = color_map.get(tipo, '#666666')
        
        folium.CircleMarker(
            location=[row['geometry'].y, row['geometry'].x],
            radius=8,
            color=color,
            fillColor=color,
            fillOpacity=0.7,
            popup=f"<b>Planta:</b> {row.get('NOME', 'N/A')}<br><b>Tipo:</b> {tipo}",
            tooltip=f"{row.get('NOME', 'Planta de Biogás')} ({tipo})"
        ).add_to(marker_cluster)

def add_lines_layer_fast(m, gdf, name, color, weight=2):
    """Adiciona camada de linhas de forma otimizada"""
    if gdf is None or len(gdf) == 0:
        return
        
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'color': color,
            'weight': weight,
            'opacity': 0.8
        },
        tooltip=folium.GeoJsonTooltip(fields=gdf.columns[:3].tolist() if len(gdf.columns) > 0 else []),
        name=name
    ).add_to(m)

def add_polygons_layer_fast(m, gdf, name, color, fill_opacity=0.3):
    """Adiciona camada de polígonos de forma otimizada"""
    if gdf is None or len(gdf) == 0:
        return
        
    folium.GeoJson(
        gdf,
        style_function=lambda x: {
            'fillColor': color,
            'color': color,
            'weight': 1,
            'fillOpacity': fill_opacity,
            'opacity': 0.6
        },
        tooltip=folium.GeoJsonTooltip(fields=gdf.columns[:3].tolist() if len(gdf.columns) > 0 else []),
        name=name
    ).add_to(m)

def add_regioes_layer_fast(m, regioes_gdf):
    """Adiciona camada de regiões administrativas de forma otimizada"""
    if regioes_gdf is None or len(regioes_gdf) == 0:
        return
        
    for _, row in regioes_gdf.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x: {
                'fillColor': '#FF6B6B',
                'color': '#FF6B6B', 
                'weight': 2,
                'fillOpacity': 0.2,
                'opacity': 0.8
            },
            popup=folium.GeoJsonPopup(fields=[row['Nome']], 
                                    aliases=['Região:'],
                                    labels=True,
                                    max_width=200),
            tooltip=f"Região: {row['Nome']}"
        ).add_to(m)

def add_municipality_circles_fast(m, df_merged, display_col, viz_type):
    """Adiciona círculos dos municípios de forma otimizada"""
    if df_merged is None or df_merged.empty or display_col not in df_merged.columns:
        return
    
    # Color scale setup
    values = df_merged[display_col].dropna()
    if len(values) == 0:
        return
        
    min_val, max_val = values.min(), values.max()
    if min_val == max_val:
        return
    
    # Color palette - 5 bins
    colors = ['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#253494']
    
    for _, row in df_merged.iterrows():
        try:
            lat, lon = float(row['lat']), float(row['lon'])
            value = float(row[display_col])
            municipio_nome = str(row.get('nome_municipio', 'Desconhecido'))
            
            if pd.isna(value) or value <= 0:
                continue
                
            # Calculate color based on quantiles
            percentile = (value - min_val) / (max_val - min_val)
            color_idx = min(int(percentile * 5), 4)
            color = colors[color_idx]
            
            # Calculate radius based on value
            if viz_type == "Círculos Proporcionais":
                # Logarithmic scale for better visualization
                radius = 5 + (np.log1p(value - min_val + 1) / np.log1p(max_val - min_val + 1)) * 25
            else:  # Fixed size
                radius = 10
            
            # Create popup content
            popup_content = f"""
            <div style="font-family: Arial; font-size: 12px; max-width: 300px;">
                <h4 style="margin: 0 0 8px 0; color: #2E8B57;">{municipio_nome}</h4>
                <p style="margin: 4px 0;"><b>🏭 Potencial Total:</b> {value:,.0f} m³/ano</p>
                <p style="margin: 4px 0;"><b>👥 População:</b> {row.get('populacao_2022', 'N/A'):,}</p>
                <p style="margin: 4px 0;"><b>📍 Coordenadas:</b> {lat:.4f}, {lon:.4f}</p>
            </div>
            """
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                popup=folium.Popup(popup_content, max_width=320),
                tooltip=f"{municipio_nome}: {value:,.0f} m³/ano",
                color='white',
                weight=2,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Erro ao processar município {row.get('nome_municipio', 'Unknown')}: {e}")
            continue

def add_choropleth_layer(m, gdf, df_merged, display_col):
    """Add choropleth layer to map using municipality boundaries"""
    if gdf is None or df_merged is None or df_merged.empty:
        return
        
    try:
        # Merge geometry with data
        merged_gdf = gdf.merge(df_merged, on='cd_mun', how='inner')
        
        if merged_gdf.empty or display_col not in merged_gdf.columns:
            return
        
        # Create choropleth layer
        folium.Choropleth(
            geo_data=merged_gdf,
            name='Potencial de Biogás',
            data=merged_gdf,
            columns=['cd_mun', display_col],
            key_on='feature.properties.cd_mun',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=f'Potencial ({display_col.replace("_", " ").title()})'
        ).add_to(m)
        
        # Add interactive layer for tooltips
        folium.features.GeoJson(
            merged_gdf,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'transparent',
                'weight': 0
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['nome_municipio', display_col, 'populacao_2022'],
                aliases=['Município:', 'Potencial:', 'População:'],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: white;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=200,
            )
        ).add_to(m)
        
    except Exception as e:
        logger.error(f"Error adding choropleth layer: {e}")

def add_proximity_visualization(m, catchment_info):
    """Add visual feedback for proximity analysis (marker + circle)"""
    if not catchment_info or not catchment_info.get("center"):
        return
    
    try:
        center_lat, center_lon = catchment_info["center"]
        radius_km = catchment_info["radius"]
        
        # Create dedicated feature group for proximity analysis
        proximity_group = folium.FeatureGroup(name="🎯 Análise de Proximidade", show=True)
        
        # Add center marker with crosshairs icon
        folium.Marker(
            location=[center_lat, center_lon],
            popup=f"""
            <div style="font-family: Arial; font-size: 12px; text-align: center;">
                <h4 style="margin: 0 0 8px 0; color: #c93c3c;">🎯 Centro de Análise</h4>
                <p style="margin: 2px 0;"><b>📍 Coordenadas:</b><br>{center_lat:.4f}, {center_lon:.4f}</p>
                <p style="margin: 2px 0;"><b>📏 Raio:</b> {radius_km} km</p>
                <p style="margin: 2px 0;"><b>🏞️ Área:</b> {3.14159 * radius_km * radius_km:.0f} km²</p>
            </div>
            """,
            tooltip=f"🎯 Centro de Análise (Raio: {radius_km} km)",
            icon=folium.Icon(color='red', icon='bullseye', prefix='fa')
        ).add_to(proximity_group)
        
        # Add radius circle
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,  # Convert km to meters
            color='#c93c3c',
            weight=3,
            fill=True,
            fill_color='#c93c3c',
            fill_opacity=0.1,
            popup=f"""
            <div style="font-family: Arial; font-size: 12px; text-align: center;">
                <h4 style="margin: 0 0 8px 0; color: #c93c3c;">🌍 Área de Análise</h4>
                <p style="margin: 2px 0;"><b>📏 Raio:</b> {radius_km} km</p>
                <p style="margin: 2px 0;"><b>🏞️ Área Total:</b> {3.14159 * radius_km * radius_km:.0f} km²</p>
                <p style="margin: 2px 0;"><b>🔍 Status:</b> Análise Ativa</p>
            </div>
            """,
            tooltip=f"Área de análise: {radius_km} km de raio"
        ).add_to(proximity_group)
        
        # Add the group to the map
        proximity_group.add_to(m)
        
        logger.info(f"Added proximity visualization: center=({center_lat:.4f}, {center_lon:.4f}), radius={radius_km}km")
        
    except Exception as e:
        logger.error(f"Error adding proximity visualization: {e}")

def create_basic_map():
    """Cria um mapa básico para fallback"""
    return folium.Map(location=[-22.5, -48.5], zoom_start=7, tiles='CartoDB positron')

def export_map_as_html(map_obj, filename="cp2b_map.html"):
    """Exporta o mapa como arquivo HTML"""
    try:
        # Get the HTML representation of the map
        map_html = map_obj._repr_html_()
        
        # Add some custom styling and metadata
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CP2B Maps - Biogas Potential Analysis</title>
            <style>
                body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
                .header {{ background: #2E8B57; color: white; padding: 10px; text-align: center; }}
                .footer {{ background: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>CP2B Maps - Análise de Potencial de Biogás</h2>
                <p>Gerado em: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
            <div style="height: calc(100vh - 120px);">
                {map_html}
            </div>
            <div class="footer">
                <p>Desenvolvido pela equipe CP2B Maps | Universidade</p>
            </div>
        </body>
        </html>
        """
        
        return full_html.encode('utf-8')
        
    except Exception as e:
        logger.error(f"Erro ao exportar mapa: {e}")
        return None