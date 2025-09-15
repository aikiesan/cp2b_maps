"""
CP2B Maps - Map Utilities
Enhanced map rendering utilities for the results page
"""

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium


def create_enhanced_results_map(municipalities, polygons=None, analysis_data=None):
    """
    Create an enhanced map for the results page with better styling and interactivity
    """
    
    # Default center (São Paulo state)
    default_center = [-23.5, -46.6]
    
    # If we have polygon data, calculate the optimal center and bounds
    map_center = default_center
    bounds = None
    
    if polygons and len(polygons) > 0:
        try:
            # Calculate bounds from all polygons
            all_bounds = []
            for polygon in polygons:
                if hasattr(polygon, 'bounds'):
                    bounds_tuple = polygon.bounds
                    all_bounds.append([bounds_tuple[1], bounds_tuple[0]])  # lat, lon
                    all_bounds.append([bounds_tuple[3], bounds_tuple[2]])  # lat, lon
            
            if all_bounds:
                lats = [b[0] for b in all_bounds]
                lons = [b[1] for b in all_bounds]
                map_center = [sum(lats) / len(lats), sum(lons) / len(lons)]
                bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]
        except Exception as e:
            st.warning(f"Erro ao calcular centro do mapa: {e}")
    
    # Create the base map with standard OpenStreetMap tiles
    m = folium.Map(
        location=map_center,
        zoom_start=8 if not bounds else 6,
        tiles='OpenStreetMap'
    )
    
    # Add polygons with enhanced styling
    if polygons and len(polygons) > 0:
        for i, polygon in enumerate(polygons):
            municipality_name = municipalities[i] if i < len(municipalities) else f"Município {i+1}"
            
            # Get analysis data for this municipality if available
            popup_content = f"<b>🏙️ {municipality_name}</b><br><br>"
            
            # Add municipality info from loader if available
            try:
                from .municipality_loader import get_municipality_info
                mun_info = get_municipality_info(municipality_name)
                if mun_info:
                    if 'area_km2' in mun_info:
                        popup_content += f"📏 <b>Área:</b> {mun_info['area_km2']:,.1f} km²<br>"
                    # Region information removed
            except:
                pass
            
            if analysis_data and i < len(analysis_data):
                data = analysis_data[i]
                if isinstance(data, dict):
                    popup_content += "<br><b>📊 Dados da Análise:</b><br>"
                    # Show relevant analysis data, excluding IDs and codes
                    relevant_keys = ['nome_municipio', 'potencial_total', 'potencial_biogas', 'area_km2']
                    shown_count = 0
                    for key, value in data.items():
                        # Skip ID fields and codes
                        if any(skip in key.lower() for skip in ['id', 'codigo', 'cd_', 'sigla']):
                            continue
                        if shown_count >= 4:  # Limit to 4 relevant items
                            break
                        if isinstance(value, (int, float)) and value > 0:
                            popup_content += f"• <b>{format_key_name(key)}:</b> {value:,.0f}<br>"
                            shown_count += 1
            
            # Enhanced polygon styling
            style_function = lambda x, i=i: {
                'fillColor': get_municipality_color(i),
                'color': '#2E8B57',
                'weight': 2,
                'fillOpacity': 0.7,
                'opacity': 0.9
            }
            
            # Add polygon to map
            folium.GeoJson(
                polygon,
                style_function=style_function,
                tooltip=folium.Tooltip(municipality_name, permanent=False),
                popup=folium.Popup(popup_content, max_width=300, parse_html=True)
            ).add_to(m)
            
            # Add centroid markers
            try:
                if hasattr(polygon, 'centroid'):
                    centroid = polygon.centroid
                    folium.Marker(
                        [centroid.y, centroid.x],
                        popup=folium.Popup(popup_content, max_width=300),
                        tooltip=municipality_name,
                        icon=folium.Icon(
                            color=get_marker_color(i),
                            icon='info-sign',
                            prefix='glyphicon'
                        )
                    ).add_to(m)
            except Exception as e:
                pass  # Skip markers if centroid calculation fails
    
    # Layer control não é necessário com apenas uma camada base
    
    # Fit bounds if we have them
    if bounds:
        try:
            m.fit_bounds(bounds, padding=(20, 20))
        except:
            pass
    
    # Add a mini map for better navigation
    try:
        minimap = folium.plugins.MiniMap(toggle_display=True, width=150, height=150)
        m.add_child(minimap)
    except:
        pass  # Skip minimap if plugin is not available
    
    return m


def get_municipality_color(index):
    """Get a unique color for each municipality based on index"""
    colors = [
        '#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336',
        '#009688', '#795548', '#607D8B', '#3F51B5', '#E91E63'
    ]
    return colors[index % len(colors)]


def get_marker_color(index):
    """Get marker color corresponding to municipality color"""
    marker_colors = [
        'green', 'blue', 'orange', 'purple', 'red',
        'darkgreen', 'darkblue', 'gray', 'darkred', 'pink'
    ]
    return marker_colors[index % len(marker_colors)]


def format_key_name(key):
    """Format key names for better display in popups"""
    name_mappings = {
        'total_final_nm_ano': 'Potencial Total (m³/ano)',
        'total_agricola_nm_ano': 'Potencial Agrícola (m³/ano)',
        'total_pecuaria_nm_ano': 'Potencial Pecuária (m³/ano)',
        'populacao_2022': 'População (2022)',
        'area_km2': 'Área (km²)',
        'potencial_biogas': 'Potencial Biogás (m³/ano)',
        'potencial_total': 'Potencial Total (m³/ano)',
        'nome_municipio': 'Município'
    }
    
    # Check if we have a direct mapping
    if key in name_mappings:
        return name_mappings[key]
    
    # Otherwise, format the key nicely
    formatted = key.replace('_', ' ').title()
    formatted = formatted.replace('m Ano', '(m³/ano)')
    formatted = formatted.replace('Km2', '(km²)')
    
    return formatted


def create_simple_overview_map(municipalities, center_lat=-23.5, center_lon=-46.6):
    """
    Create a simple overview map showing municipality locations
    """
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles='OpenStreetMap'
    )
    
    # Add markers for municipalities (as points, since we may not have polygons)
    for i, municipality in enumerate(municipalities):
        # For now, we'll place markers randomly around São Paulo
        # In a real implementation, you'd have actual coordinates
        lat_offset = (i % 5 - 2) * 0.5
        lon_offset = ((i // 5) % 5 - 2) * 0.5
        
        folium.Marker(
            [center_lat + lat_offset, center_lon + lon_offset],
            popup=municipality,
            tooltip=municipality,
            icon=folium.Icon(color=get_marker_color(i), icon='info-sign')
        ).add_to(m)
    
    return m


def add_analysis_legend(map_obj, analysis_type):
    """Add a clear and relevant legend to the map based on analysis type"""
    
    # More descriptive analysis type names
    type_descriptions = {
        'Análise de Proximidade': 'Municípios próximos selecionados',
        'Análise de Resíduos': 'Potencial por tipo de resíduo',
        'Análise de Culturas': 'Distribuição de culturas agrícolas',
        'Potencial de Biogás': 'Potencial de produção de biogás',
        'Perfil Municipal': 'Perfil detalhado dos municípios',
        'Análise Customizada': 'Resultados da análise selecionada'
    }
    
    description = type_descriptions.get(analysis_type, 'Análise de municípios')
    
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 20px; left: 20px; width: 220px; height: auto; 
                background-color: rgba(255, 255, 255, 0.95); 
                border: 2px solid #2E8B57; 
                border-radius: 8px;
                z-index:9999; 
                font-size: 12px; padding: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                ">
    <h4 style="margin: 0 0 8px 0; color: #2E8B57; font-size: 14px;">📊 Legenda</h4>
    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 11px;">{description}</p>
    <div style="font-size: 11px; line-height: 1.4;">
        <p style="margin: 4px 0;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #4CAF50; margin-right: 6px; border-radius: 2px;"></span>Municípios Selecionados</p>
        <p style="margin: 4px 0;"><span style="display: inline-block; width: 12px; height: 12px; border: 2px solid #2E8B57; margin-right: 6px; border-radius: 2px; background: transparent;"></span>Contorno Municipal</p>
        <p style="margin: 4px 0; color: #666;">📍 Clique nos polígonos para mais detalhes</p>
    </div>
    </div>
    '''
    
    map_obj.get_root().html.add_child(folium.Element(legend_html))
    return map_obj


def export_map_as_html(map_obj, filename="cp2b_analysis_map.html"):
    """Export map as standalone HTML file"""
    
    try:
        map_html = map_obj._repr_html_()
        
        # Enhanced HTML with better styling
        enhanced_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CP2B Maps - Análise de Biogás</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }}
                .header {{
                    background: linear-gradient(135deg, #4CAF50 0%, #2E8B57 100%);
                    color: white;
                    padding: 1rem;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .map-container {{
                    height: calc(100vh - 80px);
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CP2B Maps - Resultado da Análise</h1>
                <p>Potencial de Biogás • São Paulo • {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div class="map-container">
                {map_html}
            </div>
        </body>
        </html>
        """
        
        return enhanced_html
        
    except Exception as e:
        st.error(f"Erro ao exportar mapa: {e}")
        return None