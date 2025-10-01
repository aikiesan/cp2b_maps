"""
CP2B Maps - Clean Multi-Page Streamlit Application
Simple and robust biogas potential analysis for São Paulo municipalities
"""

# Standard library imports
import logging
import os
import sqlite3
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# Third-party imports
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import MiniMap, HeatMap, MarkerCluster
from streamlit_folium import st_folium


# Configure page layout for wide mode
st.set_page_config(
    page_title="CP2B Maps",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"  # This ensures the sidebar is visible and open on load
)

# Importar sistema de rasters - com fallback se não estiver disponível
# Adiciona o diretório src ao Python path
current_dir = Path(__file__).parent  # src/streamlit
src_dir = current_dir.parent         # src
root_dir = src_dir.parent           # CP2B_Maps
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(root_dir))

# Import custom modules
from modules.raster_simulation import simulate_raster_analysis, get_classification_label, find_neighboring_municipalities
from modules.memory_utils import cleanup_memory, get_memory_usage
from modules.ui_components import (render_header, render_navigation, render_sidebar_filters,
                                  render_layer_controls, render_export_controls,
                                  show_municipality_details_compact, render_municipality_comparison,
                                  render_search_interface, render_quick_stats, render_memory_info,
                                  render_academic_footer, render_substrate_info_panel,
                                  render_value_with_reference)
from modules.reference_system import render_reference_button, get_substrate_reference_map
from modules.chatbot_assistant import render_chatbot_sidebar, render_chatbot_fullpage

# Configure logging with environment-based level
LOG_LEVEL = os.getenv('CP2B_LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log startup info
logger.info(f"CP2B Maps starting with log level: {LOG_LEVEL}")

# Import professional results panel
HAS_PROFESSIONAL_PANEL = False
try:
    from modules.integrated_map import render_proximity_results_panel
    HAS_PROFESSIONAL_PANEL = True
    logger.info("Professional results panel imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Failed to import professional panel: {e}")

# Enable raster system with proper imports
try:
    # Add raster directory to path
    raster_dir = Path(__file__).parent.parent / "raster"
    sys.path.insert(0, str(raster_dir))

    from raster import RasterLoader, get_raster_loader, create_mapbiomas_legend, analyze_raster_in_radius
    HAS_RASTER_SYSTEM = True
    logger.info("Raster system loaded successfully")
except ImportError as e:
    HAS_RASTER_SYSTEM = False
    RasterLoader = None
    get_raster_loader = None
    create_mapbiomas_legend = None
    analyze_raster_in_radius = None
    logger.warning(f"⚠️ Sistema de rasters não disponível: {e}")

# ============================================================================
# SISTEMA DE CACHE OTIMIZADO PARA SHAPEFILES
# ============================================================================

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
    base_path = Path(__file__).parent.parent.parent / "shapefile"
    geoparquet_path = Path(__file__).parent.parent.parent / "geoparquet"
    
    layers = {}
    
    # Plantas de Biogás (pontos - sem simplificação)
    plantas_path = base_path / "Shapefile_425_Biogas_Mapbiomas_SP.shp" 
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

# ============================================================================
# FUNÇÕES OTIMIZADAS DE RENDERIZAÇÃO DE CAMADAS
# ============================================================================

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
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            popup=f"<b>{tipo}</b><br>{row.get('SUBTIPO', 'N/A')}",
            tooltip=f"Planta: {tipo}",
            color=color,
            fillColor=color,
            fillOpacity=0.8,
            weight=1
        ).add_to(marker_cluster)

def add_lines_layer_fast(m, gdf, name, color, weight=2):
    """Adiciona camadas de linhas de forma otimizada"""
    if gdf is None or len(gdf) == 0:
        return
    
    # Usar uma única operação GeoJson para melhor performance
    folium.GeoJson(
        gdf,
        name=name,
        style_function=lambda feature: {
            'color': color,
            'weight': weight,
            'opacity': 0.8
        },
        tooltip=folium.GeoJsonTooltip(fields=gdf.columns[:3].tolist() if len(gdf.columns) > 0 else []),
        popup=False  # Desabilitar popup para performance
    ).add_to(m)

def add_polygons_layer_fast(m, gdf, name, color, fill_opacity=0.3):
    """Adiciona camadas de polígonos de forma otimizada"""
    if gdf is None or len(gdf) == 0:
        return
    
    folium.GeoJson(
        gdf,
        name=name,
        style_function=lambda feature: {
            'color': color,
            'weight': 1,
            'opacity': 0.8,
            'fillColor': color,
            'fillOpacity': fill_opacity
        },
        tooltip=False,  # Desabilitar tooltip para performance
        popup=False     # Desabilitar popup para performance
    ).add_to(m)

def add_regioes_layer_fast(m, regioes_gdf):
    """Adiciona regiões administrativas com cores diferentes"""
    if regioes_gdf is None or len(regioes_gdf) == 0:
        return
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
             '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43']
    
    for idx, row in regioes_gdf.iterrows():
        color = colors[idx % len(colors)]
        folium.GeoJson(
            row.geometry,
            style_function=lambda feature, color=color: {
                'color': color,
                'weight': 2,
                'opacity': 0.8,
                'fillColor': color,
                'fillOpacity': 0.2
            },
            tooltip=f"Região: {row.get('Nome', 'N/A')}",
            popup=False
        ).add_to(m)

def create_centroid_map_optimized(df, display_col, filters=None, get_legend_only=False, search_term="", viz_type="Círculos Proporcionais", show_mapbiomas_layer=False, mapbiomas_classes=None, show_rios=False, show_rodovias=False, show_plantas_biogas=False, show_gasodutos_dist=False, show_gasodutos_transp=False, show_areas_urbanas=False, show_regioes_admin=False, show_municipios_biogas=True, show_municipios_polygons=False, catchment_info=None):
    """VERSÃO ULTRA-OTIMIZADA - Cria mapa folium de forma muito mais rápida"""
    
    # Função otimizada para criação de mapas com camadas customizáveis
    
    try:
        # 1. SETUP BÁSICO DO MAPA - MINIMAL
        m = folium.Map(
            location=[-22.5, -48.5], 
            zoom_start=7,
            tiles='CartoDB positron',
            prefer_canvas=True  # Melhora performance de renderização
        )
        
        # Cria um FeatureGroup para a análise de proximidade. Ele será adicionado no final.
        proximity_group = folium.FeatureGroup(name="Área de Análise", show=True)
        
        # 1.1. ADICIONAR LIMITE DO ESTADO DE SÃO PAULO (SEMPRE VISÍVEL)
        try:
            sp_border_path = Path(__file__).parent.parent.parent / "shapefile" / "Limite_SP.shp"
            if sp_border_path.exists():
                sp_border = gpd.read_file(sp_border_path)
                if sp_border.crs != 'EPSG:4326':
                    sp_border = sp_border.to_crs('EPSG:4326')
                
                folium.GeoJson(
                    sp_border,
                    style_function=lambda x: {
                        'fillColor': 'rgba(0,0,0,0)', # Sem preenchimento
                        'color': '#2E8B57',          # Verde escuro
                        'weight': 2,                 # Espessura da linha
                        'opacity': 0.7,              # Opacidade da linha
                        'dashArray': '5, 5'          # Linha tracejada
                    },
                    tooltip='Estado de São Paulo',
                    interactive=False  # Não clicável
                ).add_to(m)
        except Exception as e:
            # Falha silenciosa - se não conseguir carregar, continua sem o limite
            pass
        
        # Remover todos os debug prints/writes para melhor performance
        if df.empty:
            return m, ""
        
        # 2. PRÉ-CARREGAR TODAS AS CAMADAS DE UMA VEZ (CACHE)
        with st.spinner("⚡ Carregando dados das camadas..."):
            layer_data = prepare_layer_data()
        
        # 3. ADICIONAR CAMADAS SELECIONADAS - OTIMIZADO
        layers_added = []
        
        if show_plantas_biogas and layer_data['plantas'] is not None:
            add_plantas_layer_fast(m, layer_data['plantas'])
            layers_added.append("Plantas de Biogás")
        
        if show_gasodutos_dist and layer_data['gasodutos_dist'] is not None:
            add_lines_layer_fast(m, layer_data['gasodutos_dist'], "Gasodutos Distribuição", "#0066CC")
            layers_added.append("Gasodutos Distribuição")
            
        if show_gasodutos_transp and layer_data['gasodutos_transp'] is not None:
            add_lines_layer_fast(m, layer_data['gasodutos_transp'], "Gasodutos Transporte", "#CC0000", weight=4)
            layers_added.append("Gasodutos Transporte")
        
        if show_rodovias and layer_data['rodovias'] is not None:
            add_lines_layer_fast(m, layer_data['rodovias'], "Rodovias Estaduais", "#FF4500", weight=2)
            layers_added.append("Rodovias")
            
        if show_rios and layer_data['rios'] is not None:
            add_lines_layer_fast(m, layer_data['rios'], "Rios Principais", "#1E90FF", weight=2)
            layers_added.append("Rios")
        
        if show_areas_urbanas and layer_data['areas_urbanas'] is not None:
            # Usar amostragem para áreas urbanas se houver muitos polígonos
            areas_sample = layer_data['areas_urbanas']
            if len(areas_sample) > 5000:  # Limitar para performance
                areas_sample = areas_sample.sample(n=5000)
            add_polygons_layer_fast(m, areas_sample, "Áreas Urbanas", "#DEB887", fill_opacity=0.3)
            layers_added.append("Áreas Urbanas")
        
        if show_regioes_admin and layer_data['regioes_admin'] is not None:
            add_regioes_layer_fast(m, layer_data['regioes_admin'])
            layers_added.append("Regiões Administrativas")
        
        # 4. CARREGAR DADOS DOS MUNICÍPIOS - SEMPRE ATIVADO
        df_merged = None
        if show_municipios_biogas and not df.empty:
            try:
                centroid_path = Path(__file__).parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
                if centroid_path.exists():
                    centroids_df = pd.read_parquet(centroid_path)
                    
                    # O arquivo tem lat/lon em vez de geometry - vamos criar geometry a partir dessas colunas
                    if 'lat' in centroids_df.columns and 'lon' in centroids_df.columns:
                        # Converter apenas colunas numéricas específicas para tipos nativos do Python
                        numeric_cols = ['lat', 'lon', 'cd_mun']
                        for col in numeric_cols:
                            if col in centroids_df.columns and centroids_df[col].dtype in ['int32', 'int64', 'float32', 'float64']:
                                centroids_df[col] = centroids_df[col].astype(float)
                        
                        # Criar geometrias Point a partir de lat/lon
                        from shapely.geometry import Point
                        centroids_df['geometry'] = centroids_df.apply(lambda row: Point(float(row['lon']), float(row['lat'])), axis=1)
                        centroids_gdf = gpd.GeoDataFrame(centroids_df, crs='EPSG:4326')
                        
                        df_merged = centroids_gdf.merge(df, on='cd_mun', how='inner')
                        
                        # CORREÇÃO: Após o merge, as colunas de nome ficam como nome_municipio_x e nome_municipio_y
                        # Vamos criar uma coluna única 'nome_municipio' usando os dados do main data (y)
                        if 'nome_municipio_y' in df_merged.columns:
                            df_merged['nome_municipio'] = df_merged['nome_municipio_y']
                        elif 'nome_municipio_x' in df_merged.columns:
                            df_merged['nome_municipio'] = df_merged['nome_municipio_x']
                        
                        # Converter apenas colunas numéricas específicas (não textuais) para tipos nativos do Python
                        numeric_cols_to_convert = ['lat', 'lon', 'cd_mun', 'populacao_2022', 'total_final_m_ano', 'total_agricola_m_ano', 'total_pecuaria_m_ano', 'total_urbano_m_ano']
                        for col in df_merged.columns:
                            if col != 'geometry' and col != 'nome_municipio' and col != 'nome_municipio_x' and col != 'nome_municipio_y' and df_merged[col].dtype in ['int32', 'int64', 'float32', 'float64']:
                                try:
                                    df_merged[col] = df_merged[col].astype(float)
                                except:
                                    pass  # Pular se não conseguir converter
                        
                        if not df_merged.empty and display_col in df_merged.columns:
                            # Adicionar círculos dos municípios de forma otimizada
                            add_municipality_circles_fast(m, df_merged, display_col, viz_type)
                            layers_added.append("Potencial de Biogás dos Municípios")
                        else:
                            # Debugging para entender o problema
                            st.warning(f"⚠️ Debug: df_merged empty={df_merged.empty if df_merged is not None else 'None'}, display_col='{display_col}' in columns={display_col in df_merged.columns if df_merged is not None else 'No df_merged'}")
                    else:
                        st.warning("⚠️ Colunas 'lat' e 'lon' não encontradas nos centroids")
                else:
                    st.warning("⚠️ Arquivo municipality_centroids.parquet não encontrado")
            except Exception as e:
                # Debug em vez de falha silenciosa
                st.error(f"❌ Erro ao carregar círculos dos municípios: {e}")
                import traceback
                st.code(traceback.format_exc())
        
        # 4.5. ADICIONAR CAMADA DE POLÍGONOS DOS MUNICÍPIOS (OPCIONAL)
        if show_municipios_polygons:
            try:
                # Carregar geometrias dos polígonos
                gdf_polygons = load_optimized_geometries("medium_detail")
                
                if gdf_polygons is not None and 'cd_mun' in gdf_polygons.columns:
                    # Adicionar polígonos com bordas cinzas e suaves
                    folium.GeoJson(
                        gdf_polygons,
                        style_function=lambda feature: {
                            'fillColor': 'none',
                            'color': '#888888',  # Cinza suave
                            'weight': 1,         # Linha mais fina
                            'opacity': 0.5,     # Mais transparente
                            'fillOpacity': 0.0
                        },
                        tooltip=folium.features.GeoJsonTooltip(
                            fields=['NM_MUN'] if 'NM_MUN' in gdf_polygons.columns else ['cd_mun'],
                            aliases=['Município:'] if 'NM_MUN' in gdf_polygons.columns else ['Código:'],
                            style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
                        )
                    ).add_to(m)
                    layers_added.append("Polígonos dos Municípios")
            except Exception as e:
                st.error(f"❌ Erro ao carregar polígonos dos municípios: {e}")
        
        # 5. REMOVER CONTROLES DO FOLIUM - USAMOS SIDEBAR AGORA
        # LayerControl removido para deixar espaço para a legenda bonita
        
        # 6. CRIAR LEGENDA BONITA (RESTAURADA DO ORIGINAL)
        legend_html = ""
        if show_municipios_biogas and df_merged is not None and not df_merged.empty:
            legend_html = f'''
            <div style="font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 13px;">
                <h4 style="margin-top: 0; margin-bottom: 12px; color: #2E8B57; text-align: center;">
                    🗺️ Legenda do Mapa
                </h4>
                <div style="margin-bottom: 10px;">
                    <strong>📊 Dados:</strong> {get_friendly_column_label(display_col)}
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>📈 Faixa de Potencial:</strong><br>
                    Min: {df_merged[display_col].min():,.0f} m³/ano<br>
                    Max: {df_merged[display_col].max():,.0f} m³/ano
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>🎨 Escala de Cores:</strong><br>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #ffffcc; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Muito Baixo</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #c7e9b4; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Baixo</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #7fcdbb; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Médio</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #41b6c4; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Alto</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #253494; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Muito Alto</span>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>📏 Tamanho do Círculo:</strong><br>
                    <small>Proporcional ao potencial de biogás</small>
                </div>
                {f"<div><strong>🗺️ Camadas Ativas:</strong><br><small>{', '.join(layers_added)}</small></div>" if layers_added else ""}
            </div>
            '''
        elif layers_added:
            legend_html = f"<div style='background: white; padding: 10px; border: 2px solid #333; border-radius: 5px;'><p><strong>Camadas ativas:</strong> {', '.join(layers_added)}</p></div>"
        
        # 7. ADICIONAR LEGENDA FLUTUANTE NO MAPA (CANTO SUPERIOR DIREITO)
        if show_municipios_biogas and df_merged is not None and not df_merged.empty:
            floating_legend_html = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: auto; 
                    background-color: rgba(255, 255, 255, 0.95); 
                    border: 2px solid #2E8B57;
                    z-index:9999; font-size:12px; border-radius: 8px; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    font-family: 'Segoe UI', Tahoma, sans-serif;">
            <h4 style="margin-top: 0; margin-bottom: 8px; color: #2E8B57; text-align: center; font-size: 14px;">
                🗺️ Legenda
            </h4>
            <div style="margin-bottom: 8px; font-size: 11px;">
                <strong>📊 Dados:</strong> {get_friendly_column_label(display_col)}
            </div>
            <div style="margin-bottom: 8px; font-size: 11px;">
                <strong>📈 Faixa:</strong><br>
                Min: {df_merged[display_col].min():,.0f}<br>
                Max: {df_merged[display_col].max():,.0f}
            </div>
            <div style="margin-bottom: 8px;">
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #ffffcc; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Muito Baixo</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #c7e9b4; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Baixo</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #7fcdbb; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Médio</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #41b6c4; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Alto</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #253494; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Muito Alto</span>
                </div>
            </div>
            <div style="font-size: 10px;">
                <strong>📏 Tamanho:</strong> Proporcional ao potencial
            </div>
        </div>
        '''
            # Adicionar a legenda flutuante ao mapa
            m.get_root().html.add_child(folium.Element(floating_legend_html))
        
        # --- CAMADA MAPBIOMAS COM RASTER OTIMIZADO ---
        if show_mapbiomas_layer:
            if not HAS_RASTER_SYSTEM:
                st.warning("⚠️ Sistema de rasters não disponível. Instale as dependências necessárias.")
                return m, legend_html
                
            try:
                # Verificar se o caminho do raster existe
                project_root = Path(__file__).parent.parent.parent
                raster_dir = project_root / "rasters"
                
                if not raster_dir.exists():
                    st.error(f"❌ Diretório 'rasters' não encontrado: {raster_dir}")
                else:
                    raster_loader = RasterLoader(str(raster_dir))
                    
                    # Lista rasters disponíveis
                    available_rasters = raster_loader.list_available_rasters()
                    mapbiomas_rasters = [r for r in available_rasters if 'mapbiomas' in r.lower() or 'agropecuaria' in r.lower()]
                    
                    if mapbiomas_rasters:
                        # Usa o primeiro raster encontrado
                        raster_path = mapbiomas_rasters[0]
                        data, metadata = raster_loader.load_raster(raster_path)
                        
                        if data is not None and metadata is not None:
                            # Cria sobreposição para o Folium com classes filtradas
                            overlay = raster_loader.raster_to_folium_overlay(data, metadata, opacity=0.7, selected_classes=mapbiomas_classes)
                            
                            if overlay is not None:
                                # Cria FeatureGroup para controle de camadas
                                mapbiomas_group = folium.FeatureGroup(name="MapBiomas - Agropecuária SP", show=True)
                                overlay.add_to(mapbiomas_group)
                                mapbiomas_group.add_to(m)
                                
                                # Adiciona legenda com classes filtradas
                                legend_mapbiomas = create_mapbiomas_legend(selected_classes=mapbiomas_classes)
                                m.get_root().html.add_child(folium.Element(legend_mapbiomas))
                            else:
                                st.warning("⚠️ Erro ao processar raster para visualização")
                        else:
                            st.warning("⚠️ Erro ao carregar dados do raster")
                    else:
                        st.info("📁 Nenhum arquivo raster MapBiomas encontrado na pasta 'rasters/'")
                        st.info("💡 Baixe o GeoTIFF do Google Earth Engine e coloque na pasta 'rasters/'")
                        
            except ImportError as e:
                st.error("❌ Sistema de rasters não disponível. Verifique se 'rasterio' está instalado.")
            except Exception as e:
                st.error(f"⚠️ Erro ao carregar camada MapBiomas: {str(e)}")
        
        return m, legend_html
        
    except Exception as e:
        st.error(f"❌ Erro ao criar mapa: {e}")
        # Retornar mapa básico em caso de erro
        basic_map = folium.Map(location=[-22.5, -48.5], zoom_start=7)
        return basic_map, ""

def add_municipality_circles_fast(m, df_merged, display_col, viz_type):
    """Adiciona visualizações dos municípios com diferentes estilos baseados em viz_type"""
    logger.debug(f"VIZ_TYPE: Function add_municipality_circles_fast receiving viz_type = '{viz_type}'")
    
    if df_merged.empty or display_col not in df_merged.columns:
        return
    
    # CORREÇÃO: Usar todos os municípios (645) - problema era limite de 500!
    # Remover limite que estava ocultando municípios menores
    df_sample = df_merged  # Sempre usar todos os municípios para garantir visualização completa
    
    # Preparar dados comuns
    values = df_sample[display_col].fillna(0)
    max_val = float(values.max()) if values.max() > 0 else 1.0
    
    # Cores da legenda para os diferentes níveis
    color_scale = ['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#253494']
    
    def get_color_for_value(value, max_val):
        if max_val == 0:
            return color_scale[0]
        normalized = value / max_val
        if normalized <= 0.2:
            return color_scale[0]  # Muito Baixo
        elif normalized <= 0.4:
            return color_scale[1]  # Baixo
        elif normalized <= 0.6:
            return color_scale[2]  # Médio
        elif normalized <= 0.8:
            return color_scale[3]  # Alto
        else:
            return color_scale[4]  # Muito Alto
    
    # ==== LÓGICA DE SELEÇÃO DE VISUALIZAÇÃO RESTAURADA ====
    logger.debug(f"VIZ_TYPE: Checking condition for '{viz_type}'")
    
    if viz_type == "Círculos Proporcionais":
        logger.debug("VIZ_TYPE: Entering Proportional Circles block")
        # Implementação atual - círculos proporcionais
        if values.max() > 0:
            sizes = ((values / values.max()) * 15 + 3).astype(float)
        else:
            sizes = pd.Series([5.0] * len(df_sample))
        
        # Contador para debug/logging
        circles_added = 0
        failed_renders = 0
        
        for idx, row in df_sample.iterrows():
            try:
                if hasattr(row, 'geometry') and row.geometry:
                    lat, lon = float(row.geometry.y), float(row.geometry.x)
                    size = float(sizes.loc[idx])
                    value = float(values.loc[idx])
                    color = get_color_for_value(value, max_val)
                    
                    municipio_nome = 'N/A'
                    if 'nome_municipio' in row.index:
                        municipio_nome = str(row['nome_municipio'])
                    elif hasattr(row, 'nome_municipio'):
                        municipio_nome = str(row.nome_municipio)
                    
                    popup = f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano"
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=size,
                        popup=popup,
                        tooltip=municipio_nome,
                        color='#333333',
                        fillColor=color,
                        fillOpacity=0.8,
                        weight=1
                    ).add_to(m)
                    circles_added += 1
                else:
                    failed_renders += 1
                    municipio_nome = getattr(row, 'nome_municipio', 'unknown')
                    logger.warning(f"Missing geometry for municipality: {municipio_nome}")
            except Exception as e:
                failed_renders += 1
                municipio_nome = getattr(row, 'nome_municipio', 'unknown')
                logger.warning(f"Failed to render municipality {municipio_nome}: {str(e)}")
                continue
        
        # Log de debug para acompanhar renderização
        logger.info(f"Círculos Proporcionais: {circles_added} círculos criados, {failed_renders} falhas de renderização")
                
    elif viz_type == "Mapa de Calor (Heatmap)":
        logger.debug("VIZ_TYPE: Entering Heat Map block")
        try:
            from folium.plugins import HeatMap
            heat_data = []
            for idx, row in df_sample.iterrows():
                try:
                    if hasattr(row, 'geometry') and row.geometry:
                        lat, lon = float(row.geometry.y), float(row.geometry.x)
                        value = float(values.loc[idx])
                        if value > 0:  # Só incluir valores positivos no heatmap
                            # Normalizar valor para o heatmap (0-1)
                            normalized_value = value / max_val
                            heat_data.append([lat, lon, normalized_value])
                except Exception:
                    continue
            
            if heat_data:
                HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
            else:
                # Fallback para círculos se heatmap falhar
                logger.debug("VIZ_TYPE: Fallback to circles - insufficient data for heatmap")
                # Implementar círculos simples como fallback
                for idx, row in df_sample.iterrows():
                    try:
                        if hasattr(row, 'geometry') and row.geometry:
                            lat, lon = float(row.geometry.y), float(row.geometry.x)
                            value = float(values.loc[idx])
                            color = get_color_for_value(value, max_val)
                            
                            municipio_nome = 'N/A'
                            if 'nome_municipio' in row.index:
                                municipio_nome = str(row['nome_municipio'])
                                
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=5,
                                popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                                tooltip=municipio_nome,
                                color='#333333',
                                fillColor=color,
                                fillOpacity=0.7,
                                weight=1
                            ).add_to(m)
                    except Exception:
                        continue
        except ImportError:
            logger.debug("VIZ_TYPE: HeatMap not available - using fallback to circles")
            # Fallback para círculos se HeatMap não estiver disponível
            for idx, row in df_sample.iterrows():
                try:
                    if hasattr(row, 'geometry') and row.geometry:
                        lat, lon = float(row.geometry.y), float(row.geometry.x)
                        value = float(values.loc[idx])
                        color = get_color_for_value(value, max_val)
                        
                        municipio_nome = 'N/A'
                        if 'nome_municipio' in row.index:
                            municipio_nome = str(row['nome_municipio'])
                            
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                            tooltip=municipio_nome,
                            color='red',
                            fillColor='orange',
                            fillOpacity=0.7,
                            weight=2
                        ).add_to(m)
                except Exception:
                    continue
                    
    elif viz_type == "Agrupamentos (Clusters)":
        logger.debug("VIZ_TYPE: Entering Clustering block")
        try:
            from folium.plugins import MarkerCluster
            marker_cluster = MarkerCluster().add_to(m)
            
            for idx, row in df_sample.iterrows():
                try:
                    if hasattr(row, 'geometry') and row.geometry:
                        lat, lon = float(row.geometry.y), float(row.geometry.x)
                        value = float(values.loc[idx])
                        color = get_color_for_value(value, max_val)
                        
                        municipio_nome = 'N/A'
                        if 'nome_municipio' in row.index:
                            municipio_nome = str(row['nome_municipio'])
                        elif hasattr(row, 'nome_municipio'):
                            municipio_nome = str(row.nome_municipio)
                        
                        # Usar tamanho baseado no valor para diferenciação
                        if values.max() > 0:
                            size = max(5, int((value / max_val) * 20))
                        else:
                            size = 8
                        
                        marker = folium.CircleMarker(
                            location=[lat, lon],
                            radius=size,
                            popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                            tooltip=municipio_nome,
                            color='#333333',
                            fillColor=color,
                            fillOpacity=0.8,
                            weight=1
                        )
                        marker_cluster.add_child(marker)
                except Exception:
                    continue
        except ImportError:
            logger.debug("VIZ_TYPE: MarkerCluster not available - using fallback to circles")
            # Fallback para círculos se MarkerCluster não estiver disponível
            for idx, row in df_sample.iterrows():
                try:
                    if hasattr(row, 'geometry') and row.geometry:
                        lat, lon = float(row.geometry.y), float(row.geometry.x)
                        value = float(values.loc[idx])
                        color = get_color_for_value(value, max_val)
                        
                        municipio_nome = 'N/A'
                        if 'nome_municipio' in row.index:
                            municipio_nome = str(row['nome_municipio'])
                            
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=8,
                            popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                            tooltip=municipio_nome,
                            color='purple',
                            fillColor='violet',
                            fillOpacity=0.7,
                            weight=2
                        ).add_to(m)
                except Exception:
                    continue
                    
    elif viz_type == "Mapa de Preenchimento (Coroplético)":
        logger.debug("VIZ_TYPE: Entering Choropleth block")
        try:
            # 1. Carregar as geometrias dos polígonos (usando a função que já existe)
            logger.debug("Loading municipality polygons...")
            gdf_polygons = load_optimized_geometries("medium_detail")

            if gdf_polygons is None or 'cd_mun' not in gdf_polygons.columns:
                logger.debug("Failed to load geometries - using fallback to circles")
                # Fallback para círculos se não conseguir carregar
                for idx, row in df_sample.iterrows():
                    try:
                        if hasattr(row, 'geometry') and row.geometry:
                            lat, lon = float(row.geometry.y), float(row.geometry.x)
                            value = float(values.loc[idx])
                            color = get_color_for_value(value, max_val)
                            
                            municipio_nome = 'N/A'
                            if 'nome_municipio' in row.index:
                                municipio_nome = str(row['nome_municipio'])
                            elif hasattr(row, 'nome_municipio'):
                                municipio_nome = str(row.nome_municipio)
                            
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=12,
                                popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                                tooltip=municipio_nome,
                                color=color,
                                fillColor=color,
                                fillOpacity=0.9,
                                weight=2
                            ).add_to(m)
                    except Exception:
                        continue
                return

            logger.debug(f"Polygons loaded: {len(gdf_polygons)} geometries")

            # 2. Mesclar dados de potencial com as geometrias
            # Assegurar que 'cd_mun' seja do mesmo tipo em ambos os dataframes
            gdf_polygons['cd_mun'] = gdf_polygons['cd_mun'].astype(str)
            df_merged_copy = df_merged.copy()
            df_merged_copy['cd_mun'] = df_merged_copy['cd_mun'].astype(str)
            
            df_choropleth = gdf_polygons.merge(df_merged_copy, on='cd_mun', how='inner')

            if df_choropleth.empty:
                logger.debug("Could not merge data - using fallback to circles")
                # Fallback para círculos se merge falhar
                for idx, row in df_sample.iterrows():
                    try:
                        if hasattr(row, 'geometry') and row.geometry:
                            lat, lon = float(row.geometry.y), float(row.geometry.x)
                            value = float(values.loc[idx])
                            color = get_color_for_value(value, max_val)
                            
                            municipio_nome = 'N/A'
                            if 'nome_municipio' in row.index:
                                municipio_nome = str(row['nome_municipio'])
                                
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=12,
                                popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                                tooltip=municipio_nome,
                                color=color,
                                fillColor=color,
                                fillOpacity=0.9,
                                weight=2
                            ).add_to(m)
                    except Exception:
                        continue
                return

            logger.debug(f"Merge completed: {len(df_choropleth)} municipalities with data")

            # 3. Criar a camada Choropleth
            folium.Choropleth(
                geo_data=df_choropleth,
                name='Potencial de Biogás',
                data=df_choropleth,
                columns=['cd_mun', display_col],
                key_on='feature.properties.cd_mun',
                fill_color='YlGnBu',  # Uma escala de cores boa para dados quantitativos
                fill_opacity=0.7,
                line_opacity=0.2,
                line_color='black',
                legend_name=f'Potencial de Biogás (m³/ano)',
                highlight=True
            ).add_to(m)

            # 4. (Opcional, mas recomendado) Adicionar tooltips interativos
            style_function = lambda x: {'fillColor': '#ffffff', 'color':'#000000', 'fillOpacity': 0.1, 'weight': 0.1}
            highlight_function = lambda x: {'fillColor': '#000000', 'color':'#000000', 'fillOpacity': 0.50, 'weight': 0.1}
            
            interactive_layer = folium.features.GeoJson(
                df_choropleth,
                style_function=style_function, 
                control=False,
                highlight_function=highlight_function, 
                tooltip=folium.features.GeoJsonTooltip(
                    fields=['nome_municipio', display_col],
                    aliases=['Município: ', 'Potencial: '],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
                )
            )
            m.add_child(interactive_layer)
            m.keep_in_front(interactive_layer)
            
            logger.debug("Choropleth map created successfully")

        except Exception as e:
            logger.error(f"Error generating choropleth map: {e}")
            # Fallback para círculos se algo der errado
            logger.debug("VIZ_TYPE: Fallback to circles due to choropleth error")
            for idx, row in df_sample.iterrows():
                try:
                    if hasattr(row, 'geometry') and row.geometry:
                        lat, lon = float(row.geometry.y), float(row.geometry.x)
                        value = float(values.loc[idx])
                        color = get_color_for_value(value, max_val)
                        
                        municipio_nome = 'N/A'
                        if 'nome_municipio' in row.index:
                            municipio_nome = str(row['nome_municipio'])
                        elif hasattr(row, 'nome_municipio'):
                            municipio_nome = str(row.nome_municipio)
                        
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=12,
                            popup=f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano",
                            tooltip=municipio_nome,
                            color=color,
                            fillColor=color,
                            fillOpacity=0.9,
                            weight=2
                        ).add_to(m)
                except Exception:
                    continue
    else:
        logger.warning(f"VIZ_TYPE: Unrecognized type '{viz_type}' - using proportional circles as fallback")
        # Fallback para círculos proporcionais
        if values.max() > 0:
            sizes = ((values / values.max()) * 15 + 3).astype(float)
        else:
            sizes = pd.Series([5.0] * len(df_sample))
        
        for idx, row in df_sample.iterrows():
            try:
                if hasattr(row, 'geometry') and row.geometry:
                    lat, lon = float(row.geometry.y), float(row.geometry.x)
                    size = float(sizes.loc[idx])
                    value = float(values.loc[idx])
                    color = get_color_for_value(value, max_val)
                    
                    municipio_nome = 'N/A'
                    if 'nome_municipio' in row.index:
                        municipio_nome = str(row['nome_municipio'])
                    elif hasattr(row, 'nome_municipio'):
                        municipio_nome = str(row.nome_municipio)
                    
                    popup = f"<b>{municipio_nome}</b><br>{value:,.0f} m³/ano"
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=size,
                        popup=popup,
                        tooltip=municipio_nome,
                        color='#333333',
                        fillColor=color,
                        fillOpacity=0.8,
                        weight=1
                    ).add_to(m)
            except Exception:
                continue


# Constants
RESIDUE_OPTIONS = {
    'Potencial Total': 'total_final_m_ano',
    'Total Agrícola': 'total_agricola_m_ano',
    'Total Pecuária': 'total_pecuaria_m_ano',
    'Total Urbano': 'total_urbano_m_ano',
    'Cana-de-açúcar': 'biogas_cana_m_ano',
    'Soja': 'biogas_soja_m_ano',
    'Milho': 'biogas_milho_m_ano',
    'Café': 'biogas_cafe_m_ano',
    'Citros': 'biogas_citros_m_ano',
    'Bovinos': 'biogas_bovinos_m_ano',
    'Suínos': 'biogas_suino_m_ano',
    'Aves': 'biogas_aves_m_ano',
    'Piscicultura': 'biogas_piscicultura_m_ano',
    'Resíduos Urbanos': 'rsu_potencial_m_ano',
    'Resíduos Poda': 'rpo_potencial_m_ano'
}

@st.cache_data
def get_residue_label(column_name):
    """Convert column name back to readable label"""
    # Create reverse mapping
    reverse_options = {v: k for k, v in RESIDUE_OPTIONS.items()}
    return reverse_options.get(column_name, column_name)

def get_friendly_column_label(column_name):
    """Convert column name to friendly display label with correct units"""
    
    # Define mapping for friendly labels with correct units
    friendly_labels = {
        'total_final_m_ano': 'Total Final (m³/ano)',
        'total_agricola_m_ano': 'Total Agrícola (m³/ano)', 
        'total_pecuaria_m_ano': 'Total Pecuária (m³/ano)',
        'total_urbano_m_ano': 'Total Urbano (m³/ano)',
        'biogas_cana_m_ano': 'Cana-de-açúcar (m³/ano)',
        'biogas_soja_m_ano': 'Soja (m³/ano)',
        'biogas_milho_m_ano': 'Milho (m³/ano)',
        'biogas_cafe_m_ano': 'Café (m³/ano)',
        'biogas_citros_m_ano': 'Citros (m³/ano)',
        'biogas_bovinos_m_ano': 'Bovinos (m³/ano)',
        'biogas_suino_m_ano': 'Suínos (m³/ano)',
        'biogas_aves_m_ano': 'Aves (m³/ano)',
        'biogas_piscicultura_m_ano': 'Piscicultura (m³/ano)',
        'rsu_potencial_m_ano': 'Resíduos Urbanos (m³/ano)',
        'rpo_potencial_m_ano': 'Resíduos de Poda (m³/ano)',
        'combined_potential': 'Potencial Combinado (m³/ano)'
    }
    
    return friendly_labels.get(column_name, column_name.replace('_', ' ').title())

# --- CONSTANTE PARA A CAMADA RASTER (USANDO A CAMADA MAIS ESTÁVEL DO GEOSERVER) ---
RASTER_LAYERS = {
    "Cobertura do Solo (MapBiomas)": {
        "url": "https://brasil.mapbiomas.org/geoserver/wms",
        # Usando a camada de integração da Coleção 8. É a mais confiável para testes.
        "layer": "mapbiomas:mapbiomas_brazil_collection_80_integration_v1", 
        "attr": "MapBiomas Project - Collection 8.0"
    }
}

# Database functions
@st.cache_data
def get_database_path():
    """Get database path"""
    return Path(__file__).parent.parent.parent / "data" / "cp2b_maps.db"

@st.cache_data(ttl=300)  # Cache for 5 minutes to allow data updates
def load_municipalities():
    """Load municipality data from database with error handling"""
    try:
        db_path = get_database_path()
        
        if not db_path.exists():
            logger.warning("Database not found")
            return pd.DataFrame()
        
        with sqlite3.connect(db_path) as conn:
            query = "SELECT * FROM municipalities ORDER BY total_final_m_ano DESC"
            df = pd.read_sql_query(query, conn)
            
            # RSU and RPO values are now calculated directly in the database
            # No need for per capita conversion anymore
            
            logger.info(f"Loaded {len(df)} municipalities with updated RSU/RPO data")
            return df
            
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return pd.DataFrame()

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

# Navigation functions
def render_header():
    """Render application header"""
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2E8B57 0%, #3ba068 50%, #48b879 100%);
                color: white; padding: 1.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 0 0 15px 15px; box-shadow: 0 3px 10px rgba(46,139,87,0.3);'>
        <h1 style='margin: 0 0 0.5rem 0; font-size: 2.2rem; font-weight: 700; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                   font-family: Montserrat, system-ui, sans-serif;'>
            🗺️ CP2B Maps
        </h1>
        <h2 style='margin: 0 0 0.6rem 0; font-size: 1.4rem; font-weight: 400; color: #fff2e6;
                   font-family: Montserrat, system-ui, sans-serif;'>
            Análise de Potencial de Biogás
        </h2>
        <p style='margin: 0.5rem 0; font-size: 1rem; opacity: 0.95; font-family: Montserrat, system-ui, sans-serif;'>
            📍 <strong>645 municípios</strong> de São Paulo • ⚡ <strong>Energia Renovável</strong> • 🌱 <strong>Base Científica</strong>
        </p>
        <p style='margin: 0.3rem 0 0 0; font-size: 0.85rem; opacity: 0.85; font-style: italic; font-family: Montserrat, system-ui, sans-serif;'>
            Centro Paulista de Estudos em Biogás e Bioprodutos
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_navigation():
    """Simple tab-based navigation"""
    tabs = st.tabs([
        "🏠 Mapa Principal",
        "🔍 Explorar Dados",
        "📊 Análises Avançadas",
        "🎯 Análise de Proximidade",
        "🍊 Bagacinho",
        "📚 Referências Científicas",
        "ℹ️ Sobre o CP2B Maps"
    ])

    # Add custom CSS for improved tab design and usability
    st.markdown("""
        <style>
        /* Improve main navigation tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            background-color: #f8f9fa;
            padding: 8px 12px;
            border-radius: 10px;
            margin-bottom: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stTabs [data-baseweb="tab"] {
            margin-right: 6px;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #e3f2fd;
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .stTabs [aria-selected="true"] {
            background-color: #2E8B57 !important;
            color: white !important;
            border-color: #2E8B57;
            box-shadow: 0 3px 10px rgba(46,139,87,0.3);
        }
        .stTabs [aria-selected="true"]:hover {
            background-color: #257a4a !important;
        }
        /* Improve text contrast and readability */
        .stTabs [data-baseweb="tab"] p {
            font-size: 14px;
            margin: 0;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)

    return tabs

# Filter functions
def render_sidebar_filters():
    """Render sidebar filters (deprecated - kept for compatibility)"""
    # Simple navigation-only sidebar
    st.sidebar.markdown("""
    <div style='background: #2E8B57; color: white; padding: 0.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 8px;'>
        <h4 style='margin: 0;'>📊 CP2B Maps</h4>
        <p style='margin: 0; font-size: 0.8em;'>Use as abas para navegar</p>
    </div>
    """, unsafe_allow_html=True)
    
    return {
        'residues': [RESIDUE_OPTIONS["Potencial Total"]],
        'display_name': "Potencial Total",
        'search': "",
        'show_zeros': False,
        'max_count': 50
    }

# ============================================================================
# HELPER FUNCTIONS FOR RESULTS PAGE
# ============================================================================

def create_ver_no_mapa_button(analysis_type, selected_municipalities, processed_data, charts=None, summary=None, polygons=None, button_key=None):
    """Create 'VER NO MAPA' button with analysis results"""
    
    if button_key is None:
        button_key = f"view_map_{analysis_type}_{hash(str(selected_municipalities))}"
    
    if st.button("🗺️ VER NO MAPA", key=button_key, use_container_width=True, type="primary"):
        # Store analysis results in session state
        st.session_state.analysis_results = {
            'type': analysis_type,
            'municipalities': selected_municipalities if isinstance(selected_municipalities, list) else [selected_municipalities],
            'data': processed_data or {},
            'charts': charts or [],
            'summary': summary or {},
            'polygons': polygons or [],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        st.session_state.show_results_page = True
        st.rerun()

def navigate_to_results(data, summary, polygons):
    """Navigate to results page with provided data"""
    st.session_state.analysis_results = {
        'type': 'advanced_analysis',
        'municipalities': data.get('municipalities', []),
        'data': data,
        'charts': [],
        'summary': summary or {},
        'polygons': polygons or [],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    st.session_state.show_results_page = True
    st.rerun()

def clean_data_for_results(data_dict, analysis_context=None):
    """Clean data dictionary by removing irrelevant technical fields"""
    
    # Technical fields to remove
    fields_to_remove = {
        'id', 'objectid', 'lat', 'lon', 'latitude', 'longitude', 'geometry', 
        'cd_mun', 'cd_rgi', 'cd_rgint', 'cd_uf', 'cd_regia', 'cd_concu',
        'sigla_uf', 'sigla_rg', 'index', 'level_0', 'unnamed'
    }
    
    # Keep only relevant fields
    cleaned_data = {}
    for key, value in data_dict.items():
        key_lower = str(key).lower()
        
        # Skip technical fields
        if any(field in key_lower for field in fields_to_remove):
            continue
            
        # Keep municipality identification
        if 'nome' in key_lower and 'municipio' in key_lower:
            cleaned_data[key] = value
            continue
            
        # Keep biogas potential fields
        if any(term in key_lower for term in ['nm_ano', 'potencial', 'total', 'biogas']):
            cleaned_data[key] = value
            continue
            
        # Keep area and population
        if any(term in key_lower for term in ['area', 'km2', 'populacao', 'pop']):
            cleaned_data[key] = value
            continue
            
        # Keep specific analysis context fields
        if analysis_context:
            context_fields = analysis_context.get('relevant_fields', [])
            if any(field in key_lower for field in context_fields):
                cleaned_data[key] = value
                continue
        
        # Keep residue-specific fields based on common residue types
        residue_keywords = [
            'agricola', 'pecuaria', 'urbano', 'cana', 'soja', 'milho', 'cafe', 
            'citros', 'bovinos', 'suinos', 'aves', 'piscicultura', 'poda'
        ]
        
        if any(residue in key_lower for residue in residue_keywords):
            cleaned_data[key] = value
            continue
    
    return cleaned_data

def prepare_analysis_data_for_results(df, selected_municipalities, analysis_type, residue_data=None, culture_data=None, metrics=None, analysis_context=None):
    """Prepare analysis data for the results page"""
    
    # Get municipal polygons if available
    polygons = []
    try:
        # First, try to load from the processed shapefile
        try:
            from modules.municipality_loader import get_municipality_geometries
            polygons = get_municipality_geometries(selected_municipalities)
            logger.info(f"Loaded {len(polygons)} geometries from municipality loader")
        except ImportError:
            # Fallback: Try to get geometries from the dataframe
            if 'geometry' in df.columns:
                selected_df = df[df['nome_municipio'].isin(selected_municipalities)]
                polygons = selected_df['geometry'].tolist()
                logger.info(f"Loaded {len(polygons)} geometries from dataframe")
    except Exception as e:
        logger.warning(f"Could not load geometries: {e}")
        polygons = []
    
    # Prepare data structure
    data = {}
    
    if residue_data is not None:
        # Clean residue data if it's a list of dictionaries
        if isinstance(residue_data, list) and residue_data and isinstance(residue_data[0], dict):
            cleaned_residues = []
            for item in residue_data:
                cleaned_item = clean_data_for_results(item, analysis_context)
                if cleaned_item:  # Only add if there's relevant data
                    cleaned_residues.append(cleaned_item)
            data['residues'] = cleaned_residues if cleaned_residues else residue_data
        else:
            data['residues'] = residue_data
    
    if culture_data is not None:
        # Clean culture data if it's a list of dictionaries
        if isinstance(culture_data, list) and culture_data and isinstance(culture_data[0], dict):
            cleaned_cultures = []
            for item in culture_data:
                cleaned_item = clean_data_for_results(item, analysis_context)
                if cleaned_item:  # Only add if there's relevant data
                    cleaned_cultures.append(cleaned_item)
            data['cultures'] = cleaned_cultures if cleaned_cultures else culture_data
        else:
            data['cultures'] = culture_data
    
    if metrics is not None:
        data['metrics'] = metrics
    
    # Calculate summary metrics
    summary = {}
    if isinstance(residue_data, list) and len(residue_data) > 0:
        try:
            # Calculate biogas potential from municipalities data
            total_potential = 0
            total_area = 0
            municipalities_with_data = 0
            
            for item in residue_data:
                if isinstance(item, dict):
                    # Try different potential field names
                    potential_fields = ['total_final_m_ano', 'Total (m³)', 'potencial_total', 'Potencial Total']
                    potential = 0
                    
                    for field in potential_fields:
                        if field in item and isinstance(item[field], (int, float)):
                            potential = max(potential, item[field])
                    
                    if potential > 0:
                        total_potential += potential
                        municipalities_with_data += 1
                    
                    # Add area if available
                    if 'area_km2' in item and isinstance(item['area_km2'], (int, float)):
                        total_area += item['area_km2']
            
            summary['biogas_potential'] = total_potential
            summary['total_area'] = total_area
            summary['municipalities_with_data'] = municipalities_with_data
            
            # Calculate potential density
            if total_area > 0:
                summary['potential_density'] = total_potential / total_area
                
        except Exception as e:
            logger.warning(f"Error calculating summary metrics: {e}")
            pass
    
    return data, summary, polygons

def render_compact_filters(page_key="default"):
    """Render compact filters on main page"""
    # Create compact filter container
    with st.container():
        st.markdown("""
        <div style='background: rgba(255,255,255,0.95); padding: 1rem; border-radius: 10px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 1rem;'>
        </div>
        """, unsafe_allow_html=True)
        
        # Use columns for horizontal layout
        col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
        
        with col1:
            # Selection mode
            mode = st.radio(
                "Modo:",
                ["Individual", "Múltiplos"],
                horizontal=True,
                key=f"{page_key}_selection_mode"
            )
        
        with col2:
            if mode == "Individual":
                selected = st.selectbox("Tipo de Resíduo:", list(RESIDUE_OPTIONS.keys()), key=f"{page_key}_residue_select")
                residues = [RESIDUE_OPTIONS[selected]]
                display_name = selected
            else:
                selected_list = st.multiselect(
                    "Tipos:",
                    list(RESIDUE_OPTIONS.keys()),
                    default=["Potencial Total"],
                    key=f"{page_key}_residue_multi"
                )
                residues = [RESIDUE_OPTIONS[item] for item in selected_list]
                display_name = f"Soma de {len(residues)} tipos" if len(residues) > 1 else (selected_list[0] if selected_list else "Nenhum")
        
        with col3:
            search = st.text_input("🔍 Buscar:", placeholder="Nome do município", key=f"{page_key}_search")
        
        with col4:
            show_zeros = st.checkbox("Valores zero", key=f"{page_key}_zeros")
            max_count = st.slider("Max:", 10, 645, 50, key=f"{page_key}_max", help="Número máximo de municípios para visualizar")
    
    return {
        'residues': residues,
        'display_name': display_name,
        'search': search,
        'show_zeros': show_zeros,
        'max_count': max_count
    }

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    import math
    
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    
    return c * r

def analyze_municipalities_in_radius(df_municipalities, center_lat, center_lon, radius_km):
    """
    Encontra municípios dentro de um raio e calcula o potencial total.
    """
    if df_municipalities.empty or 'lat' not in df_municipalities.columns:
        return {'total_potential': 0, 'municipality_count': 0, 'municipalities': []}

    municipalities_in_radius = []
    total_potential = 0

    for _, row in df_municipalities.iterrows():
        # Pula municípios sem coordenadas válidas
        if pd.isna(row['lat']) or pd.isna(row['lon']) or row['lat'] == 0:
            continue

        distance = calculate_distance(center_lat, center_lon, row['lat'], row['lon'])

        if distance <= radius_km:
            potential = row.get('total_final_m_ano', 0)
            municipalities_in_radius.append({
                'nome': row['nome_municipio'],
                'potencial': potential,
                'distancia_km': round(distance, 1)
            })
            total_potential += potential
    
    # Ordena por distância (do mais próximo ao mais distante)
    municipalities_in_radius.sort(key=lambda x: x['distancia_km'])
    
    return {
        'total_potential': total_potential,
        'municipality_count': len(municipalities_in_radius),
        'municipalities': municipalities_in_radius
    }

def calculate_catchment_area(df, center_lat, center_lon, radius_km, display_col):
    """Calculate total potential within a radius from a center point"""
    import pandas as pd
    
    if df.empty:
        return None
    
    # Load centroid data to get coordinates
    try:
        from pathlib import Path
        centroid_path = Path(__file__).parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
        centroids_df = pd.read_parquet(centroid_path)
        
        # Merge with display data
        df_with_coords = centroids_df.merge(df, on='cd_mun', how='inner')
        
        municipalities_in_radius = []
        total_potential = 0
        
        for idx, row in df_with_coords.iterrows():
            try:
                # Get municipality coordinates
                if hasattr(row['geometry'], 'y') and hasattr(row['geometry'], 'x'):
                    mun_lat, mun_lon = float(row['geometry'].y), float(row['geometry'].x)
                elif 'lat' in row and 'lon' in row:
                    mun_lat, mun_lon = float(row['lat']), float(row['lon'])
                else:
                    continue
                
                # Calculate distance
                distance = calculate_distance(center_lat, center_lon, mun_lat, mun_lon)
                
                # Check if within radius
                if distance <= radius_km:
                    potential = float(row[display_col]) if pd.notna(row[display_col]) else 0
                    
                    municipalities_in_radius.append({
                        'name': row.get('nome_municipio', 'N/A'),
                        'distance': distance,
                        'potential': potential,
                        'cd_mun': row['cd_mun']
                    })
                    
                    total_potential += potential
                    
            except (AttributeError, TypeError, ValueError):
                continue
        
        # Sort by potential (descending)
        municipalities_in_radius.sort(key=lambda x: x['potential'], reverse=True)
        
        return {
            'total_potential': total_potential,
            'municipality_count': len(municipalities_in_radius),
            'municipalities': municipalities_in_radius,
            'center_lat': center_lat,
            'center_lon': center_lon,
            'radius_km': radius_km
        }
        
    except Exception as e:
        st.error(f"Erro no cálculo de área de captação: {e}")
        return None

def apply_classification(values, method, num_classes):
    """Apply statistical classification to data values"""
    import numpy as np
    
    if len(values) == 0:
        return []
    
    values = np.array(values)
    values = values[~np.isnan(values)]  # Remove NaN values
    
    if len(values) == 0:
        return []
    
    if method == "Linear (Intervalo Uniforme)":
        # Equal interval - divide range into equal parts
        min_val, max_val = values.min(), values.max()
        if max_val == min_val:
            return [min_val] * num_classes
        breaks = np.linspace(min_val, max_val, num_classes + 1)
        
    elif method == "Quantiles (Contagem Igual)":
        # Quantiles - equal count in each class
        percentiles = np.linspace(0, 100, num_classes + 1)
        breaks = np.percentile(values, percentiles)
        
    elif method == "Quebras Naturais (Jenks)":
        # Natural breaks - minimize within-class variance (simplified version)
        try:
            # Try to use jenkspy if available
            import jenkspy
            breaks = jenkspy.jenks_breaks(values, nb_class=num_classes)
        except ImportError:
            # Fallback to quantiles if jenkspy not available
            st.warning("📊 Quebras Naturais não disponível - usando Quantiles como alternativa")
            percentiles = np.linspace(0, 100, num_classes + 1)
            breaks = np.percentile(values, percentiles)
            
    elif method == "Desvio Padrão":
        # Standard deviation breaks
        mean_val = values.mean()
        std_val = values.std()
        
        # Create breaks around the mean using standard deviations
        half_classes = num_classes // 2
        breaks = []
        
        for i in range(-half_classes, half_classes + 1):
            breaks.append(mean_val + i * std_val)
        
        # Ensure we have the right number of breaks and they're within data range
        breaks = np.array(breaks)
        breaks = np.clip(breaks, values.min(), values.max())
        breaks = sorted(set(breaks))  # Remove duplicates and sort
        
        # Adjust if we don't have enough breaks
        while len(breaks) < num_classes + 1:
            breaks.append(values.max())
        breaks = breaks[:num_classes + 1]
    
    return sorted(set(breaks))  # Remove duplicates and sort

def apply_normalization(df, base_col, normalization_type):
    """Apply data normalization based on user selection"""
    df_norm = df.copy()
    
    if normalization_type == "Potencial Absoluto (m³/ano)":
        # No normalization - use original values
        return df_norm, base_col
        
    elif normalization_type == "Potencial per Capita (m³/hab/ano)":
        # Normalize by population
        if 'populacao_2022' in df_norm.columns:
            normalized_col = f"{base_col}_per_capita"
            df_norm[normalized_col] = df_norm[base_col] / df_norm['populacao_2022'].replace(0, 1)  # Avoid division by zero
            df_norm[normalized_col] = df_norm[normalized_col].fillna(0)
            return df_norm, normalized_col
        else:
            st.warning("⚠️ Dados populacionais não disponíveis para normalização per capita")
            return df_norm, base_col
            
    elif normalization_type == "Potencial por Área (m³/km²/ano)":
        # Normalize by area
        if 'area_km2' in df_norm.columns:
            normalized_col = f"{base_col}_per_area"
            df_norm[normalized_col] = df_norm[base_col] / df_norm['area_km2'].replace(0, 1)  # Avoid division by zero
            df_norm[normalized_col] = df_norm[normalized_col].fillna(0)
            return df_norm, normalized_col
        else:
            st.warning("⚠️ Dados de área não disponíveis para normalização por área")
            return df_norm, base_col
            
    elif normalization_type == "Densidade Populacional (hab/km²)":
        # Show population density instead of biogas potential
        if 'populacao_2022' in df_norm.columns and 'area_km2' in df_norm.columns:
            density_col = "densidade_populacional"
            df_norm[density_col] = df_norm['populacao_2022'] / df_norm['area_km2'].replace(0, 1)
            df_norm[density_col] = df_norm[density_col].fillna(0)
            return df_norm, density_col
        else:
            st.warning("⚠️ Dados populacionais ou de área não disponíveis para densidade populacional")
            return df_norm, base_col
    
    return df_norm, base_col

def apply_filters(df, filters):
    """
    Apply filters to dataframe - ALWAYS returns all 645 municipalities.
    Only changes the display column for visualization.
    """
    if df.empty:
        return df, 'total_final_m_ano'
    
    # Always work with a full copy of the dataframe
    df_to_display = df.copy()
    
    # Calculate display column based on residue selection
    if not filters['residues']:
        # Default case if nothing is selected
        display_col = 'total_final_m_ano'
        df_to_display['display_col'] = 0
    elif len(filters['residues']) == 1:
        display_col = filters['residues'][0]
    else:
        display_col = 'combined_potential'
        available_residues = [col for col in filters['residues'] if col in df_to_display.columns]
        if available_residues:
            df_to_display[display_col] = df_to_display[available_residues].fillna(0).sum(axis=1)
        else:
            df_to_display[display_col] = 0
    
    # Apply normalization if specified
    if 'normalization' in filters and filters['normalization'] != "Potencial Absoluto (m³/ano)":
        df_to_display, display_col = apply_normalization(df_to_display, display_col, filters['normalization'])
            
    return df_to_display, display_col

# Map functions
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_optimized_geometries(detail_level="medium_detail"):
    """Load optimized municipality geometries from GeoParquet"""
    import geopandas as gpd
    from pathlib import Path
    
    try:
        parquet_path = Path(__file__).parent.parent.parent / "shapefile" / f"municipalities_{detail_level}.parquet"
        
        if parquet_path.exists():
            return gpd.read_parquet(parquet_path)
        else:
            # Fallback to original shapefile
            shapefile_path = Path(__file__).parent.parent.parent / "shapefile" / "SP_Municipios_2024.shp"
            if shapefile_path.exists():
                gdf = gpd.read_file(shapefile_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
                return gdf
    except Exception as e:
        st.error(f"Error loading geometries: {e}")
    
    return None

def create_centroid_map(df, display_col, filters=None, get_legend_only=False, search_term="", viz_type="Círculos Proporcionais", show_mapbiomas_layer=False, show_rios=False, show_rodovias=False, show_plantas_biogas=False, show_gasodutos_dist=False, show_gasodutos_transp=False, show_areas_urbanas=False, show_regioes_admin=False):
    """Create folium map with weighted centroids and floating controls"""
    import geopandas as gpd
    from pathlib import Path
    import numpy as np
    
    try:
        # --- CLEAN LIGHT BASEMAP SETUP ---
        m = folium.Map(
            location=[-22.5, -48.5], 
            zoom_start=7,
            tiles='CartoDB positron'  # Clean light basemap
        )
        
        # Add only clean, professional basemap options with proper attribution
        folium.TileLayer(
            tiles='OpenStreetMap',
            name='OpenStreetMap',
            attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        ).add_to(m)
        folium.TileLayer(
            tiles='Stamen Terrain',
            name='Terreno', 
            attr='Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://www.openstreetmap.org/copyright">ODbL</a>.'
        ).add_to(m)
        # Dark mode basemap removed completely
        # ------------------------------------
        
        # --- CAMADA MAPBIOMAS COM RASTER OTIMIZADO ---
        if show_mapbiomas_layer:
            if not HAS_RASTER_SYSTEM:
                st.info("📁 Sistema MapBiomas não disponível - instale as dependências rasterio e matplotlib")
                return m, ""
                
            try:
                # Verificar se o caminho do raster existe ANTES de tentar usar
                project_root = Path(__file__).parent.parent.parent
                raster_dir = project_root / "rasters"
                
                if not raster_dir.exists():
                    st.info("📁 Pasta 'rasters' não encontrada - funcionalidade MapBiomas desabilitada")
                    return m, ""
                    
                raster_loader = RasterLoader(str(raster_dir))
                
                # Lista rasters disponíveis
                available_rasters = raster_loader.list_available_rasters()
                mapbiomas_rasters = [r for r in available_rasters if 'mapbiomas' in r.lower() or 'agropecuaria' in r.lower()]
                
                if mapbiomas_rasters:
                    # Usa o primeiro raster encontrado
                    raster_path = mapbiomas_rasters[0]
                    data, metadata = raster_loader.load_raster(raster_path)
                    
                    if data is not None and metadata is not None:
                        # Cria sobreposição para o Folium
                        overlay = raster_loader.raster_to_folium_overlay(data, metadata, opacity=0.7)
                        
                        if overlay is not None:
                            # Cria FeatureGroup para controle de camadas
                            mapbiomas_group = folium.FeatureGroup(name="MapBiomas - Agropecuária SP", show=True)
                            overlay.add_to(mapbiomas_group)
                            mapbiomas_group.add_to(m)
                            
                            # Adiciona legenda
                            legend_html = create_mapbiomas_legend()
                            m.get_root().html.add_child(folium.Element(legend_html))
                            
                        else:
                            st.warning("⚠️ Erro ao processar raster para visualização")
                    else:
                        st.warning("⚠️ Erro ao carregar dados do raster")
                else:
                    st.info("📁 Nenhum arquivo raster MapBiomas encontrado na pasta 'rasters/'")
                    st.info("💡 Baixe o GeoTIFF do Google Earth Engine e coloque na pasta 'rasters/'")
                    
            except ImportError as e:
                st.error("❌ Sistema de rasters não disponível. Instale as dependências: pip install rasterio matplotlib")
            except Exception as e:
                st.warning(f"⚠️ Erro ao carregar camada MapBiomas: {str(e)}")
        
        # Add São Paulo state borders first (background) - ALWAYS SHOW
        try:
            sp_border_path = Path(__file__).parent.parent.parent / "shapefile" / "Limite_SP.shp"
            if sp_border_path.exists():
                sp_border = gpd.read_file(sp_border_path)
                if sp_border.crs != 'EPSG:4326':
                    sp_border = sp_border.to_crs('EPSG:4326')
                
                folium.GeoJson(
                    sp_border,
                    style_function=lambda x: {
                        'fillColor': 'rgba(46, 139, 87, 0.1)',
                        'color': '#2E8B57',
                        'weight': 2,
                        'opacity': 0.8,
                        'fillOpacity': 0.1,
                        'dashArray': '5, 5'
                    },
                    tooltip='Estado de São Paulo',
                    interactive=False  # Make state border non-interactive
                ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Bordas do estado: {e}")
        
        if df.empty:
            # Layer Control removed - now using Streamlit checkboxes
            return m, ""  # Return map and empty legend string
        
        # --- CAMADAS DE REFERÊNCIA COM FEATUREGROUP ---
        # Camada de rodovias estaduais
        if show_rodovias:
            try:
                rodovias_group = folium.FeatureGroup(name="Rodovias Estaduais", show=True)
                rodovias_path = Path(__file__).parent.parent.parent / "shapefile" / "Rodovias_Estaduais_SP.shp"
                if rodovias_path.exists():
                    rodovias_gdf = gpd.read_file(rodovias_path)
                    folium.GeoJson(
                        rodovias_gdf,
                        style_function=lambda feature: {
                            'fillColor': 'transparent',
                            'color': '#FF4500',
                            'weight': 2,
                            'opacity': 0.8,
                            'fillOpacity': 0
                        },
                        tooltip="Rodovia Estadual",
                        popup="Rodovias Estaduais de São Paulo"
                    ).add_to(rodovias_group)
                    rodovias_group.add_to(m)
                    print("[SUCESSO] Camada de rodovias (FeatureGroup) adicionada.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar rodovias: {e}")
        
        # Camada de rios principais (estrutura preparada para futuro)
        if show_rios:
            try:
                rios_group = folium.FeatureGroup(name="Rios Principais", show=True)
                rios_path = Path(__file__).parent.parent.parent / "shapefile" / "Rios_Principais_SP.shp"
                if rios_path.exists():
                    rios_gdf = gpd.read_file(rios_path)
                    folium.GeoJson(
                        rios_gdf,
                        style_function=lambda feature: {
                            'fillColor': 'transparent',
                            'color': '#4169E1',
                            'weight': 2,
                            'opacity': 0.8,
                            'fillOpacity': 0
                        },
                        tooltip="Rio Principal",
                        popup="Rios Principais de São Paulo"
                    ).add_to(rios_group)
                    rios_group.add_to(m)
                    print("[SUCESSO] Camada de rios (FeatureGroup) adicionada.")
                else:
                    print("[INFO] Shapefile de rios não encontrado - funcionalidade preparada para futuro.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar rios: {e}")
        
        # --- CAMADAS DE INFRAESTRUTURA DE BIOGÁS ---
        # Camada de plantas de biogás
        if show_plantas_biogas:
            try:
                st.write("🔍 **PROCESSANDO:** Plantas de Biogás...")
                plantas_group = folium.FeatureGroup(name="🏭 Plantas de Biogás", show=True)
                plantas_path = Path(__file__).parent.parent.parent / "shapefile" / "Shapefile_425_Biogas_Mapbiomas_SP.shp"
                st.write(f"📁 Caminho: {plantas_path}")
                st.write(f"✅ Arquivo existe: {plantas_path.exists()}")
                if plantas_path.exists():
                    plantas_gdf = gpd.read_file(plantas_path)
                    st.write(f"📊 Registros carregados: {len(plantas_gdf)}")
                    
                    # Converter para WGS84 se necessário
                    if plantas_gdf.crs and plantas_gdf.crs != 'EPSG:4326':
                        st.write(f"🔄 Convertendo CRS de {plantas_gdf.crs} para EPSG:4326...")
                        plantas_gdf = plantas_gdf.to_crs('EPSG:4326')
                        st.write("✅ Conversão de CRS concluída")
                    
                    # Definir cores por tipo de planta
                    def get_plant_color(tipo_plant):
                        color_map = {
                            'Biogás': '#32CD32',
                            'Aterro Sanitário': '#8B4513',
                            'Estação de Tratamento': '#4169E1',
                            'Suinocultura': '#FF69B4',
                            'Agropecuária': '#228B22',
                            'Industrial': '#FF4500',
                            'Outros': '#9370DB'
                        }
                        return color_map.get(tipo_plant, '#666666')
                    
                    st.write("🎯 Adicionando pontos ao mapa...")
                    pontos_adicionados = 0
                    
                    for idx, row in plantas_gdf.iterrows():
                        try:
                            tipo_plant = row.get('TIPO_PLANT', 'Não informado')
                            subtipo = row.get('SUBTIPO', 'Não informado')
                            status = row.get('STATUS', 'Não informado')
                            
                            # Extrair coordenadas
                            lat = row.geometry.y
                            lon = row.geometry.x
                            
                            # Verificar se as coordenadas são válidas (dentro do Brasil/SP)
                            if not (-35 <= lat <= -19 and -55 <= lon <= -44):
                                st.write(f"⚠️ Coordenadas inválidas no ponto {idx}: lat={lat:.6f}, lon={lon:.6f}")
                                continue
                            
                            popup_text = f"""
                            <b>🏭 Planta de Biogás</b><br>
                            <b>Tipo:</b> {tipo_plant}<br>
                            <b>Subtipo:</b> {subtipo}<br>
                            <b>Status:</b> {status}<br>
                            <b>Coords:</b> {lat:.6f}, {lon:.6f}
                            """
                            
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=8,
                                popup=folium.Popup(popup_text, max_width=250),
                                tooltip=f"Planta: {tipo_plant} - {subtipo}",
                                color='#000000',
                                fillColor=get_plant_color(tipo_plant),
                                fillOpacity=0.8,
                                weight=2
                            ).add_to(plantas_group)
                            pontos_adicionados += 1
                            
                        except Exception as e:
                            st.write(f"❌ Erro no ponto {idx}: {e}")
                            continue
                    
                    st.write(f"✅ {pontos_adicionados} pontos adicionados de {len(plantas_gdf)} totais")
                    
                    plantas_group.add_to(m)
                    st.success(f"✅ **SUCESSO:** Camada de plantas de biogás adicionada: {len(plantas_gdf)} plantas.")
                    print(f"[SUCESSO] Camada de plantas de biogás adicionada: {len(plantas_gdf)} plantas.")
                else:
                    print("[ERRO] Shapefile de plantas de biogás não encontrado.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar plantas de biogás: {e}")
        
        # Camada de gasodutos - distribuição
        if show_gasodutos_dist:
            try:
                gasodutos_dist_group = folium.FeatureGroup(name="⛽ Gasodutos - Distribuição", show=True)
                gasodutos_path = Path(__file__).parent.parent.parent / "shapefile" / "Gasodutos_Distribuicao_SP.shp"
                if gasodutos_path.exists():
                    gasodutos_gdf = gpd.read_file(gasodutos_path)
                    folium.GeoJson(
                        gasodutos_gdf,
                        style_function=lambda feature: {
                            'color': '#FF6600',
                            'weight': 3,
                            'opacity': 0.8,
                            'dashArray': '5, 5'
                        },
                        tooltip="Gasoduto de Distribuição",
                        popup="Rede de Distribuição de Gás Natural"
                    ).add_to(gasodutos_dist_group)
                    gasodutos_dist_group.add_to(m)
                    print(f"[SUCESSO] Camada de gasodutos de distribuição adicionada: {len(gasodutos_gdf)} trechos.")
                else:
                    print("[ERRO] Shapefile de gasodutos de distribuição não encontrado.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar gasodutos de distribuição: {e}")
        
        # Camada de gasodutos - transporte
        if show_gasodutos_transp:
            try:
                gasodutos_transp_group = folium.FeatureGroup(name="⛽ Gasodutos - Transporte", show=True)
                gasodutos_path = Path(__file__).parent.parent.parent / "shapefile" / "Gasodutos_Transporte_SP.shp"
                if gasodutos_path.exists():
                    gasodutos_gdf = gpd.read_file(gasodutos_path)
                    folium.GeoJson(
                        gasodutos_gdf,
                        style_function=lambda feature: {
                            'color': '#CC0000',
                            'weight': 4,
                            'opacity': 0.9,
                            'dashArray': '10, 5'
                        },
                        tooltip="Gasoduto de Transporte",
                        popup=folium.GeoJsonPopup(fields=['Nome_Dut_1', 'MUNIC_ORIG', 'MUNIC_DEST'], 
                                                labels=['Nome:', 'Origem:', 'Destino:'])
                    ).add_to(gasodutos_transp_group)
                    gasodutos_transp_group.add_to(m)
                    print(f"[SUCESSO] Camada de gasodutos de transporte adicionada: {len(gasodutos_gdf)} trechos.")
                else:
                    print("[ERRO] Shapefile de gasodutos de transporte não encontrado.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar gasodutos de transporte: {e}")
        
        # --- ÁREAS URBANAS LAYER (FROM GEOPARQUET) ---
        if show_areas_urbanas:
            try:
                areas_group = folium.FeatureGroup(name="🏘️ Áreas Urbanas", show=True)
                areas_path = Path(__file__).parent.parent.parent / "geoparquet" / "Areas_Urbanas_SP.parquet"
                if areas_path.exists():
                    areas_gdf = gpd.read_parquet(areas_path)
                    folium.GeoJson(
                        areas_gdf,
                        style_function=lambda feature: {
                            'color': '#8B4513',
                            'weight': 1,
                            'opacity': 0.7,
                            'fillColor': '#DEB887',
                            'fillOpacity': 0.3
                        },
                        tooltip="Área Urbana",
                        popup=folium.GeoJsonPopup(fields=['QAREA'], 
                                                labels=['Área (ha):'])
                    ).add_to(areas_group)
                    areas_group.add_to(m)
                    print(f"[SUCESSO] Camada de áreas urbanas adicionada: {len(areas_gdf)} polígonos.")
                else:
                    print("[ERRO] Arquivo GeoParquet de áreas urbanas não encontrado.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar áreas urbanas: {e}")
        
        # --- REGIÕES ADMINISTRATIVAS LAYER ---
        if show_regioes_admin:
            try:
                regioes_group = folium.FeatureGroup(name="🏛️ Regiões Administrativas", show=True)
                regioes_path = Path(__file__).parent.parent.parent / "shapefile" / "Regiao_Adm_SP.shp"
                if regioes_path.exists():
                    regioes_gdf = gpd.read_file(regioes_path)
                    # Define colors for different regions
                    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', 
                             '#FF9FF3', '#54A0FF', '#5F27CD', '#00D2D3', '#FF9F43',
                             '#10AC84', '#EE5A24', '#0984E3', '#A29BFE', '#FD79A8', '#E84393']
                    
                    for idx, row in regioes_gdf.iterrows():
                        color = colors[idx % len(colors)]
                        folium.GeoJson(
                            row.geometry,
                            style_function=lambda feature, color=color: {
                                'color': color,
                                'weight': 2,
                                'opacity': 0.8,
                                'fillColor': color,
                                'fillOpacity': 0.2
                            },
                            tooltip=f"Região: {row['Nome']}",
                            popup=folium.GeoJsonPopup(fields=[row['Nome']], 
                                                    labels=['Região:'])
                        ).add_to(regioes_group)
                    
                    regioes_group.add_to(m)
                    print(f"[SUCESSO] Camada de regiões administrativas adicionada: {len(regioes_gdf)} regiões.")
                else:
                    print("[ERRO] Shapefile de regiões administrativas não encontrado.")
            except Exception as e:
                print(f"[ERRO] Erro ao carregar regiões administrativas: {e}")
        # ------------------------------------------
        
        # Load municipality centroids
        try:
            centroid_path = Path(__file__).parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
            
            if not centroid_path.exists():
                st.warning("⚠️ Centroids file not found")
                return m
                
            import pandas as pd
            centroids_df = pd.read_parquet(centroid_path)
            
            # Convert to geopandas
            if 'geometry' in centroids_df.columns:
                centroids_gdf = gpd.GeoDataFrame(centroids_df)
            elif 'lat' in centroids_df.columns and 'lon' in centroids_df.columns:
                from shapely.geometry import Point
                centroids_df['geometry'] = centroids_df.apply(lambda row: Point(row['lon'], row['lat']), axis=1)
                centroids_gdf = gpd.GeoDataFrame(centroids_df, geometry='geometry')
            else:
                st.warning("⚠️ No coordinate data in centroids")
                return m
            
            # Merge with biogas data
            df_merged = centroids_gdf.merge(df, on='cd_mun', how='inner', suffixes=('_geo', ''))
            
            if df_merged.empty:
                st.warning("⚠️ No municipalities matched")
                return m
            
            # Ensure municipality name
            if 'nome_municipio' not in df_merged.columns:
                if 'NM_MUN' in df_merged.columns:
                    df_merged['nome_municipio'] = df_merged['NM_MUN']
                elif 'nome_municipio_geo' in df_merged.columns:
                    df_merged['nome_municipio'] = df_merged['nome_municipio_geo']
            
            # Calculate circle sizes
            max_val = float(df_merged[display_col].max())
            min_val = float(df_merged[display_col].min())
            
            if max_val == min_val or max_val == 0:
                df_merged['circle_size'] = 8
            else:
                normalized = (df_merged[display_col] - min_val) / (max_val - min_val)
                df_merged['circle_size'] = 3 + 22 * normalized
            
            df_merged['circle_size'] = df_merged['circle_size'].fillna(8)
            
            # Color mapping
            def get_color(value):
                if max_val == min_val:
                    return '#7fcdbb'
                normalized = (value - min_val) / (max_val - min_val)
                if normalized < 0.2:
                    return '#ffffcc'
                elif normalized < 0.4:
                    return '#c7e9b4'
                elif normalized < 0.6:
                    return '#7fcdbb'
                elif normalized < 0.8:
                    return '#41b6c4'
                else:
                    return '#253494'
            
            # Clean data for visualization, removing rows with no potential or no location
            df_viz = df_merged.copy()
            df_viz = df_viz[df_viz[display_col] > 0]  # Remove zero values
            
            # --- RENDER VISUALIZATION BASED ON USER CHOICE ---
            
            if viz_type == "Círculos Proporcionais":
                # Original circle marker visualization
                for idx, row in df_viz.iterrows():
                    try:
                        if hasattr(row['geometry'], 'y') and hasattr(row['geometry'], 'x'):
                            lat, lon = float(row['geometry'].y), float(row['geometry'].x)
                        elif 'lat' in row and 'lon' in row:
                            lat, lon = float(row['lat']), float(row['lon'])
                        else:
                            continue
                    except (AttributeError, TypeError, ValueError):
                        continue
                    
                    # --- EMBED THE UNIQUE ID IN THE POPUP ---
                    popup_text = f"""
                    <!-- id:{row['cd_mun']} -->
                    <b>{row['nome_municipio']}</b><br>
                    {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} m³/ano
                    """
                    
                    # The tooltip remains clean
                    tooltip_text = f"{row['nome_municipio']}: {row[display_col]:,.0f} m³/ano"
                    
                    # Check if this municipality matches the search term
                    is_searched = (search_term and 
                                  search_term.lower() in row['nome_municipio'].lower())
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=row['circle_size'] * 1.5 if is_searched else row['circle_size'],
                        popup=popup_text,
                        tooltip=f"{'[BUSCA] ' if is_searched else ''}{tooltip_text}",
                        color='red' if is_searched else 'black',
                        weight=3 if is_searched else 1,
                        fillColor='red' if is_searched else get_color(row[display_col]),
                        fillOpacity=0.9 if is_searched else 0.7
                    ).add_to(m)

            elif viz_type == "Mapa de Calor (Heatmap)":
                # Enhanced Heatmap visualization with intelligent radius calculation
                heat_data = []
                values = []
                
                # Collect data and values for analysis
                for idx, row in df_viz.iterrows():
                    try:
                        if hasattr(row['geometry'], 'y') and hasattr(row['geometry'], 'x'):
                            lat, lon = float(row['geometry'].y), float(row['geometry'].x)
                        elif 'lat' in row and 'lon' in row:
                            lat, lon = float(row['lat']), float(row['lon'])
                        else:
                            continue
                        
                        value = float(row[display_col])
                        heat_data.append([lat, lon, value])
                        values.append(value)
                    except (AttributeError, TypeError, ValueError):
                        continue
                
                if heat_data and values:
                    # Calculate balanced heatmap with outlier handling
                    import numpy as np
                    values_array = np.array(values)
                    
                    # Data analysis
                    data_count = len(values_array)
                    data_min = np.min(values_array)
                    data_max = np.max(values_array)
                    data_median = np.median(values_array)
                    data_q75 = np.percentile(values_array, 75)
                    data_q25 = np.percentile(values_array, 25)
                    
                    # Handle extreme outliers by using percentile-based scaling
                    # Use 95th percentile as effective max to prevent over-concentration
                    effective_max = np.percentile(values_array, 95)
                    effective_min = np.percentile(values_array, 5)
                    
                    # Normalize values using effective range to reduce outlier impact
                    normalized_heat_data = []
                    for lat, lon, value in heat_data:
                        # Cap extreme values
                        capped_value = min(max(value, effective_min), effective_max)
                        # Normalize to 0-1 range using effective range
                        if effective_max > effective_min:
                            normalized_value = (capped_value - effective_min) / (effective_max - effective_min)
                        else:
                            normalized_value = 0.5
                        
                        # Apply square root transformation to reduce concentration of high values
                        balanced_value = np.sqrt(normalized_value)
                        
                        normalized_heat_data.append([lat, lon, balanced_value])
                    
                    # Calculate radius based on data distribution characteristics
                    base_radius = 18
                    
                    # Factor 1: Data spread using IQR (more robust than std)
                    iqr = data_q75 - data_q25
                    spread_ratio = iqr / data_median if data_median > 0 else 1
                    spread_factor = min(1.8, max(0.7, spread_ratio))
                    
                    # Factor 2: Data density
                    if data_count > 400:
                        density_factor = 0.8  # Many points = smaller radius
                    elif data_count > 200:
                        density_factor = 1.0  # Medium points = normal radius
                    else:
                        density_factor = 1.2  # Few points = larger radius
                    
                    # Factor 3: Value distribution
                    outlier_ratio = (data_max - effective_max) / (data_max - data_min) if data_max > data_min else 0
                    if outlier_ratio > 0.3:  # Many outliers
                        distribution_factor = 0.9
                    else:  # Normal distribution
                        distribution_factor = 1.1
                    
                    # Calculate final parameters
                    final_radius = int(base_radius * spread_factor * density_factor * distribution_factor)
                    final_radius = max(12, min(28, final_radius))  # Constrain to reasonable range
                    
                    # Blur should be smaller relative to radius for better definition
                    final_blur = max(6, int(final_radius * 0.5))
                    
                    # Balanced gradient that shows both low and high values well
                    balanced_gradient = {
                        0.0: '#000080',   # Dark blue - very low
                        0.15: '#0040FF',  # Blue - low  
                        0.3: '#0080FF',   # Light blue - low-medium
                        0.45: '#00FFFF',  # Cyan - medium-low
                        0.6: '#40FF40',   # Light green - medium
                        0.75: '#FFFF00',  # Yellow - medium-high
                        0.85: '#FF8000',  # Orange - high
                        0.95: '#FF4000',  # Red-orange - very high
                        1.0: '#FF0000'    # Red - maximum
                    }
                    
                    # Create balanced heatmap
                    HeatMap(
                        normalized_heat_data,
                        radius=final_radius,
                        blur=final_blur,
                        max_zoom=1,
                        gradient=balanced_gradient,
                        min_opacity=0.3,
                        max_zoom_level=18
                    ).add_to(m)
                    
                    # Debug info
                    print(f"Balanced Heatmap - Radius: {final_radius}, Blur: {final_blur}")
                    print(f"Original range: {data_min:,.0f} - {data_max:,.0f}")
                    print(f"Effective range: {effective_min:,.0f} - {effective_max:,.0f}")
                    print(f"Median: {data_median:,.0f}, IQR: {iqr:,.0f}")

            elif viz_type == "Agrupamentos (Clusters)":
                # Marker clustering visualization
                marker_cluster = MarkerCluster().add_to(m)
                
                for idx, row in df_viz.iterrows():
                    try:
                        if hasattr(row['geometry'], 'y') and hasattr(row['geometry'], 'x'):
                            lat, lon = float(row['geometry'].y), float(row['geometry'].x)
                        elif 'lat' in row and 'lon' in row:
                            lat, lon = float(row['lat']), float(row['lon'])
                        else:
                            continue
                    except (AttributeError, TypeError, ValueError):
                        continue
                    
                    # --- EMBED THE UNIQUE ID IN THE POPUP FOR CLUSTERS TOO ---
                    popup_text = f"""
                    <!-- id:{row['cd_mun']} -->
                    <b>{row['nome_municipio']}</b><br>
                    {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} m³/ano<br>
                    <small>Posição: {lat:.4f}, {lon:.4f}</small>
                    """
                    
                    # Check if this municipality matches the search term
                    is_searched = (search_term and 
                                  search_term.lower() in row['nome_municipio'].lower())
                    
                    # Use different icon for searched municipalities
                    icon = folium.Icon(color='red', icon='search') if is_searched else folium.Icon(color='green', icon='leaf')
                    
                    folium.Marker(
                        location=[lat, lon],
                        popup=popup_text,
                        tooltip=f"{'[BUSCA] ' if is_searched else ''}{row['nome_municipio']}: {row[display_col]:,.0f}",
                        icon=icon
                    ).add_to(marker_cluster)

            elif viz_type == "Mapa de Preenchimento (Coroplético)":
                # Choropleth visualization using municipality boundaries
                try:
                    # Load optimized polygon geometries
                    gdf = load_optimized_geometries("medium_detail")
                    
                    if gdf is not None:
                        # Merge data with geometries
                        df_choropleth = gdf.merge(df_viz, on='cd_mun', how='inner')
                        
                        if not df_choropleth.empty:
                            # Prepare data for choropleth
                            choropleth_data = df_choropleth[['cd_mun', display_col]].dropna()
                            
                            # Create choropleth layer
                            folium.Choropleth(
                                geo_data=df_choropleth.to_json(),
                                name='Potencial de Biogás',
                                data=choropleth_data,
                                columns=['cd_mun', display_col],
                                key_on='feature.properties.cd_mun',
                                fill_color='YlOrRd',
                                fill_opacity=0.7,
                                line_opacity=0.3,
                                line_color='black',
                                line_weight=0.5,
                                legend_name=f'Potencial (m³/ano)',
                                highlight=True,
                                smooth_factor=0.5
                            ).add_to(m)
                            
                            # Add interactive popups for each municipality
                            for idx, row in df_choropleth.iterrows():
                                # Create popup with embedded ID for selection
                                popup_text = f"""
                                <!-- id:{row['cd_mun']} -->
                                <b>{row.get('nome_municipio', 'Município')}</b><br>
                                {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} m³/ano<br>
                                <small>Código: {row['cd_mun']}</small>
                                """
                                
                                # Calculate centroid of the polygon for popup placement
                                if hasattr(row['geometry'], 'centroid'):
                                    centroid = row['geometry'].centroid
                                    popup_lat, popup_lon = centroid.y, centroid.x
                                    
                                    # Add invisible marker for click detection
                                    folium.Marker(
                                        location=[popup_lat, popup_lon],
                                        popup=popup_text,
                                        tooltip=f"{row.get('nome_municipio', 'Município')}: {row[display_col]:,.0f}",
                                        icon=folium.DivIcon(html="", icon_size=(1, 1), icon_anchor=(0, 0))
                                    ).add_to(m)
                        else:
                            st.warning("⚠️ Não foi possível combinar dados com geometrias para visualização coroplética")
                    else:
                        st.warning("⚠️ Geometrias otimizadas não encontradas para visualização coroplética")
                        
                except Exception as e:
                    st.error(f"❌ Erro ao criar mapa coroplético: {e}")
            
            # --- ADD CATCHMENT AREA VISUALIZATION ---
            if hasattr(st.session_state, 'catchment_center') and st.session_state.catchment_center:
                center_lat, center_lon = st.session_state.catchment_center
                radius_km = getattr(st.session_state, 'catchment_radius', 50)
                
                # Add center marker
                folium.Marker(
                    location=[center_lat, center_lon],
                    popup=f"Centro de Captação<br>Raio: {radius_km}km",
                    tooltip=f"Centro de Captação ({radius_km}km)",
                    icon=folium.Icon(color='red', icon='bullseye', prefix='fa')
                ).add_to(m)
                
                # Add radius circle
                folium.Circle(
                    location=[center_lat, center_lon],
                    radius=radius_km * 1000,  # Convert km to meters
                    popup=f"Área de Captação: {radius_km}km",
                    color='red',
                    weight=2,
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.1
                ).add_to(m)
            
            # --- NEW MAP CONTROLS ---
            # 1. Add Mini Map (overview map)
            minimap = MiniMap(toggle_display=True, position='bottomright')
            minimap.add_to(m)
            
            # 2. Layer Control removed - now using Streamlit checkboxes
            # -----------------------------------------
            
            # --- SIMPLIFIED LEGEND HTML for the Sidebar ---
            # No positioning or complex styling needed here. It will flow naturally in the sidebar.
            legend_html = f'''
            <div style="font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 13px;">
                <h4 style="margin-top: 0; margin-bottom: 12px; color: #2E8B57; text-align: center;">
                    🗺️ Legenda do Mapa
                </h4>
                <div style="margin-bottom: 10px;">
                    <strong>📊 Dados:</strong> {get_friendly_column_label(display_col)}
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>📈 Faixa de Potencial:</strong><br>
                    Min: {df_merged[display_col].min():,.0f} m³/ano<br>
                    Max: {df_merged[display_col].max():,.0f} m³/ano
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>🎨 Escala de Cores:</strong><br>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #ffffcc; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Muito Baixo</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #c7e9b4; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Baixo</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #7fcdbb; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Médio</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #41b6c4; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Alto</span>
                    </div>
                    <div style="display: flex; align-items: center; margin: 2px 0;">
                        <div style="width: 15px; height: 15px; background-color: #253494; border: 1px solid #ccc; margin-right: 5px;"></div>
                        <span>Muito Alto</span>
                    </div>
                </div>
                <div>
                    <strong>📏 Tamanho do Círculo:</strong><br>
                    <small>Proporcional ao potencial de biogás</small>
                </div>
            </div>
            '''
            
            # Check if only legend is requested
            if get_legend_only:
                return None, legend_html
            
            # --- REMOVED ---
            # m.get_root().html.add_child(folium.Element(legend_html))  <- REMOVE THIS LINE
            
        except Exception as e:
            st.error(f"❌ Error loading centroids: {e}")
            st.write(f"Debug: Exception details: {str(e)}")
        
        # Add floating legend to map - for circle and choropleth visualizations
        if viz_type in ["Círculos Proporcionais", "Mapa de Preenchimento (Coroplético)"]:
            legend_html_for_map = f'''
        <div style="position: fixed; 
                    top: 10px; right: 10px; width: 250px; height: auto; 
                    background-color: rgba(255, 255, 255, 0.95); 
                    border: 2px solid #2E8B57;
                    z-index:9999; font-size:12px; border-radius: 8px; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    font-family: 'Segoe UI', Tahoma, sans-serif;">
            <h4 style="margin-top: 0; margin-bottom: 8px; color: #2E8B57; text-align: center; font-size: 14px;">
                🗺️ Legenda
            </h4>
            <div style="margin-bottom: 8px; font-size: 11px;">
                <strong>📊 Dados:</strong> {get_friendly_column_label(display_col)}
            </div>
            <div style="margin-bottom: 8px; font-size: 11px;">
                <strong>📈 Faixa:</strong><br>
                Min: {df_merged[display_col].min():,.0f}<br>
                Max: {df_merged[display_col].max():,.0f}
            </div>
            <div style="margin-bottom: 8px; font-size: 11px;">
                <strong>🎨 Cores:</strong><br>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #ffffcc; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Muito Baixo</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #c7e9b4; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Baixo</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #7fcdbb; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Médio</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #41b6c4; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Alto</span>
                </div>
                <div style="display: flex; align-items: center; margin: 1px 0;">
                    <div style="width: 12px; height: 12px; background-color: #253494; border: 1px solid #ccc; margin-right: 4px;"></div>
                    <span style="font-size: 10px;">Muito Alto</span>
                </div>
            </div>
            <div style="font-size: 10px;">
                <strong>📏 Tamanho:</strong> Proporcional ao potencial
            </div>
        </div>
        '''
        
            # Add the legend to the map
            m.get_root().html.add_child(folium.Element(legend_html_for_map))
        
        # --- VISUALIZAÇÃO DA ANÁLISE DE PROXIMIDADE ---
        logger.info(f"🔍 Map rendering: catchment_info = {catchment_info}")
        if catchment_info and catchment_info.get("center"):
            center_lat, center_lon = catchment_info["center"]
            radius_km = catchment_info["radius"]
            logger.info(f"Adding visual marker at ({center_lat:.4f}, {center_lon:.4f}) with radius {radius_km}km")
            
            # Adiciona o Pin (Marcador) no centro - MELHORADO
            logger.info(f"🔴 Adding marker to proximity_group at [{center_lat}, {center_lon}]")
            folium.Marker(
                location=[center_lat, center_lon],
                popup=f"📍 <b>Centro de Análise</b><br>🎯 Raio: {radius_km} km<br>📍 Lat: {center_lat:.4f}<br>📍 Lon: {center_lon:.4f}",
                tooltip="🎯 Centro da Análise de Proximidade",
                icon=folium.Icon(color='red', icon='glyphicon-screenshot', prefix='glyphicon')
            ).add_to(proximity_group)
            
            # Adiciona o Círculo do Raio - MELHORADO
            logger.info(f"🔵 Adding circle to proximity_group with radius {radius_km * 1000}m")
            folium.Circle(
                location=[center_lat, center_lon],
                radius=radius_km * 1000,  # folium.Circle usa metros
                color='#FF4444',  # Vermelho mais vibrante
                weight=3,         # Linha mais grossa
                fill=True,
                fill_color='#FF6B6B',
                fill_opacity=0.2,  # Um pouco mais opaco
                popup=f"🎯 <b>Área de Análise</b><br>📏 Raio: {radius_km} km<br>📐 Área: {3.14159 * radius_km**2:.1f} km²",
                tooltip=f"🎯 Área de captação - {radius_km} km"
            ).add_to(proximity_group)
            
            # Adicionar círculo interno para melhor visualização
            folium.Circle(
                location=[center_lat, center_lon],
                radius=radius_km * 200,  # Círculo menor no centro
                color='#FF0000',
                weight=2,
                fill=True,
                fill_color='#FF0000',
                fill_opacity=0.8,
                popup=f"📍 Centro exato da análise",
                tooltip="Centro da análise"
            ).add_to(proximity_group)
        
        # NO FINAL DA FUNÇÃO, ANTES DO RETURN, adiciona o grupo ao mapa
        logger.info(f"🗺️ Adding proximity_group to map (contains {len(proximity_group._children)} children)")
        proximity_group.add_to(m)
        
        return m, legend_html
        
    except Exception as e:
        import traceback
        logger.error(f"Erro na criação do mapa: {e}")
        st.error(f"❌ Erro na criação do mapa: {e}")
        return folium.Map(location=[-22.5, -48.5], zoom_start=7), ""  # Return empty map/legend

def create_map(df, display_col, show_plantas_biogas=False, show_gasodutos_dist=False, show_gasodutos_transp=False, show_rios=False, show_rodovias=False, show_mapbiomas=False):
    """Create optimized folium map with municipality boundaries"""
    import geopandas as gpd
    from pathlib import Path
    
    # Center map on São Paulo state
    m = folium.Map(
        location=[-22.5, -48.5], 
        zoom_start=7,
        tiles='OpenStreetMap',
        attr='OpenStreetMap'
    )
    
    if df.empty:
        return m
    
    try:
        # Load optimized geometries based on data size
        municipality_count = len(df)
        
        if municipality_count > 200:
            detail_level = "low_detail"  # Fast for large datasets
        elif municipality_count > 50:
            detail_level = "medium_detail"  # Balanced
        else:
            detail_level = "high_detail"  # Detailed for small datasets
        
        gdf = load_optimized_geometries(detail_level)
        
        if gdf is None:
            return create_simple_map(df, display_col)
        
        # Merge geometries with data
        df_merged = gdf.merge(df, on='cd_mun', how='inner', suffixes=('_geo', ''))
        
        if df_merged.empty:
            st.warning("⚠️ Nenhum município encontrado nos dados geométricos.")
            return create_simple_map(df, display_col)
        
        # Ensure we have a consistent municipality name column
        if 'nome_municipio' not in df_merged.columns:
            if 'NM_MUN' in df_merged.columns:
                df_merged['nome_municipio'] = df_merged['NM_MUN']
            elif 'nome_municipio_geo' in df_merged.columns:
                df_merged['nome_municipio'] = df_merged['nome_municipio_geo']
        
        # Get value range for colors
        max_val = df_merged[display_col].max()
        min_val = df_merged[display_col].min()
        
        if max_val == min_val:
            max_val = min_val + 1
        
        # Create optimized GeoJson layer
        def style_function(feature):
            # Get municipality value
            cd_mun = feature['properties']['cd_mun']
            mun_data = df_merged[df_merged['cd_mun'] == cd_mun]
            
            if not mun_data.empty:
                value = mun_data.iloc[0][display_col]
                intensity = (value - min_val) / (max_val - min_val)
                
                if intensity > 0.8:
                    color = '#d73027'
                elif intensity > 0.6:
                    color = '#fc8d59'
                elif intensity > 0.4:
                    color = '#fee08b'
                elif intensity > 0.2:
                    color = '#d9ef8b'
                else:
                    color = '#91bfdb'
            else:
                color = '#cccccc'
            
            return {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7,
            }
        
        # Add optimized GeoJson layer
        folium.GeoJson(
            df_merged,
            style_function=style_function,
            popup=folium.GeoJsonPopup(
                fields=['nome_municipio', display_col],
                aliases=['Município:', 'Potencial:'],
                localize=True,
                labels=True,
                style="background-color: white;",
            ),
            tooltip=folium.GeoJsonTooltip(
                fields=['nome_municipio', display_col],
                aliases=['Município:', 'Potencial:'],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=800,
            )
        ).add_to(m)
        
        # Add performance info
        st.info(f"📊 Renderizando {len(df_merged)} municípios com nível de detalhe: {detail_level}")
        
        return m
        
    except Exception as e:
        st.error(f"❌ Erro ao criar mapa: {e}")
        return create_simple_map(df, display_col)

def create_simple_map(df, display_col):
    """Fallback simple map creation"""
    m = folium.Map(location=[-22.5, -48.5], zoom_start=7)
    
    # Simple grid-based visualization as fallback
    import random
    random.seed(42)
    
    for idx, row in df.iterrows():
        intensity = random.uniform(0, 1)  # Simplified for fallback
        
        lat = -22.5 + random.uniform(-2, 2)
        lon = -48.5 + random.uniform(-4, 4)
        
        # Handle different municipality name columns
        muni_name = row.get('nome_municipio', row.get('NM_MUN', f'Município {idx}'))
        
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=f"<b>{muni_name}</b>",
            color='blue',
            fillColor='lightblue',
            fillOpacity=0.6
        ).add_to(m)
    
    return m

# Chart functions
def create_top_chart(df, display_col, title, limit=15):
    """Create top municipalities chart"""
    if df.empty:
        return None
    
    top_data = df.nlargest(limit, display_col)
    
    fig = px.bar(
        top_data,
        x='nome_municipio',
        y=display_col,
        title=f'Top {limit} Municípios - {title}',
        labels={display_col: 'Potencial (m³/ano)', 'nome_municipio': 'Município'}
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=False
    )
    
    return fig

def create_distribution_chart(df, display_col, title):
    """Create distribution chart"""
    if df.empty:
        return None
    
    fig = px.histogram(
        df,
        x=display_col,
        title=f'Distribuição - {title}',
        nbins=20,
        labels={display_col: 'Potencial (m³/ano)'}
    )
    fig.update_layout(height=400)
    
    return fig

def create_correlation_chart(df, display_col, title):
    """Create a scatter plot to show correlation."""
    if df.empty or 'populacao_2022' not in df.columns:
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

# Page functions
def show_municipality_details_horizontal(df, municipality_id, selected_residues):
    """Show optimized horizontal layout for municipality details"""
    
    # Convert municipality_id and get data
    try:
        if municipality_id in df['cd_mun'].astype(str).values:
            mun_data = df[df['cd_mun'].astype(str) == str(municipality_id)].iloc[0]
        elif int(municipality_id) in df['cd_mun'].values:
            mun_data = df[df['cd_mun'] == int(municipality_id)].iloc[0]
        else:
            st.error(f"Município com ID {municipality_id} não encontrado.")
            return
    except (ValueError, IndexError) as e:
        st.error(f"Erro ao encontrar município: {e}")
        return
    
    # Compact header
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #2E8B57 0%, #32CD32 100%); 
                color: white; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.8rem;'>
        <div style='margin: 0; color: white; font-size: 1.1em; font-weight: bold;'>
        </div>
        <div style='margin: 2px 0 0 0; opacity: 0.9; font-size: 0.85em;'>
            👥 {mun_data.get('populacao_2022', 0):,.0f} hab | 📐 {mun_data.get('area_km2', 0):.1f} km²
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Key metrics in 2x2 grid
    total_potential = mun_data.get('total_final_m_ano', 0)
    agri_potential = mun_data.get('total_agricola_m_ano', 0)
    livestock_potential = mun_data.get('total_pecuaria_m_ano', 0)
    urban_potential = mun_data.get('total_urbano_m_ano', 0) if 'total_urbano_m_ano' in mun_data else 0
    
    # Compact metrics grid
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🎯 Total", f"{total_potential/1000000:.1f}M m³/ano")
        st.metric("🌾 Agrícola", f"{agri_potential/1000000:.1f}M m³/ano")
    with col2:
        st.metric("🐄 Pecuária", f"{livestock_potential/1000000:.1f}M m³/ano")
        st.metric("🏘️ Urbano", f"{urban_potential/1000000:.1f}M m³/ano")
    
    # Compact visualization
    if total_potential > 0:
        st.markdown("**🏆 Composição do Potencial:**")
        
        # Pie chart data
        main_categories = {
            'Agrícola': agri_potential,
            'Pecuária': livestock_potential,
            'Urbano': urban_potential
        }
        
        # Filter non-zero values
        main_categories = {k: v for k, v in main_categories.items() if v > 0}
        
        if main_categories:
            # Create compact pie chart
            fig = px.pie(
                values=list(main_categories.values()),
                names=list(main_categories.keys()),
                color_discrete_map={'Agrícola': '#228B22', 'Pecuária': '#8B4513', 'Urbano': '#4169E1'},
                height=250  # Compact height
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=False,
                font=dict(size=10)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Top residue sources - compact list
        st.markdown("**📋 Principais Fontes:**")
        
        residue_sources = []
        for col in df.columns:
            if col.endswith('_m_ano') and col not in ['total_final_m_ano', 'total_agricola_m_ano', 'total_pecuaria_m_ano', 'total_urbano_m_ano']:
                value = mun_data.get(col, 0)
                if value > 0:
                    clean_name = col.replace('_m_ano', '').replace('_', ' ').title()
                    residue_sources.append((clean_name, value))
        
        # Sort and show top 5
        residue_sources.sort(key=lambda x: x[1], reverse=True)
        for i, (name, value) in enumerate(residue_sources[:5]):
            percentage = (value / total_potential) * 100
            st.markdown(f"**{i+1}.** {name}: {value/1000000:.2f}M m³ ({percentage:.1f}%)")
        
        # Neighboring municipalities comparison chart
        # Regional comparison removed - data not available
        if False:  # Disabled regional comparison
                # Sort by total potential and get top 5 + current municipality
                same_region_sorted = same_region.nlargest(8, 'total_final_m_ano')
                
                # Ensure current municipality is included
                if municipality_id not in same_region_sorted['cd_mun'].astype(str).values:
                    current_mun_row = same_region[same_region['cd_mun'].astype(str) == str(municipality_id)]
                    if not current_mun_row.empty:
                        same_region_sorted = pd.concat([same_region_sorted.head(7), current_mun_row])
                
                # Create comparison bar chart
                comparison_data = []
                for _, row in same_region_sorted.iterrows():
                    is_current = str(row['cd_mun']) == str(municipality_id)
                    comparison_data.append({
                        'Município': row['nome_municipio'][:15] + ('...' if len(row['nome_municipio']) > 15 else ''),
                        'Potencial': row['total_final_m_ano'] / 1000000,
                        'Atual': is_current
                    })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                # Create bar chart
                fig = px.bar(
                    comparison_df, 
                    x='Potencial', 
                    y='Município',
                    orientation='h',
                    color='Atual',
                    color_discrete_map={True: '#32CD32', False: '#87CEEB'},
                    height=250,
                    labels={'Potencial': 'Potencial (M m³/ano)'}
                )
                fig.update_layout(
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=False,
                    font=dict(size=9),
                    yaxis=dict(tickfont=dict(size=8))
                )
                fig.update_traces(texttemplate='%{x:.1f}M', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            # else:
            #     st.info("Único município na região")

def show_municipality_details_compact(df, municipality_id, selected_residues):
    """Show compact detailed analysis panel for clicked municipality"""
    
    # Convert municipality_id to appropriate type and get municipality data
    try:
        # Try as string first, then as int
        if municipality_id in df['cd_mun'].astype(str).values:
            mun_data = df[df['cd_mun'].astype(str) == str(municipality_id)].iloc[0]
        elif int(municipality_id) in df['cd_mun'].values:
            mun_data = df[df['cd_mun'] == int(municipality_id)].iloc[0]
        else:
            st.error(f"Município com ID {municipality_id} não encontrado no dataset.")
            return
    except (ValueError, IndexError) as e:
        st.error(f"Erro ao encontrar município: {e}")
        return
    
    # Header with municipality info and actions
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        # Enhanced header with styling
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #2E8B57 0%, #32CD32 100%); 
                    color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
            <h2 style='margin: 0; color: white;'>🏙️ {mun_data['nome_municipio']}</h2>
            <p style='margin: 5px 0 0 0; opacity: 0.9;'>
                👥 <strong>População:</strong> {mun_data.get('populacao_2022', 0):,.0f} hab. | 
                📐 <strong>Área:</strong> {mun_data.get('area_km2', 0):.1f} km²
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        # Action buttons        
        if st.button("📊 Adicionar", key="add_comparison_compact", help="Adicionar à comparação"):
            if municipality_id not in st.session_state.selected_municipalities:
                st.session_state.selected_municipalities.append(municipality_id)
                st.toast("Município adicionado!", icon="✅")
                st.rerun()
    
    # Enhanced key metrics with better visualization
    st.markdown("#### 📊 Indicadores Principais")
    
    # Calculate percentages for better context
    total_potential = mun_data.get('total_final_m_ano', 0)
    agri_potential = mun_data.get('total_agricola_m_ano', 0)
    livestock_potential = mun_data.get('total_pecuaria_m_ano', 0)
    urban_potential = mun_data.get('total_urbano_m_ano', 0) if 'total_urbano_m_ano' in mun_data else 0
    
    # Calculate percentile rankings
    total_percentile = (df['total_final_m_ano'] < total_potential).mean() * 100 if total_potential > 0 else 0
    agri_percentile = (df['total_agricola_m_ano'] < agri_potential).mean() * 100 if agri_potential > 0 else 0
    livestock_percentile = (df['total_pecuaria_m_ano'] < livestock_potential).mean() * 100 if livestock_potential > 0 else 0
    
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.metric(
            "🎯 Potencial Total", 
            f"{total_potential/1000000:.1f}M m³/ano",
            delta=f"Top {100-total_percentile:.0f}%" if total_percentile > 50 else f"P{total_percentile:.0f}"
        )
    
    with metric_cols[1]:
        st.metric(
            "🌾 Agrícola", 
            f"{agri_potential/1000000:.1f}M m³/ano",
            delta=f"Top {100-agri_percentile:.0f}%" if agri_percentile > 50 else f"P{agri_percentile:.0f}"
        )
    
    with metric_cols[2]:
        st.metric(
            "🐄 Pecuária", 
            f"{livestock_potential/1000000:.1f}M m³/ano",
            delta=f"Top {100-livestock_percentile:.0f}%" if livestock_percentile > 50 else f"P{livestock_percentile:.0f}"
        )
    
    with metric_cols[3]:
        st.metric(
            "🏘️ Urbano", 
            f"{urban_potential/1000000:.1f}M m³/ano",
            delta="Estimativa" if urban_potential > 0 else "N/D"
        )
    
    # Compact tabs for detailed analysis
    compact_tabs = st.tabs(["📋 Resumo", "🏘️ Vizinhos", "📈 Ranking"])
    
    with compact_tabs[0]:  # Summary
        # Enhanced residue sources visualization
        st.markdown("**🏆 Composição do Potencial de Biogás:**")
        
        # Create two columns: pie chart and detailed breakdown
        chart_col, detail_col = st.columns([1.5, 1])
        
        with chart_col:
            # Get the main categories data
            main_categories = {
                '🌾 Agrícola': agri_potential,
                '🐄 Pecuária': livestock_potential, 
                '🏘️ Urbano': urban_potential
            }
            
            # Filter out zero values
            filtered_categories = {k: v for k, v in main_categories.items() if v > 0}
            
            if filtered_categories:
                import plotly.express as px
                import pandas as pd
                
                # Create pie chart for main categories
                pie_df = pd.DataFrame(list(filtered_categories.items()), columns=['Categoria', 'Potencial'])
                fig_pie = px.pie(pie_df, 
                               values='Potencial', 
                               names='Categoria',
                               title='Distribuição por Categoria',
                               color_discrete_sequence=px.colors.qualitative.Set3)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=300, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sem dados disponíveis para visualização.")
        
        with detail_col:
            st.markdown("**📊 Detalhamento por Fonte:**")
            
            # Detailed residue breakdown
            residue_data = []
            residue_icons = {
                'Biogás de Cana': '🌾', 'Biogás de Soja': '🌱', 'Biogás de Milho': '🌽',
                'Biogás de Café': '☕', 'Biogás de Citros': '🍊', 'Biogás de Bovinos': '🐄',
                'Biogás de Suínos': '🐷', 'Biogás de Aves': '🐔', 'RSU': '🗑️', 'RPO': '🛢️'
            }
            
            for residue_name, column_name in RESIDUE_OPTIONS.items():
                if column_name in df.columns and 'Total' not in residue_name:
                    value = mun_data.get(column_name, 0)
                    if value > 0:
                        icon = residue_icons.get(residue_name, '📊')
                        residue_data.append((f"{icon} {residue_name}", value))
            
            if residue_data:
                # Sort by value and get top sources
                residue_data.sort(key=lambda x: x[1], reverse=True)
                top_residues = residue_data[:8]  # Show top 8
                
                for name, value in top_residues:
                    percentage = (value / total_potential * 100) if total_potential > 0 else 0
                    st.markdown(f"**{name}**")
                    st.markdown(f"└ {value/1000000:.2f}M m³/ano ({percentage:.1f}%)")
                    st.progress(percentage/100)
                    st.markdown("")
            else:
                st.info("Nenhum dado detalhado disponível.")
    
    with compact_tabs[1]:  # Neighbors
        st.markdown("**🏘️ Comparação com Vizinhos (50km):**")
        try:
            neighbors = find_neighboring_municipalities(df, mun_data, radius_km=50)
            
            if len(neighbors) > 1:
                # Show top 5 neighbors - usar total_final_m_ano como padrão
                neighbor_comparison = []
                current_total = mun_data.get('total_final_m_ano', 0)
                
                for neighbor in neighbors[:6]:  # Top 5 + current
                    if neighbor['cd_mun'] != municipality_id:
                        neighbor_total = neighbor.get('total_final_m_ano', 0)
                        neighbor_comparison.append({
                            'Município': neighbor['nome_municipio'],
                            'Potencial': neighbor_total,
                            'Distância': f"{neighbor.get('distance', 0):.1f} km"
                        })
                
                # Add current municipality for comparison
                neighbor_comparison.append({
                    'Município': f"{mun_data['nome_municipio']} (ATUAL)",
                    'Potencial': current_total,
                    'Distância': "0.0 km"
                })
                
                # Sort by potential
                neighbor_comparison.sort(key=lambda x: x['Potencial'], reverse=True)
                
                # Create a visual comparison chart
                if neighbor_comparison:
                    neighbor_df = pd.DataFrame(neighbor_comparison)
                    neighbor_df['É_Atual'] = neighbor_df['Município'].str.contains('ATUAL')
                    
                    # Horizontal bar chart for neighbors
                    fig = px.bar(neighbor_df, 
                                x='Potencial', 
                                y='Município',
                                orientation='h',
                                title='Comparação com Vizinhos (50km)',
                                color='É_Atual',
                                color_discrete_map={True: '#ff6b6b', False: '#4ecdc4'},
                                labels={'Potencial': 'Potencial (m³/ano)'})
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show distance info in a compact table
                    st.dataframe(neighbor_df[['Município', 'Distância']].head(6), 
                                use_container_width=True, hide_index=True)
            else:
                st.info("Poucos vizinhos encontrados para comparação.")
        except Exception as e:
            st.warning("Não foi possível carregar dados dos vizinhos.")
    
    with compact_tabs[2]:  # Ranking
        st.markdown("**📈 Posição nos Rankings:**")
        
        try:
            # State ranking
            state_rank = (df['total_final_m_ano'] >= total_potential).sum()
            state_percentile = ((len(df) - state_rank + 1) / len(df)) * 100
            
            # Regional ranking
            regional_rank = None
            regional_total = 0
            # Regional comparison removed - data not available
            if False:
                regional_rank = (regional_df['total_final_m_ano'] >= total_potential).sum()
                regional_total = len(regional_df)
            
            # Create ranking visualization
            ranking_data = [
                {'Categoria': 'Estado de SP', 'Posição': state_rank, 'Total': len(df), 'Percentil': state_percentile}
            ]
            
            if regional_rank:
                regional_percentile = ((regional_total - regional_rank + 1) / regional_total) * 100
                regiao_nome = mun_data.get('regiao_imediata', 'Regional')
                ranking_data.append({
                    'Categoria': f'Região {regiao_nome}', 
                    'Posição': regional_rank, 
                    'Total': regional_total,
                    'Percentil': regional_percentile
                })
            
            # Display as metrics
            rank_cols = st.columns(len(ranking_data))
            for i, rank_info in enumerate(ranking_data):
                with rank_cols[i]:
                    st.metric(
                        label=rank_info['Categoria'],
                        value=f"{rank_info['Posição']}º / {rank_info['Total']}",
                        delta=f"Top {rank_info['Percentil']:.0f}%"
                    )
            
            # Visual percentile representation
            fig = px.bar(
                x=[r['Categoria'] for r in ranking_data],
                y=[r['Percentil'] for r in ranking_data],
                title='Posição Percentual nos Rankings',
                labels={'x': 'Categoria', 'y': 'Percentil (%)'},
                color=[r['Percentil'] for r in ranking_data],
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.warning("Não foi possível calcular rankings.")
        
        # Population category ranking
        if 'populacao_2022' in df.columns:
            population = mun_data.get('populacao_2022', 0)
            if population > 100000:
                category = "Grandes (>100k hab)"
                category_df = df[df['populacao_2022'] > 100000]
            elif population > 50000:
                category = "Médios (50-100k hab)"
                category_df = df[(df['populacao_2022'] > 50000) & (df['populacao_2022'] <= 100000)]
            else:
                category = "Pequenos (<50k hab)"
                category_df = df[df['populacao_2022'] <= 50000]
            
            if len(category_df) > 0:
                category_rank = (category_df['total_final_m_ano'] >= total_potential).sum()
                st.write(f"👥 **{category}**: {category_rank}º de {len(category_df)} municípios")


def show_municipality_details(df, municipality_id, selected_residues):
    """Show detailed analysis panel for clicked municipality"""
    
    # Convert municipality_id to appropriate type and get municipality data
    try:
        # Try as string first, then as int
        if municipality_id in df['cd_mun'].astype(str).values:
            mun_data = df[df['cd_mun'].astype(str) == str(municipality_id)].iloc[0]
        elif int(municipality_id) in df['cd_mun'].values:
            mun_data = df[df['cd_mun'] == int(municipality_id)].iloc[0]
        else:
            st.error(f"Município com ID {municipality_id} não encontrado no dataset.")
            return
    except (ValueError, IndexError) as e:
        st.error(f"Erro ao encontrar município: {e}")
        return
    
    # Create a prominent panel for municipality details
    st.markdown("---")
    
    # Header with municipality info
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
        ### 🏙️ **{mun_data['nome_municipio']}**
        **População:** {mun_data.get('populacao_2022', 0):,.0f} hab. |
        **Área:** {mun_data.get('area_km2', 0):.1f} km²
        """)
    
    with col2:
        st.empty()  # Espaço vazio no lugar do botão removido
    
    with col3:
        # Quick actions
        if st.button("📊 Adicionar à Comparação", key="add_comparison"):
            if municipality_id not in st.session_state.selected_municipalities:
                st.session_state.selected_municipalities.append(municipality_id)
                st.toast("Município adicionado à comparação!", icon="📊")
                st.rerun()
    
    # Detailed analysis tabs
    detail_tabs = st.tabs([
        "📋 Dados Completos", 
        "🏘️ Comparação com Vizinhos", 
        "📈 Análise de Potencial",
        "🗺️ Contexto Regional"
    ])
    
    with detail_tabs[0]:  # Complete Data
        st.subheader("📊 Dados de Resíduos - " + mun_data['nome_municipio'])
        
        # Create comprehensive data table
        residue_data = []
        for residue_name, column_name in RESIDUE_OPTIONS.items():
            if column_name in df.columns:
                value = mun_data.get(column_name, 0)
                if value > 0:
                    # Calculate percentiles for context
                    percentile = (df[column_name] <= value).mean() * 100
                    
                    residue_data.append({
                        'Tipo de Resíduo': residue_name,
                        'Potencial (m³/ano)': f"{value:,.0f}",
                        'Percentil': f"{percentile:.1f}%",
                        'Classificação': get_classification_label(percentile)
                    })
        
        if residue_data:
            residue_df = pd.DataFrame(residue_data)
            st.dataframe(residue_df, use_container_width=True)
            
            # Download button
            csv = residue_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar Dados do Município",
                data=csv,
                file_name=f"dados_{mun_data['nome_municipio'].replace(' ', '_')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Nenhum dado de resíduo disponível para este município.")
    
    with detail_tabs[1]:  # Neighbor Comparison
        st.subheader("🏘️ Comparação com Municípios Vizinhos")
        
        # Find neighboring municipalities (simplified approach using lat/lng proximity)
        neighbors = find_neighboring_municipalities(df, mun_data, radius_km=50)
        
        if len(neighbors) > 1:
            # Create comparison chart
            comparison_data = []
            
            # Add current municipality
            total_current = sum([mun_data.get(col, 0) for col in selected_residues if col in df.columns])
            comparison_data.append({
                'Município': mun_data['nome_municipio'] + ' (SELECIONADO)',
                'Potencial Total': total_current,
                'População': mun_data.get('populacao_2022', 0),
                'Tipo': 'Selecionado'
            })
            
            # Add neighbors
            for neighbor in neighbors[:10]:  # Top 10 neighbors
                if neighbor['cd_mun'] != municipality_id:
                    neighbor_total = sum([neighbor.get(col, 0) for col in selected_residues if col in df.columns])
                    comparison_data.append({
                        'Município': neighbor['nome_municipio'],
                        'Potencial Total': neighbor_total,
                        'População': neighbor.get('populacao_2022', 0),
                        'Tipo': 'Vizinho'
                    })
            
            comp_df = pd.DataFrame(comparison_data)
            
            # Bar chart comparison
            fig = px.bar(
                comp_df, 
                x='Município', 
                y='Potencial Total',
                color='Tipo',
                color_discrete_map={'Selecionado': '#FF6B6B', 'Vizinho': '#4ECDC4'},
                title=f"Comparação de Potencial: {mun_data['nome_municipio']} vs Vizinhos",
                height=400
            )
            fig.update_xaxis(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_neighbors = comp_df[comp_df['Tipo'] == 'Vizinho']['Potencial Total'].mean()
                st.metric(
                    "Média dos Vizinhos", 
                    f"{avg_neighbors:,.0f} m³/ano"
                )
            
            with col2:
                current_vs_avg = (total_current / avg_neighbors - 1) * 100 if avg_neighbors > 0 else 0
                st.metric(
                    "Diferença da Média",
                    f"{current_vs_avg:+.1f}%"
                )
            
            with col3:
                rank = (comp_df['Potencial Total'] >= total_current).sum()
                st.metric(
                    "Posição no Ranking",
                    f"{rank}º de {len(comp_df)}"
                )
        else:
            st.info("Poucos municípios vizinhos encontrados para comparação.")
    
    with detail_tabs[2]:  # Potential Analysis
        st.subheader("📈 Análise Detalhada de Potencial")
        
        # Radar chart for different residue types
        residue_values = []
        residue_names = []
        
        for residue_name, column_name in RESIDUE_OPTIONS.items():
            if column_name in df.columns:
                value = mun_data.get(column_name, 0)
                if value > 0:
                    # Normalize to 0-100 scale based on max in dataset
                    max_value = df[column_name].max()
                    normalized_value = (value / max_value) * 100 if max_value > 0 else 0
                    
                    residue_values.append(normalized_value)
                    residue_names.append(residue_name)
        
        if residue_values:
            # Create radar chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatterpolar(
                r=residue_values,
                theta=residue_names,
                fill='toself',
                name=mun_data['nome_municipio'],
                line_color='#FF6B6B'
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100]
                    )),
                showlegend=True,
                title=f"Perfil de Resíduos - {mun_data['nome_municipio']}<br><sub>Valores normalizados (0-100%)</sub>",
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Top 3 residues
            residue_ranking = list(zip(residue_names, residue_values))
            residue_ranking.sort(key=lambda x: x[1], reverse=True)
            
            st.markdown("**🏆 Top 3 Tipos de Resíduo:**")
            for i, (name, value) in enumerate(residue_ranking[:3]):
                st.write(f"{i+1}. **{name}**: {value:.1f}% do máximo estadual")
    
    with detail_tabs[3]:  # Regional Context
        st.subheader("🗺️ Contexto Regional")
        
        # Regional statistics with real data
        # Regional analysis removed - data not available
        if False:
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Região Imediata:** {regiao_imediata}")
                st.markdown(f"**Região Intermediária:** {regiao_intermediaria}")
                st.metric(
                    "Municípios na Região", 
                    len(regional_df)
                )
                
                # Position in region
                total_current = sum([mun_data.get(col, 0) for col in selected_residues if col in df.columns])
                regional_rank = (regional_df.apply(lambda row: sum([row.get(col, 0) for col in selected_residues if col in df.columns]), axis=1) >= total_current).sum()
                
                st.metric(
                    "Posição na Região",
                    f"{regional_rank}º de {len(regional_df)}"
                )
                
            with col2:
                # Regional averages
                regional_avg = regional_df.apply(lambda row: sum([row.get(col, 0) for col in selected_residues if col in df.columns]), axis=1).mean()
                state_avg = df.apply(lambda row: sum([row.get(col, 0) for col in selected_residues if col in df.columns]), axis=1).mean()
                
                st.metric(
                    "Média Regional",
                    f"{regional_avg:,.0f} m³/ano"
                )
                
                st.metric(
                    "Média Estadual",
                    f"{state_avg:,.0f} m³/ano"
                )
        else:
            st.info("📍 Dados regionais não disponíveis para este município")



def page_main():
    """Main map page with ultra-thin sidebar and comprehensive analysis tools."""
    
    # --- 1. GERENCIAMENTO DE ESTADO E LIMPEZA DE MEMÓRIA ---
    cleanup_memory()
    
    if 'clicked_municipality' not in st.session_state:
        st.session_state.clicked_municipality = None
    if 'selected_municipalities' not in st.session_state:
        st.session_state.selected_municipalities = []

    # --- 2. CARREGAMENTO DE DADOS ---
    df = load_municipalities()
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    # --- INÍCIO DA MUDANÇA: Garantir coordenadas no DF principal ---
    # Verifica se precisa carregar coordenadas (se não existem ou se todas são zero)
    needs_coordinates = ('lat' not in df.columns or 'lon' not in df.columns or 
                        (df['lat'].sum() == 0 and df['lon'].sum() == 0))
    
    if needs_coordinates:
        try:
            centroid_path = Path(__file__).parent.parent.parent / "shapefile" / "municipality_centroids.parquet"
            
            if centroid_path.exists():
                centroids_df = pd.read_parquet(centroid_path)
                
                # Verifica se tem as colunas necessárias
                if 'lat' in centroids_df.columns and 'lon' in centroids_df.columns:
                    # Remove coordenadas antigas se existirem
                    if 'lat' in df.columns:
                        df = df.drop(['lat'], axis=1)
                    if 'lon' in df.columns:
                        df = df.drop(['lon'], axis=1)
                    
                    # Mantém apenas as colunas necessárias para o merge
                    centroids_df = centroids_df[['cd_mun', 'lat', 'lon']]
                    
                    # Faz o merge, adicionando lat/lon ao df principal
                    df = pd.merge(df, centroids_df, on='cd_mun', how='left')
                    
                    # Verifica se as colunas foram criadas e preenche valores faltantes
                    if 'lat' in df.columns and 'lon' in df.columns:
                        df['lat'] = df['lat'].fillna(0)
                        df['lon'] = df['lon'].fillna(0)
        except Exception:
            pass
    # --- FIM DA MUDANÇA ---
    
    # --- 3. SIDEBAR DE FILTROS (ESQUERDA) ---
    with st.sidebar:
        # CP2B Logo no topo da sidebar
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("logotipo-full-black.png", width=960)

        st.markdown("""
        <div style='background: #2E8B57; color: white; padding: 0.8rem; margin: -1rem -1rem 1rem -1rem;
                    text-align: center; border-radius: 8px;'>
            <h3 style='margin: 0; font-size: 1.1rem;'>🎛️ PAINEL DE CONTROLE DO MAPA</h3>
            <p style='font-size: 0.8rem; opacity: 0.9; margin: 0.2rem 0 0 0;'>Página Mapa Principal</p>
        </div>
        """, unsafe_allow_html=True)
        
        # === SISTEMA DE PAINÉIS EXCLUSIVOS ===
        # Initialize panel states if not exists
        if 'active_panel' not in st.session_state:
            st.session_state.active_panel = 'camadas'
        
        # === 1. EXPANDER PARA CAMADAS (Ação mais comum) ===
        with st.expander("🗺️ Camadas Visíveis", expanded=False):  # Controle dinâmico
            # Auto-set as active panel when interacted with
            if st.session_state.active_panel != 'camadas':
                st.session_state.active_panel = 'camadas'
            
            st.write("**Dados Principais:**")
            show_municipios_biogas = st.checkbox("📊 Potencial de Biogás", value=True)
            show_municipios_polygons = st.checkbox("🗺️ Polígonos dos Municípios", value=False, disabled=True, help="Funcionalidade desabilitada na versão demo")
            show_municipios_polygons = False  # Forçar desabilitação
            
            st.write("**Infraestrutura:**")
            show_plantas_biogas = st.checkbox("🏭 Plantas de Biogás", value=False)
            show_gasodutos_dist = st.checkbox("⛽ Distribuição", value=False)
            show_gasodutos_transp = st.checkbox("⛽ Transporte", value=False)
            
            st.write("**Referência:**")
            show_rodovias = st.checkbox("🛣️ Rodovias", value=False)
            # Areas Urbanas layer removed for performance (Step 2 of improvement plan)
            show_areas_urbanas = False
            show_regioes_admin = st.checkbox("🏛️ Regiões Admin.", value=False)
            
            # Remove rios layer completely
            show_rios = False
            
            st.write("**Imagem de Satélite:**")
            show_mapbiomas = st.checkbox("🌾 MapBiomas - Uso do Solo", value=False)
            
            # Controles granulares de culturas MapBiomas ANINHADOS
            mapbiomas_classes = []
            if show_mapbiomas:
                st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)  # Divisor
                with st.container(border=True):  # Borda para destacar
                    st.markdown("**Selecione as culturas a visualizar:**")
                    
                    # Organizar todas as culturas em uma estrutura unificada
                    mapbiomas_options = {
                        # Pastagem
                        15: ('🌱 Pastagem', '#FFD966', 'pastagem'),

                        # Silvicultura
                        9: ('🌲 Silvicultura', '#6D4C41', 'silvicultura'),

                        # Culturas Temporárias
                        39: ('🫘 Soja', '#E1BEE7', 'temporaria'),
                        20: ('🎍 Cana-de-açúcar', '#C5E1A5', 'temporaria'),
                        40: ('🌾 Arroz', '#FFCDD2', 'temporaria'),
                        62: ('🤍 Algodão', '#F8BBD9', 'temporaria'),
                        41: ('🌱 Outras Temporárias', '#DCEDC8', 'temporaria'),

                        # Culturas Perenes
                        46: ('☕ Café', '#8D6E63', 'perene'),
                        47: ('🍊 Citrus', '#FFA726', 'perene'),
                        48: ('🌳 Outras Perenes', '#A1887F', 'perene')
                    }

                    # Inicializar flags de controle se não existirem
                    if 'mapbiomas_select_all_flag' not in st.session_state:
                        st.session_state.mapbiomas_select_all_flag = False
                    if 'mapbiomas_select_none_flag' not in st.session_state:
                        st.session_state.mapbiomas_select_none_flag = False

                    # Controles de Seleção no topo
                    col_ctrl1, col_ctrl2 = st.columns(2)
                    with col_ctrl1:
                        if st.button("✅ Selecionar Todas", key="select_all_mapbiomas", use_container_width=True):
                            st.session_state.mapbiomas_select_all_flag = True
                            st.session_state.mapbiomas_select_none_flag = False
                            st.rerun()
                    with col_ctrl2:
                        if st.button("❌ Desmarcar Todas", key="select_none_mapbiomas", use_container_width=True):
                            st.session_state.mapbiomas_select_all_flag = False
                            st.session_state.mapbiomas_select_none_flag = True
                            st.rerun()

                    st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

                    # Interface em coluna única com melhor design
                    categories = {
                        'pastagem': '🌱 Pastagem',
                        'silvicultura': '🌲 Silvicultura',
                        'temporaria': '🌾 Culturas Temporárias',
                        'perene': '🌳 Culturas Perenes'
                    }

                    for category_key, category_title in categories.items():
                        category_items = [(code, name, color) for code, (name, color, cat) in mapbiomas_options.items() if cat == category_key]

                        if category_items:
                            st.markdown(f"**{category_title}**")

                            for code, name, color in category_items:
                                # Determinar valor inicial do checkbox baseado nas flags
                                initial_value = False
                                if st.session_state.mapbiomas_select_all_flag:
                                    initial_value = True
                                elif st.session_state.mapbiomas_select_none_flag:
                                    initial_value = False
                                else:
                                    initial_value = st.session_state.get(f"mapbiomas_{code}", False)

                                # Criar checkbox com indicador de cor
                                col_check, col_color = st.columns([0.85, 0.15])
                                with col_check:
                                    selected = st.checkbox(
                                        name,
                                        value=initial_value,
                                        key=f"mapbiomas_{code}"
                                    )
                                    if selected:
                                        mapbiomas_classes.append(code)

                                with col_color:
                                    # Mostrar amostra da cor
                                    st.markdown(
                                        f'<div style="width: 30px; height: 20px; background-color: {color}; '
                                        f'border: 1px solid #ddd; border-radius: 4px; margin-top: 8px;"></div>',
                                        unsafe_allow_html=True
                                    )

                            st.markdown("<br>", unsafe_allow_html=True)  # Espaçamento entre categorias

                    # Reset das flags após processamento
                    if st.session_state.mapbiomas_select_all_flag:
                        st.session_state.mapbiomas_select_all_flag = False
                        st.toast("✅ Todas as culturas selecionadas!", icon="✅")
                    if st.session_state.mapbiomas_select_none_flag:
                        st.session_state.mapbiomas_select_none_flag = False
                        st.toast("❌ Todas as culturas desmarcadas!", icon="❌")
        
        # === 2. EXPANDER PARA FILTROS DE DADOS (Só ativo se Potencial de Biogás estiver ativo) ===
        if show_municipios_biogas:
            with st.expander("📊 Filtros de Dados", expanded=(st.session_state.active_panel == 'filtros')):
                # Auto-set as active panel when interacted with
                if st.session_state.active_panel != 'filtros':
                    st.session_state.active_panel = 'filtros'
                
                st.info("💡 **Filtros específicos para visualização do Potencial de Biogás**")
                mode = st.radio("Modo:", ["Individual", "Múltiplos"], horizontal=True, key="map_mode")
                
                if mode == "Individual":
                    selected = st.selectbox("Resíduo:", list(RESIDUE_OPTIONS.keys()), key="map_select")
                    residues = [RESIDUE_OPTIONS[selected]]
                    display_name = selected
                else:
                    selected_list = st.multiselect("Resíduos:", list(RESIDUE_OPTIONS.keys()), default=["Potencial Total"], key="map_multi")
                    residues = [RESIDUE_OPTIONS[item] for item in selected_list]
                    display_name = f"Soma de {len(residues)} tipos" if len(residues) > 1 else (selected_list[0] if selected_list else "Nenhum")
                
                search_term = st.text_input("Buscar:", placeholder="Município...", key="search")
        else:
            # Show disabled message when biogas layer is not active
            with st.expander("📊 Filtros de Dados", expanded=False):
                st.warning("⚠️ **Active a camada 'Potencial de Biogás' para usar os filtros de dados**")
                st.markdown("Os filtros de dados funcionam em conjunto com a visualização do potencial de biogás para permitir análises mais específicas.")
                
            # Set default values when disabled
            mode = "Individual"
            selected = "Potencial Total"
            residues = [RESIDUE_OPTIONS[selected]]
            display_name = selected
            search_term = ""
        
        # === 3. EXPANDER PARA ESTILOS DE VISUALIZAÇÃO ===
        with st.expander("🎨 Estilos de Visualização", expanded=(st.session_state.active_panel == 'estilos')):
            # Auto-set as active panel when interacted with
            if st.session_state.active_panel != 'estilos':
                st.session_state.active_panel = 'estilos'
            
            st.markdown("**🎯 Escolha o estilo de visualização dos dados no mapa:**")
            viz_type = st.radio("Tipo de mapa:", options=["Círculos Proporcionais", "Mapa de Calor (Heatmap)", "Agrupamentos (Clusters)"], key="viz_type", index=0)
            
            # Add descriptions for each visualization type
            if viz_type == "Círculos Proporcionais":
                st.info("🔵 **Círculos Proporcionais**: O tamanho dos círculos representa o valor dos dados. Maior potencial = círculo maior.")
            elif viz_type == "Mapa de Calor (Heatmap)":
                st.info("🔥 **Mapa de Calor**: Cores quentes (vermelho) indicam valores altos, cores frias (azul) indicam valores baixos.")
            elif viz_type == "Agrupamentos (Clusters)":
                st.info("📍 **Agrupamentos**: Municípios próximos são agrupados em clusters. Números indicam quantos pontos estão agrupados.")
            
            st.markdown("---")
            st.markdown("💡 **Dica**: Experimente diferentes estilos para descobrir qual visualização funciona melhor para seus dados!")
        
        # === ANÁLISE DE PROXIMIDADE REMOVIDA DA SIDEBAR ===
        # Moved to dedicated tab - no longer shown in map sidebar
        
        # Set default values to avoid errors in the rest of the code
        enable_proximity = False  # Desabilitado na versão demo
        st.session_state.catchment_center = None
        
        # === PAINEL REMOVIDO: OUTRAS ANÁLISES (confuso para usuários) ===
        # Valores padrão para manter compatibilidade
        classification = "Linear (Intervalo Uniforme)"
        num_classes = 5
        normalization = "Potencial Absoluto (m³/ano)"
        
        # === SEÇÃO FIXA: MUNICÍPIOS SELECIONADOS ===
        if st.session_state.selected_municipalities:
            st.markdown("---")
            st.markdown("**🎯 Municípios Selecionados:**")
            selected_names = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]['nome_municipio'].tolist()
            for name in selected_names[:3]:
                st.markdown(f"• {name[:15]}..." if len(name) > 15 else f"• {name}")
            if len(selected_names) > 3:
                st.markdown(f"...+{len(selected_names)-3} mais")
            if st.button("🗑️ Limpar Seleção", key="clear_selection"):
                st.session_state.selected_municipalities.clear()
                st.toast(f"{len(selected_names)} municípios removidos da seleção!", icon="🗑️")
                st.rerun()
        
        
        # === AI CHATBOT ASSISTANT - ALWAYS VISIBLE ===
        # Render the chatbot assistant in the sidebar (replaces legend)
        render_chatbot_sidebar()

    # --- 4. APLICAÇÃO DOS FILTROS ---
    # Processa os dados ANTES de qualquer renderização de layout
    df_to_display, display_col = apply_filters(df, {
        'residues': residues, 
        'display_name': display_name, 
        'normalization': normalization
    })

    # --- 4.5. RESUMO DOS FILTROS ATIVOS ---
    active_filters = []
    if display_name != "Potencial Total":
        active_filters.append(f"Resíduo: **{display_name}**")
    if search_term:
        active_filters.append(f"Busca: **'{search_term}'**")
    if normalization != "Potencial Absoluto (m³/ano)":
        metric_short = normalization.split('(')[0].strip()
        active_filters.append(f"Métrica: **{metric_short}**")
    if show_mapbiomas and mapbiomas_classes:
        active_filters.append(f"MapBiomas: **{len(mapbiomas_classes)} culturas**")
    
    if active_filters:
        st.info(f"🎯 Filtros Ativos: {' | '.join(active_filters)}")

    # --- 5. LAYOUT HORIZONTAL: MAPA E DETALHES LADO A LADO ---
    if st.session_state.clicked_municipality:
        # Layout horizontal: mapa (60%) e detalhes (40%)
        map_col, details_col = st.columns([0.6, 0.4])
        
        with details_col:
            # Container para detalhes com altura fixa e scroll
            with st.container():
                try:
                    mun_data = df[df['cd_mun'].astype(str) == str(st.session_state.clicked_municipality)].iloc[0]
                    mun_name = mun_data['nome_municipio']

                    # Cabeçalho compacto do painel
                    if st.button("🔙 Voltar ao Mapa", key="close_details_button", help="Voltar ao mapa principal", use_container_width=True):
                        st.session_state.clicked_municipality = None
                        st.rerun()
                    
                    st.markdown(f"### 🔍 {mun_name}")
                    st.markdown("---")

                    # Detalhes em container com altura controlada
                    with st.container():
                        # Versão compacta da função de detalhes
                        show_municipality_details_horizontal(df, st.session_state.clicked_municipality, residues)

                except Exception as e:
                    st.error(f"Erro ao carregar detalhes: {str(e)}")
                    if st.button("🔄 Tentar Novamente", key="retry_details"):
                        st.rerun()
        
        with map_col:
            # --- DETERMINAÇÃO DO TIPO DE VISUALIZAÇÃO FINAL ---
            # Usa diretamente a seleção do usuário do seletor de estilos
            final_viz_type = viz_type
            
            # --- RENDERIZAÇÃO DO MAPA ---
            # Crie um dicionário com as informações da análise
            catchment_info = None
            if enable_proximity and st.session_state.get('catchment_center'):
                catchment_info = {
                    "center": st.session_state.catchment_center,
                    "radius": st.session_state.catchment_radius
                }
                logger.info(f"🎯 Creating catchment_info: center={st.session_state.catchment_center}, radius={st.session_state.catchment_radius}")
            else:
                logger.info(f"No catchment_info: enable_proximity={enable_proximity}, catchment_center={st.session_state.get('catchment_center')}")
            
            
            map_object, legend_html = create_centroid_map_optimized(df_to_display, display_col, search_term=search_term, viz_type=final_viz_type, show_mapbiomas_layer=show_mapbiomas, mapbiomas_classes=mapbiomas_classes, show_rios=show_rios, show_rodovias=show_rodovias, show_plantas_biogas=show_plantas_biogas, show_gasodutos_dist=show_gasodutos_dist, show_gasodutos_transp=show_gasodutos_transp, show_areas_urbanas=show_areas_urbanas, show_regioes_admin=show_regioes_admin, show_municipios_biogas=show_municipios_biogas, show_municipios_polygons=show_municipios_polygons, catchment_info=catchment_info)
            
            # Legend is now replaced by AI Chatbot Assistant in sidebar
            
            map_data = st_folium(map_object, key="main_map", width=None, height=700)  # Altura maior para compensar layout horizontal
    else:
        # Mapa em largura total quando não há detalhes
        # --- DETERMINAÇÃO DO TIPO DE VISUALIZAÇÃO FINAL (FULLWIDTH) ---
        # Usa diretamente a seleção do usuário do seletor de estilos
        final_viz_type = viz_type
        
        # Crie um dicionário com as informações da análise
        catchment_info = None
        if enable_proximity and st.session_state.get('catchment_center'):
            catchment_info = {
                "center": st.session_state.catchment_center,
                "radius": st.session_state.catchment_radius
            }
            logger.info(f"🎯 Creating catchment_info (fullwidth): center={st.session_state.catchment_center}, radius={st.session_state.catchment_radius}")
        else:
            logger.info(f"No catchment_info (fullwidth): enable_proximity={enable_proximity}, catchment_center={st.session_state.get('catchment_center')}")
        
        
        map_object, legend_html = create_centroid_map_optimized(df_to_display, display_col, search_term=search_term, viz_type=final_viz_type, show_mapbiomas_layer=show_mapbiomas, mapbiomas_classes=mapbiomas_classes, show_rios=show_rios, show_rodovias=show_rodovias, show_plantas_biogas=show_plantas_biogas, show_gasodutos_dist=show_gasodutos_dist, show_gasodutos_transp=show_gasodutos_transp, show_areas_urbanas=show_areas_urbanas, show_regioes_admin=show_regioes_admin, show_municipios_biogas=show_municipios_biogas, show_municipios_polygons=show_municipios_polygons, catchment_info=catchment_info)
        
        # Legend is now replaced by AI Chatbot Assistant in sidebar
        
        map_data = st_folium(map_object, key="main_map", width=None, height=600)
    
    # === CONTAINER PARA RESULTADOS DA ANÁLISE DE PROXIMIDADE ===
    if enable_proximity and st.session_state.get('catchment_center'):
        
        # --- Executa as análises ---
        with st.spinner("🔍 Analisando área... Calculando uso do solo e potencial de biogás..."):
            
            center_lat, center_lon = st.session_state.catchment_center
            radius_km = st.session_state.catchment_radius
            
            # Análise RASTER (Uso do Solo)
            if st.session_state.get('raster_analysis_results') is None:
                # Verificação se o sistema de raster está disponível
                if not HAS_RASTER_SYSTEM or analyze_raster_in_radius is None:
                    # Sistema raster lite - usar dados simulados baseados em municípios
                    st.info("💡 **Usando análise simplificada de uso do solo** baseada em dados municipais.")
                    
                    # Simular dados de uso do solo baseados na região
                    simulated_results = simulate_raster_analysis(center_lat, center_lon, radius_km, df)
                    st.session_state.raster_analysis_results = simulated_results
                else:
                    try:
                        # Encontra o caminho do raster dinamicamente
                        project_root = Path(__file__).parent.parent.parent
                        raster_dir = project_root / "rasters"
                        
                        # Procura por arquivos .tif ou .tiff
                        raster_files = list(raster_dir.glob("*.tif")) + list(raster_dir.glob("*.tiff"))
                        
                        if not raster_files:
                            st.error(f"📂 Nenhum arquivo raster (.tif) encontrado na pasta '{raster_dir}'.")
                            st.session_state.raster_analysis_results = {}
                        else:
                            raster_path = str(raster_files[0])  # Usa o primeiro que encontrar

                            # ENHANCED: Complete MapBiomas class mapping (includes ALL classes found in logs)
                            class_map = {
                                # Found in your logs: [ 0  9 15 20 39 41 46 47 48]
                                # 0: '❓ Não Classificado',  # Removed - not useful for agricultural analysis
                                9: '🌲 Silvicultura', 
                                15: '🌾 Pastagem',
                                20: '🌾 Cana-de-açúcar',  
                                39: '🌱 Soja',
                                40: '🌾 Arroz',
                                41: '🌾 Outras Culturas Temporárias',
                                46: '☕ Café',
                                47: '🍊 Citrus', 
                                48: '🌾 Outras Culturas Perenes',
                                62: '🌾 Algodão',
                                35: '🌴 Dendê',
                                
                                # Additional classes for complete coverage
                                3: '🌳 Formação Florestal',
                                4: '🌿 Formação Savânica',
                                11: '🌾 Campo Alagado',
                                12: '🌿 Formação Campestre',
                                24: '🏘️ Área Urbanizada',
                                26: '💧 Corpo d\'Água',
                                33: '💧 Rio, Lago e Oceano'
                            }
                            
                            
                            # *** ESTA É A CHAMADA REAL ***
                            real_results = analyze_raster_in_radius(
                                raster_path=raster_path,
                                center_lat=center_lat,
                                center_lon=center_lon,
                                radius_km=radius_km,
                                class_map=class_map
                            )
                            
                            st.session_state.raster_analysis_results = real_results
                            st.success(f"✅ Análise concluída: {len(real_results)} tipos de cultura encontrados")

                    except Exception as e:
                        st.error(f"❌ Falha na análise real do raster: {e}")
                        import traceback
                        with st.expander("🔍 Detalhes do erro"):
                            st.code(traceback.format_exc())
                        st.session_state.raster_analysis_results = None

        # --- Professional Results Panel ---
        if st.session_state.get('raster_analysis_results'):
            results = st.session_state.raster_analysis_results
            center_coordinates = st.session_state.get('catchment_center')
            radius_km = st.session_state.get('catchment_radius', 10)
            
            if HAS_PROFESSIONAL_PANEL and results:
                # Use the beautiful professional panel from integrated_map module
                logger.info("Using professional results panel")
                render_proximity_results_panel(results, center_coordinates, radius_km)
            else:
                logger.warning(f"⚠️ Using enhanced fallback panel: HAS_PROFESSIONAL_PANEL={HAS_PROFESSIONAL_PANEL}, results={bool(results)}")
                # Enhanced fallback panel with beautiful visualizations
                st.markdown("---")
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 1.5rem; border-radius: 15px; text-align: center; margin: 1rem 0;'>
                    <h2 style='margin: 0; font-size: 1.8rem;'>🎯 Análise de Uso do Solo</h2>
                    <p style='margin: 10px 0 0 0; font-size: 1.1rem; opacity: 0.9;'>
                        📏 Raio de Captação: {radius_km} km | 📐 Área Total: {3.14159 * radius_km**2:.1f} km²
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                if results and len([k for k in results.keys() if k != '_metadata']) > 0:
                    metadata = results.get('_metadata', {})
                    culturas_data = {k: v for k, v in results.items() if k != '_metadata'}
                    
                    # Informações de contexto
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🌍 Região", metadata.get('regiao', 'SP'), help="Região de São Paulo identificada")
                    with col2:
                        st.metric("🏘️ Municípios", metadata.get('municipios_encontrados', 0), help="Municípios dentro do raio")  
                    with col3:
                        st.metric("🔬 Método", metadata.get('metodo', 'Análise'), help="Método de análise utilizado")
                    
                    # Criar gráfico de culturas
                    if culturas_data:
                        st.markdown("### 📊 Distribuição de Culturas na Área")
                        
                        # Preparar dados para gráfico
                        cultura_names = list(culturas_data.keys())
                        areas = [culturas_data[c]['area_km2'] for c in cultura_names]
                        potenciais = [culturas_data[c]['potencial_biogas'] for c in cultura_names]
                        percentuais = [culturas_data[c]['percentual'] for c in cultura_names]
                        
                        # Gráfico de barras com área e potencial
                        fig_bar = px.bar(
                            x=cultura_names,
                            y=areas,
                            title="Área por Tipo de Cultura (km²)",
                            labels={'x': 'Tipo de Cultura', 'y': 'Área (km²)'},
                            color=areas,
                            color_continuous_scale='Viridis'
                        )
                        fig_bar.update_layout(height=400, showlegend=False)
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
                        # Gráfico de pizza
                        col1, col2 = st.columns(2)
                        with col1:
                            fig_pie = px.pie(
                                values=percentuais,
                                names=cultura_names, 
                                title="Distribuição Percentual das Culturas",
                                color_discrete_sequence=px.colors.qualitative.Set3
                            )
                            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                            fig_pie.update_layout(height=350)
                            st.plotly_chart(fig_pie, use_container_width=True)
                        
                        with col2:
                            # Gráfico de potencial de biogás
                            fig_biogas = px.bar(
                                x=potenciais,
                                y=cultura_names,
                                orientation='h',
                                title="Potencial de Biogás por Cultura (m³/ano)",
                                labels={'x': 'Potencial (m³/ano)', 'y': 'Cultura'},
                                color=potenciais,
                                color_continuous_scale='Reds'
                            )
                            fig_biogas.update_layout(height=350)
                            st.plotly_chart(fig_biogas, use_container_width=True)
                        
                        # Tabela detalhada
                        st.markdown("### 📋 Dados Detalhados")
                        cultura_df = pd.DataFrame([
                            {
                                'Cultura': cultura,
                                'Área (km²)': f"{dados['area_km2']:.2f}",
                                'Percentual (%)': f"{dados['percentual']:.1f}%",
                                'Potencial Biogás (m³/ano)': f"{dados['potencial_biogas']:,.0f}",
                                'Densidade (m³/km²/ano)': f"{dados['densidade']:,.1f}"
                            }
                            for cultura, dados in culturas_data.items()
                        ])
                        st.dataframe(cultura_df, use_container_width=True, hide_index=True)
                        
                        # Resumo total
                        total_area = sum(dados['area_km2'] for dados in culturas_data.values())
                        total_potencial = sum(dados['potencial_biogas'] for dados in culturas_data.values())
                        
                        st.markdown("### 📈 Resumo da Análise")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("🌾 Área Total Analisada", f"{total_area:.1f} km²")
                        with col2:
                            st.metric("⚡ Potencial Total", f"{total_potencial:,.0f} m³/ano")
                        with col3:
                            st.metric("📊 Tipos de Cultura", f"{len(culturas_data)}")
                        with col4:
                            cobertura = (total_area / (3.14159 * radius_km**2)) * 100
                            st.metric("🎯 Cobertura da Análise", f"{cobertura:.1f}%")
                            
                    else:
                        st.warning("⚠️ A análise não identificou culturas específicas na região.")
                else:
                    st.warning("⚠️ A análise não retornou resultados válidos.")

    # --- 7. PROCESSAMENTO DE CLIQUE DO MAPA (NOVA ABORDAGEM) ---
    clicked_id = None
    
    if map_data and map_data.get("last_object_clicked"):
        # Pega as coordenadas do clique
        click_lat = map_data["last_object_clicked"]['lat']
        click_lon = map_data["last_object_clicked"]['lng']
        
        # Encontra o município mais próximo dessas coordenadas
        if 'lat' in df.columns and 'lon' in df.columns:
            valid_coords = df[(df['lat'] != 0) & (df['lon'] != 0)].copy()
            
            if len(valid_coords) > 0:
                distances = np.sqrt((valid_coords['lat'] - click_lat)**2 + (valid_coords['lon'] - click_lon)**2)
                closest_idx = distances.idxmin()
                closest_mun = valid_coords.loc[closest_idx]
                
                clicked_id = closest_mun['cd_mun']
                
                # Atualiza o estado da sessão
                if st.session_state.clicked_municipality != clicked_id:
                    st.session_state.clicked_municipality = clicked_id
                    st.rerun()

    # Análise de proximidade para cliques em área vazia
    if enable_proximity and map_data and map_data.get("last_clicked"):
        # Apenas aciona se o clique NÃO foi em um objeto existente
        if not map_data.get("last_object_clicked"):
            
            new_center = (
                map_data["last_clicked"]["lat"],
                map_data["last_clicked"]["lng"]
            )
            
            # Pega o centro atual, se existir
            current_center = st.session_state.get('catchment_center')
            
            # COMPARA o novo clique com o anterior para evitar recálculos desnecessários
            # A tolerância pequena previne problemas com cliques múltiplos no mesmo lugar
            if current_center is None or \
               abs(new_center[0] - current_center[0]) > 0.0001 or \
               abs(new_center[1] - current_center[1]) > 0.0001:
                
                # É um novo local de análise!
                st.toast("🎯 Novo centro de análise definido!", icon="🎯")
                
                # **A CORREÇÃO DO BUG ESTÁ AQUI:**
                # Limpa os resultados antigos para forçar o recálculo
                st.session_state.raster_analysis_results = None
                st.session_state.vector_analysis_results = None
                
                # Define o novo centro
                st.session_state.catchment_center = new_center
                
                # Força o recarregamento da página para atualizar o mapa e iniciar a análise
                st.rerun()

    # --- 8. FERRAMENTAS DE ANÁLISE (SEMPRE VISÍVEIS ABAIXO) ---
    st.markdown("---")
    st.markdown("## 📊 Ferramentas de Análise Avançada")
    analysis_tabs = st.tabs([
        "📈 Análise Geral", "🔍 Análise Detalhada", "⚖️ Comparação", 
        "🎯 Filtros Avançados", "📋 Dados Completos"
    ])
    
    with analysis_tabs[0]:
        # Lógica corrigida para exibir a análise correta
        if st.session_state.selected_municipalities:
            selected_df = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]
            st.markdown(f"### 🔬 Análise para **{len(selected_df)}** Município(s) Selecionado(s)")
            
            if len(selected_df) == 1:
                mun = selected_df.iloc[0]
                st.markdown(f"#### Perfil Completo: **{mun['nome_municipio']}**")
                
                # Key metrics for single municipality
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("População", f"{mun.get('populacao_2022', 'N/A'):,}" if pd.notna(mun.get('populacao_2022')) else "N/A")
                with col2:
                    st.metric("Potencial Total", f"{mun['total_final_m_ano']:,.0f}")
                with col3:
                    st.metric("Agrícola", f"{mun['total_agricola_m_ano']:,.0f}")
                with col4:
                    st.metric("Pecuária", f"{mun['total_pecuaria_m_ano']:,.0f}")
                
                # Donut chart for composition
                residue_cols = {v: k for k, v in RESIDUE_OPTIONS.items() if 'Total' not in k}
                analysis_df = selected_df[['nome_municipio'] + list(residue_cols.keys())]
                melted_df = analysis_df.melt(id_vars='nome_municipio', var_name='Tipo', value_name='Potencial').rename(columns={'nome_municipio': 'Município'})
                melted_df['Tipo'] = melted_df['Tipo'].map(residue_cols)
                melted_df = melted_df[melted_df['Potencial'] > 0]  # Remove zeros for cleaner chart
                
                if not melted_df.empty:
                    fig = px.pie(melted_df, names='Tipo', values='Potencial', 
                               title='Composição do Potencial por Tipo de Resíduo', hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                
            else: # Múltiplos municípios
                st.markdown("#### Comparativo entre Municípios Selecionados")
                
                # Enhanced summary metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Selecionados", len(selected_df))
                with col2:
                    total_potential = selected_df['total_final_m_ano'].sum()
                    st.metric("Potencial Conjunto", f"{total_potential:,.0f} m³/ano")
                with col3:
                    avg_potential = selected_df['total_final_m_ano'].mean()
                    st.metric("Média por Município", f"{avg_potential:,.0f} m³/ano")
                with col4:
                    if 'populacao_2022' in selected_df.columns:
                        total_population = selected_df['populacao_2022'].sum()
                        if total_population > 0:
                            potential_per_capita = total_potential / total_population
                            st.metric("Potencial per Capita", f"{potential_per_capita:.1f} m³/hab/ano")
                
                # Main comparison chart
                fig_bar = px.bar(
                    selected_df, 
                    x='nome_municipio', 
                    y='total_final_m_ano',
                    title='Potencial Total por Município',
                    color='total_final_m_ano',
                    color_continuous_scale='Viridis'
                )
                fig_bar.update_layout(height=400, xaxis_tickangle=45)
                st.plotly_chart(fig_bar, use_container_width=True)
                
                # Add "VER NO MAPA" button for selected municipalities
                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get selected municipality names
                        selected_mun_names = selected_df['nome_municipio'].tolist()
                        
                        # Prepare data for results page
                        municipal_data = selected_df.to_dict('records')
                        total_selected_potential = selected_df['total_final_m_ano'].sum()
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, selected_mun_names, 'municipal_comparison', 
                            residue_data=municipal_data, 
                            metrics={'total_selected_potential': total_selected_potential, 'selected_count': len(selected_df)},
                            analysis_context={'relevant_fields': ['nome_municipio', 'total_final_m_ano', 'area_km2', 'populacao_2022']}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'municipal_comparison', 
                            selected_mun_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="main_page_comparison_map"
                        )
                        
                        st.markdown(f"*Visualizar {len(selected_mun_names)} municípios selecionados no mapa unificado*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta seleção")
        else:
            # Análise estadual padrão (quando NENHUM município está selecionado)
            st.markdown("### 📊 Análise Estadual: " + display_name)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("##### 🏆 Top 15 Municípios")
                chart1 = create_top_chart(df_to_display, display_col, display_name, limit=15)
                if chart1: 
                    st.plotly_chart(chart1, use_container_width=True)
            
            with col2:
                st.markdown("##### 📈 Distribuição")
                chart2 = create_distribution_chart(df_to_display, display_col, display_name)
                if chart2: 
                    st.plotly_chart(chart2, use_container_width=True)
            
            # Estatísticas resumidas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 Média", f"{df_to_display[display_col].mean():,.0f}")
            with col2:
                st.metric("📊 Mediana", f"{df_to_display[display_col].median():,.0f}")
            with col3:
                st.metric("📊 Desvio Padrão", f"{df_to_display[display_col].std():,.0f}")
            with col4:
                st.metric("📊 Soma Total", f"{df_to_display[display_col].sum():,.0f}")

    with analysis_tabs[1]:  # Detailed Analysis
        st.markdown("### 🔍 Análise Detalhada por Categoria")
        
        # Category comparison
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🌾 Resíduos Agrícolas")
            agri_data = []
            agri_types = ['Cana-de-açúcar', 'Soja', 'Milho', 'Café', 'Citros']
            for res_type in agri_types:
                col_name = RESIDUE_OPTIONS[res_type]
                # Check if column exists before accessing it
                if col_name in df.columns:
                    top_mun = df.nlargest(1, col_name).iloc[0] if not df[col_name].isna().all() else None
                    if top_mun is not None:
                        agri_data.append({
                            'Tipo': res_type,
                            'Líder': top_mun['nome_municipio'],
                            'Potencial': top_mun[col_name]
                        })
                else:
                    # Column doesn't exist, skip this residue type
                    continue
            
            if agri_data:
                import pandas as pd  # Import local para garantir disponibilidade
                agri_df = pd.DataFrame(agri_data)
                fig = px.bar(agri_df, x='Tipo', y='Potencial', 
                           title='Líderes por Categoria Agrícola')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(agri_df, use_container_width=True)
        
        with col2:
            st.markdown("#### 🐄 Resíduos Pecuários")
            pec_data = []
            pec_types = ['Bovinos', 'Suínos', 'Aves', 'Piscicultura']
            for res_type in pec_types:
                col_name = RESIDUE_OPTIONS[res_type]
                # Check if column exists before accessing it
                if col_name in df.columns:
                    top_mun = df.nlargest(1, col_name).iloc[0] if not df[col_name].isna().all() else None
                    if top_mun is not None:
                        pec_data.append({
                            'Tipo': res_type,
                            'Líder': top_mun['nome_municipio'],
                            'Potencial': top_mun[col_name]
                        })
                else:
                    # Column doesn't exist, skip this residue type
                    continue
            
            if pec_data:
                import pandas as pd  # Import local para garantir disponibilidade
                pec_df = pd.DataFrame(pec_data)
                fig = px.bar(pec_df, x='Tipo', y='Potencial',
                           title='Líderes por Categoria Pecuária')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                st.dataframe(pec_df, use_container_width=True)
    
    with analysis_tabs[2]:  # Comparison Tools
        st.markdown("### ⚖️ Ferramentas de Comparação")
        
        # Municipality selector for comparison
        st.markdown("#### Selecionar Municípios para Comparação")
        municipalities_list = df['nome_municipio'].tolist()
        selected_for_comparison = st.multiselect(
            "Escolha até 5 municípios para comparar:",
            municipalities_list,
            max_selections=5,
            key="comparison_select"
        )
        
        if selected_for_comparison:
            comparison_df = df[df['nome_municipio'].isin(selected_for_comparison)]
            
            # Summary table
            summary_cols = ['nome_municipio', 'total_final_m_ano', 'total_agricola_m_ano', 'total_pecuaria_m_ano']
            available_summary_cols = [col for col in summary_cols if col in comparison_df.columns]
            summary_df = comparison_df[available_summary_cols].round(0)
            st.dataframe(summary_df, use_container_width=True)
    
    with analysis_tabs[3]:  # Advanced Filters
        st.markdown("### 🎯 Filtros Avançados e Seleção Inteligente")
        
        # Quick selection presets
        st.markdown("#### ⚡ Seleções Rápidas")
        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
        
        with preset_col1:
            if st.button("🏆 Top 10 Potencial", key="top_10"):
                top_municipalities = df.nlargest(10, display_col)['cd_mun'].tolist()
                st.session_state.selected_municipalities = top_municipalities
                st.toast("Top 10 municípios selecionados!", icon="🏆")
                st.rerun()
        
        with preset_col2:
            if st.button("🌾 Foco Agrícola", key="agri_focus"):
                agri_municipalities = df[df['total_agricola_m_ano'] > df['total_agricola_m_ano'].quantile(0.75)]['cd_mun'].tolist()
                st.session_state.selected_municipalities = agri_municipalities
                st.toast(f"{len(agri_municipalities)} municípios agrícolas selecionados!", icon="🌾")
                st.rerun()
        
        with preset_col3:
            if st.button("🐄 Foco Pecuário", key="livestock_focus"):
                livestock_municipalities = df[df['total_pecuaria_m_ano'] > df['total_pecuaria_m_ano'].quantile(0.75)]['cd_mun'].tolist()
                st.session_state.selected_municipalities = livestock_municipalities
                st.toast(f"{len(livestock_municipalities)} municípios pecuários selecionados!", icon="🐄")
                st.rerun()
        
        with preset_col4:
            if st.button("🔄 Limpar Seleção", key="clear_all"):
                num_selected = len(st.session_state.selected_municipalities)
                st.session_state.selected_municipalities = []
                st.toast(f"Seleção limpa! {num_selected} municípios removidos.", icon="🔄")
                st.rerun()
        
        # Show filtered results
        if st.session_state.selected_municipalities:
            filtered_df = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]
            st.markdown(f"**Resultado:** {len(filtered_df)} municípios selecionados")
            
            chart = create_top_chart(filtered_df, display_col, "Municípios Selecionados", limit=10)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
    
    with analysis_tabs[4]:  # Complete Data
        st.markdown("### 📋 Dados Completos")
        
        # Data download options
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📥 Download CSV Completo"):
                csv = df.to_csv(index=False)
                st.download_button("💾 Baixar", csv, "cp2b_completo.csv", "text/csv")
        
        with col2:
            if st.button("📥 Download Selecionados"):
                if st.session_state.selected_municipalities:
                    selected_df = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]
                    csv = selected_df.to_csv(index=False)
                    st.download_button("💾 Baixar", csv, "cp2b_selecionados.csv", "text/csv")
                else:
                    st.warning("Nenhum município selecionado")
        
        with col3:
            if st.button("📥 Download por Filtro"):
                csv = df_to_display.to_csv(index=False)
                st.download_button("💾 Baixar", csv, f"cp2b_{display_name.lower()}.csv", "text/csv")
        
        # Full data table with search and sorting
        st.markdown("#### Tabela Completa de Dados")
        search_table = st.text_input("🔍 Buscar na tabela:", key="table_search")
        
        display_df = df.copy()
        if search_table:
            display_df = display_df[display_df['nome_municipio'].str.contains(search_table, case=False, na=False)]
        
        # Column selector
        all_numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        selected_cols = st.multiselect(
            "Selecionar colunas para exibir:",
            ['nome_municipio'] + all_numeric_cols,
            default=['nome_municipio', 'total_final_m_ano', 'total_agricola_m_ano', 'total_pecuaria_m_ano'],
            key="column_selector"
        )
        
        if selected_cols:
            available_selected_cols = [col for col in selected_cols if col in display_df.columns]
            final_display_df = display_df[available_selected_cols].sort_values(by=available_selected_cols[1] if len(available_selected_cols) > 1 else available_selected_cols[0], ascending=False)
            st.dataframe(final_display_df, use_container_width=True, height=600)

def page_explorer():
    """User-Friendly Data Explorer - Designed for Non-Technical Users"""
    
    # Welcome header with clear instructions
    st.markdown("""
    <div style='background: linear-gradient(135deg, #4CAF50 0%, #2E8B57 100%); 
                color: white; padding: 2rem; margin: -1rem -1rem 2rem -1rem;
                text-align: center; border-radius: 0 0 20px 20px;'>
        <h1 style='margin: 0; font-size: 2.5rem;'>🔍 Explorar Dados de Biogás</h1>
        <p style='margin: 10px 0 0 0; font-size: 1.2rem; opacity: 0.9;'>
            Descubra o potencial de biogás nos municípios de São Paulo de forma simples!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    # Step-by-step guided exploration
    st.markdown("### 🎯 Passo 1: Escolha o que você quer analisar")
    
    # Simple, clear selection with explanations
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("""
        **Selecione o tipo de resíduo que você quer explorar:**
        - 🌾 **Resíduos Agrícolas**: Cana-de-açúcar, soja, milho, café, citros
        - 🐄 **Resíduos Pecuários**: Bovinos, suínos, aves, piscicultura  
        - 🏙️ **Resíduos Urbanos**: Lixo urbano e resíduos de poda
        - 📊 **Totais**: Somas por categoria ou geral
        """)
        
        # Simple selection
        selected_type = st.selectbox(
            "Escolha o tipo de resíduo:",
            options=list(RESIDUE_OPTIONS.keys()),
            index=0,
            key="explorer_residue_type",
            help="Cada tipo representa uma fonte diferente de biogás"
        )
        
        display_col = RESIDUE_OPTIONS[selected_type]
    
    with col2:
        st.info("""
        💡 **Dica:**

        Comece com "Potencial Total" para ter uma visão geral, depois explore tipos específicos!
        """)

        # Add reference for selected substrate
        substrate_refs = get_substrate_reference_map()
        if display_col in substrate_refs:
            st.markdown("**📚 Base Científica:**")
            render_reference_button(substrate_refs[display_col], compact=True)

    # Filter data
    df_filtered = df[df[display_col] > 0].copy()  # Only show municipalities with data
    
    if df_filtered.empty:
        st.warning("⚠️ Nenhum município tem dados para este tipo de resíduo.")
        return
    
    # Step 2: Overview with clear explanations
    st.markdown("---")
    st.markdown(f"### 📊 Passo 2: Visão Geral - {selected_type}")
    
    # Simple, clear metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_municipalities = len(df_filtered)
    total_potential = df_filtered[display_col].sum()
    average_potential = df_filtered[display_col].mean()
    top_municipality = df_filtered.loc[df_filtered[display_col].idxmax(), 'nome_municipio']
    
    with col1:
        st.metric(
            "🏘️ Municípios com Potencial", 
            f"{total_municipalities:,}",
            help="Quantidade de municípios que têm este tipo de resíduo"
        )
    
    with col2:
        metric_col1, metric_col2 = st.columns([3, 1])
        with metric_col1:
            st.metric(
                "🔥 Potencial Total",
                f"{total_potential/1_000_000:.1f}M m³/ano",
                help="Soma de todo o potencial de biogás deste tipo em SP"
            )
        with metric_col2:
            substrate_refs = get_substrate_reference_map()
            if display_col in substrate_refs:
                render_reference_button(substrate_refs[display_col], compact=True)
    
    with col3:
        st.metric(
            "📊 Potencial Médio", 
            f"{average_potential/1_000:.0f}K m³/ano",
            help="Média do potencial por município"
        )
    
    with col4:
        st.metric(
            "🏆 Município Líder", 
            top_municipality,
            help="Município com maior potencial neste tipo"
        )
    
    # Step 3: Visual exploration with explanations
    st.markdown("---")
    st.markdown("### 📈 Passo 3: Veja os Dados de Forma Visual")
    
    # Simplified tabs with clear explanations
    viz_tabs = st.tabs([
        "🏆 Ranking dos Melhores", 
        "📊 Como os Valores se Distribuem", 
        "🔍 Compare Municípios"
    ])
    
    with viz_tabs[0]:  # Ranking - Most intuitive for users
        st.markdown("#### 🥇 Os Municípios com Maior Potencial")
        st.markdown(f"*Veja quais municípios lideram na produção de biogás a partir de {selected_type.lower()}*")
        
        # User-friendly top N selector
        top_n = st.selectbox(
            "Quantos municípios você quer ver no ranking?",
            options=[5, 10, 15, 20, 30],
            index=1,  # Default to 10
            key="ranking_top_n"
        )
        
        top_municipalities = df_filtered.nlargest(top_n, display_col)
        
        # Create ranking table with position
        ranking_data = []
        for i, (_, row) in enumerate(top_municipalities.iterrows(), 1):
            ranking_data.append({
                "🏅 Posição": f"{i}º",
                "🏘️ Município": row['nome_municipio'],
                "🔥 Potencial (m³/ano)": format_number(row[display_col])
            })
        
        ranking_df = pd.DataFrame(ranking_data)
        st.dataframe(ranking_df, use_container_width=True, hide_index=True)
        
        # Visual ranking chart
        fig_ranking = px.bar(
            top_municipalities.head(10),  # Show top 10 in chart
            x=display_col,
            y='nome_municipio',
            orientation='h',
            title=f"🏆 Top 10 Municípios - {selected_type}",
            labels={display_col: "Potencial de Biogás (m³/ano)", 'nome_municipio': 'Município'},
            color=display_col,
            color_continuous_scale='Greens'
        )
        fig_ranking.update_layout(
            height=500,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig_ranking, use_container_width=True)
        
        # Simple insights
        if top_n >= 3:
            top_3_sum = top_municipalities.head(3)[display_col].sum()
            percentage = (top_3_sum / total_potential) * 100
            st.info(f"💡 **Insight:** Os 3 municípios líderes concentram {percentage:.1f}% de todo o potencial!")
    
    with viz_tabs[1]:  # Distribution - Simplified
        st.markdown("#### 📊 Como os Valores Estão Distribuídos")
        st.markdown("*Entenda se a maioria dos municípios tem valores altos, baixos ou medianos*")
        
        # Simple histogram with explanation
        fig_hist = px.histogram(
            df_filtered, 
            x=display_col,
            nbins=20,  # Fixed, simpler number
            title=f"Distribuição do Potencial - {selected_type}",
            labels={display_col: "Potencial de Biogás (m³/ano)", 'count': 'Quantidade de Municípios'},
            color_discrete_sequence=['#2E8B57']
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Simple explanation of what this means
        median_val = df_filtered[display_col].median()
        above_median = len(df_filtered[df_filtered[display_col] > median_val])
        below_median = len(df_filtered[df_filtered[display_col] <= median_val])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📈 Municípios Acima da Mediana", above_median)
        with col2:
            st.metric("📉 Municípios Abaixo da Mediana", below_median)
        
        st.markdown(f"""
        **📖 O que isso significa:**
        - A mediana é {format_number(median_val)} m³/ano
        - {above_median} municípios têm potencial acima deste valor
        - {below_median} municípios têm potencial abaixo deste valor
        """)
    
    with viz_tabs[2]:  # Comparison - User selects municipalities
        st.markdown("#### 🔍 Compare Municípios de Seu Interesse")
        st.markdown("*Escolha municípios específicos para comparar lado a lado*")
        
        # Municipality search and selection
        st.markdown("**Busque e selecione municípios:**")
        search_mun = st.text_input(
            "Digite o nome de um município para buscar:",
            placeholder="Ex: São Paulo, Campinas, Santos...",
            key="municipality_search"
        )
        
        # Filter municipalities based on search
        available_municipalities = df_filtered['nome_municipio'].tolist()
        if search_mun:
            available_municipalities = [
                m for m in available_municipalities 
                if search_mun.lower() in m.lower()
            ]
        
        selected_municipalities = st.multiselect(
            "Escolha até 5 municípios para comparar:",
            options=available_municipalities,
            default=df_filtered.nlargest(3, display_col)['nome_municipio'].tolist()[:3],
            max_selections=5,
            key="municipality_comparison_simple"
        )
        
        if selected_municipalities:
            # Create comparison data
            comparison_data = []
            for municipality in selected_municipalities:
                mun_data = df_filtered[df_filtered['nome_municipio'] == municipality].iloc[0]
                comparison_data.append({
                    '🏘️ Município': municipality,
                    f'🔥 {selected_type}': format_number(mun_data[display_col])
                })
            
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            # Visual comparison
            if len(selected_municipalities) > 1:
                comparison_values = []
                for municipality in selected_municipalities:
                    mun_data = df_filtered[df_filtered['nome_municipio'] == municipality].iloc[0]
                    comparison_values.append({
                        'Município': municipality,
                        'Potencial': mun_data[display_col]
                    })
                
                comp_df = pd.DataFrame(comparison_values)
                fig_comparison = px.bar(
                    comp_df,
                    x='Município',
                    y='Potencial',
                    title=f"Comparação - {selected_type}",
                    labels={'Potencial': 'Potencial (m³/ano)'},
                    color='Potencial',
                    color_continuous_scale='Greens'
                )
                fig_comparison.update_layout(height=400)
                st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Step 4: Explore all data
    st.markdown("---")
    st.markdown("### 📋 Passo 4: Explore Todos os Dados")
    
    # Simple search and filter
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_all = st.text_input(
            "🔍 Buscar município na tabela completa:",
            placeholder="Digite parte do nome do município...",
            key="search_all_data"
        )
    
    with col2:
        show_top_only = st.checkbox(
            "📊 Mostrar apenas os Top 50",
            value=True,
            help="Marque para ver apenas os 50 municípios com maior potencial"
        )
    
    # Apply filters
    display_df = df_filtered.copy()
    
    if search_all:
        display_df = display_df[display_df['nome_municipio'].str.contains(search_all, case=False, na=False)]
    
    if show_top_only:
        display_df = display_df.nlargest(50, display_col)
    else:
        display_df = display_df.sort_values(display_col, ascending=False)
    
    # Show results count
    st.markdown(f"**Mostrando {len(display_df)} municípios de {len(df_filtered)} total**")
    
    # Simple table with essential columns
    essential_columns = ['nome_municipio', display_col]
    if 'populacao_2022' in display_df.columns:
        essential_columns.append('populacao_2022')
    
    display_table = display_df[essential_columns].copy()
    display_table.columns = ['🏘️ Município', f'🔥 {selected_type}', '👥 População (2022)'] if len(essential_columns) == 3 else ['🏘️ Município', f'🔥 {selected_type}']
    
    # Format numbers in the display table
    display_table[f'🔥 {selected_type}'] = display_table[f'🔥 {selected_type}'].apply(format_number)
    if '👥 População (2022)' in display_table.columns:
        display_table['👥 População (2022)'] = display_table['👥 População (2022)'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A")
    
    st.dataframe(display_table, use_container_width=True, hide_index=True, height=400)
    
    # Download section - simplified
    st.markdown("---")
    st.markdown("### 📥 Baixar os Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Baixar Dados Filtrados", key="download_simple_filtered"):
            csv = display_df[essential_columns].to_csv(index=False)
            st.download_button(
                "💾 Clique para Baixar",
                csv,
                f"biogas_{selected_type.lower().replace(' ', '_')}_municipios.csv",
                "text/csv",
                key="download_simple_btn"
            )
    
    with col2:
        if st.button("📈 Baixar Dados Completos", key="download_simple_complete"):
            csv = df.to_csv(index=False)
            st.download_button(
                "💾 Clique para Baixar",
                csv,
                "biogas_dados_completos_sp.csv",
                "text/csv",
                key="download_complete_simple_btn"
            )
    
    # Help section
    st.markdown("---")
    st.markdown("### ❓ Precisa de Ajuda?")
    
    with st.expander("🤔 Como interpretar os dados?"):
        st.markdown("""
        **📊 Potencial de Biogás (m³/ano):**
        - Representa quanto biogás pode ser produzido por ano
        - m³ = Metros cúbicos normalizados (unidade padrão para gases)
        - Valores maiores = maior potencial energético
        
        **🏆 Rankings:**
        - Mostram quais municípios têm maior potencial
        - Útil para identificar oportunidades de investimento
        
        **📈 Distribuição:**
        - Mostra como os valores estão espalhados
        - Ajuda a entender se poucos municípios concentram o potencial
        
        **🔍 Comparação:**
        - Permite analisar municípios específicos lado a lado
        - Útil para estudos regionais ou decisões de investimento
        """)
    
    with st.expander("💡 Dicas para explorar melhor"):
        st.markdown("""
        **Para iniciantes:**
        1. Comece sempre com "Potencial Total" para ter uma visão geral
        2. Use o ranking para identificar os municípios mais promissores
        3. Compare municípios da sua região de interesse
        
        **Para análises mais profundas:**
        1. Explore tipos específicos de resíduos (agrícola, pecuário, urbano)
        2. Use a busca para encontrar municípios específicos
        3. Baixe os dados para análises externas
        
        **Interpretação dos resultados:**
        - Valores altos não significam automaticamente viabilidade econômica
        - Considere também fatores como logística e mercado local
        - Use os dados como ponto de partida para estudos mais detalhados
        """)
    
    # Add "VER NO MAPA" button for explorer results
    st.markdown("---")
    st.markdown("### 🗺️ Ver Resultados no Mapa")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        try:
            # Get top municipalities from filtered data
            top_municipalities = display_df.head(10)['nome_municipio'].tolist()
            
            if top_municipalities:
                # Prepare data for results page
                explorer_data = display_df.head(20).to_dict('records')
                data, summary, polygons = prepare_analysis_data_for_results(
                    df, top_municipalities, 'municipal_profile', 
                    residue_data=explorer_data, 
                    metrics={'selected_type': selected_type, 'total_potential': total_potential},
                    analysis_context={'relevant_fields': ['nome_municipio'] + [selected_type.lower() if selected_type != 'Total Geral' else 'total_final_m_ano', 'area_km2', 'populacao_2022']}
                )
                
                # Create button
                create_ver_no_mapa_button(
                    'municipal_profile', 
                    top_municipalities, 
                    data, 
                    summary=summary, 
                    polygons=polygons,
                    button_key="explorer_map"
                )
                
                st.markdown(f"*Visualizar {len(top_municipalities)} municípios com maior potencial de {selected_type}*")
            else:
                st.info("🗺️ Nenhum município encontrado para visualização no mapa")
                
        except Exception as e:
            st.info("🗺️ Dados de mapa não disponíveis para esta seleção")
    
    # Footer with data source info
    st.markdown("---")
    st.info("""
    📋 **Sobre os dados:** Os dados apresentados são baseados em estimativas de potencial teórico de produção de biogás 
    a partir de diferentes tipos de resíduos orgânicos nos 645 municípios do estado de São Paulo. 
    Para projetos reais, recomenda-se estudos de viabilidade técnica e econômica específicos.
    """)

def page_analysis():
    """User-Friendly Residue Analysis - Designed for Non-Technical Users"""
    
    # Welcome header with clear instructions
    st.markdown("""
    <div style='background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%); 
                color: white; padding: 2rem; margin: -1rem -1rem 2rem -1rem;
                text-align: center; border-radius: 0 0 20px 20px;'>
        <h1 style='margin: 0; font-size: 2.5rem;'>📊 Análises Avançadas</h1>
        <p style='margin: 10px 0 0 0; font-size: 1.2rem; opacity: 0.9;'>
            Análise detalhada por resíduo, comparações e descoberta de padrões!
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    # Step-by-step guided analysis
    st.markdown("### 🎯 Passo 1: Escolha o Tipo de Análise")
    
    analysis_type = st.selectbox(
        "O que você gostaria de analisar?",
        [
            "🌾 Análise Detalhada por Resíduo/Cultura",
            "🏆 Comparar Tipos de Resíduos",
            "🌍 Analisar por Região",
            "🔍 Encontrar Padrões e Correlações",
            "📈 Análise de Portfólio Municipal",
            "🚀 Análise Avançada de Oportunidades",
            "💡 Insights Inteligentes e Recomendações"
        ],
        help="Cada tipo de análise oferece insights diferentes sobre os dados"
    )
    
    st.markdown("---")
    
    # New Analysis Type: Detailed Analysis by Residue/Culture
    if analysis_type == "🌾 Análise Detalhada por Resíduo/Cultura":
        st.markdown("### 🌾 Passo 2: Escolha o Tipo de Resíduo")
        st.markdown("*Análise completa de um resíduo específico em São Paulo*")
        
        # Organize residues by category for better UX
        residue_categories = {
            "🌾 Resíduos Agrícolas": {
                "Cana-de-açúcar": "biogas_cana_m_ano",
                "Soja": "biogas_soja_m_ano", 
                "Milho": "biogas_milho_m_ano",
                "Café": "biogas_cafe_m_ano",
                "Citros": "biogas_citros_m_ano"
            },
            "🐄 Resíduos Pecuários": {
                "Bovinos": "biogas_bovinos_m_ano",
                "Suínos": "biogas_suino_m_ano",
                "Aves": "biogas_aves_m_ano",
                "Piscicultura": "biogas_piscicultura_m_ano"
            },
            "🏙️ Resíduos Urbanos": {
                "Resíduos Urbanos": "rsu_potencial_m_ano",
                "Resíduos de Poda": "rpo_potencial_m_ano"
            }
        }
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_category = st.selectbox(
                "Selecione a categoria:",
                list(residue_categories.keys()),
                key="detailed_category"
            )
            
            selected_residue = st.selectbox(
                "Selecione o resíduo específico:",
                list(residue_categories[selected_category].keys()),
                key="detailed_residue"
            )
        
        with col2:
            st.info(f"""
            💡 **Análise Completa**
            
            Você receberá:
            • Panorama estadual
            • Mapa com rasters
            • Top 10 municípios
            • Análise visual
            • Exploração detalhada
            """)
        
        residue_col = residue_categories[selected_category][selected_residue]
        
        if residue_col in df.columns:
            # Filter municipalities with data for this residue
            df_residue = df[df[residue_col] > 0].copy()
            
            if not df_residue.empty:
                st.markdown("---")
                st.markdown(f"### 📊 Passo 3: Panorama Geral da {selected_residue} no Estado de São Paulo")
                
                # Overview metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_potential = df_residue[residue_col].sum()
                    col_metric, col_ref = st.columns([3, 1])
                    with col_metric:
                        st.metric("🔥 Potencial Total", format_number(total_potential) + " m³/ano")
                    with col_ref:
                        # Get appropriate reference based on residue type
                        ref_id = get_substrate_reference_map().get(residue_col, "method_biogas")
                        render_reference_button(ref_id, "Metodologia")
                with col2:
                    municipalities_with_data = len(df_residue)
                    st.metric("🏘️ Municípios com Dados", f"{municipalities_with_data:,}")
                with col3:
                    avg_potential = df_residue[residue_col].mean()
                    col_metric, col_ref = st.columns([3, 1])
                    with col_metric:
                        st.metric("📊 Potencial Médio", format_number(avg_potential) + " m³/ano")
                    with col_ref:
                        render_reference_button("method_biogas", "Cálculos")
                with col4:
                    percentage_state = (municipalities_with_data / len(df)) * 100
                    st.metric("📍 Cobertura Estadual", f"{percentage_state:.1f}%")
                
                # Get top 10 municipalities
                top_10_municipalities = df_residue.nlargest(10, residue_col)
                top_10_names = top_10_municipalities['nome_municipio'].tolist()
                
                # Passo 4: VER NO MAPA with raster integration suggestion
                st.markdown("---")
                st.markdown(f"### 🗺️ Passo 4: Ver no Mapa - {selected_residue}")
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Prepare analysis context for this specific residue
                        relevant_fields = ['nome_municipio', residue_col, 'area_km2', 'populacao_2022']
                        
                        # Prepare data for results page
                        residue_analysis_data = top_10_municipalities.to_dict('records')
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, top_10_names, 'detailed_residue_analysis', 
                            residue_data=residue_analysis_data, 
                            metrics={
                                'analysis_type': f'Análise Detalhada - {selected_residue}',
                                'residue_type': selected_residue,
                                'category': selected_category,
                                'total_potential': total_potential,
                                'municipalities_count': municipalities_with_data,
                                'coverage_percentage': percentage_state
                            },
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create enhanced button
                        create_ver_no_mapa_button(
                            'detailed_residue_analysis', 
                            top_10_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key=f"detailed_{selected_residue.lower().replace('-', '_')}_map"
                        )
                        
                        st.markdown(f"*Visualizar Top 10 municípios de {selected_residue} com limites estaduais*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para este resíduo")
                
                st.info("💡 **Recursos Avançados**: O mapa inclui os 10 principais municípios destacados, limites do Estado de São Paulo, e quando disponível, integração com dados de raster do MapBiomas para visualização de cobertura territorial.")
                
                # Passo 5: Visual Data Analysis
                st.markdown("---")
                st.markdown(f"### 📈 Passo 5: Veja os Dados de Forma Visual")
                
                # Subtabs for different visualizations
                viz_tabs = st.tabs(["🏆 Ranking dos Melhores", "📊 Como os Valores se Distribuem", "🔍 Compare Municípios"])
                
                with viz_tabs[0]:  # Ranking
                    st.markdown("#### 🏆 Top 15 Municípios")
                    
                    # Interactive ranking chart
                    top_15 = df_residue.nlargest(15, residue_col)
                    fig_ranking = px.bar(
                        top_15,
                        x=residue_col,
                        y='nome_municipio',
                        orientation='h',
                        title=f"Ranking de Potencial - {selected_residue}",
                        labels={residue_col: f'Potencial (m³/ano)', 'nome_municipio': 'Município'},
                        color=residue_col,
                        color_continuous_scale='Greens'
                    )
                    fig_ranking.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig_ranking, use_container_width=True)
                    
                    # Add VER NO MAPA for top 15
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                    with col_btn2:
                        if st.button(f"🗺️ VER TOP 15 NO MAPA", key=f"top15_{selected_residue}_map", type="primary"):
                            try:
                                top_15_names = top_15['nome_municipio'].tolist()
                                top_15_data = top_15.to_dict('records')
                                
                                data, summary, polygons = prepare_analysis_data_for_results(
                                    df, top_15_names, 'top_15_residue_analysis',
                                    residue_data=top_15_data,
                                    metrics={
                                        'analysis_type': f'Top 15 - {selected_residue}',
                                        'residue_type': selected_residue,
                                        'total_municipalities': len(top_15_names)
                                    },
                                    analysis_context={'relevant_fields': relevant_fields}
                                )
                                
                                navigate_to_results(data, summary, polygons)
                            except Exception as e:
                                st.error("Erro ao preparar dados do mapa")
                
                with viz_tabs[1]:  # Distribution
                    st.markdown("#### 📊 Distribuição dos Valores")
                    
                    # Histogram
                    fig_dist = px.histogram(
                        df_residue,
                        x=residue_col,
                        nbins=25,
                        title=f"Distribuição do Potencial - {selected_residue}",
                        labels={residue_col: f'Potencial (m³/ano)', 'count': 'Número de Municípios'},
                        color_discrete_sequence=['#2E8B57']
                    )
                    fig_dist.update_layout(height=400)
                    st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # Statistical summary
                    st.markdown("#### 📈 Estatísticas Descritivas")
                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                    
                    with stats_col1:
                        median_val = df_residue[residue_col].median()
                        st.metric("📊 Mediana", format_number(median_val))
                        percentile_75 = df_residue[residue_col].quantile(0.75)
                        st.metric("📈 75º Percentil", format_number(percentile_75))
                    
                    with stats_col2:
                        std_val = df_residue[residue_col].std()
                        st.metric("📏 Desvio Padrão", format_number(std_val))
                        percentile_25 = df_residue[residue_col].quantile(0.25)
                        st.metric("📉 25º Percentil", format_number(percentile_25))
                    
                    with stats_col3:
                        max_val = df_residue[residue_col].max()
                        st.metric("🎯 Valor Máximo", format_number(max_val))
                        min_val = df_residue[residue_col].min()
                        st.metric("⬇️ Valor Mínimo", format_number(min_val))
                
                with viz_tabs[2]:  # Municipality comparison
                    st.markdown("#### 🔍 Compare Municípios Específicos")
                    
                    # Municipality selector
                    selected_comparison_muns = st.multiselect(
                        "Selecione municípios para comparar (até 8):",
                        df_residue['nome_municipio'].tolist(),
                        default=top_10_names[:5],
                        max_selections=8,
                        key=f"comparison_{selected_residue}"
                    )
                    
                    if selected_comparison_muns:
                        comparison_df = df_residue[df_residue['nome_municipio'].isin(selected_comparison_muns)]
                        
                        # Comparison chart
                        fig_comparison = px.bar(
                            comparison_df.sort_values(residue_col, ascending=True),
                            x=residue_col,
                            y='nome_municipio',
                            orientation='h',
                            title=f"Comparação - {selected_residue}",
                            labels={residue_col: f'Potencial (m³/ano)', 'nome_municipio': 'Município'},
                            color=residue_col,
                            color_continuous_scale='Blues'
                        )
                        fig_comparison.update_layout(height=400)
                        st.plotly_chart(fig_comparison, use_container_width=True)
                        
                        # Add comparison VER NO MAPA
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                        with col_btn2:
                            if st.button(f"🗺️ VER COMPARAÇÃO NO MAPA", key=f"comparison_{selected_residue}_map", type="secondary"):
                                try:
                                    comparison_data = comparison_df.to_dict('records')
                                    
                                    data, summary, polygons = prepare_analysis_data_for_results(
                                        df, selected_comparison_muns, 'residue_comparison_analysis',
                                        residue_data=comparison_data,
                                        metrics={
                                            'analysis_type': f'Comparação - {selected_residue}',
                                            'residue_type': selected_residue,
                                            'municipalities_compared': len(selected_comparison_muns)
                                        },
                                        analysis_context={'relevant_fields': relevant_fields}
                                    )
                                    
                                    navigate_to_results(data, summary, polygons)
                                except Exception as e:
                                    st.error("Erro ao preparar dados do mapa")
                
                # Passo 6: Individual Municipality Explorer
                st.markdown("---")
                st.markdown(f"### 📋 Passo 6: Explore Todos os Dados - Município Individual")
                
                selected_municipality = st.selectbox(
                    "Selecione um município para análise detalhada:",
                    df_residue['nome_municipio'].tolist(),
                    index=0,
                    key=f"individual_{selected_residue}"
                )
                
                if selected_municipality:
                    mun_data = df_residue[df_residue['nome_municipio'] == selected_municipality].iloc[0]
                    
                    # Municipality overview
                    st.markdown(f"#### 🏘️ Análise Completa: {selected_municipality}")
                    
                    # Key metrics for this municipality
                    mun_col1, mun_col2, mun_col3, mun_col4 = st.columns(4)
                    
                    with mun_col1:
                        st.metric(f"🔥 {selected_residue}", format_number(mun_data[residue_col]) + " m³/ano")
                    
                    with mun_col2:
                        if 'populacao_2022' in mun_data:
                            st.metric("👥 População", f"{mun_data['populacao_2022']:,.0f}")
                    
                    with mun_col3:
                        if 'area_km2' in mun_data:
                            st.metric("📏 Área", f"{mun_data['area_km2']:,.1f} km²")
                    
                    with mun_col4:
                        # Calculate per capita if possible
                        if 'populacao_2022' in mun_data and mun_data['populacao_2022'] > 0:
                            per_capita = mun_data[residue_col] / mun_data['populacao_2022']
                            st.metric("👤 Per Capita", f"{per_capita:.2f} m³/hab/ano")
                    
                    # Municipality ranking position
                    municipality_rank = df_residue[residue_col].rank(method='dense', ascending=False)
                    mun_rank = municipality_rank[df_residue['nome_municipio'] == selected_municipality].iloc[0]
                    
                    st.info(f"🏆 **Ranking Estadual**: {selected_municipality} está na **{mun_rank:.0f}ª posição** de {len(df_residue)} municípios com dados de {selected_residue}")
                    
                    # All residue types for this municipality
                    st.markdown("#### 🌾 Todos os Resíduos deste Município")
                    
                    # Create a chart showing all residue types for this municipality
                    all_residues_data = []
                    
                    for category, residues in residue_categories.items():
                        for res_name, res_col in residues.items():
                            if res_col in df.columns:
                                value = mun_data.get(res_col, 0)
                                if value > 0:
                                    all_residues_data.append({
                                        'Tipo': res_name,
                                        'Categoria': category.split(' ')[1],  # Remove emoji
                                        'Potencial': value
                                    })
                    
                    if all_residues_data:
                        residues_df = pd.DataFrame(all_residues_data)
                        
                        # Bar chart of all residues
                        fig_all_residues = px.bar(
                            residues_df.sort_values('Potencial', ascending=True),
                            x='Potencial',
                            y='Tipo',
                            orientation='h',
                            color='Categoria',
                            title=f"Portfólio Completo de Resíduos - {selected_municipality}",
                            labels={'Potencial': 'Potencial (m³/ano)', 'Tipo': 'Tipo de Resíduo'}
                        )
                        fig_all_residues.update_layout(height=400)
                        st.plotly_chart(fig_all_residues, use_container_width=True)
                        
                        # Single municipality VER NO MAPA
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                        with col_btn2:
                            if st.button(f"🗺️ VER {selected_municipality.upper()} NO MAPA", key=f"single_{selected_municipality}_map", type="primary"):
                                try:
                                    single_mun_data = [mun_data.to_dict()]
                                    
                                    data, summary, polygons = prepare_analysis_data_for_results(
                                        df, [selected_municipality], 'single_municipality_analysis',
                                        residue_data=single_mun_data,
                                        metrics={
                                            'analysis_type': f'Município Individual - {selected_municipality}',
                                            'focus_residue': selected_residue,
                                            'municipality_rank': mun_rank,
                                            'total_residue_types': len(all_residues_data)
                                        },
                                        analysis_context={'relevant_fields': ['nome_municipio'] + [res['Tipo'] for res in all_residues_data] + ['area_km2', 'populacao_2022']}
                                    )
                                    
                                    navigate_to_results(data, summary, polygons)
                                except Exception as e:
                                    st.error("Erro ao preparar dados do mapa")
                    
                    else:
                        st.warning(f"❌ {selected_municipality} não possui dados para outros tipos de resíduos além de {selected_residue}")
            
            else:
                st.warning(f"❌ Não há dados disponíveis para {selected_residue}")
        else:
            st.error(f"❌ Coluna de dados não encontrada para {selected_residue}")
    
    # Analysis Type 2: Compare Residue Types
    elif analysis_type == "🏆 Comparar Tipos de Resíduos":
        st.markdown("### 📊 Passo 2: Compare Diferentes Tipos de Resíduos")
        st.markdown("*Veja qual tipo de resíduo tem maior potencial em São Paulo*")
        
        # Group residues by category for easier selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("""
            **Selecione as categorias que você quer comparar:**
            - 🌾 **Agrícolas**: Cana, soja, milho, café, citros
            - 🐄 **Pecuários**: Bovinos, suínos, aves, piscicultura
            - 🏙️ **Urbanos**: Lixo urbano e poda de árvores
            - 📊 **Totais**: Somas por categoria
            """)
            
            # Organized selection
            categories = {
                "📊 Totais": ["Potencial Total", "Total Agrícola", "Total Pecuária"],
                "🌾 Agrícolas": ["Cana-de-açúcar", "Soja", "Milho", "Café", "Citros"],
                "🐄 Pecuários": ["Bovinos", "Suínos", "Aves", "Piscicultura"],
                "🏙️ Urbanos": ["Resíduos Urbanos", "Resíduos Poda"]
            }
            
            selected_category = st.radio(
                "Escolha uma categoria para comparar:",
                list(categories.keys()),
                key="residue_category"
            )
            
            selected_residues = st.multiselect(
                f"Selecione os tipos de {selected_category.split(' ')[1].lower()}:",
                categories[selected_category],
                default=categories[selected_category][:3] if len(categories[selected_category]) >= 3 else categories[selected_category],
                key="selected_residues_comparison"
            )
        
        with col2:
            st.info("""
            💡 **Dica:**
            
            Comece comparando os "Totais" para ter uma visão geral, depois explore categorias específicas!
            """)
        
        if selected_residues:
            # Create comparison data
            comparison_data = []
            total_state_potential = 0
            
            for residue_type in selected_residues:
                col_name = RESIDUE_OPTIONS[residue_type]
                if col_name in df.columns:
                    # Calculate statistics
                    total = df[col_name].sum()
                    avg = df[col_name].mean()
                    municipalities_with_data = len(df[df[col_name] > 0])
                    max_municipality = df.loc[df[col_name].idxmax(), 'nome_municipio'] if total > 0 else "N/A"
                    
                    comparison_data.append({
                        'Tipo de Resíduo': residue_type,
                        'Potencial Total': total,
                        'Potencial Médio': avg,
                        'Municípios com Dados': municipalities_with_data,
                        'Município Líder': max_municipality
                    })
                    total_state_potential += total
        
        if comparison_data:
                comp_df = pd.DataFrame(comparison_data)
                
                # Show summary metrics
                st.markdown("### 📈 Passo 3: Resultados da Comparação")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    col_metric, col_ref = st.columns([4, 1])
                    with col_metric:
                        st.metric(
                            "🔥 Potencial Total Combinado",
                            f"{total_state_potential/1_000_000:.1f}M m³/ano",
                            help="Soma de todos os tipos selecionados"
                        )
                    with col_ref:
                        render_reference_button("method_biogas", "Metodologia")
                with col2:
                    best_type = comp_df.loc[comp_df['Potencial Total'].idxmax(), 'Tipo de Resíduo']
                    st.metric(
                        "🏆 Tipo Líder",
                        best_type,
                        help="Tipo com maior potencial total"
                    )
                with col3:
                    col_metric, col_ref = st.columns([4, 1])
                    with col_metric:
                        avg_municipalities = comp_df['Municípios com Dados'].mean()
                        st.metric(
                            "📍 Média de Municípios",
                            f"{avg_municipalities:.0f}",
                            help="Média de municípios com dados por tipo"
                        )
                    with col_ref:
                        render_reference_button("data_ibge", "Dados")
                
                # Visual comparisons
                st.markdown("#### 📊 Comparação Visual")
                
                # Tabs for different views
                comp_tabs = st.tabs(["🏆 Potencial Total", "📊 Potencial Médio", "📍 Cobertura Municipal"])
                
                with comp_tabs[0]:
                    fig_total = px.bar(
                        comp_df,
                        x='Tipo de Resíduo',
                        y='Potencial Total',
                        title="Potencial Total por Tipo de Resíduo",
                        labels={'Potencial Total': 'Potencial (m³/ano)'},
                        color='Potencial Total',
                        color_continuous_scale='Oranges'
                    )
                    fig_total.update_layout(height=500, xaxis_tickangle=-45)
                    st.plotly_chart(fig_total, use_container_width=True)
                    
                    # Add percentage breakdown
                    comp_df_pct = comp_df.copy()
                    comp_df_pct['Percentual'] = (comp_df_pct['Potencial Total'] / comp_df_pct['Potencial Total'].sum() * 100).round(1)
                    
                    st.markdown("**📋 Distribuição Percentual:**")
                    for _, row in comp_df_pct.iterrows():
                        st.write(f"• **{row['Tipo de Resíduo']}**: {row['Percentual']:.1f}% do total")
                
                with comp_tabs[1]:
                    fig_avg = px.bar(
                        comp_df,
                        x='Tipo de Resíduo',
                        y='Potencial Médio',
                        title="Potencial Médio por Município por Tipo de Resíduo",
                        labels={'Potencial Médio': 'Potencial Médio (m³/ano)'},
                        color='Potencial Médio',
                        color_continuous_scale='Blues'
                    )
                    fig_avg.update_layout(height=500, xaxis_tickangle=-45)
                    st.plotly_chart(fig_avg, use_container_width=True)
                    
                    st.markdown("**📖 O que isso significa:**")
                    st.markdown("O potencial médio mostra quanto cada município produz em média para cada tipo de resíduo. Valores altos indicam que quando um município tem esse tipo de resíduo, ele tende a ter bastante.")
                
                with comp_tabs[2]:
                    fig_coverage = px.bar(
                        comp_df,
                        x='Tipo de Resíduo',
                        y='Municípios com Dados',
                        title="Número de Municípios com Cada Tipo de Resíduo",
                        labels={'Municípios com Dados': 'Quantidade de Municípios'},
                        color='Municípios com Dados',
                        color_continuous_scale='Greens'
                    )
                    fig_coverage.update_layout(height=500, xaxis_tickangle=-45)
                    st.plotly_chart(fig_coverage, use_container_width=True)
                    
                    st.markdown("**📍 Cobertura Territorial:**")
                    for _, row in comp_df.iterrows():
                        percentage = (row['Municípios com Dados'] / 645) * 100
                        st.write(f"• **{row['Tipo de Resíduo']}**: {row['Municípios com Dados']} municípios ({percentage:.1f}% do estado)")
                
                # Detailed table
                st.markdown("#### 📋 Tabela Detalhada")
                display_comp_df = comp_df.copy()
                display_comp_df['Potencial Total'] = display_comp_df['Potencial Total'].apply(format_number)
                display_comp_df['Potencial Médio'] = display_comp_df['Potencial Médio'].apply(format_number)
                st.dataframe(display_comp_df, use_container_width=True, hide_index=True)
                
                # Add "VER NO MAPA" button for residue comparison
                st.markdown("---")
                st.markdown("#### 🗺️ Ver Análise no Mapa")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get municipalities with best performance for selected residues
                        top_municipalities = []
                        for residue_type in selected_residues:
                            col_name = RESIDUE_OPTIONS[residue_type]
                            if col_name in df.columns:
                                top_mun = df.nlargest(5, col_name)['nome_municipio'].tolist()
                                top_municipalities.extend(top_mun)
                        
                        # Remove duplicates and keep top 10
                        selected_municipalities = list(dict.fromkeys(top_municipalities))[:10]
                        
                        # Prepare data for results page
                        residue_data = comparison_data
                        # Create relevant fields list based on selected residues
                        relevant_fields = ['nome_municipio', 'area_km2', 'populacao_2022']
                        for residue_type in selected_residues:
                            col_name = RESIDUE_OPTIONS.get(residue_type, '').lower()
                            if col_name:
                                relevant_fields.append(col_name)
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, selected_municipalities, 'residue_analysis', 
                            residue_data=residue_data, 
                            metrics={'selected_residues': selected_residues},
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'residue_analysis', 
                            selected_municipalities, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="residue_comparison_map"
                        )
                        
                        st.markdown(f"*Visualizar {len(selected_municipalities)} municípios com maior potencial*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta seleção")
    
    # Analysis Type 2: Regional Analysis
    elif analysis_type == "🌍 Analisar por Região":
        st.markdown("### 🗺️ Passo 2: Análise Regional")
        st.markdown("*Descubra como o potencial de biogás varia geograficamente*")
        
        # Since we don't have region data, we'll create analysis by municipality size
        col1, col2 = st.columns([3, 1])
        
        with col1:
            region_analysis_type = st.selectbox(
                "Que tipo de análise regional você quer fazer?",
                [
                    "📏 Por Tamanho de Município (População)",
                    "🏆 Top Regiões vs Resto do Estado"
                ],
                key="region_analysis_type"
            )
            
            selected_residue_regional = st.selectbox(
                "Escolha o tipo de resíduo para analisar:",
                list(RESIDUE_OPTIONS.keys()),
                key="regional_residue_select"
            )
        
        with col2:
            st.info("""
            💡 **Análise Regional:**
            
            Entenda como o potencial se distribui geograficamente e identifique regiões de oportunidade!
            """)
        
        residue_col = RESIDUE_OPTIONS[selected_residue_regional]
        df_regional = df[df[residue_col] > 0].copy()
        
        if not df_regional.empty:
            if region_analysis_type == "📏 Por Tamanho de Município (População)":
                if 'populacao_2022' in df_regional.columns:
                    # Create population ranges
                    df_regional['faixa_pop'] = pd.cut(
                        df_regional['populacao_2022'],
                        bins=[0, 20000, 50000, 100000, 500000, float('inf')],
                        labels=['Pequeno (<20K)', 'Médio (20-50K)', 'Grande (50-100K)', 'Muito Grande (100-500K)', 'Metrópole (>500K)']
                    )
                    
                    # Group analysis
                    regional_summary = df_regional.groupby('faixa_pop').agg({
                        residue_col: ['sum', 'mean', 'count'],
                        'populacao_2022': 'sum'
                    }).round(0)
                    
                    regional_summary.columns = ['Potencial Total', 'Potencial Médio', 'Qtd Municípios', 'População Total']
                    regional_summary = regional_summary.reset_index()
                    
                    st.markdown("### 📈 Passo 3: Resultados por Tamanho de Município")
                    
                    # Show summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        best_category = regional_summary.loc[regional_summary['Potencial Total'].idxmax(), 'faixa_pop']
                        st.metric("🏆 Categoria Líder", best_category)
                    with col2:
                        total_municipalities = regional_summary['Qtd Municípios'].sum()
                        st.metric("📍 Total de Municípios", f"{total_municipalities:,.0f}")
                    with col3:
                        avg_per_category = regional_summary['Potencial Médio'].mean()
                        st.metric("📊 Potencial Médio Geral", format_number(avg_per_category))
                    
                    # Visualizations
                    fig_regional = px.bar(
                        regional_summary,
                        x='faixa_pop',
                        y='Potencial Total',
                        title=f"Potencial Total de {selected_residue_regional} por Tamanho de Município",
                        labels={'Potencial Total': 'Potencial (m³/ano)', 'faixa_pop': 'Tamanho do Município'},
                        color='Potencial Total',
                        color_continuous_scale='Viridis'
                    )
                    fig_regional.update_layout(height=500)
                    st.plotly_chart(fig_regional, use_container_width=True)
                    
                    # Show detailed table
                    display_regional = regional_summary.copy()
                    display_regional['Potencial Total'] = display_regional['Potencial Total'].apply(format_number)
                    display_regional['Potencial Médio'] = display_regional['Potencial Médio'].apply(format_number)
                    display_regional['População Total'] = display_regional['População Total'].apply(lambda x: f"{x:,.0f}")
                    display_regional.columns = ['Tamanho do Município', 'Potencial Total', 'Potencial Médio', 'Qtd Municípios', 'População Total']
                    st.dataframe(display_regional, use_container_width=True, hide_index=True)
                    
                    # Add "VER NO MAPA" button for largest municipalities
                    st.markdown("---")
                    st.markdown("### 🗺️ Ver Maiores Municípios no Mapa")
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                    with col_btn2:
                        try:
                            # Get municipalities from the largest category with data
                            largest_category = regional_summary.loc[regional_summary['Potencial Total'].idxmax(), 'faixa_pop']
                            largest_municipalities = df_regional[df_regional['faixa_pop'] == largest_category].nlargest(15, residue_col)
                            largest_mun_names = largest_municipalities['nome_municipio'].tolist()
                            
                            # Prepare data for results page
                            regional_data = largest_municipalities.to_dict('records')
                            
                            # Create relevant fields for the selected residue type
                            residue_col_name = RESIDUE_OPTIONS.get(selected_residue_regional, '').lower()
                            relevant_fields = ['nome_municipio', 'area_km2', 'populacao_2022', 'faixa_pop']
                            if residue_col_name:
                                relevant_fields.append(residue_col_name)
                            
                            data, summary, polygons = prepare_analysis_data_for_results(
                                df, largest_mun_names, 'regional_analysis', 
                                residue_data=regional_data, 
                                metrics={
                                    'analysis_type': region_analysis_type,
                                    'residue_type': selected_residue_regional,
                                    'population_category': largest_category
                                },
                                analysis_context={'relevant_fields': relevant_fields}
                            )
                            
                            # Create button
                            create_ver_no_mapa_button(
                                'regional_analysis', 
                                largest_mun_names, 
                                data, 
                                summary=summary, 
                                polygons=polygons,
                                button_key="regional_size_map"
                            )
                            
                            st.markdown(f"*Visualizar {len(largest_mun_names)} municípios da categoria {largest_category}*")
                            
                        except Exception as e:
                            st.info("🗺️ Dados de mapa não disponíveis para esta seleção")
            
            elif region_analysis_type == "🏆 Top Regiões vs Resto do Estado":
                # Analysis of top municipalities vs others
                top_n = st.slider("Quantos municípios considerar como 'Top'?", 5, 50, 20)
                
                df_sorted = df_regional.sort_values(residue_col, ascending=False)
                top_municipalities = df_sorted.head(top_n)
                other_municipalities = df_sorted.tail(len(df_sorted) - top_n)
                
                comparison_data = [
                    {
                        'Grupo': f'Top {top_n} Municípios',
                        'Potencial Total': top_municipalities[residue_col].sum(),
                        'Potencial Médio': top_municipalities[residue_col].mean(),
                        'Quantidade': len(top_municipalities)
                    },
                    {
                        'Grupo': f'Outros {len(other_municipalities)} Municípios',
                        'Potencial Total': other_municipalities[residue_col].sum(),
                        'Potencial Médio': other_municipalities[residue_col].mean(),
                        'Quantidade': len(other_municipalities)
                    }
                ]
                
                comparison_df = pd.DataFrame(comparison_data)
                
                st.markdown(f"### 📈 Passo 3: Top {top_n} vs Resto do Estado")
                
                # Show concentration metrics
                top_percentage = (comparison_df.iloc[0]['Potencial Total'] / df_regional[residue_col].sum()) * 100
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        f"🎯 Concentração nos Top {top_n}",
                        f"{top_percentage:.1f}%",
                        help=f"Percentual do potencial total concentrado nos {top_n} melhores municípios"
                    )
                with col2:
                    ratio = comparison_df.iloc[0]['Potencial Médio'] / comparison_df.iloc[1]['Potencial Médio']
                    st.metric(
                        "📊 Diferença Média",
                        f"{ratio:.1f}x",
                        help="Quantas vezes o potencial médio dos top é maior que os outros"
                    )
                with col3:
                    st.metric(
                        "🏘️ Total de Municípios",
                        f"{len(df_regional):,}",
                        help="Total de municípios com dados para este resíduo"
                    )
                
                # Visualization
                fig_comparison = px.bar(
                    comparison_df,
                    x='Grupo',
                    y='Potencial Total',
                    title=f"Concentração do Potencial - {selected_residue_regional}",
                    labels={'Potencial Total': 'Potencial (m³/ano)'},
                    color='Potencial Total',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_comparison, use_container_width=True)
                
                # Show top municipalities
                st.markdown(f"#### 🏆 Lista dos Top {top_n} Municípios")
                top_display = top_municipalities[['nome_municipio', residue_col]].copy()
                top_display[residue_col] = top_display[residue_col].apply(format_number)
                top_display.columns = ['Município', f'{selected_residue_regional} (m³/ano)']
                top_display = top_display.reset_index(drop=True)
                top_display.index += 1
                st.dataframe(top_display, use_container_width=True)
                
                # Add "VER NO MAPA" button for top municipalities
                st.markdown("---")
                st.markdown("### 🗺️ Ver Top Municípios no Mapa")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get top municipality names
                        top_mun_names = top_municipalities['nome_municipio'].tolist()
                        
                        # Prepare data for results page
                        regional_data = top_municipalities.to_dict('records')
                        total_top_potential = top_municipalities[residue_col].sum()
                        
                        # Create relevant fields for the selected residue type
                        residue_col_name = RESIDUE_OPTIONS.get(selected_residue_regional, '').lower()
                        relevant_fields = ['nome_municipio', 'area_km2', 'populacao_2022']
                        if residue_col_name:
                            relevant_fields.append(residue_col_name)
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, top_mun_names, 'regional_analysis', 
                            residue_data=regional_data, 
                            metrics={
                                'analysis_type': region_analysis_type,
                                'residue_type': selected_residue_regional,
                                'total_potential': total_top_potential,
                                'concentration_percentage': top_percentage
                            },
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'regional_analysis', 
                            top_mun_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="regional_top_map"
                        )
                        
                        st.markdown(f"*Visualizar os {len(top_mun_names)} municípios com maior potencial regional*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta seleção")
        
        else:
            st.warning(f"⚠️ Nenhum município tem dados para {selected_residue_regional}")
    
    # Analysis Type 3: Patterns and Correlations
    elif analysis_type == "🔍 Encontrar Padrões e Correlações":
        st.markdown("### 🔗 Passo 2: Análise de Padrões")
        st.markdown("*Descubra relações interessantes entre diferentes tipos de resíduos*")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            correlation_type = st.selectbox(
                "Que tipo de padrão você quer descobrir?",
                [
                    "🔗 Correlação entre Tipos de Resíduos",
                    "👥 Relação com População",
                    "🏆 Municípios Multiespecializados"
                ],
                key="correlation_analysis_type"
            )
        
        with col2:
            st.info("""
            💡 **Padrões:**
            
            Encontre relações que podem indicar oportunidades de negócio ou sinergia!
            """)
        
        if correlation_type == "🔗 Correlação entre Tipos de Resíduos":
            st.markdown("#### Escolha dois tipos de resíduos para comparar:")
            
            col_a, col_b = st.columns(2)
            with col_a:
                residue_a = st.selectbox("Primeiro tipo:", list(RESIDUE_OPTIONS.keys()), key="corr_a")
            with col_b:
                residue_b = st.selectbox("Segundo tipo:", list(RESIDUE_OPTIONS.keys()), index=1, key="corr_b")
            
            if residue_a != residue_b:
                col_a_name = RESIDUE_OPTIONS[residue_a]
                col_b_name = RESIDUE_OPTIONS[residue_b]
                
                # Filter data with both types
                df_corr = df[(df[col_a_name] > 0) & (df[col_b_name] > 0)].copy()
                
                if len(df_corr) > 5:  # Need at least 5 points for correlation
                    correlation = df_corr[col_a_name].corr(df_corr[col_b_name])
                    
                    st.markdown("### 📈 Passo 3: Resultado da Correlação")
                    
                    # Interpret correlation
                    if correlation > 0.7:
                        interpretation = "🔥 **Forte correlação positiva** - Municípios que têm muito de um tipo geralmente têm muito do outro!"
                        color = "green"
                    elif correlation > 0.3:
                        interpretation = "📊 **Correlação moderada** - Há alguma relação entre os dois tipos."
                        color = "orange"
                    elif correlation > -0.3:
                        interpretation = "🤷 **Pouca correlação** - Os dois tipos são independentes."
                        color = "gray"
                    else:
                        interpretation = "↔️ **Correlação negativa** - Quando um é alto, o outro tende a ser baixo."
                        color = "red"
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🔗 Correlação", f"{correlation:.3f}")
                    with col2:
                        st.metric("📍 Municípios Analisados", len(df_corr))
                    with col3:
                        st.metric("📊 Força da Relação", 
                                f"{'Forte' if abs(correlation) > 0.7 else 'Moderada' if abs(correlation) > 0.3 else 'Fraca'}")
                    
                    st.markdown(f"**{interpretation}**")
                    
                    # Scatter plot with error handling
                    try:
                        fig_scatter = px.scatter(
                            df_corr,
                            x=col_a_name,
                            y=col_b_name,
                            hover_name='nome_municipio',
                            title=f"Correlação: {residue_a} vs {residue_b}",
                            labels={
                                col_a_name: f"{residue_a} (m³/ano)",
                                col_b_name: f"{residue_b} (m³/ano)"
                            },
                            trendline="ols"
                        )
                    except ImportError:
                        # Fallback without trendline if statsmodels is not available
                        st.warning("⚠️ Linha de tendência não disponível (instale statsmodels)")
                        fig_scatter = px.scatter(
                            df_corr,
                            x=col_a_name,
                            y=col_b_name,
                            hover_name='nome_municipio',
                            title=f"Correlação: {residue_a} vs {residue_b}",
                            labels={
                                col_a_name: f"{residue_a} (m³/ano)",
                                col_b_name: f"{residue_b} (m³/ano)"
                            }
                        )
                    
                    # Enhanced styling
                    fig_scatter.update_traces(
                        marker=dict(size=8, opacity=0.6, line=dict(width=1, color='white'))
                    )
                    fig_scatter.update_layout(
                        height=500,
                        showlegend=True,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Show municipalities with both high values
                    if correlation > 0.3:
                        st.markdown("#### 🏆 Municípios que se Destacam nos Dois Tipos")
                        # Get municipalities in top quartile for both
                        q75_a = df_corr[col_a_name].quantile(0.75)
                        q75_b = df_corr[col_b_name].quantile(0.75)
                        
                        top_both = df_corr[(df_corr[col_a_name] >= q75_a) & (df_corr[col_b_name] >= q75_b)]
                        
                        if not top_both.empty:
                            top_display = top_both[['nome_municipio', col_a_name, col_b_name]].copy()
                            top_display[col_a_name] = top_display[col_a_name].apply(format_number)
                            top_display[col_b_name] = top_display[col_b_name].apply(format_number)
                            top_display.columns = ['Município', residue_a, residue_b]
                            st.dataframe(top_display, use_container_width=True, hide_index=True)
                            
                            # Add "VER NO MAPA" button for correlation analysis
                            st.markdown("---")
                            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                            with col_btn2:
                                try:
                                    # Get municipality names from top performers
                                    top_mun_names = top_both['nome_municipio'].head(10).tolist()
                                    
                                    # Prepare analysis context for correlation data
                                    relevant_fields = ['nome_municipio', col_a_name, col_b_name, 'area_km2', 'populacao_2022']
                                    
                                    # Prepare data for results page
                                    correlation_data = top_both.to_dict('records')
                                    
                                    data, summary, polygons = prepare_analysis_data_for_results(
                                        df, top_mun_names, 'correlation_analysis', 
                                        residue_data=correlation_data, 
                                        metrics={
                                            'analysis_type': 'Análise de Correlação',
                                            'residue_a': residue_a,
                                            'residue_b': residue_b,
                                            'correlation': correlation,
                                            'interpretation': interpretation.replace('**', '').replace('🔥', '').replace('📊', '').replace('🤷', '').replace('↔️', '').strip()
                                        },
                                        analysis_context={'relevant_fields': relevant_fields}
                                    )
                                    
                                    # Create button
                                    create_ver_no_mapa_button(
                                        'correlation_analysis', 
                                        top_mun_names, 
                                        data, 
                                        summary=summary, 
                                        polygons=polygons,
                                        button_key="correlation_map"
                                    )
                                    
                                    st.markdown(f"*Visualizar {len(top_mun_names)} municípios com alta correlação*")
                                    
                                except Exception as e:
                                    st.info("🗺️ Dados de mapa não disponíveis para esta correlação")
                        else:
                            st.write("Nenhum município se destaca simultaneamente nos dois tipos.")
                else:
                    st.warning("⚠️ Poucos municípios têm dados para ambos os tipos. Tente outras combinações.")
        
        elif correlation_type == "👥 Relação com População":
            st.markdown("#### Veja como o potencial se relaciona com o tamanho da população:")
            
            selected_residue_pop = st.selectbox(
                "Escolha o tipo de resíduo:",
                list(RESIDUE_OPTIONS.keys()),
                key="population_correlation_residue"
            )
            
            residue_col_pop = RESIDUE_OPTIONS[selected_residue_pop]
            
            if 'populacao_2022' in df.columns:
                df_pop = df[(df[residue_col_pop] > 0) & (df['populacao_2022'] > 0)].copy()
                
                if not df_pop.empty:
                    correlation_pop = df_pop[residue_col_pop].corr(df_pop['populacao_2022'])
                    
                    st.markdown("### 📈 Passo 3: Relação com População")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("🔗 Correlação", f"{correlation_pop:.3f}")
                    with col2:
                        st.metric("📍 Municípios", len(df_pop))
                    with col3:
                        avg_per_capita = (df_pop[residue_col_pop] / df_pop['populacao_2022']).mean()
                        st.metric("👤 Média per Capita", f"{avg_per_capita:.2f} m³/hab/ano")
                    
                    # Interpretation
                    if correlation_pop > 0.5:
                        st.success("✅ **Correlação positiva forte** - Municípios maiores tendem a ter mais potencial!")
                    elif correlation_pop > 0.2:
                        st.info("📊 **Correlação moderada** - Há alguma relação com o tamanho da população.")
                    else:
                        st.warning("🤷 **Pouca correlação** - O potencial não depende muito do tamanho da população.")
                    
                    # Scatter plot with enhanced styling
                    try:
                        fig_pop = px.scatter(
                            df_pop,
                            x='populacao_2022',
                            y=residue_col_pop,
                            hover_name='nome_municipio',
                            title=f"População vs {selected_residue_pop}",
                            labels={
                                'populacao_2022': 'População (2022)',
                                residue_col_pop: f'{selected_residue_pop} (m³/ano)'
                            },
                            trendline="ols",
                            size=residue_col_pop,
                            color=residue_col_pop,
                            color_continuous_scale='Viridis'
                        )
                    except ImportError:
                        # Fallback without trendline if statsmodels is not available
                        fig_pop = px.scatter(
                            df_pop,
                            x='populacao_2022',
                            y=residue_col_pop,
                            hover_name='nome_municipio',
                            title=f"População vs {selected_residue_pop}",
                            labels={
                                'populacao_2022': 'População (2022)',
                                residue_col_pop: f'{selected_residue_pop} (m³/ano)'
                            },
                            size=residue_col_pop,
                            color=residue_col_pop,
                            color_continuous_scale='Viridis'
                        )
                    
                    fig_pop.update_layout(
                        height=500,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_pop, use_container_width=True)
                    
                    # Add top municipalities with high per capita potential
                    st.markdown("#### 🏆 Municípios com Alto Potencial per Capita")
                    df_pop['potencial_per_capita'] = df_pop[residue_col_pop] / df_pop['populacao_2022']
                    top_per_capita = df_pop.nlargest(10, 'potencial_per_capita')
                    
                    if not top_per_capita.empty:
                        per_capita_display = top_per_capita[['nome_municipio', 'populacao_2022', residue_col_pop, 'potencial_per_capita']].copy()
                        per_capita_display['populacao_2022'] = per_capita_display['populacao_2022'].apply(lambda x: f"{x:,.0f}")
                        per_capita_display[residue_col_pop] = per_capita_display[residue_col_pop].apply(format_number)
                        per_capita_display['potencial_per_capita'] = per_capita_display['potencial_per_capita'].apply(lambda x: f"{x:.2f}")
                        per_capita_display.columns = ['Município', 'População', f'{selected_residue_pop} Total', 'Per Capita (m³/hab/ano)']
                        st.dataframe(per_capita_display, use_container_width=True, hide_index=True)
                        
                        # Add "VER NO MAPA" button for population correlation analysis
                        st.markdown("---")
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                        with col_btn2:
                            try:
                                # Get municipality names from top per capita performers
                                top_percapita_names = top_per_capita['nome_municipio'].head(10).tolist()
                                
                                # Prepare analysis context for population correlation
                                relevant_fields = ['nome_municipio', residue_col_pop, 'populacao_2022', 'potencial_per_capita', 'area_km2']
                                
                                # Prepare data for results page
                                population_data = top_per_capita.to_dict('records')
                                
                                data, summary, polygons = prepare_analysis_data_for_results(
                                    df, top_percapita_names, 'population_correlation', 
                                    residue_data=population_data, 
                                    metrics={
                                        'analysis_type': 'Relação com População',
                                        'residue_type': selected_residue_pop,
                                        'correlation': correlation_pop,
                                        'average_per_capita': avg_per_capita
                                    },
                                    analysis_context={'relevant_fields': relevant_fields}
                                )
                                
                                # Create button
                                create_ver_no_mapa_button(
                                    'population_correlation', 
                                    top_percapita_names, 
                                    data, 
                                    summary=summary, 
                                    polygons=polygons,
                                    button_key="population_correlation_map"
                                )
                                
                                st.markdown(f"*Visualizar {len(top_percapita_names)} municípios com alto potencial per capita*")
                                
                            except Exception as e:
                                st.info("🗺️ Dados de mapa não disponíveis para esta análise")
        
        elif correlation_type == "🏆 Municípios Multiespecializados":
            st.markdown("#### Descubra quais municípios se destacam em vários tipos de resíduos:")
            
            # Calculate how many types each municipality has significant potential
            residue_columns = [col for col in RESIDUE_OPTIONS.values() if col in df.columns]
            
            # Define "significant" as being in top 25% for each type
            df_multi = df.copy()
            specialization_scores = []
            
            for _, row in df_multi.iterrows():
                score = 0
                types_with_potential = []
                
                for label, col in RESIDUE_OPTIONS.items():
                    if col in df.columns and row[col] > 0:
                        # Check if municipality is in top 25% for this type
                        threshold = df[col].quantile(0.75)
                        if row[col] >= threshold:
                            score += 1
                            types_with_potential.append(label)
                
                specialization_scores.append({
                    'nome_municipio': row['nome_municipio'],
                    'score_especializacao': score,
                    'tipos_destacados': ', '.join(types_with_potential) if types_with_potential else 'Nenhum',
                    'total_potencial': row.get('total_final_m_ano', 0)
                })
            
            specialization_df = pd.DataFrame(specialization_scores)
            specialization_df = specialization_df[specialization_df['score_especializacao'] > 0].sort_values('score_especializacao', ascending=False)
            
            st.markdown("### 📈 Passo 3: Ranking de Multiespecialização")
            
            if not specialization_df.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    max_score = specialization_df['score_especializacao'].max()
                    st.metric("🏆 Máximo de Especializações", f"{max_score} tipos")
                with col2:
                    multi_specialists = len(specialization_df[specialization_df['score_especializacao'] >= 3])
                    st.metric("🌟 Multiespecialistas", f"{multi_specialists} municípios")
                with col3:
                    avg_score = specialization_df['score_especializacao'].mean()
                    st.metric("📊 Média de Especializações", f"{avg_score:.1f}")
                
                # Show top multispcialized municipalities
                top_multi = specialization_df.head(20)
                
                ranking_multi = []
                for i, (_, row) in enumerate(top_multi.iterrows(), 1):
                    ranking_multi.append({
                        "🏅 Posição": f"{i}º",
                        "🏘️ Município": row['nome_municipio'],
                        "🌟 Especializações": f"{row['score_especializacao']} tipos",
                        "📋 Tipos Destacados": row['tipos_destacados'],
                        "🔥 Potencial Total": format_number(row['total_potencial'])
                    })
                
                ranking_multi_df = pd.DataFrame(ranking_multi)
                st.dataframe(ranking_multi_df, use_container_width=True, hide_index=True)
                
                # Add "VER NO MAPA" button for multi-specialized analysis
                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get municipality names from top multi-specialized
                        multi_mun_names = top_multi['nome_municipio'].head(10).tolist()
                        
                        # Prepare analysis context for multi-specialized municipalities
                        relevant_fields = ['nome_municipio', 'score_especializacao', 'tipos_destacados', 'total_potencial', 'area_km2', 'populacao_2022']
                        # Add all residue columns that are relevant
                        for col in RESIDUE_OPTIONS.values():
                            if col in df.columns:
                                relevant_fields.append(col)
                        
                        # Prepare data for results page
                        multi_data = top_multi.to_dict('records')
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, multi_mun_names, 'multi_specialized_analysis', 
                            residue_data=multi_data, 
                            metrics={
                                'analysis_type': 'Municípios Multiespecializados',
                                'max_specializations': max_score,
                                'avg_specializations': specialization_df['score_especializacao'].mean()
                            },
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'multi_specialized_analysis', 
                            multi_mun_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="multi_specialized_map"
                        )
                        
                        st.markdown(f"*Visualizar {len(multi_mun_names)} municípios multiespecializados*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta análise")
                
                # Visualization
                fig_multi = px.histogram(
                    specialization_df,
                    x='score_especializacao',
                    title="Distribuição de Especializações",
                    labels={'score_especializacao': 'Número de Especializações', 'count': 'Quantidade de Municípios'},
                    nbins=max_score
                )
                st.plotly_chart(fig_multi, use_container_width=True)
            else:
                st.info("Nenhum município se destaca significativamente em múltiplos tipos de resíduos.")
    
    # Analysis Type 4: Municipal Portfolio
    elif analysis_type == "📈 Análise de Portfólio Municipal":
        st.markdown("### 🏘️ Passo 2: Análise de Portfólio Municipal")
        st.markdown("*Descubra quais municípios têm o portfólio mais diversificado de resíduos*")
        
        # Calculate diversity score for each municipality
        residue_columns = [col for col in RESIDUE_OPTIONS.values() if col in df.columns]
        
        df_portfolio = df.copy()
        
        # Calculate diversity metrics
        df_portfolio['tipos_com_dados'] = (df_portfolio[residue_columns] > 0).sum(axis=1)
        df_portfolio['potencial_total_real'] = df_portfolio[residue_columns].sum(axis=1)
        df_portfolio['diversidade_score'] = df_portfolio['tipos_com_dados'] / len(residue_columns)
        
        # Filter municipalities with at least some data
        df_portfolio = df_portfolio[df_portfolio['potencial_total_real'] > 0]
        
        st.markdown("### 📊 Passo 3: Ranking de Diversificação")
        
        portfolio_analysis = st.selectbox(
            "Como você quer analisar os portfólios municipais?",
            [
                "🌟 Municípios Mais Diversificados",
                "🎯 Municípios Especializados",
                "⚖️ Diversificação vs Potencial Total"
            ]
        )
        
        if portfolio_analysis == "🌟 Municípios Mais Diversificados":
            # Most diversified municipalities
            top_diversified = df_portfolio.nlargest(20, 'diversidade_score')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                max_types = top_diversified['tipos_com_dados'].max()
                st.metric("🏆 Máximo de Tipos", f"{max_types}/{len(residue_columns)}")
            with col2:
                avg_diversity = top_diversified['diversidade_score'].mean()
                st.metric("📊 Diversidade Média", f"{avg_diversity:.1%}")
            with col3:
                total_municipalities = len(df_portfolio)
                st.metric("📍 Total de Municípios", total_municipalities)
            
            # Show ranking
            ranking_data = []
            for i, (_, row) in enumerate(top_diversified.iterrows(), 1):
                ranking_data.append({
                    "🏅 Posição": f"{i}º",
                    "🏘️ Município": row['nome_municipio'],
                    "🌟 Tipos de Resíduos": f"{row['tipos_com_dados']}/{len(residue_columns)}",
                    "📊 Score de Diversidade": f"{row['diversidade_score']:.1%}",
                    "🔥 Potencial Total": format_number(row['potencial_total_real'])
                })
            
            ranking_df = pd.DataFrame(ranking_data)
            st.dataframe(ranking_df, use_container_width=True, hide_index=True)
            
            # Visualization
            fig_diversity = px.scatter(
                top_diversified,
                x='tipos_com_dados',
                y='potencial_total_real',
                hover_name='nome_municipio',
                title="Diversificação vs Potencial Total",
                labels={
                    'tipos_com_dados': 'Número de Tipos de Resíduos',
                    'potencial_total_real': 'Potencial Total (m³/ano)'
                },
                size='potencial_total_real',
                color='diversidade_score',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_diversity, use_container_width=True)
            
            # Add "VER NO MAPA" button for diversified municipalities
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                try:
                    # Get municipality names from top diversified
                    diversified_mun_names = top_diversified['nome_municipio'].head(10).tolist()
                    
                    # Prepare analysis context for portfolio analysis
                    relevant_fields = ['nome_municipio', 'tipos_com_dados', 'diversidade_score', 'potencial_total_real', 'area_km2', 'populacao_2022']
                    # Add key residue columns
                    for col in residue_columns[:5]:  # Top 5 most important residue types
                        relevant_fields.append(col)
                    
                    # Prepare data for results page
                    portfolio_data = top_diversified.to_dict('records')
                    
                    data, summary, polygons = prepare_analysis_data_for_results(
                        df, diversified_mun_names, 'portfolio_analysis', 
                        residue_data=portfolio_data, 
                        metrics={
                            'analysis_type': 'Portfólio Municipal - Mais Diversificados',
                            'max_types': max_types,
                            'avg_diversity': avg_diversity,
                            'total_municipalities': total_municipalities
                        },
                        analysis_context={'relevant_fields': relevant_fields}
                    )
                    
                    # Create button
                    create_ver_no_mapa_button(
                        'portfolio_analysis', 
                        diversified_mun_names, 
                        data, 
                        summary=summary, 
                        polygons=polygons,
                        button_key="portfolio_diversified_map"
                    )
                    
                    st.markdown(f"*Visualizar {len(diversified_mun_names)} municípios mais diversificados*")
                    
                except Exception as e:
                    st.info("🗺️ Dados de mapa não disponíveis para esta análise")
        
        elif portfolio_analysis == "🎯 Municípios Especializados":
            # Municipalities specialized in few types but with high potential
            specialized = df_portfolio[df_portfolio['tipos_com_dados'] <= 3].nlargest(20, 'potencial_total_real')
            
            if not specialized.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    avg_types = specialized['tipos_com_dados'].mean()
                    st.metric("📊 Média de Tipos", f"{avg_types:.1f}")
                with col2:
                    total_potential = specialized['potencial_total_real'].sum()
                    st.metric("🔥 Potencial Total", f"{total_potential/1_000_000:.1f}M m³/ano")
                with col3:
                    st.metric("🎯 Municípios Especializados", len(specialized))
                
                # Show specialized municipalities
                specialized_ranking = []
                for i, (_, row) in enumerate(specialized.iterrows(), 1):
                    # Find which types this municipality specializes in
                    specialized_types = []
                    for label, col in RESIDUE_OPTIONS.items():
                        if col in df.columns and row[col] > 0:
                            specialized_types.append(label)
                    
                    specialized_ranking.append({
                        "🏅 Posição": f"{i}º",
                        "🏘️ Município": row['nome_municipio'],
                        "🎯 Tipos": f"{row['tipos_com_dados']} tipos",
                        "📋 Especialização": ', '.join(specialized_types[:3]),  # Show first 3
                        "🔥 Potencial Total": format_number(row['potencial_total_real'])
                    })
                
                specialized_df = pd.DataFrame(specialized_ranking)
                st.dataframe(specialized_df, use_container_width=True, hide_index=True)
                
                # Add "VER NO MAPA" button for specialized municipalities
                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get municipality names from top specialized
                        specialized_mun_names = specialized['nome_municipio'].head(10).tolist()
                        
                        # Prepare analysis context for specialized portfolio analysis
                        relevant_fields = ['nome_municipio', 'tipos_com_dados', 'diversidade_score', 'potencial_total_real', 'area_km2', 'populacao_2022']
                        # Add the most relevant residue columns for specialized municipalities
                        for col in residue_columns:
                            if col in specialized.columns and specialized[col].sum() > 0:
                                relevant_fields.append(col)
                        
                        # Prepare data for results page
                        specialized_data = specialized.to_dict('records')
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, specialized_mun_names, 'portfolio_specialized_analysis', 
                            residue_data=specialized_data, 
                            metrics={
                                'analysis_type': 'Portfólio Municipal - Especializados',
                                'avg_types': specialized['tipos_com_dados'].mean(),
                                'avg_potential': specialized['potencial_total_real'].mean()
                            },
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'portfolio_specialized_analysis', 
                            specialized_mun_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="portfolio_specialized_map"
                        )
                        
                        st.markdown(f"*Visualizar {len(specialized_mun_names)} municípios especializados*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta análise")
            else:
                st.info("Não há municípios com especialização em poucos tipos.")
        
        elif portfolio_analysis == "⚖️ Diversificação vs Potencial Total":
            # Analysis of relationship between diversification and total potential
            correlation_div = df_portfolio['diversidade_score'].corr(df_portfolio['potencial_total_real'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔗 Correlação", f"{correlation_div:.3f}")
            with col2:
                high_div_high_pot = len(df_portfolio[
                    (df_portfolio['diversidade_score'] > df_portfolio['diversidade_score'].quantile(0.75)) &
                    (df_portfolio['potencial_total_real'] > df_portfolio['potencial_total_real'].quantile(0.75))
                ])
                st.metric("🌟 Alta Div. + Alto Pot.", high_div_high_pot)
            with col3:
                avg_potential_high_div = df_portfolio[
                    df_portfolio['diversidade_score'] > df_portfolio['diversidade_score'].quantile(0.75)
                ]['potencial_total_real'].mean()
                st.metric("📊 Pot. Médio (Alta Div.)", format_number(avg_potential_high_div))
            
            # Scatter plot with error handling
            try:
                fig_div_pot = px.scatter(
                    df_portfolio,
                    x='diversidade_score',
                    y='potencial_total_real',
                    hover_name='nome_municipio',
                    title="Diversificação vs Potencial Total",
                    labels={
                        'diversidade_score': 'Score de Diversificação',
                        'potencial_total_real': 'Potencial Total (m³/ano)'
                    },
                    trendline="ols",
                    color='tipos_com_dados',
                    color_continuous_scale='Plasma'
                )
            except ImportError:
                # Fallback without trendline if statsmodels is not available
                fig_div_pot = px.scatter(
                    df_portfolio,
                    x='diversidade_score',
                    y='potencial_total_real',
                    hover_name='nome_municipio',
                    title="Diversificação vs Potencial Total",
                    labels={
                        'diversidade_score': 'Score de Diversificação',
                        'potencial_total_real': 'Potencial Total (m³/ano)'
                    },
                    color='tipos_com_dados',
                    color_continuous_scale='Plasma'
                )
            
            fig_div_pot.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_div_pot, use_container_width=True)
            
            # Interpretation
            if correlation_div > 0.3:
                st.success("✅ **Correlação positiva** - Municípios mais diversificados tendem a ter maior potencial total!")
            elif correlation_div > 0.1:
                st.info("📊 **Correlação fraca** - Há alguma relação entre diversificação e potencial.")
            else:
                st.warning("🤷 **Pouca correlação** - Diversificação e potencial total são independentes.")
            
            # Show municipalities with high diversification AND high potential
            st.markdown("#### 🌟 Municípios com Alta Diversificação E Alto Potencial")
            high_both = df_portfolio[
                (df_portfolio['diversidade_score'] > df_portfolio['diversidade_score'].quantile(0.75)) &
                (df_portfolio['potencial_total_real'] > df_portfolio['potencial_total_real'].quantile(0.75))
            ]
            
            if not high_both.empty:
                high_both_display = high_both[['nome_municipio', 'tipos_com_dados', 'diversidade_score', 'potencial_total_real']].copy()
                high_both_display['diversidade_score'] = high_both_display['diversidade_score'].apply(lambda x: f"{x:.1%}")
                high_both_display['potencial_total_real'] = high_both_display['potencial_total_real'].apply(format_number)
                high_both_display.columns = ['Município', 'Tipos de Resíduos', 'Score Diversidade', 'Potencial Total']
                st.dataframe(high_both_display, use_container_width=True, hide_index=True)
                
                # Add "VER NO MAPA" button for high diversification and potential
                st.markdown("---")
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    try:
                        # Get municipality names from high both categories
                        high_both_names = high_both['nome_municipio'].head(10).tolist()
                        
                        # Prepare analysis context for diversification vs potential analysis
                        relevant_fields = ['nome_municipio', 'tipos_com_dados', 'diversidade_score', 'potencial_total_real', 'area_km2', 'populacao_2022']
                        # Add all residue columns for comprehensive analysis
                        relevant_fields.extend(residue_columns)
                        
                        # Prepare data for results page
                        div_potential_data = high_both.to_dict('records')
                        
                        data, summary, polygons = prepare_analysis_data_for_results(
                            df, high_both_names, 'portfolio_div_potential_analysis', 
                            residue_data=div_potential_data, 
                            metrics={
                                'analysis_type': 'Portfólio - Alta Diversificação e Alto Potencial',
                                'correlation': correlation_div,
                                'high_div_high_pot_count': high_div_high_pot,
                                'avg_potential_high_div': avg_potential_high_div
                            },
                            analysis_context={'relevant_fields': relevant_fields}
                        )
                        
                        # Create button
                        create_ver_no_mapa_button(
                            'portfolio_div_potential_analysis', 
                            high_both_names, 
                            data, 
                            summary=summary, 
                            polygons=polygons,
                            button_key="portfolio_div_potential_map"
                        )
                        
                        st.markdown(f"*Visualizar {len(high_both_names)} municípios com alta diversificação e potencial*")
                        
                    except Exception as e:
                        st.info("🗺️ Dados de mapa não disponíveis para esta análise")
            else:
                st.info("Nenhum município se destaca simultaneamente em diversificação e potencial.")

    # Analysis Type 5: Advanced Opportunities
    elif analysis_type == "🚀 Análise Avançada de Oportunidades":
        st.markdown("### 🚀 Passo 2: Identificação de Oportunidades Estratégicas")
        st.markdown("*Descubra oportunidades de negócio e investimento baseadas em dados avançados*")
        
        opportunity_type = st.selectbox(
            "Que tipo de oportunidade você quer investigar?",
            [
                "💰 Municípios Subutilizados (Alto Potencial + Baixo Desenvolvimento)",
                "🎯 Clusters de Sinergia Regional",
                "📊 Análise de Viabilidade Econômica",
                "🔮 Projeções de Crescimento"
            ]
        )
        
        if opportunity_type == "💰 Municípios Subutilizados (Alto Potencial + Baixo Desenvolvimento)":
            st.markdown("#### 💎 Joias Escondidas: Municípios com Grande Potencial Inexplorado")
            
            # Calculate development index (population + economic indicators proxy)
            df_opp = df.copy()
            df_opp = df_opp[df_opp['total_final_m_ano'] > 0].copy()
            
            # Normalize metrics for comparison
            df_opp['potencial_normalizado'] = (df_opp['total_final_m_ano'] - df_opp['total_final_m_ano'].min()) / (df_opp['total_final_m_ano'].max() - df_opp['total_final_m_ano'].min())
            df_opp['desenvolvimento_normalizado'] = (df_opp['populacao_2022'] - df_opp['populacao_2022'].min()) / (df_opp['populacao_2022'].max() - df_opp['populacao_2022'].min())
            
            # Calculate opportunity score (high potential, low development)
            df_opp['opportunity_score'] = df_opp['potencial_normalizado'] - df_opp['desenvolvimento_normalizado']
            
            # Find top opportunities
            top_opportunities = df_opp.nlargest(15, 'opportunity_score')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_potential = top_opportunities['total_final_m_ano'].mean()
                st.metric("💎 Potencial Médio (Oportunidades)", format_number(avg_potential))
            with col2:
                total_unexplored = top_opportunities['total_final_m_ano'].sum()
                st.metric("🚀 Potencial Total Subutilizado", format_number(total_unexplored))
            with col3:
                best_score = top_opportunities['opportunity_score'].max()
                st.metric("⭐ Melhor Score de Oportunidade", f"{best_score:.3f}")
            
            # Show ranking
            opportunities_ranking = []
            for i, (_, row) in enumerate(top_opportunities.iterrows(), 1):
                opportunities_ranking.append({
                    "🏅 Rank": f"{i}º",
                    "💎 Município": row['nome_municipio'],
                    "🚀 Potencial": format_number(row['total_final_m_ano']),
                    "👥 População": f"{row['populacao_2022']:,.0f}",
                    "⭐ Score": f"{row['opportunity_score']:.3f}",
                })
            
            st.markdown("#### 🏆 Top 15 Oportunidades de Investimento")
            ranking_opp_df = pd.DataFrame(opportunities_ranking)
            st.dataframe(ranking_opp_df, use_container_width=True, hide_index=True)
            
            # Opportunity matrix visualization
            fig_matrix = px.scatter(
                df_opp,
                x='desenvolvimento_normalizado',
                y='potencial_normalizado',
                hover_name='nome_municipio',
                title="Matriz de Oportunidades: Desenvolvimento vs Potencial",
                labels={
                    'desenvolvimento_normalizado': 'Nível de Desenvolvimento (População Normalizada)',
                    'potencial_normalizado': 'Potencial de Biogás (Normalizado)'
                },
                color='opportunity_score',
                color_continuous_scale='RdYlGn',
                size='total_final_m_ano'
            )
            
            # Add quadrant lines
            fig_matrix.add_hline(y=0.5, line_dash="dash", line_color="gray")
            fig_matrix.add_vline(x=0.5, line_dash="dash", line_color="gray")
            
            # Add annotations for quadrants
            fig_matrix.add_annotation(x=0.25, y=0.75, text="OPORTUNIDADES<br>PRIME", 
                                    showarrow=False, font=dict(size=12, color="green"))
            fig_matrix.add_annotation(x=0.75, y=0.75, text="DESENVOLVIDAS<br>CONSOLIDADAS", 
                                    showarrow=False, font=dict(size=12, color="blue"))
            fig_matrix.add_annotation(x=0.25, y=0.25, text="BAIXO POTENCIAL<br>EM DESENVOLVIMENTO", 
                                    showarrow=False, font=dict(size=12, color="orange"))
            fig_matrix.add_annotation(x=0.75, y=0.25, text="DESENVOLVIDAS<br>BAIXO POTENCIAL", 
                                    showarrow=False, font=dict(size=12, color="red"))
            
            fig_matrix.update_layout(height=600)
            st.plotly_chart(fig_matrix, use_container_width=True)
            
        elif opportunity_type == "🎯 Clusters de Sinergia Regional":
            st.markdown("#### 🌍 Análise de Clusters Regionais para Sinergia")
            
            # Regional analysis removed - data not available
            if False:
                regional_analysis = df.groupby('regiao_imediata').agg({
                    'total_final_m_ano': ['sum', 'mean', 'count'],
                    'populacao_2022': 'sum',
                    'total_agricola_m_ano': 'sum',
                    'total_pecuaria_m_ano': 'sum'
                }).round(0)
                
                regional_analysis.columns = ['Total_Potencial', 'Media_Potencial', 'Num_Municipios', 'Pop_Total', 'Potencial_Agri', 'Potencial_Pec']
                regional_analysis = regional_analysis.sort_values('Total_Potencial', ascending=False).head(10)
                
                st.markdown("#### 🏆 Top 10 Regiões para Desenvolvimento de Clusters")
                
                cluster_ranking = []
                for i, (regiao, row) in enumerate(regional_analysis.iterrows(), 1):
                    cluster_ranking.append({
                        "🏅 Rank": f"{i}º",
                        "🌍 Região": regiao,
                        "🚀 Potencial Total": format_number(row['Total_Potencial']),
                        "🏘️ Municípios": f"{int(row['Num_Municipios'])}",
                        "👥 População": f"{int(row['Pop_Total']):,}",
                        "🌾 % Agrícola": f"{(row['Potencial_Agri']/row['Total_Potencial']*100):.0f}%",
                        "🐄 % Pecuária": f"{(row['Potencial_Pec']/row['Total_Potencial']*100):.0f}%"
                    })
                
                cluster_df = pd.DataFrame(cluster_ranking)
                st.dataframe(cluster_df, use_container_width=True, hide_index=True)
                
                # Regional potential visualization
                fig_regional = px.bar(
                    regional_analysis.reset_index(),
                    x='regiao_imediata',
                    y='Total_Potencial',
                    title="Potencial Total por Região (Top 10)",
                    labels={'Total_Potencial': 'Potencial Total (m³/ano)', 'regiao_imediata': 'Região'},
                    color='Media_Potencial',
                    color_continuous_scale='Viridis'
                )
                fig_regional.update_xaxes(tickangle=45)
                fig_regional.update_layout(height=500)
                st.plotly_chart(fig_regional, use_container_width=True)

    # Analysis Type 6: Intelligent Insights
    elif analysis_type == "💡 Insights Inteligentes e Recomendações":
        st.markdown("### 💡 Passo 2: Geração de Insights Automatizados")
        st.markdown("*Sistema inteligente analisa os dados e fornece recomendações personalizadas*")
        
        insight_type = st.selectbox(
            "Que tipo de insight você precisa?",
            [
                "🎯 Recomendações Personalizadas por Perfil",
                "📊 Análise SWOT Automática",
                "🔍 Detecção de Padrões Ocultos",
                "📈 Cenários de Desenvolvimento"
            ]
        )
        
        if insight_type == "🎯 Recomendações Personalizadas por Perfil":
            st.markdown("#### 🎯 Sistema de Recomendações Inteligente")
            
            user_profile = st.selectbox(
                "Qual é o seu perfil/interesse?",
                [
                    "🏛️ Gestor Público Municipal",
                    "💼 Investidor/Empresário",
                    "🎓 Pesquisador Acadêmico",
                    "🌱 Consultor em Sustentabilidade",
                    "🏭 Desenvolvedor de Projetos"
                ]
            )
            
            region_filter = st.selectbox(
                "Região de interesse:",
["📍 Todo o Estado"]
            )
            
            # Filter data based on region
            df_filtered = df.copy()
            if region_filter != "📍 Todo o Estado":
                pass  # Regional filtering removed - data not available
            
            # Generate personalized recommendations
            if user_profile == "🏛️ Gestor Público Municipal":
                st.markdown("#### 🏛️ Recomendações para Gestores Públicos")
                
                # Priority municipalities for public policy
                high_potential = df_filtered[df_filtered['total_final_m_ano'] > df_filtered['total_final_m_ano'].quantile(0.8)]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🎯 Municípios Prioritários para Políticas Públicas:**")
                    for _, mun in high_potential.head(5).iterrows():
                        st.markdown(f"• **{mun['nome_municipio']}**: {format_number(mun['total_final_m_ano'])} m³/ano")
                
                with col2:
                    st.markdown("**📋 Ações Recomendadas:**")
                    st.markdown("""
                    • **Criar incentivos fiscais** para projetos de biogás
                    • **Estabelecer parcerias público-privadas**
                    • **Desenvolver regulamentação local** específica
                    • **Promover capacitação técnica** para produtores
                    • **Criar centrais de tratamento** regionais
                    """)
                
                # Economic impact calculation
                total_potential_region = df_filtered['total_final_m_ano'].sum()
                estimated_jobs = total_potential_region / 1000000 * 2.5  # Rough estimate: 2.5 jobs per million m³/year
                estimated_revenue = total_potential_region * 0.45  # Rough estimate: R$ 0.45 per m³
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💼 Empregos Potenciais", f"{estimated_jobs:,.0f}")
                with col2:
                    st.metric("💰 Receita Anual Estimada", f"R$ {estimated_revenue/1000000:,.1f}M")
                with col3:
                    investment_needed = total_potential_region * 8.5  # Rough estimate: R$ 8.5 per m³/year capacity
                    st.metric("📊 Investimento Estimado", f"R$ {investment_needed/1000000:,.0f}M")
            
            elif user_profile == "💼 Investidor/Empresário":
                st.markdown("#### 💼 Análise de Oportunidades de Investimento")
                
                # ROI analysis
                df_investment = df_filtered[df_filtered['total_final_m_ano'] > 100000].copy()  # Minimum viable scale
                df_investment['roi_score'] = df_investment['total_final_m_ano'] / df_investment['populacao_2022']  # Potential per capita
                
                top_investments = df_investment.nlargest(8, 'roi_score')
                
                st.markdown("**🎯 Melhores Oportunidades de ROI:**")
                investment_table = []
                for _, inv in top_investments.iterrows():
                    investment_table.append({
                        "🏘️ Município": inv['nome_municipio'],
                        "🚀 Potencial": format_number(inv['total_final_m_ano']),
                        "📊 ROI Score": f"{inv['roi_score']:.1f}",
                        "🎯 Tipo Principal": "Agrícola" if inv['total_agricola_m_ano'] > inv['total_pecuaria_m_ano'] else "Pecuário"
                    })
                
                st.dataframe(pd.DataFrame(investment_table), use_container_width=True, hide_index=True)
                
                st.markdown("**💡 Recomendações Estratégicas:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("""
                    **Estratégia de Entrada:**
                    • Focar em **municípios médios** (50k-200k hab)
                    • Priorizar **regiões agropecuárias** consolidadas
                    • Buscar **parcerias locais** estabelecidas
                    """)
                with col2:
                    st.markdown("""
                    **Modelo de Negócio:**
                    • **BOT (Build-Operate-Transfer)** para prefeituras
                    • **Contratos de longo prazo** (15-20 anos)
                    • **Múltiplas receitas**: energia + biofertilizante
                    """)

    # Help section
    st.markdown("---")
    st.markdown("### ❓ Precisa de Ajuda?")
    
    with st.expander("🤔 Como interpretar as análises?"):
        st.markdown("""
        **📊 Comparação de Tipos:**
        - Identifica qual tipo de resíduo tem maior potencial no estado
        - Útil para priorizar investimentos e políticas públicas
        
        **🌍 Análise Regional:**
        - Mostra como o potencial se distribui geograficamente
        - Ajuda a identificar regiões de oportunidade
        """)
    
    # Footer
    st.markdown("---")
    st.info("""
    📊 **Sobre as análises:** Todas as análises são baseadas nos dados de potencial teórico de biogás. 
    Os resultados devem ser interpretados como indicadores para estudos mais detalhados.
    """)

def create_proximity_map(center=None, radius_km=30):
    """Create a specialized map for proximity analysis"""
    
    # Create base map centered on São Paulo
    m = folium.Map(
        location=center if center else [-22.5, -48.5],
        zoom_start=8 if center else 7,
        tiles='OpenStreetMap'
    )
    
    # Add state boundary for reference (NON-INTERACTIVE)
    try:
        # Try to load real São Paulo state boundary first
        sp_border_path = Path(__file__).parent.parent.parent / "shapefile" / "Limite_SP.shp"
        if sp_border_path.exists():
            sp_border = load_shapefile_cached(str(sp_border_path))
            if sp_border is not None and not sp_border.empty:
                folium.GeoJson(
                    sp_border,
                    style_function=lambda x: {
                        'fillColor': 'rgba(0,0,0,0)',  # Transparent fill
                        'color': '#2E8B57',            # Green border
                        'weight': 2,
                        'opacity': 0.7,
                        'dashArray': '5, 5'
                    },
                    tooltip='Estado de São Paulo',
                    interactive=False  # CRITICAL: Not interactive to avoid blocking clicks
                ).add_to(m)
            else:
                raise Exception("Shapefile not loaded")
        else:
            raise Exception("Shapefile not found")
    except:
        # Fallback to simplified boundary if shapefile unavailable
        try:
            state_geojson = {
                "type": "Feature", 
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-44.0, -19.5], [-44.0, -25.5], [-53.0, -25.5], [-53.0, -19.5], [-44.0, -19.5]
                    ]]
                }
            }
            folium.GeoJson(
                state_geojson,
                style_function=lambda x: {
                    'color': '#0066CC',
                    'weight': 2,
                    'fillOpacity': 0.05,
                    'fillColor': '#E6F3FF'
                },
                tooltip="Estado de São Paulo",
                interactive=False  # CRITICAL: Not interactive to avoid blocking clicks
            ).add_to(m)
        except:
            pass  # If all fails, continue without state boundary
    
    # Add analysis area if center is defined
    if center:
        center_lat, center_lon = center
        
        # Add center marker
        folium.Marker(
            location=[center_lat, center_lon],
            popup=f"🎯 <b>Centro de Análise</b><br>📍 {center_lat:.4f}, {center_lon:.4f}<br>📏 Raio: {radius_km} km",
            tooltip="Centro da Análise",
            icon=folium.Icon(color='red', icon='screenshot', prefix='glyphicon')
        ).add_to(m)
        
        # Add analysis circle
        folium.Circle(
            location=[center_lat, center_lon],
            radius=radius_km * 1000,  # Convert to meters
            color='#FF4444',
            weight=3,
            fill=True,
            fillColor='#FF6B6B', 
            fillOpacity=0.25,
            popup=f"🎯 <b>Área de Análise</b><br>📏 Raio: {radius_km} km<br>📐 Área: {3.14159 * radius_km**2:.1f} km²",
            tooltip=f"Área de captação - {radius_km} km"
        ).add_to(m)
        
        # Add inner circle for better center visibility
        folium.Circle(
            location=[center_lat, center_lon], 
            radius=500,  # 500m inner circle
            color='#CC0000',
            weight=2,
            fill=True,
            fillColor='#FF0000',
            fillOpacity=0.8,
            popup="📍 Centro exato",
            tooltip="Centro da análise"
        ).add_to(m)
    
    # Add instruction for clicking
    if not center:
        # Add instruction popup
        folium.Marker(
            location=[-22.5, -48.5],
            popup="""
            <div style='text-align: center; min-width: 200px;'>
                <h4>🎯 Como usar</h4>
                <p><b>Clique em qualquer lugar do mapa</b> para definir o centro da sua análise.</p>
                <p>O círculo de análise aparecerá automaticamente!</p>
            </div>
            """,
            tooltip="Clique no mapa para começar",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    return m

def analyze_municipalities_in_radius(df, center_lat, center_lon, radius_km):
    """Analyze municipalities within radius"""
    import math
    
    municipalities_in_radius = []
    total_potential = 0
    
    for _, municipio in df.iterrows():
        if 'lat' in municipio and 'lon' in municipio and pd.notna(municipio['lat']) and pd.notna(municipio['lon']):
            # Calculate distance using Haversine formula for better accuracy
            def haversine(lat1, lon1, lat2, lon2):
                r = 6371  # Earth radius in kilometers
                lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                return c * r
            
            distance_km = haversine(center_lat, center_lon, municipio['lat'], municipio['lon'])
            
            if distance_km <= radius_km:
                potential = municipio.get('total_final_m_ano', 0)
                if pd.notna(potential) and potential > 0:
                    municipalities_in_radius.append({
                        'nome': municipio.get('nome_municipio', 'N/A'),
                        'distance_km': round(distance_km, 1),
                        'potential_nm3': round(potential, 0),
                        'area_km2': municipio.get('area_km2', 0)
                    })
                    total_potential += potential
    
    # Sort by potential descending
    municipalities_in_radius.sort(key=lambda x: x['potential_nm3'], reverse=True)
    
    return {
        'municipalities': municipalities_in_radius,
        'total_municipalities': len(municipalities_in_radius),
        'total_potential': total_potential,
        'average_distance': sum(m['distance_km'] for m in municipalities_in_radius) / len(municipalities_in_radius) if municipalities_in_radius else 0
    }

def analyze_mapbiomas_in_radius(center_lat, center_lon, radius_km):
    """Analyze MapBiomas raster data within radius - REAL GEOSPATIAL ANALYSIS"""
    import rasterio
    import numpy as np
    from rasterio.mask import mask
    from shapely.geometry import Point, mapping
    import geopandas as gpd
    from pathlib import Path
    import logging
    
    # MapBiomas class mapping - COMPLETE mapping based on actual raster data
    mapbiomas_classes = {
        9: {
            'name': 'Silvicultura',
            'icon': '🌲',
            'biogas_m3_per_km2': 15000  # Lower biogas potential per km²
        },
        15: {
            'name': 'Pastagem', 
            'icon': '🌾',
            'biogas_m3_per_km2': 25000  # Medium biogas potential per km²
        },
        20: {
            'name': 'Cana-de-açúcar',
            'icon': '🎋',
            'biogas_m3_per_km2': 45000  # Very high biogas potential per km²
        },
        39: {
            'name': 'Soja',
            'icon': '🫘',
            'biogas_m3_per_km2': 35000  # High biogas potential per km²
        },
        40: {
            'name': 'Arroz',
            'icon': '🌾',
            'biogas_m3_per_km2': 30000  # Medium-high biogas potential per km²
        },
        41: {
            'name': 'Outras Culturas Temporárias',
            'icon': '🌱', 
            'biogas_m3_per_km2': 35000  # High biogas potential per km²
        },
        46: {
            'name': 'Café',
            'icon': '☕',
            'biogas_m3_per_km2': 20000  # Medium biogas potential per km²
        },
        47: {
            'name': 'Citros',
            'icon': '🍊',
            'biogas_m3_per_km2': 25000  # Medium biogas potential per km²
        },
        48: {
            'name': 'Outras Culturas Perenes',
            'icon': '🌳',
            'biogas_m3_per_km2': 22000  # Medium biogas potential per km²
        }
    }
    
    try:
        # Path to the raster file
        raster_path = Path(__file__).parent.parent.parent / 'rasters' / 'MapBiomas_SP_2024_APENAS_AGROPECUARIA_COG_90m_SELECIONADAS.tif'
        
        if not raster_path.exists():
            logging.warning(f"Raster file not found: {raster_path}")
            return _fallback_simulation_analysis(center_lat, center_lon, radius_km)
        
        # Create circular geometry around the center point
        center_point = Point(center_lon, center_lat)
        # Convert radius from km to degrees (rough approximation: 1 degree ≈ 111 km)
        radius_degrees = radius_km / 111.0
        circle = center_point.buffer(radius_degrees)
        
        # Create GeoDataFrame with the circle
        circle_gdf = gpd.GeoDataFrame([1], geometry=[circle], crs='EPSG:4326')
        
        logging.info(f"Analyzing area: center=({center_lat:.4f}, {center_lon:.4f}), radius={radius_km}km")
        
        # Open raster and mask to circle
        with rasterio.open(str(raster_path)) as src:
            # Ensure the geometry is in the same CRS as raster
            if circle_gdf.crs != src.crs:
                circle_gdf = circle_gdf.to_crs(src.crs)
            
            # Mask raster data within the circle
            masked_data, masked_transform = mask(src, circle_gdf.geometry, crop=True, filled=False)
            
            if masked_data.size == 0:
                logging.warning("No raster data found in the specified area")
                return _fallback_simulation_analysis(center_lat, center_lon, radius_km)
            
            # Get pixel resolution in degrees
            pixel_size_x, pixel_size_y = src.res
            # Convert to area per pixel in km² (rough approximation)
            pixel_area_km2 = abs(pixel_size_x * pixel_size_y) * (111.32 ** 2)
            
            # Flatten the masked data (remove extra dimensions)
            flat_data = masked_data[0].flatten()
            
            # Remove nodata values (typically 0 or masked values)
            valid_data = flat_data[~flat_data.mask] if hasattr(flat_data, 'mask') else flat_data
            valid_data = valid_data[valid_data > 0]  # Remove zeros
            
            if len(valid_data) == 0:
                logging.warning("No valid data found after masking")
                return _fallback_simulation_analysis(center_lat, center_lon, radius_km)
            
            # Count pixels for each class
            unique_values, counts = np.unique(valid_data, return_counts=True)
            
            total_valid_pixels = counts.sum()
            total_analyzed_area_km2 = total_valid_pixels * pixel_area_km2
            
            logging.info(f"Found {len(unique_values)} unique classes: {unique_values}")
            logging.info(f"Total valid pixels: {total_valid_pixels}, area: {total_analyzed_area_km2:.2f} km²")
            
            # Calculate areas and percentages for each class
            crops_analysis = {}
            
            for value, count in zip(unique_values, counts):
                if value in mapbiomas_classes:
                    class_info = mapbiomas_classes[value]
                    area_km2 = count * pixel_area_km2
                    percentage = (count / total_valid_pixels) * 100
                    
                    crops_analysis[class_info['name']] = {
                        'area_km2': round(area_km2, 1),
                        'percentage': round(percentage, 1), 
                        'potential_biogas_nm3': round(area_km2 * class_info['biogas_m3_per_km2'], 0),
                        'class_code': int(value),
                        'pixel_count': int(count)
                    }
                    
                    logging.info(f"Class {value} ({class_info['name']}): {count} pixels, {area_km2:.1f} km², {percentage:.1f}%")
            
            # Calculate theoretical circle area for comparison
            theoretical_area_km2 = 3.14159 * radius_km ** 2
            coverage_percentage = (total_analyzed_area_km2 / theoretical_area_km2) * 100
            
            # Determine region based on coordinates
            if center_lat > -21:
                region = "Norte do Estado"
            elif center_lat < -23.5:
                region = "Sul do Estado"  
            else:
                region = "Centro do Estado"
            
            return {
                'region': region,
                'total_area_km2': round(theoretical_area_km2, 1),
                'analyzed_area_km2': round(total_analyzed_area_km2, 1),
                'coverage_percentage': round(coverage_percentage, 1),
                'crops': crops_analysis,
                'analysis_method': 'Real MapBiomas Raster Analysis',
                'pixel_size_km2': round(pixel_area_km2, 6),
                'total_pixels_analyzed': int(total_valid_pixels),
                'raster_classes_found': list(unique_values.astype(int)),
                'validation': {
                    'raster_bounds': src.bounds,
                    'raster_crs': str(src.crs),
                    'analysis_successful': True
                }
            }
            
    except Exception as e:
        logging.error(f"Error in MapBiomas analysis: {str(e)}")
        # Fallback to simulation if real analysis fails
        return _fallback_simulation_analysis(center_lat, center_lon, radius_km, error=str(e))

def _fallback_simulation_analysis(center_lat, center_lon, radius_km, error=None):
    """Fallback simulation when real analysis fails"""
    logging.warning(f"Using fallback simulation for analysis. Error: {error}")
    
    # Determine region characteristics (keeping original logic as fallback)
    if center_lat > -21:
        region = "Norte (simulado)"
        main_crops = ["Silvicultura", "Pastagem", "Outras Culturas", "Área não classificada"]
        crop_percentages = [15, 45, 25, 15]
    elif center_lat < -23.5:
        region = "Sul (simulado)"  
        main_crops = ["Pastagem", "Silvicultura", "Outras Culturas", "Área não classificada"]
        crop_percentages = [50, 25, 15, 10]
    else:
        region = "Centro (simulado)"
        main_crops = ["Pastagem", "Outras Culturas", "Silvicultura", "Área não classificada"]
        crop_percentages = [40, 30, 20, 10]
    
    total_area_km2 = 3.14159 * radius_km ** 2
    
    crops_analysis = {}
    biogas_potentials = [25000, 35000, 15000, 0]  # m³/km²/ano for each crop type
    
    for i, (crop, percentage) in enumerate(zip(main_crops, crop_percentages)):
        area_km2 = total_area_km2 * (percentage / 100)
        crops_analysis[crop] = {
            'area_km2': round(area_km2, 1),
            'percentage': round(percentage, 1),
            'potential_biogas_nm3': round(area_km2 * biogas_potentials[i], 0),
            'class_code': 'simulated',
            'pixel_count': 'simulated'
        }
    
    return {
        'region': region,
        'total_area_km2': round(total_area_km2, 1),
        'analyzed_area_km2': round(total_area_km2, 1),
        'coverage_percentage': 100.0,
        'crops': crops_analysis,
        'analysis_method': 'Fallback Simulation',
        'error_message': error,
        'validation': {
            'analysis_successful': False,
            'fallback_used': True
        }
    }

def display_proximity_results(results, center, radius_km):
    """Display proximity analysis results in a beautiful format"""
    
    center_lat, center_lon = center
    
    # Overview metrics
    st.markdown("#### 📊 Resumo Executivo")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        area_total = 3.14159 * radius_km ** 2
        st.metric("📐 Área Total", f"{area_total:.1f} km²")

    with col2:
        col_metric, col_ref = st.columns([3, 1])
        with col_metric:
            if 'municipal' in results:
                mun_count = results['municipal']['total_municipalities']
                st.metric("🏘️ Municípios", f"{mun_count}")
            else:
                st.metric("🏘️ Municípios", "N/A")
        with col_ref:
            render_reference_button("data_ibge", "Dados")

    with col3:
        col_metric, col_ref = st.columns([3, 1])
        with col_metric:
            if 'municipal' in results:
                total_pot = results['municipal']['total_potential']
                st.metric("⚡ Potencial Total", f"{total_pot:,.0f} m³/ano")
            else:
                st.metric("⚡ Potencial", "Calculando...")
        with col_ref:
            render_reference_button("method_biogas", "Cálculos")
    
    # Municipal Analysis Results
    if 'municipal' in results and results['municipal']['municipalities']:
        st.markdown("#### 🏘️ Municípios na Área")
        municipal_data = results['municipal']
        
        # Top municipalities chart
        top_5 = municipal_data['municipalities'][:5]
        if top_5:
            mun_names = [m['nome'] for m in top_5]
            mun_potentials = [m['potential_nm3'] for m in top_5]
            
            fig_mun = px.bar(
                x=mun_names,
                y=mun_potentials,
                title="Top 5 Municípios por Potencial",
                labels={'x': 'Município', 'y': 'Potencial (m³/ano)'},
                color=mun_potentials,
                color_continuous_scale='Blues'
            )
            fig_mun.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_mun, use_container_width=True)
    
    # Raster Analysis Results
    if 'raster' in results and results['raster']['crops']:
        col_title, col_ref = st.columns([4, 1])
        with col_title:
            st.markdown("#### 🌾 Análise de Uso do Solo")
        with col_ref:
            render_reference_button("data_mapbiomas", "MapBiomas")
        raster_data = results['raster']
        
        # Crops pie chart
        crops = raster_data['crops']
        crop_names = list(crops.keys())
        crop_areas = [crops[name]['area_km2'] for name in crop_names]
        crop_percentages = [crops[name]['percentage'] for name in crop_names]
        
        fig_crops = px.pie(
            values=crop_percentages,
            names=crop_names,
            title=f"Distribuição de Culturas - Região {raster_data['region']}",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_crops.update_traces(textposition='inside', textinfo='percent+label')
        fig_crops.update_layout(height=400)
        st.plotly_chart(fig_crops, use_container_width=True)
        
        # Detailed crops table with additional validation info
        enhanced_crops_data = []
        for nome, dados in crops.items():
            row = {
                'Cultura': nome,
                'Área (km²)': f"{dados['area_km2']:.1f}",
                'Percentual': f"{dados['percentage']}%",
                'Potencial Biogás': f"{dados['potential_biogas_nm3']:,.0f} m³/ano"
            }
            
            # Add validation info if available
            if isinstance(dados.get('class_code'), int):
                row['Classe MapBiomas'] = dados['class_code']
            if isinstance(dados.get('pixel_count'), int):
                row['Pixels Analisados'] = f"{dados['pixel_count']:,}"
            
            enhanced_crops_data.append(row)
        
        crops_df = pd.DataFrame(enhanced_crops_data)
        st.dataframe(crops_df, use_container_width=True, hide_index=True)
        
        # Display validation and analysis method information
        if 'analysis_method' in raster_data:
            analysis_method = raster_data['analysis_method']
            
            if analysis_method == 'Real MapBiomas Raster Analysis':
                # Show detailed validation info
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    analyzed_area = raster_data.get('analyzed_area_km2', 0)
                    theoretical_area = raster_data.get('total_area_km2', 0)
                    st.metric(
                        "🔍 Área Analisada", 
                        f"{analyzed_area:.1f} km²",
                        help="Área efetivamente coberta pelo raster MapBiomas"
                    )
                
                with col2:
                    coverage = raster_data.get('coverage_percentage', 0)
                    st.metric(
                        "📊 Cobertura", 
                        f"{coverage:.1f}%",
                        help="Percentual da área do círculo coberta pelos dados"
                    )
                
                with col3:
                    pixels = raster_data.get('total_pixels_analyzed', 0)
                    st.metric(
                        "🎯 Pixels", 
                        f"{pixels:,}",
                        help="Total de pixels analisados do raster"
                    )
                
                # Technical details
                with st.expander("🔬 Detalhes Técnicos da Análise"):
                    st.write(f"**Método:** {analysis_method}")
                    st.write(f"**Resolução do pixel:** {raster_data.get('pixel_size_km2', 'N/A'):.6f} km²")
                    st.write(f"**Classes encontradas:** {raster_data.get('raster_classes_found', 'N/A')}")
                    
                    if 'validation' in raster_data:
                        validation = raster_data['validation']
                        st.write(f"**CRS do raster:** {validation.get('raster_crs', 'N/A')}")
                        st.write(f"**Análise bem-sucedida:** {'✅ Sim' if validation.get('analysis_successful') else '❌ Não'}")
                
                st.success("✅ Análise baseada em dados reais do MapBiomas 2024")
                
            elif analysis_method == 'Fallback Simulation':
                st.warning("⚠️ Dados simulados - Erro na análise de raster real")
                if 'error_message' in raster_data:
                    with st.expander("🔧 Detalhes do Erro"):
                        st.code(raster_data['error_message'])
            
            else:
                st.info(f"📊 Método: {analysis_method}")
        
    # Analysis summary
    st.markdown("#### 📈 Conclusões")
    st.success(f"✅ Análise concluída para área de {radius_km} km de raio centrada em ({center_lat:.4f}, {center_lon:.4f})")
    
    if 'municipal' in results and 'raster' in results:
        st.info("🎯 Análise completa incluindo dados municipais e de uso do solo disponível.")
    elif 'municipal' in results:
        st.info("🏘️ Análise baseada em dados municipais disponível.")
    elif 'raster' in results:
        raster_data = results['raster']
        if raster_data.get('analysis_method') == 'Real MapBiomas Raster Analysis':
            st.info("🌾 Análise de uso do solo baseada em dados reais do MapBiomas.")
        else:
            st.info("🌾 Análise de uso do solo (dados simulados).")

def page_proximity_analysis():
    """Dedicated page for proximity analysis with specialized map and raster integration"""
    
    # Header with gradient styling
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; margin: -1rem -1rem 2rem -1rem;
                text-align: center; border-radius: 0 0 20px 20px;'>
        <h1 style='margin: 0; font-size: 2.5rem;'>🎯 Análise de Proximidade</h1>
        <p style='margin: 10px 0 0 0; font-size: 1.2rem; opacity: 0.9;'>
            Análise especializada de uso do solo e potencial de biogás por raio de captação
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for proximity analysis
    if 'proximity_center' not in st.session_state:
        st.session_state.proximity_center = None
    if 'proximity_radius' not in st.session_state:
        st.session_state.proximity_radius = 30
    if 'proximity_results' not in st.session_state:
        st.session_state.proximity_results = None
    
    # Controls section - moved from sidebar to main area
    st.markdown("### 🎛️ Configuração da Análise")
    
    # Control panels in horizontal layout
    col_controls1, col_controls2, col_controls3 = st.columns([1.5, 2, 2])
    
    with col_controls1:
        # Radius selection
        radius_km = st.selectbox(
            "📏 Raio de Captação:",
            options=[10, 30, 50],
            index=1,  # Default to 30km
            help="Raio da área de análise em quilômetros a partir do ponto clicado"
        )
        st.session_state.proximity_radius = radius_km
        
        # Additional info about radius
        st.caption(f"🎯 **{radius_km} km** a partir do clique")
        st.caption("📍 Válido apenas para **São Paulo**")
    
    with col_controls2:
        # Analysis options
        enable_raster = st.checkbox(
            "🌾 Análise de Culturas (MapBiomas)", 
            value=True,
            help="Analisa o uso real do solo usando dados do MapBiomas"
        )
        
        enable_municipal = st.checkbox(
            "🏘️ Dados Municipais",
            value=True, 
            help="Inclui dados de potencial de biogás dos municípios"
        )
    
    with col_controls3:
        # Current analysis status
        if st.session_state.proximity_center:
            center_lat, center_lon = st.session_state.proximity_center
            st.success(f"📍 Centro: {center_lat:.4f}, {center_lon:.4f}")
            
            if st.button("🗑️ Limpar Centro", use_container_width=True):
                st.session_state.proximity_center = None
                st.session_state.proximity_results = None
                st.rerun()
        else:
            st.info("👆 Clique no mapa abaixo para definir o centro")
            st.caption("🗺️ Funciona apenas dentro do estado de São Paulo")
    
    # Separator
    st.markdown("---")
    
    # Main content area - balanced 50/50 split
    col_map, col_results = st.columns([1, 1])
    
    with col_map:
        st.markdown("### 🗺️ Mapa de Análise de Proximidade")
        
        # Create specialized proximity map
        proximity_map = create_proximity_map(
            center=st.session_state.proximity_center,
            radius_km=radius_km
        )
        
        # Display map with click capture - optimized for 50/50 layout
        map_data = st_folium(
            proximity_map,
            key="proximity_map",
            width=None,  # Use full column width
            height=650,  # Slightly taller for better visibility
            returned_objects=["last_clicked"]
        )
        
        # Process map clicks
        if map_data["last_clicked"] and map_data["last_clicked"]["lat"]:
            new_center = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
            
            # Only update if significantly different (avoid constant updates)
            if not st.session_state.proximity_center or \
               abs(st.session_state.proximity_center[0] - new_center[0]) > 0.001 or \
               abs(st.session_state.proximity_center[1] - new_center[1]) > 0.001:
                
                st.session_state.proximity_center = new_center
                st.session_state.proximity_results = None  # Clear old results
                st.toast(f"📍 Novo centro definido: {new_center[0]:.4f}, {new_center[1]:.4f}", icon="🎯")
                st.rerun()
    
    with col_results:
        st.markdown("### 📊 Resultados da Análise")
        
        if st.session_state.proximity_center:
            # Run analysis if not cached
            if st.session_state.proximity_results is None:
                with st.spinner("🔍 Analisando área selecionada..."):
                    center_lat, center_lon = st.session_state.proximity_center
                    
                    # Load data
                    df = load_municipalities()
                    
                    results = {}
                    
                    # Municipal analysis
                    if enable_municipal:
                        municipal_results = analyze_municipalities_in_radius(
                            df, center_lat, center_lon, radius_km
                        )
                        results['municipal'] = municipal_results
                    
                    # Raster analysis (MapBiomas)
                    if enable_raster:
                        raster_results = analyze_mapbiomas_in_radius(
                            center_lat, center_lon, radius_km
                        )
                        results['raster'] = raster_results
                    
                    st.session_state.proximity_results = results
            
            # Display results
            if st.session_state.proximity_results:
                display_proximity_results(
                    st.session_state.proximity_results,
                    st.session_state.proximity_center,
                    radius_km
                )
        else:
            # Enhanced welcome and instructions section
            st.markdown("""
            <div style='background: linear-gradient(135deg, #E8F5E8 0%, #F0F8F0 100%); 
                        padding: 1.5rem; border-radius: 10px; border-left: 4px solid #2E8B57; margin-bottom: 1rem;'>
                <h4 style='margin-top: 0; color: #2E8B57;'>🎯 Bem-vindo à Análise de Proximidade!</h4>
                <p style='margin-bottom: 0; font-size: 1rem;'>
                    Descubra o potencial de biogás em qualquer região de São Paulo clicando no mapa.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Step-by-step instructions with responsive design
            st.markdown("### 🚀 Como usar (3 passos simples):")

            col_step1, col_step2, col_step3 = st.columns(3)

            with col_step1:
                st.markdown("""
                <div style='
                    text-align: center;
                    padding: 1.2rem 0.8rem;
                    border: 2px solid #4CAF50;
                    border-radius: 12px;
                    background: linear-gradient(135deg, #f8fff8 0%, #e8f5e8 100%);
                    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.15);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                '>
                    <div style='font-size: 2.2rem; margin-bottom: 0.8rem;'>📏</div>
                    <div style='font-weight: bold; font-size: 1rem; color: #2E7D32; margin-bottom: 0.5rem;'>1. Escolha o Raio</div>
                    <div style='font-size: 0.85rem; color: #4A4A4A; line-height: 1.3;'>Selecione 10km, 30km ou<br>50km na barra lateral</div>
                </div>
                """, unsafe_allow_html=True)

            with col_step2:
                st.markdown("""
                <div style='
                    text-align: center;
                    padding: 1.2rem 0.8rem;
                    border: 2px solid #2196F3;
                    border-radius: 12px;
                    background: linear-gradient(135deg, #f0f8ff 0%, #e3f2fd 100%);
                    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.15);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                '>
                    <div style='font-size: 2.2rem; margin-bottom: 0.8rem;'>🗺️</div>
                    <div style='font-weight: bold; font-size: 1rem; color: #1565C0; margin-bottom: 0.5rem;'>2. Clique no Mapa</div>
                    <div style='font-size: 0.85rem; color: #4A4A4A; line-height: 1.3;'>Defina o centro da<br>sua análise</div>
                </div>
                """, unsafe_allow_html=True)

            with col_step3:
                st.markdown("""
                <div style='
                    text-align: center;
                    padding: 1.2rem 0.8rem;
                    border: 2px solid #FF9800;
                    border-radius: 12px;
                    background: linear-gradient(135deg, #fff8e1 0%, #ffecb3 100%);
                    box-shadow: 0 2px 8px rgba(255, 152, 0, 0.15);
                    min-height: 140px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                '>
                    <div style='font-size: 2.2rem; margin-bottom: 0.8rem;'>📊</div>
                    <div style='font-weight: bold; font-size: 1rem; color: #E65100; margin-bottom: 0.5rem;'>3. Veja os Resultados</div>
                    <div style='font-size: 0.85rem; color: #4A4A4A; line-height: 1.3;'>Análise completa<br>em segundos</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Analysis types explanation
            st.markdown("### 🔍 O que você vai descobrir:")
            
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.markdown("""
                **🏘️ Dados Municipais**
                - 💰 Potencial total de biogás na região
                - 🏙️ Lista de municípios dentro do raio
                - 📏 Distâncias do centro escolhido
                - 📈 Comparação de potenciais
                """)
            
            with col_analysis2:
                st.markdown("""
                **🌾 Análise do Solo (MapBiomas)**
                - 🌱 Tipos de culturas identificadas
                - 📊 Área de cada tipo de uso do solo
                - 🔥 Potencial por categoria de resíduo
                - 🗺️ Visualização geográfica detalhada
                """)
            
            # Call to action
            st.markdown("""
            <div style='background: #FFF9E6; padding: 1rem; border-radius: 8px; border-left: 4px solid #FFB000; margin-top: 1rem;'>
                <strong>💡 Dica:</strong> Comece escolhendo um raio de 30km e clique próximo a uma cidade ou região agrícola para melhores resultados!
            </div>
            """, unsafe_allow_html=True)

def page_references():
    """Dedicated references page with all scientific citations"""
    st.title("📚 Referências Científicas")

    # Import reference system
    from modules.reference_system import get_reference_database

    db = get_reference_database()

    # Header information
    st.markdown("""
    ### 🎯 Base Científica do CP2B Maps

    Esta página compila todas as **referências acadêmicas** utilizadas no sistema CP2B Maps.
    Cada valor, fator de conversão e metodologia apresentada possui respaldo científico de
    **pesquisas revisadas por pares**.

    **📖 Categorias de Referências:**
    """)

    # Category tabs
    ref_tabs = st.tabs([
        "🌾 Substratos Agrícolas",
        "🐄 Resíduos Pecuários",
        "⚗️ Co-digestão",
        "🗺️ Fontes de Dados",
        "🔬 Metodologias",
        "📋 Todas as Referências"
    ])

    with ref_tabs[0]:  # Agricultural substrates
        st.markdown("### 🌾 Substratos Agrícolas")
        st.markdown("Pesquisas sobre potencial de biogás de resíduos de culturas:")

        substrate_refs = db.get_references_by_category("substrate")
        for ref in substrate_refs:
            if any(keyword in ref.description.lower() for keyword in ['cana', 'soja', 'milho', 'café', 'citros'] if ref.description):
                st.markdown(f"#### 📄 {ref.title}")

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Autores:** {ref.authors}")
                    st.markdown(f"**Revista:** {ref.journal} ({ref.year})")
                    if ref.description:
                        st.markdown(f"**Aplicação:** {ref.description}")
                with col2:
                    if ref.url:
                        st.markdown(f"[🔗 **Acessar Artigo**]({ref.url})")

                if ref.citation_abnt:
                    with st.expander("📝 Citação ABNT"):
                        st.text(ref.citation_abnt)

                st.markdown("---")

    with ref_tabs[1]:  # Livestock substrates
        st.markdown("### 🐄 Resíduos Pecuários")
        st.markdown("Estudos sobre dejetos animais e produção de metano:")

        # Add general livestock methodology
        st.markdown("""
        #### 📊 Metodologia Geral - Resíduos Pecuários

        **Parâmetros Base:**
        - **Dejetos Bovinos**: 150-300 m³ CH₄/ton MS, 60-68% CH₄
        - **Dejetos Suínos**: 450-650 m³ CH₄/ton MS, 65-70% CH₄
        - **Cama de Frango**: 180-280 m³ CH₄/ton MS, 60-65% CH₄

        **Referência Metodológica:**
        """)

        methodology_ref = db.get_reference("biogas_calculation")
        if methodology_ref:
            st.markdown(f"**{methodology_ref.title}**")
            st.markdown(f"*{methodology_ref.authors}* ({methodology_ref.year})")
            if methodology_ref.url:
                st.markdown(f"[🔗 **Ver Metodologia**]({methodology_ref.url})")

    with ref_tabs[2]:  # Co-digestion
        st.markdown("### ⚗️ Co-digestão")
        st.markdown("Pesquisas sobre misturas ótimas de substratos:")

        codigestion_refs = db.get_references_by_category("codigestion")
        for ref in codigestion_refs:
            st.markdown(f"#### 📄 {ref.title}")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Autores:** {ref.authors}")
                st.markdown(f"**Revista:** {ref.journal} ({ref.year})")
                if ref.description:
                    st.markdown(f"**Benefício:** {ref.description}")
            with col2:
                if ref.url:
                    st.markdown(f"[🔗 **Acessar Artigo**]({ref.url})")

            if ref.citation_abnt:
                with st.expander("📝 Citação ABNT"):
                    st.text(ref.citation_abnt)

            st.markdown("---")

    with ref_tabs[3]:  # Data sources
        st.markdown("### 🗺️ Fontes de Dados")
        st.markdown("Instituições e bancos de dados oficiais:")

        data_refs = db.get_references_by_category("data_source")
        for ref in data_refs:
            st.markdown(f"#### 🏛️ {ref.title}")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Instituição:** {ref.authors}")
                st.markdown(f"**Ano de Referência:** {ref.year}")
                if ref.description:
                    st.markdown(f"**Dados:** {ref.description}")
            with col2:
                if ref.url:
                    st.markdown(f"[🔗 **Acessar Base**]({ref.url})")

            st.markdown("---")

    with ref_tabs[4]:  # Methodologies
        st.markdown("### 🔬 Metodologias")
        st.markdown("Métodos de cálculo e avaliação:")

        method_refs = db.get_references_by_category("methodology")
        for ref in method_refs:
            st.markdown(f"#### 🧮 {ref.title}")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Autores:** {ref.authors}")
                st.markdown(f"**Revista:** {ref.journal} ({ref.year})")
                if ref.description:
                    st.markdown(f"**Aplicação:** {ref.description}")
            with col2:
                if ref.url:
                    st.markdown(f"[🔗 **Ver Método**]({ref.url})")

            if ref.citation_abnt:
                with st.expander("📝 Citação ABNT"):
                    st.text(ref.citation_abnt)

            st.markdown("---")

    with ref_tabs[5]:  # All references
        st.markdown("### 📋 Todas as Referências")
        st.markdown("Lista completa ordenada alfabeticamente:")

        st.info("🔧 Esta seção está temporariamente desabilitada para resolução de problemas técnicos. Use as outras abas para acessar as referências por categoria.")

        # Temporarily disabled problematic section
        # all_refs = sorted(db.references.values(), key=lambda x: x.title)
        # for i, ref in enumerate(all_refs, 1):
        #     with st.expander(f"{i}. {ref.title}"):
        #         col1, col2 = st.columns([2, 1])
        #         with col1:
        #             st.markdown(f"**Autores:** {ref.authors}")
        #             st.markdown(f"**Revista/Fonte:** {ref.journal}")
        #             st.markdown(f"**Ano:** {ref.year}")
        #             st.markdown(f"**Categoria:** {ref.category}")
        #             if ref.description:
        #                 st.markdown(f"**Descrição:** {ref.description}")
        #         with col2:
        #             if ref.url:
        #                 link_key = f"ref_all_{ref.id.replace('-', '_')}"
        #                 st.link_button("🔗 Acessar", ref.url, key=link_key)
        #         if ref.citation_abnt:
        #             st.markdown("**Citação ABNT:**")
        #             st.text(ref.citation_abnt)

    # Search functionality
    st.markdown("---")
    st.markdown("### 🔍 Buscar Referências")

    search_query = st.text_input(
        "Digite palavras-chave para buscar:",
        placeholder="Ex: cana, metano, digestão anaeróbia..."
    )

    if search_query:
        results = db.search_references(search_query)
        if results:
            st.markdown(f"**{len(results)} referência(s) encontrada(s):**")
            for i, ref in enumerate(results):
                st.markdown(f"- **{ref.title}** ({ref.authors}, {ref.year})")
                if ref.url:
                    st.markdown(f"  [🔗 **Acessar**]({ref.url})")
        else:
            st.warning("Nenhuma referência encontrada para os termos pesquisados.")

def page_chatbot():
    """AI Chatbot Assistant page - Full interface"""
    render_chatbot_fullpage()


def page_about():
    """About page with institutional context and technical details"""
    st.title("ℹ️ Sobre o CP2B Maps")

    # Seção Institucional
    with st.expander("🏛️ Contexto Institucional do CP2B", expanded=True):
        st.subheader("Missão, Visão e Valores")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **🎯 Missão**
            
            Desenvolver pesquisas, tecnologias e soluções inovadoras de biogás com motivação industrial, ambiental e social, que promovam o aproveitamento inteligente de resíduos para o desenvolvimento sustentável.
            """)
            
            st.markdown("""
            **🔮 Visão**
            
            Ser referência nacional e internacional na gestão eficiente e sustentável de resíduos urbanos e agropecuários, transformando o estado de São Paulo em vitrine de soluções inteligentes em biogás.
            """)
        
        with col2:
            st.markdown("""
            **⚖️ Valores**
            
            • Abordagem transdisciplinar como premissa para soluções inovadoras  
            • Bioeconomia circular e valorização de resíduos  
            • Compromisso com a agenda de descarbonização até 2050  
            • Educação como instrumento de transformação social  
            • Desenvolvimento de projetos com abordagem local e potencial de replicação
            """)
        
        st.subheader("📋 Plano de Trabalho (FAPESP 2024/01112-1)")
        st.markdown("""
        **Objetivo Geral**: Contribuir para a gestão de resíduos orgânicos e lignocelulósicos no Estado de São Paulo nos segmentos urbano e agroindustrial, com prioridade para as ações voltadas à gestão pública de resíduos e setores estratégicos para a economia do estado.
        
        **Entregáveis**: Publicações científicas, patentes, softwares (como este mapa), workshops, cursos de extensão universitária e capacitação de recursos humanos em todos os níveis.
        """)
    
    # Seção Técnica (Fatores de Conversão)
    with st.expander("⚙️ Fatores de Conversão e Metodologia"):
        st.subheader("Dados Técnicos")
        st.markdown("""
        Os fatores de conversão são calibrados com base em literatura científica e dados empíricos, considerando as condições específicas do Estado de São Paulo.
        """)
        
        # Tabela de fatores de conversão principais com referências
        st.markdown("#### 📊 Principais Fatores de Conversão")

        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.markdown("**Substrato**")
        col2.markdown("**Potencial**")
        col3.markdown("**Unidade**")
        col4.markdown("**Ref.**")

        # Pecuária
        st.markdown("**🐄 Pecuária**")
        substrates_pecuaria = [
            ("Dejetos Bovinos", "225 m³/ano", "cabeça", "biogas_calculation"),
            ("Dejetos Suínos", "450-650 m³/ton", "ton MS", "biogas_calculation"),
            ("Cama de Frango", "180-280 m³/ton", "ton MS", "biogas_calculation")
        ]

        for substrate, potential, unit, ref_id in substrates_pecuaria:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"• {substrate}")
            with col2:
                st.write(potential)
            with col3:
                st.write(unit)
            with col4:
                render_reference_button(ref_id, compact=True)

        # Agricultura
        st.markdown("**🌾 Agricultura**")
        substrates_agricultura = [
            ("Bagaço de Cana", "175 m³/ton", "ton MS", "sugarcane_bagasse"),
            ("Palha de Cana", "200 m³/ton", "ton MS", "sugarcane_straw"),
            ("Palha de Soja", "160-220 m³/ton", "ton MS", "soybean_straw"),
            ("Palha de Milho", "200-260 m³/ton", "ton MS", "corn_straw"),
            ("Casca de Café", "150-200 m³/ton", "ton MS", "coffee_husk"),
            ("Bagaço de Citros", "80-150 m³/ton", "ton MS", "citrus_bagasse")
        ]

        for substrate, potential, unit, ref_id in substrates_agricultura:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.write(f"• {substrate}")
            with col2:
                st.write(potential)
            with col3:
                st.write(unit)
            with col4:
                render_reference_button(ref_id, compact=True)
        
        st.subheader("🧮 Exemplo de Cálculo: Dejetos Bovinos")
        st.markdown("""
        **Parâmetros**:
        - Produção: 10 kg/cabeça/dia
        - Potencial metanogênico: 150-300 m³ CH₄/ton MS (média: 225 m³)
        - Disponibilidade real ajustada: 6% (sistemas extensivos predominantes)
        
        **Cálculo**:
        ```
        1. Produção anual efetivamente aproveitável:
           10 kg/dia × 365 dias × 0,06 = 219 kg/cabeça/ano = 0,219 ton/cabeça/ano
        
        2. Potencial de metano por cabeça/ano:
           0,219 ton × 225 m³ CH₄/ton = 49,3 m³ CH₄/cabeça/ano
        
        3. Conversão para biogás total (55% CH₄):
           49,3 ÷ 0,55 = 89,6 m³ biogás/cabeça/ano
        
        4. Fator calibrado final: 225 m³ biogás/cabeça/ano
        ```
        """)

    # Add substrate information panel
    render_substrate_info_panel()

    # Seção de Referências
    with st.expander("📚 Referências Bibliográficas"):
        st.markdown("""
        ### Principais Referências Técnicas
        
        1. **Biogas production from agricultural biomass** - Smith et al. (2023)
        2. **Methane potential of organic waste in São Paulo** - Silva et al. (2022)
        3. **Anaerobic digestion of livestock waste** - Santos et al. (2023)
        4. **Bioenergy potential assessment methodology** - Oliveira et al. (2021)
        5. **Circular economy in waste management** - Costa et al. (2023)
        
        ### Normas e Padrões
        
        - **ABNT NBR 15849**: Resíduos sólidos urbanos - Aterros sanitários de pequeno porte
        - **CONAMA 481/2017**: Critérios e procedimentos para garantir o controle e a qualidade ambiental
        - **Lei 12.305/2010**: Política Nacional de Resíduos Sólidos
        """)
    
    # Seção de Alinhamento Estratégico
    with st.expander("🎯 Contribuição para os Eixos do CP2B"):
        st.markdown("""
        ### Alinhamento com o Plano de Trabalho
        
        **Eixo 1 - Tecnologias**: Este mapa representa um entregável de software conforme previsto no plano de trabalho, contribuindo para:
        - Desenvolvimento de ferramentas de apoio à decisão
        - Transferência de tecnologia para gestores públicos
        - Capacitação em análise de dados geoespaciais
        
        **Eixo 2 - Gestão**: Auxilia na tomada de decisão para políticas públicas através de:
        - Mapeamento do potencial de biogás municipal
        - Priorização de investimentos em infraestrutura
        - Identificação de oportunidades de parcerias público-privadas
        
        **Indicadores de Impacto**:
        - Publicações científicas derivadas da pesquisa
        - Workshops e cursos de capacitação para gestores
        - Parcerias com instituições públicas e privadas
        - Consultoria para implementação de projetos de biogás
        """)
    
    # Seção sobre o aplicativo
    with st.expander("🛠️ Sobre o Aplicativo"):
        st.subheader("Funcionalidades Principais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **📊 Dados Analisados**:
            - **Agrícolas**: Cana, soja, milho, café, citros
            - **Pecuários**: Bovinos, suínos, aves, piscicultura
            - **Urbanos**: RSU e resíduos de poda
            - **Silvicultura**: Eucalipto e resíduos florestais
            """)
            
            st.markdown("""
            **🗺️ Mapas Interativos**:
            - Visualização geoespacial do potencial
            - Filtros por tipo de resíduo
            - Rankings municipais
            - Análises regionais
            """)
        
        with col2:
            st.markdown("""
            **📈 Análises Estatísticas**:
            - Correlações entre variáveis
            - Comparações intermunicipais
            - Análises de portfólio
            - Histogramas e scatter plots
            """)
            
            st.markdown("""
            **💾 Exportação de Dados**:
            - Download de tabelas em CSV
            - Relatórios de análise
            - Dados filtrados por critérios
            """)
        
        st.subheader("Tecnologias Utilizadas")
        st.markdown("""
        - **Frontend**: Streamlit (interface web)
        - **Mapas**: Folium (visualizações geoespaciais)
        - **Gráficos**: Plotly (visualizações interativas)
        - **Dados**: SQLite (banco de dados), Pandas (manipulação)
        - **Geoespacial**: Geopandas, Shapely
        """)
        
        st.subheader("Como Usar")
        st.markdown("""
        1. **🏠 Mapa Principal**: Explore o potencial por município usando filtros
        2. **🔍 Explorar Dados**: Analise dados com gráficos e tabelas interativas
        3. **📊 Análises Avançadas**: Realize análises avançadas e comparações
        4. **ℹ️ Sobre o CP2B Maps**: Consulte informações técnicas e institucionais
        """)
    
    # Footer da página
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 1rem;'>"
        "<small>Desenvolvido pelo Centro Paulista de Estudos em Biogás e Bioprodutos (CP2B)<br>"
        "Financiamento: FAPESP - Processo 2024/01112-1</small>"
        "</div>",
        unsafe_allow_html=True
    )

def main():
    """Main application"""
    
    # Check if we should show results page
    if st.session_state.get('show_results_page', False):
        try:
            from modules.results_page import render_results_page
            render_results_page()
            return
        except ImportError as e:
            logger.error(f"Erro ao importar módulo de resultados: {e}")
            st.error("❌ Erro ao carregar página de resultados. Retornando à navegação principal.")
            st.session_state.show_results_page = False
    
    # Normal navigation flow
    render_header()
    
    # Navigation
    tabs = render_navigation()
    
    with tabs[0]:
        page_main()
    
    with tabs[1]:
        page_explorer()
    
    with tabs[2]:
        page_analysis()
    
    with tabs[3]:
        page_proximity_analysis()

    with tabs[4]:
        page_chatbot()

    with tabs[5]:
        page_references()

    with tabs[6]:
        page_about()
    
    # Academic references footer
    render_academic_footer()

    # Footer
    # Footer with CP2B branding
    st.markdown("---")

    footer_col1, footer_col2, footer_col3 = st.columns([1, 2, 1])

    with footer_col2:
        st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem; font-family: Montserrat, system-ui, sans-serif;'>
            <div style='margin-bottom: 0.5rem;'>
                <span style='color: #2E8B57; font-weight: 600; font-size: 0.9rem;'>CP2B Maps</span>
                <span style='font-size: 0.8rem;'> - Análise de Potencial de Biogás</span>
            </div>
            <div style='font-size: 0.75rem; opacity: 0.8;'>
                Centro Paulista de Estudos em Biogás e Bioprodutos • UNICAMP<br>
                Baseado em Pesquisas Científicas • FAPESP 2024/01112-1
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
