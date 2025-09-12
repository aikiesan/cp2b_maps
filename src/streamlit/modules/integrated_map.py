"""
Integrated Map Creation Module for CP2B Maps
Combines all map functionality with proximity analysis
"""

import folium
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import logging

from .map_renderer import (
    add_plantas_layer_fast, add_lines_layer_fast, add_polygons_layer_fast,
    add_regioes_layer_fast, add_municipality_circles_fast, add_choropleth_layer,
    add_proximity_visualization
)
from .data_loader import prepare_layer_data, load_optimized_geometries

logger = logging.getLogger(__name__)

def create_integrated_map(df, display_col, layers_config, viz_type, catchment_info=None):
    """
    Create a comprehensive map with all layers and proximity analysis
    
    Args:
        df: Municipality data DataFrame
        display_col: Column to display (e.g., 'total_final_nm_ano')
        layers_config: Dict of layer visibility settings
        viz_type: Visualization type ('Choropleth', 'Círculos Proporcionais', etc.)
        catchment_info: Dict with proximity analysis info {'center': [lat, lon], 'radius': km}
    
    Returns:
        folium.Map: Complete map with all requested layers and visualizations
    """
    
    try:
        # 1. Create base map
        m = folium.Map(
            location=[-22.5, -48.5], 
            zoom_start=7,
            tiles='CartoDB positron',
            prefer_canvas=True
        )
        
        # 2. Add São Paulo state border (always visible)
        try:
            sp_border_path = Path(__file__).parent.parent.parent.parent / "shapefile" / "Limite_SP.shp"
            if sp_border_path.exists():
                sp_border = gpd.read_file(sp_border_path)
                if sp_border.crs != 'EPSG:4326':
                    sp_border = sp_border.to_crs('EPSG:4326')
                
                folium.GeoJson(
                    sp_border,
                    style_function=lambda x: {
                        'fillColor': 'rgba(0,0,0,0)',
                        'color': '#2E8B57',
                        'weight': 2,
                        'opacity': 0.7,
                        'dashArray': '5, 5'
                    },
                    tooltip='Estado de São Paulo',
                    interactive=False
                ).add_to(m)
        except Exception as e:
            logger.warning(f"Could not load SP border: {e}")
        
        # 3. Load layer data if any layers are enabled
        layer_data = None
        if any(layers_config.values()):
            with st.spinner("⚡ Carregando dados das camadas..."):
                layer_data = prepare_layer_data()
        
        # 4. Add infrastructure layers
        if layer_data:
            if layers_config.get('show_plantas_biogas') and layer_data['plantas'] is not None:
                add_plantas_layer_fast(m, layer_data['plantas'])
            
            if layers_config.get('show_gasodutos_dist') and layer_data['gasodutos_dist'] is not None:
                add_lines_layer_fast(m, layer_data['gasodutos_dist'], "Gasodutos Distribuição", "#0066CC")
                
            if layers_config.get('show_gasodutos_transp') and layer_data['gasodutos_transp'] is not None:
                add_lines_layer_fast(m, layer_data['gasodutos_transp'], "Gasodutos Transporte", "#CC0000", weight=4)
            
            if layers_config.get('show_rodovias') and layer_data['rodovias'] is not None:
                add_lines_layer_fast(m, layer_data['rodovias'], "Rodovias Estaduais", "#FF4500", weight=2)
                
            if layers_config.get('show_rios') and layer_data['rios'] is not None:
                add_lines_layer_fast(m, layer_data['rios'], "Rios Principais", "#1E90FF", weight=2)
            
            if layers_config.get('show_regioes_admin') and layer_data['regioes_admin'] is not None:
                add_regioes_layer_fast(m, layer_data['regioes_admin'])
        
        # 5. Add municipality data visualization
        if layers_config.get('show_municipios_biogas', True) and not df.empty:
            try:
                centroid_path = Path(__file__).parent.parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
                
                if centroid_path.exists():
                    centroids_df = pd.read_parquet(centroid_path)
                    
                    if 'lat' in centroids_df.columns and 'lon' in centroids_df.columns:
                        # Create geometry from lat/lon
                        from shapely.geometry import Point
                        centroids_df['geometry'] = centroids_df.apply(
                            lambda row: Point(float(row['lon']), float(row['lat'])), axis=1
                        )
                        centroids_gdf = gpd.GeoDataFrame(centroids_df, crs='EPSG:4326')
                        
                        # Merge with municipality data
                        df_merged = centroids_gdf.merge(df, on='cd_mun', how='inner')
                        
                        # Fix duplicate column names
                        if 'nome_municipio_y' in df_merged.columns:
                            df_merged['nome_municipio'] = df_merged['nome_municipio_y']
                        elif 'nome_municipio_x' in df_merged.columns:
                            df_merged['nome_municipio'] = df_merged['nome_municipio_x']
                        
                        # Convert numeric columns
                        numeric_cols = ['lat', 'lon', 'cd_mun', 'populacao_2022', 'total_final_nm_ano', 'total_agricola_nm_ano', 'total_pecuaria_nm_ano']
                        for col in df_merged.columns:
                            if col in numeric_cols and col != 'geometry' and col != 'nome_municipio':
                                try:
                                    df_merged[col] = df_merged[col].astype(float)
                                except:
                                    pass
                        
                        if not df_merged.empty and display_col in df_merged.columns:
                            # Choose visualization type
                            if viz_type == "Mapa de Preenchimento (Coroplético)":
                                # Load municipality geometries for choropleth
                                municipality_gdf = load_optimized_geometries()
                                if municipality_gdf is not None:
                                    add_choropleth_layer(m, municipality_gdf, df_merged, display_col)
                            else:
                                # Use circles (proportional or fixed)
                                add_municipality_circles_fast(m, df_merged, display_col, viz_type)
                                
            except Exception as e:
                logger.error(f"Error adding municipality visualization: {e}")
                st.error(f"❌ Erro ao carregar visualização dos municípios: {e}")
        
        # 6. Add proximity analysis visualization (MOST IMPORTANT!)
        if catchment_info:
            add_proximity_visualization(m, catchment_info)
            logger.info(f"Proximity visualization added to map: {catchment_info}")
        
        # 7. Add layer control
        folium.LayerControl().add_to(m)
        
        return m
        
    except Exception as e:
        logger.error(f"Error creating integrated map: {e}")
        st.error(f"❌ Erro na criação do mapa: {e}")
        return folium.Map(location=[-22.5, -48.5], zoom_start=7, tiles='CartoDB positron')

def render_proximity_results_panel(results, center_coordinates, radius_km):
    """Render a professional results panel below the map"""
    logger.info(f"🎨 Rendering professional panel: {len(results) if results else 0} results")
    if not results:
        st.warning("⚠️ No results to display in professional panel")
        return
    
    try:
        st.markdown("---")
        st.markdown(f"### 🎯 Análise de Uso do Solo - Raio de {radius_km} km")
        
        if center_coordinates:
            center_lat, center_lon = center_coordinates
            st.caption(f"**📍 Centro:** {center_lat:.4f}, {center_lon:.4f} | **📏 Raio:** {radius_km} km | **🏞️ Área Total:** {3.14159 * radius_km * radius_km:.0f} km²")
        
        if isinstance(results, dict) and results:
            # Convert to DataFrame for better display
            results_df = pd.DataFrame([
                {'Uso do Solo': uso, 'Área (hectares)': area, 'Área (km²)': area/100}
                for uso, area in results.items() if area > 0
            ]).sort_values('Área (hectares)', ascending=False)
            
            if not results_df.empty:
                # Separate agricultural from other uses
                agricultural_keywords = ['🌾', '🌱', '☕', '🍊', '🌴', '🌲']
                agri_df = results_df[results_df['Uso do Solo'].str.contains('|'.join(agricultural_keywords), na=False)]
                other_df = results_df[~results_df['Uso do Solo'].str.contains('|'.join(agricultural_keywords), na=False)]
                
                col1, col2 = st.columns([1.5, 1])
                
                with col1:
                    # Data tables
                    if not agri_df.empty:
                        st.success(f"✅ **Culturas Agrícolas Encontradas: {len(agri_df)} tipos**")
                        st.dataframe(agri_df[['Uso do Solo', 'Área (hectares)']], 
                                   width='stretch', hide_index=True)
                        
                        if not other_df.empty:
                            with st.expander(f"ℹ️ Outros Usos do Solo ({len(other_df)} tipos)"):
                                st.dataframe(other_df[['Uso do Solo', 'Área (hectares)']], 
                                           width='stretch', hide_index=True)
                    else:
                        st.warning("⚠️ **Nenhuma Cultura Agrícola Encontrada**")
                        if not other_df.empty:
                            st.info(f"**Outros Usos Identificados: {len(other_df)} tipos**")
                            st.dataframe(other_df[['Uso do Solo', 'Área (hectares)']], 
                                       width='stretch', hide_index=True)
                
                with col2:
                    # Summary metrics
                    total_area = results_df['Área (hectares)'].sum()
                    agri_area = agri_df['Área (hectares)'].sum() if not agri_df.empty else 0
                    agri_percentage = (agri_area / total_area * 100) if total_area > 0 else 0
                    
                    st.metric("📊 Área Analisada", f"{total_area:,.0f} ha")
                    st.metric("🌾 Área Agrícola", f"{agri_area:,.0f} ha")
                    st.metric("📈 % Agrícola", f"{agri_percentage:.1f}%")
                    
                    # Top use
                    if not results_df.empty:
                        top_use = results_df.iloc[0]
                        clean_name = top_use['Uso do Solo']
                        for emoji in agricultural_keywords + ['🌳', '🏘️', '💧', '🌿']:
                            clean_name = clean_name.replace(f'{emoji} ', '')
                        st.metric("🥇 Uso Predominante", clean_name, 
                                f"{top_use['Área (hectares)']:,.0f} ha")
                    
                    # Pie chart
                    try:
                        import plotly.express as px
                        if len(results_df) > 1:
                            fig = px.pie(
                                results_df.head(8),  # Top 8 to avoid clutter
                                values='Área (hectares)', 
                                names='Uso do Solo',
                                title='Distribuição de Uso do Solo'
                            )
                            fig.update_layout(height=300, showlegend=False)
                            st.plotly_chart(fig)
                    except ImportError:
                        pass
            else:
                st.info("🔍 Nenhum uso do solo identificado na área selecionada.")
        else:
            st.warning("⚠️ A análise não retornou resultados válidos.")
            
    except Exception as e:
        logger.error(f"❌ Error in professional results panel: {e}")
        st.error(f"❌ Error rendering results panel: {e}")
        # Fallback to simple display
        st.write("**Results (fallback):**")
        for cultura, area in results.items():
            st.write(f"- {cultura}: {area:,.1f} ha")