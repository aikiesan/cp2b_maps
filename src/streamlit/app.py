"""
CP2B Maps - Clean Multi-Page Streamlit Application
Simple and robust biogas potential analysis for São Paulo municipalities
"""

import streamlit as st

# Configure page layout for wide mode
st.set_page_config(
    page_title="CP2B Maps",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"  # This ensures the sidebar is visible and open on load
)
import pandas as pd
import folium
from streamlit_folium import st_folium
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import numpy as np
import logging
from folium.plugins import MiniMap, HeatMap, MarkerCluster
import re  # We need this for parsing the popup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Constants
RESIDUE_OPTIONS = {
    'Potencial Total': 'total_final_nm_ano',
    'Total Agrícola': 'total_agricola_nm_ano',
    'Total Pecuária': 'total_pecuaria_nm_ano',
    'Cana-de-açúcar': 'biogas_cana_nm_ano',
    'Soja': 'biogas_soja_nm_ano',
    'Milho': 'biogas_milho_nm_ano',
    'Café': 'biogas_cafe_nm_ano',
    'Citros': 'biogas_citros_nm_ano',
    'Bovinos': 'biogas_bovinos_nm_ano',
    'Suínos': 'biogas_suino_nm_ano',
    'Aves': 'biogas_aves_nm_ano',
    'Piscicultura': 'biogas_piscicultura_nm_ano',
    'Resíduos Urbanos': 'rsu_potencial_nm_habitante_ano',
    'Resíduos Poda': 'rpo_potencial_nm_habitante_ano'
}

# Database functions
@st.cache_data
def get_database_path():
    """Get database path"""
    return Path(__file__).parent.parent.parent / "data" / "cp2b_maps.db"

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
            logger.info(f"Loaded {len(df)} municipalities")
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

# Navigation functions
def render_header():
    """Render application header"""
    st.markdown("""
    <div style='background: linear-gradient(135deg, #2E8B57 0%, #228B22 50%, #32CD32 100%); 
                color: white; padding: 1.5rem; margin: -1rem -1rem 1rem -1rem;
                text-align: center; border-radius: 0 0 15px 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
        <h1 style='margin: 0; font-size: 2.2rem; font-weight: 700;'>🗺️ Análise de Potencial de Biogás</h1>
        <p style='margin: 5px 0 0 0; font-size: 1rem; opacity: 0.9;'>
            645 municípios de São Paulo
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_navigation():
    """Simple tab-based navigation"""
    tabs = st.tabs([
        "🏠 Mapa Principal",
        "🔍 Explorar Dados",
        "📊 Análises",
        "ℹ️ Sobre"
    ])
    
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
            max_count = st.slider("Max:", 10, 645, 100, key=f"{page_key}_max")
    
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
    
    if normalization_type == "Potencial Absoluto (Nm³/ano)":
        # No normalization - use original values
        return df_norm, base_col
        
    elif normalization_type == "Potencial per Capita (Nm³/hab/ano)":
        # Normalize by population
        if 'populacao_2022' in df_norm.columns:
            normalized_col = f"{base_col}_per_capita"
            df_norm[normalized_col] = df_norm[base_col] / df_norm['populacao_2022'].replace(0, 1)  # Avoid division by zero
            df_norm[normalized_col] = df_norm[normalized_col].fillna(0)
            return df_norm, normalized_col
        else:
            st.warning("⚠️ Dados populacionais não disponíveis para normalização per capita")
            return df_norm, base_col
            
    elif normalization_type == "Potencial por Área (Nm³/km²/ano)":
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
        return df, 'total_final_nm_ano'
    
    # Always work with a full copy of the dataframe
    df_to_display = df.copy()
    
    # Calculate display column based on residue selection
    if not filters['residues']:
        # Default case if nothing is selected
        display_col = 'total_final_nm_ano'
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
    if 'normalization' in filters and filters['normalization'] != "Potencial Absoluto (Nm³/ano)":
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
            shapefile_path = Path(__file__).parent.parent.parent / "shapefile" / "Municipios_SP_shapefile.shp"
            if shapefile_path.exists():
                gdf = gpd.read_file(shapefile_path)
                if gdf.crs != 'EPSG:4326':
                    gdf = gdf.to_crs('EPSG:4326')
                gdf['cd_mun'] = gdf['CD_MUN'].astype(str)
                return gdf
    except Exception as e:
        st.error(f"Error loading geometries: {e}")
    
    return None

def create_centroid_map(df, display_col, filters=None, get_legend_only=False, search_term="", viz_type="Círculos Proporcionais"):
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
        
        # Add only clean, professional basemap options (NO DARK MODE)
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
        folium.TileLayer('Stamen Terrain', name='Terreno').add_to(m)
        # Dark mode basemap removed completely
        # ------------------------------------
        
        if df.empty:
            # Add Layer Control even if map is empty, for consistency
            folium.LayerControl().add_to(m)
            return m, ""  # Return map and empty legend string
        
        # Add São Paulo state borders first (background)
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
                    tooltip='Estado de São Paulo'
                ).add_to(m)
        except Exception as e:
            st.warning(f"⚠️ Bordas do estado: {e}")
        
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
                    {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} Nm³/ano
                    """
                    
                    # The tooltip remains clean
                    tooltip_text = f"{row['nome_municipio']}: {row[display_col]:,.0f} Nm³/ano"
                    
                    # Check if this municipality matches the search term
                    is_searched = (search_term and 
                                  search_term.lower() in row['nome_municipio'].lower())
                    
                    folium.CircleMarker(
                        location=[lat, lon],
                        radius=row['circle_size'] * 1.5 if is_searched else row['circle_size'],
                        popup=popup_text,
                        tooltip=f"{'🔍 ' if is_searched else ''}{tooltip_text}",
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
                    {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} Nm³/ano<br>
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
                        tooltip=f"{'🔍 ' if is_searched else ''}{row['nome_municipio']}: {row[display_col]:,.0f}",
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
                                legend_name=f'Potencial (Nm³/ano)',
                                highlight=True,
                                smooth_factor=0.5
                            ).add_to(m)
                            
                            # Add interactive popups for each municipality
                            for idx, row in df_choropleth.iterrows():
                                # Create popup with embedded ID for selection
                                popup_text = f"""
                                <!-- id:{row['cd_mun']} -->
                                <b>{row.get('nome_municipio', 'Município')}</b><br>
                                {display_col.replace('_', ' ').title()}: {row[display_col]:,.0f} Nm³/ano<br>
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
            
            # 2. Add Layer Control at the end to ensure it's on top
            folium.LayerControl().add_to(m)
            # -----------------------------------------
            
            # --- SIMPLIFIED LEGEND HTML for the Sidebar ---
            # No positioning or complex styling needed here. It will flow naturally in the sidebar.
            legend_html = f'''
            <div style="font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 13px;">
                <h4 style="margin-top: 0; margin-bottom: 12px; color: #2E8B57; text-align: center;">
                    🗺️ Legenda do Mapa
                </h4>
                <div style="margin-bottom: 10px;">
                    <strong>📊 Dados:</strong> {display_col.replace('_', ' ').title()}
                </div>
                <div style="margin-bottom: 12px;">
                    <strong>📈 Faixa de Potencial:</strong><br>
                    Min: {df_merged[display_col].min():,.0f} Nm³/ano<br>
                    Max: {df_merged[display_col].max():,.0f} Nm³/ano
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
                <strong>📊 Dados:</strong> {display_col.replace('_', ' ').title()}
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
        
        return m, legend_html
        
    except Exception as e:
        st.error(f"❌ Map creation error: {e}")
        return folium.Map(location=[-22.5, -48.5], zoom_start=7), ""  # Return empty map/legend

def create_map(df, display_col):
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
        labels={display_col: 'Potencial (Nm³/ano)', 'nome_municipio': 'Município'}
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
        labels={display_col: 'Potencial (Nm³/ano)'}
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
        labels={'populacao_2022': 'População (2022)', display_col: 'Potencial (Nm³/ano)'},
        color_continuous_scale='Viridis',
        size_max=60
    )
    fig.update_layout(height=400)
    return fig

# Page functions
def page_main():
    """Main map page with ultra-thin sidebar and comprehensive analysis tools."""
    
    # --- 1. Ultra-thin sidebar CSS ---
    st.markdown("""<style>
    section[data-testid="stSidebar"] { 
        width: 200px !important; 
        min-width: 200px !important; 
        max-width: 200px !important; 
    }
    section[data-testid="stSidebar"] .stButton button { width: 100%; font-size: 12px; }
    section[data-testid="stSidebar"] .stSelectbox label { font-size: 14px; }
    section[data-testid="stSidebar"] h2 { font-size: 1.2rem; }
    section[data-testid="stSidebar"] h3 { font-size: 1rem; }
    </style>""", unsafe_allow_html=True)

    if 'selected_municipalities' not in st.session_state:
        st.session_state.selected_municipalities = []

    df = load_municipalities()
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    total_municipality_count = len(df)

    # --- 2. Ultra-minimal sidebar ---
    with st.sidebar:
        st.markdown("## 🎛️ Filtros")
        
        # Selection mode
        mode = st.radio(
            "Modo:",
            ["Individual", "Múltiplos"],
            horizontal=True,
            key="map_mode"
        )
        
        # Residue selection based on mode
        if mode == "Individual":
            selected = st.selectbox("Resíduo:", list(RESIDUE_OPTIONS.keys()), key="map_select")
            residues = [RESIDUE_OPTIONS[selected]]
            display_name = selected
        else:
            selected_list = st.multiselect(
                "Resíduos:",
                list(RESIDUE_OPTIONS.keys()),
                default=["Potencial Total"],
                key="map_multi"
            )
            residues = [RESIDUE_OPTIONS[item] for item in selected_list]
            display_name = f"Soma de {len(residues)} tipos" if len(residues) > 1 else (selected_list[0] if selected_list else "Nenhum")
        
        # Quick search
        search_term = st.text_input("🔍 Buscar:", placeholder="Município...", key="search")
        
        st.markdown("---")
        st.markdown("### 📊 Normalização de Dados")
        
        normalization = st.selectbox(
            "Métrica:",
            options=[
                "Potencial Absoluto (Nm³/ano)",
                "Potencial per Capita (Nm³/hab/ano)", 
                "Potencial por Área (Nm³/km²/ano)",
                "Densidade Populacional (hab/km²)"
            ],
            key="normalization",
            help="Escolha como normalizar os dados para comparação mais justa entre municípios"
        )
        
        st.markdown("---")
        st.markdown("### 📈 Classificação dos Dados")
        
        classification = st.selectbox(
            "Método de Classificação:",
            options=[
                "Linear (Intervalo Uniforme)",
                "Quantiles (Contagem Igual)", 
                "Quebras Naturais (Jenks)",
                "Desvio Padrão"
            ],
            key="classification",
            help="Escolha como agrupar os valores para visualização em classes"
        )
        
        num_classes = st.slider(
            "Número de Classes:",
            min_value=3,
            max_value=8,
            value=5,
            key="num_classes",
            help="Quantidade de grupos/cores para classificar os dados"
        )
        
        st.markdown("---")
        st.markdown("### 🗺️ Estilo de Visualização")

        viz_type = st.radio(
            "Selecione o tipo de mapa:",
            options=["Círculos Proporcionais", "Mapa de Calor (Heatmap)", "Agrupamentos (Clusters)", "Mapa de Preenchimento (Coroplético)"],
            horizontal=False,
            label_visibility="collapsed",
            help="Mude a forma como os dados são exibidos no mapa.",
            key="viz_type"
        )
        
        st.markdown("---")
        st.markdown("### 🎯 Análise de Proximidade")
        
        # Initialize proximity analysis session state
        if 'catchment_center' not in st.session_state:
            st.session_state.catchment_center = None
        if 'catchment_radius' not in st.session_state:
            st.session_state.catchment_radius = 50
        
        # Proximity analysis controls
        enable_proximity = st.checkbox(
            "Ativar Análise de Raio de Captação",
            help="Clique no mapa para definir centro e calcular potencial total na área"
        )
        
        if enable_proximity:
            catchment_radius = st.slider(
                "Raio de Captação (km):",
                min_value=10,
                max_value=200,
                value=st.session_state.catchment_radius,
                step=5,
                help="Distância máxima para coleta de resíduos"
            )
            st.session_state.catchment_radius = catchment_radius
            
            # Display current analysis results
            if st.session_state.catchment_center:
                center_lat, center_lon = st.session_state.catchment_center
                st.write(f"**Centro:** {center_lat:.4f}, {center_lon:.4f}")
                
                # Calculate municipalities within radius
                catchment_results = calculate_catchment_area(
                    df_to_display, center_lat, center_lon, catchment_radius, display_col
                )
                
                if catchment_results:
                    st.metric(
                        f"Potencial Total ({catchment_radius}km):",
                        f"{catchment_results['total_potential']:,.0f} Nm³/ano"
                    )
                    st.metric(
                        "Municípios na Área:",
                        f"{catchment_results['municipality_count']}"
                    )
                    
                    with st.expander(f"Ver {len(catchment_results['municipalities'])} Municípios"):
                        for mun in catchment_results['municipalities'][:10]:  # Show top 10
                            st.write(f"• {mun['name']}: {mun['potential']:,.0f} ({mun['distance']:.1f}km)")
                        if len(catchment_results['municipalities']) > 10:
                            st.write(f"... e mais {len(catchment_results['municipalities'])-10}")
                
                if st.button("Limpar Centro de Captação"):
                    st.session_state.catchment_center = None
                    st.rerun()
            else:
                st.info("👆 Clique no mapa para definir o centro de captação")
        else:
            st.session_state.catchment_center = None
        
        # Selected municipalities (if any)
        if st.session_state.selected_municipalities:
            st.markdown("**Selecionados:**")
            selected_names = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]['nome_municipio'].tolist()
            for name in selected_names[:3]:  # Show only first 3 to save space
                st.markdown(f"• {name[:15]}..." if len(name) > 15 else f"• {name}")
            if len(selected_names) > 3:
                st.markdown(f"...+{len(selected_names)-3} mais")
            if st.button("Limpar", key="clear_selection"):
                st.session_state.selected_municipalities.clear()
                st.rerun()
            
    # --- 3. Main Page Content ---
    df_to_display, display_col = apply_filters(df, {
        'residues': residues, 
        'display_name': display_name, 
        'normalization': normalization,
        'classification': classification,
        'num_classes': num_classes
    })
    
    # Map
    map_object, _ = create_centroid_map(df_to_display, display_col, search_term=search_term, viz_type=viz_type)
    map_data = st_folium(map_object, key="main_map", width=None, height=650)

    # Process map clicks
    if map_data:
        # Handle proximity analysis clicks (clicks on empty map areas)
        if map_data.get("last_clicked") and enable_proximity:
            clicked_lat = map_data["last_clicked"]["lat"]
            clicked_lng = map_data["last_clicked"]["lng"]
            st.session_state.catchment_center = (clicked_lat, clicked_lng)
            st.rerun()
        
        # Handle municipality selection clicks (clicks on popups)
        elif map_data.get("last_object_clicked_popup"):
            popup_html = map_data["last_object_clicked_popup"]
            match = re.search(r"<!-- id:(\d+) -->", popup_html)
            if match:
                clicked_id = match.group(1)
                if clicked_id in st.session_state.selected_municipalities:
                    st.session_state.selected_municipalities.remove(clicked_id)
                else:
                    st.session_state.selected_municipalities.append(clicked_id)
                st.rerun()
    
    # --- 4. COMPREHENSIVE ANALYSIS TOOLS BELOW MAP ---
    st.markdown("---")
    st.markdown("## 📊 Ferramentas de Análise Avançada")
    
    # Analysis mode selection
    analysis_tabs = st.tabs([
        "📈 Análise Geral", 
        "🔍 Análise Detalhada", 
        "⚖️ Comparação", 
        "🎯 Filtros Avançados",
        "📋 Dados Completos"
    ])
    
    with analysis_tabs[0]:  # General Analysis
        if st.session_state.selected_municipalities:
            selected_df = df[df['cd_mun'].isin(st.session_state.selected_municipalities)]
            st.markdown(f"### 🔬 Análise para **{len(selected_df)}** Município(s) Selecionado(s)")
            
            # Enhanced single vs multiple analysis
            if len(selected_df) == 1:
                mun = selected_df.iloc[0]
                st.markdown(f"#### Perfil Completo: **{mun['nome_municipio']}**")
                
                # Key metrics for single municipality
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("População", f"{mun.get('populacao_2022', 'N/A'):,}" if pd.notna(mun.get('populacao_2022')) else "N/A")
                with col2:
                    st.metric("Potencial Total", f"{mun['total_final_nm_ano']:,.0f}")
                with col3:
                    st.metric("Agrícola", f"{mun['total_agricola_nm_ano']:,.0f}")
                with col4:
                    st.metric("Pecuária", f"{mun['total_pecuaria_nm_ano']:,.0f}")
                
                # Donut chart for composition
                residue_cols = {v: k for k, v in RESIDUE_OPTIONS.items() if 'Total' not in k}
                analysis_df = selected_df[['nome_municipio'] + list(residue_cols.keys())]
                melted_df = analysis_df.melt(id_vars='nome_municipio', var_name='Tipo', value_name='Potencial').rename(columns={'nome_municipio': 'Município'})
                melted_df['Tipo'] = melted_df['Tipo'].map(residue_cols)
                melted_df = melted_df[melted_df['Potencial'] > 0]  # Remove zeros for cleaner chart
                
                fig = px.pie(melted_df, names='Tipo', values='Potencial', 
                           title='Composição do Potencial por Tipo de Resíduo', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.markdown("#### Comparativo entre Municípios Selecionados")
                # Summary metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Selecionados", len(selected_df))
                with col2:
                    st.metric("Potencial Conjunto", f"{selected_df['total_final_nm_ano'].sum():,.0f}")
                with col3:
                    st.metric("Média dos Selecionados", f"{selected_df['total_final_nm_ano'].mean():,.0f}")
                
                # Comparative bar chart
                residue_cols = {v: k for k, v in RESIDUE_OPTIONS.items() if 'Total' not in k}
                analysis_df = selected_df[['nome_municipio'] + list(residue_cols.keys())]
                melted_df = analysis_df.melt(id_vars='nome_municipio', var_name='Tipo', value_name='Potencial').rename(columns={'nome_municipio': 'Município'})
                melted_df['Tipo'] = melted_df['Tipo'].map(residue_cols)
                
                fig = px.bar(melted_df, x='Município', y='Potencial', color='Tipo',
                           title='Comparativo de Potencial por Tipo de Resíduo', barmode='group')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
        else:
            # State-wide analysis with enhanced visuals
            st.markdown("### 📊 Análise Estadual: " + display_name)
            
            # Enhanced 4-column layout
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("##### 🏆 Top 15 Municípios")
                chart1 = create_top_chart(df_to_display, display_col, display_name, limit=15)
                if chart1: st.plotly_chart(chart1, use_container_width=True)
            with col2:
                st.markdown("##### 📈 Distribuição")
                chart2 = create_distribution_chart(df_to_display, display_col, display_name)
                if chart2: st.plotly_chart(chart2, use_container_width=True)
            with col3:
                st.markdown("##### 👥 vs População")
                chart3 = create_correlation_chart(df_to_display, display_col, display_name)
                if chart3: st.plotly_chart(chart3, use_container_width=True)
            with col4:
                st.markdown("##### 📊 Estatísticas")
                st.metric("Média", f"{df_to_display[display_col].mean():,.0f}")
                st.metric("Mediana", f"{df_to_display[display_col].median():,.0f}")
                st.metric("Desvio Padrão", f"{df_to_display[display_col].std():,.0f}")
                st.metric("Soma Total", f"{df_to_display[display_col].sum():,.0f}")
    
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
                top_mun = df.nlargest(1, col_name).iloc[0] if not df[col_name].isna().all() else None
                if top_mun is not None:
                    agri_data.append({
                        'Tipo': res_type,
                        'Líder': top_mun['nome_municipio'],
                        'Potencial': top_mun[col_name]
                    })
            
            if agri_data:
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
                top_mun = df.nlargest(1, col_name).iloc[0] if not df[col_name].isna().all() else None
                if top_mun is not None:
                    pec_data.append({
                        'Tipo': res_type,
                        'Líder': top_mun['nome_municipio'],
                        'Potencial': top_mun[col_name]
                    })
            
            if pec_data:
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
            
            # Radar chart comparison
            residue_cols = {v: k for k, v in RESIDUE_OPTIONS.items() if 'Total' not in k}
            
            # Create radar chart data
            radar_data = []
            for _, mun in comparison_df.iterrows():
                for col_key, col_name in residue_cols.items():
                    if col_key in mun and pd.notna(mun[col_key]):
                        radar_data.append({
                            'Município': mun['nome_municipio'],
                            'Categoria': col_name,
                            'Potencial': mun[col_key]
                        })
            
            if radar_data:
                radar_df = pd.DataFrame(radar_data)
                
                # Line chart for comparison
                fig = px.line(radar_df, x='Categoria', y='Potencial', color='Município',
                            title='Comparação Detalhada entre Municípios',
                            markers=True)
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary table
                summary_cols = ['nome_municipio', 'total_final_nm_ano', 'total_agricola_nm_ano', 'total_pecuaria_nm_ano']
                available_summary_cols = [col for col in summary_cols if col in comparison_df.columns]
                summary_df = comparison_df[available_summary_cols].round(0)
                st.dataframe(summary_df, use_container_width=True)
    
    with analysis_tabs[3]:  # Advanced Filters
        st.markdown("### 🎯 Filtros Avançados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Filtros por Valor")
            min_potential = st.number_input("Potencial Mínimo:", min_value=0, value=0, step=1000)
            max_potential = st.number_input("Potencial Máximo:", min_value=0, value=int(df[display_col].max()), step=1000)
            
        with col2:
            st.markdown("#### Filtros por Tipo")
            residue_filter = st.multiselect(
                "Incluir apenas tipos:",
                list(RESIDUE_OPTIONS.keys()),
                default=list(RESIDUE_OPTIONS.keys()),
                key="advanced_residue_filter"
            )
            
        with col3:
            st.markdown("#### Filtros Geográficos")
            if 'populacao_2022' in df.columns and df['populacao_2022'].notna().any():
                pop_min = int(df['populacao_2022'].min())
                pop_max = int(df['populacao_2022'].max())
                
                # Ensure min is less than max for slider
                if pop_min >= pop_max:
                    pop_max = pop_min + 1000
                
                pop_range = st.slider(
                    "Faixa populacional:",
                    min_value=pop_min,
                    max_value=pop_max,
                    value=(pop_min, pop_max),
                    key="pop_range"
                )
            else:
                st.info("Dados populacionais não disponíveis")
                pop_range = None
        
        # Apply filters
        filtered_df = df_to_display.copy()
        filtered_df = filtered_df[(filtered_df[display_col] >= min_potential) & 
                                (filtered_df[display_col] <= max_potential)]
        
        if pop_range is not None and 'populacao_2022' in df.columns:
            filtered_df = filtered_df[(filtered_df['populacao_2022'] >= pop_range[0]) & 
                                    (filtered_df['populacao_2022'] <= pop_range[1])]
        
        st.markdown(f"**Resultado do filtro:** {len(filtered_df)} municípios")
        
        if len(filtered_df) > 0:
            # Show filtered results
            chart = create_top_chart(filtered_df, display_col, "Municípios Filtrados", limit=10)
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
            default=['nome_municipio', 'total_final_nm_ano', 'total_agricola_nm_ano', 'total_pecuaria_nm_ano'],
            key="column_selector"
        )
        
        if selected_cols:
            available_selected_cols = [col for col in selected_cols if col in display_df.columns]
            final_display_df = display_df[available_selected_cols].sort_values(by=available_selected_cols[1] if len(available_selected_cols) > 1 else available_selected_cols[0], ascending=False)
            st.dataframe(final_display_df, use_container_width=True, height=600)

def page_explorer():
    """Data explorer page"""
    st.markdown("## 🔍 Explorar Dados")
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    filters = render_compact_filters("explorer")
    df_filtered, display_col = apply_filters(df, filters)
    
    if df_filtered.empty:
        st.warning("⚠️ Nenhum dado encontrado.")
        return
    
    # Statistics
    st.markdown("### 📈 Estatísticas")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Contagem", len(df_filtered))
    with col2:
        st.metric("Média", format_number(df_filtered[display_col].mean()))
    with col3:
        st.metric("Mediana", format_number(df_filtered[display_col].median()))
    with col4:
        st.metric("Desvio Padrão", format_number(df_filtered[display_col].std()))
    
    # Rankings by category
    st.markdown("---")
    st.markdown("### 🏆 Rankings por Categoria")
    
    for label, column in RESIDUE_OPTIONS.items():
        if column in df.columns:
            top_5 = df.nlargest(5, column)
            if not top_5.empty and top_5[column].sum() > 0:
                with st.expander(f"Top 5 - {label}"):
                    for _, row in top_5.iterrows():
                        st.write(f"**{row['nome_municipio']}**: {format_number(row[column])}")
    
    # Download section
    st.markdown("---")
    st.markdown("### 📥 Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📁 Dataset Completo"):
            csv = df.to_csv(index=False)
            st.download_button(
                "💾 Baixar CSV",
                csv,
                "cp2b_completo.csv",
                "text/csv"
            )
    
    with col2:
        if st.button("🔍 Dados Filtrados"):
            csv = df_filtered.to_csv(index=False)
            st.download_button(
                "💾 Baixar Filtrados",
                csv,
                "cp2b_filtrados.csv",
                "text/csv"
            )

def page_analysis():
    """Analysis page"""
    st.markdown("## 📊 Análises Avançadas")
    
    df = load_municipalities()
    
    if df.empty:
        st.error("❌ Dados não encontrados.")
        return
    
    st.markdown("### 📈 Correlações")
    
    # Get numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) > 1:
        # Select columns for correlation
        selected_cols = st.multiselect(
            "Selecione colunas para correlação:",
            numeric_cols,
            default=numeric_cols[:5]
        )
        
        if len(selected_cols) > 1:
            corr_matrix = df[selected_cols].corr()
            
            fig = px.imshow(
                corr_matrix,
                title="Matriz de Correlação",
                color_continuous_scale="RdBu_r"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Comparação Entre Tipos")
    
    # Multiple residue comparison
    comparison_types = st.multiselect(
        "Selecione tipos para comparar:",
        list(RESIDUE_OPTIONS.keys()),
        default=list(RESIDUE_OPTIONS.keys())[:3]
    )
    
    if comparison_types:
        comparison_data = []
        for municipality in df.nlargest(10, 'total_final_nm_ano')['nome_municipio']:
            muni_data = df[df['nome_municipio'] == municipality].iloc[0]
            for res_type in comparison_types:
                col_name = RESIDUE_OPTIONS[res_type]
                if col_name in df.columns:
                    comparison_data.append({
                        'Município': municipality,
                        'Tipo': res_type,
                        'Potencial': muni_data[col_name]
                    })
        
        if comparison_data:
            df_comp = pd.DataFrame(comparison_data)
            
            fig = px.bar(
                df_comp,
                x='Município',
                y='Potencial',
                color='Tipo',
                title='Comparação por Tipo de Resíduo (Top 10)',
                barmode='group'
            )
            fig.update_layout(xaxis_tickangle=-45, height=500)
            st.plotly_chart(fig, use_container_width=True)

def page_about():
    """About page"""
    st.markdown("## ℹ️ Sobre o CP2B Maps")
    
    st.markdown("""
    ### 🎯 Objetivo
    
    Plataforma para análise do potencial de biogás nos municípios de São Paulo.
    
    ### 📊 Dados
    
    - **Agrícolas**: Cana, soja, milho, café, citros
    - **Pecuários**: Bovinos, suínos, aves, piscicultura
    - **Urbanos**: RSU e resíduos de poda
    
    ### 🛠️ Tecnologias
    
    - Streamlit, Folium, Plotly, SQLite, Pandas
    
    ### 📝 Como Usar
    
    1. Use as abas para navegar
    2. Ajuste filtros na barra lateral
    3. Explore mapas e dados
    4. Baixe dados quando necessário
    
    ### 🔗 Desenvolvimento
    
    Baseado no repositório cp2b_maps com foco em simplicidade e robustez.
    """)

def main():
    """Main application"""
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
        page_about()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; padding: 1rem;'>"
        "<small>CP2B Maps - Análise de Potencial de Biogás</small>"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()